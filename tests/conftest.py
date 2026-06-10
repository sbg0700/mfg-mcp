"""
tests/conftest.py — throwaway PG 하니스 + 하드 격리 가드 (DL-2.5, D-182).

설계:
- session fixture 가 postgres:16 컨테이너를 127.0.0.1:55432/dl_test 로 기동/정리.
- ★ 하드 가드(E3 교훈): 테스트 DSN = 코드 고정 127.0.0.1:55432/dl_test 뿐.
  ambient PG*(라이브 manufacturing@5432) env 를 '읽지 않고' throwaway 값으로 강제 override.
  import 시점 assert(PGPORT==55432 등) — 위반 경로가 생기면 컬렉션 전체 abort(라이브 오접촉 차단).
- docker 호출은 subprocess env 로 DOCKER_HOST 를 명시(셸 상태 비의존) — rootless 소켓 고정.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import pytest_asyncio

# ── 1. 하드 격리 가드: 라이브 PG* 를 throwaway 로 강제 덮어쓰기 (E3) ──────────
#    ambient(라이브 manufacturing@5432) 값을 '읽지 않는다' = 무조건 override.
_TEST_DB = {
    "PGHOST": "127.0.0.1",
    "PGPORT": "55432",
    "PGUSER": "postgres",
    "PGPASSWORD": "test",
    "PGDATABASE": "dl_test",
}
os.environ.update(_TEST_DB)
# 트립와이어 — 55432/127.0.0.1/dl_test 아닌 어떤 값도 즉시 abort(라이브 오접촉 방지).
assert os.environ["PGPORT"] == "55432", "TEST GUARD 위반: PGPORT != 55432 (라이브 오접촉 차단)"
assert os.environ["PGHOST"] == "127.0.0.1", "TEST GUARD 위반: PGHOST != 127.0.0.1"
assert os.environ["PGDATABASE"] == "dl_test", "TEST GUARD 위반: PGDATABASE != dl_test"

# ── 2. import 경로: backend/(catalog, db) + tools/(datalake_ingest) ──────────
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "backend"))
sys.path.insert(0, str(_REPO / "tools"))

# ── 3. docker (rootless 소켓 명시 — DOCKER_HOST env 가 죽은 경로일 수 있음) ──
_DOCKER_ENV = {**os.environ, "DOCKER_HOST": "unix:///run/user/1002/docker.sock"}
_CONTAINER = "dl_test_pg"
_DSN = dict(host="127.0.0.1", port=55432, user="postgres",
            password="test", database="dl_test")


def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], env=_DOCKER_ENV,
                          capture_output=True, text=True, check=check)


async def _ping() -> None:
    import asyncpg
    conn = await asyncpg.connect(**_DSN)
    await conn.close()


def _wait_ready(timeout: int = 60) -> None:
    end = time.monotonic() + timeout
    while True:
        try:
            asyncio.run(_ping())
            return
        except Exception as e:  # noqa: BLE001
            if time.monotonic() >= end:
                raise RuntimeError(f"throwaway PG 준비 실패({timeout}s): {type(e).__name__}")
            time.sleep(1)


@pytest.fixture(scope="session")
def pg_container():
    """postgres:16 throwaway 컨테이너 — 127.0.0.1:55432/dl_test. 세션 1회 기동/정리."""
    _docker("rm", "-f", _CONTAINER, check=False)            # 이전 잔재 정리
    _docker("run", "--rm", "-d", "--name", _CONTAINER,
            "-p", "127.0.0.1:55432:5432",
            "-e", "POSTGRES_PASSWORD=test",
            "-e", "POSTGRES_DB=dl_test",
            "postgres:16")
    try:
        _wait_ready()
        yield _DSN
    finally:
        _docker("rm", "-f", _CONTAINER, check=False)


@pytest_asyncio.fixture
async def cat(pg_container):
    """마이그레이션된 깨끗한 datalake 스키마 + catalog 모듈 반환.
    매 테스트: run_migration(멱등) → datalake 전 테이블 TRUNCATE → 테스트 후 풀 정리."""
    import catalog
    import db as dbmod
    await catalog.run_migration()
    pool = await dbmod.get_pool()
    rows = await pool.fetch("SELECT tablename FROM pg_tables WHERE schemaname='datalake'")
    names = [f"datalake.{r['tablename']}" for r in rows]
    if names:
        await pool.execute("TRUNCATE " + ", ".join(names) + " RESTART IDENTITY CASCADE")
    try:
        yield catalog
    finally:
        await dbmod.close_pool()
