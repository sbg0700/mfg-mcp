"""
harness/schema_validation.py — Harness 요소 ① 도구 스키마 검증.

목적: LLM의 잘못된 MCP 도구 호출을 사전 차단.
수직 슬라이스: 경량 검증만. (pydantic 모델 강제는 Sprint 2)
"""
from __future__ import annotations
from typing import Any

VALID_TOOLS = {"detect_encoding", "list_columns", "get_schema", "sample",
               "check_constraints", "apply_preprocessing", "lineage"}


def validate_tool_call(tool_name: str, args: dict[str, Any]) -> tuple[bool, str]:
    """호출 도구명이 표준 7종에 속하는지 + 필수 인자 존재 여부 검증."""
    if tool_name not in VALID_TOOLS:
        return False, f"unknown tool: {tool_name} (허용: {sorted(VALID_TOOLS)})"
    if tool_name != "detect_encoding" and "dataset_id" not in args:
        return False, f"{tool_name} requires 'dataset_id'"
    return True, "ok"
