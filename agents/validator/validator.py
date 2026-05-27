"""
agents/validator/validator.py — 4단 Validator (검증 강화).

역할: Executor가 한 일이 올바른지 ★사후 검증★한다. Agentic Flow의 마지막 4단.
헌법 "LLM은 제안, 규칙이 결정"의 후반부 — LLM/규칙이 만든 결과를 결정론적으로 검증.

4종 검증:
  1. 컴플라이언스  — 모든 done 단계에 lineage가 있는가 (기록 없는 변환 = 추적 불가 = 위반)
  2. 변환 결과    — 변환이 의도대로 됐는가 (fill_missing 후 결측이 줄었나? normalize 됐나?)
  3. 계획 무결성  — 같은 작업이 중복 제안됐나 (width/height 중복 같은 것), 그룹 이중 처리?
  4. 회귀         — 전처리가 데이터를 망치진 않았나 (행 급감 등)

검증 실패 시 → next_action으로 라우팅 (재시도/사람개입/검토권고).
입력: ExecutionResult + (선택) PreprocessingPlan, DataProfile — 더 풍부한 검증을 위해.
"""
from __future__ import annotations
from typing import Any


def _check_compliance(results: list[dict]) -> list[dict]:
    """검증1 — done 단계에 lineage 누락 = 컴플라이언스 위반."""
    issues = []
    for r in results:
        if r.get("status") == "done" and not r.get("lineage_id"):
            issues.append({
                "kind": "compliance", "severity": "high", "order": r.get("order"),
                "message": f"단계 {r.get('order')}({r.get('operation')}): lineage 기록 누락 — 추적 불가",
            })
    return issues


def _check_transform_result(results: list[dict]) -> list[dict]:
    """검증2 — 변환이 의도대로 됐는가 (before/after 통계 비교)."""
    issues = []
    for r in results:
        if r.get("status") != "done":
            continue
        op = r.get("operation")
        before, after = r.get("before_stats", {}), r.get("after_stats", {})

        if op == "clean_masking":
            if not after:
                issues.append({"kind": "transform", "severity": "medium", "order": r.get("order"),
                               "message": f"단계 {r.get('order')}(clean_masking): 변환 결과 통계 없음 — 정제 여부 불명"})
        if op == "fill_missing":
            nb = before.get("nulls"); na = after.get("nulls")
            if nb is not None and na is not None and na >= nb:
                issues.append({"kind": "transform", "severity": "high", "order": r.get("order"),
                               "message": f"단계 {r.get('order')}(fill_missing): 결측이 줄지 않음 ({nb}→{na}) — 채우기 실패 의심"})
        if op == "normalize_group":
            n = after.get("normalized", 0)
            if n == 0:
                issues.append({"kind": "transform", "severity": "medium", "order": r.get("order"),
                               "message": f"단계 {r.get('order')}(normalize_group): 정규화된 컬럼 0개 — 그룹 처리 실패"})
    return issues


def _check_plan_integrity(results: list[dict], plan: dict | None) -> list[dict]:
    """검증3 — 계획 무결성: 중복 작업 감지 (width/height 중복 같은 것)."""
    issues = []
    steps = (plan or {}).get("steps", results)

    seen: dict[tuple, int] = {}
    for s in steps:
        key = (s.get("operation"), s.get("target_column"))
        if s.get("target_column") is None and s.get("semantic_group"):
            key = (s.get("operation"), "group:" + str(s.get("semantic_group")))
        seen[key] = seen.get(key, 0) + 1

    for (op, target), cnt in seen.items():
        if cnt > 1 and op is not None:
            tgt = target or "(전역)"
            issues.append({"kind": "integrity", "severity": "medium",
                           "message": f"중복 작업 감지: {op} · {tgt} 가 {cnt}회 — 계획에 중복 (정리 권장)"})

    grouped_cols: set = set()
    for s in steps:
        if s.get("operation") == "normalize_group":
            grouped_cols.update(s.get("group_members", []))
    for s in steps:
        if s.get("operation") in ("clean_masking", "fill_missing") and s.get("target_column") in grouped_cols:
            issues.append({"kind": "integrity", "severity": "low",
                           "message": f"'{s.get('target_column')}'가 그룹 정규화와 개별 작업에 동시 포함 — 순서 확인 권장"})
    return issues


def _check_regression(results: list[dict], profile: dict | None) -> list[dict]:
    """검증4 — 회귀: 전처리가 데이터를 망치진 않았나 (행 급감 등)."""
    issues = []
    final_rows = None
    for r in results:
        if r.get("operation") == "compute_stats":
            after = r.get("after_stats", {})
            final_rows = after.get("n_rows")
    orig_rows = (profile or {}).get("n_rows")

    if orig_rows and final_rows:
        loss = (orig_rows - final_rows) / orig_rows
        if loss > 0.5:
            issues.append({"kind": "regression", "severity": "high",
                           "message": f"행 급감: {orig_rows}→{final_rows} ({loss*100:.0f}% 손실) — 데이터 손실 과다"})
    return issues


async def validate(execution: dict, plan: dict | None = None,
                   profile: dict | None = None) -> dict:
    """ExecutionResult 검증 → ValidationReport. 4종 검증 수행.
    plan/profile을 주면 무결성·회귀 검증이 강화됨 (없어도 기본 검증은 동작)."""
    results = execution.get("results", [])

    done = [r for r in results if r.get("status") == "done"]
    failed = [r for r in results if r.get("status") == "failed"]
    pending = [r for r in results if r.get("status") == "awaiting_approval"]

    issues: list[dict] = []
    issues += _check_compliance(results)            # 1. 컴플라이언스
    issues += _check_transform_result(results)      # 2. 변환 결과
    issues += _check_plan_integrity(results, plan)  # 3. 계획 무결성
    issues += _check_regression(results, profile)   # 4. 회귀

    high = [i for i in issues if i.get("severity") == "high"]
    medium = [i for i in issues if i.get("severity") == "medium"]
    low = [i for i in issues if i.get("severity") == "low"]

    if failed or high:
        next_action = "retry_or_human"
    elif pending:
        next_action = "await_approval"
    elif medium:
        next_action = "review_recommended"
    else:
        next_action = "ready_for_ml"

    checks = {
        "compliance": not any(i["kind"] == "compliance" for i in issues),
        "transform": not any(i["kind"] == "transform" for i in issues),
        "integrity": not any(i["kind"] == "integrity" for i in issues),
        "regression": not any(i["kind"] == "regression" for i in issues),
    }

    return {
        "dataset_id": execution.get("dataset_id"),
        "passed": len(high) == 0 and len(failed) == 0,
        "n_done": len(done), "n_failed": len(failed), "n_pending": len(pending),
        "checks": checks,
        "issues": issues,
        "n_high": len(high), "n_medium": len(medium), "n_low": len(low),
        "next_action": next_action,
    }
