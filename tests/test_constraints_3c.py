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


# ── ①② 머지 3케이스 + 재승인 게이트 (D-167) ──────────────────────────────
def _pf(datalake_id: str, constraints_v2: dict | None) -> dict:
    """모듈 1개짜리 pipeline_full (module_key = '0.0')."""
    m: dict = {"index": 0, "function": "process", "modality": "timeseries",
               "dataset_role": "primary", "datalake_id": datalake_id}
    if constraints_v2 is not None:
        m["constraints_v2"] = constraints_v2
    return {"line_id": "L1", "stages": [
        {"stage_order": 0, "node_id": "n1", "modules": [m]}]}


async def _session(api, pipeline_full: dict) -> str:
    r = await api.post("/api/sessions/create", json={"pipeline_full": pipeline_full})
    assert r.status_code == 200
    return r.json()["session_id"]


async def test_merge_three_cases_unit():
    """순수 함수 단위 — ① 세션 오버라이드 > ② prefill(applied=False 고정) > ③ 빈칸."""
    import datalake_api
    columns = [{"name": "temp"}, {"name": "rpm"}, {"name": "blank_col"}]
    session_specs = {"temp": {"type": "range", "min": 1, "max": 2, "unit": None}}
    prefill = [
        {"column_name": "temp", "constraint_spec": {"type": "range", "min": 0, "max": 9,
                                                    "unit": None},
         "approved_by": "qa", "approved_at": None},
        {"column_name": "rpm", "constraint_spec": {"type": "single_value", "value": 7},
         "approved_by": "qa", "approved_at": None},
    ]
    view = {v["column_name"]: v
            for v in datalake_api.merge_constraint_view(columns, session_specs, prefill)}
    # ① 세션 오버라이드 — prefill 존재해도 세션값 우선
    assert view["temp"]["source"] == "session" and view["temp"]["applied"] is True
    assert view["temp"]["spec"]["min"] == 1
    assert view["temp"]["prefill"]["constraint_spec"]["min"] == 0   # 제안은 병기(은닉 0)
    # ② prefill — spec 미주입(값 주입 0) + applied=False (재승인 게이트)
    assert view["rpm"]["source"] == "prefill" and view["rpm"]["applied"] is False
    assert view["rpm"]["spec"] is None
    assert view["rpm"]["prefill"]["constraint_spec"] == {"type": "single_value", "value": 7}
    # ③ 빈칸
    assert view["blank_col"]["source"] == "blank" and view["blank_col"]["spec"] is None


async def test_merge_endpoint_and_reapproval_gate(api):
    """② 재승인 게이트 — prefill 존재 + 미승인 → 세션 적용 0 (자동 적용 절대 0)."""
    await _seed_k("g1")
    # catalog prefill 1건 존재
    r = await api.post(f"{BASE}/g1/constraints", json={
        "column_name": "temp",
        "constraint_spec": {"type": "range", "min": 5, "max": 50, "unit": None},
        "approved_by": "past_user"})
    assert r.status_code == 200

    # 세션 생성 + 유저가 승인 없이 PUT full (constraints_v2 빈 맵 = 미승인)
    sid = await _session(api, _pf("g1", {}))
    r = await api.put(f"{BASE}/sessions/{sid}/full",
                      json={"pipeline_full": _pf("g1", {})})
    assert r.status_code == 200

    # 세션 적용 0 — prefill 이 세션/엔진 어디에도 자동 주입되지 않음
    sess = (await api.get(f"/api/sessions/{sid}")).json()
    mod = sess["pipeline_full"]["stages"][0]["modules"][0]
    assert mod["constraints"] == {} and mod["constraints_v2"] == {}

    # merge view: source=prefill, applied=False, spec 미주입 — 제안 박스 소스만
    r = await api.get(f"{BASE}/sessions/{sid}/constraint_merge",
                      params={"datalake_id": "g1", "module_key": "0.0"})
    view = {v["column_name"]: v for v in r.json()["merged"]}
    assert view["temp"]["source"] == "prefill" and view["temp"]["applied"] is False
    assert view["temp"]["spec"] is None
    assert view["temp"]["prefill"]["approved_by"] == "past_user"

    # 유저가 승인(프론트) → 세션 저장 경유로만 적용 (= ① 세션 오버라이드로 전환)
    approved = {"temp": {"type": "range", "min": 5, "max": 50, "unit": None}}
    r = await api.put(f"{BASE}/sessions/{sid}/full",
                      json={"pipeline_full": _pf("g1", approved)})
    assert r.status_code == 200
    r = await api.get(f"{BASE}/sessions/{sid}/constraint_merge",
                      params={"datalake_id": "g1", "module_key": "0.0"})
    view = {v["column_name"]: v for v in r.json()["merged"]}
    assert view["temp"]["source"] == "session" and view["temp"]["applied"] is True

    # 데이터셋 변경 시 구 세션값 무효 (datalake_id 불일치 → 빈칸/프리필로 폴백)
    await _seed_k("g2")
    r = await api.get(f"{BASE}/sessions/{sid}/constraint_merge",
                      params={"datalake_id": "g2", "module_key": "0.0"})
    view = {v["column_name"]: v for v in r.json()["merged"]}
    assert view["temp"]["source"] == "blank"


# ── ⑤ 다운컨버트 (D-189) ──────────────────────────────────────────────────
async def test_downconvert_unit():
    import datalake_api
    engine, excluded = datalake_api.downconvert_constraints({
        "a": {"type": "range", "min": 10, "max": 90, "unit": "bar"},
        "b": {"type": "range", "min": 10, "max": None, "unit": None},   # 한쪽 null 그대로
        "c": {"type": "aggregate", "metric": "rms", "op": "<=", "value": 1.5, "unit": None},
        "d": {"type": "single_value", "value": 7, "unit": None},
    })
    assert engine == {"a": [10, 90], "b": [10, None]}                   # range 만, 구 shape
    assert excluded == [{"column_name": "c", "type": "aggregate"},
                        {"column_name": "d", "type": "single_value"}]   # silent drop 0
    assert datalake_api.downconvert_constraints(None) == ({}, [])
    assert datalake_api.downconvert_constraints({}) == ({}, [])


async def test_put_full_v2_downconvert_and_engine_shape(api):
    """PUT v2 → 엔진이 읽는 m['constraints'] 에 비-range 0 + engine_excluded 메타."""
    await _seed_k("v1")
    sid = await _session(api, _pf("v1", None))
    cmap = {
        "temp": {"type": "range", "min": 10, "max": 90, "unit": "°C"},
        "temp__dup2": {"type": "single_value", "value": 42},
        "waveform": {"type": "aggregate", "metric": "rms", "op": "<=", "value": 1.5,
                     "unit": "g"},
    }
    r = await api.put(f"{BASE}/sessions/{sid}/full",
                      json={"pipeline_full": _pf("v1", cmap)})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready" and body["modules_with_constraints"] == 1
    assert body["engine_excluded"] == [
        {"column_name": "temp__dup2", "type": "single_value", "module_key": "0.0"},
        {"column_name": "waveform", "type": "aggregate", "module_key": "0.0"}]

    # 세션 저장 결과: 엔진 입력(constraints) = range 만 구 shape, 비-range 0
    sess = (await api.get(f"/api/sessions/{sid}")).json()
    mod = sess["pipeline_full"]["stages"][0]["modules"][0]
    assert mod["constraints"] == {"temp": [10, 90]}
    assert mod["engine_excluded"] == [
        {"column_name": "temp__dup2", "type": "single_value"},
        {"column_name": "waveform", "type": "aggregate"}]
    assert mod["constraints_v2"] == cmap                # canonical 원본 보존(복원용)


async def test_put_full_v2_validation_and_404(api):
    await _seed_k("v2d")
    # session 부재 → 404
    r = await api.put(f"{BASE}/sessions/ghost/full",
                      json={"pipeline_full": _pf("v2d", {})})
    assert r.status_code == 404
    # canonical 위반 → 422 (세션도 폼 생성 가능값만 — anti-silent)
    sid = await _session(api, _pf("v2d", None))
    r = await api.put(f"{BASE}/sessions/{sid}/full", json={"pipeline_full": _pf(
        "v2d", {"temp": {"type": "range", "min": None, "max": None, "unit": None}})})
    assert r.status_code == 422
    r = await api.put(f"{BASE}/sessions/{sid}/full", json={"pipeline_full": _pf(
        "v2d", {"temp": {"type": "ratio"}})})
    assert r.status_code == 422 and "미확정" in r.json()["detail"]


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
