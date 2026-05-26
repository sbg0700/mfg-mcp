"""
agents/inspector/inspector.py
=============================
Inspector 에이전트 — 4단 파이프라인의 1단 (CLAUDE.md §5, 권한 L1).

역할: raw 데이터를 받아 메타데이터·스키마·인코딩·기초 통계를 추출하고(=결정론적),
      그 위에 LLM(Gemma)이 "해석"을 얹는다(=판단).

설계 포인트 (왜 이렇게):
  - 무거운 추론은 LLM에 시키지 않는다. 프로파일링은 MCP 도구가 결정론적으로 한다.
  - LLM은 그 프로파일을 보고 (1) 모달리티 추정 (2) 의심스러운 점 (3) 권장 다음 단계
    를 자연어/구조화로 제시한다. → E4B 같은 작은 모델로도 안정적으로 동작.

출력: DataProfile (schemas.py 참조)
"""

from __future__ import annotations
import os
import json
import httpx

# MCP timeseries 서버 주소 (도커 내부망)
MCP_TIMESERIES = os.environ.get("MCP_TIMESERIES_URL", "http://mcp-timeseries:8101")


async def _mcp_get(path: str, **params) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{MCP_TIMESERIES}{path}", params=params)
        r.raise_for_status()
        return r.json()


async def inspect(dataset_id: str, model: str | None = None) -> dict:
    """dataset_id를 받아 DataProfile을 생성한다.

    1) MCP 도구(결정론적)로 프로파일 수집
    2) LLM(Gemma)에게 해석 요청
    """
    # ---- 1. 결정론적 프로파일 수집 (MCP 도구 호출) ----
    columns = await _mcp_get("/list_columns", dataset_id=dataset_id)
    schema = await _mcp_get("/get_schema", dataset_id=dataset_id)
    sample = await _mcp_get("/sample", dataset_id=dataset_id, n=5)
    encoding = await _mcp_get("/detect_encoding", dataset_id=dataset_id)

    # 결정론적으로 감지된 '챌린지 신호' (LLM 없이도 잡히는 것)
    flags = []
    if encoding.get("encoding") in ("cp949", "euc-kr"):
        flags.append("non-utf8 encoding (한글 인코딩)")
    if columns.get("read_notes", {}).get("headerless"):
        flags.append("headerless (헤더가 데이터 행)")
    for c in columns.get("columns", []):
        if c.get("mixed_dtype_suspected"):
            flags.append(f"mixed dtype in '{c['name']}' (마스킹/혼재 의심)")

    profile = {
        "dataset_id": dataset_id,
        "encoding": encoding.get("encoding"),
        "n_rows": columns.get("n_rows"),
        "n_cols": columns.get("n_cols"),
        "columns": columns.get("columns"),
        "sample_rows": sample.get("rows"),
        "deterministic_flags": flags,
    }

    # ---- 2. LLM 해석 (Gemma) ----
    # 큰 데이터를 통째로 넣지 않는다 (Harness §7-2). 요약만 전달.
    from llm import generate  # backend/llm.py (PYTHONPATH로 연결)

    col_brief = ", ".join(
        f"{c['name']}({c['dtype']})" for c in (columns.get("columns") or [])[:20]
    )
    system = (
        "You are a manufacturing data inspector. Given a dataset profile, "
        "respond ONLY in compact JSON with keys: "
        "modality_guess (one of: timeseries, inspection-image, event-log, order), "
        "concerns (array of short Korean strings), "
        "recommended_next_steps (array of short Korean strings). "
        "Base your judgment only on the provided profile."
    )
    prompt = (
        f"dataset_id: {dataset_id}\n"
        f"encoding: {profile['encoding']}\n"
        f"rows: {profile['n_rows']}, cols: {profile['n_cols']}\n"
        f"columns: {col_brief}\n"
        f"deterministic_flags: {flags}\n"
        f"sample(first rows): {json.dumps(profile['sample_rows'], ensure_ascii=False)[:800]}\n"
    )
    raw = await generate(prompt, system=system, fmt_json=True, model=model)
    try:
        interpretation = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        interpretation = {"_raw": raw, "_note": "LLM 출력 JSON 파싱 실패 (모델 미설치 가능)"}

    profile["llm_interpretation"] = interpretation
    return profile
