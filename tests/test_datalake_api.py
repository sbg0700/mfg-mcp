"""
tests/test_datalake_api.py — DL-3a /api/datalake/* 표면 테스트 (D-186/D-187, throwaway PG 전용 D-182).

- 대상 = backend/main.py 의 app (include_router 마운트까지 검증) — httpx ASGITransport.
- LAKE_ROOT 는 monkeypatch 로 tmp_path 대체 — 실 data/lake 접촉 0.
- DB = conftest 의 throwaway 127.0.0.1:55432/dl_test. 라이브 접촉 0.
"""
from __future__ import annotations

import httpx
import pytest_asyncio

BASE = "/api/datalake"


# ── 하니스 ────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def api(pg_container, tmp_path, monkeypatch):
    """마이그레이션+TRUNCATE 된 깨끗한 스키마 + main.app ASGI 클라이언트.
    LAKE_ROOT → tmp_path/lake (실 data/lake 오염 0). 테스트 후 풀 정리(루프 격리)."""
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


def _entry(datalake_id: str, **over) -> dict:
    """완전 레코드(D-172) 시드 헬퍼."""
    e = dict(datalake_id=datalake_id, source="kamp", name=datalake_id,
             modality="timeseries", function="process", site="site_a", vid="V1",
             size_bytes=10, encoding="utf-8", format="csv",
             data_path=f"data/lake/{datalake_id}/", reusable_flag=False, company="kamp")
    e.update(over)
    return e


async def _seed(catalog, *entries):
    for e in entries:
        await catalog.upsert_entry(e)


# ── 7. /list — 3축 AND 필터 (D-166) ─────────────────────────────────────
async def test_list_three_axis_and_filter(api):
    import catalog
    await _seed(catalog,
                _entry("a1", vid="V1", function="process", site="s1"),
                _entry("a2", vid="V1", function="quality", site="s1"),
                _entry("a3", vid="V2", function="process", site="s2"))
    r = await api.get(f"{BASE}/list")
    assert r.status_code == 200
    body = r.json()
    assert {e["datalake_id"] for e in body["entries"]} == {"a1", "a2", "a3"}
    # registered_at ISO 직렬화 (문자열 + 파싱 가능)
    from datetime import datetime
    ra = body["entries"][0]["registered_at"]
    assert isinstance(ra, str) and datetime.fromisoformat(ra)

    r = await api.get(f"{BASE}/list", params={"vid": "V1"})
    assert {e["datalake_id"] for e in r.json()["entries"]} == {"a1", "a2"}
    r = await api.get(f"{BASE}/list", params={"vid": "V1", "function": "process"})
    assert {e["datalake_id"] for e in r.json()["entries"]} == {"a1"}
    r = await api.get(f"{BASE}/list",
                      params={"vid": "V1", "function": "process", "site": "s1"})
    assert {e["datalake_id"] for e in r.json()["entries"]} == {"a1"}
    r = await api.get(f"{BASE}/list", params={"vid": "V2", "function": "quality"})
    assert r.json()["entries"] == []


# ── 9. /{id}/metadata ────────────────────────────────────────────────────
async def test_metadata_200_and_404(api):
    import catalog
    await _seed(catalog, _entry("m1", modality="order", encoding="cp949"))
    r = await api.get(f"{BASE}/m1/metadata")
    assert r.status_code == 200
    body = r.json()
    assert body["datalake_id"] == "m1" and body["modality"] == "order"
    assert isinstance(body["registered_at"], str)
    assert (await api.get(f"{BASE}/ghost/metadata")).status_code == 404


# ── 9b. /{id}/columns — group·__dupN 그대로 노출 (D-90/D-161/D-180) ──────
async def test_columns_group_and_dupn(api):
    import catalog
    await _seed(catalog, _entry("c1"))
    await catalog.replace_columns("c1", [
        {"name": "temp", "dtype": "float", "column_kind": "scalar", "group_desc": None},
        {"name": "temp__dup2", "dtype": "float", "column_kind": "scalar", "group_desc": None},
        {"name": "waveform", "dtype": "float", "column_kind": "group",
         "group_desc": {"kind": "waveform", "n_cols": 2048, "fs_hz": 800}},
    ])
    r = await api.get(f"{BASE}/c1/columns")
    assert r.status_code == 200
    cols = {c["name"]: c for c in r.json()["columns"]}
    assert "temp__dup2" in cols                      # __dupN 드롭·은닉 금지
    assert cols["waveform"]["column_kind"] == "group"
    assert cols["waveform"]["group_desc"]["kind"] == "waveform"
    assert (await api.get(f"{BASE}/ghost/columns")).status_code == 404


# ── 9c·9d. /{id}/constraints GET·POST (D-167/D-179/D-185) ────────────────
async def test_constraints_post_and_get_roundtrip(api):
    import catalog
    import db as dbmod
    await _seed(catalog, _entry("k1"))
    await catalog.replace_columns("k1", [
        {"name": "pressure", "dtype": "float", "column_kind": "scalar", "group_desc": None}])

    spec = {"type": "range", "min": 10, "max": 90, "unit": "bar"}
    r = await api.post(f"{BASE}/k1/constraints",
                       json={"column_name": "pressure", "constraint_spec": spec,
                             "approved_by": "qa_lead"})
    assert r.status_code == 200 and r.json()["saved"] is True

    r = await api.get(f"{BASE}/k1/constraints")
    cons = r.json()["constraints"]
    assert len(cons) == 1
    assert cons[0]["constraint_spec"] == spec
    assert cons[0]["approved_by"] == "qa_lead"        # approved_by 보존

    # history 부수효과 (D-179): create → 재POST 시 update
    r = await api.post(f"{BASE}/k1/constraints",
                       json={"column_name": "pressure",
                             "constraint_spec": {"type": "single_value", "value": 42}})
    assert r.status_code == 200
    pool = await dbmod.get_pool()
    hist = await pool.fetch(
        "SELECT action, approved_by FROM datalake.constraints_history "
        "WHERE datalake_id='k1' ORDER BY history_id")
    assert [h["action"] for h in hist] == ["create", "update"]
    assert hist[1]["approved_by"] == "user"           # approved_by 디폴트 = "user"


async def test_constraints_post_validation_three_steps(api):
    import catalog
    # ① entry 부재 → 404
    r = await api.post(f"{BASE}/ghost/constraints",
                       json={"column_name": "x", "constraint_spec": {"type": "range"}})
    assert r.status_code == 404
    await _seed(catalog, _entry("k2"))
    await catalog.replace_columns("k2", [
        {"name": "rpm", "dtype": "integer", "column_kind": "scalar", "group_desc": None}])
    # ② type ∉ D-185 화이트리스트 → 422 (type 누락 포함)
    r = await api.post(f"{BASE}/k2/constraints",
                       json={"column_name": "rpm", "constraint_spec": {"type": "banana"}})
    assert r.status_code == 422 and "D-185" in r.json()["detail"]
    r = await api.post(f"{BASE}/k2/constraints",
                       json={"column_name": "rpm", "constraint_spec": {"min": 1}})
    assert r.status_code == 422
    # ③ column_name ∉ datalake.columns → 422 (min 명시 — canonical 검증과 독립 도달, D-190)
    r = await api.post(f"{BASE}/k2/constraints",
                       json={"column_name": "ghost_col",
                             "constraint_spec": {"type": "range", "min": 1, "max": None,
                                                 "unit": None}})
    assert r.status_code == 422
    # aggregate 는 화이트리스트 포함 (D-185) — 단 3c부터 column_kind=group 전용 정합
    # 검증이 추가돼(D-190) scalar 컬럼(rpm) 대상은 422 (3a 시점 200 placeholder 갱신).
    r = await api.post(f"{BASE}/k2/constraints",
                       json={"column_name": "rpm",
                             "constraint_spec": {"type": "aggregate", "metric": "rms",
                                                 "op": "<=", "value": 1.5}})
    assert r.status_code == 422 and "group" in r.json()["detail"]


# ── 8. /register — Mode B 한정 (D-186) ──────────────────────────────────
async def test_register_mode_b_tabular(api, tmp_path):
    import datalake_api
    src = tmp_path / "src" / "sensor.csv"
    src.parent.mkdir()
    src.write_text("ts,temp,temp\n1,20.5,21.0\n2,20.7,21.2\n", encoding="utf-8")

    r = await api.post(f"{BASE}/register", json={
        "name": "My Sensor Data", "server_path": str(src), "modality": "timeseries",
        "function_hint": "process", "site": "s9", "vid": "V9", "company": "acme"})
    assert r.status_code == 200
    body = r.json()
    e = body["entry"]
    assert e["datalake_id"] == "my_sensor_data"       # slug(name), [a-z0-9_]
    assert e["source"] == "user_registered"
    assert e["function"] == "process"                  # function_hint → 권위 컬럼 function
    assert e["data_path"] == "data/lake/my_sensor_data/"
    assert body["n_columns"] == 3
    # 복사 실재 (monkeypatch 된 LAKE_ROOT 아래)
    assert (datalake_api.LAKE_ROOT / "my_sensor_data" / "sensor.csv").exists()
    # 헤더 실측 — 중복 헤더는 __dupN 으로 보존 (ingest 단일 구현 재사용 증거)
    cols = (await api.get(f"{BASE}/my_sensor_data/columns")).json()["columns"]
    assert {c["name"] for c in cols} == {"ts", "temp", "temp__dup2"}

    # 충돌 409 — 자동 변형 금지 (anti-silent)
    r = await api.post(f"{BASE}/register", json={
        "name": "My Sensor Data", "server_path": str(src), "modality": "timeseries"})
    assert r.status_code == 409


async def test_register_rejections(api, tmp_path):
    # server_path 부재 → 400
    r = await api.post(f"{BASE}/register", json={
        "name": "x", "server_path": str(tmp_path / "nope.csv"), "modality": "order"})
    assert r.status_code == 400
    # Mode A(multipart) → 명시적 400 + 이월 안내 (D-186)
    r = await api.post(f"{BASE}/register", files={"file": ("a.csv", b"a,b\n1,2\n")})
    assert r.status_code == 400 and "Mode B" in r.json()["detail"]
    # modality 화이트리스트(4종) 위반 → 422
    p = tmp_path / "ok.csv"
    p.write_text("a\n1\n", encoding="utf-8")
    r = await api.post(f"{BASE}/register", json={
        "name": "y", "server_path": str(p), "modality": "video"})
    assert r.status_code == 422
    # 필수 필드 누락 → 422
    r = await api.post(f"{BASE}/register", json={"name": "z"})
    assert r.status_code == 422


async def test_register_orphan_dir_guard(api, tmp_path):
    """3a 룰링 ④ 후속(3b ⓞ): DELETE=DB-only 라 잔존한 data/lake/<id>/ 가 있으면
    DB entry 부재여도 409(orphan 명시) — 동일 id silent 복사(이종 혼입) 차단."""
    import datalake_api
    orphan = datalake_api.LAKE_ROOT / "ghost_data"
    orphan.mkdir(parents=True)                       # DB entry 없이 디렉터리만 잔존
    src = tmp_path / "g.csv"
    src.write_text("a\n1\n", encoding="utf-8")
    r = await api.post(f"{BASE}/register", json={
        "name": "Ghost Data", "server_path": str(src), "modality": "timeseries"})
    assert r.status_code == 409 and "orphan" in r.json()["detail"]
    assert list(orphan.iterdir()) == []              # silent 복사 0 (디렉터리 불변)


async def test_register_non_tabular_columns_zero(api, tmp_path):
    src = tmp_path / "blob.bin"
    src.write_bytes(b"\x00\x01\x02")
    r = await api.post(f"{BASE}/register", json={
        "name": "raw blob", "server_path": str(src), "modality": "inspection-image"})
    assert r.status_code == 200
    body = r.json()
    assert body["n_columns"] == 0 and "columns_note" in body   # 비표형식 = 0 + 응답 명시
    cols = (await api.get(f"{BASE}/raw_blob/columns")).json()["columns"]
    assert cols == []


# ── 10. DELETE /{id} ─────────────────────────────────────────────────────
async def test_delete_404_and_history(api):
    import catalog
    import db as dbmod
    assert (await api.delete(f"{BASE}/ghost")).status_code == 404

    await _seed(catalog, _entry("d1"))
    await catalog.replace_columns("d1", [
        {"name": "v", "dtype": "float", "column_kind": "scalar", "group_desc": None}])
    await catalog.insert_constraint("d1", "v", {"type": "range", "min": 0, "max": 1},
                                    approved_by="user")
    r = await api.delete(f"{BASE}/d1")
    assert r.status_code == 200 and r.json() == {"deleted": True}
    assert (await api.get(f"{BASE}/d1/metadata")).status_code == 404
    pool = await dbmod.get_pool()
    actions = [h["action"] for h in await pool.fetch(
        "SELECT action FROM datalake.constraints_history "
        "WHERE datalake_id='d1' ORDER BY history_id")]
    assert actions == ["create", "delete"]            # 삭제도 history append (D-179)
