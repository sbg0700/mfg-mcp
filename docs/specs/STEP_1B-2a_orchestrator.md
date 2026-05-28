# STEP 1B-2a 구현 명세서 — Resumable Orchestrator (Claude Code 인계용)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정했고, 이 문서대로 본진(`~/FINAL/manufacturing-mcp/`)에서 구현한다.
> **작성**: 2026-05-28. STEP 1B-1(Module Catalog + Planner constraints/module_context + Validator 5종) 완료·push 직후.

---

## 0. 시작 전 필독 (컨텍스트 로딩)

구현 전 반드시 다음을 순서대로 읽어 맥락을 흡수한다.

1. `CLAUDE.md` — 설계 헌법 (절대 규칙). 다른 모든 것에 우선.
2. `docs/decisions.md` — 결정 이력 D-01~D-50. 특히 D-38~D-40(step_key 승인), D-43~D-50(1B-1).
3. `docs/0_project_blueprint_v5.md` Part 2-5(Resumable Orchestrator 의사코드), Part 2-6(빈 슬롯 정책), Part 2-7(박스 안 모듈 통합), Part 4-5(LLM judge).
4. `docs/0_variable_index_v5.md` §8(자료구조 8종), §9(API).

### 절대 어기면 안 되는 원칙 (헌법 요약)
- **"LLM은 제안, 규칙이 결정"**. LLM은 해석·순서·이유·알람만. 작업 선택·변환·검증·흐름제어는 결정론.
- **외부 API 호출 절대 금지**. 로컬 Ollama만.
- **모달리티 5번째 추가 금지**.
- **OPERATION_PERMISSION 12종 외 새 작업을 LLM이 생성 불가**.
- **`★`(별표) 마크업 사용 금지**.

---

## 1. STEP 1B-2a 범위 (이번 작업)

STEP 1B-2는 둘로 나눴고, 이번은 **1B-2a (Orchestrator + 미업로드 알람)**.
Context Aggregator는 1B-2b(다음)로 분리 — Orchestrator가 돌아야 의미가 있기 때문.

```
STEP 1B-2a (이번)  Resumable Orchestrator + llm_judge_data_necessity
STEP 1B-2b (다음)  Context Aggregator (결정론, 4단 판단 기록 → EDA/모델링 전파)
STEP 1B-3 (이후)  Mini UI 6 페이지 + SSE
```

### 1B-2a에서 만드는 것
1. **세션 상태 머신** (`backend/session_store.py`, 인메모리) — 파이프라인 진행 상태 저장/조회
2. **`POST /api/execute_pipeline`** — 여러 Stage·Module을 순회 처리. L2/L3에서 suspend.
3. **`GET /api/pipeline/{session_id}/status`** — 진행 상태 폴링 조회
4. **`POST /api/pipeline/{session_id}/approve`** — step_key 단건 승인 후 resume
5. **`llm_judge_data_necessity`** — 미업로드 모듈 알람 (LLM은 알람만, 결정은 사용자)
6. (보조) **`POST /api/sessions/create`** + pipeline_full 주입 — 테스트용 세션 생성

### ★중요 방법론 결정 (claude.ai 확정)★
- **SSE 아님, 폴링이다.** blueprint 의사코드는 SSE+blocking(`wait_for_approval`)이지만,
  1B-2a는 **suspend-and-return + 폴링**으로 구현한다 (SSE는 1B-3 UI 때 얹음).
  → `execute_pipeline`은 L2/L3 만나면 **blocking 하지 않고**, 상태를 `awaiting_approval`로
    저장하고 **즉시 응답 반환**한다. 사용자가 `/approve` 후 `/execute_pipeline`을 **다시 호출**하면
    `completed_*`를 skip하며 resume.
- **세션 상태는 인메모리** (lineage와 동일 정책. postgres 이전은 Sprint 2).

---

## 2. 자료구조 — PipelineSession (인메모리)

`backend/session_store.py` 신규. 모듈 전역 dict에 세션 저장 (lineage의 `_STORE` 패턴 동일).

```python
# backend/session_store.py
from __future__ import annotations
import uuid
from typing import Any
from collections import defaultdict

_SESSIONS: dict[str, dict] = {}

def create_session(pipeline_full: dict) -> str:
    """pipeline_full(1-1+1-2 출력)을 받아 세션 생성. session_id 반환."""
    sid = str(uuid.uuid4())
    _SESSIONS[sid] = {
        "session_id": sid,
        "pipeline_full": pipeline_full,
        "status": "created",                 # created|running|awaiting_approval|completed|error
        "approved_step_keys": [],            # 누적 (list — set은 JSON 직렬화 안 됨)
        "completed_stage_orders": [],        # resume 시 skip
        "completed_module_keys": [],         # resume 시 skip
        "accumulated_context": [],           # Stage별 요약 누적 (1B-2b Aggregator가 사용)
        "module_results": {},                # module_key -> {profile, plan, execution, validation}
        "pending": None,                     # 현재 멈춘 지점 {stage_order, module_key, step_key, ...}
        "alarms": [],                        # 미업로드 알람 기록
    }
    return sid

def get_session(sid: str) -> dict | None:
    return _SESSIONS.get(sid)

def save_session(sid: str, session: dict) -> None:
    _SESSIONS[sid] = session
```

> `approved_step_keys` 등은 set이 아니라 list로 저장 (JSON 직렬화 위해). 멤버십 검사는 `in`으로.

---

## 3. 작업 1 — `POST /api/execute_pipeline` (Resumable, 폴링형)

### 입력
```json
{ "session_id": "..." }
```
세션은 미리 `/api/sessions/create`로 만들어져 있고, 그 안에 `pipeline_full`이 있음.

### pipeline_full 구조 (1-1 + 1-2 출력 — blueprint Part 2-3)
```python
{
  "line_id": "module_3_polymer_electronic",
  "stages": [
    { "stage_order": 0, "node_id": "injection_molding",
      "modules": [
        { "index": 0, "function": "process", "dataset_role": "injection_optimize",
          "datalake_id": "cnc_machine_injection", "constraints": {"1ST INJECTION VELOCITY":[40,70]} },
        { "index": 1, "function": "maintenance", "dataset_role": "mold_anomaly",
          "datalake_id": null, "constraints": {} }          # 미업로드
      ] }
  ]
}
```
> **datalake_id 단순화 (1B-2a)**: blueprint는 DataLakeEntry catalog 조회(`entry.data_path`)지만,
> 1B-2a에서는 **datalake_id = 기존 dataset_id로 직접 사용**한다 (예: "cnc_machine_injection").
> Data Lake catalog 레이어는 STEP 1B-3/3에서 도입. 지금은 기존 4 모달리티 데이터셋 이름을 그대로 쓴다.
> modality는 module에 `modality` 필드를 두거나, node_id로 추론 (아래 4-1 참조).

### 로직 (의사코드 — blueprint Part 2-5를 폴링형으로 변형)
```python
@app.post("/api/execute_pipeline")
async def execute_pipeline(req):  # req.session_id
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(404, "session not found")
    session["status"] = "running"

    for stage in session["pipeline_full"]["stages"]:
        if stage["stage_order"] in session["completed_stage_orders"]:
            continue   # resume: 이미 끝난 stage skip

        # (A) 미업로드 모듈 알람 — 단, 이미 처리한 stage면 재알람 안 함
        missing = [m for m in stage["modules"] if m.get("datalake_id") is None]
        uploaded = [m for m in stage["modules"] if m.get("datalake_id")]
        if missing and stage["stage_order"] not in [a["stage_order"] for a in session["alarms"]]:
            alarm = await llm_judge_data_necessity(stage, missing, uploaded)
            session["alarms"].append({"stage_order": stage["stage_order"], "alarm": alarm})
            # 알람은 '기록'만 — 사용자 결정은 폴링으로 status 보고 판단. blocking 안 함.

        # (B) 업로드된 모듈만 처리
        for module in uploaded:
            module_key = f"{stage['stage_order']}.{module['index']}"
            if module_key in session["completed_module_keys"]:
                continue   # resume skip

            dataset_id = module["datalake_id"]
            modality = _resolve_modality(module)         # 4-1 참조
            constraints = module.get("constraints", {})

            # Inspector
            profile = await run_inspect(dataset_id, modality=modality)
            # Planner (module_context + constraints. stage_context는 1B-2b에서 누적 주입)
            plan = await run_plan(profile, constraints=constraints,
                                  module_context={"node_id": stage["node_id"],
                                                  "function": module["function"]})

            # Executor — L2/L3 step이 승인 안 됐으면 suspend-and-return
            approved = set(session["approved_step_keys"])
            unapproved = [s for s in plan["steps"]
                          if s["permission_level"] != "L1" and s.get("step_key") not in approved]
            if unapproved:
                # ★suspend: blocking 하지 않고 상태 저장 후 즉시 반환 (폴링형)
                session["status"] = "awaiting_approval"
                session["pending"] = {
                    "stage_order": stage["stage_order"], "module_key": module_key,
                    "dataset_id": dataset_id, "plan": plan,
                    "pending_steps": [{"step_key": s["step_key"],
                                       "operation": s["operation"],
                                       "permission_level": s["permission_level"],
                                       "semantic_group": s.get("semantic_group"),
                                       "rationale": s.get("rationale")} for s in unapproved],
                }
                save_session(req.session_id, session)
                return {"status": "awaiting_approval", "pending": session["pending"],
                        "session": _public_view(session)}

            # 전부 승인됨 → 실행
            execution = await run_execute(plan, approved_keys=approved, modality=modality)
            validation = await run_validate(execution, plan=plan, profile=profile,
                                            constraints=constraints)
            session["module_results"][module_key] = {
                "profile": profile, "plan": plan,
                "execution": execution, "validation": validation}
            session["completed_module_keys"].append(module_key)

        session["completed_stage_orders"].append(stage["stage_order"])
        session["accumulated_context"].append(   # 1B-2b Aggregator가 쓸 요약
            {"stage_order": stage["stage_order"], "node_id": stage["node_id"],
             "modules_done": [m["index"] for m in uploaded]})

    session["status"] = "completed"
    session["pending"] = None
    save_session(req.session_id, session)
    return {"status": "completed", "session": _public_view(session)}
```

### 핵심 — suspend는 blocking이 아니다
blueprint 의사코드의 `await session.wait_for_approval()`(blocking)은 **쓰지 않는다.**
대신 **unapproved step을 만나면 상태 저장 후 즉시 return.** 사용자가 `/approve`로 step_key를
승인한 뒤 **`/execute_pipeline`을 다시 호출**하면, `completed_*`를 skip하며 그 지점부터 resume.
→ 이게 폴링 모델. 단순하고 디버깅 쉬움.

---

## 4. 작업 2 — modality 해석 + 기존 Agent 재사용

### 4-1. `_resolve_modality(module)`
module에서 modality를 얻는다. 우선순위:
1. `module.get("modality")` 가 있으면 그것
2. 없으면 `node_id`로 추론 (catalogs/lines.yaml의 node→대표 modality 매핑)
   - 간단히: semiconductor_inspect/surface_inspect → inspection-image,
     order_planning → order, 그 외 → timeseries (event-log는 명시 필요)
3. 최후 폴백: "timeseries"

> 자동 modality 분류(D-40)는 여전히 미룸. 여기선 module에 modality를 명시하거나 node 매핑.
> 1B-2a 테스트는 module에 `modality` 필드를 명시하는 방식 권장.

### 4-2. 기존 Agent는 그대로 재사용
`run_inspect`, `run_plan`, `run_execute`, `run_validate`는 **이미 있는 것 호출.**
1B-1에서 plan()에 module_context/constraints 추가됨 — 그대로 활용.
execute는 approved_keys(set) 기반 — 그대로. 새 Agent 만들지 말 것.

---

## 5. 작업 3 — `GET /api/pipeline/{session_id}/status` (폴링)

```python
@app.get("/api/pipeline/{session_id}/status")
async def pipeline_status(session_id: str) -> dict:
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    return _public_view(session)   # status, pending, completed_*, module_results 요약, alarms
```

`_public_view(session)` — 세션에서 사용자에게 보여줄 필드만 추려 반환 (JSON 직렬화 가능하게).
큰 데이터(전체 profile 등)는 요약하거나 생략.

---

## 6. 작업 4 — `POST /api/pipeline/{session_id}/approve` (단건 승인)

```python
class ApproveReq(BaseModel):
    step_key: str
    stage_order: int | None = None    # 참고용 (로깅)
    module_index: int | None = None

@app.post("/api/pipeline/{session_id}/approve")
async def pipeline_approve(session_id: str, req: ApproveReq) -> dict:
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    if req.step_key not in session["approved_step_keys"]:
        session["approved_step_keys"].append(req.step_key)
    save_session(session_id, session)
    # 승인만 기록. resume은 클라이언트가 /execute_pipeline 재호출로 트리거 (폴링형).
    return {"approved": True, "step_key": req.step_key,
            "approved_count": len(session["approved_step_keys"])}
```

> blueprint의 `notify_approval`(awaiter release)은 blocking 모델 전용이라 안 씀.
> 폴링형: approve는 승인 기록만, resume은 execute_pipeline 재호출.

---

## 7. 작업 5 — `llm_judge_data_necessity` (미업로드 알람)

### 위치
`agents/planner/data_necessity.py` 신규 (또는 inspector 옆). Planner 계열 헬퍼.

### 역할 (blueprint Part 4-5, 2-6)
모듈은 있는데 datalake_id가 null(데이터 미업로드)일 때, **"이 데이터가 이 공정에 필수인가"를
LLM이 판단해 알람**. 단 **LLM은 알람 문구만 생성, 결정은 사용자.**

```python
async def llm_judge_data_necessity(stage, missing, uploaded, model=None):
    """미업로드 모듈에 대해 '필수성 알람'을 LLM이 생성. 결정은 사용자 몫.
    LLM = 알람 문구만 (환각 방어: 데이터 처리/흐름 결정에 영향 0)."""
    from llm import generate
    missing_desc = [f"{m['function']}/{m.get('dataset_role','?')}" for m in missing]
    uploaded_desc = [f"{m['function']}/{m.get('dataset_role','?')}" for m in uploaded]
    system = (
        "You are a manufacturing pipeline assistant. Some module slots in a process "
        "stage have NO data uploaded. Judge whether the missing data is likely ESSENTIAL "
        "for this stage's analysis, given the other uploaded modules. "
        "You only RAISE AN ALARM with reasoning — you do NOT decide. The user decides. "
        "Respond ONLY in JSON: {\"likely_essential\": true/false, "
        "\"alarm_ko\": \"<한국어 알람 1-2문장>\"}"
    )
    prompt = (f"stage node: {stage['node_id']}\n"
              f"missing modules: {missing_desc}\n"
              f"uploaded modules: {uploaded_desc}\n")
    raw = await generate(prompt, system=system, fmt_json=True, model=model)
    try:
        import json
        out = json.loads(raw)
        return {"likely_essential": bool(out.get("likely_essential", False)),
                "alarm_ko": out.get("alarm_ko", "데이터 미업로드 모듈이 있습니다."),
                "missing": missing_desc}
    except Exception:
        return {"likely_essential": False,
                "alarm_ko": "데이터 미업로드 모듈이 있습니다. (LLM 판단 실패 — 사용자 확인 요망)",
                "missing": missing_desc}
```

### 환각 방어 확인
- LLM은 `likely_essential`(참고) + `alarm_ko`(문구)만. **파이프라인 흐름을 바꾸지 않음.**
- 알람은 session["alarms"]에 기록만. 처리 진행/중단 결정은 사용자가 status 보고 판단.
- judge 실패해도 안전 (likely_essential=False 폴백, 알람만).

---

## 8. 절대 하지 말 것 (금지 목록)

- ❌ SSE 구현 (이번은 폴링. SSE는 1B-3)
- ❌ blocking `wait_for_approval` (suspend-and-return으로)
- ❌ Context Aggregator 구현 (1B-2b)
- ❌ 세션을 DB에 저장 (인메모리. postgres는 나중)
- ❌ 새 Agent 만들기 (기존 inspect/plan/execute/validate 재사용)
- ❌ llm_judge가 흐름을 결정하게 하기 (알람만, 결정은 사용자)
- ❌ 자동 modality 분류 (D-40 — module에 modality 명시 또는 node 매핑)
- ❌ Data Lake catalog 레이어 (1B-2a는 datalake_id=dataset_id 직접 사용)
- ❌ 1층 `/api/execute`(단일 데이터셋) 변경 — 그대로 보존. pipeline은 별도 엔드포인트.

---

## 9. 완료 검증 기준 (체크리스트)

- [ ] `POST /api/sessions/create` (pipeline_full 주입) → session_id 반환
- [ ] `POST /api/execute_pipeline` 한 stage·여러 module 처리:
  - [ ] L1만 있는 module → 바로 완료
  - [ ] L2/L3 있는 module → status=awaiting_approval + pending 반환 (blocking 안 함)
- [ ] `POST /api/pipeline/{id}/approve` step_key 승인 → approved_step_keys에 누적
- [ ] approve 후 `/api/execute_pipeline` 재호출 → 멈췄던 지점부터 resume → 완료
- [ ] resume 시 completed_module_keys/completed_stage_orders skip 동작 (중복 처리 안 함)
- [ ] 미업로드 모듈 있는 stage → alarms에 llm_judge 결과 기록
- [ ] `GET /api/pipeline/{id}/status` → 진행 상태 반환 (폴링 가능)
- [ ] 기존 `/api/execute`(1층 단일) 회귀 없음 — 그대로 동작
- [ ] 4 모달리티 중 최소 2개로 pipeline 통과 (timeseries + 하나 더)
- [ ] 전체 `python3 -m py_compile` 통과
- [ ] 외부 API 호출 0, 모달리티 4종 유지

### 테스트용 pipeline_full 예시 (검증에 사용)
```json
{ "line_id": "module_3_polymer_electronic",
  "stages": [
    { "stage_order": 0, "node_id": "injection_molding",
      "modules": [
        { "index": 0, "function": "process", "modality": "timeseries",
          "datalake_id": "cnc_machine_injection",
          "constraints": {"1ST INJECTION VELOCITY": [40, 70]} },
        { "index": 1, "function": "maintenance", "modality": "timeseries",
          "datalake_id": null, "constraints": {} }
      ] }
  ] }
```
기대: module 0은 normalize_group/remove_outlier가 L2라 awaiting_approval →
승인 후 resume → 완료. module 1(datalake_id=null)은 알람 기록 후 skip.

---

## 10. 커밋 + 인계 방식

### git 커밋 메시지 (영어, 논리 단위)
```
feat(STEP1B-2a): add in-memory PipelineSession store
feat(STEP1B-2a): add POST /api/execute_pipeline (resumable, polling-based suspend)
feat(STEP1B-2a): add pipeline status + approve endpoints
feat(STEP1B-2a): add llm_judge_data_necessity (alarm only, user decides)
docs(STEP1B-2a): record decisions + variable_index update
```

### 작업 흐름
1. 0번 필독 문서 읽기
2. 작업 1~5 순서대로 구현 (각 작업 후 문법 검증)
3. 9번 체크리스트 검증 (테스트 pipeline_full로 실제 호출)
4. 논리 단위 커밋 → push
5. `docs/decisions.md`에 D-51~ 추가
6. `docs/0_variable_index_v5.md` §8(PipelineSession 추가)·§9(엔드포인트 4개) 갱신

### 완료 후 claude.ai 세션에 보고할 것
- 9번 체크리스트 결과 (항목별)
- `backend/session_store.py` 내용
- `/api/execute_pipeline` 핵심 로직 (suspend-and-return 부분)
- 테스트 pipeline_full로 실제 호출 로그 (awaiting_approval → approve → resume → completed)
- `llm_judge_data_necessity` 함수
- `git log --oneline -6`
→ claude.ai가 검증하고 STEP 1B-2b(Context Aggregator)로 진행

---

## 부록 — 현재 코드 상태 (1B-1 완료 시점)

- `backend/main.py`:
  - `/api/execute` (POST, ExecuteReq: dataset_id/approved_keys/model/modality + constraints/module_context)
  - `/api/lines` (GET, lines.yaml 파싱), `/api/lineage` (GET)
  - run_inspect/run_plan/run_execute/run_validate import 됨
- `agents/planner/planner.py` `plan(data_profile, constraints=None, module_context=None, model=None)`
- `agents/validator/validator.py` `validate(execution, plan=None, profile=None, constraints=None)` — 5종 검증
- `agents/executor/executor.py` `execute(plan, approved_keys=set, modality)` — ExecutionResult에 output_path
- `harness/lineage.py` 인메모리 _STORE (참고 — session_store도 같은 패턴)
- `catalogs/lines.yaml` (3 Line 18 Node), `catalogs/modules.yaml` (5 Node, constraint_keys)
- step_key = "operation:semantic_group(or target_column)" (planner_schemas PlanStep.step_key property)
