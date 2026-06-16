"""
tests/test_ingest_unit.py — datalake_ingest._uniquify_headers 단위 (DB 불요, D-182).

검증: 비어있지 않은 중복 헤더 → 결정론 __dupN 접미, 드롭 0, 비중복 무변형,
멱등(이미 유니크한 입력에 재적용 = 항등). columns PK(datalake_id,name) 위반 방지의 근거.
"""
from datalake_ingest import _uniquify_headers, audit_header_names, read_header


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


# ── DL-3.5 B (D-195): 헤더 anti-silent 리포트 카운팅/출처 분류 단위 (DB 불요) ──
def test_audit_counts_and_source_classification(tmp_path):
    """합성 헤더(정확중복 2 / .N 3 / 빈헤더 1)를 기존 ingest 헤더 경로
    (read_header → _uniquify_headers)로 통과시켜 카운트·출처 분류 검증. 라이브 무접촉."""
    csv_path = tmp_path / "synthetic_header.csv"
    # A×3 → __dup2/__dup3(우리 마킹 2) · bare 단위+단위.1/.2/.3(상류 pandas 가족 .N 3) · 끝 빈칸(1)
    csv_path.write_text("A,A,A,단위,단위.1,단위.2,단위.3,\nv,v,v,u,1,2,3,9\n", encoding="utf-8")

    stored = read_header(csv_path, "utf-8")                      # 빈헤더 → __unnamed_i
    assert stored == ["A", "A", "A", "단위", "단위.1", "단위.2", "단위.3", "__unnamed_7"]
    uniq, renamed = _uniquify_headers(stored)                    # 정확중복 → __dupN(우리 마킹)
    assert renamed == ["A→A__dup2", "A→A__dup3"]

    a = audit_header_names(uniq)
    assert a["dup_marked"]["count"] == 2                         # __dupN 생성 건수(우리 마킹)
    assert a["dup_marked"]["names"] == ["A__dup2", "A__dup3"]
    assert a["dup_marked"]["source"] == "ingest"
    assert a["unnamed_marked"]["count"] == 1                     # 빈헤더 채움(우리 마킹)
    assert a["unnamed_marked"]["names"] == ["__unnamed_7"]
    assert a["unnamed_marked"]["source"] == "ingest"
    assert a["dotn_upstream"]["count"] == 3                      # .N 의심(상류 보존, bare 단위 동반)
    assert a["dotn_upstream"]["names"] == ["단위.1", "단위.2", "단위.3"]   # bare 단위 자체는 무분류
    assert a["dotn_upstream"]["source"] == "upstream"           # informational — 결함 단정 아님


def test_audit_clean_header_all_zero():
    """클린 헤더 → 전 카운트 0(오검출 없음). 그룹 디스크립터 이름도 무분류."""
    a = audit_header_names(["temp", "pressure", "current", "waveform", "image_set"])
    assert a["dup_marked"]["count"] == 0
    assert a["unnamed_marked"]["count"] == 0
    assert a["dotn_upstream"]["count"] == 0


def test_audit_dotn_requires_bare_base_sibling():
    """단순 소수/날짜 컬럼명(0.025·…07.380958)은 bare base 형제 부재 → .N 오검출 배제
    (L3_mold_anomaly 실데이터 회귀). bare base 동반 시에만 .N 분류."""
    a = audit_header_names(["2023-11-10 09:07:07.380958", "0.02875", "0.025", "0.05"])
    assert a["dotn_upstream"]["count"] == 0                      # base 형제 없음 → 미분류

    b = audit_header_names(["0", "0.1", "0.2"])                  # bare '0' 동반 → 가족 패턴
    assert b["dotn_upstream"]["names"] == ["0.1", "0.2"]


def test_audit_buckets_mutually_exclusive():
    """정확중복된 .N 이름은 최종명 기준 단일 버킷(첫 건=.N, 재명명건=__dupN). bare base 동반."""
    uniq, _ = _uniquify_headers(["단위", "단위.1", "단위.1"])   # → ["단위","단위.1","단위.1__dup2"]
    a = audit_header_names(uniq)
    assert a["dotn_upstream"]["names"] == ["단위.1"]             # 첫 .N = 상류
    assert a["dup_marked"]["names"] == ["단위.1__dup2"]          # 재명명 = 우리 __dupN
    assert a["dotn_upstream"]["count"] == 1 and a["dup_marked"]["count"] == 1
