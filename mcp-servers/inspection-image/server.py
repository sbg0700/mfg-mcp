"""
mcp-servers/inspection-image/server.py
======================================
inspection-image MCP 서버 — 7종 도구를 HTTP로 노출.
★timeseries 서버와 동일한 엔드포인트 계약★ (포트만 8102).

실행: uvicorn server:app --host 0.0.0.0 --port 8102
"""
from __future__ import annotations
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import tools

app = FastAPI(title="MCP inspection-image", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "modality": "inspection-image"}


@app.get("/tools")
def list_tools() -> dict[str, list[str]]:
    return {"tools": list(tools.TOOLS.keys())}


@app.get("/datasets")
def datasets() -> dict[str, list[str]]:
    """이미지 데이터셋 = 최상위 폴더들 (timeseries는 CSV 파일이었음)."""
    root = tools.IMAGE_DATA_ROOT
    if not os.path.isdir(root):
        return {"datasets": []}
    folders = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
    return {"datasets": sorted(folders)}


@app.get("/list_columns")
def ep_list_columns(dataset_id: str, data_path: str | None = None) -> dict[str, Any]:
    try:
        return tools.list_columns(dataset_id, data_path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.get("/get_schema")
def ep_get_schema(dataset_id: str, data_path: str | None = None) -> dict[str, Any]:
    try:
        return tools.get_schema(dataset_id, data_path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.get("/sample")
def ep_sample(dataset_id: str, n: int = 5, data_path: str | None = None) -> dict[str, Any]:
    try:
        return tools.sample(dataset_id, n, data_path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.get("/detect_encoding")
def ep_detect_encoding(dataset_id: str, data_path: str | None = None) -> dict[str, Any]:
    """이미지셋의 첫 이미지 포맷/모드 감지."""
    try:
        path = tools._resolve(dataset_id, data_path)
        items = tools._scan(path)
        if not items:
            raise HTTPException(404, "no images")
        import os as _os
        first = _os.path.join(path, items[0]["file"])
        return tools.detect_encoding(first)
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
