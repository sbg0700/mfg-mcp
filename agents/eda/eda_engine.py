"""agents/eda/eda_engine.py — STEP 3a Page 5 EDA 결정론 엔진.

★생명선★
  - 이 모듈의 데이터 함수는 LLM을 부르지 않는다 (numpy + pandas만).
  - `_llm_recommend_charts`만 LLM 호출 — 추천(제안). 결과는 호출부에서 CHART_TYPE_IDS 필터.
  - 같은 입력(parquet 바이트 동일) → 같은 출력 (재현성 보장). 랜덤·시각 의존 0.

흐름 (spec STEP_3a §4):
  ① _build_eda_profile     : processed.parquet → 컬럼/카디널리티/범위 메타 (LLM 입력)
  ② _llm_recommend_charts  : LLM이 어떤 차트가 필요한지 추천 (제안 — 환각 방어는 호출부)
  ③ compute_chart_data     : 추천된 chart_type별 결정론 데이터 (numpy+pandas, LLM 0)

데이터 출처: data/processed/{dataset_id}__processed.parquet (Executor가 4단 표준화 후 저장).
부재 시 {available: False} 반환 — graceful degrade.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from .chart_types import CHART_TYPES, CHART_TYPE_IDS, FUNCTION_CHART_GUIDE  # package import (테스트)
except ImportError:
    from chart_types import CHART_TYPES, CHART_TYPE_IDS, FUNCTION_CHART_GUIDE   # flat sys.path (backend)

# Executor와 동일 루트 (PROCESSED_ROOT) — 그렇지 않으면 같은 dataset에 두 폴더가 생김
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_ROOT = os.environ.get("PROCESSED_ROOT", str(_REPO_ROOT / "data" / "processed"))


# ─────────────────────────────────────────────────────────────────────────
# 1) Parquet 로드 (결정론 I/O)
# ─────────────────────────────────────────────────────────────────────────
def processed_path(dataset_id: str) -> str:
    """`{dataset_id}__processed.parquet`의 절대 경로. Executor 저장 규약과 1:1."""
    return os.path.join(OUTPUT_ROOT, f"{dataset_id}__processed.parquet")


def load_processed_df(dataset_id: str) -> pd.DataFrame | None:
    """processed.parquet을 읽어 DataFrame 반환. 없으면 None (graceful)."""
    p = processed_path(dataset_id)
    if not os.path.exists(p):
        return None
    try:
        return pd.read_parquet(p)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────
# 2) 데이터 규모 가드 (spec-2 Part 6-5) — 결정론
# ─────────────────────────────────────────────────────────────────────────
def _apply_row_guard(df: pd.DataFrame, max_rows: int = 1_000_000,
                     target_rows: int = 10_000) -> pd.DataFrame:
    """row > max_rows면 stride 샘플링 (결정론 — 같은 size → 같은 stride)."""
    if len(df) <= max_rows:
        return df
    stride = max(1, len(df) // target_rows)
    return df.iloc[::stride].copy()


def _topn_categories(series: pd.Series, top: int = 50) -> tuple[pd.Series, int]:
    """카테고리 30+ → 상위 top + Others 1행. (counts, others_count) 반환.
    spec-2 Part 6-5 가드 5: 카테고리 30+ 상위 N 노출 + Others."""
    vc = series.value_counts(dropna=True)
    if len(vc) <= top:
        return vc, 0
    head = vc.head(top)
    others = int(vc.iloc[top:].sum())
    return head, others


def _sliding_window_mean_signal(sig: np.ndarray, window: int = 4096) -> np.ndarray:
    """spec-2 Part 6-5 가드 7: 긴 신호는 window 단위로 잘라 평균 (FFT 입력 안정화).
    len <= window면 그대로. 그 외엔 (n_window, window) reshape 후 axis=0 평균."""
    n = len(sig)
    if n <= window:
        return sig.astype(float, copy=False)
    n_win = n // window
    if n_win == 0:
        return sig.astype(float, copy=False)
    trimmed = sig[: n_win * window]
    return trimmed.reshape(n_win, window).mean(axis=0).astype(float)


# ─────────────────────────────────────────────────────────────────────────
# 3) EDA 프로파일 — LLM 판단 입력 (결정론)
# ─────────────────────────────────────────────────────────────────────────
def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if np.isnan(f) or np.isinf(f):
        return None
    return f


def build_eda_profile(dataset_id: str, modality: str) -> dict:
    """processed.parquet을 읽어 LLM 판단용 메타 생성 (결정론, 분포 대략).

    LLM은 이 프로파일을 보고 어떤 chart_type이 필요한지 추천한다.
    """
    df = load_processed_df(dataset_id)
    if df is None:
        return {"available": False, "dataset_id": dataset_id,
                "reason": f"processed parquet not found at {processed_path(dataset_id)}"}

    cols: list[dict] = []
    for c in df.columns:
        s = df[c]
        is_num = bool(pd.api.types.is_numeric_dtype(s))
        info: dict[str, Any] = {
            "name": str(c),
            "dtype": str(s.dtype),
            "is_numeric": is_num,
            "n_unique": int(s.nunique(dropna=True)),
            "null_count": int(s.isna().sum()),
        }
        if is_num:
            s_nn = s.dropna()
            if len(s_nn):
                info["range"] = [_safe_float(s_nn.min()), _safe_float(s_nn.max())]
                info["mean"] = _safe_float(s_nn.mean())
                info["std"] = _safe_float(s_nn.std())
        else:
            # 카테고리 후보 — 상위 5 미리보기
            vc = s.value_counts(dropna=True).head(5)
            info["top_values"] = {str(k): int(v) for k, v in vc.items()}
        cols.append(info)

    return {
        "available": True,
        "dataset_id": dataset_id,
        "modality": modality,
        "rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "columns": cols,
    }


# ─────────────────────────────────────────────────────────────────────────
# 4) LLM 차트 추천 (제안) — 환각 방어는 호출부에서 CHART_TYPE_IDS 필터
# ─────────────────────────────────────────────────────────────────────────
def _slim_stage_chain(stage_chain: list[dict] | None) -> list[dict]:
    """ctx.stage_chain → EDA LLM payload용 slim 투영 (결정론, BLUEPRINT §2.3 / D-170).

    main_findings 생략(key_findings와 중복). stage_order 포함(흐름 순서 — DL-3.5 ordinal
    교훈 일관, 신규 계산 0·원본 필드 전파일 뿐). LLM 0 — 원본 필드 추리기만.
    """
    return [
        {
            "stage_order": s.get("stage_order"),
            "node_id": s.get("node_id"),
            "downstream_implication": s.get("downstream_implication"),
        }
        for s in (stage_chain or [])
    ]


async def llm_recommend_charts(profile: dict, ctx: dict, function_axis: str,
                               modality: str, model: str | None) -> dict:
    """LLM이 데이터 특성 보고 필요한 차트 추천 (제안). 1B-3c /questions 패턴.

    반환: {"_llm_failed": True, ...} 또는 {"recommendations": [...]} dict.
    호출부는 _llm_failed 체크 후, recommendations를 CHART_TYPE_IDS + modality로 필터.
    """
    from llm import generate_json   # backend가 sys.path에 backend/ 등록 (main.py 상단)

    system = (
        "You are a manufacturing data EDA analyst. "
        "Look at the parquet profile + analysis purpose + key_findings, "
        "and recommend which EDA charts are needed. "
        f"Allowed chart_type values (HARD WHITELIST — do NOT invent): {sorted(CHART_TYPE_IDS)}. "
        "Each item: {chart_type, target_column (if applicable), label_column (if boxplot_by_label), reason_ko}. "
        "Return ONLY JSON: {\"recommendations\":[{...}, ...]}. "
        "Max 4 items. Pick those that match the data (numeric/categorical/signal) and the purpose. "
        "slim_stage_chain encodes this dataset's position in its process flow (stage_order) and its downstream impact (downstream_implication). Use it as flow context when interpreting EDA, but it must not affect any chart or statistical computation."
    )
    # 키 컬럼 필요 시 LLM이 골라낼 수 있도록 컬럼 종류·카디널리티 제공
    user = json.dumps({
        "profile": profile,
        "function_axis": function_axis,
        "function_guide_hint": FUNCTION_CHART_GUIDE.get(function_axis, {}),
        "modality": modality,
        "key_findings_sample": (ctx.get("key_findings") or [])[:10],
        "user_intent": ctx.get("user_intent"),
        "slim_stage_chain": _slim_stage_chain(ctx.get("stage_chain")),  # D-170/BLUEPRINT §2.3 — 흐름 컨텍스트(해석용). compute_chart_data 미참조(D-59).
    }, ensure_ascii=False, default=str)

    return await generate_json(user, system=system, model=model)


def fallback_charts_from_guide(function_axis: str, modality: str) -> list[dict]:
    """LLM 실패/빈 결과 시 사용. function 기본 가이드의 primary 중 modality 적합만."""
    guide = FUNCTION_CHART_GUIDE.get(function_axis, {})
    out: list[dict] = []
    for ct in guide.get("primary", []) + guide.get("secondary", []):
        spec = CHART_TYPES.get(ct)
        if not spec:
            continue
        if modality not in spec["modality"]:
            continue
        out.append({"chart_type": ct, "reason_ko": "LLM 미응답 — function 기본 가이드 폴백",
                    "fallback": True})
        if len(out) >= 2:
            break
    return out


def filter_recommendations(recs: list[dict], modality: str) -> list[dict]:
    """환각 방어 + modality 적합성 필터. 허용 chart_type만 통과."""
    out: list[dict] = []
    seen: set[str] = set()
    for r in recs or []:
        if not isinstance(r, dict):
            continue
        ct = r.get("chart_type")
        if ct not in CHART_TYPE_IDS:
            continue
        if modality not in CHART_TYPES[ct]["modality"]:
            continue
        if ct in seen:
            continue   # 중복 chart_type 1회만
        seen.add(ct)
        out.append({
            "chart_type": ct,
            "target_column": r.get("target_column"),
            "label_column": r.get("label_column"),
            "reason_ko": str(r.get("reason_ko") or r.get("reason") or ""),
        })
    return out


# ─────────────────────────────────────────────────────────────────────────
# 5) 결정론 차트 데이터 계산 (LLM 0)
# ─────────────────────────────────────────────────────────────────────────
def _pick_numeric_column(df: pd.DataFrame, hint: str | None) -> str | None:
    if hint and hint in df.columns and pd.api.types.is_numeric_dtype(df[hint]):
        return hint
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            return str(c)
    return None


def _pick_categorical_column(df: pd.DataFrame, hint: str | None) -> str | None:
    if hint and hint in df.columns:
        return hint
    # 카디널리티 낮은 컬럼 우선 (라벨 후보)
    candidates = [(c, df[c].nunique(dropna=True)) for c in df.columns
                  if not pd.api.types.is_numeric_dtype(df[c])]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1])
    return str(candidates[0][0])


def compute_chart_data(df: pd.DataFrame, chart_type: str, spec: dict,
                       modality: str) -> dict:
    """추천된 1개 차트의 데이터 결정론 계산. LLM 0, numpy+pandas만."""
    df = _apply_row_guard(df)   # 가드: row > 1M → stride 샘플링 (synthetic은 무발동)

    if chart_type == "histogram":
        col = _pick_numeric_column(df, spec.get("target_column"))
        if not col:
            return {"error": "no numeric column"}
        s = df[col].dropna().astype(float)
        if len(s) == 0:
            return {"error": "empty after dropna", "column": col}
        counts, edges = np.histogram(s, bins="auto")
        return {
            "column": col,
            "bins": [float(x) for x in edges.tolist()],
            "counts": [int(x) for x in counts.tolist()],
            "stats": {"mean": float(s.mean()), "std": float(s.std()),
                      "min": float(s.min()), "max": float(s.max()), "n": int(len(s))},
        }

    if chart_type == "boxplot_by_label":
        target = _pick_numeric_column(df, spec.get("target_column"))
        label = _pick_categorical_column(df, spec.get("label_column"))
        if not target:
            return {"error": "no numeric target"}
        groups: dict[str, dict] = {}
        if label and label in df.columns:
            grouped = df.groupby(label)[target]
        else:
            grouped = [("all", df[target])]
            label = None
        # 카테고리 30+ 가드: 상위 30개 그룹만
        if label is not None:
            count_per_group = df[label].value_counts(dropna=True).head(30).index
            grouped = [(g, df.loc[df[label] == g, target]) for g in count_per_group]
        for g, sub in grouped:
            sub_nn = sub.dropna().astype(float)
            if len(sub_nn) == 0:
                continue
            q = np.percentile(sub_nn, [0, 25, 50, 75, 100])
            groups[str(g)] = {
                "min": float(q[0]), "q1": float(q[1]), "median": float(q[2]),
                "q3": float(q[3]), "max": float(q[4]), "n": int(len(sub_nn)),
            }
        return {"target_column": target, "label_column": label, "groups": groups}

    if chart_type == "fft_spectrum":
        col = _pick_numeric_column(df, spec.get("target_column"))
        if not col:
            return {"error": "no numeric column"}
        sig = df[col].dropna().to_numpy(dtype=float)
        if len(sig) < 8:
            return {"error": "signal too short", "column": col, "n": int(len(sig))}
        sig = _sliding_window_mean_signal(sig)
        freqs = np.fft.rfftfreq(len(sig))
        mag = np.abs(np.fft.rfft(sig))
        # 너무 길면 상위 512 bin (시각화용)
        if len(freqs) > 512:
            step = len(freqs) // 512
            freqs = freqs[::step]
            mag = mag[::step]
        return {
            "column": col,
            "freqs": [float(x) for x in freqs.tolist()],
            "magnitude": [float(x) for x in mag.tolist()],
            "stats": {"window_len": int(len(sig)), "peak_freq": float(freqs[int(np.argmax(mag))])},
        }

    if chart_type == "rms_trend":
        col = _pick_numeric_column(df, spec.get("target_column"))
        if not col:
            return {"error": "no numeric column"}
        sig = df[col].dropna().to_numpy(dtype=float)
        if len(sig) < 8:
            return {"error": "signal too short"}
        window = max(8, len(sig) // 64)
        n_win = len(sig) // window
        if n_win == 0:
            return {"error": "window too large"}
        trimmed = sig[: n_win * window].reshape(n_win, window)
        rms = np.sqrt(np.mean(trimmed ** 2, axis=1))
        return {
            "column": col,
            "window_size": int(window),
            "rms": [float(x) for x in rms.tolist()],
            "indices": list(range(int(n_win))),
        }

    if chart_type == "class_distribution":
        col = _pick_categorical_column(df, spec.get("target_column"))
        if not col:
            return {"error": "no categorical column"}
        top, others = _topn_categories(df[col], top=50)
        out = {
            "column": col,
            "labels": [str(k) for k in top.index.tolist()],
            "counts": [int(v) for v in top.tolist()],
        }
        if others:
            out["others_count"] = others
        return out

    if chart_type == "pareto":
        col = _pick_categorical_column(df, spec.get("target_column"))
        if not col:
            return {"error": "no categorical column"}
        top, others = _topn_categories(df[col], top=50)
        total = float(top.sum()) + others
        if total <= 0:
            return {"error": "empty"}
        cum = (top.cumsum() / total * 100).tolist()
        out = {
            "column": col,
            "labels": [str(k) for k in top.index.tolist()],
            "counts": [int(v) for v in top.tolist()],
            "cumulative_pct": [float(x) for x in cum],
        }
        if others:
            out["others_count"] = others
        return out

    if chart_type == "correlation_bar":
        target = spec.get("target_column")
        num = df.select_dtypes(include=[np.number]).dropna(axis=1, how="all")
        if num.shape[1] < 2:
            return {"error": "need >= 2 numeric columns"}
        if not target or target not in num.columns:
            # 분산 가장 큰 numeric을 잠정 타겟으로
            stds = num.std(numeric_only=True)
            target = str(stds.idxmax())
        corr = num.corr(numeric_only=True)[target].drop(target).abs().sort_values(ascending=False)
        top = corr.head(20)
        return {
            "target_column": str(target),
            "columns": [str(c) for c in top.index.tolist()],
            "values": [float(v) for v in top.tolist()],
        }

    if chart_type == "scatter":
        num = df.select_dtypes(include=[np.number]).dropna(axis=1, how="all")
        if num.shape[1] < 2:
            return {"error": "need >= 2 numeric columns"}
        x_col = spec.get("target_column")
        y_col = spec.get("label_column")
        if not (x_col in num.columns):
            # 분산 큰 두 컬럼
            stds = num.std(numeric_only=True).sort_values(ascending=False)
            x_col = str(stds.index[0])
        if not (y_col in num.columns) or y_col == x_col:
            stds = num.std(numeric_only=True).drop(x_col, errors="ignore").sort_values(ascending=False)
            y_col = str(stds.index[0]) if len(stds) else None
        if not y_col:
            return {"error": "no second numeric column"}
        # 점이 너무 많으면 5000개로 stride
        xs = df[x_col].astype(float).to_numpy()
        ys = df[y_col].astype(float).to_numpy()
        mask = ~(np.isnan(xs) | np.isnan(ys))
        xs, ys = xs[mask], ys[mask]
        if len(xs) > 5000:
            stride = len(xs) // 5000
            xs = xs[::stride]
            ys = ys[::stride]
        return {
            "x_column": str(x_col), "y_column": str(y_col),
            "x": [float(v) for v in xs.tolist()],
            "y": [float(v) for v in ys.tolist()],
            "n": int(len(xs)),
        }

    return {"error": f"unknown chart_type: {chart_type}"}


# ─────────────────────────────────────────────────────────────────────────
# 6) 자연어 요약 (LLM) — 가치 ④ (spec-2 Part 6-6)
# ─────────────────────────────────────────────────────────────────────────
async def llm_chart_summary(chart_type: str, stats: dict, findings: list[dict],
                            user_purpose: str | None, model: str | None) -> dict:
    """차트 stats + findings → 한국어 2~3문장 요약 (LLM, 환각 방어: 숫자 그대로).

    "새 추론·새 숫자 금지" — 입력값만 인용. JSON {summary, key_points}.
    """
    from llm import generate_json

    system = (
        "You are a manufacturing data analysis explainer (Korean). "
        "Summarize the given chart stats + findings in 2~3 Korean sentences. "
        "STRICT RULES: cite numbers EXACTLY from input; do not infer new numbers; "
        "do not propose actions outside the input. "
        "Respond ONLY in JSON: {\"summary\": \"...\", \"key_points\": [\"...\", \"...\"]}."
    )
    user = json.dumps({
        "chart_type": chart_type,
        "stats": stats,
        "findings_sample": (findings or [])[:5],
        "user_purpose": user_purpose,
    }, ensure_ascii=False, default=str)
    return await generate_json(user, system=system, model=model)
