#!/usr/bin/env python3
"""
tools/datalake_ordinal_backfill.py — DL-3.5 A: datalake.columns.ordinal backfill (D-193/194).

배경: get_columns 가 ORDER BY name(ASCII 사전정렬) → L1_cnc '1ST<2ND<…<10TH' 같은 소스 헤더
물리 순서가 '10TH,1ST,2ND…' 로 뒤집히는 anti-silent 결함(DL-3 이월). columns.ordinal(소스 헤더
물리 순서) 를 채워 get_columns ORDER BY ordinal 로 순서 복원.

시맨틱 (D-194):
- 소스 = 원본 파일 헤더 재파싱, 단 ingest 기존 헤더→컬럼 구성 경로(build_record) 그대로 재사용.
  ordinal = 그 산출 정렬 리스트(rec['columns'])의 index(0,1,2…). UPDATE 는 (datalake_id, name) 매칭.
- __dupN/.N/__unnamed = 소스 헤더 물리 위치 그대로(재정렬·병합·드롭 0 — 상류 산물 존중).
- group(waveform/image_set): ordinal = 저장 행(scalar+group) 기준 위치(build_record 가 group 을
  scalar 뒤에 배치 → 후행 연속 가정). 비연속 group = fail-loud(현 32셋 사례 부재·범위 밖 안전망).
- fail-loud: 재파싱 name-set ≠ DB name-set(해당 entry) → 부분 UPDATE 금지·즉시 실패(헤더 드리프트 표면화).
- 멱등: 재실행 = 동일 ordinal(결정론 헤더 + _uniquify_headers).

finalize (backfill 이후, 멱등 가드):
- 전수 채움 검증(NULL 0) → ALTER ordinal SET NOT NULL(NULL 잔존 시 실패=미채움 검출)
  → UNIQUE(datalake_id, ordinal)(pg_constraint IF NOT EXISTS 가드 — entry 내 ordinal 중복 차단).

모드:
  --dry-run (기본) : manifest 재파싱 → name-set 검증 + 계획 출력. DB write 0.
  --execute        : 검증 통과 시 라이브 UPDATE + finalize(단일 트랜잭션). 라이브 = Phase B(명선 수행).

불변식: datalake.columns.ordinal 만 write(entries/constraints/history 미접촉). 부분 적재 금지.
접속: backend/db.py 와 동일(PG* env). 시크릿/host/port 미출력.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))                       # tools/ (datalake_ingest)
sys.path.insert(0, str(_HERE.parent / "backend"))    # backend/ (catalog, db)

# UNIQUE 제약 (멱등 가드 — PG 는 ADD CONSTRAINT IF NOT EXISTS 미지원 → pg_constraint 확인)
_UNIQ_NAME = "datalake_columns_id_ordinal_uniq"
_FINALIZE_UNIQUE = f"""
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = '{_UNIQ_NAME}'
      AND conrelid = 'datalake.columns'::regclass
  ) THEN
    ALTER TABLE datalake.columns
      ADD CONSTRAINT {_UNIQ_NAME} UNIQUE (datalake_id, ordinal);
  END IF;
END $$;
"""


# ── 순수 로직 (DB 불요 — 단위 테스트 대상) ────────────────────────────────
def compute_ordinal_map(records: list[dict]) -> dict[str, list[str]]:
    """build_record 산출 → {datalake_id: [name0, name1, …]} (소스 헤더 물리 순서).
    ordinal = 리스트 index. 컬럼 0개(경로 없음 등)는 제외."""
    return {r["datalake_id"]: [c["name"] for c in r["columns"]]
            for r in records if r.get("columns")}


def check_group_contiguity(records: list[dict]) -> list[tuple[str, str]]:
    """waveform group 의 numeric 블록이 후행 연속인지(_group_trailing) 검증.
    비연속이면 ordinal=index 가 물리순서와 불일치 → 위반 반환(fail-loud 대상).
    image_set 은 단일 그룹 행(위치 개념 무관) → 검사 제외. 현 32셋은 전부 후행 연속."""
    viol: list[tuple[str, str]] = []
    for r in records:
        is_wav = any(c.get("column_kind") == "group"
                     and (c.get("group_desc") or {}).get("kind") == "waveform"
                     for c in r.get("columns", []))
        if is_wav and r.get("_group_trailing") is False:
            viol.append((r["datalake_id"],
                         "비연속 group(numeric 블록 후행 연속 아님) — ordinal 물리순서 불일치"))
    return viol


def diff_name_sets(ordinal_map: dict[str, list[str]],
                   db_cols: dict[str, list[str]]) -> list[tuple[str, str]]:
    """DB 의 각 entry name-set 과 재파싱 name-set 대조(해당 entry). 불일치 = 헤더 드리프트.
    DB entry 가 재파싱 산출에 없어도 불일치(ordinal 부여 불가)."""
    mism: list[tuple[str, str]] = []
    for did, dbnames in db_cols.items():
        src = ordinal_map.get(did)
        if src is None:
            mism.append((did, "manifest 재파싱 산출 없음(entry 부재/소스 없음) — ordinal 불가"))
            continue
        s_src, s_db = set(src), set(dbnames)
        if s_src != s_db:
            mism.append((did, f"name-set 불일치: src∖db={sorted(s_src - s_db)[:5]} · "
                              f"db∖src={sorted(s_db - s_src)[:5]}"))
    return mism


# ── DB 경로 (conn 또는 pool 수용 — 둘 다 execute/fetch/fetchval) ───────────
async def fetch_db_cols(db) -> dict[str, list[str]]:
    rows = await db.fetch("SELECT datalake_id, name FROM datalake.columns")
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["datalake_id"], []).append(r["name"])
    return out


async def apply_ordinals(db, ordinal_map: dict[str, list[str]]) -> int:
    """(datalake_id, name) 매칭으로 ordinal=index UPDATE. 반환=영향 행수.
    멱등(동일 입력=동일 ordinal). 매칭 행 없는 (manifest-only) entry 는 0행."""
    updated = 0
    for did, names in ordinal_map.items():
        for idx, name in enumerate(names):
            res = await db.execute(
                "UPDATE datalake.columns SET ordinal=$1 WHERE datalake_id=$2 AND name=$3",
                idx, did, name)
            updated += int(res.split()[-1])   # "UPDATE N"
    return updated


async def finalize_ordinal_constraints(db) -> None:
    """전수 채움 검증(NULL 0, fail-loud) → SET NOT NULL → UNIQUE(datalake_id, ordinal).
    멱등(SET NOT NULL 재적용=무해 · UNIQUE pg_constraint 가드). NULL 잔존 시 차단."""
    null_n = await db.fetchval("SELECT count(*) FROM datalake.columns WHERE ordinal IS NULL")
    if null_n:
        raise RuntimeError(f"finalize 차단: ordinal NULL {null_n}행 잔존 — 전수 채움 실패(fail-loud)")
    await db.execute("ALTER TABLE datalake.columns ALTER COLUMN ordinal SET NOT NULL")
    await db.execute(_FINALIZE_UNIQUE)


async def verify_backfill(db) -> dict[str, int]:
    return {
        "null":    await db.fetchval("SELECT count(*) FROM datalake.columns WHERE ordinal IS NULL"),
        "cols":    await db.fetchval("SELECT count(*) FROM datalake.columns"),
        "entries": await db.fetchval("SELECT count(DISTINCT datalake_id) FROM datalake.columns"),
    }


# ── CLI 오케스트레이션 (라이브 = Phase B, 명선 수행) ──────────────────────
async def run(execute: bool) -> int:
    import datalake_ingest as di
    datasets, _excluded = di.load_manifest()
    data_root = di.DEFAULT_DATA_ROOT
    if not data_root.exists():
        sys.exit(f"ABORT: 데이터 루트 없음: {data_root} — backfill 은 소스 헤더 재파싱 필요(D-194).")
    records = [di.build_record(ds, data_root) for ds in datasets]
    ordinal_map = compute_ordinal_map(records)

    viol = check_group_contiguity(records)
    if viol:
        print("ABORT: 비연속 group 검출 (ordinal 물리순서 가정 위반, D-194):", file=sys.stderr)
        for did, m in viol:
            print(f"  - {did}: {m}", file=sys.stderr)
        sys.exit(2)

    import catalog
    import db
    await catalog.run_migration()                    # ordinal 컬럼 보장(멱등 ALTER)
    pool = await db.get_pool()
    try:
        db_cols = await fetch_db_cols(pool)
        mism = diff_name_sets(ordinal_map, db_cols)
        if mism:
            print("ABORT: name-set 불일치 — 부분 UPDATE 금지(헤더 드리프트 표면화, D-194):",
                  file=sys.stderr)
            for did, m in mism:
                print(f"  - {did}: {m}", file=sys.stderr)
            sys.exit(3)

        target_rows = sum(len(v) for v in db_cols.values())
        print(f"[plan] entries={len(db_cols)} · columns={target_rows} · "
              f"name-set 매칭 OK · 비연속 group 0")
        if not execute:
            print("DRY-RUN — DB write 0. (--execute 로 라이브 UPDATE + finalize)")
            return 0

        async with pool.acquire() as conn:
            async with conn.transaction():
                updated = await apply_ordinals(conn, ordinal_map)
                await finalize_ordinal_constraints(conn)
        stats = await verify_backfill(pool)
        ok = stats["null"] == 0 and stats["cols"] == target_rows
        print(f"[execute] ordinal UPDATE {updated}행 · NULL잔존={stats['null']} · "
              f"NOT NULL+UNIQUE 적용 · entries={stats['entries']} cols={stats['cols']} "
              f"[{'OK' if ok else '‼ 검증 실패'}]")
        if not ok:
            sys.exit("ABORT: 적재 후 검증 실패(NULL 잔존 또는 행수 불일치).")
        return 0
    finally:
        await db.close_pool()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="DL-3.5 A datalake.columns.ordinal backfill (D-193/194, dry-run 기본)")
    ap.add_argument("--dry-run", action="store_true",
                    help="재파싱 + name-set 검증 + 계획 출력 (기본, DB write 0)")
    ap.add_argument("--execute", action="store_true",
                    help="라이브 UPDATE + finalize (Phase B — fresh dump 선행 후 명선 수행)")
    args = ap.parse_args(argv)
    return asyncio.run(run(execute=args.execute))


if __name__ == "__main__":
    raise SystemExit(main())
