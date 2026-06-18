"""
backend/catalog.py — DL-1 datalake catalog 접근 계층.

- 마이그레이션: spec-1 §1-5 정규화 3테이블(entries 14컬럼/columns/constraints) + 6 인덱스.
  멱등(CREATE ... IF NOT EXISTS · ADD COLUMN IF NOT EXISTS), DROP 0, datalake 스키마만 (PROTOCOL §3).
  DL-2 확장: entries +format +company (D-174). 기존 DL-1 테이블엔 ALTER 로 멱등 추가.
- datalake.get(id) → {data_path, modality}: 데이터→엔진 경계의 단일 해석점.
  단일 SELECT, LLM 0 (D-163).
- CRUD: entries(upsert/get/list) · columns(insert/get) · constraints(insert/get) · delete.
- 컬럼명은 D-171 반영: column_name / constraint_spec.
- 감사(D-179): constraints +approved_by, 모든 쓰기/삭제 경로는 동일 트랜잭션에서
  constraints_history(append-only, FK 없음)에 action(create/update/delete) 기록.
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
    format         TEXT,                  -- DL-2: 원본 파일 포맷 (canonical 정규화 후 원본 추적, D-174/#11)
    data_path      TEXT NOT NULL,
    reusable_flag  BOOLEAN DEFAULT FALSE,
    company        TEXT,                  -- DL-2: 멀티테넌트 필터 (현 kamp degenerate, site 형제, D-174)
    registered_at  TIMESTAMPTZ DEFAULT now()
);

-- DL-2: 기존 테이블(DL-1 생성)은 CREATE IF NOT EXISTS 가 스킵되므로 ALTER 로 멱등 추가
-- (ADD COLUMN IF NOT EXISTS = DROP 0, 비파괴, PROTOCOL §3 / D-174). 라이브 실행은 B단계(백업 후).
ALTER TABLE datalake.entries ADD COLUMN IF NOT EXISTS format  TEXT;
ALTER TABLE datalake.entries ADD COLUMN IF NOT EXISTS company TEXT;

-- per-column 메타. column_kind = scalar | group (광폭/숫자헤더 = group descriptor, D-161;
-- L3 vibration = raw 시간영역 waveform, group_desc.kind='waveform' D-176)
CREATE TABLE IF NOT EXISTS datalake.columns (
    datalake_id    TEXT NOT NULL REFERENCES datalake.entries(datalake_id),
    name           TEXT NOT NULL,
    dtype          TEXT,
    column_kind    TEXT NOT NULL DEFAULT 'scalar',
    group_desc     JSONB,
    ordinal        INT,                   -- DL-3.5 A: 소스 헤더 물리 순서 (D-193/194; group=first-member rank, scalar=index)
    PRIMARY KEY (datalake_id, name)
);

-- DL-3.5 A (D-193): ordinal 기존 DB 진화 = ALTER 멱등 추가(additive, DROP 0, PROTOCOL §3).
-- NOT NULL + UNIQUE(datalake_id, ordinal) 는 backfill 이후 finalize(tools/datalake_ordinal_backfill.py)
-- — run_migration(항상 실행)에 두면 backfill 전 NULL / replace_columns(ordinal 미주입)로 실패 → 분리.
ALTER TABLE datalake.columns ADD COLUMN IF NOT EXISTS ordinal INT;

-- (b) 관측 통계 min/max — 데이터 '사실'(규격 제안 아님 → D-43 무위반). additive, DROP 0, 멱등.
--     백필 = tools/datalake_stats_backfill.py (라인3 우선, 후속 전체). get_columns SELECT * 로 API 자동 노출.
ALTER TABLE datalake.columns ADD COLUMN IF NOT EXISTS stat_min DOUBLE PRECISION;
ALTER TABLE datalake.columns ADD COLUMN IF NOT EXISTS stat_max DOUBLE PRECISION;

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
CREATE INDEX IF NOT EXISTS idx_datalake_company  ON datalake.entries(company);

-- ── DL-2.5: constraints 감사 추적 (approved_by + append-only history, D-179) ──
-- additive only (ADD COLUMN/CREATE ... IF NOT EXISTS), DROP 0. 라이브 적용 = C-2(백업·복원드릴 후).
ALTER TABLE datalake.constraints
    ADD COLUMN IF NOT EXISTS approved_by TEXT;

CREATE TABLE IF NOT EXISTS datalake.constraints_history (
    history_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    datalake_id     TEXT NOT NULL,
    column_name     TEXT NOT NULL,
    constraint_spec JSONB NOT NULL,
    approved_by     TEXT,
    approved_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    action          TEXT NOT NULL CHECK (action IN ('create','update','delete'))
);
-- 감사 레코드는 entry 삭제 후에도 보존 → FK 없음(의도, D-179).
CREATE INDEX IF NOT EXISTS idx_dl_constraints_hist_key
    ON datalake.constraints_history(datalake_id, column_name);
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
             size_bytes, encoding, format, data_path, reusable_flag, company)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
        ON CONFLICT (datalake_id) DO UPDATE SET
            source=EXCLUDED.source, name=EXCLUDED.name, modality=EXCLUDED.modality,
            function=EXCLUDED.function, site=EXCLUDED.site, vid=EXCLUDED.vid,
            size_bytes=EXCLUDED.size_bytes, encoding=EXCLUDED.encoding,
            format=EXCLUDED.format, data_path=EXCLUDED.data_path,
            reusable_flag=EXCLUDED.reusable_flag, company=EXCLUDED.company
        """,
        entry["datalake_id"], entry.get("source"), entry.get("name"),
        entry.get("modality"), entry.get("function"), entry.get("site"),
        entry.get("vid"), entry.get("size_bytes"), entry.get("encoding"),
        entry.get("format"), entry["data_path"], entry.get("reusable_flag", False),
        entry.get("company"),
    )


async def get_entry(datalake_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM datalake.entries WHERE datalake_id = $1", datalake_id)
    return dict(row) if row is not None else None


# 필터 화이트리스트 (인젝션 차단 — 고정 컬럼명만 동적 WHERE에 허용)
# company 포함 — idx_datalake_company 활용(멀티테넌트 필터, D-174)
_FILTERABLE = ("modality", "function", "site", "source", "vid", "company")


async def list_entries(**filters: Any) -> list[dict[str, Any]]:
    """필터(modality/function/site/source/vid/company) AND 조합. 미지정 필터는 무시."""
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


async def replace_columns(datalake_id: str, columns: list[dict[str, Any]]) -> None:
    """columns 멱등 full-sync — DELETE(id) → re-INSERT. 재적재 시 stale 컬럼 제거 포함
    (columns판 full-record-replace, D-172 정합). constraints 미접촉(D-167; FK가
    entries 참조라 columns 삭제 무영향). 단일 트랜잭션. 호출 순서: upsert_entry 뒤.

    DL-3.5 A (D-193, forward 캡처): ordinal = 입력 리스트 index(=헤더 물리 순서). 호출자(build_record·
    register 헤더 실측)가 이미 소스 순서로 준 리스트를 그대로 enumerate — **재정렬·재계산 0**(group
    행 위치도 빌드 산출 순서 그대로). backfill 과 동일 순서 → finalize(NOT NULL+UNIQUE) 후에도
    register/재적재가 ordinal 공급 → fail-loud 아님. DELETE→re-INSERT(단일 트랜잭션)라 ordinal 재부여
    시 UNIQUE(datalake_id, ordinal) 전이 위반 0."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM datalake.columns WHERE datalake_id = $1", datalake_id)
            for ordinal, c in enumerate(columns):
                gd = c.get("group_desc")
                await conn.execute(
                    "INSERT INTO datalake.columns "
                    "(datalake_id, name, dtype, column_kind, group_desc, ordinal) "
                    "VALUES ($1,$2,$3,$4,$5::jsonb,$6)",
                    datalake_id, c["name"], c.get("dtype"),
                    c.get("column_kind", "scalar"),
                    json.dumps(gd) if gd is not None else None,
                    ordinal,
                )


async def get_columns(datalake_id: str) -> list[dict[str, Any]]:
    # DL-3.5 A (D-193/194): ORDER BY ordinal — 소스 헤더 물리 순서 보존
    # (구 ORDER BY name 의 ASCII 사전정렬 결함 해소: L1_cnc 1ST<2ND<…<10TH).
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM datalake.columns WHERE datalake_id = $1 ORDER BY ordinal", datalake_id)
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        if d.get("group_desc") is not None:
            d["group_desc"] = json.loads(d["group_desc"])
        out.append(d)
    return out


# ── constraints (D-171: column_name / constraint_spec) ──────────────────
async def insert_constraint(datalake_id: str, column_name: str,
                            constraint_spec: dict,
                            approved_by: str | None = None) -> None:
    """제약 = 유저 승인값(D-167). prefill 제안 소스이지 잠금 아님.
    감사(D-179): 동일 트랜잭션에서 기존 행 유무로 action(create/update) 선판별 →
    upsert + constraints_history append. 이력은 앱 레벨(트리거 금지).
    불변식: constraints 의 모든 쓰기 경로는 동일 트랜잭션 history append 의무."""
    pool = await get_pool()
    spec_json = json.dumps(constraint_spec)
    async with pool.acquire() as conn:
        async with conn.transaction():
            exists = await conn.fetchval(
                "SELECT 1 FROM datalake.constraints "
                "WHERE datalake_id=$1 AND column_name=$2", datalake_id, column_name)
            action = "update" if exists else "create"
            await conn.execute(
                """
                INSERT INTO datalake.constraints
                    (datalake_id, column_name, constraint_spec, approved_by)
                VALUES ($1,$2,$3::jsonb,$4)
                ON CONFLICT (datalake_id, column_name) DO UPDATE SET
                    constraint_spec=EXCLUDED.constraint_spec,
                    approved_by=EXCLUDED.approved_by, approved_at=now()
                """,
                datalake_id, column_name, spec_json, approved_by)
            await conn.execute(
                """
                INSERT INTO datalake.constraints_history
                    (datalake_id, column_name, constraint_spec, approved_by, action)
                VALUES ($1,$2,$3::jsonb,$4,$5)
                """,
                datalake_id, column_name, spec_json, approved_by, action)


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


async def delete_constraint(datalake_id: str, column_name: str,
                            approved_by: str | None = None) -> bool:
    """단건 제약 삭제 — "빈칸으로 영속 업데이트" 경로 (D-191).
    감사(D-179 불변식): 동일 트랜잭션에서 삭제 전 spec 을 constraints_history 에
    action='delete' 로 append (delete_entry 와 동일 패턴 — 이전값 보존).
    approved_by = 삭제 수행 주체. 행 부재 시 False (삭제 0, history 0)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT constraint_spec FROM datalake.constraints "
                "WHERE datalake_id=$1 AND column_name=$2", datalake_id, column_name)
            if row is None:
                return False
            await conn.execute(
                """
                INSERT INTO datalake.constraints_history
                    (datalake_id, column_name, constraint_spec, approved_by, action)
                VALUES ($1,$2,$3::jsonb,$4,'delete')
                """,
                datalake_id, column_name, row["constraint_spec"], approved_by)
            await conn.execute(
                "DELETE FROM datalake.constraints "
                "WHERE datalake_id=$1 AND column_name=$2", datalake_id, column_name)
    return True


# ── delete (명시 삭제 — CASCADE 미채택, §1-5 FK verbatim 유지) ──────────
async def delete_entry(datalake_id: str) -> None:
    """자식(constraints→columns) 명시 삭제 후 부모 삭제(단일 트랜잭션).
    CASCADE 미채택: §1-5 FK를 verbatim 유지하고 연쇄삭제를 코드에서 명시적으로
    드러낸다(anti-silent-conversion).
    감사(D-179): 삭제되는 각 constraints 행을 constraints_history에 action='delete'로
    append(행 0개면 append 0). 동일 트랜잭션."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            doomed = await conn.fetch(
                "SELECT column_name, constraint_spec, approved_by "
                "FROM datalake.constraints WHERE datalake_id = $1", datalake_id)
            for r in doomed:
                await conn.execute(
                    """
                    INSERT INTO datalake.constraints_history
                        (datalake_id, column_name, constraint_spec, approved_by, action)
                    VALUES ($1,$2,$3::jsonb,$4,'delete')
                    """,
                    datalake_id, r["column_name"], r["constraint_spec"], r["approved_by"])
            await conn.execute(
                "DELETE FROM datalake.constraints WHERE datalake_id = $1", datalake_id)
            await conn.execute(
                "DELETE FROM datalake.columns WHERE datalake_id = $1", datalake_id)
            await conn.execute(
                "DELETE FROM datalake.entries WHERE datalake_id = $1", datalake_id)
