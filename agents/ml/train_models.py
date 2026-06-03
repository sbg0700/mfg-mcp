"""agents/ml/train_models.py — STEP 3c 학습 가능 모델 매핑 (코드 고정, 환각 방어).

각 모델은 modules.yaml.recommended_models의 한 항목과 1:1.
advisory_only(CNNClassifier 등 VRAM 무거운 딥러닝)는 여기 없음 → 학습 거부.
balance_options(D-104)/chart_types(D-120) 패턴 일관 — frozenset 환각 방어.
"""
from __future__ import annotations

from sklearn.ensemble import (
    RandomForestRegressor,
    RandomForestClassifier,
    IsolationForest,
)
from xgboost import XGBClassifier


# 학습 매핑: name → {cls, task, supervised}
# task: regression(지도) / classification(지도) / anomaly(비지도)
TRAIN_MODELS: dict[str, dict] = {
    "RandomForestRegressor": {
        "cls": RandomForestRegressor,
        "task": "regression",
        "supervised": True,
    },
    "RandomForestClassifier": {
        "cls": RandomForestClassifier,
        "task": "classification",
        "supervised": True,
    },
    "XGBoostClassifier": {
        "cls": XGBClassifier,
        "task": "classification",
        "supervised": True,
    },
    "IsolationForest": {
        "cls": IsolationForest,
        "task": "anomaly",
        "supervised": False,
    },
}

# 환각 방어 필터 — TrainReq.model_name이 이 안에 있어야 학습 가능
# (CNNClassifier 등 advisory_only는 부재 → /train에서 400 거부)
TRAINABLE_MODEL_NAMES: frozenset[str] = frozenset(TRAIN_MODELS.keys())
