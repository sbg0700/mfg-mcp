"""
agents/executor/balance_options.py — STEP 2a: 클래스 불균형 옵션 카드 + 결정론 미리보기.

설계 (D-103):
  - 옵션 풀(BALANCE_OPTIONS) = 코드 고정 4종. LLM이 옵션을 생성하지 않음 (환각 방어).
  - 미리보기(compute_balance_preview) = 결정론 산식. LLM 0, pandas value_counts만 사용.
  - 옵션 추가해도 LLM 호출 횟수 불변 → Planner는 "balance_classes 필요" 1회 판단 그대로.

대상 = balance_classes 단일 op (L2). guardrails/OperationType에 새 op 추가 안 함 (Strategy 식별자 방식).
"""
from __future__ import annotations


# ─────────────────────────────────────────────────────────────────────────
# 옵션 풀 (4종, 코드 고정 — LLM 생성 X)
# ─────────────────────────────────────────────────────────────────────────
BALANCE_OPTIONS: list[dict] = [
    {
        "id": "class_weight",
        "label": "클래스 가중치 (class_weight)",
        "description": "데이터를 바꾸지 않고, 학습 시 소수 클래스에 가중치 부여. 가장 안전.",
        "effect": "rows_unchanged",
        "weight": "light",
        "caution": "데이터 분포 그대로. 모델이 가중치를 지원해야 함.",
    },
    {
        "id": "smote",
        "label": "SMOTE 오버샘플링",
        "description": "소수 클래스를 합성 샘플로 늘려 균형. 데이터 증가.",
        "effect": "minority_up",
        "weight": "heavy",
        "caution": "합성 샘플이 추가됨 — 원본 아님. 과적합 주의.",
    },
    {
        "id": "random_under",
        "label": "랜덤 언더샘플링",
        "description": "다수 클래스를 줄여 균형. 데이터 급감.",
        "effect": "majority_down",
        "weight": "heavy",
        "caution": "다수 클래스 정보 손실. 데이터가 적으면 비권장.",
    },
    {
        "id": "skip",
        "label": "보정 안 함 (skip)",
        "description": "불균형을 인지하되 보정하지 않고 그대로 진행.",
        "effect": "none",
        "weight": "none",
        "caution": "모델이 다수 클래스에 편향될 수 있음.",
    },
]

# 환각 방어 필터용 — 허용된 옵션 id 집합. ApproveReq.selected_option 저장 시 이 집합 안의 값만 통과.
BALANCE_OPTION_IDS: frozenset[str] = frozenset(o["id"] for o in BALANCE_OPTIONS)


# ─────────────────────────────────────────────────────────────────────────
# 결정론 미리보기 — 각 옵션 적용 시 행수 추정 (실제 리샘플링 X)
# ─────────────────────────────────────────────────────────────────────────
def compute_balance_preview(df, col: str) -> dict:
    """클래스 분포 기반으로 각 옵션의 결과를 결정론 계산. 미리보기용.

    실제 리샘플링(SMOTE/언더샘플)을 돌리지 않고 행수 변화를 추정한다.
    imbalanced-learn 기본 동작 가정:
      - SMOTE: 모든 클래스를 majority에 맞춤 → 각 클래스 majority행, 총 majority*n_classes행
      - RandomUnderSampler: 모든 클래스를 minority에 맞춤 → 각 minority행, 총 minority*n_classes행
      - class_weight: 행수 유지. sklearn 'balanced' 산식: weight_k = total / (n_classes * count_k)

    LLM 0 — 순수 산수.
    """
    import pandas as pd  # pyright: ignore[reportMissingImports]

    if df is None or col is None or col not in getattr(df, "columns", []):
        return {"applicable": False, "reason": "대상 컬럼 없음", "previews": {}}

    vc = df[col].value_counts(dropna=True)
    counts = {str(k): int(v) for k, v in vc.items()}
    total = int(vc.sum())
    n_classes = int(len(vc))

    if n_classes < 2:
        return {
            "applicable": False,
            "reason": f"단일 클래스(또는 0개) — 불균형 보정 불가 (클래스 수={n_classes})",
            "previews": {},
            "current": {"counts": counts, "total": total},
        }
    if total <= 0:
        return {"applicable": False, "reason": "유효 행 0", "previews": {}}

    majority = int(vc.max())
    minority = int(vc.min())
    minority_ratio = round(minority / total, 4)

    # class_weight (sklearn 'balanced' 산식)
    weights = {str(k): round(total / (n_classes * int(v)), 4) for k, v in vc.items()}
    max_weight = max(weights.values())

    # SMOTE/Under 추정 (imbalanced-learn 기본)
    rows_smote = majority * n_classes
    rows_under = minority * n_classes

    previews = {
        "class_weight": {
            "rows_after": total,
            "rows_delta": 0,
            "weights": weights,
            "detail": (
                f"행수 유지({total}행). 소수 클래스 가중치 최대 ~{max_weight:.2f}배 "
                f"(sklearn class_weight='balanced')."
            ),
        },
        "smote": {
            "rows_after": rows_smote,
            "rows_delta": rows_smote - total,
            "detail": (
                f"소수 클래스 합성 → 각 클래스 {majority}행, 총 {rows_smote}행 "
                f"(+{rows_smote - total})."
            ),
        },
        "random_under": {
            "rows_after": rows_under,
            "rows_delta": rows_under - total,
            "detail": (
                f"다수 클래스 축소 → 각 클래스 {minority}행, 총 {rows_under}행 "
                f"({rows_under - total})."
            ),
        },
        "skip": {
            "rows_after": total,
            "rows_delta": 0,
            "detail": "보정 안 함. 불균형 그대로 유지.",
        },
    }
    return {
        "applicable": True,
        "current": {
            "counts": counts,
            "total": total,
            "n_classes": n_classes,
            "majority": majority,
            "minority": minority,
            "minority_ratio": minority_ratio,
        },
        "previews": previews,
    }
