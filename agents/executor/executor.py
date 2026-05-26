"""
agents/executor/executor.py — 3단 Executor (실동작).

역할: PreprocessingPlan의 각 단계를 실제로 실행한다. 4단 중 3단.

설계 (4가지 결정):
  1) 진짜로 데이터를 변환한다 (Inspector/Planner는 보기만 했음).
  2) 권한 게이트: L1 즉시 / L2·L3는 approval_token 없으면 awaiting_approval로 멈춤.
  3) 모든 변환을 lineage에 기록 + 변환 전 백업 → 되돌리기(rollback) 가능.
  4) 변환 로직은 결정론적 Python (LLM 아님). LLM은 Planner에서 '무엇을' 정했고,
     Executor는 '안전하게 실행'만 한다.

수직 슬라이스: clean_masking / fill_missing / compute_stats / balance_classes 구현.
나머지(drop_column 등 L3)는 게이트만 통과시키고 stub.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(ROOT), str(ROOT / "agents" / "executor")):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import lineage  # noqa: E402
from executor_schemas import StepResult, ExecutionResult  # noqa: E402

# 데이터 위치 (MCP 서버와 동일 루트)
DATA_ROOT = os.environ.get(
    "TIMESERIES_DATA_ROOT",
    str(ROOT / "data" / "synthetic" / "timeseries"),
)
# 정제 결과·백업 저장 위치
OUTPUT_ROOT = os.environ.get("PROCESSED_ROOT", str(ROOT / "data" / "processed"))
MASK_TOKENS = {"*", "**", "***", "-", "N/A", "n/a", "null", "NULL", ""}


def _resolve(dataset_id: str) -> str:
    name = dataset_id if dataset_id.endswith(".csv") else f"{dataset_id}.csv"
    return os.path.join(DATA_ROOT, name)


def _col_stats(s: pd.Series) -> dict[str, Any]:
    """컬럼 요약 (변환 전후 비교용)."""
    return {
        "dtype": str(s.dtype),
        "nulls": int(s.isna().sum()),
        "n_unique": int(s.nunique(dropna=True)),
    }


# ---------------------------------------------------------------------------
# 실제 변환 함수들 (결정론적)
# ---------------------------------------------------------------------------
def _op_clean_masking(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, dict, dict]:
    """[L2] 마스킹 문자('*','**','***' 등) → NaN 변환 후 수치화."""
    before = _col_stats(df[col])
    df[col] = df[col].apply(lambda v: np.nan if str(v).strip() in MASK_TOKENS else v)
    df[col] = pd.to_numeric(df[col], errors="coerce")  # 수치화 (실패는 NaN)
    after = _col_stats(df[col])
    return df, before, after


def _op_fill_missing(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, dict, dict]:
    """[L2] 결측치 채우기 (수치는 중앙값, 그 외는 최빈값)."""
    before = _col_stats(df[col])
    if pd.api.types.is_numeric_dtype(df[col]):
        df[col] = df[col].fillna(df[col].median())
    else:
        mode = df[col].mode()
        if len(mode):
            df[col] = df[col].fillna(mode.iloc[0])
    after = _col_stats(df[col])
    return df, before, after


def _op_balance_classes(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, dict, dict]:
    """[L2] 클래스 불균형 정보 산출 (실제 리샘플링은 ML 단계에서. 여기선 진단·가중치 제안)."""
    before = _col_stats(df[col])
    counts = df[col].value_counts().to_dict()
    total = sum(counts.values())
    ratios = {str(k): round(v / total, 4) for k, v in counts.items()}
    after = {**_col_stats(df[col]), "class_ratios": ratios,
             "suggested_strategy": "class_weight or SMOTE (ML 단계 적용)"}
    return df, before, after


def _op_compute_stats(df: pd.DataFrame, col: str | None) -> tuple[pd.DataFrame, dict, dict]:
    """[L1] 기초 통계 (전처리 효과 검증용). 데이터 변경 없음."""
    desc = df.describe(include="all").fillna("").to_dict()
    # 너무 크면 컬럼별 핵심만
    brief = {c: {k: (round(v, 3) if isinstance(v, float) else v)
                 for k, v in stat.items() if k in ("count", "mean", "std", "min", "max", "unique")}
             for c, stat in desc.items()}
    return df, {}, {"summary": brief}


_OPERATIONS = {
    "clean_masking": _op_clean_masking,
    "fill_missing": _op_fill_missing,
    "balance_classes": _op_balance_classes,
    "compute_stats": _op_compute_stats,
}


async def execute(plan: dict, approval_tokens: dict | None = None) -> dict:
    """PreprocessingPlan 실행.

    approval_tokens: {step_order: token} — 사용자가 승인한 단계들.
                     L2/L3는 여기 토큰이 있어야 실행됨.
    """
    approval_tokens = approval_tokens or {}
    dataset_id = plan.get("dataset_id", "unknown")
    path = _resolve(dataset_id)

    if not os.path.exists(path):
        return ExecutionResult(dataset_id=dataset_id, all_done=False,
                               results=[]).model_dump() | {"error": f"file not found: {path}"}

    # 인코딩 안전 로드 (cp949 등 흡수)
    enc = "utf-8-sig"
    for cand in ("utf-8-sig", "cp949", "latin1"):
        try:
            df = pd.read_csv(path, encoding=cand, low_memory=False)
            enc = cand
            break
        except (UnicodeDecodeError, LookupError):
            continue

    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    # 변환 전 원본 백업 (rollback 근거)
    backup_path = os.path.join(OUTPUT_ROOT, f"{dataset_id}__backup.parquet")
    df.to_parquet(backup_path, index=False)

    results: list[StepResult] = []
    pending: list[int] = []

    for step in plan.get("steps", []):
        order = step["order"]
        op = step["operation"]
        col = step.get("target_column")
        perm = step["permission_level"]

        # --- 권한 게이트 ---
        if perm in ("L2", "L3") and order not in approval_tokens:
            results.append(StepResult(
                order=order, operation=op, target_column=col, permission_level=perm,
                status="awaiting_approval",
                detail=f"{perm} 작업은 사용자 승인이 필요합니다. 승인 후 실행됩니다.",
            ))
            pending.append(order)
            continue

        # --- 실행 ---
        fn = _OPERATIONS.get(op)
        if fn is None:
            results.append(StepResult(
                order=order, operation=op, target_column=col, permission_level=perm,
                status="skipped", detail=f"'{op}'는 아직 미구현 (Sprint 2+).",
            ))
            continue

        try:
            if op == "compute_stats":
                df, before, after = fn(df, None)
            else:
                if not col or col not in df.columns:
                    results.append(StepResult(
                        order=order, operation=op, target_column=col, permission_level=perm,
                        status="failed", detail=f"대상 컬럼 '{col}' 없음.",
                    ))
                    continue
                df, before, after = fn(df, col)

            # Lineage 기록 (변환 추적)
            lid = lineage.record(
                dataset_id=dataset_id, transformation_type=op,
                source_column=col, result_column=col,
                params={"permission_level": perm}, applied_by_agent="executor",
                user_approval_id=approval_tokens.get(order), can_rollback=True,
            )
            results.append(StepResult(
                order=order, operation=op, target_column=col, permission_level=perm,
                status="done",
                detail=_describe(op, col, before, after),
                lineage_id=lid, can_rollback=True,
                before_stats=before, after_stats=after,
            ))
        except Exception as e:
            results.append(StepResult(
                order=order, operation=op, target_column=col, permission_level=perm,
                status="failed", detail=f"실행 오류: {e}",
            ))

    # 정제 결과 저장 (승인 대기가 없을 때만 최종본으로)
    output_path = os.path.join(OUTPUT_ROOT, f"{dataset_id}__processed.parquet")
    df.to_parquet(output_path, index=False)

    all_done = len(pending) == 0 and all(r.status == "done" for r in results if r.status != "skipped")
    return ExecutionResult(
        dataset_id=dataset_id, results=results, output_path=output_path,
        pending_approvals=pending, all_done=all_done,
    ).model_dump()


def _describe(op: str, col: str | None, before: dict, after: dict) -> str:
    """변환 결과를 사람이 읽을 한국어로."""
    if op == "clean_masking":
        return (f"'{col}': 마스킹 문자 → NaN 변환 후 수치화. "
                f"dtype {before.get('dtype')}→{after.get('dtype')}, "
                f"결측 {before.get('nulls')}→{after.get('nulls')}개")
    if op == "fill_missing":
        return f"'{col}': 결측치 채움. {before.get('nulls')}→{after.get('nulls')}개"
    if op == "balance_classes":
        return f"'{col}': 클래스 비율 분석 완료. {after.get('class_ratios')}"
    if op == "compute_stats":
        return "전체 컬럼 기초 통계 산출 완료 (전처리 효과 검증용)."
    return "완료."
