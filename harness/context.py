"""
harness/context.py — Harness 요소 ② 컨텍스트 관리 (stub).

목적: 큰 데이터를 LLM 컨텍스트에 직접 넣지 않음 → 토큰 폭발 방지.
     MCP가 요약·샘플링만 전달 (현재 tools.sample()이 이 역할 일부 수행).

⚠️ 수직 슬라이스: stub. 256K 윈도우 모니터링·요약 재생성은 Sprint 2.
"""
from __future__ import annotations


def summarize_for_llm(profile: dict, max_chars: int = 1500) -> str:
    """프로파일을 LLM 입력용으로 압축. (지금은 단순 절단)"""
    import json
    s = json.dumps(profile, ensure_ascii=False)
    return s if len(s) <= max_chars else s[:max_chars] + "...(truncated)"
