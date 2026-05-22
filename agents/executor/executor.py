"""
agents/executor/executor.py — 3단 Executor (골격, Sprint 2 구현 예정).

역할: PreprocessingPlan의 각 단계 실행. 권한 등급별 분기(L1 즉시 / L2 승인 / L3 차단+백업).
출력: ProcessingResult + Lineage.

⚠️ 수직 슬라이스에서는 미구현. (CLAUDE.md §2)
"""
from __future__ import annotations


async def execute(plan: dict) -> dict:
    # TODO(Sprint2): plan의 각 step을 권한 분기로 실행. L2/L3는 승인 게이트.
    #                모든 변환을 harness.lineage.record()로 기록 강제.
    return {
        "dataset_id": plan.get("dataset_id"),
        "status": "not_implemented",
        "_note": "Executor는 Sprint 2에서 구현.",
    }
