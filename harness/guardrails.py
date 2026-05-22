"""
harness/guardrails.py — Harness 요소 ③ 가드레일 (3-tier 권한 모델).

CLAUDE.md §5의 L1/L2/L3 분기 로직.
"""
from __future__ import annotations
from enum import Enum


class Permission(str, Enum):
    L1 = "L1"  # 자동 (메타·스키마·인코딩·통계)
    L2 = "L2"  # 제안+승인 (결측·이상치·피처)
    L3 = "L3"  # 차단+백업 (컬럼 삭제·라벨 재정의)


# 작업 유형 → 권한 등급 매핑 (확장 가능)
OPERATION_PERMISSION = {
    "detect_encoding": Permission.L1,
    "compute_stats": Permission.L1,
    "fill_missing": Permission.L2,
    "remove_outlier": Permission.L2,
    "create_feature": Permission.L2,
    "drop_column": Permission.L3,
    "relabel": Permission.L3,
    "merge_external": Permission.L3,
}


def needs_approval(operation: str) -> bool:
    """해당 작업이 사용자 승인을 필요로 하는가 (L2/L3)?"""
    return OPERATION_PERMISSION.get(operation, Permission.L3) != Permission.L1
