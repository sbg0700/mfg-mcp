"""
agents/executor/schemas.py — Executor 출력 계약(ExecutionResult).

핵심 (CLAUDE.md §5 가드레일):
  - L1은 즉시 실행. L2/L3는 approval_token 없으면 'awaiting_approval'로 멈춤.
  - 모든 실행 단계는 lineage_id를 남긴다 (재현·책임추적).
  - can_rollback=True면 백업이 있어 되돌릴 수 있다.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class StepResult(BaseModel):
    """한 단계 실행 결과."""
    order: int
    operation: str
    target_column: str | None = None
    permission_level: Literal["L1", "L2", "L3"]
    status: Literal["done", "awaiting_approval", "skipped", "failed"]
    semantic_group: str | None = None  # 우려1: 그룹 단위 작업이면 그룹명
    detail: str = ""                         # 사람이 읽을 결과 설명 (한국어)
    lineage_id: str | None = None            # harness.lineage에 기록된 ID
    can_rollback: bool = False
    before_stats: dict[str, Any] = Field(default_factory=dict)  # 변환 전 요약
    after_stats: dict[str, Any] = Field(default_factory=dict)   # 변환 후 요약


class ExecutionResult(BaseModel):
    """Executor → Validator 로 넘어가는 표준 메시지 (A2A)."""
    dataset_id: str
    results: list[StepResult] = []
    output_path: str | None = None           # 정제된 데이터 저장 위치
    pending_approvals: list[int] = []         # 승인 대기 중인 step order 목록
    all_done: bool = False                    # 모든 단계 완료 여부
    generated_by: str = "executor"
