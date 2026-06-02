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

FRONTEND = ROOT / "frontend" / "_legacy_dashboard.html"   # STEP 1B-3a: 새 React 앱은 Vite(5173)에서, 백엔드 / 는 레거시 보존


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


@app.get("/api/datasets/all")
async def datasets_all() -> dict:
    """STEP 1B-3b — 4 모달리티 데이터셋을 한 번에 묶어 반환 (Page 3 드롭다운).
    각 MCP /datasets는 디렉터리 스캔이므로 데이터 비종속 (D-82).
    한 MCP가 다운돼도 다른 모달리티는 정상 반환."""
    import httpx
    out: dict[str, list[str]] = {}
    for modality, mcp_url in MCP_SERVERS.items():
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{mcp_url}/datasets")
                out[modality] = r.json().get("datasets", []) if r.status_code == 200 else []
        except Exception:
            out[modality] = []
    return {"datasets_by_modality": out}


@app.get("/api/datasets/{dataset_id}/columns")
async def dataset_columns(dataset_id: str, modality: str = "timeseries",
                          numeric_only: bool = True) -> dict:
    """STEP 1B-3c (D-90 해결) — 데이터셋의 실제 컬럼 목록.
    MCP /list_columns (CLAUDE.md §4)를 위임 호출하므로 데이터 비종속(파일 헤더 스캔).
    numeric_only=True면 범위 제약에 의미 있는 수치 컬럼만 반환."""
    import httpx
    mcp_url = MCP_SERVERS.get(modality)
    if not mcp_url:
        return {"dataset_id": dataset_id, "modality": modality, "columns": [],
                "n_total": 0, "n_numeric": 0}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{mcp_url}/list_columns", params={"dataset_id": dataset_id})
            if r.status_code != 200:
                return {"dataset_id": dataset_id, "modality": modality, "columns": [],
                        "error": f"MCP {modality} returned {r.status_code}"}
            data = r.json()
            all_cols = data.get("columns", [])
            num_cols = [c for c in all_cols
                        if "int" in str(c.get("dtype", "")) or "float" in str(c.get("dtype", ""))]
            picked = num_cols if numeric_only else all_cols
            slim = [{"name": c["name"], "dtype": c.get("dtype"),
                     "semantic_group": c.get("semantic_group"),
                     "null_count": c.get("null_count", 0)} for c in picked]
            return {"dataset_id": dataset_id, "modality": modality,
                    "columns": slim, "n_total": len(all_cols), "n_numeric": len(num_cols)}
    except Exception as e:
        return {"dataset_id": dataset_id, "modality": modality, "columns": [],
                "error": str(e)}


@app.get("/api/modules")
async def modules_catalog() -> dict:
    """STEP 1B-3b — modules.yaml 조회 (Page 3 constraint 폼, Page 6 모델 추천 소스).
    catalogs/modules.yaml (5 Node: injection_molding/cnc_cutting/press_forming/
    semiconductor_inspect/pdm) 그대로 반환. typical_ranges 값 디폴트 0(D-43)."""
    import yaml
    path = ROOT / "catalogs" / "modules.yaml"
    if not path.exists():
        raise HTTPException(500, f"catalog not found: {path}")
    with open(path, encoding="utf-8") as f:
        return {"modules": yaml.safe_load(f)}


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
    """Inspector → Planner → ★사전 검증★ → Executor → Validator 전체 체인 (STEP 1B-2c).
    approved_keys에 든 작업만 L2/L3 실행 (step_key 기반 — order 비결정성 회피).
    constraints/module_context는 옵션 — 안 주면 기존 동작 그대로 (회귀 없음, STEP 1B-1)."""
    from inspector import inspect as run_inspect
    from planner import plan as run_plan
    from executor import execute as run_execute
    from validator import validate as run_validate, validate_plan
    try:
        profile = await run_inspect(req.dataset_id, model=req.model, modality=req.modality)
        plan_result = await run_plan(profile, constraints=req.constraints,
                                     module_context=req.module_context, model=req.model)
        # ★사전 검증 (STEP 1B-2c): Executor 전. blocking(high 충돌) 시 실행 중단
        pre_validation = validate_plan(plan_result, profile)
        if pre_validation.get("blocking"):
            return {"profile": profile, "plan": plan_result,
                    "pre_validation": pre_validation,
                    "execution": None, "validation": None,
                    "note": "계획 사전 검증 실패(blocking) — 실행 중단"}
        exec_result = await run_execute(plan_result, approved_keys=set(req.approved_keys),
                                        modality=req.modality)
        # ★사후 Validator: 6종 검증 (compliance/transform/integrity/regression/constraint/output_health)
        validation = await run_validate(exec_result, plan=plan_result, profile=profile,
                                        constraints=req.constraints)
        validation["pre_validation"] = pre_validation
        return {"profile": profile, "plan": plan_result,
                "pre_validation": pre_validation,
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


# ★STEP 2a (D-104): suspend 시 balance_classes 미리보기용 df 로드.
#   Executor의 데이터 로더(_resolve / _load_eventlog)를 재사용 — 일관성 유지.
#   balance_classes pending step이 없으면 로드 자체를 건너뜀(불필요 I/O 회피).
def _maybe_load_df_for_preview(dataset_id: str, modality: str, pending_steps: list[dict]):
    """미리보기 필요시에만 df 로드 (balance_classes pending step 있을 때).
    실패해도 파이프라인은 계속 (preview만 빠짐). LLM 0 — 순수 데이터 I/O."""
    if not any(s.get("operation") == "balance_classes" and s.get("target_column")
               for s in pending_steps):
        return None
    try:
        import pandas as pd
        if modality in ("timeseries", "order"):
            from executor import _resolve
            path = _resolve(dataset_id, modality)
            for enc in ("utf-8-sig", "cp949", "latin1"):
                try:
                    return pd.read_csv(path, encoding=enc, low_memory=False)
                except (UnicodeDecodeError, LookupError):
                    continue
            return None
        if modality == "event-log":
            from executor import _load_eventlog
            df, _path, _n = _load_eventlog(dataset_id)
            return df
        # inspection-image: balance_classes 의미 없음
        return None
    except Exception:
        return None


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
    # ★STEP 1B-3a: 둘 다 옵션 — Page 1은 line_id만, 기존 직접 호출은 pipeline_full만 (회귀 보존, D-74)
    line_id: str | None = None
    pipeline_full: dict | None = None   # {line_id, stages:[{stage_order, node_id, modules:[...]}]}
    model: str | None = None            # ★STEP 1B-3d B2: 세션이 자기 model을 기억 (D-99)


@app.post("/api/sessions/create")
async def sessions_create(req: CreateSessionReq) -> dict:
    """세션 생성 — Page 1(line_id 단독) 또는 직접 호출(pipeline_full)이 모두 허용된다.
    line_id만 오면 빈 stages로 초기화 — Page 2에서 PUT /structure로 채움.
    model이 주어지면 세션에 저장 — 이후 모든 LLM 호출이 이 model 사용 (B2, D-99)."""
    from session_store import create_session, get_session, save_session
    if not req.line_id and not req.pipeline_full:
        raise HTTPException(400, "either line_id or pipeline_full is required")
    skeleton = req.pipeline_full or {"line_id": req.line_id, "stages": []}
    sid = create_session(skeleton)
    # line_id를 세션 최상위에도 저장 (Page 2의 GET /sessions/{id}가 쉽게 읽도록)
    session = get_session(sid)
    if req.line_id:
        session["line_id"] = req.line_id
    elif req.pipeline_full and req.pipeline_full.get("line_id"):
        session["line_id"] = req.pipeline_full["line_id"]
    if req.model:
        session["model"] = req.model
    save_session(sid, session)
    return {"session_id": sid, "status": "created",
            "line_id": session.get("line_id"), "model": session.get("model")}


class SessionModelReq(BaseModel):
    model: str    # 빈 문자열이면 세션 model 해제 (백엔드 환경변수 폴백)


@app.put("/api/sessions/{session_id}/model")
async def session_put_model(session_id: str, req: SessionModelReq) -> dict:
    """STEP 1B-3d B2 — 드롭다운 모델 변경을 세션에 반영.
    이후 execute_pipeline / analyze / model recommend가 이 model을 사용 (D-99)."""
    from session_store import get_session, save_session
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    if req.model:
        session["model"] = req.model
    else:
        session.pop("model", None)   # 빈 값이면 폴백
    save_session(session_id, session)
    return {"session_id": session_id, "model": session.get("model")}


@app.get("/api/sessions/{session_id}")
async def session_get(session_id: str) -> dict:
    """세션 복원 (Page 2 새로고침/되돌아오기 등)."""
    from session_store import get_session, public_view
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    out = public_view(session)
    out["line_id"] = session.get("line_id") or (out.get("pipeline_full") or {}).get("line_id")
    return out


class StructureReq(BaseModel):
    line_id: str
    stages: list[dict]   # [{stage_order, node_id, modules:[{index, function, dataset_role}]}]


@app.put("/api/sessions/{session_id}/structure")
async def session_put_structure(session_id: str, req: StructureReq) -> dict:
    """Page 2(드래그앤드롭) 출력 PipelineStructure 저장.
    데이터(datalake_id)와 제약(constraints)은 Page 3에서 추가 — 이번은 뼈대만."""
    from session_store import get_session, save_session
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    session["pipeline_full"] = {"line_id": req.line_id, "stages": req.stages}
    session["line_id"] = req.line_id
    session["status"] = "structured"
    save_session(session_id, session)
    return {"session_id": session_id, "status": "structured",
            "stage_count": len(req.stages),
            "module_count": sum(len(s.get("modules", [])) for s in req.stages)}


class FullReq(BaseModel):
    pipeline_full: dict   # {line_id, stages:[{stage_order, node_id, modules:[{index,function,modality,datalake_id,constraints}]}]}


@app.put("/api/sessions/{session_id}/full")
async def session_put_full(session_id: str, req: FullReq) -> dict:
    """STEP 1B-3b — Page 3 출력 PipelineFull 저장 (데이터 + 제약 포함).
    이후 /api/execute_pipeline {session_id} 호출이 이 pipeline_full을 처리."""
    from session_store import get_session, save_session
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    pf = req.pipeline_full or {}
    session["pipeline_full"] = pf
    if pf.get("line_id"):
        session["line_id"] = pf["line_id"]
    session["status"] = "ready"   # 실행 준비 완료
    save_session(session_id, session)
    # 통계 — 데이터 매핑된 모듈 수, 제약 입력된 모듈 수
    n_modules = 0
    n_with_data = 0
    n_with_constraints = 0
    for stage in pf.get("stages", []):
        for m in stage.get("modules", []):
            n_modules += 1
            if m.get("datalake_id"):
                n_with_data += 1
            if m.get("constraints"):
                n_with_constraints += 1
    return {"session_id": session_id, "status": "ready",
            "modules_total": n_modules,
            "modules_with_data": n_with_data,
            "modules_with_constraints": n_with_constraints}


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
    from validator import validate as run_validate, validate_plan
    from data_necessity import llm_judge_data_necessity

    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {req.session_id}")

    session["status"] = "running"
    session["pending"] = None
    pipeline_full = session.get("pipeline_full") or {}
    stages = pipeline_full.get("stages", [])
    # ★STEP 1B-3d B2: 세션 model 우선 → req.model → generate 폴백 (D-99)
    model = session.get("model") or req.model

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
                alarm = await llm_judge_data_necessity(stage, missing, uploaded, model=model)
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
                profile = await run_inspect(dataset_id, model=model, modality=modality)

                # 2) Planner — module_context는 stage·module에서 합성 (1B-1 연장)
                module_context = {
                    "node_id": node_id,
                    "function": module.get("function"),
                    "dataset_role": module.get("dataset_role"),
                }
                plan_result = await run_plan(profile, constraints=constraints,
                                             module_context=module_context, model=model)

                # ★사전 검증 (STEP 1B-2c) — Executor 전 결정론 검증
                pre_validation = validate_plan(plan_result, profile)
                if pre_validation.get("blocking"):
                    # high 충돌(예: drop_column + 같은 컬럼 변환) → 해당 모듈 차단, 세션 error
                    session["module_results"][module_key] = {
                        "modality": modality,
                        "dataset_id": dataset_id,
                        "profile": profile,
                        "plan": plan_result,
                        "pre_validation": pre_validation,
                        "execution": None,
                        "validation": None,
                        "note": "계획 사전 검증 실패(blocking) — 실행 중단",
                    }
                    session["status"] = "error"
                    session["error"] = (f"plan blocking at {module_key}: "
                                        f"{pre_validation.get('n_high')} high issue(s)")
                    save_session(req.session_id, session)
                    return {"status": "error", "blocking_module": module_key,
                            "pre_validation": pre_validation,
                            "session": public_view(session)}

                # 3) 권한 게이트 — unapproved L2/L3 있으면 suspend-and-return
                approved = set(session["approved_step_keys"])
                unapproved = [
                    s for s in plan_result.get("steps", [])
                    if s.get("permission_level") in ("L2", "L3")
                    and s.get("step_key") not in approved
                ]
                if unapproved:
                    session["status"] = "awaiting_approval"
                    # ★STEP 2a (D-104): balance_classes pending step에 available_options + 결정론 미리보기 첨부.
                    #   df는 미리보기 시점에만 로드 (Executor와 별개 — 가벼움). LLM 호출 없음.
                    preview_df = _maybe_load_df_for_preview(dataset_id, modality, unapproved)
                    pending_steps_payload = []
                    for s in unapproved:
                        ps = {
                            "step_key": s.get("step_key"),
                            "order": s.get("order"),
                            "operation": s.get("operation"),
                            "permission_level": s.get("permission_level"),
                            "target_column": s.get("target_column"),
                            "semantic_group": s.get("semantic_group"),
                            "rationale": s.get("rationale"),
                            "available_options": s.get("available_options", []),
                        }
                        # balance_classes에만 preview 채움 (다른 step은 빈 채로 — 회귀 0)
                        if (s.get("operation") == "balance_classes" and preview_df is not None
                                and s.get("target_column")):
                            try:
                                from balance_options import compute_balance_preview
                                ps["preview"] = compute_balance_preview(preview_df, s["target_column"])
                            except Exception as _e:
                                ps["preview"] = {"applicable": False,
                                                 "reason": f"preview 계산 실패: {_e}"}
                        pending_steps_payload.append(ps)
                    session["pending"] = {
                        "stage_order": so,
                        "node_id": node_id,
                        "module_index": module.get("index"),
                        "module_key": module_key,
                        "dataset_id": dataset_id,
                        "modality": modality,
                        "plan": plan_result,
                        "pending_steps": pending_steps_payload,
                    }
                    save_session(req.session_id, session)
                    return {"status": "awaiting_approval",
                            "pending": session["pending"],
                            "session": public_view(session)}

                # 4) Executor (전부 승인됨) + Validator (사후 6종)
                # ★STEP 2a (D-103): 세션에 저장된 옵션 선택을 Executor로 전달 (balance_classes 분기).
                selected_options = session.get("selected_options") or {}
                execution = await run_execute(plan_result, approved_keys=approved,
                                              modality=modality,
                                              selected_options=selected_options)
                validation = await run_validate(execution, plan=plan_result,
                                                profile=profile, constraints=constraints)
                validation["pre_validation"] = pre_validation  # 사전 결과도 첨부
                session["module_results"][module_key] = {
                    "modality": modality,
                    "dataset_id": dataset_id,
                    "profile": profile,
                    "plan": plan_result,
                    "pre_validation": pre_validation,
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
    # ★STEP 2a (D-103): 옵션 카드 선택 결과 (balance_classes 등). 없으면 옵션 무관 작업.
    selected_option: str | None = None


@app.post("/api/pipeline/{session_id}/approve")
async def pipeline_approve(session_id: str, req: ApproveReq) -> dict:
    """단건 승인 — step_key를 누적 승인 목록에 추가.
    resume은 클라이언트가 /api/execute_pipeline 재호출로 트리거 (폴링형, D-51).
    ★STEP 2a (D-103): selected_option이 오면 허용 옵션 집합(BALANCE_OPTION_IDS)만 저장.
    허용 외 값은 무시(환각 방어). 옵션 없는 step은 selected_option=None 그대로 동작."""
    from session_store import get_session, save_session
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    if req.step_key not in session["approved_step_keys"]:
        session["approved_step_keys"].append(req.step_key)
    # ★옵션 저장 — 환각 방어 필터 (허용된 옵션 id만 통과)
    if req.selected_option:
        from balance_options import BALANCE_OPTION_IDS
        if req.selected_option in BALANCE_OPTION_IDS:
            session.setdefault("selected_options", {})[req.step_key] = req.selected_option
        # 허용 외 옵션은 조용히 무시 (저장 안 함) — 환각·오타·악의적 입력 방어
    save_session(session_id, session)
    return {"approved": True, "step_key": req.step_key,
            "approved_count": len(session["approved_step_keys"]),
            "selected_option": (session.get("selected_options") or {}).get(req.step_key),
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


# ──────────────────────────────────────────────────────────────────────
# STEP 1B-3c — Page 5 (분석목적/EDA) + Page 6 (모델링) 백엔드
# ──────────────────────────────────────────────────────────────────────
# LLM 가치 영역 ③(분석목적 추천) + ⑤(모델 추천). 환각 방어:
#   - available_options / available_models 외 LLM 추천 → 코드로 필터링
#   - fit_score 1~5 범위 강제
#   - rationale_ko는 AggregatedContext(key_findings 등) 인용 권장
# 우리 시스템의 실제 범위 끝 = 추천(LLM). EDA 차트·실제 ML 학습은 STEP 2·3.

ANALYSIS_PURPOSES: list[str] = [
    "anomaly_detection",       # 이상 탐지
    "quality_classification",  # 품질 분류
    "process_optimization",    # 공정 최적화
    "predictive_maintenance",  # 예지보전
    "demand_forecasting",      # 생산량/수요 예측
    "statistical_comparison",  # 통계·SPC 비교
]

# spec-2 Part 6-4 매핑 (결정론) — 분석목적 → Function 축
_PURPOSE_FUNCTION: dict[str, str] = {
    "anomaly_detection": "maintenance",
    "quality_classification": "quality",
    "process_optimization": "process",
    "predictive_maintenance": "maintenance",
    "demand_forecasting": "reference",
    "statistical_comparison": "reference",
}


# Page 6 권고만(실행 불가) 분류용 — VRAM 초과/특수 인프라 모델
_VRAM_HEAVY_MODELS: set[str] = {"CNNClassifier", "EfficientNet", "ResNet", "ViT", "BERT"}


def _slim_ctx(ctx: dict) -> dict:
    """LLM 프롬프트 토큰 절약 — AggregatedContext에서 추천에 필요한 핵심만 추림.
    agent_records의 큰 본문은 제외 (해석은 key_findings에 이미 결정론으로 추출됨)."""
    return {
        "key_findings": ctx.get("key_findings", []),
        "function_axis_summary": ctx.get("function_axis_summary", {}),
        "stage_chain": ctx.get("stage_chain", []),
        "pipeline_constraints": ctx.get("pipeline_constraints", {}),
    }


def _collect_recommended_models(session: dict) -> list[dict]:
    """pipeline_full.stages의 node_id 들에 대해 modules.yaml.recommended_models를 합집합으로 수집.
    Page 6 추천 풀(available_models). 환각 방어 — LLM은 이 풀 안에서만 추천."""
    import yaml
    path = ROOT / "catalogs" / "modules.yaml"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        modules = yaml.safe_load(f) or {}
    pf = session.get("pipeline_full") or {}
    seen: set[tuple] = set()
    out: list[dict] = []
    for stage in pf.get("stages", []):
        node_id = stage.get("node_id")
        node_def = modules.get(node_id) or {}
        for m in node_def.get("recommended_models", []) or []:
            name = m.get("name")
            if not name: continue
            key = (name, node_id)
            if key in seen: continue
            seen.add(key)
            out.append({
                "name": name,
                "task": m.get("task"),
                "when": m.get("when"),
                "from_node": node_id,
                "advisory_only": name in _VRAM_HEAVY_MODELS,
            })
    return out


@app.get("/api/analyze/{session_id}/questions")
async def analyze_questions(session_id: str) -> dict:
    """STEP 1B-3c — 분석목적 추천 (LLM, AggregatedContext 기반).
    환각 방어 (D-91): ANALYSIS_PURPOSES 외 추천은 코드로 제거. rationale_ko는 facts 인용.
    STEP 1B-3d B1·B2: session["model"]을 LLM 호출에 전달 (D-99)."""
    from session_store import get_session
    from llm import generate
    import json
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    ctx = session.get("aggregated_context") or {}
    model = session.get("model")   # B1·B2 — 세션 model 우선 (없으면 generate가 환경변수 폴백)

    system = (
        "You are a manufacturing data analysis advisor. "
        "Given the aggregated_context (key_findings, function_axis_summary, stage_chain), "
        "recommend 1-2 analysis purposes from available_options. "
        "ABSOLUTELY DO NOT invent new purposes outside available_options. "
        "Each rationale_ko (Korean, 1-2 sentences) MUST cite a specific fact from key_findings "
        "or function_axis_summary — e.g., '제약 위반 172/800행 → 이상 탐지 적합'. "
        "Respond ONLY in JSON: "
        '{"recommendations":[{"option":"...","rank":1,"rationale_ko":"..."}]}'
    )
    prompt = json.dumps({
        "aggregated_context": _slim_ctx(ctx),
        "available_options": ANALYSIS_PURPOSES,
    }, ensure_ascii=False)

    raw = await generate(prompt, system=system, fmt_json=True, model=model)   # B1: model 전달
    # STEP 1B-3d B3 — _llm_failed 마커 + JSON 보정 (generate_json 사용)
    from llm import _try_parse_llm
    parsed = _try_parse_llm(raw)
    if parsed.get("_llm_failed"):
        return {"session_id": session_id, "recommendations": [],
                "all_options": ANALYSIS_PURPOSES,
                "llm_status": "failed", "llm_error": parsed.get("error"),
                "model_used": model}
    recs = []
    for r in parsed.get("recommendations", []) or []:
        opt = r.get("option")
        if opt in ANALYSIS_PURPOSES:
            recs.append({
                "option": opt,
                "rank": int(r.get("rank", len(recs) + 1)),
                "rationale_ko": str(r.get("rationale_ko", "")),
            })
    recs.sort(key=lambda x: x["rank"])
    return {"session_id": session_id, "recommendations": recs[:3],
            "all_options": ANALYSIS_PURPOSES, "llm_status": "ok",
            "model_used": model}


class AnalyzeSelectReq(BaseModel):
    analysis_purpose: str
    free_input: str | None = None


@app.post("/api/analyze/{session_id}/select")
async def analyze_select(session_id: str, req: AnalyzeSelectReq) -> dict:
    """STEP 1B-3c — 사용자 선택 저장 + function_axis 반환.
    AggregatedContext.user_intent (1B-2b에서 None이던 자리)를 채운다."""
    from session_store import get_session, save_session
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    fn_axis = _PURPOSE_FUNCTION.get(req.analysis_purpose, "process")
    ctx = session.get("aggregated_context") or {}
    ctx["user_intent"] = {
        "analysis_purpose": req.analysis_purpose,
        "function_axis_focus": fn_axis,
        "free_input": req.free_input,
    }
    session["aggregated_context"] = ctx
    session["analysis_purpose"] = req.analysis_purpose
    save_session(session_id, session)
    return {"session_id": session_id, "analysis_purpose": req.analysis_purpose,
            "function_axis": fn_axis, "free_input": req.free_input}


@app.get("/api/model/{session_id}/recommend")
async def model_recommend(session_id: str) -> dict:
    """STEP 1B-3c — 모델 추천 (LLM, modules.yaml recommended_models 풀 + AggregatedContext).
    환각 방어 (D-92): available_models 외 추천 제거, fit_score 1~5 강제.
    STEP 1B-3d B1·B2: session["model"]을 LLM 호출에 전달 (D-99)."""
    from session_store import get_session
    from llm import generate
    import json
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, f"session not found: {session_id}")
    available = _collect_recommended_models(session)
    user_purpose = session.get("analysis_purpose")
    ctx = session.get("aggregated_context") or {}
    model = session.get("model")   # B1·B2 — 세션 model 우선
    if not available:
        return {"session_id": session_id, "recommendations": [], "available_models": [],
                "user_purpose": user_purpose,
                "note": "modules.yaml에 매칭되는 노드의 recommended_models가 없습니다."}

    system = (
        "You are a manufacturing modeling advisor. "
        "Pick the most fitting models from available_models for the user's purpose, "
        "given facts in aggregated_context (key_findings, function_axis_summary). "
        "ABSOLUTELY DO NOT invent new model names. "
        "fit_score MUST be an integer 1-5 (5=best). "
        "rationale_ko (Korean, 1-2 sentences) MUST cite key_findings — "
        "e.g., 'imbalance ratio 2.83% → class_weight 권장'. "
        "context_reflections is a short list (strings) of facts considered. "
        "Respond ONLY in JSON: "
        '{"recommendations":[{"name":"...","fit_score":N,"rationale_ko":"...","context_reflections":["..."]}]}'
    )
    prompt = json.dumps({
        "aggregated_context": _slim_ctx(ctx),
        "user_purpose": user_purpose,
        "available_models": available,
    }, ensure_ascii=False)

    raw = await generate(prompt, system=system, fmt_json=True, model=model)   # B1: model 전달
    # STEP 1B-3d B3 — _llm_failed 마커 + JSON 보정
    from llm import _try_parse_llm
    parsed = _try_parse_llm(raw)
    if parsed.get("_llm_failed"):
        return {"session_id": session_id, "recommendations": [],
                "available_models": available, "user_purpose": user_purpose,
                "llm_status": "failed", "llm_error": parsed.get("error"),
                "model_used": model}
    name_to_meta = {m["name"]: m for m in available}
    recs = []
    for r in parsed.get("recommendations", []) or []:
        n = r.get("name")
        fs = r.get("fit_score")
        if n not in name_to_meta:
            continue
        try:
            fs_int = int(fs)
        except (TypeError, ValueError):
            continue
        if not (1 <= fs_int <= 5):
            continue
        meta = name_to_meta[n]
        recs.append({
            "name": n,
            "fit_score": fs_int,
            "rationale_ko": str(r.get("rationale_ko", "")),
            "context_reflections": list(r.get("context_reflections", []))[:5],
            "task": meta.get("task"),
            "when": meta.get("when"),
            "from_node": meta.get("from_node"),
            "advisory_only": meta.get("advisory_only", False),
        })
    recs.sort(key=lambda x: -x["fit_score"])
    return {"session_id": session_id, "recommendations": recs,
            "available_models": available, "user_purpose": user_purpose,
            "llm_status": "ok", "model_used": model}


@app.get("/")
async def root() -> FileResponse:
    """더미 대시보드 서빙."""
    if FRONTEND.exists():
        return FileResponse(str(FRONTEND))
    raise HTTPException(404, "frontend/index.html not found")
