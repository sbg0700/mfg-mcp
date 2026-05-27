"""
mcp-servers/order/server.py
================================
order MCP 서버 — 7종 도구를 HTTP 엔드포인트로 노출 (수제 prototype).

⚠️ 이것은 '진짜 MCP 프로토콜'의 stand-in이다 (CLAUDE.md §4).
   계약(7개 도구 시그니처)이 동일하므로, 나중에 실제 MCP 프로토콜로 교체해도
   상위(Agent)는 영향받지 않는다.

실행: uvicorn server:app --host 0.0.0.0 --port 8104
"""

from __future__ import annotations
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import tools

app = FastAPI(title="MCP order", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "modality": "order"}


@app.get("/tools")
def list_tools() -> dict[str, list[str]]:
    """이 서버가 제공하는 표준 도구 7종."""
    return {"tools": list(tools.TOOLS.keys())}


# ---- 도구별 엔드포인트 (계약: CLAUDE.md §4) ----

@app.get("/datasets")
def datasets() -> dict[str, list[str]]:
    import os
    root = tools.DATA_ROOT
    files = [f[:-4] for f in os.listdir(root) if f.endswith(".csv")] if os.path.isdir(root) else []
    return {"datasets": sorted(files)}


@app.get("/list_columns")
def ep_list_columns(dataset_id: str) -> dict[str, Any]:
    try:
        return tools.list_columns(dataset_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.get("/get_schema")
def ep_get_schema(dataset_id: str) -> dict[str, Any]:
    try:
        return tools.get_schema(dataset_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.get("/sample")
def ep_sample(dataset_id: str, n: int = 5) -> dict[str, Any]:
    try:
        return tools.sample(dataset_id, n)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.get("/detect_encoding")
def ep_detect_encoding(dataset_id: str) -> dict[str, Any]:
    try:
        return tools.detect_encoding(tools._resolve(dataset_id))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


class ConstraintReq(BaseModel):
    dataset_id: str
    constraints: dict[str, Any] = {}


@app.post("/check_constraints")
def ep_check_constraints(req: ConstraintReq) -> dict[str, Any]:
    try:
        return tools.check_constraints(req.dataset_id, req.constraints)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


class PreprocessReq(BaseModel):
    dataset_id: str
    operations: list[dict[str, Any]] = []
    permission_level: str = "L1"


@app.post("/apply_preprocessing")
def ep_apply_preprocessing(req: PreprocessReq) -> dict[str, Any]:
    return tools.apply_preprocessing(req.dataset_id, req.operations, req.permission_level)


@app.get("/lineage")
def ep_lineage(dataset_id: str) -> dict[str, Any]:
    return tools.lineage(dataset_id)
