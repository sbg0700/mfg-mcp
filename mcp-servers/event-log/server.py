"""
mcp-servers/event-log/server.py — event-log MCP 서버 (포트 8103).
★timeseries/image 서버와 동일한 엔드포인트 계약★.
"""
from __future__ import annotations
import os
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tools

app = FastAPI(title="MCP event-log", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "modality": "event-log"}


@app.get("/tools")
def list_tools() -> dict[str, list[str]]:
    return {"tools": list(tools.TOOLS.keys())}


@app.get("/datasets")
def datasets() -> dict[str, list[str]]:
    root = tools.EVENTLOG_DATA_ROOT
    if not os.path.isdir(root):
        return {"datasets": []}
    files = [f for f in os.listdir(root) if f.endswith((".csv", ".xlsx"))]
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
