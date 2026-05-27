"""
backend/main.py
===============
백엔드 오케스트레이션 (FastAPI). 수직 슬라이스의 진입점.

흐름: 브라우저 → /api/inspect → Inspector 에이전트 → (MCP 도구 + Gemma) → DataProfile
또한 frontend/index.html(더미 대시보드)을 서빙한다.

⚠️ 지금은 FastAPI 하나로 충분. tRPC/Express는 Sprint 2 프론트 본격화 때. (CLAUDE.md §2)
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 레포 루트를 PYTHONPATH에 추가 (agents/, harness/ import용)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents" / "inspector"))
sys.path.insert(0, str(ROOT / "agents" / "planner"))
sys.path.insert(0, str(ROOT / "agents" / "executor"))
sys.path.insert(0, str(ROOT / "agents" / "validator"))
sys.path.insert(0, str(ROOT / "backend"))

app = FastAPI(title="manufacturing-mcp backend", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

FRONTEND = ROOT / "frontend" / "index.html"


@app.get("/api/health")
async def health() -> dict:
    """LLM + MCP 가용성 한눈에."""
    from llm import health as llm_health
    out = {"backend": "ok"}
    out["llm"] = await llm_health()
    try:
        import httpx
        mcp_url = os.environ.get("MCP_TIMESERIES_URL", "http://mcp-timeseries:8101")
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{mcp_url}/health")
            out["mcp_timeseries"] = r.json()
    except Exception as e:
        out["mcp_timeseries"] = {"status": "down", "error": str(e)}
    return out


MCP_SERVERS = {
    "timeseries": os.environ.get("MCP_TIMESERIES_URL", "http://mcp-timeseries:8101"),
    "inspection-image": os.environ.get("MCP_IMAGE_URL", "http://mcp-inspection-image:8102"),
    "event-log": os.environ.get("MCP_EVENTLOG_URL", "http://mcp-event-log:8103"),
    "order": os.environ.get("MCP_ORDER_URL", "http://mcp-order:8104"),
}


@app.get("/api/modalities")
async def modalities() -> dict:
    """사용 가능한 모달리티 목록 (UI 드롭다운용). 각 서버 health도 확인."""
    import httpx
    out = []
    for name, url in MCP_SERVERS.items():
        status = "down"
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"{url}/health")
                status = r.json().get("status", "down")
        except Exception:
            pass
        out.append({"modality": name, "status": status})
    return {"modalities": out}


@app.get("/api/datasets")
async def datasets(modality: str = "timeseries") -> dict:
    """모달리티별 데이터셋 목록. modality에 맞는 MCP 서버로 라우팅."""
    import httpx
    mcp_url = MCP_SERVERS.get(modality, MCP_SERVERS["timeseries"])
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{mcp_url}/datasets")
        data = r.json()
        data["modality"] = modality
        return data


@app.get("/api/models")
async def models() -> dict:
    """Ollama에 설치된 모델 목록 (UI 드롭다운용)."""
    from llm import health as llm_health, OLLAMA_MODEL
    h = await llm_health()
    return {"installed": h.get("installed_models", []), "default": OLLAMA_MODEL}


@app.get("/api/inspect")
async def inspect(dataset_id: str, model: str | None = None,
                  modality: str = "timeseries") -> dict:
    """수직 슬라이스의 핵심 엔드포인트: Inspector 에이전트 실행."""
    from inspector import inspect as run_inspect
    try:
        return await run_inspect(dataset_id, model=model, modality=modality)
    except Exception as e:
        raise HTTPException(500, f"inspect failed: {e}")


@app.get("/api/plan")
async def plan_endpoint(dataset_id: str, model: str | None = None,
                        modality: str = "timeseries") -> dict:
    """Inspector → Planner 체인 실행. DataProfile을 만들고 그걸로 전처리 계획 생성.
    이게 Agentic Flow의 1→2단 연결 (A2A: Inspector 출력이 Planner 입력)."""
    from inspector import inspect as run_inspect
    from planner import plan as run_plan
    try:
        profile = await run_inspect(dataset_id, model=model, modality=modality)
        plan_result = await run_plan(profile, model=model)
        return {"profile": profile, "plan": plan_result}
    except Exception as e:
        raise HTTPException(500, f"plan failed: {e}")


class ExecuteReq(BaseModel):
    dataset_id: str
    approved_keys: list[str] = []     # 사용자가 승인한 step_key 목록 (order 대신 안정적 식별자)
    model: str | None = None          # UI에서 선택한 모델
    modality: str = "timeseries"      # UI에서 선택한 모달리티


@app.post("/api/execute")
async def execute_endpoint(req: ExecuteReq) -> dict:
    """Inspector → Planner → Executor → Validator 전체 체인 (Agentic Flow 1→2→3→4단).
    approved_keys에 든 작업만 L2/L3 실행 (step_key 기반 — order 비결정성 회피)."""
    from inspector import inspect as run_inspect
    from planner import plan as run_plan
    from executor import execute as run_execute
    from validator import validate as run_validate
    try:
        profile = await run_inspect(req.dataset_id, model=req.model, modality=req.modality)
        plan_result = await run_plan(profile, model=req.model)
        exec_result = await run_execute(plan_result, approved_keys=set(req.approved_keys),
                                        modality=req.modality)
        # ★4단 Validator: 실행 결과를 plan·profile과 함께 검증
        validation = await run_validate(exec_result, plan=plan_result, profile=profile)
        return {"profile": profile, "plan": plan_result,
                "execution": exec_result, "validation": validation}
    except Exception as e:
        raise HTTPException(500, f"execute failed: {e}")


@app.get("/api/lineage")
async def lineage_endpoint(dataset_id: str) -> dict:
    """데이터셋의 변환 이력(lineage) 전체 조회. SI 컴플라이언스 — 추적 가능성 증명.
    각 변환의 무엇을/언제/누가/승인여부/롤백가능 여부를 시간순으로 반환."""
    from harness.lineage import get_chain  # executor와 동일 경로 (같은 _STORE 공유)
    chain = get_chain(dataset_id)
    return {"dataset_id": dataset_id, "n_records": len(chain), "chain": chain}


@app.get("/")
async def root() -> FileResponse:
    """더미 대시보드 서빙."""
    if FRONTEND.exists():
        return FileResponse(str(FRONTEND))
    raise HTTPException(404, "frontend/index.html not found")
