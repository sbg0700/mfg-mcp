"""
tests/test_ingest_unit.py — datalake_ingest._uniquify_headers 단위 (DB 불요, D-182).

검증: 비어있지 않은 중복 헤더 → 결정론 __dupN 접미, 드롭 0, 비중복 무변형,
멱등(이미 유니크한 입력에 재적용 = 항등). columns PK(datalake_id,name) 위반 방지의 근거.
"""
from datalake_ingest import _uniquify_headers


def test_duplicate_gets_dup2_suffix_no_drop():
    out, renamed = _uniquify_headers(["a", "b", "a"])
    assert out == ["a", "b", "a__dup2"]          # 결정론 접미 (__dup2)
    assert renamed == ["a→a__dup2"]
    assert len(out) == 3                         # 드롭 0 — 입력 길이 보존


def test_multiple_duplicates_increment_counter():
    out, renamed = _uniquify_headers(["a", "a", "a"])
    assert out == ["a", "a__dup2", "a__dup3"]    # 카운터 증가
    assert renamed == ["a→a__dup2", "a→a__dup3"]


def test_no_duplicate_unchanged():
    out, renamed = _uniquify_headers(["a", "b", "c"])
    assert out == ["a", "b", "c"]                # 비중복 무변형
    assert renamed == []


def test_idempotent_second_pass_is_identity():
    names = ["x", "x", "y", "x"]
    out1, renamed1 = _uniquify_headers(names)
    assert out1 == ["x", "x__dup2", "y", "x__dup3"]
    out2, renamed2 = _uniquify_headers(out1)     # 이미 유니크 → 항등(멱등)
    assert out2 == out1
    assert renamed2 == []
