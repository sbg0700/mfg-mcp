"""
agents/validator/validator.py — 4단 Validator (가벼운 실동작).

역할: ExecutionResult를 검증한다. 4단 중 마지막.
  - 모든 'done' 단계에 lineage_id가 있는가 (컴플라이언스: 기록 누락 차단)
  - 실패/대기 단계가 있는가
  - 다음 행동 라우팅 (재시도/사용자개입/완료)

수직 슬라이스: 검증 규칙만. ML 단계 연결은 Sprint 2+.
"""
from __future__ import annotations
from typing import Any


async def validate(execution: dict) -> dict:
    """ExecutionResult 검증 → ValidationReport."""
    results = execution.get("results", [])
    issues: list[str] = []

    done = [r for r in results if r.get("status") == "done"]
    failed = [r for r in results if r.get("status") == "failed"]
    pending = [r for r in results if r.get("status") == "awaiting_approval"]

    # 컴플라이언스 검증: done인데 lineage 누락 = 위반
    for r in done:
        if not r.get("lineage_id"):
            issues.append(f"단계 {r['order']}({r['operation']}): lineage 기록 누락 — 컴플라이언스 위반")

    # 라우팅 결정
    if failed:
        next_action = "retry_or_human"   # 실패 → 재시도 또는 사람 개입
    elif pending:
        next_action = "await_approval"   # 승인 대기 → 사용자 승인 필요
    elif issues:
        next_action = "fix_lineage"      # 기록 누락 → 보정 필요
    else:
        next_action = "ready_for_ml"     # 전부 OK → ML 단계로

    return {
        "dataset_id": execution.get("dataset_id"),
        "passed": len(issues) == 0 and len(failed) == 0,
        "n_done": len(done), "n_failed": len(failed), "n_pending": len(pending),
        "issues": issues,
        "next_action": next_action,
    }
