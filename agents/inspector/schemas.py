"""agents/inspector/schemas.py — Inspector 출력 계약(DataProfile)."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    null_count: int = 0
    n_unique: int = 0
    mixed_dtype_suspected: bool = False


class DataProfile(BaseModel):
    """Inspector → Planner 로 넘어가는 표준 메시지 (A2A)."""
    dataset_id: str
    encoding: str | None = None
    n_rows: int | None = None
    n_cols: int | None = None
    columns: list[ColumnInfo] = []
    deterministic_flags: list[str] = []
    llm_interpretation: dict[str, Any] = {}
