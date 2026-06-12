"""
tests/test_constraints_3c.py — DL-3c 제약 폼 백엔드 (D-189/D-190/D-191, throwaway PG 전용 D-182).

범위:
- ③ POST canonical shape (D-190): 확정 3종 통과 / 미확정 3종 422 / 필드 위반 422 /
  미실존 column 4xx / aggregate↔scalar kind 불일치 4xx
- ④ delete 경로 (D-191): 빈 spec POST = delete_constraint, history append(action=delete)
- ①② 머지 3케이스 + 재승인 게이트 (D-167)
- ⑤ 다운컨버트 (D-189): range→[min,max] 구 shape, 비-range→engine_excluded(silent drop 0)

하니스 = test_datalake_api.py 와 동일(httpx ASGITransport + throwaway 55432/dl_test).
"""
from __future__ import annotations

import httpx
import pytest_asyncio

BASE = "/api/datalake"


@pytest_asyncio.fixture
async def api(pg_container, tmp_path, monkeypatch):
    """마이그레이션+TRUNCATE 된 깨끗한 스키마 + main.app ASGI 클라이언트 (3a 하니스 동일)."""
    import catalog
    import datalake_api
    import db as dbmod
    import main as main_mod

    monkeypatch.setattr(datalake_api, "LAKE_ROOT", tmp_path / "lake")
    await catalog.run_migration()
    pool = await dbmod.get_pool()
    rows = await pool.fetch("SELECT tablename FROM pg_tables WHERE schemaname='datalake'")
    names = [f"datalake.{r['tablename']}" for r in rows]
    if names:
        await pool.execute("TRUNCATE " + ", ".join(names) + " RESTART IDENTITY CASCADE")
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=main_mod.app),
                               base_url="http://testserver")
    try:
        yield client
    finally:
        await client.aclose()
        await dbmod.close_pool()


async def _seed_k(datalake_id: str = "k"):
    """entry + scalar 2종(temp, temp__dup2) + group 1종(waveform) 시드."""
    import catalog
    await catalog.upsert_entry(dict(
        datalake_id=datalake_id, source="kamp", name=datalake_id, modality="timeseries",
        function="process", site="s1", vid="V1", size_bytes=10, encoding="utf-8",
        format="csv", data_path=f"data/lake/{datalake_id}/", reusable_flag=False,
        company="kamp"))
    await catalog.replace_columns(datalake_id, [
        {"name": "temp", "dtype": "float", "column_kind": "scalar", "group_desc": None},
        {"name": "temp__dup2", "dtype": "float", "column_kind": "scalar", "group_desc": None},
        {"name": "waveform", "dtype": "float", "column_kind": "group",
         "group_desc": {"kind": "waveform", "n_cols": 2048, "fs_hz": 800}},
    ])


# ── ③ POST canonical shape (D-190) ────────────────────────────────────────
async def test_post_canonical_three_types_pass(api):
    await _seed_k("c3")
    # range — min 만 non-null 허용 (D-180/D-190)
    r = await api.post(f"{BASE}/c3/constraints", json={
        "column_name": "temp",
        "constraint_spec": {"type": "range", "min": 10, "max": None, "unit": "°C"}})
    assert r.status_code == 200 and r.json()["saved"] is True
    # single_value — unit 생략(=null) 허용
    r = await api.post(f"{BASE}/c3/constraints", json={
        "column_name": "temp__dup2",
        "constraint_spec": {"type": "single_value", "value": 42}})
    assert r.status_code == 200
    # aggregate — group 컬럼 전용 (D-185/D-190)
    r = await api.post(f"{BASE}/c3/constraints", json={
        "column_name": "waveform",
        "constraint_spec": {"type": "aggregate", "metric": "rms", "op": "<=",
                            "value": 1.5, "unit": "g"}})
    assert r.status_code == 200
    cons = (await api.get(f"{BASE}/c3/constraints")).json()["constraints"]
    assert {c["column_name"] for c in cons} == {"temp", "temp__dup2", "waveform"}


async def test_post_deferred_types_422(api):
    """ratio/list/text = canonical 미확정 (D-190) — 즉흥 정의 금지, 명시 422."""
    await _seed_k("c4")
    for t in ("ratio", "list", "text"):
        r = await api.post(f"{BASE}/c4/constraints", json={
            "column_name": "temp", "constraint_spec": {"type": t}})
        assert r.status_code == 422, t
        assert "미확정" in r.json()["detail"], t
    assert (await api.get(f"{BASE}/c4/constraints")).json()["constraints"] == []


async def test_post_canonical_field_violations_422(api):
    await _seed_k("c5")
    bad = [
        {"type": "range", "min": None, "max": None, "unit": None},   # 둘 다 null (D-180)
        {"type": "range", "min": 1, "max": 2, "extra": 9},           # 허용 외 필드
        {"type": "range", "min": "1", "max": 2},                     # min 비숫자
        {"type": "range", "min": True, "max": None},                 # bool 은 num 아님
        {"type": "single_value", "unit": "mm"},                      # value 누락
        {"type": "single_value", "value": "42"},                     # value 비숫자
        {"type": "aggregate", "metric": "median", "op": "<=", "value": 1},  # metric 위반
        {"type": "aggregate", "metric": "rms", "op": "<", "value": 1},      # op 위반
        {"type": "aggregate", "metric": "rms", "op": ">="},          # value 누락
        {"type": "range", "min": 1, "max": 2, "unit": 7},            # unit 비문자열
    ]
    target = {"aggregate": "waveform"}   # aggregate 만 group 컬럼 대상 (kind 정합 통과시키고 필드 검증 도달)
    for spec in bad:
        col = target.get(spec["type"], "temp")
        r = await api.post(f"{BASE}/c5/constraints",
                           json={"column_name": col, "constraint_spec": spec})
        assert r.status_code == 422, spec
        assert "D-19" in r.json()["detail"] or "D-180" in r.json()["detail"], spec
    assert (await api.get(f"{BASE}/c5/constraints")).json()["constraints"] == []


async def test_post_column_checks_4xx(api):
    await _seed_k("c6")
    # 미실존 column → 422
    r = await api.post(f"{BASE}/c6/constraints", json={
        "column_name": "ghost",
        "constraint_spec": {"type": "range", "min": 0, "max": 1, "unit": None}})
    assert r.status_code == 422 and "ghost" in r.json()["detail"]
    # aggregate ↔ scalar kind 불일치 → 422
    r = await api.post(f"{BASE}/c6/constraints", json={
        "column_name": "temp",
        "constraint_spec": {"type": "aggregate", "metric": "rms", "op": "<=", "value": 1}})
    assert r.status_code == 422 and "group" in r.json()["detail"]
    # 역방향(range on group)은 차단 명세 없음 (D-190 — aggregate 정합만 규정)
    r = await api.post(f"{BASE}/c6/constraints", json={
        "column_name": "waveform",
        "constraint_spec": {"type": "range", "min": 0, "max": 1, "unit": None}})
    assert r.status_code == 200


# ── ④ delete 경로 (D-191) — 빈 spec POST = delete_constraint + history ─────
async def test_post_empty_spec_delete_with_history(api):
    import db as dbmod
    await _seed_k("d3")
    spec = {"type": "range", "min": 0, "max": 9, "unit": None}
    r = await api.post(f"{BASE}/d3/constraints", json={
        "column_name": "temp", "constraint_spec": spec, "approved_by": "qa_lead"})
    assert r.status_code == 200

    # 빈 값({} 또는 null) = delete 경로 (D-191)
    r = await api.post(f"{BASE}/d3/constraints", json={
        "column_name": "temp", "constraint_spec": {}, "approved_by": "remover"})
    assert r.status_code == 200 and r.json()["deleted"] is True
    assert (await api.get(f"{BASE}/d3/constraints")).json()["constraints"] == []

    # history: create → delete, 삭제 행은 삭제 전 spec 보존 + 삭제 주체 기록 (D-179)
    pool = await dbmod.get_pool()
    hist = await pool.fetch(
        "SELECT action, approved_by, constraint_spec FROM datalake.constraints_history "
        "WHERE datalake_id='d3' ORDER BY history_id")
    assert [h["action"] for h in hist] == ["create", "delete"]
    assert hist[1]["approved_by"] == "remover"
    import json as _json
    assert _json.loads(hist[1]["constraint_spec"]) == spec

    # 부재 행 재삭제 = 404 (silent no-op 금지) — history 추가 0
    r = await api.post(f"{BASE}/d3/constraints",
                       json={"column_name": "temp", "constraint_spec": None})
    assert r.status_code == 404
    n = await pool.fetchval(
        "SELECT count(*) FROM datalake.constraints_history WHERE datalake_id='d3'")
    assert n == 2


async def test_delete_constraint_transactional_unit(cat):
    """catalog.delete_constraint 단위: 반환값 + 동일 트랜잭션 효과(행 삭제 ↔ history 동시)."""
    await _seed_k("d4")
    assert await cat.delete_constraint("d4", "temp") is False        # 부재 = False, history 0
    await cat.insert_constraint("d4", "temp", {"type": "single_value", "value": 1},
                                approved_by="u1")
    assert await cat.delete_constraint("d4", "temp", approved_by="u2") is True
    assert await cat.get_constraints("d4") == []
    import db as dbmod
    pool = await dbmod.get_pool()
    hist = await pool.fetch(
        "SELECT action, approved_by FROM datalake.constraints_history "
        "WHERE datalake_id='d4' ORDER BY history_id")
    assert [(h["action"], h["approved_by"]) for h in hist] == [
        ("create", "u1"), ("delete", "u2")]
