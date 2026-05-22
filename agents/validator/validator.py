"""
agents/validator/validator.py — 4단 Validator (골격, Sprint 2 구현 예정).

역할: ProcessingResult 검증 + Lineage 기록 확인 + 다음 단계 라우팅.
출력: ValidationReport.

⚠️ 수직 슬라이스에서는 미구현. (CLAUDE.md §2)
"""
from __future__ import annotations


async def validate(result: dict) -> dict:
    # TODO(Sprint2): 결과 무결성 검증 + lineage 누락 여부 확인 + 재시도/사용자개입 결정.
    return {
        "dataset_id": result.get("dataset_id"),
        "status": "not_implemented",
        "_note": "Validator는 Sprint 2에서 구현.",
    }
