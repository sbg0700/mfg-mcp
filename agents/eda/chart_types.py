"""agents/eda/chart_types.py — STEP 3a 허용 차트 타입 (코드 고정, 환각 방어).

spec-2 Part 6-4 기반. LLM이 추천하는 chart_type은 반드시 CHART_TYPE_IDS 안에 있어야
유효 (호출부에서 필터). 가이드 밖 차트는 LLM이 데이터 보고 제안 가능 (단 IDs 안에서).

★function_axis별 FUNCTION_CHART_GUIDE는 LLM "참고용". 강제 매핑이 아님.★
"""
from __future__ import annotations

# 허용 차트 타입 정의 — 코드 고정 (LLM 생성 X)
CHART_TYPES: dict[str, dict] = {
    "fft_spectrum": {
        "label": "FFT 주파수 스펙트럼",
        "modality": ["timeseries"],
        "needs": "numeric_signal",
        "description": "주파수 도메인 분석 — 진동/주기성 (베어링 결함, 회전체 이상)",
    },
    "boxplot_by_label": {
        "label": "타겟 라벨별 박스플롯",
        "modality": ["timeseries", "order", "event-log"],
        "needs": "numeric+label",
        "description": "라벨(class/PASS_YN 등) 그룹별 5수치 비교 — 라벨 영향 가시화",
    },
    "histogram": {
        "label": "히스토그램",
        "modality": ["timeseries", "order"],
        "needs": "numeric",
        "description": "연속 변수 분포 (bins/counts) — 정규성·다봉 확인",
    },
    "class_distribution": {
        "label": "클래스 분포 막대",
        "modality": ["event-log", "order"],
        "needs": "categorical",
        "description": "카테고리/클래스 카운트 — 불균형 가시화",
    },
    "correlation_bar": {
        "label": "타겟 상관계수 막대",
        "modality": ["timeseries", "order"],
        "needs": "numeric_multi",
        "description": "타겟과의 |피어슨 상관| 상위 — 변수 중요도 후보",
    },
    "scatter": {
        "label": "산점도 (핵심 2변수)",
        "modality": ["timeseries", "order"],
        "needs": "numeric_multi",
        "description": "두 연속 변수 관계 (선형·비선형·이상치) 시각화",
    },
    "pareto": {
        "label": "파레토 차트",
        "modality": ["event-log", "order"],
        "needs": "categorical_count",
        "description": "결함/원인 상위 카테고리 + 누적 % (80/20)",
    },
    "rms_trend": {
        "label": "RMS 트렌드",
        "modality": ["timeseries"],
        "needs": "numeric_signal",
        "description": "윈도우별 RMS 평균 — 진동 에너지 추세",
    },
}

# 환각 방어 필터 — LLM 추천 chart_type이 이 안에 있어야 통과
CHART_TYPE_IDS: frozenset[str] = frozenset(CHART_TYPES.keys())

# function_axis별 기본 차트 가이드 (LLM 참고용 — 강제 아님).
# LLM 실패 / 빈 추천 시 폴백으로도 사용.
FUNCTION_CHART_GUIDE: dict[str, dict[str, list[str]]] = {
    "maintenance": {"primary": ["fft_spectrum"],                "secondary": ["rms_trend", "boxplot_by_label"]},
    "quality":     {"primary": ["boxplot_by_label", "class_distribution"], "secondary": ["histogram", "correlation_bar"]},
    "process":     {"primary": ["boxplot_by_label"],            "secondary": ["correlation_bar", "scatter", "histogram"]},
    "reference":   {"primary": ["pareto"],                      "secondary": ["histogram", "class_distribution"]},
}


def is_chart_modality_ok(chart_type: str, modality: str) -> bool:
    """chart_type이 해당 modality에서 의미 있는지 확인 (환각 방어 보조)."""
    spec = CHART_TYPES.get(chart_type)
    if not spec:
        return False
    return modality in spec.get("modality", [])
