"""agents/ml/train_engine.py — STEP 3c 학습 엔진 + OOM 가드 + task 분기.

★생명선★
  - 이 모듈은 LLM을 부르지 않는다. scikit-learn/xgboost 결정론.
  - random_state=42 고정 → 같은 데이터 + 같은 params → 같은 결과 (재현성).
  - task 분기: regression/classification(지도, 타겟+confusion/R²)
              vs anomaly(비지도 IsolationForest, 타겟 없음+score 분포).

OOM 가드 (실데이터 대비 — synthetic은 미발동):
  - 행 > ROW_SAMPLE_THRESHOLD → 결정론 샘플링 (random_state=42)
  - 카테고리 컬럼 unique > CATEGORY_MAX_UNIQUE → one-hot 폭발 방지로 제외
  - 둘 다 notices로 사용자에게 알림 (학습 후 result에 동봉)
"""
from __future__ import annotations
import os
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score, confusion_matrix,
    r2_score, mean_squared_error,
)
import joblib

try:
    from .train_models import TRAIN_MODELS
    from .param_whitelist import validate_and_clamp_params, RANDOM_STATE
except ImportError:
    from train_models import TRAIN_MODELS  # type: ignore[no-redef]
    from param_whitelist import (   # type: ignore[no-redef]
        validate_and_clamp_params, RANDOM_STATE,
    )


# OOM 가드 임계값 (D-143)
CATEGORY_MAX_UNIQUE: int = 100   # ITEM_CODE 등 고차원 카테고리 one-hot 폭발 방지
ROW_SAMPLE_THRESHOLD: int = 200_000  # 실데이터 대비 (synthetic 무발동)

# 모델 저장 루트 (Executor OUTPUT_ROOT와 별도 — 학습 산출물)
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODELS_ROOT: str = os.environ.get(
    "MODELS_ROOT", os.path.join(_REPO_ROOT, "data", "models")
)


# ─────────────────────────────────────────────────────────────────────────
# 1) Feature 준비 + OOM 가드 (결정론)
# ─────────────────────────────────────────────────────────────────────────
def prepare_features(
    df: pd.DataFrame, target_col: str | None, supervised: bool
) -> tuple[pd.DataFrame, pd.Series | None, list[str]]:
    """학습 전 feature 준비 + OOM 가드.
    반환: (X, y or None, notices).
    """
    notices: list[str] = []

    # row 가드 (실데이터 대비)
    original_rows = len(df)
    if original_rows > ROW_SAMPLE_THRESHOLD:
        df = df.sample(ROW_SAMPLE_THRESHOLD, random_state=RANDOM_STATE)
        notices.append(
            f"행 {original_rows:,}+ → {ROW_SAMPLE_THRESHOLD:,} 샘플링 "
            f"(random_state={RANDOM_STATE})"
        )

    # EDA와 동일 기준의 인덱스성·타임스탬프 제외 헬퍼 재사용
    try:
        from eda_engine import _junk_cols  # type: ignore[import-not-found]
    except ImportError:
        from agents.eda.eda_engine import _junk_cols  # type: ignore[no-redef]

    # 타겟 분리 (지도학습만) — ★타깃 결측 행만 제거(feature 결측은 아래 0 대치, 전체행 dropna 금지)
    y: pd.Series | None = None
    if supervised:
        if not target_col or target_col not in df.columns:
            raise ValueError(
                f"지도학습 타겟 컬럼 필요: '{target_col}' 없음 (df cols: "
                f"{list(df.columns)[:10]}...)"
            )
        n_before = len(df)
        df = df[df[target_col].notna()]
        n_drop = n_before - len(df)
        if n_drop:
            notices.append(f"타깃 '{target_col}' 결측 {n_drop:,}행 제외 (feature 결측은 0 대치)")
        y = df[target_col]
        X = df.drop(columns=[target_col])
    else:
        X = df.copy()

    # ★인덱스성·타임스탬프 컬럼 feature 제외 (idx/Unnamed/TimeStamp 등 — 학습 누출 방지)
    junk = [c for c in _junk_cols(X) if c in X.columns]
    if junk:
        X = X.drop(columns=junk)
        notices.append(f"인덱스성·타임스탬프 {len(junk)}개 feature 제외: "
                       f"{', '.join(map(str, junk[:6]))}" + (" …" if len(junk) > 6 else ""))

    # 고차원 카테고리 제외 (OOM 가드)
    cat_cols = X.select_dtypes(include=["object", "category"]).columns
    dropped: list[str] = []
    for c in cat_cols:
        nun = int(X[c].nunique(dropna=True))
        if nun > CATEGORY_MAX_UNIQUE:
            X = X.drop(columns=[c])
            dropped.append(f"{c}({nun})")
    if dropped:
        notices.append(
            f"고차원 카테고리 {len(dropped)}개 제외 — one-hot 폭발 방지: "
            f"{', '.join(dropped)}"
        )

    # 남은 카테고리는 one-hot, 숫자/bool만 통과, 결측은 0으로
    if X.shape[1] > 0:
        X = pd.get_dummies(X, drop_first=True)
    X = X.select_dtypes(include=["number", "bool"]).fillna(0)
    # bool → int (sklearn 호환)
    bool_cols = X.select_dtypes(include=["bool"]).columns
    if len(bool_cols):
        X[bool_cols] = X[bool_cols].astype(int)

    if X.shape[1] == 0:
        raise ValueError(
            "학습 가능한 피처가 없습니다 (모든 컬럼이 가드에 의해 제외됨)"
        )

    return X, y, notices


# ─────────────────────────────────────────────────────────────────────────
# 2) Feature importance (RF/XGB만 — IF는 None)
# ─────────────────────────────────────────────────────────────────────────
def feature_importance(model: Any, columns: list[str]) -> list[dict] | None:
    if not hasattr(model, "feature_importances_"):
        return None
    pairs = list(zip(columns, [float(v) for v in model.feature_importances_]))
    pairs.sort(key=lambda x: -x[1])
    return [{"feature": str(c), "importance": float(v)} for c, v in pairs[:20]]


# ─────────────────────────────────────────────────────────────────────────
# 3) Train (task 분기) — 동기, CPU 결정론
# ─────────────────────────────────────────────────────────────────────────
def run_training(
    dataset_id: str,
    model_name: str,
    target_col: str | None,
    params: dict | None,
    contamination: float = 0.05,
) -> dict:
    """실제 학습 (결정론, LLM 0). 호출부는 사전에 TRAINABLE_MODEL_NAMES 검증 필수.

    반환 dict 키:
      status: "completed" | "error"
      task, model_name, params_used, metrics, notices, model_path
      + task별: confusion_matrix(classification), score_distribution(anomaly)
      + feature_importance: list | None
    """
    # eda_engine은 backend의 sys.path 등록을 통해 import 가능 (D-130 동일 패턴)
    try:
        from eda_engine import load_processed_df  # type: ignore[import-not-found]
    except ImportError:
        from agents.eda.eda_engine import load_processed_df  # type: ignore[no-redef]

    meta = TRAIN_MODELS[model_name]
    df = load_processed_df(dataset_id)
    if df is None:
        return {
            "status": "error",
            "error": f"표준화 데이터 없음: {dataset_id}__processed.parquet",
        }

    # OOM 가드 + feature 준비
    X, y, prep_notices = prepare_features(df, target_col, meta["supervised"])

    # 파라미터 화이트리스트 (clamp + notice)
    safe_params, param_notices = validate_and_clamp_params(model_name, params)
    ModelCls = meta["cls"]
    result: dict = {
        "model_name": model_name,
        "task": meta["task"],
        "notices": prep_notices + param_notices,
        "n_features_used": int(X.shape[1]),
        "feature_names": [str(c) for c in X.columns][:50],
    }

    if meta["task"] == "regression":
        Xtr, Xte, ytr, yte = train_test_split(
            X, y, test_size=0.2, random_state=RANDOM_STATE
        )
        model = ModelCls(**safe_params)
        model.fit(Xtr, ytr)
        pred = model.predict(Xte)
        result["metrics"] = {
            "r2": float(r2_score(yte, pred)),
            "rmse": float(np.sqrt(mean_squared_error(yte, pred))),
            "n_train": int(len(Xtr)),
            "n_test": int(len(Xte)),
        }
        result["feature_importance"] = feature_importance(
            model, list(X.columns)
        )

    elif meta["task"] == "classification":
        # XGBoost는 라벨이 0/1 정수 또는 문자열 → LabelEncoder 적용 (xgb 호환)
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        y_enc = le.fit_transform(y)
        labels_orig = [str(c) for c in le.classes_]

        Xtr, Xte, ytr, yte = train_test_split(
            X, y_enc, test_size=0.2, random_state=RANDOM_STATE, stratify=y_enc
        )
        model = ModelCls(**safe_params)
        model.fit(Xtr, ytr)
        pred = model.predict(Xte)
        metrics = {
            "accuracy": float(accuracy_score(yte, pred)),
            "f1": float(f1_score(yte, pred, average="weighted")),
            "n_train": int(len(Xtr)),
            "n_test": int(len(Xte)),
        }
        # AUC (이진만)
        n_classes = len(labels_orig)
        if n_classes == 2 and hasattr(model, "predict_proba"):
            try:
                proba = model.predict_proba(Xte)[:, 1]
                metrics["auc"] = float(roc_auc_score(yte, proba))
            except Exception:
                pass
        cm = confusion_matrix(yte, pred, labels=list(range(n_classes))).tolist()
        result["metrics"] = metrics
        result["confusion_matrix"] = {
            "labels": labels_orig,
            "matrix": [[int(v) for v in row] for row in cm],
        }
        result["feature_importance"] = feature_importance(
            model, list(X.columns)
        )

    else:  # anomaly (비지도 IsolationForest) — 타겟 없음
        # contamination을 화이트리스트 범위로 한 번 더 안전화
        safe_contam = max(0.001, min(0.5, float(contamination)))
        if "contamination" not in safe_params:
            safe_params["contamination"] = safe_contam
        model = ModelCls(**safe_params)
        model.fit(X)
        scores = model.decision_function(X)
        pred = model.predict(X)   # 1=정상, -1=이상
        n_anom = int((pred == -1).sum())
        counts, edges = np.histogram(scores, bins=30)
        result["metrics"] = {
            "n_total": int(len(X)),
            "n_anomaly": n_anom,
            "anomaly_ratio": round(n_anom / max(1, len(X)), 4),
            "contamination": float(safe_params["contamination"]),
        }
        result["score_distribution"] = {
            "bins": [float(e) for e in edges.tolist()],
            "counts": [int(c) for c in counts.tolist()],
        }
        result["feature_importance"] = None  # IF는 importance 없음

    # 모델 직렬화 (감사 — lineage params에 경로 기록)
    os.makedirs(MODELS_ROOT, exist_ok=True)
    safe_id = "".join(c if c.isalnum() or c in "._-" else "_" for c in dataset_id)
    model_path = os.path.join(MODELS_ROOT, f"{safe_id}__{model_name}.joblib")
    joblib.dump(model, model_path)
    result["model_path"] = model_path
    result["params_used"] = safe_params
    result["status"] = "completed"
    return result
