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
sys.path.insert(0, str(ROOT / "agents" / "aggregator"))   # STEP 1B-2b
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
    # ★STEP 1B-1: 사용자 입력 constraints + 공정 맥락 (둘 다 옵션 — 빈 값이면 기존 동작)
    constraints: dict | None = None        # 예: {"injection_velocity": [40, 70]}
    module_context: dict | None = None     # 예: {"node_id":"injection_molding","function":"process"}


@app.post("/api/execute")
async def execute_endpoint(req: ExecuteReq) -> dict:
    """Inspector → Planner → Executor → Validator 전체 체인 (Agentic Flow 1→2→3→4단).
    approved_keys에 든 작업만 L2/L3 실행 (step_key 기반 — order 비결정성 회피).
    constraints/module_context는 옵션 — 안 주면 기존 동작 그대로 (회귀 없음, STEP 1B-1)."""
    from inspector import inspect as run_inspect
    from planner import plan as run_plan
    from executor import execute as run_execute
    from validator import validate as run_validate
    try:
        profile = await run_inspect(req.dataset_id, model=req.model, modality=req.modality)
        plan_result = await run_plan(profile, constraints=req.constraints,
                                     module_context=req.module_context, model=req.model)
        exec_result = await run_execute(plan_result, approved_keys=set(req.approved_keys),
                                        modality=req.modality)
        # ★4단 Validator: 실행 결과를 plan·profile·constraints와 함께 검증 (5종)
        validation = await run_validate(exec_result, plan=plan_result, profile=profile,
                                        constraints=req.constraints)
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


@app.get("/api/lines")
async def lines_endpoint() -> dict:
    """Line·Node·Module 카탈로그 조회 (STEP 1B-1, Page 2 CatalogPanel 향). lines.yaml 파싱.
    UI는 STEP 1B-3 — 여기선 카탈로그 JSON 반환만."""
    import yaml
    path = ROOT / "catalogs" / "lines.yaml"
    if not path.exists():
        raise HTTPException(500, f"catalog not found: {path}")
    with open(path, encoding="utf-8") as f:
        return {"lines": yaml.safe_load(f)}


# ──────────────────────────────────────────────────────────────────────
# STEP 1B-2a — Resumable Orchestrator (폴링형)
# ──────────────────────────────────────────────────────────────────────
# 흐름: /api/sessions/create → /api/execute_pipeline → (awaiting_approval 시
#   /api/pipeline/{id}/approve 후 /api/execute_pipeline 재호출로 resume)
#
# ★blocking awaiter 없음★ — L2/L3 만나면 상태 저장 후 즉시 반환 (D-51).
# 1층 /api/execute(단일 데이터셋)는 보존 — pipeline은 별도 엔드포인트.
# ──────────────────────────────────────────────────────────────────────

# node_id → 대표 modality 매핑 (lines.yaml의 hint_dataset 기반 휴리스틱). module.modality 우선.
_NODE_MODALITY: dict[str, str] = {
    "semiconductor_inspect": "inspection-image",
    "surface_inspect": "inspection-image",
    "welding_inspect": "inspection-image",
    "order_planning": "order",
}


def _resolve_modality(module: dict, node_id: str | None = None) -> str:
    """모듈/노드에서 modality 결정. 우선순위:
    1) module["modality"] 명시,
    2) node_id 매핑(검사/주문),
    3) 폴백 "timeseries".
    자동 modality 분류(D-40)는 별개 — 여기선 명시/매핑만."""
    m = module.get("modality")
    if m:
        return m
    if node_id and node_id in _NODE_MODALITY:
        return _NODE_MODALITY[node_id]
    return "timeseries"


class CreateSessionReq(BaseModel):
    pipeline_full: dict   # {line_id, stages:[{stage_order, node_id, modules:[...]}, ...]}


@app.post("/api/sessions/create")
async def sessions_create(req: CreateSessionReq) -> dict:
    """pipeline_full을 주입해 세션 생성 (1B-2a 폴링 사이클의 시작점).
    Page 2(1-1) + Page 3(1-2) 통합 출력을 받는 자리. 1B-3 UI 도입 전에는 테스트가 직접 호출."""
    from session_store import create_session
    sid = create_session(req.pipeline_full)
    return {"session_id": sid, "status": "created"}


class ExecutePipelineReq(BaseModel):
    session_id: str
    model: str | None = None       # LLM 호출(plan/llm_judge)에 사용할 모델 (옵션)


@app.post("/api/execute_pipeline")
async def execute_pipeline(req: ExecutePipelineReq) -> dict:
    """파이프라인 진행 (Resumable, suspend-and-return).
    L2/L3 unapproved step을 만나면 상태 저장 후 즉시 awaiting_approval로 반환.
    /approve 후 본 엔드포인트 재호출로 이전 지점부터 resume (completed_* skip).
    """
    from session_store import get_session, save_session, public_view
    from inspector import inspect as run_inspect
    from planner import plan as run_plan
    from executor import execute as run_execute
    from validator import validate as run_validate
    from data_necessity import llm_judge_data_necessity

    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {req.session_id}")

    session["status"] = "running"
    session["pending"] = None
    pipeline_full = session.get("pipeline_full") or {}
    stages = pipeline_full.get("stages", [])

    try:
        for stage in stages:
            so = stage.get("stage_order")
            if so in session["completed_stage_orders"]:
                continue   # resume: 이미 끝난 stage skip

            node_id = stage.get("node_id")
            modules_all = stage.get("modules", [])
            missing = [m for m in modules_all if m.get("datalake_id") in (None, "")]
            uploaded = [m for m in modules_all if m.get("datalake_id")]

            # (A) 미업로드 알람 — stage당 1회만 (resume 시 재알람 없음)
            already_alarmed = {a.get("stage_order") for a in session["alarms"]}
            if missing and so not in already_alarmed:
                alarm = await llm_judge_data_necessity(stage, missing, uploaded, model=req.model)
                session["alarms"].append({"stage_order": so, "node_id": node_id, "alarm": alarm})
                # 알람은 기록만 — 흐름은 계속 (skip된 missing은 처리 안 함)

            # (B) 업로드된 모듈 순회
            for module in uploaded:
                module_key = f"{so}.{module.get('index')}"
                if module_key in session["completed_module_keys"]:
                    continue   # resume skip

                dataset_id = module["datalake_id"]
                modality = _resolve_modality(module, node_id)
                constraints = module.get("constraints") or {}

                # 1) Inspector
                profile = await run_inspect(dataset_id, model=req.model, modality=modality)

                # 2) Planner — module_context는 stage·module에서 합성 (1B-1 연장)
                module_context = {
                    "node_id": node_id,
                    "function": module.get("function"),
                    "dataset_role": module.get("dataset_role"),
                }
                plan_result = await run_plan(profile, constraints=constraints,
                                             module_context=module_context, model=req.model)

                # 3) 권한 게이트 — unapproved L2/L3 있으면 suspend-and-return
                approved = set(session["approved_step_keys"])
                unapproved = [
                    s for s in plan_result.get("steps", [])
                    if s.get("permission_level") in ("L2", "L3")
                    and s.get("step_key") not in approved
                ]
                if unapproved:
                    session["status"] = "awaiting_approval"
                    session["pending"] = {
                        "stage_order": so,
                        "node_id": node_id,
                        "module_index": module.get("index"),
                        "module_key": module_key,
                        "dataset_id": dataset_id,
                        "modality": modality,
                        "plan": plan_result,
                        "pending_steps": [{
                            "step_key": s.get("step_key"),
                            "order": s.get("order"),
                            "operation": s.get("operation"),
                            "permission_level": s.get("permission_level"),
                            "target_column": s.get("target_column"),
                            "semantic_group": s.get("semantic_group"),
                            "rationale": s.get("rationale"),
                        } for s in unapproved],
                    }
                    save_session(req.session_id, session)
                    return {"status": "awaiting_approval",
                            "pending": session["pending"],
                            "session": public_view(session)}

                # 4) Executor (전부 승인됨) + Validator
                execution = await run_execute(plan_result, approved_keys=approved,
                                              modality=modality)
                validation = await run_validate(execution, plan=plan_result,
                                                profile=profile, constraints=constraints)
                session["module_results"][module_key] = {
                    "modality": modality,
                    "dataset_id": dataset_id,
                    "profile": profile,
                    "plan": plan_result,
                    "execution": execution,
                    "validation": validation,
                }
                session["completed_module_keys"].append(module_key)

            session["completed_stage_orders"].append(so)
            # 1B-2b Aggregator가 쓸 stage 요약 (지금은 가벼운 메타만 — 결정론)
            session["accumulated_context"].append({
                "stage_order": so,
                "node_id": node_id,
                "modules_done": [m.get("index") for m in uploaded],
                "modules_skipped_missing": [m.get("index") for m in missing],
            })

        session["status"] = "completed"
        session["pending"] = None
        # ★STEP 1B-2b: Context Aggregator 자동 트리거 (결정론, LLM 0)
        #   blueprint Part 2-5 마지막 줄 정합. 같은 입력 → 같은 출력이므로 재호출 안전.
        from context_aggregator import aggregate as _aggregate
        session["aggregated_context"] = _aggregate(session)
        save_session(req.session_id, session)
        return {"status": "completed", "session": public_view(session),
                "aggregated_context": session["aggregated_context"]}

    except HTTPException:
        raise
    except Exception as e:
        session["status"] = "error"
        session["error"] = str(e)
        save_session(req.session_id, session)
        raise HTTPException(500, f"execute_pipeline failed: {e}")


@app.get("/api/pipeline/{session_id}/status")
async def pipeline_status(session_id: str) -> dict:
    """폴링 조회 — 세션 진행 상태 + pending + completed_* + alarms 반환.
    SSE 없이 클라이언트가 주기적으로 호출 (1B-3에서 SSE 추가 검토)."""
    from session_store import get_session, public_view
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    return public_view(session)


class ApproveReq(BaseModel):
    step_key: str
    stage_order: int | None = None    # 참고/로깅용
    module_index: int | None = None


@app.post("/api/pipeline/{session_id}/approve")
async def pipeline_approve(session_id: str, req: ApproveReq) -> dict:
    """단건 승인 — step_key를 누적 승인 목록에 추가.
    resume은 클라이언트가 /api/execute_pipeline 재호출로 트리거 (폴링형, D-51)."""
    from session_store import get_session, save_session
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    if req.step_key not in session["approved_step_keys"]:
        session["approved_step_keys"].append(req.step_key)
    save_session(session_id, session)
    return {"approved": True, "step_key": req.step_key,
            "approved_count": len(session["approved_step_keys"]),
            "stage_order": req.stage_order, "module_index": req.module_index}


@app.get("/api/aggregate_context/{session_id}")
async def aggregate_context_endpoint(session_id: str) -> dict:
    """STEP 1B-2b — 세션의 4단 판단 기록을 결정론으로 집계해 AggregatedContext 반환.
    Page 5/6 LLM 프롬프트의 컨텍스트 소스(spec-1 API 14b). LLM 호출 0 (D-59).
    이미 집계돼 있으면 캐시 반환(결정론이라 재생성해도 동일).
    """
    from session_store import get_session, save_session
    from context_aggregator import aggregate as _aggregate
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    if session.get("aggregated_context"):
        return session["aggregated_context"]
    ctx = _aggregate(session)
    session["aggregated_context"] = ctx
    save_session(session_id, session)
    return ctx


@app.get("/")
async def root() -> FileResponse:
    """더미 대시보드 서빙."""
    if FRONTEND.exists():
        return FileResponse(str(FRONTEND))
    raise HTTPException(404, "frontend/index.html not found")
