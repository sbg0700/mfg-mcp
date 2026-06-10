"""
tests/test_catalog.py — backend.catalog 통합 (throwaway PG 55432/dl_test, D-182).

검증: run_migration 멱등 · datalake.get round-trip · list AND 필터(vid×function×site) ·
D-172 full-record-replace(부분 upsert 시 NULL 덮임 *명시*) · scalar/group 컬럼(JSONB) ·
constraints CRUD(명시삭제 = delete_entry 경유).
※ Phase C(D-179) constraints 감사(approved_by/history) 테스트는 파일 하단에 추가.
"""


def _entry(did: str, **kw):
    """완전 레코드 헬퍼 (D-172: 호출자는 항상 완전 레코드)."""
    base = {"datalake_id": did, "source": "kamp", "name": did, "data_path": f"data/lake/{did}/"}
    base.update(kw)
    return base


async def test_migration_idempotent(cat):
    import db
    pool = await db.get_pool()
    await cat.run_migration()                                  # fixture 1회 + 여기 1회
    tabs1 = sorted(r["tablename"] for r in await pool.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='datalake'"))
    idx1 = sorted(r["indexname"] for r in await pool.fetch(
        "SELECT indexname FROM pg_indexes WHERE schemaname='datalake'"))
    await cat.run_migration()                                  # 또 1회 → 동일해야
    tabs2 = sorted(r["tablename"] for r in await pool.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='datalake'"))
    idx2 = sorted(r["indexname"] for r in await pool.fetch(
        "SELECT indexname FROM pg_indexes WHERE schemaname='datalake'"))
    assert tabs1 == tabs2                                      # 스키마 멱등
    assert idx1 == idx2                                        # 인덱스 멱등
    assert {"entries", "columns", "constraints"} <= set(tabs1)


async def test_get_roundtrip(cat):
    await cat.upsert_entry(_entry("t1", modality="timeseries"))
    assert await cat.get("t1") == {"data_path": "data/lake/t1/", "modality": "timeseries"}
    assert await cat.get("nonexistent") is None


async def test_list_and_filter(cat):
    await cat.upsert_entry(_entry("e1", vid="L1", function="process", site="A"))
    await cat.upsert_entry(_entry("e2", vid="L1", function="process", site="B"))
    await cat.upsert_entry(_entry("e3", vid="L1", function="quality", site="A"))
    await cat.upsert_entry(_entry("e4", vid="L2", function="process", site="A"))
    got = await cat.list_entries(vid="L1", function="process", site="A")   # AND 3축 조합
    assert [r["datalake_id"] for r in got] == ["e1"]
    assert len(await cat.list_entries(vid="L1")) == 3                       # 단일축


async def test_d172_full_record_replace_nulls(cat):
    await cat.upsert_entry(_entry(
        "t2", name="n", modality="m", site="A", function="process", vid="L1",
        company="C", encoding="utf-8", format="csv", size_bytes=10, reusable_flag=True))
    # 부분 필드 누락 재upsert → 미지정 컬럼이 NULL 로 덮임 (D-172 full-record-replace 명시 검증)
    await cat.upsert_entry({"datalake_id": "t2", "source": "kamp", "name": "n2",
                            "data_path": "p2"})
    row = await cat.get_entry("t2")
    assert row["name"] == "n2" and row["data_path"] == "p2"
    for col in ("modality", "site", "function", "vid", "company",
                "encoding", "format", "size_bytes"):
        assert row[col] is None, f"{col} 가 NULL 로 안 덮임 — D-172 위반"
    assert row["reusable_flag"] is False                       # 미지정 → 기본 False


async def test_scalar_and_group_columns(cat):
    await cat.upsert_entry(_entry("t3"))
    await cat.replace_columns("t3", [
        {"name": "temp", "dtype": "float64", "column_kind": "scalar"},
        {"name": "waveform", "column_kind": "group",
         "group_desc": {"n_cols": 2048, "kind": "waveform",
                        "axis": "time_offset_s", "fs_hz": 488}},
    ])
    cols = {c["name"]: c for c in await cat.get_columns("t3")}
    assert cols["temp"]["column_kind"] == "scalar"
    assert cols["temp"]["group_desc"] is None
    g = cols["waveform"]
    assert g["column_kind"] == "group"
    assert isinstance(g["group_desc"], dict)                   # JSONB → dict round-trip
    assert g["group_desc"]["axis"] == "time_offset_s"
    assert g["group_desc"]["n_cols"] == 2048


async def test_constraints_crud(cat):
    await cat.upsert_entry(_entry("c1"))
    await cat.insert_constraint("c1", "temp", {"type": "range", "min": 0, "max": 100, "unit": "C"})
    cs = await cat.get_constraints("c1")
    assert len(cs) == 1
    assert cs[0]["constraint_spec"] == {"type": "range", "min": 0, "max": 100, "unit": "C"}
    # update (동일 키 upsert)
    await cat.insert_constraint("c1", "temp", {"type": "range", "min": 10, "max": 90, "unit": "C"})
    cs = await cat.get_constraints("c1")
    assert len(cs) == 1 and cs[0]["constraint_spec"]["min"] == 10
    # 명시 삭제 = delete_entry 경유 (자식 constraints 까지 단일 트랜잭션 삭제)
    await cat.delete_entry("c1")
    assert await cat.get_constraints("c1") == []
    assert await cat.get("c1") is None


# ── DL-2.5 / D-179: constraints 감사 (approved_by + append-only history) ──────
async def test_constraints_history_migration_idempotent(cat):
    """ALTER/CREATE 2회 무해 — approved_by 컬럼 + constraints_history 테이블 멱등."""
    import db
    pool = await db.get_pool()
    await cat.run_migration()
    await cat.run_migration()
    constr_cols = {r["column_name"] for r in await pool.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='datalake' AND table_name='constraints'")}
    assert "approved_by" in constr_cols
    hist = await pool.fetchval(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='datalake' AND table_name='constraints_history'")
    assert hist == 1


async def test_constraint_history_create_update_delete(cat):
    """create→update→delete 시 history 3행·action 정확·approved_by 보존."""
    import db
    pool = await db.get_pool()
    await cat.upsert_entry(_entry("h1"))
    await cat.insert_constraint("h1", "temp", {"type": "range", "min": 0, "max": 100}, approved_by="alice")
    await cat.insert_constraint("h1", "temp", {"type": "range", "min": 10, "max": 90}, approved_by="bob")
    await cat.delete_entry("h1")
    rows = await pool.fetch(
        "SELECT action, approved_by FROM datalake.constraints_history "
        "WHERE datalake_id='h1' AND column_name='temp' ORDER BY history_id")
    assert [r["action"] for r in rows] == ["create", "update", "delete"]
    assert [r["approved_by"] for r in rows] == ["alice", "bob", "bob"]   # delete=직전행(bob) 보존


async def test_history_survives_entry_delete(cat):
    """entry 삭제 후에도 history 잔존(FK 없음, D-179)."""
    import db
    pool = await db.get_pool()
    await cat.upsert_entry(_entry("h2"))
    await cat.insert_constraint("h2", "x", {"type": "range", "min": 1, "max": 2}, approved_by="z")
    await cat.delete_entry("h2")
    n = await pool.fetchval(
        "SELECT count(*) FROM datalake.constraints_history WHERE datalake_id='h2'")
    assert n == 2                                # create + delete
    assert await cat.get("h2") is None
    assert await cat.get_constraints("h2") == []
