"""
mcp-servers/timeseries/semantic.py
==================================
컬럼 의미 그룹 분류기 (우려 1 — 공정 의미 기반 표준화).

★헌법 "LLM은 제안, 규칙이 결정" 그대로 적용★:
  - 규칙(컬럼명 정규식 패턴)이 먼저 분류한다. 거의 다 여기서 해결.
  - 패턴에 안 걸린 컬럼만 'unknown'으로 남겨, Inspector가 LLM에게 보조 질의.

왜 이게 필요한가 (모달리티는 외형, 의미 그룹은 도메인 — 두 차원이 직교):
  같은 timeseries 안에서도 'INJECTION VELOCITY 1~10'은 '사출 시퀀스'라는 도메인 의미를 가진다.
  독립 정규화하면 1→10 시퀀스 추세가 소실된다. 그룹으로 묶어 시퀀스 보존 정규화해야 한다.

그룹별 표준화 전략(strategy)도 함께 정의 — Planner/Executor가 이를 보고 처리를 결정.
"""
from __future__ import annotations
import re
from typing import Any

# (정규식 패턴, semantic_group, 표준화 전략) — 위에서부터 우선 매칭
# strategy 의미:
#   passthrough         = 정규화 안 함 (메타데이터/식별자)
#   sequence_preserve   = 시퀀스 묶음. 1→N 추세 보존하며 그룹 단위 정규화
#   profile_group       = 프로파일 묶음. 그룹 평균0/표준편차1 (형상 보존)
#   single_zscore       = 단독 z-score
#   label               = 라벨 컬럼 (정규화 아닌 클래스 처리 대상)
_PATTERNS: list[tuple[str, str, str]] = [
    # 메타데이터/식별자 (정규화 제외) — LOT No., LOT_NO, LOTNO 등 변형 포괄
    (r"^lot[\s_.]*(no|id)?[\s_.]*$",              "metadata",            "passthrough"),
    (r"^(timestamp|time|date|datetime|일시|시각)$", "metadata",            "passthrough"),
    (r"^(eqp[\s_]?id|equip|설비|장비|machine[\s_]?id)$", "metadata",        "passthrough"),
    (r"^(tagid|tag[\s_]?id|id|uid|index|seq[\s_]?no)$", "metadata",        "passthrough"),
    (r"^(operator|작업자|inspector|검사자)$",       "metadata",            "passthrough"),

    # 라벨/판정 (클래스 처리 대상)
    (r"^(pass[\s_]?yn|판정|판정결과|result|judge|judgement|ok[\s_]?ng|label|quality)$",
     "label", "label"),

    # 사출 시퀀스 — ★switch를 velocity보다 먼저 (더 구체적 패턴 우선)★
    (r"injection\s*switch", "injection_switch_sequence", "sequence_preserve"),
    (r"injection\s*velocity",   "injection_sequence",      "sequence_preserve"),
    (r"injection\s*pressure",   "injection_pressure_sequence", "sequence_preserve"),
    (r"\d+(st|nd|rd|th)\s*injection", "injection_sequence", "sequence_preserve"),

    # 보압 프로파일 (1~6 — 프로파일 형상 보존)
    (r"pack\s*pressure\s*\d+",        "pack_pressure_profile",   "profile_group"),
    (r"pack\s*time\s*\d+",            "pack_time_profile",       "profile_group"),
    (r"hold\s*pressure\s*\d+",        "hold_pressure_profile",   "profile_group"),

    # 단독 측정값 (단독 정규화)
    (r"back\s*pressure",              "back_pressure",           "single_zscore"),
    (r"(servo|cnc).*load",            "servo_load",              "single_zscore"),
    (r"(servo|cnc).*current",         "servo_current",           "single_zscore"),
    (r"temp|temperature|온도",         "temperature",             "single_zscore"),
    (r"press(ure)?|압력|press_force",  "pressure",                "single_zscore"),
    (r"value|값|측정값|measure",        "measurement",             "single_zscore"),
    (r"cycle|사이클|cycletime",        "cycle",                   "single_zscore"),
]


def classify_column(name: str) -> tuple[str, str]:
    """컬럼명 → (semantic_group, strategy). 규칙 매칭. 미매칭이면 ('unknown','single_zscore')."""
    n = name.strip().lower()
    for pat, group, strategy in _PATTERNS:
        if re.search(pat, n):
            return group, strategy
    return "unknown", "single_zscore"


def classify_columns(names: list[str]) -> dict[str, dict[str, Any]]:
    """컬럼명 리스트 → {컬럼명: {semantic_group, strategy}}.
    + 같은 그룹에 속한 컬럼들(시퀀스/프로파일)을 묶어 group_members 정보도 제공."""
    result: dict[str, dict[str, Any]] = {}
    group_members: dict[str, list[str]] = {}
    for name in names:
        group, strategy = classify_column(name)
        result[name] = {"semantic_group": group, "strategy": strategy}
        group_members.setdefault(group, []).append(name)
    # 그룹에 멤버가 2개 이상이면 '묶음 처리 대상'으로 표시 (중복 방지의 근거)
    for name, info in result.items():
        members = group_members[info["semantic_group"]]
        info["group_size"] = len(members)
        info["is_grouped"] = len(members) > 1 and info["semantic_group"] not in ("unknown", "metadata")
    return result


def summarize_groups(names: list[str]) -> dict[str, Any]:
    """그룹 요약 (Inspector/Planner가 쓰기 좋게).
    {group: {members, strategy, count}} + unknown 목록(LLM 보조 대상)."""
    cls = classify_columns(names)
    groups: dict[str, dict[str, Any]] = {}
    for name, info in cls.items():
        g = info["semantic_group"]
        if g not in groups:
            groups[g] = {"members": [], "strategy": info["strategy"]}
        groups[g]["members"].append(name)
    for g in groups:
        groups[g]["count"] = len(groups[g]["members"])
    unknown = groups.get("unknown", {}).get("members", [])
    return {"groups": groups, "unknown_columns": unknown,
            "n_groups": len([g for g in groups if g != "unknown"])}
