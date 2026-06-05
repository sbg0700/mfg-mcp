"""
agents/planner/schemas.py — Planner 출력 계약(PreprocessingPlan).

핵심 설계 (CLAUDE.md §5 가드레일과 연결):
  - Planner는 '계획'만 만든다. 실행은 Executor.
  - 각 단계(PlanStep)는 권한 등급(L1/L2/L3)을 반드시 포함한다.
    → 이게 있어야 Executor가 "자동 실행 / 승인 대기 / 차단+백업" 분기를 할 수 있고,
      프론트가 "이 단계는 승인 필요" UI를 자동으로 붙일 수 있다.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


# 전처리 작업 유형 (확장 가능). harness/guardrails.py의 OPERATION_PERMISSION과 짝을 이룬다.
OperationType = Literal[
    "detect_encoding",   # L1 — 인코딩 정규화 (cp949 → utf-8)
    "reparse_header",    # L1 — 헤더 없는 데이터 재파싱
    "compute_stats",     # L1 — 기초 통계
    "clean_masking",     # L2 — 마스킹 문자('*','**') → NaN 변환 후 처리
    "fill_missing",      # L2 — 결측치 채우기
    "remove_outlier",    # L2 — 이상치 제거
    "create_feature",    # L2 — 피처 생성
    "drop_column",       # L3 — 컬럼 삭제
    "relabel",           # L3 — 라벨 재정의
    "balance_classes",   # L2 — 클래스 불균형 보정
    "normalize_group",   # L2 — ★의미 그룹 단위 정규화 (우려1: 시퀀스/프로파일 보존)
]


class PlanStep(BaseModel):
    """전처리 계획의 한 단계."""
    order: int                                  # 실행 순서 (1부터)
    operation: OperationType                    # 작업 유형
    target_column: str | None = None            # 대상 컬럼 (전체면 None)
    permission_level: Literal["L1", "L2", "L3"] # 권한 등급 (가드레일이 결정)
    rationale: str = ""                         # 왜 이 단계가 필요한가 (LLM 설명, 한국어)
    params: dict[str, Any] = Field(default_factory=dict)
    # ★우려1: 의미 그룹 단위 작업이면 그룹명·멤버·전략을 담는다 (컬럼 1개씩 아님)
    semantic_group: str | None = None
    group_members: list[str] = Field(default_factory=list)
    strategy: str | None = None
    # ★STEP 2a (D-103): 옵션 카드 — strategy 식별자 방식.
    # available_options: 코드 고정 옵션 풀(LLM 생성 X). preview: 결정론 미리보기(LLM 0).
    # balance_classes에만 채워지고 다른 step은 빈 채로 — 회귀 0.
    available_options: list[dict] = Field(default_factory=list)
    preview: dict[str, Any] = Field(default_factory=dict)

    @property
    def step_key(self) -> str:
        """순서(order)와 무관한 안정적 식별자. 승인 매칭에 사용.
        order는 LLM이 매번 다르게 배열할 수 있어 승인이 어긋남 → operation+대상으로 고정.
        ★STEP 2a: 옵션 선택은 step_key를 바꾸지 않음 — 기존 승인 누적과 호환.★"""
        target = self.semantic_group or self.target_column or "global"
        return f"{self.operation}:{target}"


class PreprocessingPlan(BaseModel):
    """Planner → Executor 로 넘어가는 표준 메시지 (A2A)."""
    dataset_id: str
    steps: list[PlanStep] = []
    summary: str = ""                           # 계획 전체 요약 (사람이 읽을 한국어)
    requires_approval: bool = False             # L2/L3가 하나라도 있으면 True
    generated_by: str = "planner"
