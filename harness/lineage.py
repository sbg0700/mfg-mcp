"""
harness/lineage.py — Harness 요소 ④ Lineage 추적 (SI 컴플라이언스 핵심).

목적: 모든 변환의 재현 가능성 + 책임 추적.
수직 슬라이스: 인메모리 저장 (실동작). Sprint 2에서 PostgreSQL schema:lineage로 이전.

스키마(인계서 [7-4]):
  id, dataset_id, source_column, transformation_type,
  transformation_params, result_column, applied_at, applied_by_agent,
  user_approval_id, can_rollback
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any

_STORE: dict[str, list[dict[str, Any]]] = defaultdict(list)


def record(dataset_id: str, transformation_type: str,
           source_column: str | None = None, result_column: str | None = None,
           params: dict | None = None, applied_by_agent: str = "system",
           user_approval_id: str | None = None, can_rollback: bool = True) -> str:
    entry = {
        "id": str(uuid.uuid4()),
        "dataset_id": dataset_id,
        "source_column": source_column,
        "transformation_type": transformation_type,
        "transformation_params": params or {},
        "result_column": result_column,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "applied_by_agent": applied_by_agent,
        "user_approval_id": user_approval_id,
        "can_rollback": can_rollback,
    }
    _STORE[dataset_id].append(entry)
    return entry["id"]


def get_chain(dataset_id: str) -> list[dict[str, Any]]:
    return list(_STORE.get(dataset_id, []))
