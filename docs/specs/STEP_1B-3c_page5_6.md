# STEP 1B-3c 구현 명세서 — Page 5(분석목적/EDA) + Page 6(모델링) + Page 3 제약폼 개선

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정했고, 이 문서대로 본진(`~/FINAL/manufacturing-mcp/`)에서 구현한다.
> **작성**: 2026-05-28. STEP 1B-3b(Page 3·4) 완료·push 직후. STEP 1B-3의 마지막 단계.

---

## 0. 시작 전 필독 (컨텍스트 로딩)

1. `CLAUDE.md` — 설계 헌법.
2. `docs/decisions.md` — D-01~D-90. 특히 D-90(Page 3 제약 키↔컬럼명 매핑 한계 — 이번에 개선).
3. `docs/0_pipeline_ui_spec-2_v5.md` — Part 6(Page 5 분석목적/EDA), Part 7(Page 6 모델링). ★정독★.
4. `docs/0_pipeline_ui_spec-1_v5.md` — Part 1-8(LLM 가치 5영역), Part 4(Page 3 — 개선 대상).
5. STEP 1B-3a/3b 산출물(`frontend/src/`)과 1B-2b AggregatedContext.

### 절대 원칙
- 기존 백엔드 + 1B-3a/3b 프론트는 **그대로 활용.** 그 위에 얹는다.
- 외부 API 0, 모달리티 4종, `★` 마크업 금지(문서. 코드 주석 ★는 OK).
- LLM 환각 방어: available_options/available_models **외 추천 금지**, rationale은 facts(AggregatedContext) 인용 강제.

### ★이번 단계의 범위 경계 (claude.ai 확정 — 가장 중요)★
우리 시스템의 실제 구현 범위는 **"LLM이 분석 방법론·모델을 추천하는 것까지"**다.
실제 EDA 차트 데이터 생성(FFT/박스플롯 등)과 실제 ML 학습은 **STEP 2·3**이다.

| 기능 | 1B-3c에서 | 비고 |
|---|---|---|
| Page 5 분석목적 추천 (/questions) | **실동작** | AggregatedContext → LLM (가치영역 ③) |
| Page 5 분석목적 선택 (/select) | **실동작** | user_intent 갱신 |
| Page 5 EDA 차트 | **UI 골격 + mock** | 실제 차트 데이터 생성은 STEP 2·3 |
| Page 6 모델 추천 (/recommend) | **실동작** | recommended_models + 컨텍스트 → LLM (방법론 추천) |
| Page 6 실제 학습 (/train) | **UI 골격 + "STEP 3 예정"** | 실제 ML 학습은 STEP 3 |
| Page 3 제약폼 개선 (D-90) | **실동작** | 실제 컬럼명으로 제약 입력 |

→ "추천(LLM)은 진짜로 돌고, 차트·학습(엔진)은 골격." 해석 B.

---

## 1. STEP 1B-3c 범위 (이번 작업 — 3개 작업)

```
STEP 1B-3a ✅  골격 + Page 1·2
STEP 1B-3b ✅  Page 3·4 (데이터·제약 + 실행/승인/검증/집계)
STEP 1B-3c (이번)  Page 5(분석목적/EDA) + Page 6(모델링) + Page 3 제약폼 개선
─────── STEP 1B 전체 완료 ───────
이후: STEP 2(옵션카드), STEP 3(EDA·ML 실엔진 + 공장통합)
```

### 만드는 것 (작업 3개)
- **작업 1 — Page 3 제약폼 개선 (D-90 해결):** 데이터셋 선택 시 실제 컬럼 목록 조회 → 제약을 실제 컬럼에 매핑
- **작업 2 — Page 5 (분석목적/EDA):** 분석목적 추천(실동작) + 선택(실동작) + EDA 차트(골격/mock)
- **작업 3 — Page 6 (모델링):** 모델 추천(실동작) + 학습(골격)

---

## 2. 작업 1 — Page 3 제약폼 개선 (D-90 해결)

### 문제 (D-90)
현재 Page 3 제약폼은 modules.yaml의 **추상 키**(injection_velocity)를 보여주는데,
실제 데이터 컬럼명(`1ST INJECTION VELOCITY`)과 달라서 Validator가 "일치 컬럼 없음"으로 스킵.
→ 데이터셋 선택 시 **실제 컬럼 목록을 불러와**, 제약을 실제 컬럼에 걸게 한다.

### 2-1. 백엔드 — 데이터셋 컬럼 조회
데이터셋의 실제 컬럼명을 주는 엔드포인트. 기존 inspect 또는 MCP 활용:
```python
@app.get("/api/datasets/{dataset_id}/columns")
async def dataset_columns(dataset_id: str, modality: str = "timeseries") -> dict:
    """데이터셋의 실제 수치 컬럼 목록 (Page 3 제약 매핑용). 디렉터리 스캔/파일 헤더 읽기.
    데이터 비종속 — 파일 헤더에서 동적으로."""
    mcp_url = MCP_SERVERS.get(modality)
    if not mcp_url:
        return {"columns": []}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            # MCP의 inspect 또는 columns 엔드포인트 (없으면 추가). 수치 컬럼만.
            r = await c.get(f"{mcp_url}/columns", params={"dataset_id": dataset_id})
            return {"columns": r.json().get("columns", []) if r.status_code == 200 else []}
    except Exception:
        return {"columns": []}
```
> MCP 서버에 `/columns` 없으면 추가 필요 (timeseries/order는 csv 헤더에서 수치 컬럼 추출).
> 이미 inspect가 컬럼 정보를 주면 그걸 재사용해도 됨. 핵심: **실제 컬럼명을 프론트에 제공.**

### 2-2. 프론트 — 제약폼 UI 개선
```jsx
// 데이터셋 선택 시:
//   GET /api/datasets/{dataset_id}/columns → 실제 컬럼 목록
// 제약폼을 두 방식 중 하나로:
//   (A) constraint_keys(추상) 대신 실제 컬럼 드롭다운 + min/max
//       "컬럼 [1ST INJECTION VELOCITY ▼]  [40] ~ [70]  [+ 추가]"
//   (B) constraint_keys는 힌트로 두고, 각 키에 "실제 컬럼 매핑" 드롭다운 추가
// → (A) 권장 (단순, 실제 컬럼에 직접). constraint_keys는 "이런 항목 권장" 안내로만.
```
권장 UI (방식 A):
```
제약 조건 (선택한 데이터셋의 컬럼 기준)
  컬럼: [1ST INJECTION VELOCITY ▼]  [40] ~ [70]   [삭제]
  컬럼: [+ 제약 추가]
  ※ 권장 항목 (modules.yaml): injection_velocity, pack_pressure, cycle_time (참고)
```
- 데이터셋 선택 전엔 "데이터셋을 먼저 선택하세요"
- 컬럼 드롭다운 = 실제 데이터 컬럼 (GET columns 결과)
- constraints = `{실제컬럼명: [min, max]}` → pipeline_full에 저장
- → 이제 Validator가 실제 컬럼을 찾아 172/800 검출 (D-90 해결)

### 검증
- [ ] cnc_machine_injection 선택 → 실제 컬럼 목록 (1ST INJECTION VELOCITY 등) 드롭다운
- [ ] `1ST INJECTION VELOCITY`에 [40,70] → Page 4 실행 → **constraint_violation 172/800** (스킵 아님)

---

## 3. 작업 2 — Page 5: 분석목적 + EDA (spec-2 Part 6)

### URL / 동작
`/pipeline/analyze?session=<id>` → 진입 시 분석목적 추천 → 선택 → EDA(골격) → Page 6

### 3-1. 분석목적 추천 (실동작 — LLM 가치영역 ③)
백엔드 신규:
```python
@app.get("/api/analyze/{session_id}/questions")
async def analyze_questions(session_id: str) -> dict:
    """AggregatedContext 보고 분석목적 추천 (LLM). available_options 외 추천 금지."""
    session = get_session(session_id)
    if session is None: raise HTTPException(404, ...)
    ctx = session.get("aggregated_context") or {}
    from llm import generate
    AVAILABLE = ["anomaly_detection", "quality_classification", "process_optimization",
                 "predictive_maintenance", "demand_forecasting", "statistical_comparison"]
    system = ("제조 데이터 분석 어드바이저. facts(aggregated_context) 보고 분석 목적 1~2개 추천. "
              "available_options 외 추천 금지. rationale은 facts 인용. "
              'JSON: {"recommendations":[{"option":..,"rank":1,"rationale_ko":..}], "all_options":[..]}')
    prompt = json.dumps({"aggregated_context": _slim(ctx), "available_options": AVAILABLE},
                        ensure_ascii=False)
    raw = await generate(prompt, system=system, fmt_json=True)
    try:
        out = json.loads(raw)
        # 환각 방어: available 외 제거
        recs = [r for r in out.get("recommendations", []) if r.get("option") in AVAILABLE]
        return {"recommendations": recs, "all_options": AVAILABLE}
    except Exception:
        return {"recommendations": [], "all_options": AVAILABLE}
```
> `_slim(ctx)` — AggregatedContext에서 key_findings/function_axis_summary만 추려 LLM에 (토큰 절약, harness ② 정신).
> 환각 방어: AVAILABLE 6개 외 옵션은 코드로 필터링 (LLM이 새 목적 만들어도 제거).

### 3-2. 분석목적 선택 (실동작)
```python
class SelectReq(BaseModel):
    analysis_purpose: str
    free_input: str | None = None

@app.post("/api/analyze/{session_id}/select")
async def analyze_select(session_id: str, req: SelectReq) -> dict:
    session = get_session(session_id)
    if session is None: raise HTTPException(404, ...)
    # AggregatedContext.user_intent 갱신 (1B-2b에서 None이던 자리)
    ctx = session.get("aggregated_context") or {}
    ctx["user_intent"] = {"analysis_purpose": req.analysis_purpose, "free_input": req.free_input}
    session["aggregated_context"] = ctx
    session["analysis_purpose"] = req.analysis_purpose
    save_session(session_id, session)
    # EDA 실제 실행은 STEP 2·3. 여기선 user_intent 저장 + function축 결정만.
    return {"session_id": session_id, "analysis_purpose": req.analysis_purpose,
            "function_axis": _purpose_to_function(req.analysis_purpose)}
```
`_purpose_to_function` — spec-2 Part 6-4 매핑 (결정론):
```python
_PURPOSE_FUNCTION = {
    "anomaly_detection": "maintenance", "quality_classification": "quality",
    "process_optimization": "process", "predictive_maintenance": "maintenance",
    "demand_forecasting": "reference", "statistical_comparison": "reference",
}
```

### 3-3. 프론트 — Page 5 UI
```jsx
// 1. GET /api/analyze/{id}/questions → 추천 목적 라디오 (rank 표시 + rationale)
//    + available_options 전체 라디오 + "직접 입력"
// 2. 선택 → POST /api/analyze/{id}/select → function_axis 받기
// 3. EDA 결과 영역 (골격):
//    - 선택된 function_axis 기준 spec-2 Part 6-4 차트 "자리" 표시
//    - 실제 차트는 mock 또는 "EDA 차트는 다음 단계(STEP 2·3)에서 실제 데이터로 생성됩니다" 안내
//    - AggregatedContext.key_findings를 텍스트로 보여줌 (이건 실데이터 — 이미 있음)
// 4. [다음 → Page 6]
```
> EDA 차트는 골격 — recharts로 mock 데이터 차트를 1~2개 보여주거나, key_findings를
> 차트 대신 요약으로. "실제 차트 생성은 STEP 2·3" 명시. **추천·function축 결정까지가 실동작.**

### 검증
- [ ] 진입 시 분석목적 추천 (LLM, AggregatedContext 기반, rationale 한국어)
- [ ] available_options 외 추천 안 됨 (환각 방어)
- [ ] 선택 → user_intent 갱신 + function_axis 반환
- [ ] EDA 영역 골격 + key_findings 표시 + "차트는 STEP 2·3" 안내
- [ ] [다음] Page 6 이동

---

## 4. 작업 3 — Page 6: 모델링 (spec-2 Part 7)

### URL / 동작
`/pipeline/model?session=<id>` → 모델 추천(실동작) → 선택 → 학습(골격)

### 4-1. 모델 추천 (실동작 — 우리 범위의 핵심)
백엔드 신규:
```python
@app.get("/api/model/{session_id}/recommend")
async def model_recommend(session_id: str) -> dict:
    """AggregatedContext + modules.yaml recommended_models → LLM이 적합도(fit_score) 판단.
    available_models 외 추천 금지. ★우리 시스템의 실제 범위 끝 = 여기(추천·방법론)★."""
    session = get_session(session_id)
    if session is None: raise HTTPException(404, ...)
    ctx = session.get("aggregated_context") or {}
    purpose = session.get("analysis_purpose")
    # modules.yaml에서 관련 노드의 recommended_models 수집 (available_models 풀)
    available = _collect_recommended_models(session)   # modules.yaml 기반
    from llm import generate
    system = ("제조 모델링 어드바이저. available_models만 사용. fit_score 1~5. "
              "새 모델 생성 금지. rationale은 facts(key_findings) 인용. "
              'JSON: {"recommendations":[{"name":..,"fit_score":..,"rationale_ko":..,'
              '"context_reflections":[..]}]}')
    prompt = json.dumps({"aggregated_context": _slim(ctx), "user_purpose": purpose,
                         "available_models": available}, ensure_ascii=False)
    raw = await generate(prompt, system=system, fmt_json=True)
    try:
        out = json.loads(raw)
        names = {m["name"] for m in available}
        recs = [r for r in out.get("recommendations", [])
                if r.get("name") in names and 1 <= r.get("fit_score", 0) <= 5]
        return {"recommendations": sorted(recs, key=lambda x: -x["fit_score"]),
                "available_models": available}
    except Exception:
        return {"recommendations": [], "available_models": available}
```
환각 방어:
- available_models(modules.yaml recommended_models) 외 추천 코드로 제거
- fit_score 1~5 범위 강제
- rationale = key_findings 인용

AggregatedContext 자동 반영 (rationale에 반영되도록 프롬프트로 유도):
- 불균형 → class_weight 권장 / 결측 → 모델별 처리 / 컬럼 수 → 적합성

### 4-2. 프론트 — Page 6 UI
```jsx
// 1. GET /api/model/{id}/recommend → 추천 모델 카드 (fit_score 순)
//    카드: 모델명, ⭐순위, fit_score, rationale, context_reflections(불균형→class_weight 등)
//    + 추정 성능/시간/메모리 (modules.yaml 또는 정적 추정값)
// 2. "권고만 (실행 불가)" 섹션 — VRAM 초과 모델 (spec-2 Part 7-4): EfficientNet 등 표시만
// 3. [학습 시작] → ★골격★:
//    "모델 학습은 다음 단계(STEP 3)에서 실제로 실행됩니다" 안내 또는 mock 진행률
//    실제 train 엔드포인트 호출 ❌ (STEP 3)
```

### 4-3. 학습은 골격 (STEP 3 예정)
- "학습 시작" 버튼은 두되, 실제 ML 학습(/train)은 **구현 안 함.**
- 클릭 시: "모델 학습은 STEP 3에서 실제 데이터로 실행됩니다" 안내, 또는 mock 결과 카드(F1 추정치 등 정적).
- 이유: 실제 학습 엔진(RandomForest/XGBoost fit)은 STEP 3. 우리 범위는 추천까지.

### 검증
- [ ] 모델 추천 (LLM, recommended_models 풀 내에서, fit_score)
- [ ] available_models 외 추천 안 됨 (환각 방어)
- [ ] rationale에 AggregatedContext 반영 (불균형/결측 등)
- [ ] VRAM 초과 모델 "권고만" 표시
- [ ] [학습 시작] → 골격 (실제 학습 안 함, "STEP 3" 안내)

---

## 5. 절대 하지 말 것

- ❌ 실제 EDA 차트 데이터 생성 (FFT/박스플롯 계산 — STEP 2·3)
- ❌ 실제 ML 학습 (model fit/train — STEP 3)
- ❌ available_options/available_models 외 LLM 추천 허용 (코드로 필터)
- ❌ LLM이 fit_score 범위(1~5) 벗어나게
- ❌ 기존 백엔드/프론트 로직 변경 (엔드포인트·페이지 추가만)
- ❌ 외부 API, 5번째 모달리티, 문서 별표(★)

---

## 6. 완료 검증 기준 (체크리스트)

### 작업 1 (Page 3 개선, D-90)
- [ ] `GET /api/datasets/{id}/columns` — 실제 컬럼 목록 (디렉터리/헤더 스캔)
- [ ] Page 3 제약폼이 실제 컬럼 드롭다운으로 → cnc_machine_injection + 1ST INJECTION VELOCITY [40,70]
- [ ] Page 4 실행 시 **constraint_violation 172/800** (D-90 해결 — "일치 컬럼 없음" 아님)

### 작업 2 (Page 5)
- [ ] `GET /api/analyze/{id}/questions` — LLM 분석목적 추천 (AggregatedContext 기반)
- [ ] available_options 외 추천 안 됨 (환각 방어 코드)
- [ ] `POST /api/analyze/{id}/select` — user_intent 갱신 + function_axis
- [ ] Page 5 UI: 추천 라디오 + 선택 + EDA 골격(key_findings 표시 + "차트 STEP 2·3" 안내)

### 작업 3 (Page 6)
- [ ] `GET /api/model/{id}/recommend` — LLM 모델 추천 (recommended_models 풀, fit_score)
- [ ] available_models 외 추천 안 됨, fit_score 1~5
- [ ] rationale에 AggregatedContext(불균형/결측 등) 반영
- [ ] Page 6 UI: 모델 카드(fit_score 순) + 권고만 섹션 + 학습 골격("STEP 3")

### 통합 (end-to-end 6페이지 완성)
- [ ] Page 1 → 2 → 3 → 4 → 5 → 6 전체 흐름 브라우저 실동작:
      Line선택 → 구성 → 데이터·제약(실컬럼) → 실행·승인·검증 → 분석목적 추천·선택 → 모델 추천
- [ ] Page 3 개선 후 172/800이 Page 4에 표시
- [ ] Page 5·6 추천(LLM)이 실제로 동작 (mock 아님)
- [ ] npm run build 성공

---

## 7. 커밋 + 인계 방식

### 작업 흐름
1. 0번 필독 (특히 spec-2 Part 6·7, D-90)
2. 작업 1(Page 3 개선) → 작업 2(Page 5) → 작업 3(Page 6) 순서
3. **전체 완성 후** 6번 체크리스트 검증 (npm run dev로 Page 1~6 전체 흐름)
4. **검증 끝나고** 논리 단위 커밋 (중간 커밋·git checkout 되돌리기 금지):
   ```
   feat(STEP1B-3c): add dataset columns endpoint + Page 3 real-column constraint form (D-90)
   feat(STEP1B-3c): add analyze questions/select endpoints + Page 5 purpose/EDA
   feat(STEP1B-3c): add model recommend endpoint + Page 6 modeling (recommend live, train skeleton)
   docs(STEP1B-3c): record decisions + variable_index update
   ```
5. **push는 claude.ai 검증 후.**
6. `docs/decisions.md` D-91~ 추가 (D-90 해결 포함), `docs/0_variable_index_v5.md` §5·§9 갱신

### 완료 후 claude.ai에 보고할 것
- 6번 체크리스트 결과 (항목별)
- 백엔드 신규 엔드포인트 (columns, analyze questions/select, model recommend) 코드
- Page 3 개선 (실컬럼 제약폼) + 172/800 검증 로그
- Page 5 분석목적 추천 + Page 6 모델 추천 LLM 응답 예시 (환각 방어 확인)
- 실제 동작: Page 1~6 전체 흐름 (스크린샷 — Page 5 추천, Page 6 모델 카드, Page 4 172/800)
- `git log --oneline -8` (push 전)
→ claude.ai가 검증하고 STEP 1B 전체 완료 선언 → STEP 2로

### ★1B-2/3 교훈★
전체 완성 → 검증 → 마지막에 논리 단위 커밋. git checkout/reset 금지. push는 검증 후.
프론트는 브라우저 직접 확인. 문서 별표(★) 금지.

---

## 부록 — 현재 코드 상태 (1B-3b 완료 시점)

### 백엔드 엔드포인트
- 1층/1B-1/1B-2a/2b/3a/3b 전부 (execute_pipeline, approve, status, aggregate_context,
  sessions create/get/structure/full, lines, modules, datasets, datasets/all, models)
- MCP_SERVERS dict (4 모달리티)

### AggregatedContext (Page 5·6 입력 — 1B-2b)
```
{ session_id, pipeline_structure, pipeline_constraints,
  key_findings: [{type, stage_order, module_function, column, severity, detail}],
  function_axis_summary: {process[], quality[], maintenance[], reference[]},
  stage_chain: [{stage_order, node_id, main_findings[], downstream_implication}],
  agent_records: [...], user_intent: null ← Page 5 select가 채움 }
```

### modules.yaml recommended_models (Page 6 추천 풀)
```yaml
injection_molding:
  recommended_models:
    - { name: "RandomForestRegressor", task: regression, when: "process 최적화" }
    - { name: "IsolationForest", task: anomaly, when: "maintenance 이상감지" }
    - { name: "XGBoostClassifier", task: classification, when: "quality 양/불 판정" }
# cnc_cutting/press_forming/semiconductor_inspect/pdm 각각 recommended_models 있음
```
→ `_collect_recommended_models(session)`가 pipeline의 노드들에서 이 풀을 수집.

### 프론트 (1B-3a/3b)
- step1_line, step2_user_input_pipeline, step3_user_input_data, step4_standardize
- 라우트: / /pipeline/build /pipeline/data /pipeline/run
- 이번 추가: /pipeline/analyze (Page5), /pipeline/model (Page6)
- 공통: Breadcrumb, ModelDropdown, Toast, ModuleCard, api.js
- LLM 호출: backend llm.py generate() (Planner·judge에서 사용 중 — analyze/model도 동일 사용)

### LLM 가치 영역 (spec-1 Part 1-8) — 이번에 ③④ 실현
- ① 자연어→작업 매핑, ② 의미그룹, ③ 분석목적 추천(Page5), ④ EDA 요약(Page5),
  ⑤ 계획 이유(Planner) — 이번 1B-3c가 ③(분석목적)+모델추천 실현
