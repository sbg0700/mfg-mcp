"""
tests/test_ordinal_3_5.py — DL-3.5 A: columns.ordinal backfill + get_columns 정렬 (D-193/194).

검증(throwaway PG 55432/dl_test, D-182):
- 순수: compute_ordinal_map · check_group_contiguity · diff_name_sets(fail-loud).
- DB: apply_ordinals 가 소스 물리 순서로 ordinal=index 부여 · get_columns ORDER BY ordinal
  (L1_cnc ASCII 사전정렬 결함 해소 실증) · 한글/그룹/__dupN·.N 위치 보존 · 멱등 ·
  finalize(NULL fail-loud · SET NOT NULL · UNIQUE).
- finalize 변이 테스트는 finally 에서 NOT NULL/UNIQUE 해제(공유 세션 스키마 오염 방지).
"""
import asyncpg
import pytest

from datalake_ordinal_backfill import (
    _UNIQ_NAME,
    apply_ordinals,
    check_group_contiguity,
    compute_ordinal_map,
    diff_name_sets,
    finalize_ordinal_constraints,
)


def _entry(did: str, **kw):
    base = {"datalake_id": did, "source": "kamp", "name": did, "data_path": f"data/lake/{did}/"}
    base.update(kw)
    return base


def _scalars(names):
    return [{"name": n, "column_kind": "scalar"} for n in names]


async def _reset_ordinal_state(pool):
    """finalize 테스트 오염 방지 — 다른 테스트(test_catalog 등)는 ordinal 미주입 INSERT 이므로
    NOT NULL/UNIQUE 가 남으면 깨진다. 멱등(이미 nullable/제약없음이면 무해)."""
    await pool.execute(f"ALTER TABLE datalake.columns DROP CONSTRAINT IF EXISTS {_UNIQ_NAME}")
    await pool.execute("ALTER TABLE datalake.columns ALTER COLUMN ordinal DROP NOT NULL")


# ── 순수 로직 (DB 불요) ──────────────────────────────────────────────────
def test_compute_ordinal_map_preserves_order_and_skips_empty():
    recs = [
        {"datalake_id": "a", "columns": [{"name": "x"}, {"name": "y"}, {"name": "z"}]},
        {"datalake_id": "b", "columns": []},                       # 컬럼 0(경로없음) → 제외
    ]
    assert compute_ordinal_map(recs) == {"a": ["x", "y", "z"]}     # 순서 보존


def test_diff_name_sets_fail_loud():
    assert diff_name_sets({"e": ["a", "b"]}, {"e": ["a", "b"]}) == []   # 일치 → 0
    m = diff_name_sets({"e": ["a"]}, {"e": ["a", "b"]})                 # DB 드리프트(+b)
    assert len(m) == 1 and m[0][0] == "e"
    m2 = diff_name_sets({}, {"e": ["a"]})                              # 재파싱 산출 없음
    assert len(m2) == 1 and "산출 없음" in m2[0][1]


def test_group_contiguity_check():
    wav = {"name": "waveform", "column_kind": "group", "group_desc": {"kind": "waveform"}}
    base = [{"name": "ts", "column_kind": "scalar"}, wav]
    assert check_group_contiguity(
        [{"datalake_id": "w", "columns": base, "_group_trailing": True}]) == []      # 후행연속 OK
    v = check_group_contiguity(
        [{"datalake_id": "w", "columns": base, "_group_trailing": False}])           # 비연속 → 위반
    assert len(v) == 1 and v[0][0] == "w"
    img = {"name": "image_set", "column_kind": "group", "group_desc": {"kind": "image_set"}}
    assert check_group_contiguity(
        [{"datalake_id": "i", "columns": [img], "_group_trailing": False}]) == []    # image_set 제외


# ── DB: ordinal 부여 + 정렬 (throwaway PG) ──────────────────────────────
async def test_get_columns_orders_by_ordinal_ascii_defect_resolved(cat):
    import db
    pool = await db.get_pool()
    await _reset_ordinal_state(pool)
    await cat.upsert_entry(_entry("cnc"))
    src = [f"{n}TH INJECTION VELOCITY" for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)]   # 소스 물리 순서
    await cat.replace_columns("cnc", _scalars(src))               # replace_columns 가 입력순서로 ordinal 공급(b)
    await apply_ordinals(pool, {"cnc": src})                      # backfill 도 동일 순서 재부여(라이브 32셋 경로)

    got = [c["name"] for c in await cat.get_columns("cnc")]
    assert got == src                                             # ORDER BY ordinal = 물리 순서
    ascii_order = sorted(src)
    assert ascii_order != src                                    # ASCII 사전정렬 ≠ 물리 순서(결함 실재)
    assert ascii_order[0] == src[9]                              # 구 ORDER BY name 은 '10TH…' 가 맨앞


async def test_korean_header_order_preserved(cat):
    import db
    pool = await db.get_pool()
    await _reset_ordinal_state(pool)
    await cat.upsert_entry(_entry("kor"))
    src = ["검사호기", "검사일시", "실제값", "기준값", "측정값"]
    await cat.replace_columns("kor", _scalars(src))
    await apply_ordinals(pool, {"kor": src})
    assert [c["name"] for c in await cat.get_columns("kor")] == src


async def test_group_ordinal_is_trailing_rank(cat):
    import db
    pool = await db.get_pool()
    await _reset_ordinal_state(pool)
    await cat.upsert_entry(_entry("wav"))
    src = ["timestamp", "waveform"]                              # build_record: scalar 먼저, group 후행
    await cat.replace_columns("wav", [
        {"name": "timestamp", "column_kind": "scalar"},
        {"name": "waveform", "column_kind": "group",
         "group_desc": {"kind": "waveform", "n_cols": 2048}}])
    await apply_ordinals(pool, {"wav": src})
    got = await cat.get_columns("wav")
    assert {c["name"]: c["ordinal"] for c in got} == {"timestamp": 0, "waveform": 1}
    assert [c["name"] for c in got] == src


async def test_dup_dotn_unnamed_physical_position_preserved(cat):
    import db
    pool = await db.get_pool()
    await _reset_ordinal_state(pool)
    await cat.upsert_entry(_entry("dup"))
    src = ["a", "a__dup2", "단위", "단위.1", "__unnamed_4"]      # 상류/우리 마킹 — 위치 그대로
    await cat.replace_columns("dup", _scalars(src))
    await apply_ordinals(pool, {"dup": src})
    assert [c["name"] for c in await cat.get_columns("dup")] == src   # 재정렬·병합·드롭 0


async def test_backfill_idempotent(cat):
    import db
    pool = await db.get_pool()
    await _reset_ordinal_state(pool)
    await cat.upsert_entry(_entry("idem"))
    names = ["c0", "c1", "c2", "c3"]
    await cat.replace_columns("idem", _scalars(names))
    await apply_ordinals(pool, {"idem": names})
    first = {c["name"]: c["ordinal"] for c in await cat.get_columns("idem")}
    await apply_ordinals(pool, {"idem": names})                  # 2회차
    second = {c["name"]: c["ordinal"] for c in await cat.get_columns("idem")}
    assert first == second == {"c0": 0, "c1": 1, "c2": 2, "c3": 3}


# ── DB: finalize (NULL fail-loud · NOT NULL · UNIQUE) ────────────────────
async def test_finalize_fail_loud_on_null(cat):
    import db
    pool = await db.get_pool()
    await _reset_ordinal_state(pool)
    await cat.upsert_entry(_entry("nn"))
    await cat.replace_columns("nn", _scalars(["a"]))
    await pool.execute(                                          # 라이브 32셋 pre-backfill(ordinal NULL) 모사
        "UPDATE datalake.columns SET ordinal=NULL WHERE datalake_id='nn'")
    with pytest.raises(RuntimeError, match="NULL"):
        await finalize_ordinal_constraints(pool)                # SET NOT NULL 도달 전 차단


async def test_finalize_not_null_and_unique_then_reset(cat):
    import db
    pool = await db.get_pool()
    await _reset_ordinal_state(pool)
    await cat.upsert_entry(_entry("fz"))
    await cat.replace_columns("fz", _scalars(["a", "b"]))
    await apply_ordinals(pool, {"fz": ["a", "b"]})
    try:
        await finalize_ordinal_constraints(pool)                # NULL 0 → SET NOT NULL → UNIQUE
        with pytest.raises(asyncpg.exceptions.NotNullViolationError):
            await pool.execute(
                "INSERT INTO datalake.columns (datalake_id,name,ordinal) VALUES ('fz','c',NULL)")
        with pytest.raises(asyncpg.exceptions.UniqueViolationError):
            await pool.execute(                                 # (fz, ordinal=0) 중복
                "INSERT INTO datalake.columns (datalake_id,name,ordinal) VALUES ('fz','d',0)")
    finally:
        await _reset_ordinal_state(pool)                        # 공유 세션 오염 해제


# ── (b) forward 캡처: replace_columns 가 ordinal 공급 → finalize 후 register/재적재 안전 ──
async def test_replace_columns_supplies_ordinal_survives_finalize(cat):
    """replace_columns 가 입력 순서로 ordinal 0..k-1 공급(forward 캡처) → finalize(NOT NULL+UNIQUE)
    후에도 register(신규)·재적재(replace 재호출) 통과(fail-loud 아님 · UNIQUE 전이 위반 0).
    호출처 2곳(ingest execute_load · API register)이 replace_columns 경유라 자동 커버."""
    import db
    pool = await db.get_pool()
    await _reset_ordinal_state(pool)
    await cat.upsert_entry(_entry("reg"))
    await cat.replace_columns("reg", _scalars(["x", "y", "z"]))   # 입력 순서 = ordinal index
    assert {c["name"]: c["ordinal"] for c in await cat.get_columns("reg")} == {"x": 0, "y": 1, "z": 2}
    try:
        await finalize_ordinal_constraints(pool)                 # NULL 0 → NOT NULL + UNIQUE
        # finalize 후 신규 register — replace_columns 가 ordinal 공급 → NOT NULL 위반 0
        await cat.upsert_entry(_entry("reg2"))
        await cat.replace_columns("reg2", _scalars(["a", "b"]))
        assert {c["name"]: c["ordinal"] for c in await cat.get_columns("reg2")} == {"a": 0, "b": 1}
        # 재적재 경로: 기존 entry replace 재호출(컬럼 추가) → ordinal 재부여, UNIQUE 전이 위반 0
        await cat.replace_columns("reg", _scalars(["x", "y", "z", "w"]))
        assert {c["name"]: c["ordinal"]
                for c in await cat.get_columns("reg")} == {"x": 0, "y": 1, "z": 2, "w": 3}
    finally:
        await _reset_ordinal_state(pool)
