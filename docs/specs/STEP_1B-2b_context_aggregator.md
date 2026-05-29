# STEP 1B-2b 구현 명세서 — Context Aggregator (Claude Code 인계용)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정했고, 이 문서대로 본진(`~/FINAL/manufacturing-mcp/`)에서 구현한다.
> **작성**: 2026-05-28. STEP 1B-2a(Resumable Orchestrator + llm_judge) 완료·push 직후.

---

## 0. 시작 전 필독 (컨텍스트 로딩)

구현 전 반드시 다음을 순서대로 읽어 맥락을 흡수한다.

1. `CLAUDE.md` — 설계 헌법 (절대 규칙).
2. `docs/decisions.md` — 결정 이력 D-01~D-58. 특히 D-51~D-58(1B-2a Orchestrator).
3. `docs/0_project_blueprint_v5.md` Part 4-4 (Context Aggregator), Part 2-5 마지막 줄 (`context_aggregator.aggregate(session)` 트리거 지점).
4. `docs/0_pipeline_ui_spec-1_v5.md` Part 1-2 (바) — **AggregatedContext 전체 스키마 (line 279~381)**. 이게 이번 작업의 출력 스펙. 정독 필수.
5. `docs/0_pipeline_ui_spec-1_v5.md` Part 1-9-7 — Context Aggregator 검증 기준.

### 절대 어기면 안 되는 원칙 (이번 작업의 생명선)
- **Context Aggregator는 LLM을 절대 호출하지 않는다.** 순수 결정론(dict 조작·임계 비교·규칙)만.
  - blueprint Part 4-4 표: "Context Aggregation — LLM 역할 **없음**, 결정론 역할 추출·구조화, 환각 위험 **0**".
  - 이게 이번 작업의 핵심 가치다. LLM이 1줄이라도 끼면 이 컴포넌트의 존재 이유가 무너진다.
- agent_records는 **원본 거의 그대로 보존** (요약하지 않음 — Page 5/6 LLM이 직접 활용).
- 같은 입력 → 같은 출력 (100% 재현. 결정론이니 당연).
- 외부 API 호출 금지, 모달리티 4종 유지.

---

## 1. STEP 1B-2b 범위 (이번 작업)

STEP 1B-2의 마지막 조각. Orchestrator(1B-2a)가 완성한 세션의 처리 기록을
**결정론으로 집계**해서 Page 5/6(EDA·모델링)이 쓸 `AggregatedContext`를 만든다.

```
STEP 1B-2a ✅  Resumable Orchestrator + llm_judge (완료)
STEP 1B-2b (이번)  Context Aggregator (결정론 집계) + /api/aggregate_context/{id}
STEP 1B-3 (다음)  Mini UI 6 페이지
```

### 1B-2b에서 만드는 것
1. **`agents/aggregator/context_aggregator.py`** (신규) — 결정론 집계 함수 `aggregate(session)`
2. **`/api/aggregate_context/{session_id}`** (GET) — AggregatedContext 생성/조회 (spec-1 API 14b)
3. **execute_pipeline 완료 시 자동 트리거** — `status=completed` 직후 aggregate 호출, 세션에 저장
4. (검증) key_findings 추출 규칙 + agent_records 보존 정합성 테스트

### 이번 작업이 "작은" 이유
1B-2a에서 이미 `session["module_results"][module_key]`에 각 모듈의
`{profile, plan, execution, validation}`을 **다 저장**하고 있다.
Aggregator는 **새 계산을 거의 안 하고**, 그 저장된 기록을 읽어서 AggregatedContext
스키마로 **재구성(추출·구조화)**만 한다. 통계 재계산 불필요(이미 before/after_stats 있음).

---

## 2. 출력 스키마 — AggregatedContext (spec-1 Part 1-2 (바) 그대로)

`docs/0_pipeline_ui_spec-1_v5.md` line 283~372의 스키마를 **그대로** 따른다. 5개 영역:

```python
{
  "session_id": str,

  # (A) 앞단 입력 그대로 보존 — 1B-2a 세션의 pipeline_full에서 추출
  "pipeline_structure": dict,      # pipeline_full의 stages 구조 (모듈 구성)
  "pipeline_constraints": dict,    # 각 module의 constraints 모음

  # (B) 결정론 추출 — key_findings (Aggregator 알고리즘의 핵심, 아래 3장)
  "key_findings": [
    { "type": str, "stage_order": int, "module_function": str,
      "column": str | None, "severity": str, ...case_specific... }
  ],

  # (C) Function 축 요약 — key_findings를 function별로 분류
  "function_axis_summary": {
    "process": [...], "quality": [...], "maintenance": [...], "reference": [...]
  },

  # (D) Stage 체인 요약 — stage별 main_findings + downstream 함의
  "stage_chain": [
    { "stage_order": int, "node_id": str,
      "main_findings": list[str], "downstream_implication": str }
  ],

  # (E) 4단 Agent 판단 기록 — 원본 거의 그대로 보존 (요약 X)
  "agent_records": [
    { "stage_order": int, "module_function": str, "dataset_role": str,
      "inspector": {deterministic_flags, modality_guess, concerns, recommended_next_steps},
      "planner": {candidate_operations, ordered_with_rationale[], llm_summary},
      "executor": {applied_steps[], rolled_back[]},
      "validator": {passed, issues, next_action} }
  ],

  # (F) Page 5 사용자 선택 후 추가 — 이번엔 None (Page 5는 1B-3/이후)
  "user_intent": None
}
```

> `user_intent`는 이번 범위에서 **항상 None.** Page 5(분석목적 선택) UI가 아직 없으므로.
> 자리만 만들어 두고 채우지 않는다.

---

## 3. 작업 1 — `aggregate(session)` 결정론 함수

### 위치
`agents/aggregator/context_aggregator.py` (신규 디렉터리 + 파일).

### 핵심 — 입력은 1B-2a 세션
```python
def aggregate(session: dict) -> dict:
    """PipelineSession → AggregatedContext (결정론, LLM 0).
    session["module_results"][module_key] = {profile, plan, execution, validation} 를
    읽어서 spec-1 Part 1-2(바) 스키마로 재구성한다."""
```

### 3-1. agent_records 구성 (영역 E) — 원본 보존
각 `module_results[module_key]`에서 4단 기록을 거의 그대로 옮긴다:
```python
record = {
  "stage_order": ...,                 # module_key "0.0"에서 또는 pipeline_full 매칭
  "module_function": module["function"],
  "dataset_role": module.get("dataset_role") or module.get("datalake_id"),
  "inspector": {
    "deterministic_flags": profile.get("deterministic_flags", []),
    "modality_guess": profile.get("modality") or "?",  # 또는 LLM 해석의 modality_guess
    "concerns": profile.get("concerns", []),            # Inspector LLM 해석에 있으면
    "recommended_next_steps": profile.get("recommended_next_steps", []),
  },
  "planner": {
    "candidate_operations": ...,        # plan에서 추출 가능한 범위 (없으면 [])
    "ordered_with_rationale": [
      {"operation": s["operation"], "rationale": s.get("rationale",""),
       "permission_level": s["permission_level"], "step_key": s.get("step_key")}
      for s in plan["steps"]
    ],
    "llm_summary": plan.get("summary", ""),
  },
  "executor": {
    "applied_steps": [
      {"step_key": r.get("step_key"), "operation": r["operation"],
       "before_stats": r.get("before_stats", {}), "after_stats": r.get("after_stats", {}),
       "lineage_id": r.get("lineage_id"), "status": r["status"]}
      for r in execution["results"]
    ],
    "rolled_back": [],                  # rollback 미구현 — 빈 list
  },
  "validator": {
    "passed": validation["passed"],
    "issues": [i.get("message","") for i in validation.get("issues",[])],
    "next_action": validation["next_action"],
  },
}
```
> 실제 필드명은 본진 코드의 profile/plan/execution/validation 구조를 **읽어서 정확히 매핑.**
> 위는 가이드. 없는 필드는 빈 값(`[]`,`""`,`None`)으로 안전 처리. KeyError 내지 말 것.

### 3-2. key_findings 추출 (영역 B) — 결정론 규칙
agent_records를 훑어 "주목할 사실"을 규칙으로 뽑는다. **임계 비교 + 규칙만** (LLM 0):

| finding type | 추출 규칙 (결정론) | severity |
|---|---|---|
| `class_imbalance` | Inspector flags에 불균형, 또는 execution에 balance_classes 적용 | minority_ratio<5%→high |
| `missing_values` | execution에 fill_missing 적용 + before_stats.nulls>0 | nulls 비율 따라 |
| `dtype_mixed` | Inspector flags에 mixed_dtype_suspected | medium |
| `transformation_applied` | execution의 각 done step (normalize_group 등) | low (정보성) |
| `validation_concern` | validation.issues 각 항목 | issue severity 따름 |
| `constraint_violation` | validation에 constraint kind issue (1B-1) | medium |

규칙 예:
```python
for record in agent_records:
    for step in record["executor"]["applied_steps"]:
        if step["operation"] == "balance_classes" and step["status"] == "done":
            key_findings.append({
              "type": "class_imbalance", "stage_order": record["stage_order"],
              "module_function": record["module_function"], "column": ...,
              "severity": "high", "detail": "클래스 불균형 보정 적용됨"})
    for issue in record["validator"]["issues"]:
        key_findings.append({
          "type": "validation_concern", "stage_order": record["stage_order"],
          "module_function": record["module_function"], "column": None,
          "severity": "medium", "detail": issue})
```
> 핵심: **모든 추출이 if/비교/순회.** LLM 호출 절대 없음. 같은 입력 → 같은 출력.

### 3-3. function_axis_summary (영역 C)
key_findings를 `module_function`(process/quality/maintenance/reference)별로 분류:
```python
function_axis_summary = {"process": [], "quality": [], "maintenance": [], "reference": []}
for f in key_findings:
    fn = f.get("module_function")
    if fn in function_axis_summary:
        function_axis_summary[fn].append(f)
```

### 3-4. stage_chain (영역 D)
stage별로 main_findings(그 stage의 finding 요약 문자열들) + downstream_implication:
```python
for stage in session["pipeline_full"]["stages"]:
    so = stage["stage_order"]
    stage_findings = [f for f in key_findings if f["stage_order"] == so]
    main = [f"{f['type']}({f['severity']})" for f in stage_findings]
    # downstream_implication: 규칙 기반 한 줄 (LLM 아님 — 템플릿)
    impl = _downstream_template(stage_findings)   # 예: "불균형 보정됨 → 분류 모델 시 class_weight 권장"
    stage_chain.append({"stage_order": so, "node_id": stage["node_id"],
                        "main_findings": main, "downstream_implication": impl})
```
> `downstream_implication`도 **LLM 아님.** finding type → 함의 문자열 매핑 테이블(템플릿).
> 예: class_imbalance → "분류 시 class_weight/SMOTE 고려". 없으면 "특이사항 없음".

### 3-5. pipeline_structure / pipeline_constraints (영역 A)
```python
pipeline_structure = session["pipeline_full"]    # 1-1+1-2 구조 그대로
pipeline_constraints = {}                         # 각 module의 constraints 모음
for stage in session["pipeline_full"]["stages"]:
    for m in stage["modules"]:
        if m.get("constraints"):
            pipeline_constraints[f"{stage['stage_order']}.{m['index']}"] = m["constraints"]
```

---

## 4. 작업 2 — `/api/aggregate_context/{session_id}` (GET)

spec-1 API 14b. Page 5/6 진입 시 호출 (지금은 직접 curl로 검증).

```python
@app.get("/api/aggregate_context/{session_id}")
async def aggregate_context_endpoint(session_id: str) -> dict:
    """세션의 처리 기록 → AggregatedContext (결정론). Page 5/6 LLM 컨텍스트 소스."""
    from session_store import get_session
    from context_aggregator import aggregate
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    # 이미 집계돼 있으면 그대로 반환 (결정론이라 재생성해도 동일하지만 캐시 활용)
    if session.get("aggregated_context"):
        return session["aggregated_context"]
    ctx = aggregate(session)
    session["aggregated_context"] = ctx
    save_session(session_id, session)
    return ctx
```
> backend sys.path에 `agents/aggregator` 추가 필요.

---

## 5. 작업 3 — execute_pipeline 완료 시 자동 트리거

blueprint Part 2-5 마지막: `session.aggregated_context = context_aggregator.aggregate(session)`.
1B-2a의 execute_pipeline에서 `status="completed"` 설정 직후에 추가:

```python
# (execute_pipeline 끝부분, 모든 stage 완료 후)
session["status"] = "completed"
session["pending"] = None
# ★Context Aggregator 자동 트리거 (결정론, LLM 0)
from context_aggregator import aggregate
session["aggregated_context"] = aggregate(session)
save_session(req.session_id, session)
return {"status": "completed", "session": public_view(session),
        "aggregated_context": session["aggregated_context"]}
```
> 자동 트리거 + `/api/aggregate_context` 둘 다 둔다. 자동은 완료 즉시, 엔드포인트는 나중 조회용.
> 결정론이라 몇 번 호출해도 동일 결과.

---

## 6. 절대 하지 말 것 (금지 목록)

- ❌ **Context Aggregator에서 LLM 호출** (이게 1순위 금지. 1줄도 안 됨)
- ❌ agent_records를 요약/축약 (원본 보존 — Page 5/6 LLM이 직접 씀)
- ❌ key_findings를 LLM으로 생성 (규칙·임계 비교만)
- ❌ downstream_implication을 LLM으로 생성 (템플릿 매핑)
- ❌ 통계 재계산 (이미 before/after_stats에 있음 — 그대로 인용)
- ❌ user_intent 채우기 (Page 5 없으니 None)
- ❌ Page 5/6 UI나 LLM 질문 생성 구현 (1B-3/이후)
- ❌ 1B-2a의 execute_pipeline 흐름 변경 (완료 직후 aggregate 호출만 추가)
- ❌ 외부 API, 5번째 모달리티

---

## 7. 완료 검증 기준 (체크리스트)

- [ ] `agents/aggregator/context_aggregator.py` `aggregate(session)` 동작
- [ ] execute_pipeline 완료 → session["aggregated_context"] 자동 생성
- [ ] `GET /api/aggregate_context/{id}` → AggregatedContext 5영역 반환
- [ ] **key_findings 추출**: 1B-2a 테스트 세션(cnc_machine_injection, constraint 위반 172행)으로:
  - [ ] constraint_violation finding 추출됨
  - [ ] transformation_applied (normalize_group들) finding 추출됨
- [ ] **agent_records 보존**: module_results 원본과 비교 — 손실 0 (spec-1 §1-9-7 기준)
- [ ] **function_axis_summary**: process/quality/maintenance/reference 4키 존재, finding 분류됨
- [ ] **stage_chain**: stage별 main_findings + downstream_implication (템플릿)
- [ ] **결정론 재현**: 같은 세션 2번 aggregate → 동일 출력 (deepequal)
- [ ] **LLM 호출 0 확인**: context_aggregator.py에 `from llm import` 또는 generate 호출 없음 (grep)
- [ ] 기존 1층 /api/execute + 1B-2a pipeline 회귀 없음
- [ ] `python3 -m py_compile` 통과

### 검증용 시퀀스 (1B-2a 테스트 재사용)
```
1) POST /api/sessions/create (cnc_machine_injection, constraints={"1ST INJECTION VELOCITY":[40,70]})
2) POST /api/execute_pipeline → awaiting_approval
3) POST /approve × N (전체 step_key)
4) POST /api/execute_pipeline → completed + aggregated_context 포함
5) GET /api/aggregate_context/{id} → 5영역 확인:
   - key_findings에 constraint_violation + transformation_applied
   - agent_records에 inspector/planner/executor/validator 다 보존
   - function_axis_summary.process에 finding 분류
6) GET 2회 → 동일 출력 (결정론)
7) grep "from llm\|generate(" context_aggregator.py → 0건 (LLM 없음 증명)
```

---

## 8. 커밋 + 인계 방식

### 작업 흐름 (1B-2a 교훈 반영)
1. 0번 필독 (특히 spec-1 Part 1-2(바) 스키마)
2. 작업 1~3 구현
3. **전체 완성 후** 7번 체크리스트 검증 (실 HTTP 호출 + grep으로 LLM 0 증명)
4. **검증 끝나고** 논리 단위로 커밋 (중간 커밋·되돌리기 하지 말 것):
   ```
   feat(STEP1B-2b): add deterministic Context Aggregator (agents/aggregator)
   feat(STEP1B-2b): auto-trigger aggregate on pipeline completion
   feat(STEP1B-2b): add GET /api/aggregate_context endpoint
   docs(STEP1B-2b): record decisions + variable_index AggregatedContext
   ```
5. **`git push`는 claude.ai 검증 후.** 검증 전엔 commit까지만, push 멈춤.
6. `docs/decisions.md` D-59~ 추가, `docs/0_variable_index_v5.md` §8(AggregatedContext) 갱신

### 완료 후 claude.ai 세션에 보고할 것
- 7번 체크리스트 결과 (항목별)
- `context_aggregator.py` 전체 (특히 LLM 없음 — grep 결과 포함)
- key_findings 추출 규칙 부분
- 실 호출 로그 (execute_pipeline → aggregated_context, GET /aggregate_context 5영역)
- 결정론 재현 테스트 결과 (2회 동일)
- `git log --oneline -6` (push 전 상태)
→ claude.ai가 검증하고 STEP 1B-3(Mini UI)로 진행

### ★중요 — 1B-2a 교훈★
1B-2a 때 중간 커밋 + git checkout 되돌리기로 혼선이 있었다. 이번엔:
- **전체 완성 → 검증 → 마지막에 논리 단위 커밋** (중간 커밋 X)
- **git checkout / reset 등 되돌리기 명령 쓰지 말 것** (꼬이면 멈추고 보고)
- **push는 claude.ai 검증 후**

---

## 부록 — 현재 코드 상태 (1B-2a 완료 시점)

- `backend/main.py`:
  - 1층: /api/execute, /api/lines, /api/lineage, /api/inspect, /api/plan, /api/datasets, /api/models, /api/modalities, /api/health
  - 1B-2a: /api/sessions/create, /api/execute_pipeline, /api/pipeline/{id}/status, /api/pipeline/{id}/approve
  - run_inspect/run_plan/run_execute/run_validate import 됨
- `backend/session_store.py`: `_SESSIONS` 인메모리, create_session/get_session/save_session.
  세션 dict: session_id, pipeline_full, status, approved_step_keys[], completed_stage_orders[],
  completed_module_keys[], accumulated_context[], module_results{}, pending, alarms[]
  → ★module_results[module_key] = {profile, plan, execution, validation} 가 Aggregator의 주 입력★
- `agents/planner/data_necessity.py`: llm_judge_data_necessity (1B-2a)
- `agents/planner/planner.py`: plan(data_profile, constraints, module_context, model)
- `agents/validator/validator.py`: validate(execution, plan, profile, constraints) — 5종 검증
- `agents/executor/executor.py`: execute(plan, approved_keys, modality) — ExecutionResult.output_path,
  results[]에 step_key/before_stats/after_stats/lineage_id/status/semantic_group
- `catalogs/modules.yaml`: 5 Node, function_hints + constraint_keys + recommended_models
  (Function 축: process/quality/maintenance/reference)
