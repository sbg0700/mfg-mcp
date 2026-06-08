"""
backend/db.py — DL-1 asyncpg 연결 풀 (lazy / guarded).

설계 (DL-1, D-160/D-164):
- 풀은 첫 사용 시점에만 생성한다(lazy). import·부팅 시 DB 접속 0 →
  Sprint-1 in-memory 흐름은 catalog DB가 죽어도 부팅된다(non-regression 불변식).
- 접속 자격은 libpq 표준 환경변수(PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE)에서만
  읽는다 — host 하드코딩 금지. (.env는 병갑 관리, 코드는 env만 참조.)
"""
from __future__ import annotations

import asyncpg

# 프로세스 전역 풀 (session_store._SESSIONS 패턴 — 같은 프로세스 내 공유)
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """전역 풀 반환(없으면 생성). 인자 없는 create_pool → libpq PG* env로 접속."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(min_size=1, max_size=5)
    return _pool


async def close_pool() -> None:
    """풀 graceful 정리. 미생성 상태면 무동작."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
