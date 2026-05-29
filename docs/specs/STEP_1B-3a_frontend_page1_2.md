# STEP 1B-3a 구현 명세서 — Frontend 골격 + Page 1·2 (Claude Code 인계용)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정했고, 이 문서대로 본진(`~/FINAL/manufacturing-mcp/`)에서 구현한다.
> **작성**: 2026-05-28. STEP 1B-2c(Validator 강화) 완료·push 직후. 백엔드 전체 완성 시점.

---

## 0. 시작 전 필독 (컨텍스트 로딩)

1. `CLAUDE.md` — 설계 헌법.
2. `docs/decisions.md` — D-01~D-73.
3. `docs/0_pipeline_ui_spec-1_v5.md` — **UI 명세 핵심**. Part 0(6페이지 흐름), Part 1-1(기술 스택), Part 1-3(API), Part 2(Page 1), Part 3(Page 2 드래그앤드롭).
4. `docs/0_variable_index_v5.md` §5(페이지 prefix), §10(컴포넌트).
5. `docs/0_README_v5.md` — 페이지별 본진 코드 위치.

### 절대 원칙
- 기존 백엔드(1층 + 1B-1·2a·2b·2c)는 **그대로 보존.** UI는 그 위에 얹는다.
- 외부 API 0, 모달리티 4종, `★` 마크업 금지.
- **이번은 Page 1·2만.** Page 3~6은 1B-3b/3c.

---

## 1. STEP 1B-3 분할 + 이번(3a) 범위

```
STEP 1B-3a (이번)  Frontend 골격(React+Vite+도커) + Page 1(Line선택) + Page 2(Pipeline구성)
                   + 백엔드: 세션 조회/저장 엔드포인트 보강
STEP 1B-3b (다음)  Page 3(데이터·제약) + Page 4(표준화 진행/승인) — 백엔드 핵심 연결
STEP 1B-3c (이후)  Page 5(분석목적/EDA) + Page 6(모델링) — UI 제대로, 실엔진은 STEP 2·3
```

### ★해석 B (claude.ai 확정)★
6페이지 UI는 **전부 명세 수준으로 제대로** 만든다. 단 실동작 백엔드 연결은:
- Page 1~4: 백엔드 완비 → **완전 실동작** (3a+3b)
- Page 5~6: UI는 제대로 만들되, EDA/ML 실엔진은 **청사진 로드맵 STEP 2·3에서** 연결 (3c는 UI + mock)

### 1B-3a에서 만드는 것
1. **Frontend 골격** — React 18 + Vite 프로젝트 셋업 + 도커 통합 (`frontend/` 재구성)
2. **공통 인프라** — 라우팅, 세션 상태, fetch 래퍼, 공통 컴포넌트(Breadcrumb, ModelDropdown, Toast)
3. **Page 1 (Line 선택)** — 라디오 3개 → 세션 생성 → Page 2 이동
4. **Page 2 (Pipeline 구성)** — 좌 카탈로그 + 우 Stage 박스 + HTML5 드래그앤드롭
5. **백엔드 보강** — 세션 조회/저장 엔드포인트 (아래 2장)

---

## 2. 작업 1 — 백엔드 세션 엔드포인트 보강 (먼저)

UI를 붙이려면 백엔드에 세션 조회·저장이 필요하다. 현재 `POST /api/sessions/create`만 있음.
spec-1 Part 1-3 기준으로 보강:

### 현재 vs 필요
| API | 현재 | 이번 작업 |
|---|---|---|
| `POST /api/sessions/create` | 있음 (pipeline_full 받음) | **수정** — `line_id`만으로도 생성 가능하게 |
| `GET /api/sessions/{id}` | 없음 | **신규** — 세션 상태 복원 |
| `PUT /api/sessions/{id}/structure` | 없음 | **신규** — Page 2 PipelineStructure 저장 |
| `GET /api/lines` | 있음 (1B-1) | 그대로 |
| `GET /api/models` | 확인 | 없으면 신규 (Ollama 모델 목록) |

### 2-1. sessions/create 수정
현재는 `pipeline_full`을 받아야 생성됨. Page 1에서는 `line_id`만 있으므로, **둘 다 허용**:
```python
class CreateSessionReq(BaseModel):
    line_id: str | None = None
    pipeline_full: dict | None = None    # 기존 호환 (테스트/직접 호출)

@app.post("/api/sessions/create")
async def create_session_endpoint(req: CreateSessionReq) -> dict:
    # line_id만 오면 빈 구조로 세션 생성, pipeline_full 오면 그대로 (기존 동작 보존)
    sid = create_session(req.pipeline_full or {"line_id": req.line_id, "stages": []})
    session = get_session(sid)
    if req.line_id:
        session["line_id"] = req.line_id
    save_session(sid, session)
    return {"session_id": sid, "status": "created", "line_id": req.line_id}
```
> 기존 pipeline_full 직접 호출(우리 curl 테스트)도 계속 동작해야 함 (회귀 없음).

### 2-2. GET /api/sessions/{id} (세션 복원)
```python
@app.get("/api/sessions/{session_id}")
async def get_session_endpoint(session_id: str) -> dict:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    return public_view(session)   # 이미 있는 public_view 재사용
```

### 2-3. PUT /api/sessions/{id}/structure (Page 2 저장)
Page 2에서 드래그앤드롭으로 구성한 PipelineStructure 저장:
```python
class StructureReq(BaseModel):
    line_id: str
    stages: list[dict]    # [{stage_order, node_id, modules:[{function, dataset_role}]}]

@app.put("/api/sessions/{session_id}/structure")
async def put_structure(session_id: str, req: StructureReq) -> dict:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    # pipeline_full의 뼈대(structure) 저장. 데이터(datalake_id)·제약은 Page 3에서 채움.
    session["pipeline_full"] = {"line_id": req.line_id, "stages": req.stages}
    session["status"] = "structured"
    save_session(session_id, session)
    return {"session_id": session_id, "status": "structured", "stage_count": len(req.stages)}
```

### 2-4. GET /api/models (모델 드롭다운)
없으면 신규. Ollama 설치 모델 목록 (각 페이지 우상단 드롭다운용):
```python
@app.get("/api/models")
async def models_endpoint() -> dict:
    # Ollama /api/tags 조회 또는 하드코딩 폴백 [gemma4:e4b, gemma4:26b]
    return {"models": ["gemma4:e4b", "gemma4:26b"], "default": "gemma4:e4b"}
```

---

## 3. 작업 2 — Frontend 골격 (React + Vite + 도커)

### 3-1. 프로젝트 셋업
`frontend/`를 React+Vite 구조로 (기존 `frontend/index.html` 대시보드는 `frontend/_legacy_dashboard.html`로 백업 후 교체).

```
frontend/
  package.json          # react 18, vite, react-router-dom (최소 의존성)
  vite.config.js        # dev proxy: /api → http://backend:8000 (도커) 또는 localhost:8000
  index.html
  src/
    main.jsx            # 엔트리 + 라우터
    api.js              # fetch 래퍼 (baseURL, 에러 처리)
    session.js          # 세션 상태 (useReducer 또는 context)
    components/
      Breadcrumb.jsx    # 좌상단 Line/세션 정보
      ModelDropdown.jsx # 우상단 모델 선택
      Toast.jsx         # 토스트 알림
    step1_line/
      LineSelectPage.jsx
    step2_user_input_pipeline/
      PipelineBuildPage.jsx
      CatalogPanel.jsx  # 좌측 카탈로그
      StageBox.jsx      # 우측 Stage 박스
      ModuleCard.jsx    # 드래그 가능 모듈 카드
```

### 3-2. 의존성 (최소)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0"
  },
  "devDependencies": { "vite": "^5.0.0", "@vitejs/plugin-react": "^4.2.0" }
}
```
> 드래그앤드롭은 HTML5 native (의존성 0). 차트(Page 5~6)는 3c에서 recharts 추가. 스타일은 CSS Modules 또는 inline (Tailwind 금지 — 빌드 의존성 회피).

### 3-3. 도커 통합
backend 컨테이너와 별개로 frontend dev 서버 또는 정적 빌드 서빙. 두 옵션 중 택1:
- **(권장) dev 단계**: frontend를 호스트에서 `npm run dev`로 띄우고, Vite proxy로 `/api`를 backend(8000)로. 도커 추가 안 함 (개발 빠름).
- **배포 단계**: `npm run build` → `frontend/dist`를 backend FastAPI의 StaticFiles로 서빙 (도커 1개 유지). 1B-3 후반/STEP에서.

1B-3a는 **dev 방식**으로 시작 (Vite proxy). 도커 컴포즈 변경 최소화.

### 3-4. api.js (fetch 래퍼)
```javascript
const BASE = "/api";   // Vite proxy가 backend로
export async function api(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json", ...opts.headers }, ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw { status: res.status, ...err };   // 1-4 에러 패턴
  }
  return res.json();
}
```

---

## 4. 작업 3 — Page 1: Line 선택 (spec-1 Part 2)

### URL / 동작
`/` → 라디오 버튼 3개 (lines.yaml의 3 Line) → 선택 → "다음" → 세션 생성 → `/pipeline/build?session=<id>`

### 구현
```jsx
// LineSelectPage.jsx
// 1. GET /api/lines → 3 Line 표시 (line_id, display_name, max_stages)
// 2. 라디오 선택 → 로컬 state
// 3. "다음" → POST /api/sessions/create {line_id} → session_id 받기
// 4. navigate(`/pipeline/build?session=${sid}`)
```
mockup (spec-1 Part 2-1):
```
┌──────────────────────────────────────┐
│ 제조 데이터 파이프라인        [모델 ▼] │
│ 라인을 선택하세요:                     │
│  ○ Line 1: 금속 가공·검사 라인 (6 Stage)│
│  ○ Line 2: ...                         │
│  ○ Line 3: ...                         │
│                          [다음 →]      │
└──────────────────────────────────────┘
```

### 검증 (spec-1 Part 2-6)
- [ ] GET /api/lines로 3 Line 렌더링
- [ ] 선택 안 하면 "다음" 비활성
- [ ] 세션 생성 후 session_id로 Page 2 이동

---

## 5. 작업 4 — Page 2: Pipeline 구성 (spec-1 Part 3) — 핵심

### URL / 동작
`/pipeline/build?session=<id>` → 좌 카탈로그 + 우 Stage 박스 + 드래그앤드롭으로 모듈 배치 → "다음" → structure 저장 → Page 3

### 5-1. 진입 시 데이터 로드
```jsx
// 1. URL에서 session 읽기
// 2. GET /api/sessions/{id} → line_id 복원 (structure 있으면 복원, 없으면 빈 stages)
// 3. GET /api/lines → 해당 line_id의 stages·available_modules 로드
```

### 5-2. 좌측 카탈로그 (CatalogPanel)
- 해당 Line의 Node별 `available_modules` 카드 나열
- 카드: `function` 라벨(색상) + `hint_dataset`. `draggable={true}`
- **색상 매핑**: process=파랑, quality=초록, maintenance=주황, reference=회색

### 5-3. 우측 Stage 박스 (StageBox)
- Line의 `stages` 순서대로 박스 N개(`max_stages`) 렌더링
- 박스 라벨: `Stage <order>: <node_display_name>`
- 박스 사이 ↓ 화살표 (시간순)
- 박스 내부: 추가된 모듈 + "(드래그해서 추가)" 빈 영역

### 5-4. 드래그앤드롭 (HTML5 native — spec-1 Part 3-4 그대로)
```javascript
// onDragStart: dataTransfer에 {function, hint_dataset, source_node_id} JSON
// onDrop: 검증 후 setStages
//   - source_node_id !== target_node_id → "다른 공정 노드" 토스트, 거부
//   - modules.length >= max_modules → "최대 N개" 토스트, 거부
//   - 중복(function+dataset_role 같음) → "이미 추가됨" 토스트, 거부
// onDragOver: preventDefault + dropEffect="copy"
// 모듈 제거: 카드 [×] 또는 Delete 키
```

### 5-5. 검증 규칙 (spec-1 Part 3-6)
| 규칙 | 시점 | UX |
|---|---|---|
| 빈 Stage 허용 | 저장 시 자동 (list에서 제외) | OK |
| 최소 1+ Stage에 1+ 모듈 | "다음" 클릭 | "최소 1개 모듈" 토스트 |
| max_modules 초과 금지 | 드롭 시 | 거부 + 토스트 |
| 같은 Stage 중복 모듈 금지 | 드롭 시 | 거부 + 토스트 |

### 5-6. "다음" → 저장
```jsx
// PUT /api/sessions/{id}/structure { line_id, stages }
//   stages = 모듈 1+ 있는 Stage만 (빈 Stage 제외)
// → navigate(`/pipeline/data?session=${sid}`)  (Page 3, 3b에서 구현)
```

### 검증 (spec-1 Part 3-10)
- [ ] 카탈로그에서 Stage로 드래그 → 모듈 추가
- [ ] 노드 불일치/초과/중복 → 거부 + 토스트
- [ ] [×]로 모듈 제거
- [ ] "다음" → structure 저장 + Page 3 URL 이동 (Page 3 미구현이라 빈 화면 OK)
- [ ] 새로고침 후 GET /api/sessions/{id}로 구성 복원

---

## 6. 공통 컴포넌트 (3a에서 만들고 이후 재사용)

| 컴포넌트 | 역할 | 이후 재사용 |
|---|---|---|
| Breadcrumb | 좌상단 Line/세션 정보 | 모든 페이지 |
| ModelDropdown | 우상단 모델 선택 (GET /api/models) | 모든 페이지 |
| Toast | 알림 (드롭 거부 등) | 모든 페이지 |
| ModuleCard | function 색상 + 드래그 | Page 2·3 |

---

## 7. 절대 하지 말 것

- ❌ Page 3~6 구현 (3b/3c)
- ❌ React Flow (자유 DAG는 STEP 3 — 여긴 고정 Stage 박스 + HTML5 DnD)
- ❌ Tailwind 등 빌드 의존성 (CSS Modules/inline)
- ❌ 차트 라이브러리 (Page 5~6용, 3c)
- ❌ 기존 백엔드 로직 변경 (세션 엔드포인트 추가만, 기존 execute_pipeline 등 보존)
- ❌ sessions/create 기존 pipeline_full 호출 깨기 (회귀 — 둘 다 허용)
- ❌ 외부 API, 5번째 모달리티

---

## 8. 완료 검증 기준 (체크리스트)

### 백엔드
- [ ] `POST /api/sessions/create` — line_id로 생성 + 기존 pipeline_full 호출도 동작 (회귀 없음)
- [ ] `GET /api/sessions/{id}` — 세션 복원, 404 처리
- [ ] `PUT /api/sessions/{id}/structure` — structure 저장
- [ ] `GET /api/models` — 모델 목록
- [ ] 기존 엔드포인트 회귀 없음 (execute_pipeline, aggregate_context 등)

### 프론트엔드
- [ ] `npm install && npm run dev` → Vite 서버 기동, /api proxy로 backend 연결
- [ ] Page 1: 3 Line 표시 → 선택 → 세션 생성 → Page 2 이동
- [ ] Page 2: 카탈로그 표시 → 드래그앤드롭으로 모듈 배치 → 검증(거부 토스트) → structure 저장
- [ ] 새로고침 시 세션 복원
- [ ] function 색상 매핑 (process파랑/quality초록/maintenance주황/reference회색)

### 통합
- [ ] Page 1 → 2 → (structure 저장) 흐름이 실제 백엔드와 연결되어 동작
- [ ] `npm run build` 성공 (빌드 에러 없음)

---

## 9. 커밋 + 인계 방식

### 작업 흐름 (1B-2 교훈)
1. 0번 필독 (특히 spec-1 Part 2·3)
2. 작업 1(백엔드) → 작업 2(골격) → 작업 3(Page1) → 작업 4(Page2) 순서
3. **전체 완성 후** 8번 체크리스트 검증 (npm run dev로 실제 브라우저 또는 curl + 빌드)
4. **검증 끝나고** 논리 단위 커밋 (중간 커밋·git checkout 되돌리기 금지):
   ```
   feat(STEP1B-3a): add session get/structure/models backend endpoints
   feat(STEP1B-3a): scaffold React+Vite frontend (router, api, session, common components)
   feat(STEP1B-3a): add Page 1 Line selection
   feat(STEP1B-3a): add Page 2 pipeline build with HTML5 drag-and-drop
   docs(STEP1B-3a): record decisions + variable_index frontend update
   ```
5. **push는 claude.ai 검증 후.**
6. `docs/decisions.md` D-74~ 추가, `docs/0_variable_index_v5.md` §5·§9·§10 갱신

### 완료 후 claude.ai에 보고할 것
- 8번 체크리스트 결과 (항목별)
- 백엔드 세션 엔드포인트 코드 (create 수정 + structure)
- frontend 디렉터리 구조 (`ls -R frontend/src`)
- Page 1·2 핵심 컴포넌트 (LineSelectPage, PipelineBuildPage, 드래그앤드롭 부분)
- 실제 동작 확인: `npm run dev` 후 Page1→2 흐름 (스크린샷 또는 curl로 세션 생성·structure 저장 로그)
- `npm run build` 성공 로그
- `git log --oneline -7` (push 전)
→ claude.ai가 검증하고 STEP 1B-3b(Page 3·4)로 진행

### ★1B-2 교훈★
전체 완성 → 검증 → 마지막에 논리 단위 커밋. git checkout/reset 되돌리기 금지. push는 검증 후.

> 프론트엔드는 백엔드와 달리 "브라우저에서 실제로 보이는지"가 중요. npm run dev로 띄워서
> 병갑님이 직접 화면을 볼 수 있게 하는 게 검증의 핵심. (curl만으론 UI 확인 불가)

---

## 부록 — 현재 코드 상태 (백엔드 완성 시점)

### 백엔드 (그대로 활용)
- `backend/main.py`: 1층(/api/execute, /api/inspect, /api/plan, /api/datasets, /api/health) +
  1B-1(/api/lines) + 1B-2a(/api/sessions/create, /api/execute_pipeline, /api/pipeline/{id}/status, /approve) +
  1B-2b(/api/aggregate_context/{id})
- `backend/session_store.py`: create_session/get_session/save_session/public_view, _SESSIONS 인메모리
  세션 dict: session_id, pipeline_full, status, approved_step_keys[], completed_*[], module_results{}, alarms[], aggregated_context
- `catalogs/lines.yaml`: 3 Line · 18 Node · 34 Module. 각 module {function, hint_dataset}
- `catalogs/modules.yaml`: 5 Node, function_hints + constraint_keys + recommended_models

### lines.yaml 구조 (Page 1·2가 소비)
```yaml
- line_id: module_1_metal_processing
  display_name: "금속 가공·검사 라인"
  max_stages: 6
  stages:
    - node_id: primary_forming
      display_name: "1차 성형"
      max_modules: 2
      available_modules:
        - { function: maintenance, hint_dataset: "L3_mold_condition" }
```
→ Page 1: line_id/display_name/max_stages. Page 2: stages·available_modules.

### 프론트 (현재)
- `frontend/index.html`: 1층 다크 대시보드 (순수 HTML). → `_legacy_dashboard.html`로 백업 후 React로 교체.

### 페이지별 위치 (README/variable_index §5)
- Page 1: `frontend/src/step1_line/`
- Page 2: `frontend/src/step2_user_input_pipeline/`
- (Page 3~6: step3_user_input_data / step4_standardize / step5_analyze / step6_modeling — 3b/3c)
