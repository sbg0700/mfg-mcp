"""
backend/catalog.py — DL-1 datalake catalog 접근 계층.

- 마이그레이션: spec-1 §1-5 정규화 3테이블(entries/columns/constraints) + 5 인덱스.
  멱등(CREATE ... IF NOT EXISTS), DROP 0, datalake 스키마만 (PROTOCOL §3).
- datalake.get(id) → {data_path, modality}: 데이터→엔진 경계의 단일 해석점.
  단일 SELECT, LLM 0 (D-163).
- CRUD: entries(upsert/get/list) · columns(insert/get) · constraints(insert/get) · delete.
- 컬럼명은 D-171 반영: column_name / constraint_spec.
"""
from __future__ import annotations

import json
from typing import Any

from db import get_pool

# spec-1 §1-5 verbatim (D-160/D-161/D-167/D-171). 멱등·비파괴 — DROP 0, datalake 스키마만.
MIGRATION_SQL = """
CREATE SCHEMA IF NOT EXISTS datalake;

CREATE TABLE IF NOT EXISTS datalake.entries (
    datalake_id    TEXT PRIMARY KEY,
    source         TEXT NOT NULL,
    name           TEXT NOT NULL,
    modality       TEXT,
    function       TEXT,
    site           TEXT,
    vid            TEXT,
    size_bytes     BIGINT,
    encoding       TEXT,
    data_path      TEXT NOT NULL,
    reusable_flag  BOOLEAN DEFAULT FALSE,
    registered_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS datalake.columns (
    datalake_id    TEXT NOT NULL REFERENCES datalake.entries(datalake_id),
    name           TEXT NOT NULL,
    dtype          TEXT,
    column_kind    TEXT NOT NULL DEFAULT 'scalar',
    group_desc     JSONB,
    PRIMARY KEY (datalake_id, name)
);

CREATE TABLE IF NOT EXISTS datalake.constraints (
    datalake_id     TEXT NOT NULL REFERENCES datalake.entries(datalake_id),
    column_name     TEXT NOT NULL,
    constraint_spec JSONB NOT NULL,
    approved_at     TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (datalake_id, column_name)
);

CREATE INDEX IF NOT EXISTS idx_datalake_modality ON datalake.entries(modality);
CREATE INDEX IF NOT EXISTS idx_datalake_source   ON datalake.entries(source);
CREATE INDEX IF NOT EXISTS idx_datalake_vid      ON datalake.entries(vid);
CREATE INDEX IF NOT EXISTS idx_datalake_function ON datalake.entries(function);
CREATE INDEX IF NOT EXISTS idx_datalake_site     ON datalake.entries(site);
"""


async def run_migration() -> None:
    """멱등 마이그레이션. 여러 번 실행해도 동일(객체 중복 0)."""
    pool = await get_pool()
    await pool.execute(MIGRATION_SQL)


# ── 결정론 라우터 (D-163) ──────────────────────────────────────────────
async def get(datalake_id: str) -> dict[str, Any] | None:
    """datalake.get — {data_path, modality} 또는 None. 단일 SELECT, LLM 0."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT data_path, modality FROM datalake.entries WHERE datalake_id = $1",
        datalake_id,
    )
    return dict(row) if row is not None else None


# ── entries ────────────────────────────────────────────────────────────
async def upsert_entry(entry: dict[str, Any]) -> None:
    """entries upsert. ON CONFLICT(datalake_id) — registered_at은 최초 등록값 보존."""
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO datalake.entries
            (datalake_id, source, name, modality, function, site, vid,
             size_bytes, encoding, data_path, reusable_flag)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        ON CONFLICT (datalake_id) DO UPDATE SET
            source=EXCLUDED.source, name=EXCLUDED.name, modality=EXCLUDED.modality,
            function=EXCLUDED.function, site=EXCLUDED.site, vid=EXCLUDED.vid,
            size_bytes=EXCLUDED.size_bytes, encoding=EXCLUDED.encoding,
            data_path=EXCLUDED.data_path, reusable_flag=EXCLUDED.reusable_flag
        """,
        entry["datalake_id"], entry.get("source"), entry.get("name"),
        entry.get("modality"), entry.get("function"), entry.get("site"),
        entry.get("vid"), entry.get("size_bytes"), entry.get("encoding"),
        entry["data_path"], entry.get("reusable_flag", False),
    )


async def get_entry(datalake_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM datalake.entries WHERE datalake_id = $1", datalake_id)
    return dict(row) if row is not None else None


# 필터 화이트리스트 (인젝션 차단 — 고정 컬럼명만 동적 WHERE에 허용)
_FILTERABLE = ("modality", "function", "site", "source", "vid")


async def list_entries(**filters: Any) -> list[dict[str, Any]]:
    """필터(modality/function/site/source/vid) AND 조합. 미지정 필터는 무시."""
    clauses: list[str] = []
    args: list[Any] = []
    for col in _FILTERABLE:
        val = filters.get(col)
        if val is not None:
            args.append(val)
            clauses.append(f"{col} = ${len(args)}")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    pool = await get_pool()
    rows = await pool.fetch(
        f"SELECT * FROM datalake.entries{where} ORDER BY registered_at DESC", *args)
    return [dict(r) for r in rows]


# ── columns (column_kind = scalar | group, group_desc JSONB — D-161) ────
async def insert_column(datalake_id: str, name: str, dtype: str | None = None,
                        column_kind: str = "scalar",
                        group_desc: dict | None = None) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO datalake.columns (datalake_id, name, dtype, column_kind, group_desc)
        VALUES ($1,$2,$3,$4,$5::jsonb)
        ON CONFLICT (datalake_id, name) DO UPDATE SET
            dtype=EXCLUDED.dtype, column_kind=EXCLUDED.column_kind,
            group_desc=EXCLUDED.group_desc
        """,
        datalake_id, name, dtype, column_kind,
        json.dumps(group_desc) if group_desc is not None else None,
    )


async def get_columns(datalake_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM datalake.columns WHERE datalake_id = $1 ORDER BY name", datalake_id)
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        if d.get("group_desc") is not None:
            d["group_desc"] = json.loads(d["group_desc"])
        out.append(d)
    return out


# ── constraints (D-171: column_name / constraint_spec) ──────────────────
async def insert_constraint(datalake_id: str, column_name: str,
                            constraint_spec: dict) -> None:
    """제약 = 유저 승인값(D-167). prefill 제안 소스이지 잠금 아님."""
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO datalake.constraints (datalake_id, column_name, constraint_spec)
        VALUES ($1,$2,$3::jsonb)
        ON CONFLICT (datalake_id, column_name) DO UPDATE SET
            constraint_spec=EXCLUDED.constraint_spec, approved_at=now()
        """,
        datalake_id, column_name, json.dumps(constraint_spec),
    )


async def get_constraints(datalake_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM datalake.constraints WHERE datalake_id = $1 ORDER BY column_name",
        datalake_id)
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        if d.get("constraint_spec") is not None:
            d["constraint_spec"] = json.loads(d["constraint_spec"])
        out.append(d)
    return out


# ── delete (명시 삭제 — CASCADE 미채택, §1-5 FK verbatim 유지) ──────────
async def delete_entry(datalake_id: str) -> None:
    """자식(constraints→columns) 명시 삭제 후 부모 삭제(단일 트랜잭션).
    CASCADE 미채택: §1-5 FK를 verbatim 유지하고 연쇄삭제를 코드에서 명시적으로
    드러낸다(anti-silent-conversion)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM datalake.constraints WHERE datalake_id = $1", datalake_id)
            await conn.execute(
                "DELETE FROM datalake.columns WHERE datalake_id = $1", datalake_id)
            await conn.execute(
                "DELETE FROM datalake.entries WHERE datalake_id = $1", datalake_id)
