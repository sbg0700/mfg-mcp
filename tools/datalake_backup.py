#!/usr/bin/env python3
"""
tools/datalake_backup.py — datalake 스코프 논리 백업/복원 (python·asyncpg, D-178).

배경(D-178): host에 pg_dump/psql 미설치 + mfg-postgres가 byeonggab89 rootless docker
네임스페이스라 `docker exec` 영구 불가(STEP A0/C 실측) → datalake 4테이블(entries/
columns/constraints/constraints_history) 전건을 owner=myeongsun 권한으로 TCP 논리
덤프한다. PROTOCOL §3 "대량 ingest/변경 전 스냅샷"의 보호점에서 실행(DL-2 Phase 2,
DL-3c 선결 등). constraints_history(D-179)는 DL-2.5에서 추가 — DL-3c부터 덤프 포함.

접속: backend/db.py 와 동일 libpq PG* env(인자 없는 asyncpg.connect). 시크릿 값 출력/Read 0.

모드:
  --dump (기본)   : 4테이블 전건 SELECT → 타임스탬프 JSON 파일. 읽기 전용(DB write 0).
                    JSONB(group_desc/constraint_spec)=dict 무손실 보존, TIMESTAMPTZ=ISO8601.
                    덤프행수 == 라이브행수 self-check(불일치 시 abort).
  --verify FILE   : 덤프 파일 행수 ↔ 현재 라이브 행수 대조 출력. 읽기 전용.
  --restore FILE  : JSON → datalake.* 복원(FK 순서, 단일 트랜잭션 전건 교체). datalake 스코프만 write.

불변식: datalake.* 밖 미접촉(권한 경계). 덤프=읽기전용. 복원=전건 교체(멱등) +
constraints_history는 IDENTITY 보존(OVERRIDING SYSTEM VALUE + 시퀀스 재설정). 전테이블 포함.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import asyncpg

DEFAULT_BACKUP_DIR = Path("~/FINAL/0_BGS/backups").expanduser()

# FK 부모→자식 순 (삽입 순서). constraints_history는 FK 없음(D-179 의도) — 맨 뒤.
TABLES = ("entries", "columns", "constraints", "constraints_history")
ORDER_BY = {                                              # 결정론적 덤프(재현 가능 정렬)
    "entries":             "registered_at, datalake_id",
    "columns":             "datalake_id, name",
    "constraints":         "datalake_id, column_name",
    "constraints_history": "history_id",
}
# history_id = GENERATED ALWAYS AS IDENTITY → 복원 시 명시값 삽입에 OVERRIDING 필요
IDENTITY_TABLES = {"constraints_history": "history_id"}
TS_COLS = {"registered_at", "approved_at"}                # TIMESTAMPTZ — 복원 시 ISO→datetime


def _json_default(o: object) -> str:
    """JSON 비직렬화 타입 처리 — TIMESTAMPTZ(datetime) → ISO8601."""
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"직렬화 불가 타입: {type(o).__name__}")


async def _connect() -> asyncpg.Connection:
    """libpq PG* env 로 접속(인자 0). JSONB ↔ dict 코덱 등록(무손실 보존).
    연결 실패 시 클래스명만 — host/port 노출 방지(시크릿 정책)."""
    try:
        conn = await asyncpg.connect()
    except Exception as e:                                # noqa: BLE001 (메시지 미출력)
        raise SystemExit(
            f"ABORT: DB 연결 실패({type(e).__name__}) — PG* env 확인. "
            "메시지 미출력(host/port 노출 방지).")
    await conn.set_type_codec(
        "jsonb", schema="pg_catalog", encoder=json.dumps, decoder=json.loads)
    return conn


async def _col_order(conn: asyncpg.Connection, t: str) -> list[str]:
    """빈 테이블이라 첫 행이 없을 때 컬럼 순서를 information_schema 에서 취득."""
    rows = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='datalake' AND table_name=$1 ORDER BY ordinal_position", t)
    return [r["column_name"] for r in rows]


async def dump(path: Path | None) -> None:
    """3테이블 전건 → JSON. 읽기 전용. 덤프행수 == 라이브행수 self-check."""
    conn = await _connect()
    try:
        out: dict = {
            "meta": {
                "database":  await conn.fetchval("SELECT current_database()"),
                "schema":    "datalake",
                "dumped_at": (await conn.fetchval("SELECT now()")).isoformat(),
                "purpose":   "datalake logical snapshot (D-178)",
            },
            "tables": {},
        }
        for t in TABLES:
            rows = await conn.fetch(f"SELECT * FROM datalake.{t} ORDER BY {ORDER_BY[t]}")
            order = list(rows[0].keys()) if rows else await _col_order(conn, t)
            out["tables"][t] = {"order": order, "rows": [dict(r) for r in rows]}
        live = {t: await conn.fetchval(f"SELECT count(*) FROM datalake.{t}") for t in TABLES}
    finally:
        await conn.close()

    if path is None:
        ts = out["meta"]["dumped_at"].replace(":", "").replace("-", "")[:15]
        DEFAULT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        path = DEFAULT_BACKUP_DIR / f"datalake_{out['meta']['database']}_{ts}.json"
    path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8")

    print(f"논리 백업 완료: {path} ({path.stat().st_size} bytes)")
    print(f"  dumped_at={out['meta']['dumped_at']}  db={out['meta']['database']}  schema=datalake")
    ok = True
    for t in TABLES:
        dn, ln = len(out["tables"][t]["rows"]), live[t]
        ok = ok and (dn == ln)
        print(f"  datalake.{t}: dump {dn} rows == live {ln}  [{'OK' if dn == ln else '‼ 불일치'}]")
    if not ok:
        sys.exit("ABORT: 덤프 행수 != 라이브 행수 — 백업 불완전(재시도).")
    print("  self-check PASS — 덤프=라이브 전건(누락 0).")


async def verify(path: Path) -> None:
    """덤프 파일 행수 ↔ 현재 라이브 행수 대조. 읽기 전용.
    Phase 2 적재 후 '덤프 후 row count vs 적재 후 row count' 대조용."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    conn = await _connect()
    try:
        print(f"검증 대상: {path}")
        print(f"  dumped_at={doc['meta'].get('dumped_at')}  db={doc['meta'].get('database')}")
        for t in TABLES:
            if t not in doc["tables"]:                     # DL-2 시기 3테이블 덤프 호환
                print(f"  datalake.{t}: 덤프에 없음(구버전 3테이블 덤프) — 대조 생략")
                continue
            dn = len(doc["tables"][t]["rows"])
            ln = await conn.fetchval(f"SELECT count(*) FROM datalake.{t}")
            diff = "동일" if dn == ln else f"차이 {ln - dn:+d}"
            print(f"  datalake.{t}: dump {dn} ↔ live {ln}  [{diff}]")
    finally:
        await conn.close()


async def restore(path: Path) -> None:
    """JSON → datalake.* 전건 복원. 단일 트랜잭션: 자식→부모 DELETE, 부모→자식 INSERT.
    datalake.* 한정 write(권한 경계). 멱등(전건 교체)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    conn = await _connect()
    try:
        present = [t for t in TABLES if t in doc["tables"]]   # DL-2 시기 3테이블 덤프 호환
        for t in TABLES:
            if t not in doc["tables"]:
                print(f"  datalake.{t}: 덤프에 없음(구버전 3테이블 덤프) — 복원 생략(현재값 유지)")
        async with conn.transaction():
            for t in reversed(present):                    # 자식→부모 DELETE
                await conn.execute(f"DELETE FROM datalake.{t}")
            for t in present:                              # 부모→자식 INSERT
                tbl = doc["tables"][t]
                order, rows = tbl["order"], tbl["rows"]
                cols = ", ".join(order)
                ph = ", ".join(f"${i + 1}" for i in range(len(order)))
                over = " OVERRIDING SYSTEM VALUE" if t in IDENTITY_TABLES else ""
                sql = f"INSERT INTO datalake.{t} ({cols}){over} VALUES ({ph})"
                for r in rows:
                    vals = [
                        datetime.fromisoformat(r[c])
                        if c in TS_COLS and isinstance(r.get(c), str) else r.get(c)
                        for c in order
                    ]
                    await conn.execute(sql, *vals)
            for t in present:                              # IDENTITY 시퀀스 재설정(다음 append 충돌 방지)
                if t in IDENTITY_TABLES:
                    c = IDENTITY_TABLES[t]
                    await conn.execute(
                        f"SELECT setval(pg_get_serial_sequence('datalake.{t}', '{c}'), "
                        f"COALESCE(MAX({c}), 0) + 1, false) FROM datalake.{t}")
        for t in present:
            n = await conn.fetchval(f"SELECT count(*) FROM datalake.{t}")
            print(f"  복원 datalake.{t}: {n} rows")
        print("복원 완료 — 단일 트랜잭션, datalake.* 전건 교체(멱등).")
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DL-2 datalake 논리 백업/복원 (D-178)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dump", action="store_true", help="3테이블 전건 JSON 덤프 (기본, 읽기전용)")
    g.add_argument("--verify", metavar="FILE", help="덤프 파일 ↔ 라이브 행수 대조 (읽기전용)")
    g.add_argument("--restore", metavar="FILE", help="JSON → datalake.* 복원 (datalake write)")
    ap.add_argument("-o", "--out", help="덤프 출력 경로(미지정 시 ~/FINAL/0_BGS/backups/)")
    args = ap.parse_args(argv)

    if args.verify:
        asyncio.run(verify(Path(args.verify).expanduser()))
    elif args.restore:
        asyncio.run(restore(Path(args.restore).expanduser()))
    else:                                                  # 기본 = dump (읽기전용)
        asyncio.run(dump(Path(args.out).expanduser() if args.out else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
