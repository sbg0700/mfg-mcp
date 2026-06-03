"""agents/ml/param_whitelist.py — STEP 3c 파라미터 화이트리스트 (clamp + notice).

3a-2 code_sandbox AST 화이트리스트 + STEP 2a balance_options 발상.
원칙: 비현실값(환각/낭비)만 거름. 적합한 범위(10~500 등)는 통과 → 학습 품질 영향 0.
초과 시 무조건 파기 X → 안전 범위로 clamp + 사용자 알림(notices) → 사용자 결정.

random_state는 항상 RANDOM_STATE(=42)로 고정 — 재현성 헌법.
"""
from __future__ import annotations
from typing import Any


RANDOM_STATE: int = 42  # 모든 모델 재현성 고정 (D-141 3원칙 ②)


# 모델별 허용 파라미터 + 안전 범위
# - tuple (lo, hi): 수치 범위 (밖이면 clamp)
# - list [v1, v2, ...]: 허용 값 목록 (외이면 첫 값으로)
# - "fixed": 사용자/LLM이 보낸 값 무시, 항상 RANDOM_STATE 사용
ALLOWED_PARAMS: dict[str, dict[str, Any]] = {
    "RandomForestRegressor": {
        "n_estimators": (10, 500),
        "max_depth": (2, 30),
        "min_samples_split": (2, 50),
        "random_state": "fixed",
    },
    "RandomForestClassifier": {
        "n_estimators": (10, 500),
        "max_depth": (2, 30),
        "min_samples_split": (2, 50),
        "class_weight": ["balanced", None],
        "random_state": "fixed",
    },
    "XGBoostClassifier": {
        "n_estimators": (10, 500),
        "max_depth": (2, 20),
        "learning_rate": (0.01, 0.3),
        "random_state": "fixed",
    },
    "IsolationForest": {
        "n_estimators": (10, 500),
        "contamination": (0.001, 0.5),
        "random_state": "fixed",
    },
}


def validate_and_clamp_params(
    model_name: str, requested: dict | None
) -> tuple[dict, list[str]]:
    """제안 파라미터를 화이트리스트로 검증.
    범위 초과 시 상한/하한으로 clamp, 허용 외 키는 무시.
    반환: (safe_params, notices). safe_params는 random_state 항상 포함.

    무조건 파기 X — 조정 후 notices에 알림 → 호출부(/train/validate)가
    사용자에게 보여주고 진행/취소 결정 (옵션 카드 D-111 패턴 일관).
    """
    spec = ALLOWED_PARAMS.get(model_name, {})
    safe: dict[str, Any] = {"random_state": RANDOM_STATE}
    notices: list[str] = []

    for key, val in (requested or {}).items():
        if key == "random_state":
            # 사용자가 다른 값을 보내도 무시(notice) + RANDOM_STATE 유지
            if val != RANDOM_STATE:
                notices.append(
                    f"'random_state' {val} → {RANDOM_STATE}로 고정 (재현성)"
                )
            continue
        if key not in spec:
            notices.append(f"'{key}'는 허용 파라미터가 아님 — 무시")
            continue
        rule = spec[key]
        if rule == "fixed":
            continue  # spec 자체가 고정 (예: random_state는 위에서 처리됨)
        if isinstance(rule, tuple):
            lo, hi = rule
            try:
                # int/float 보존: 정수 spec이면 정수로
                if isinstance(lo, int) and isinstance(hi, int):
                    nval: Any = int(val)
                else:
                    nval = float(val)
            except (TypeError, ValueError):
                notices.append(f"'{key}' 값 형 오류 — 무시")
                continue
            if nval < lo:
                safe[key] = lo
                notices.append(f"'{key}' {val} → 최소 {lo}로 조정 (안전 범위)")
            elif nval > hi:
                safe[key] = hi
                notices.append(f"'{key}' {val} → 최대 {hi}로 조정 (안전 범위)")
            else:
                safe[key] = nval
        elif isinstance(rule, list):
            if val in rule:
                safe[key] = val
            else:
                safe[key] = rule[0]
                notices.append(
                    f"'{key}' '{val}'은 허용 목록 외 → '{rule[0]}'로 대체"
                )
        else:
            notices.append(f"'{key}' 규칙 형식 미지원 — 무시")

    return safe, notices
