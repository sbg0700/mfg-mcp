# STEP 1B-3b 구현 명세서 — Page 3 (데이터·제약) + Page 4 (표준화 진행/승인)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정했고, 이 문서대로 본진(`~/FINAL/manufacturing-mcp/`)에서 구현한다.
> **작성**: 2026-05-28. STEP 1B-3a(Frontend 골격 + Page 1·2) 완료·push 직후.

---

## 0. 시작 전 필독 (컨텍스트 로딩)

1. `CLAUDE.md` — 설계 헌법.
2. `docs/decisions.md` — D-01~D-81. 특히 D-51~D-58(Orchestrator 폴링), D-43~D-50(constraint_keys), D-74~D-81(프론트 골격).
3. `docs/0_pipeline_ui_spec-1_v5.md` — Part 4(Page 3 데이터·제약), Part 1-5(세션), Part 1-3(API).
4. `docs/0_pipeline_ui_spec-2_v5.md` — Part 5(Page 4 표준화 진행/승인). ★폴링 폴백 명시 부분★.
5. STEP 1B-3a 산출물(`frontend/src/`)과 1B-2a/2b/2c 백엔드.

### 절대 원칙
- 기존 백엔드(1층 + 1B-1·2a·2b·2c) + 1B-3a 프론트 골격은 **그대로 활용.** 그 위에 얹는다.
- 외부 API 0, 모달리티 4종, `★` 마크업 금지(코드 주석 ★는 기존 스타일 OK).
- **이번은 Page 3·4만.** Page 5·6은 1B-3c.
- 폴링 (SSE 아님 — 1B-2a 결정 D-51 일관).

---

## 1. STEP 1B-3b 범위 + 데이터 비종속성 (먼저 못 박을 것)

```
STEP 1B-3a ✅  Frontend 골격 + Page 1(Line) + Page 2(Pipeline 구성)
STEP 1B-3b (이번)  Page 3(데이터·제약 입력) + Page 4(표준화 진행/승인)
STEP 1B-3c (다음)  Page 5(분석목적/EDA) + Page 6(모델링) — UI만, 실엔진 STEP 2·3
```

### ★데이터 비종속성 (claude.ai 확정 — 반드시 지킬 것) D-기록★
현재 `data/synthetic/`의 더미(cnc_machine_injection 등)는 **개발·검증용 임시 데이터**다.
**최종 기준은 실증 데이터셋(KAMP 등 실데이터)**이며, 더미는 실데이터로 교체될 예정이다.
- 따라서 **어떤 코드도 특정 데이터의 파일명·컬럼명·구조에 하드코딩하지 않는다.** 규칙·패턴 기반으로 동작.
- Page 3은 데이터셋 목록을 **디렉터리 동적 스캔**으로 가져온다 (이미 그렇게 구현됨 — 아래 2장 확인). 실데이터 교체 시 코드 변경 0, 파일만 바꾸면 됨.
- 체계적 데이터 관리(Data Lake `/api/datalake/*` register/metadata)는 **STEP 3에서** 도입. 1B-3b는 기존 `/api/datasets`(디렉터리 스캔) 사용.

### 1B-3b에서 만드는 것
1. **Page 3 (데이터·제약 입력)** — 각 모듈 슬롯에 데이터셋 연결(드롭다운) + constraint_keys 폼 입력 → pipeline_full 완성
2. **백엔드: `PUT /api/sessions/{id}/full`** — 완성된 pipeline_full 저장
3. **백엔드: `/api/datasets` 모달리티별 통합 조회 보강** (Page 3 드롭다운용)
4. **Page 4 (표준화 진행/승인)** — execute_pipeline 폴링 + 승인 카드 + resume + 완료/집계 표시
5. **(선택) 데이터 업로드 버튼** — 자리만. 실제 업로드 로직은 후속(범위 밖, 아래 7장)

---

## 2. 데이터 소스 — 기존 /api/datasets (디렉터리 스캔, 하드코딩 아님)

### 현재 구조 (확인됨)
`GET /api/datasets?modality=<m>` → 해당 MCP 서버의 `/datasets` 위임 → **디렉터리 스캔**:
```python
# mcp-servers/timeseries/server.py (확인됨 — 하드코딩 아님)
@app.get("/datasets")
def datasets():
    files = [f[:-4] for f in os.listdir(root) if f.endswith(".csv")] if os.path.isdir(root) else []
    return {"datasets": sorted(files)}
```
→ 데이터 비종속성 OK. 실데이터를 디렉터리에 넣으면 자동 목록화.

### 2-1. 보강 — 4 모달리티 통합 조회 (Page 3 편의)
Page 3은 모든 모달리티의 데이터셋을 한 번에 보여줘야 편하다. 통합 엔드포인트 추가:
```python
@app.get("/api/datasets/all")
async def datasets_all() -> dict:
    """4 모달리티의 데이터셋을 모달리티별로 묶어 반환 (Page 3 드롭다운용).
    각 MCP 서버의 /datasets를 모아 합침. 디렉터리 스캔이라 데이터 비종속."""
    out = {}
    for modality, mcp_url in MCP_SERVERS.items():   # 기존 MCP_SERVERS dict 재사용
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{mcp_url}/datasets")
                out[modality] = r.json().get("datasets", []) if r.status_code == 200 else []
        except Exception:
            out[modality] = []
    return {"datasets_by_modality": out}
```
> 기존 `GET /api/datasets?modality=` 는 그대로 둔다 (단일 조회). all은 추가.

---

## 3. 작업 1 — Page 3: 데이터·제약 입력 (spec-1 Part 4)

### URL / 동작
`/pipeline/data?session=<id>` → Page 2에서 만든 각 모듈 슬롯에:
1. **데이터셋 연결** (드롭다운 — 해당 모달리티 데이터셋 목록)
2. **constraint 입력** (modules.yaml의 constraint_keys 폼)
→ "다음" → pipeline_full 완성 저장 → Page 4

### 3-1. 진입 시 로드
```jsx
// 1. GET /api/sessions/{id} → pipeline_full(structure) 복원 (Page 2에서 저장한 stages)
// 2. GET /api/datasets/all → 모달리티별 데이터셋 목록
// 3. GET /api/lines → modules.yaml의 constraint_keys (또는 별도 /api/modules)
//    ※ constraint_keys는 modules.yaml에 있음. lines.yaml엔 없음.
//      → constraint_keys 조회용 엔드포인트 필요 (아래 3-4)
```

### 3-2. 모듈 슬롯별 UI (각 Stage의 각 모듈)
```
┌─ Stage 1: 사출 성형 ──────────────────┐
│  [process] 모듈                        │
│   데이터셋: [ cnc_machine_injection ▼ ] │  ← 드롭다운 (timeseries 목록)
│   제약 조건:                            │
│    injection_velocity  [40] ~ [70] mm/s │  ← constraint_keys 폼
│    pack_pressure       [  ] ~ [  ] MPa  │
│   [+ 데이터 업로드] (선택)              │  ← 자리만 (7장)
└────────────────────────────────────────┘
```
- 데이터셋 드롭다운: 모듈의 modality에 맞는 목록 (process/timeseries면 timeseries 데이터셋)
- modality 추론: 모듈 function·node로 (1B-2a `_resolve_modality` 패턴) 또는 사용자 선택
- constraint 폼: node의 constraint_keys 각각 min/max 입력란. **빈 칸 허용**(제약 없으면 비움)
- 입력한 constraint는 `{key: [min, max]}` 형태로 모듈에 저장

### 3-3. "다음" → pipeline_full 완성 저장
Page 2의 structure(데이터·제약 없음)에 데이터셋·제약을 채워 **완성된 pipeline_full** 만들기:
```jsx
// 각 모듈에 datalake_id(선택한 데이터셋) + constraints 채움
// 데이터셋 미선택 모듈 → datalake_id: null (Page 4에서 llm_judge 알람 대상)
// PUT /api/sessions/{id}/full { pipeline_full }
// → navigate(`/pipeline/run?session=${id}`)  (Page 4)
```
완성된 pipeline_full 구조 (1B-2a가 먹는 형태):
```json
{ "line_id": "...", "stages": [
  { "stage_order": 0, "node_id": "injection_molding", "modules": [
    { "index": 0, "function": "process", "modality": "timeseries",
      "datalake_id": "cnc_machine_injection",
      "constraints": {"injection_velocity": [40, 70]} }
  ]}
]}
```

### 3-4. 백엔드 보강 — constraint_keys 조회
modules.yaml의 constraint_keys를 Page 3이 폼으로 그리려면 조회 필요:
```python
@app.get("/api/modules")
async def modules_endpoint() -> dict:
    """modules.yaml 조회 (Page 3 constraint 폼 + Page 6 모델추천)."""
    import yaml, os
    path = os.path.join(ROOT, "catalogs", "modules.yaml")
    with open(path, encoding="utf-8") as f:
        return {"modules": yaml.safe_load(f)}
```

### 3-5. 백엔드 보강 — PUT /sessions/{id}/full
```python
class FullReq(BaseModel):
    pipeline_full: dict

@app.put("/api/sessions/{session_id}/full")
async def put_full(session_id: str, req: FullReq) -> dict:
    session = get_session(session_id)
    if session is None: raise HTTPException(404, "session not found")
    session["pipeline_full"] = req.pipeline_full
    session["status"] = "ready"     # 실행 준비 완료
    save_session(session_id, session)
    n_data = sum(1 for s in req.pipeline_full.get("stages", [])
                 for m in s.get("modules", []) if m.get("datalake_id"))
    return {"session_id": session_id, "status": "ready", "modules_with_data": n_data}
```

### 검증 (spec-1 Part 4)
- [ ] Page 2 structure 복원 + 모듈별 데이터셋 드롭다운
- [ ] constraint_keys 폼 (modules.yaml 기준), 빈 칸 허용
- [ ] 데이터셋 선택 + 제약 입력 → PUT /full → Page 4 이동
- [ ] 데이터 미선택 모듈 → datalake_id: null (정상, 알람 대상)

---

## 4. 작업 2 — Page 4: 표준화 진행/승인 (spec-2 Part 5) — 데모 핵심

### URL / 동작
`/pipeline/run?session=<id>` → "실행" → execute_pipeline → **폴링으로 진행 표시** →
awaiting_approval 시 **승인 카드** → approve → 재호출 resume → completed → 집계 요약

### 4-1. 실행 + 폴링 (★폴링 — SSE 아님, D-51★)
spec-2가 SSE 1차 권장하나 "폴링 폴백 가능" 명시. 우리는 1B-2a부터 폴링이므로 폴링으로 간다.
```jsx
// "실행" 클릭:
//   POST /api/execute_pipeline { session_id }
//   응답 status에 따라 분기:
//     "awaiting_approval" → 승인 카드 표시 (pending.pending_steps)
//     "completed"         → 완료 + aggregated_context 표시
//     "error"             → 에러 표시 (pre_validation blocking 등)
// 폴링(선택): 긴 작업이면 GET /api/pipeline/{id}/status 를 2~3초 간격으로.
//   (현재는 execute_pipeline이 동기적으로 한 모듈씩 처리 후 suspend하므로,
//    응답 자체가 상태. 별도 폴링 루프는 모듈이 많을 때만. 일단 응답 기반으로.)
```
> 현재 execute_pipeline은 suspend 지점까지 처리 후 응답을 준다(블로킹 아님, 즉시 반환).
> 따라서 "실행→응답"이 곧 상태 전환이다. 폴링 루프는 옵션(진행률 애니메이션용).
> status GET은 새로고침/복원 시 사용.

### 4-2. 진행 표시 (spec-2 Part 5 mockup)
Stage·Module 단위로 진행 상태 표시:
```
파이프라인 실행
┌─ Stage 1: 사출 성형 ──────────────┐
│  ✓ 검사 완료                       │
│  ✓ 계획 완료 (사전검증 통과)        │
│  ⏸ 승인 대기 (6개 작업)            │  ← awaiting_approval
└────────────────────────────────────┘
```
- completed_stage_orders / completed_module_keys로 완료 표시
- pending 있으면 현재 멈춘 모듈 강조

### 4-3. ★승인 카드 (핵심 — step_key 단건 승인)★
pending.pending_steps를 카드로. 각 작업의 operation·이유·권한 표시 + 승인 버튼:
```
┌─ 승인 필요: 사출 성형 / process 모듈 ─────────┐
│  이 작업들은 데이터를 변경합니다. 검토 후 승인:  │
│                                                  │
│  [L2] 이상치 제거 — 1ST INJECTION VELOCITY      │
│       사용자 제약 [40,70] 위반값 제거            │
│       [ 승인 ]                                   │
│                                                  │
│  [L2] 그룹 정규화 — injection_sequence (5컬럼)   │
│       시퀀스 추세 보존 z-score                   │
│       [ 승인 ]                                   │
│  ...                                             │
│  [ 전체 승인 ]  [ 선택 승인 후 계속 ]            │
└──────────────────────────────────────────────────┘
```
승인 동작:
```jsx
// 개별 승인: POST /api/pipeline/{id}/approve { step_key, stage_order, module_index }
// 전체 승인: pending_steps 전부 순회 approve
// 승인 후 "계속" → POST /api/execute_pipeline { session_id } 재호출 (resume)
//   → 다음 suspend 또는 completed
```
> 권한 색상: L2=주황(승인 권장), L3=빨강(주의). L1은 자동이라 승인 카드에 안 나옴.
> semantic_group 있으면 그룹 멤버 표시 (normalize_group의 5컬럼 등).

### 4-4. 미업로드 알람 표시
session.alarms (llm_judge 결과)를 배너로:
```
⚠ 사출 성형 Stage에 데이터 미업로드 모듈이 있습니다 (maintenance).
   "유지보수 데이터가 분석에 필수는 아닐 수 있습니다..." [무시] [Page 3에서 추가]
```
> 알람은 정보성. 사용자가 무시하거나 Page 3으로 돌아가 데이터 추가. (결정은 사용자 — 1B-2a)

### 4-5. 완료 — AggregatedContext 요약 표시
status=completed 시 aggregated_context를 보기 좋게:
```
✓ 파이프라인 완료
주요 발견 (key_findings):
  · [medium] 사용자 제약 위반 172/800행 (1ST INJECTION VELOCITY)
  · [low] 시퀀스 그룹 정규화 5건 (추세 보존)
검증: 통과 (constraint=주의, output_health=정상)
[분석 단계로 → (Page 5)]
```
- key_findings를 severity 색상으로 나열
- validator passed + checks 표시
- "다음 → Page 5" (Page 5는 1B-3c, 일단 버튼만)

### 4-6. 에러 처리 (spec 1-4)
| 케이스 | 처리 |
|---|---|
| pre_validation blocking (계획 충돌) | "계획 사전 검증 실패" + 사유 표시, 실행 중단 |
| execute 중 module 실패 | 해당 모듈 에러 표시, status=error |
| 세션 만료(404) | Page 1 리다이렉트 |
| LLM/MCP 응답 지연 | 로딩 표시 + 재시도 |

### 검증 (spec-2 Part 5)
- [ ] 실행 → awaiting_approval → 승인 카드 표시 (pending_steps)
- [ ] 개별/전체 승인 → approve 누적
- [ ] "계속" → resume → 다음 단계 또는 completed
- [ ] 완료 시 key_findings/검증 요약 표시
- [ ] 미업로드 알람 배너
- [ ] 새로고침 시 status로 현재 상태 복원

---

## 5. 공통 — 1B-3a 컴포넌트 재사용
Breadcrumb / ModelDropdown / Toast / api.js / 세션 상태 — 1B-3a 것 그대로. Page 3·4 추가만.

---

## 6. 절대 하지 말 것

- ❌ Page 5·6 구현 (1B-3c)
- ❌ SSE (폴링 — D-51)
- ❌ Data Lake `/api/datalake/*` 신규 (STEP 3 — 기존 /api/datasets 디렉터리 스캔 사용)
- ❌ 데이터 파일명·컬럼명 하드코딩 (데이터 비종속 — 디렉터리 스캔/규칙 기반)
- ❌ 기존 백엔드 로직 변경 (execute_pipeline/approve/aggregate 그대로 — 엔드포인트 추가만)
- ❌ 실제 파일 업로드 로직 (7장 — 자리만, 후속)
- ❌ 외부 API, 5번째 모달리티

---

## 7. (선택) 데이터 업로드 — 이번엔 자리만

Page 3에 "[+ 데이터 업로드]" 버튼은 두되, **실제 업로드 로직은 이번 범위 밖.**
- 버튼 클릭 시 "추후 지원 예정" 토스트 또는 비활성
- 실제 업로드(POST /api/datasets/upload + 디스크 저장)는 후속 STEP에서.
- 이유: 기존 데이터셋 선택만으로 데모 전체 흐름이 완성됨. 업로드는 제품화 단계 기능.

---

## 8. 완료 검증 기준 (체크리스트)

### 백엔드
- [ ] `GET /api/datasets/all` — 4 모달리티 데이터셋 통합 (디렉터리 스캔)
- [ ] `GET /api/modules` — modules.yaml constraint_keys 조회
- [ ] `PUT /api/sessions/{id}/full` — 완성 pipeline_full 저장, status=ready
- [ ] 기존 엔드포인트 회귀 없음 (execute_pipeline/approve/status/aggregate_context)

### Page 3
- [ ] Page 2 structure 복원 + 모듈별 데이터셋 드롭다운 (모달리티 매칭)
- [ ] constraint_keys 폼 (modules.yaml), 빈 칸 허용
- [ ] "다음" → PUT /full → Page 4 이동
- [ ] 미선택 모듈 datalake_id null 처리

### Page 4 (핵심)
- [ ] 실행 → awaiting_approval → 승인 카드 (pending_steps, operation·이유·권한)
- [ ] 개별/전체 승인 → approve → "계속" → resume → completed
- [ ] 완료 시 aggregated_context key_findings/검증 요약 표시
- [ ] 미업로드 알람 배너
- [ ] pre_validation blocking 시 에러 표시
- [ ] 새로고침 복원 (GET status)

### 통합 (end-to-end)
- [ ] Page 1 → 2 → 3 → 4 전체 흐름이 브라우저에서 실동작:
      Line선택 → 파이프라인구성 → 데이터·제약 → 실행·승인·완료
- [ ] cnc_machine_injection + constraint [40,70] → 172/800 위반이 화면 key_findings에 표시
- [ ] npm run build 성공

---

## 9. 커밋 + 인계 방식

### 작업 흐름
1. 0번 필독 (특히 spec-1 Part 4, spec-2 Part 5)
2. 백엔드 보강 → Page 3 → Page 4 순서
3. **전체 완성 후** 8번 체크리스트 검증 (npm run dev로 Page1~4 전체 흐름 실제 클릭)
4. **검증 끝나고** 논리 단위 커밋 (중간 커밋·git checkout 되돌리기 금지):
   ```
   feat(STEP1B-3b): add datasets/all, modules, sessions/full backend endpoints
   feat(STEP1B-3b): add Page 3 data binding + constraint form
   feat(STEP1B-3b): add Page 4 pipeline run with approval cards (polling)
   docs(STEP1B-3b): record decisions + variable_index update
   ```
5. **push는 claude.ai 검증 후.**
6. `docs/decisions.md` D-82~ 추가 (데이터 비종속성 명시 포함), `docs/0_variable_index_v5.md` §5·§9 갱신

### 완료 후 claude.ai에 보고할 것
- 8번 체크리스트 결과 (항목별)
- 백엔드 신규 엔드포인트 코드 (datasets/all, modules, sessions/full)
- Page 3 데이터·제약 입력 핵심 (드롭다운 + constraint 폼 + pipeline_full 조립)
- Page 4 승인 카드 + resume 핵심 코드
- 실제 동작: Page 1→2→3→4 전체 흐름 (스크린샷 또는 흐름 로그)
- 특히 awaiting_approval → 승인 → resume → completed + key_findings 172/800 화면 확인
- `git log --oneline -8` (push 전)
→ claude.ai가 검증하고 STEP 1B-3c(Page 5·6)로 진행

### ★1B-2/3a 교훈★
전체 완성 → 검증 → 마지막에 논리 단위 커밋. git checkout/reset 되돌리기 금지. push는 검증 후.
프론트는 브라우저에서 실제로 보이는지가 검증 핵심 — npm run dev로 병갑님이 직접 확인.

---

## 부록 — 현재 코드 상태 (1B-3a 완료 시점)

### 백엔드 (그대로 활용)
- `backend/main.py` 엔드포인트:
  - 1층: /api/execute, /api/inspect, /api/plan, /api/datasets(?modality=, MCP 위임 디렉터리스캔), /api/models, /api/health
  - 1B-1: /api/lines
  - 1B-2a: /api/sessions/create(line_id|pipeline_full), /api/execute_pipeline, /api/pipeline/{id}/status, /api/pipeline/{id}/approve
  - 1B-2b: /api/aggregate_context/{id}
  - 1B-3a: GET /api/sessions/{id}, PUT /api/sessions/{id}/structure
- `MCP_SERVERS`: {timeseries: ..., inspection-image: ..., event-log: ..., order: ...} dict
- session dict: session_id, pipeline_full, status, line_id, approved_step_keys[], completed_stage_orders[],
  completed_module_keys[], module_results{}, pending, alarms[], aggregated_context

### execute_pipeline 응답 구조 (Page 4가 의존)
```
awaiting_approval: { status, pending: { stage_order, node_id, module_index, module_key,
                     dataset_id, modality, plan, pending_steps: [{step_key, order, operation,
                     permission_level, semantic_group, rationale}] }, session: public_view }
completed: { status, session: public_view, aggregated_context: {5영역} }
error: { status, blocking_module, pre_validation, session }
```

### approve 응답
`{ approved: true, step_key, approved_count, stage_order, module_index }`

### aggregated_context 구조 (Page 4 완료 표시 + Page 5/6 입력)
```
{ session_id, pipeline_structure, pipeline_constraints,
  key_findings: [{type, stage_order, module_function, column, severity, detail}],
  function_axis_summary: {process[], quality[], maintenance[], reference[]},
  stage_chain: [{stage_order, node_id, main_findings[], downstream_implication}],
  agent_records: [{stage_order, module_function, inspector, planner, executor, validator}],
  user_intent: null }
```

### 프론트 (1B-3a)
- `frontend/src/`: main.jsx(라우터), App.jsx, api.js, session 상태, styles.css(Function 색상)
- components/: Breadcrumb, ModelDropdown, Toast, ModuleCard
- step1_line/LineSelectPage.jsx, step2_user_input_pipeline/{PipelineBuildPage,CatalogPanel,StageBox}.jsx
- 라우트: / (Page1), /pipeline/build (Page2), /pipeline/data (Page3 — 이번), /pipeline/run (Page4 — 이번)

### catalogs
- lines.yaml: 3 Line 18 Node 34 Module 슬롯, 각 module {function, hint_dataset}
- modules.yaml: 5 Node, function_hints + constraint_keys[{key, unit, type}] + recommended_models
- ★constraint_keys가 Page 3 제약 폼의 소스★
