# STEP 1B-3d 보강 명세 — LLM model 전달 + 에러 표면화 (B1·B2·B3)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> STEP 1B-3c(Page 5·6) 검증 중 발견된 버그 3개를 잡는 보강 작업. 1B-3c 커밋 전.
> **작성**: 2026-05-28. 진단 보고(Claude Code) 기반.

---

## 0. 배경 — 발견된 버그 3개 (진단 완료)

웹 드롭다운에서 gemma4:26b를 골라도 실제론 e4b로 추론됨 (`ollama ps`로 확인). 진단 결과:

| 버그 | 위치 | 원인 |
|---|---|---|
| **B1** | `/api/analyze/{id}/questions`, `/api/model/{id}/recommend` | model 파라미터 안 받고 `generate()`에 안 넘김 → 항상 OLLAMA_MODEL(e4b) |
| **B2** | `ModelDropdown.jsx` + 프론트 전반 | 드롭다운 `selected`가 로컬 useState에만 살고, 어떤 API 호출에도 안 실림 |
| **B3** | `backend/llm.py` generate() | HTTP 에러를 `{"_llm_error":..}` JSON으로 위장 반환 → 호출부 `json.loads` 성공 → LLM 실패가 "빈 결과"로 둔갑. 재시도 없음. 별개로, 소형 모델(e4b)이 깨진 JSON 출력 시 `json.loads` 실패도 처리 안 됨 |

정상인 부분 (건드리지 말 것): Inspector/Planner/llm_judge는 model을 제대로 받아 전달함(Diag 2). main.py의 /api/execute, /api/execute_pipeline도 req.model을 chain 끝까지 전달함. ExecuteReq/ExecutePipelineReq는 이미 `model: str | None = None` 필드 보유.

---

## 1. 확정된 설계 (claude.ai)

- **B2 해결 방식 = 세션에 model 저장 (가)**: model을 매 호출에 싣는 대신, **세션이 자기 model을 기억**한다. "이 세션은 어떤 두뇌(model)로 도는가"를 세션 수준에서 결정.
- **B3 해결 범위 = 전부 (A)**: 에러 표면화 + JSON 재시도 + JSON 보정 모두.

### 흐름 (B2 적용 후)
```
드롭다운 26b 선택 → PUT /sessions/{id}/model {model:"gemma4:26b"} → session["model"]="gemma4:26b"
이후 모든 LLM 호출(execute_pipeline / analyze / model recommend)이 session["model"]을 읽어 generate(model=...)
→ 실제 26b로 추론
```

---

## 2. B1 — /analyze, /model에 model 전달

### 2-1. 두 엔드포인트가 세션의 model을 사용
GET 엔드포인트이므로 query param도 허용하되, **세션에 저장된 model을 우선** 사용 (B2와 통합):
```python
@app.get("/api/analyze/{session_id}/questions")
async def analyze_questions(session_id: str) -> dict:
    session = get_session(session_id)
    if session is None: raise HTTPException(404, ...)
    model = session.get("model")    # ← 세션의 model (B2)
    ...
    raw = await generate(prompt, system=system, fmt_json=True, model=model)   # ← 전달 (B1)
```
```python
@app.get("/api/model/{session_id}/recommend")
async def model_recommend(session_id: str) -> dict:
    session = get_session(session_id)
    if session is None: raise HTTPException(404, ...)
    model = session.get("model")    # ← 세션의 model
    ...
    raw = await generate(prompt, system=system, fmt_json=True, model=model)   # ← 전달
```
> generate()는 `model=None`이면 OLLAMA_MODEL(e4b)로 폴백하므로, 세션에 model 없으면 기본값 — 안전.

---

## 3. B2 — 세션에 model 저장 + 모든 LLM 호출이 세션 model 사용

### 3-1. 세션 생성 시 model 저장
`sessions/create`에 model 받기 (선택적, 기본 None → 백엔드 폴백):
```python
class CreateSessionReq(BaseModel):
    line_id: str | None = None
    pipeline_full: dict | None = None
    model: str | None = None        # ← 추가

@app.post("/api/sessions/create")
async def sessions_create(req: CreateSessionReq) -> dict:
    ...
    if req.model:
        session["model"] = req.model
    save_session(sid, session)
    return {"session_id": sid, "status": "created", "line_id": ..., "model": session.get("model")}
```

### 3-2. 세션 model 갱신 엔드포인트 (드롭다운 변경 시)
```python
class ModelReq(BaseModel):
    model: str

@app.put("/api/sessions/{session_id}/model")
async def session_put_model(session_id: str, req: ModelReq) -> dict:
    session = get_session(session_id)
    if session is None: raise HTTPException(404, "session not found")
    session["model"] = req.model
    save_session(session_id, session)
    return {"session_id": session_id, "model": req.model}
```

### 3-3. execute_pipeline이 세션 model 사용
현재 execute_pipeline은 `req.model`(ExecutePipelineReq.model)을 쓰는데, 이게 프론트에서 안 실림.
→ **세션의 model을 우선 사용**하도록:
```python
@app.post("/api/execute_pipeline")
async def execute_pipeline(req: ExecutePipelineReq) -> dict:
    session = get_session(req.session_id)
    ...
    model = session.get("model") or req.model   # ← 세션 model 우선, 없으면 req.model, 없으면 generate가 폴백
    # 이후 run_inspect/run_plan/llm_judge 호출에 model=model 전달 (이미 chain 있음)
```
> /api/execute(단건)도 동일 패턴으로 세션 개념 없으면 req.model 유지. execute_pipeline만 세션 model 적용.

### 3-4. 프론트 — 드롭다운 선택을 세션에 반영
ModelDropdown이 세션 컨텍스트를 알아야 한다. 현재 세션 id는 URL(?session=)이나 세션 상태에 있음.
```jsx
// ModelDropdown.jsx
// onChange 시:
//   1. setSelected(value)  (로컬 표시)
//   2. 현재 세션 id가 있으면 → PUT /sessions/{sid}/model {model: value}
//      (세션 id는 App 세션 상태 또는 URL query에서)
// 세션 생성(Page 1) 시: POST /sessions/create에 현재 selected model 포함
```
- 세션 id 접근: 1B-3a의 세션 상태(App.jsx session 상태) 또는 라우트 query. 기존 구조 활용.
- 세션 없을 때(Page 1 진입 전) 드롭다운 변경 → 로컬만, 세션 생성 시 반영.
- 세션 있을 때 변경 → PUT으로 즉시 세션 갱신.

### 3-5. (선택) 세션 model을 화면에 반영
Breadcrumb나 페이지 상단에 "현재 세션 모델: gemma4:26b" 표시하면 사용자가 명확. (선택)

---

## 4. B3 — LLM 에러 표면화 + JSON 재시도 + 보정

### 4-1. generate() — 에러를 위장하지 말 것
현재 HTTP 에러를 `{"_llm_error":..}` 정상 JSON으로 반환 → 호출부가 못 알아챔.
→ **명확한 실패 신호**로. 두 방식 중 (B 권장):
- (A) 예외를 다시 raise → 호출부가 try/except로 잡음
- **(B) 구조화된 실패 객체 반환 + 호출부가 체크** (기존 "파이프라인 안 죽음" 정신 유지하며 표면화)

(B) 방식:
```python
async def generate(prompt, system=None, fmt_json=False, model=None) -> str:
    payload = {...}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
            r.raise_for_status()
            return r.json().get("response", "")
        except httpx.HTTPError as e:
            # 위장하지 말고 명확한 마커. 호출부가 _llm_failed를 반드시 체크.
            return json.dumps({"_llm_failed": True, "error": str(e),
                               "hint": "ollama 컨테이너/모델(pull)/타임아웃 확인"})
```
> `_llm_failed: True` 마커를 명확히. 호출부는 이 마커를 체크해서 "LLM 실패"를 구분.

### 4-2. _safe_json_parse 헬퍼 (재시도 + 보정)
새 헬퍼 (llm.py 또는 공통 유틸). generate 호출 + JSON 파싱을 묶어 재시도·보정:
```python
async def generate_json(prompt, system=None, model=None, retries=2) -> dict:
    """generate + 견고한 JSON 파싱. 실패 시 재시도. 최종 실패 시 {"_llm_failed": True} 반환.
    소형 모델(e4b)의 깨진 JSON·HTTP 에러를 모두 흡수."""
    last_err = None
    for attempt in range(retries + 1):
        raw = await generate(prompt, system=system, fmt_json=True, model=model)
        # HTTP 에러 마커 체크
        try:
            probe = json.loads(raw)
            if isinstance(probe, dict) and probe.get("_llm_failed"):
                last_err = probe.get("error", "llm failed")
                continue   # 재시도
        except Exception:
            pass
        # JSON 보정 시도
        parsed = _coerce_json(raw)
        if parsed is not None:
            return parsed
        last_err = "json parse failed"
    return {"_llm_failed": True, "error": last_err or "unknown"}

def _coerce_json(raw: str):
    """코드펜스/앞뒤 텍스트 제거 후 JSON 파싱 시도. 실패 시 None."""
    if not raw: return None
    s = raw.strip()
    # ```json ... ``` 펜스 제거
    if s.startswith("```"):
        s = s.strip("`")
        if s.startswith("json"): s = s[4:]
    # 첫 { ~ 마지막 } 추출
    import re
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m: s = m.group(0)
    try:
        return json.loads(s)
    except Exception:
        return None
```
> 재시도가 핵심 — 소형 모델은 매번 다르게 답하므로, 깨진 JSON이면 다시 부르면 대개 성공.
> retries=2 (총 3회 시도). 타임아웃 누적 주의 — 각 호출 TIMEOUT 유지.

### 4-3. 호출부가 LLM 실패를 표면화
analyze_questions, model_recommend, Planner, llm_judge가 `generate_json` 사용하도록 교체.
실패 시 사용자에게 명확히:
```python
result = await generate_json(prompt, system=system, model=model)
if result.get("_llm_failed"):
    return {"recommendations": [], "all_options": ANALYSIS_PURPOSES,
            "llm_error": result.get("error"), "llm_status": "failed"}
# 정상: 환각 방어 필터 적용
recs = [r for r in result.get("recommendations", []) if r.get("option") in ANALYSIS_PURPOSES]
...
```
프론트: `llm_status === "failed"`면 "LLM 응답 실패 (재시도/모델 확인)" 표시 — 빈 결과와 구분.

> Planner/judge도 generate_json으로 교체하되, 기존 폴백("규칙 기반 계획") 유지 — LLM 실패해도 파이프라인은 진행.

---

## 5. 검증 (26b 실동작 포함)

### B1·B2
- [ ] sessions/create에 model 저장, PUT /sessions/{id}/model 갱신
- [ ] 드롭다운에서 26b 선택 → 세션 model=gemma4:26b
- [ ] Page 4 실행 → `docker exec mfg-ollama ollama ps`에 **gemma4:26b 로드 확인** (e4b 아님)
- [ ] Page 5·6 추천도 26b로 (세션 model 사용)
- [ ] e4b 선택 시 e4b로 (회귀 없음)

### B3
- [ ] LLM 정상 시 추천 정상 동작 (e4b·26b 둘 다)
- [ ] LLM 깨진 JSON 시 재시도로 복구 (e4b에서 가끔 발생하던 Expecting ',' 오류 완화)
- [ ] LLM 다운/잘못된 모델명 시 → "빈 결과" 아니라 "LLM 실패" 명확 표시
- [ ] Planner/judge는 실패해도 규칙 기반 폴백으로 파이프라인 진행

### 통합
- [ ] e4b: Page 1~6 전체 흐름 정상
- [ ] 26b: 드롭다운 26b 선택 후 Page 4 실행 → 26b 추론 (느려도 동작) → ollama ps 확인
- [ ] npm run build 성공

### ★26b 속도 관찰 (기록용)★
- 26b(17GB)는 8GB VRAM 초과 → 대부분 CPU 오프로딩 → 느림 (추론 1회 수십 초~분 가능). 정상.
- e4b(9.6GB)도 8GB 초과 → 일부 CPU (`offloaded 42/43 to GPU`, CPU 6.6GB). e4b가 26b보다 빠름.
- GPU 우선 할당은 Ollama 자동 (최대한 GPU, 넘치면 CPU). 코드로 강제 불가 — 물리 8GB 한계.
- 측정: e4b vs 26b 추론 시간 비교해서 decisions에 기록 (영업/배포 권장사양 근거).

---

## 6. 절대 하지 말 것
- ❌ Inspector/Planner/judge의 정상 model chain 변경 (이미 정상)
- ❌ generate() 에러 시 파이프라인 죽이기 (표면화하되 폴백 유지)
- ❌ 모델명 하드코딩 (세션/환경변수/요청 파라미터로만)
- ❌ Page 5·6 기능 자체 변경 (model 전달·에러 처리만 보강)
- ❌ 외부 API, 문서 별표(★)

---

## 7. 커밋 + 인계
이건 1B-3c와 별개 보강이므로 **1B-3c 커밋과 함께 또는 직후**. 권장: 1B-3c 먼저 커밋 후 이 보강을 별도 커밋.
```
fix(STEP1B-3d): pass session model to analyze/model endpoints (B1)
fix(STEP1B-3d): store model in session + ModelDropdown updates session (B2)
fix(STEP1B-3d): surface LLM errors + JSON retry/coerce, no more silent empty (B3)
docs(STEP1B-3d): record D-91~ model-passing fixes + 8GB VRAM model strategy
```
> 또는 1B-3c 4개 커밋 + 이 보강을 묶어서. claude.ai와 상의.

### 완료 후 보고
- B1·B2·B3 수정 코드 (generate_json, 세션 model, 엔드포인트)
- **26b 실동작 증거**: 드롭다운 26b → ollama ps에 26b 로드 스크린샷/로그
- e4b vs 26b 추론 시간 비교 (대략)
- LLM 실패 시 "실패" 표시되는지 (위장 안 됨)
- git log (push 전)

### ★모델 전략 정정 (중요 — decisions에 기록)★
기존 "운영=26b / 개발=e4b" 기록을 정정:
- **8GB VRAM(RTX 3070) 현실**: e4b(9.6GB)도 초과 → 일부 CPU. 26b(17GB)는 대부분 CPU → 매우 느림.
- **데모/개발 = e4b** (8GB에서 그나마 현실적), **26b 운영 = 24GB+ GPU 전제** (RTX 4090/A100 등).
- 영업 시 "운영은 큰 GPU"를 전제로. 8GB 데모 머신에서 26b 자랑 금지.

---

## 부록 — 현재 정상 chain (참고, 건드리지 말 것)
```
agents/inspector/inspector.py  inspect(..., model)  → generate(..., model=model) ✓
agents/planner/planner.py       plan(..., model)     → generate(..., model=model) ✓
agents/planner/data_necessity.py llm_judge(..., model) → generate(..., model=model) ✓
main.py /api/execute, /api/execute_pipeline → req.model을 chain 전달 ✓
ExecuteReq/ExecutePipelineReq.model: str|None=None ✓
```
B1·B2는 이 정상 chain에 "세션 model"을 연결하는 작업. B3는 generate 자체의 에러 처리 개선.
