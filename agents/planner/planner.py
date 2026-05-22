"""
agents/planner/planner.py — 2단 Planner (골격, Sprint 2 구현 예정).

역할: DataProfile + 사용자 제약 → PreprocessingPlan(각 단계 권한등급 포함).
권한: 계획만 (실행 권한 없음).

⚠️ 수직 슬라이스에서는 미구현. 인터페이스만 고정한다. (CLAUDE.md §2)
"""
from __future__ import annotations
from typing import Any


async def plan(data_profile: dict, constraints: dict[str, Any] | None = None) -> dict:
    # TODO(Sprint2): DataProfile을 보고 결측→이상치→피처엔지니어링 시퀀스 제안.
    #                각 단계에 L1/L2/L3 권한 등급 부여.
    return {
        "dataset_id": data_profile.get("dataset_id"),
        "status": "not_implemented",
        "planned_steps": [],
        "_note": "Planner는 Sprint 2에서 구현. 인터페이스만 고정됨.",
    }
