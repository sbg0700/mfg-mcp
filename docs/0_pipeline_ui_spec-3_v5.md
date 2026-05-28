# pipeline_ui_spec-3_v5 — Phase 3 (종합: 컴포넌트 + API + 에러 + 테스트 + 데모 + 부록, v5)

> **목적**: STEP 1B UI 구현 명세 Phase 3. 종합 부분 — 컴포넌트 라이브러리 + 전체 API 종합 + 에러 처리 + 테스트 시나리오 + 데모 시나리오 + 부록 A/B/C.
>
> **분할 정보**:
> - `0_pipeline_ui_spec-1_v5.md` = Phase 1 (구조 + 공통 + Page 1~3)
> - `0_pipeline_ui_spec-2_v5.md` = Phase 2 (Page 4~6)
> - **spec-3 (본 파일)** = Phase 3 (종합 + 부록)
>
> **Snapshot**: 2026-05-27 v5 (분할판 최종)
>
> **상위 문서**: `0_project_blueprint_v5.md` / `0_CHANGELOG_v5.md` / `0_variable_index_v5.md`
>
> **단계 진입 시 필독 (3 파일)**: 청사진 + CHANGELOG + 본 파일
>
> **이전 Phase**: `0_pipeline_ui_spec-2_v5.md` (Phase 2, Page 4~6)
> **다음 Phase**: 없음 (본 파일이 명세서 마무리)

---

## 이전 단계 검증 (Phase 2 → Phase 3 인수)

### 본 명세 작업 진입 전 필독·검증 항목

- [ ] `0_pipeline_ui_spec-1_v5.md` (Phase 1) 숙독 완료
- [ ] `0_pipeline_ui_spec-2_v5.md` (Phase 2, Page 4~6) 숙독 완료
- [ ] `0_CHANGELOG_v5.md` 알파 진입 후 기록 확인 (v5 시점은 비어 있음)
- [ ] `0_variable_index_v5.md` §10 컴포넌트 / §9 API / §12 환각 방어 인지

### Phase 1 + Phase 2 누적 결정 사항 (Phase 3 작성에 활용)

| 영역 | 위치 | Phase 3 활용 |
|---|---|---|
| 자료구조 8종 | spec-1 Part 1-2 | Part 9 종합 표 + 부록 A 실 JSON 예시 |
| API 25 엔드포인트 | spec-1 Part 1-3 (21개) + spec-2 Part 5~7 | Part 9-1 종합 25 표 + 부록 B curl 예시 |
| 컴포넌트 22종 | spec-2 Page 4~6 + spec-1 Page 1~3 | Part 8 컴포넌트 라이브러리 |
| 환각 방어 메커니즘 | spec-1 Part 1-7 / spec-2 Part 5-5,5-6,6-2,6-6,7-2 | Part 10 에러 처리 + Part 11 테스트 |
| 데모 시나리오 4종 (B/D/A/C) | 사용자 합의 | Part 12 데모 분배 |
| 알파/베타/운영 검증 | spec-1 Part 1-9-9 | Part 11 테스트 + Part 12 베타 환경 분리 |

### Phase 2 에서 누적된 설계 결정 (본 Phase 3 가 그대로 활용)

> `0_CHANGELOG_v5.md` 는 알파 진입 후 기록 시작 (현재 비어 있음). 본 섹션은 v5 설계 단계 결정의 요약.

- Page 4 동작: SSE+폴링, step_key 승인, Context Aggregator 자동 트리거
- Page 5 동작: 자동 질문, EDA 4 Function 매핑, 데이터 가드 7종, 자연어 요약
- Page 6 동작: 추천 모델 AggregatedContext 활용, 2 depth CNN, 결과 송출 조합

### Phase 3 작성 시 적용할 원칙

| 원칙 | 의미 |
|---|---|
| 종합 표 우선 | Part 9/10 = 페이지별 흩어진 정보를 한 곳에 모음 |
| 실 예시 우선 | 부록 A (JSON) / 부록 B (curl) = 추상 명세 보강 |
| 알파 검증 명시 | Part 11 테스트 시나리오 = 알파 단계 발견 항목 매핑 |
| 베타 시연 명시 | Part 12 데모 시나리오 = 4 시나리오 매트릭스 |

위 검증 통과 후 본 명세 진입.

---

## Part 8. 컴포넌트 라이브러리 (재사용 React 컴포넌트)

본 명세에서 도출된 재사용 컴포넌트. props + 사용 페이지 + 상태 명세.

### 8-1. 컴포넌트 목록

| 컴포넌트 | 사용 페이지 | 역할 |
|---|---|---|
| `<ModelDropdown>` | 모든 페이지 (우상단) | Ollama 설치 모델 선택 (e4b/26b) |
| `<Breadcrumb>` | 모든 페이지 (좌상단) | Line / 진행 단계 표시 |
| `<LineRadioGroup>` | Page 1 | Line 3개 라디오 버튼 + 진입 트리거 |
| `<CatalogPanel>` | Page 2 | Stage·Node·Module 사전정의 카탈로그 드래그 소스 |
| `<StageBox>` | Page 2, 4 | Stage 박스 (DnD 대상 또는 진행 표시) |
| `<ModuleCard>` | Page 2, 3, 4, 6 | 모듈 카드 (함수별 색상, function/dataset_role 표시) |
| `<DatasetSelector>` | Page 3 | Data Lake 드롭다운 + 신규 등록 모달 |
| `<ConstraintForm>` | Page 3 | constraint_keys 기반 동적 폼 (range/single/ratio/list/text) |
| `<UploadModal>` | Page 3 | 신규 데이터셋 등록 (Mode A 업로드 / Mode B 서버 경로) |
| `<ProgressBar>` | Page 4, 6 | 진행률 + 예상 잔여 시간 |
| `<LLMInterpretationPanel>` | Page 4 | Inspector LLM 해석 표시 (modality_guess/concerns) |
| `<ApprovalCard>` | Page 4 | 결정론 미리보기 + step_key 기반 승인 |
| `<NaturalInput>` | Page 4, 5 | 자연어 입력 + LLM 매핑 + 재확인 (2단계 환각방어) |
| `<AlarmBanner>` | Page 4 | 데이터 미업로드 / 표준화 우려 알람 |
| `<QuestionRadioGroup>` | Page 5 | 분석 목적 6 라디오 + 자유 입력 |
| `<ChartPanel>` | Page 5 | 차트 + 결정론 통계 + LLM 자연어 요약 |
| `<DataGuardWrapper>` | Page 5 | 데이터 규모 가드 자동 적용 (row > 1M 등) |
| `<ModelCard>` | Page 6 | 모델 추천 카드 (fit_score/시간/메모리/추정 성능) |
| `<TwoDepthDecisionModal>` | Page 6 | CNN Quick/Full/Skip 모달 |
| `<TrainingProgress>` | Page 6 | 학습 진행 (step + step_unit + loss 실시간 — CNN=epoch / 트리=boosting_round) |
| `<ResultsDashboard>` | Page 6 | 기본 (지표+Confusion+Importance) + 풀 확장 |
| `<SHAPModal>` | Page 6 | SHAP 시간 경고 모달 |

### 8-2. 핵심 컴포넌트 props 예시

#### `<ApprovalCard>` (Page 4)
```typescript
interface ApprovalCardProps {
  stageOrder: number;
  moduleIndex: number;
  stepKey: string;           // order 아님 — step_key 기반
  operation: string;          // OPERATION_PERMISSION 키 12종
  targetColumn: string | null;
  permissionLevel: "L2" | "L3";
  beforeStats: Record<string, any>;
  predictedAfterStats: Record<string, any>;
  directionText: string;     // "마스킹 → NaN → float64 수치화"
  onApprove: (stepKey: string) => Promise<void>;
  onReject: (stepKey: string) => Promise<void>;
}
```

#### `<NaturalInput>` (Page 4, 5)
```typescript
interface NaturalInputProps {
  sessionId: string;
  context: {
    stageOrder?: number;
    moduleIndex?: number;
    currentAvailableOperations?: string[];  // OPERATION_PERMISSION 12종
  };
  onMappingComplete: (mapping: {
    operation: string;
    permissionLevel: string;
    confidence: number;
  }) => void;
  confidenceThreshold?: number;  // 기본 0.7
}
```

#### `<ChartPanel>` (Page 5)
```typescript
interface ChartPanelProps {
  chartType: "boxplot_by_label" | "fft_spectrum" | "image_grid" | 
             "pareto" | "class_distribution" | ...;
  data: any;                              // 결정론 계산 통계
  guards: DataGuardConfig;                // 데이터 규모 가드
  llmSummary?: {
    summary: string;
    keyPoints: string[];
  };
  function_axis: "process" | "quality" | "maintenance" | "reference";
}
```

#### `<ModelCard>` (Page 6)
```typescript
interface ModelCardProps {
  modelName: string;
  fitScore: 1 | 2 | 3 | 4 | 5;
  isPrimary: boolean;                     // 추천 1순위 강조
  rationale: string;                      // AggregatedContext 인용
  aggregatedContextApplied: string[];     // ["불균형 → class_weight 자동", ...]
  estimatedTimeMin: number;
  vramGB: number;
  estimatedPerformance: string;           // "F1 0.80~0.90"
  requires2DepthDecision: boolean;        // CNN 만 true
  executable: boolean;                    // 대형 모델 false
  onSelect: (modelName: string) => void;
}
```

### 8-3. 색상 매핑 (Function 축)

| Function | 색상 | 용도 |
|---|---|---|
| process | 파랑 (#3B82F6) | ModuleCard 테두리, 카탈로그 라벨 |
| quality | 초록 (#10B981) | 〃 |
| maintenance | 주황 (#F59E0B) | 〃 |
| reference | 회색 (#6B7280) | 〃 |

### 8-4. 상태 관리 (useState 구조)

각 페이지 독립 useState. 페이지 간 공유는 백엔드 (sessions DB) 통해.

```typescript
// Page 2 useState 예시
const [stages, setStages] = useState<Stage[]>(
  initialStages  // Line.stages 로부터 max_stages만큼 빈 박스
);

const [selectedModule, setSelectedModule] = useState<{
  stageOrder: number;
  moduleIndex: number;
} | null>(null);
```

### 8-5. 컴포넌트 트리

```
<App>
  ├── <Router>
  │     ├── <Page1>           (/) Line 선택
  │     │     ├── <ModelDropdown />
  │     │     └── <LineRadioGroup />
  │     │
  │     ├── <Page2>           (/pipeline/build) Pipeline 구성
  │     │     ├── <Breadcrumb />
  │     │     ├── <ModelDropdown />
  │     │     ├── <CatalogPanel>
  │     │     │     └── <ModuleCard draggable />
  │     │     └── <StagePanel>
  │     │           └── <StageBox dropTarget>
  │     │                 └── <ModuleCard removable />
  │     │
  │     ├── <Page3>           (/pipeline/data) 데이터+제약
  │     │     ├── <ModuleCard expandable>
  │     │     │     ├── <DatasetSelector />
  │     │     │     │     └── <UploadModal />
  │     │     │     └── <ConstraintForm />
  │     │     └── <AlarmModal /> (LLM judge 알람 시)
  │     │
  │     ├── <Page4>           (/pipeline/run) 표준화 진행
  │     │     ├── <StagePanel> (좌)
  │     │     │     ├── <StageBox progress />
  │     │     │     └── <AlarmBanner />
  │     │     └── <DetailPanel> (우)
  │     │           ├── <LLMInterpretationPanel />
  │     │           ├── <ApprovalCard />
  │     │           └── <NaturalInput />
  │     │
  │     ├── <Page5>           (/pipeline/analyze) 분석 목적
  │     │     ├── <QuestionRadioGroup />
  │     │     ├── <NaturalInput /> (자유 입력)
  │     │     └── <EDAResults>
  │     │           └── <ChartPanel> (DataGuardWrapper 적용)
  │     │
  │     └── <Page6>           (/pipeline/model) 모델링
  │           ├── <ModelCard /> × N
  │           ├── <TwoDepthDecisionModal /> (CNN)
  │           ├── <TrainingProgress />
  │           ├── <ResultsDashboard />
  │           └── <SHAPModal />
```

---

## Part 9. 전체 API/자료구조 종합

### 9-1. API 엔드포인트 종합 표

| # | 엔드포인트 | 메서드 | 페이지 | 요청 | 응답 | 비고 |
|---|---|---|---|---|---|---|
| 1 | `/api/lines` | GET | 1 | — | `LineCatalog` | 카탈로그 |
| 2 | `/api/models` | GET | 모든 | — | `{installed: [str], default: str}` | Ollama 모델 |
| 3 | `/api/sessions/create` | POST | 1 | `{line_id}` | `{session_id, line_id, status}` | 세션 생성 |
| 4 | `/api/sessions/{id}` | GET | 모든 | — | 세션 전체 상태 | 복원용 |
| 5 | `/api/sessions/{id}/structure` | PUT | 2 | `PipelineStructure` | `{session_id, status}` | 1-1 저장 |
| 6 | `/api/sessions/{id}/full` | PUT | 3 | `PipelineFull` | `{session_id, status, alarms}` | 1-2 저장 |
| 7 | `/api/datalake/list` | GET | 3 | `?modality=&function=&source=` | `{entries: [DataLakeEntry]}` | 카탈로그 |
| 8 | `/api/datalake/register` | POST | 3 | multipart (Mode A) 또는 JSON (Mode B) | `DataLakeEntry` | 신규 등록 |
| 9 | `/api/datalake/{id}/metadata` | GET | 3 | — | `DataLakeEntry` | 메타 조회 |
| 10 | `/api/datalake/{id}` | DELETE | 3 | — | `{deleted: true}` | 삭제 |
| 11 | `/api/execute_pipeline` | POST | 4 | `{session_id, model}` | `{status, estimated_seconds}` | 실행 트리거 |
| 12 | `/api/pipeline/{id}/status` | GET | 4 | — | `PipelineStatus` | 폴링 |
| 13 | `/api/pipeline/{id}/stream` | SSE | 4 | — | `PipelineStatus` 스트림 | SSE 권장 |
| 14 | `/api/pipeline/{id}/approve` | POST | 4 | `{stage_order, module_index, step_key}` | `{approved: true}` | step_key 승인 |
| 15 | `/api/pipeline/{id}/natural_input` | POST | 4, 5 | `{stage_order, module_index, natural_text, context}` | `{mapped_operation, permission_level, confidence, requires_confirmation}` | 자연어 매핑 |
| 16 | `/api/aggregate_context/{id}` | GET | 5, 6 진입 | — | `AggregatedContext` | Context Aggregator |
| 17 | `/api/analyze/{id}/questions` | GET | 5 | — | `AnalysisQuestion` | 자동 질문 |
| 18 | `/api/analyze/{id}/select` | POST | 5 | `{analysis_purpose, free_input}` | `{updated_context}` | 사용자 선택 |
| 19 | `/api/analyze/{id}/results` | GET | 5 | — | EDA 차트 데이터 + 요약 | EDA 결과 |
| 20 | `/api/model/{id}/recommend` | GET | 6 | — | 추천 카드 list | 모델 추천 |
| 21 | `/api/model/{id}/train` | POST | 6 | `{model_name, mode, options}` | `{training_id, status}` | 학습 트리거 |
| 22 | `/api/model/{id}/status` | GET | 6 | — | `{step, step_unit, loss, progress, eta}` | 학습 진행 (step_unit ∈ {"epoch"\|"boosting_round"} — CNN은 epoch, XGBoost/LightGBM은 boosting_round) |
| 23 | `/api/model/{id}/results` | GET | 6 | — | 기본 결과 (지표+Confusion+Importance) | 결과 |
| 24 | `/api/model/{id}/dashboard` | GET | 6 | — | 풀 (ROC+SHAP+예측 샘플) | 확장 |
| 25 | `/api/model/{id}/cancel` | POST | 6 | — | `{cancelled: true}` | 학습 중단 |

### 9-2. 자료구조 종합 (Part 1-2 참조 + 종합 표)

| # | 자료구조 | 생성 시점 | 저장 위치 | 활용 페이지 |
|---|---|---|---|---|
| 1 | `LineCatalog` | 시스템 정적 | `catalogs/lines.yaml` (메모리 로드) | 1, 2 |
| 2 | `PipelineStructure` | Page 2 사용자 입력 | DB `sessions.structure` (JSONB) | 2, 3 |
| 3 | `PipelineFull` | Page 3 사용자 입력 | DB `sessions.full_data` + 파일 시스템 (raw) | 3, 4 |
| 4 | `PipelineResults` | Page 4 백엔드 실행 | DB `sessions.results` + `lineage.transformations` | 4, 5 (간접) |
| 5 | `PipelineStatus` | Page 4 실시간 | 메모리 (SSE/폴링) | 4 |
| 6 | `AnalysisQuestion` | Page 5 자동 생성 | DB `sessions.analysis` | 5 |
| 7 | `DataLakeEntry` | 등록 시점 | DB `datalake.entries` + 파일 시스템 | 3 |
| 8 | `AggregatedContext` | Page 4 완료 후 자동 | DB `sessions.results` 확장 필드 | 5, 6 |

### 9-3. 사용자 입력 → 백엔드 저장 흐름

```
[Page 1] line_id 선택
   → POST /api/sessions/create
      → DB sessions.line_id 저장

[Page 2] 모듈 드래그앤드롭
   → 클라이언트 useState 만 갱신
   → [다음] 클릭 시 PUT /api/sessions/{id}/structure
      → DB sessions.structure (JSONB) 저장

[Page 3] 데이터 선택 + 제약 입력
   → 데이터 선택: GET /api/datalake/list (정적)
   → 신규 등록: POST /api/datalake/register
   → 클라이언트 useState 갱신
   → [다음] 클릭 시 PUT /api/sessions/{id}/full
      → DB sessions.full_data (JSONB) 저장

[Page 4] 표준화 실행
   → POST /api/execute_pipeline (트리거)
   → 백엔드 비동기 처리 + DB sessions.results 누적 갱신
   → 사용자: GET /api/pipeline/{id}/stream (SSE) 구독
   → 사용자 승인: POST /api/pipeline/{id}/approve (step_key)
   → 모든 Stage 완료 시 백엔드 자동 GET /api/aggregate_context/{id}
   → DB sessions.results 에 AggregatedContext 저장

[Page 5] 분석 목적 선택
   → GET /api/aggregate_context/{id} (이미 저장된 것 조회)
   → GET /api/analyze/{id}/questions (LLM 자동 질문)
   → 사용자 선택: POST /api/analyze/{id}/select
   → DB sessions.analysis (JSONB) 저장
   → GET /api/analyze/{id}/results (EDA 차트 데이터)

[Page 6] 모델링
   → GET /api/model/{id}/recommend (LLM 적합도)
   → 사용자 선택 + (CNN) 2 depth 모달
   → POST /api/model/{id}/train (트리거)
   → GET /api/model/{id}/status (진행)
   → GET /api/model/{id}/results (완료 시)
   → DB sessions.model_results (JSONB) + 파일 시스템 (모델 binary)
```

---

## Part 10. 에러 처리 종합

### 10-1. 페이지별 에러 케이스

| 페이지 | 에러 케이스 | 처리 |
|---|---|---|
| **모든 페이지** | 세션 만료 | Page 1 리다이렉트 + 토스트 |
| **모든 페이지** | 네트워크 단절 | 재시도 버튼 + offline 표시 |
| **모든 페이지** | localStorage 손상 | 새 세션 생성 권유 |
| 1 | `/api/lines` 응답 없음 | 재시도 |
| 1 | Line 미선택 + [다음] | 버튼 비활성 |
| 2 | DnD 검증 실패 | 토스트 (max_modules 초과, 중복, Node 불일치) |
| 2 | 0 모듈 상태 [다음] | 토스트 + 차단 |
| 3 | Data Lake 조회 실패 | 카탈로그 새로고침 + 재시도 |
| 3 | Mode A 업로드 100MB 초과 | 토스트 + Mode B 권유 |
| 3 | Mode B 서버 경로 없음 | 토스트 + 경로 재입력 |
| 3 | LLM judge 알람 (미입력) | 모달 → "돌아가서 입력" / "무시" |
| 4 | MCP 서버 down | 모듈 skip + 재시도 |
| 4 | Ollama LLM down | LLM 해석 "응답 없음" + 결정론 계속 + Validator 낮은 신뢰도 |
| 4 | Inspector 실패 | 모듈 failed, 다음 모듈 진행 |
| 4 | Planner LLM JSON 파싱 실패 | 규칙 fallback |
| 4 | Executor 변환 실패 | rollback + Validator issues |
| 4 | approval_token 만료 (1시간) | 카드 재표시 |
| 4 | 자연어 매핑 confidence < 0.7 | 자동 거부 + "다시 입력" |
| 4 | OPERATION_PERMISSION 외 LLM 출력 | 차단 + 로그 |
| 4 | Context Aggregator 실패 | 재시도 + [다음] 비활성 |
| 5 | 자동 질문 LLM 실패 | 기본 후보 4종 + "추천 비활성" |
| 5 | 자유 입력 매핑 confidence < 0.5 | "라디오 선택 권유" |
| 5 | EDA 차트 렌더링 실패 (대용량) | 가드 자동 적용 + 실패 시 "규모 확인" |
| 5 | 자연어 요약 LLM 실패 | 통계만 표시 |
| 5 | `available_options` 외 추천 | 차단 + fallback |
| 6 | 추천 모델 LLM 실패 | 기본 카드 (Module Catalog 그대로) |
| 6 | VRAM 초과 (학습 중) | OOM 감지 → 중단 → "Quick 재시도?" |
| 6 | 학습 시간 초과 (예상 × 3) | 자동 중단 + 알림 |
| 6 | Feature Importance 추출 실패 | 다른 지표만 |
| 6 | Confusion Matrix 생성 실패 (회귀) | MAE/RMSE/R² 대체 |
| 6 | 모델 저장 실패 | 학습 성공, 저장 재시도 |
| 6 | SHAP 시간 초과 | 자동 중단 + 기본 결과 |
| 6 | 사용자 학습 중단 | 즉시 + 부분 결과 |

### 10-2. 공통 에러 응답 형식 (재명시)

```python
{
  "error": {
    "code": str,           # 표준 코드
    "message": str,        # 한국어 사용자 메시지
    "details": dict | None # 디버그 (개발자 모드만)
  }
}
```

### 10-3. 표준 에러 코드

| 코드 | HTTP | 의미 |
|---|---|---|
| `INVALID_INPUT` | 400 | 클라이언트 입력 오류 |
| `SESSION_NOT_FOUND` | 404 | 세션 만료/없음 |
| `RESOURCE_NOT_FOUND` | 404 | datalake_id / step_key 등 없음 |
| `VALIDATION_FAILED` | 422 | 폼/스키마 검증 실패 |
| `LLM_UNAVAILABLE` | 503 | Ollama down |
| `MCP_UNAVAILABLE` | 503 | MCP 서버 down |
| `LLM_HALLUCINATION_BLOCKED` | 422 | 가드레일 외 출력 차단 |
| `PERMISSION_DENIED` | 403 | L3 작업 백업 없이 시도 등 |
| `RESOURCE_EXCEEDED` | 507 | VRAM/디스크 초과 |
| `TIMEOUT_EXCEEDED` | 408 | 학습/LLM 시간 초과 |
| `INTERNAL_ERROR` | 500 | 백엔드 예외 |

### 10-4. 재시도 정책

| 시나리오 | 정책 |
|---|---|
| 네트워크 일시 단절 | 자동 재시도 3회 (지수 백오프 1s/2s/4s) |
| LLM 응답 timeout | 자동 재시도 1회 + 실패 시 fallback |
| MCP 서버 일시 down | 자동 재시도 2회 + 실패 시 모듈 skip |
| 학습 OOM | 재시도 ❌ — Quick 모드 권유 |
| 사용자 입력 검증 실패 | 재시도 ❌ — 입력 수정 |
| 가드레일 차단 | 재시도 ❌ — 자연어 재입력 또는 카드 선택 |

---

## Part 11. 테스트 시나리오

### 11-1. E2E (End-to-End) 시나리오

#### 시나리오 1: 정상 흐름 (Happy Path)

```
1. /api/lines → Line 1 선택
2. POST /api/sessions/create → session_id 발급
3. Page 2 → DnD 로 모듈 3개 배치 (Stage 0, 2, 5)
4. PUT /api/sessions/{id}/structure → 200
5. Page 3 → KAMP 데이터셋 선택 + 제약 입력 (3 모듈)
6. PUT /api/sessions/{id}/full → 200, alarms = []
7. POST /api/execute_pipeline → 200
8. SSE /api/pipeline/{id}/stream 구독
9. L2 작업 승인 카드 3개 → 모두 [승인]
10. POST /api/pipeline/{id}/approve × 3 → 200
11. 모든 Stage done → GET /api/aggregate_context/{id} 자동
12. Page 5 [다음] 클릭
13. GET /api/analyze/{id}/questions → 추천 1순위 "품질 예측·분류"
14. 사용자 선택 → POST /api/analyze/{id}/select
15. EDA 차트 4종 표시 + LLM 요약
16. Page 6 [다음] 클릭
17. GET /api/model/{id}/recommend → XGBoost 1순위
18. [선택] → POST /api/model/{id}/train
19. 학습 완료 (~30초) → 기본 결과 표시
20. F1 = 0.849 확인 + [완료]
```

#### 시나리오 2: 데이터 미업로드 + LLM judge 알람

```
3. Page 3 → maintenance 모듈에 데이터 업로드 안 함
6. PUT /api/sessions/{id}/full → 200, alarms = [{
     stage: 0, module: maintenance,
     reason: "예지보전 모듈은 constraint_keys 입력 필수"
   }]
7. 사용자 모달 → [돌아가서 업로드] 또는 [무시하고 skip]
8a. [돌아가서 업로드] → Page 3 복귀
8b. [무시] → POST /api/execute_pipeline + Validator 낮은 신뢰도
```

#### 시나리오 3: L2/L3 승인 거부

```
9. clean_masking (L2) 카드 → [거부]
10. step skipped 표시
11. Validator issues: ["clean_masking 거부됨, lineage 누락"]
12. 다음 step 진행
13. Page 4 완료 시 낮은 신뢰도 표시
```

#### 시나리오 4: 자연어 매핑 실패

```
4-15. 자연어 입력 "이 데이터 통째로 삭제해줘"
       → POST /api/pipeline/{id}/natural_input
       → LLM 매핑 시도 → confidence = 0.4
       → 자동 거부 → "다시 입력 또는 카드 선택" 안내
```

#### 시나리오 5: 자유 입력 분석 목적

```
14. 사용자 자유 입력 "고장 예측해줘"
    → LLM 매핑 → confidence = 0.85
    → "predictive_maintenance 로 해석" 재확인 모달
    → [예] → POST /api/analyze/{id}/select
```

#### 시나리오 6: CNN 2 depth (Quick)

```
17-19. 작은 CNN 선택
       → 2 depth 모달
       → Quick 선택
       → 학습 ~5분 진행
       → 결과: F1 0.72 (참고용)
       → 사용자: "더 정확히 보려면 Full 모드 재학습"
```

### 11-2. 챌린지 8 회귀 테스트

각 챌린지가 해당 페이지에서 정확히 잡히는지:

| 챌린지 | 더미 데이터셋 | 검증 페이지 | 기대 동작 |
|---|---|---|---|
| 1. 인코딩 (CP949) | order_cp949 | Page 4 | Inspector flags 에 "non-utf8 encoding" 등장 |
| 2. 헤더 없음 | mold_anomaly_headerless | Page 4 | "headerless" flag + reparse_header L1 자동 |
| 3. dtype 혼재 | cnc_lathe_masked | Page 4 | "mixed dtype" flag + clean_masking L2 카드 |
| 4. 대용량 | (1M+ 데이터) | Page 5 | Data Guard 활성 (RMS 윈도우) |
| 5. 이미지 라벨 6종 | wafer/welding/press | Page 4 | 모달리티 inspection-image 라우팅 |
| 6. 불균형 (2.85%) | press_imbalance | Page 4 | "imbalance_suspected" + balance_classes L2 카드 |
| 7. PK / LoT 키 | (event-log 더미) | Page 4 | LOT_NO outer merge 동작 |
| 8. 멀티시트 | (xlsx 더미) | Page 4 | "multi_sheet_merged" flag |

### 11-3. 단위 테스트 우선순위

| 단위 | 테스트 항목 |
|---|---|
| Context Aggregator | 결정론 안정성 — 같은 입력 100회 → 같은 출력 |
| Planner | candidate_operations 추출 정합성 (각 flag → 정확한 작업) |
| 가드레일 | OPERATION_PERMISSION 외 작업 차단 |
| 환각 방어 | `available_options` 외 LLM 출력 차단 |
| step_key | order 변경 시에도 매칭 안정 |
| Executor | parquet 백업 + rollback 동작 |
| LLM judge | confidence 임계 (0.7 / 0.5) 정확 |

---

## Part 12. 데모 시나리오 (3분 / 7분 / 15분)

### 12-1. 3분 (Quick Pitch)

**목표**: 핵심 차별점 1개 ("AI가 코드를 짠다 + 로컬 + 추적 가능") 전달

| 시간 | 페이지 | 동작 | 사용 데이터 |
|---|---|---|---|
| 0:00~0:10 | Page 1 | Line 3 선택 | — |
| 0:10~0:40 | Page 2 | 사출 성형 Node 에 process 모듈 1개 DnD | KAMP injection_production 힌트 |
| 0:40~1:00 | Page 3 | Data Lake 선택 + 제약 1개 입력 | injection_production (184행) |
| 1:00~2:00 | Page 4 | 표준화 실시간 (LLM 해석 자막) + clean_masking L2 카드 [승인] | — |
| 2:00~2:30 | Page 5 | 자동 질문 "품질 예측·분류" 추천 + 박스플롯 자동 생성 | — |
| 2:30~3:00 | Page 6 | XGBoost 카드 [선택] → 학습 30초 → F1 표시 + 마무리 멘트 | — |

**멘트**: "30초 만에 1 모듈 표준화, 30초 만에 모델 학습. 전부 로컬. 모든 변환 Lineage 추적."

### 12-2. 7분 (Standard Demo)

**목표**: 1층 (모달리티) → 1.5층 (STEP 1B 컨텍스트) → 2층 (모델링) 전체 흐름

| 시간 | 페이지 | 동작 | 사용 데이터 |
|---|---|---|---|
| 0:00~0:30 | Page 1, 2 | Line 2 선택 + 프레스 + 용접 검사 2 Node | press + welding_inspect |
| 0:30~1:30 | Page 3 | 2 모듈 데이터 + 제약 입력 (불균형 경고 발생) | press_imbalance, welding_bead |
| 1:30~3:30 | Page 4 | 2 Stage 순차 처리 + LLM 해석 표시 + balance_classes L2 카드 [승인] + 모달리티 자동 분기 시연 | — |
| 3:30~4:00 | Page 4 | Context Aggregator 자동 + AggregatedContext JSON 1초 표시 (영업 메시지: "MCP 발견 사실 → LLM 컨텍스트") | — |
| 4:00~5:00 | Page 5 | 자동 질문 "품질 예측·분류" 추천 + 박스플롯 + 이미지 그리드 + LLM 자연어 요약 | — |
| 5:00~6:30 | Page 6 | XGBoost 학습 (30초) + 결과 dashboard + 작은 CNN 옵션 시연 (Skip 선택 시 권고만 보여주기) | — |
| 6:30~7:00 | 종합 | Lineage 추적 화면 1회 + 사용자 통제권 메시지 | — |

**멘트**: "공정 다 다르지만 MCP 4개로 처리. 같은 코드, 다른 데이터. LLM은 판단, MCP는 변환, 사용자는 승인."

### 12-3. 15분 (Full Demo)

**목표**: 차별점 5가지 모두 + 자연어 매핑 + KAMP 외 데이터 등록 + 풀 대시보드 + Q&A

| 시간 | 페이지 | 동작 |
|---|---|---|
| 0:00~3:00 | Page 1, 2, 3 | Line 1 + 6 모듈 (process×2 / quality×2 / maintenance×2) + KAMP 외 사용자 등록 데이터 시연 |
| 3:00~6:00 | Page 4 | 6 Stage 순차 + 자연어 매핑 시연 (사용자가 직접 자연어 입력) + 환각 방어 차단 사례 시연 (가드레일 외 작업 차단) |
| 6:00~9:00 | Page 5 | 자유 입력 분석 목적 + LLM 매핑 + EDA 4 차트 + 자연어 요약 + 추가 전처리 |
| 9:00~14:00 | Page 6 | XGBoost (30초) + LightGBM (20초) + 작은 CNN Quick (5분) + 풀 대시보드 (ROC + SHAP) + 모델 비교 |
| 14:00~15:00 | 종합 | Lineage 전체 추적 + 영업 메시지 5가지 + Q&A |

### 12-4. 시연 데이터셋 매트릭스 (베타 환경)

| 데이터셋 | 3분 | 7분 | 15분 | 가치 |
|---|---|---|---|---|
| injection_production | ⭕ | — | ⭕ | 빠름, 라벨 포함 |
| press_imbalance | — | ⭕ | ⭕ | 불균형 시연 |
| welding_bead | — | ⭕ | ⭕ | 이미지 모달리티 |
| cnc_lathe_masked | — | — | ⭕ | dtype 혼재 |
| order_cp949 | — | — | ⭕ | CP949 인코딩 |
| wafer_defect | — | — | ⭕ | 6 클래스 이미지 + CNN |

★베타 환경 분리★: 시연용 4 시나리오 (사용자 합의)를 별도 환경(예: `docker-compose.beta.yml` 또는 같은 환경 다른 session_id) 에서 운영. 실제 운영 코드와 코드 자체는 동일, 데이터/세션만 분리.

---

## 부록 A. 자료구조 전체 예시 (실 JSON)

### A-1. `PipelineFull` 실제 값

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "line_id": "module_3_polymer_electronic",
  "stages": [
    {
      "stage_order": 0,
      "node_id": "injection_molding",
      "modules": [
        {
          "function": "process",
          "dataset_role": "L1_injection_optimize",
          "datalake_id": "kamp_L1_injection_optimize",
          "constraints": {
            "cycle_time_sec": [15, 180],
            "mold_temp_max_c": 400,
            "max_null_ratio": 0.1
          }
        },
        {
          "function": "quality",
          "dataset_role": "L1_injection_production",
          "datalake_id": "kamp_L1_injection_production",
          "constraints": {
            "required_columns": ["Label"]
          }
        }
      ]
    },
    {
      "stage_order": 4,
      "node_id": "semiconductor_inspect",
      "modules": [
        {
          "function": "quality",
          "dataset_role": "L2_wafer_defect",
          "datalake_id": "kamp_L2_wafer_defect",
          "constraints": {
            "required_mode": "RGB",
            "min_count_per_class": 30
          }
        }
      ]
    }
  ]
}
```

### A-2. `AggregatedContext` 실제 값 (Page 5 입력)

```json
{
  "session_id": "550e8400-...",
  "pipeline_structure": { "...PipelineStructure 참조..." },
  "pipeline_constraints": { "...각 모듈 constraints 모음..." },
  "key_findings": [
    {
      "type": "class_imbalance",
      "stage_order": 4,
      "module_function": "quality",
      "column": "Label",
      "minority_ratio": 0.0285,
      "severity": "high"
    },
    {
      "type": "transformation_applied",
      "stage_order": 0,
      "module_function": "process",
      "operation": "clean_masking",
      "column": "CV_005",
      "before_stats": { "dtype": "object", "nulls": 0 },
      "after_stats": { "dtype": "float64", "nulls": 240 }
    },
    {
      "type": "sensor_overflow_suspected",
      "stage_order": 0,
      "module_function": "process",
      "column": "Cushion_Position",
      "extreme_value": 4.29e8
    }
  ],
  "function_axis_summary": {
    "process": [{ "type": "transformation_applied", ... }],
    "quality": [{ "type": "class_imbalance", ... }],
    "maintenance": [],
    "reference": []
  },
  "stage_chain": [
    {
      "stage_order": 0,
      "node_id": "injection_molding",
      "main_findings": ["sensor overflow", "마스킹 처리됨"],
      "downstream_implication": "Stage 4 검사 결과에 영향 가능"
    }
  ],
  "agent_records": [
    {
      "stage_order": 0,
      "module_function": "process",
      "dataset_role": "L1_injection_optimize",
      "inspector": {
        "deterministic_flags": ["mixed dtype in 'CV_005'"],
        "modality_guess": "timeseries",
        "concerns": ["Cushion_Position 비현실적 최대값 (센서 오버플로 의심)"],
        "recommended_next_steps": ["clean_masking 적용", "outlier 처리"]
      },
      "planner": {
        "candidate_operations": ["clean_masking", "compute_stats"],
        "ordered_with_rationale": [
          { "operation": "clean_masking", "rationale": "마스킹 → 수치화 우선", "permission_level": "L2", "step_key": "clean_masking:CV_005" },
          { "operation": "compute_stats", "rationale": "기초 통계", "permission_level": "L1", "step_key": "compute_stats:global" }
        ],
        "llm_summary": "2단계 계획 — 마스킹 정리 후 기초 통계"
      },
      "executor": {
        "applied_steps": [
          { "step_key": "clean_masking:CV_005", "operation": "clean_masking", "before_stats": {...}, "after_stats": {...}, "lineage_id": "ln-001", "status": "done" }
        ],
        "rolled_back": []
      },
      "validator": {
        "passed": true,
        "issues": [],
        "next_action": "ready_for_ml"
      }
    }
  ],
  "user_intent": null
}
```

### A-3. `PipelineStatus` 실시간 스트림 예시 (Page 4 SSE)

```
event: status
data: {
  "session_id": "550e8400-...",
  "overall_progress": 0.45,
  "current_stage_order": 0,
  "current_module_index": 1,
  "stages": [...]
}

event: approval_required
data: {
  "stage_order": 0,
  "module_index": 0,
  "pending_approvals": [
    {
      "step_key": "clean_masking:CV_005",
      "operation": "clean_masking",
      "before_stats": {...},
      "predicted_after_stats": {...},
      "direction_text": "마스킹 → NaN → float64"
    }
  ]
}

event: stage_complete
data: { "stage_order": 0, "summary": "..." }
```

---

## 부록 B. 주요 API curl 예시 (16/25)

> 25 종합표는 Part 9-1 참조. 본 부록은 자주 사용되는 16개 엔드포인트 curl 예시. 미수록 9개: `/api/models`, `/api/sessions/{id}` (GET), `/api/datalake/{id}/metadata`, `/api/datalake/{id}` (DELETE), `/api/pipeline/{id}/status` (GET 폴링), `/api/analyze/{id}/results`, `/api/model/{id}/status`, `/api/model/{id}/dashboard`, `/api/model/{id}/cancel`.

```bash
# 1. 라인 카탈로그 조회
curl http://localhost:8000/api/lines

# 2. 세션 생성
curl -X POST http://localhost:8000/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"line_id": "module_3_polymer_electronic"}'

# 3. Pipeline 구조 저장 (Page 2 후)
curl -X PUT http://localhost:8000/api/sessions/{id}/structure \
  -H "Content-Type: application/json" \
  -d '{
    "line_id": "module_3_polymer_electronic",
    "stages": [{...}]
  }'

# 4. Data Lake 조회
curl "http://localhost:8000/api/datalake/list?modality=timeseries&function=process"

# 5. Data Lake 신규 등록 (Mode A 업로드)
curl -X POST http://localhost:8000/api/datalake/register \
  -F "name=my_injection_data" \
  -F "modality=timeseries" \
  -F "function_hint=process" \
  -F "file=@/path/to/local/data.csv"

# 6. Pipeline 전체 저장 (Page 3 후)
curl -X PUT http://localhost:8000/api/sessions/{id}/full \
  -H "Content-Type: application/json" \
  -d '{...PipelineFull...}'

# 7. 실행 트리거
curl -X POST http://localhost:8000/api/execute_pipeline \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "model": "gemma4:e4b"}'

# 8. SSE 스트림 구독
curl -N http://localhost:8000/api/pipeline/{id}/stream

# 9. 승인 (step_key 기반)
curl -X POST http://localhost:8000/api/pipeline/{id}/approve \
  -H "Content-Type: application/json" \
  -d '{
    "stage_order": 0,
    "module_index": 0,
    "step_key": "clean_masking:CV_005"
  }'

# 10. 자연어 입력
curl -X POST http://localhost:8000/api/pipeline/{id}/natural_input \
  -H "Content-Type: application/json" \
  -d '{
    "stage_order": 0,
    "module_index": 0,
    "natural_text": "CV_005는 그대로 두고 진행해줘"
  }'

# 11. AggregatedContext 조회
curl http://localhost:8000/api/aggregate_context/{id}

# 12. 자동 질문
curl http://localhost:8000/api/analyze/{id}/questions

# 13. 분석 목적 선택
curl -X POST http://localhost:8000/api/analyze/{id}/select \
  -H "Content-Type: application/json" \
  -d '{"analysis_purpose": "quality_classification"}'

# 14. 모델 추천
curl http://localhost:8000/api/model/{id}/recommend

# 15. 학습 트리거
curl -X POST http://localhost:8000/api/model/{id}/train \
  -H "Content-Type: application/json" \
  -d '{"model_name": "XGBoost", "mode": "full"}'

# 16. 학습 결과
curl http://localhost:8000/api/model/{id}/results
```

---

## 부록 C. 상태 천이 다이어그램

### C-1. Session Status 천이

```
created  ──[POST sessions/create]──▶  building
   │
   │  [PUT sessions/{id}/structure]
   ▼
data  ──[PUT sessions/{id}/full]──▶  running
   │
   │  [POST execute_pipeline]
   ▼
running  ──[모든 Stage done]──▶  analyzing
   │       │
   │       └──[Validator concern]──▶  validation_concern
   │
   │  [POST analyze/select]
   ▼
analyzing  ──[EDA 완료]──▶  modeling
   │
   │  [POST model/train]
   ▼
modeling  ──[학습 완료]──▶  done
   │
   ▼
done   (최종)

언제든 [세션 만료] 또는 [사용자 명시 중단] → cancelled
```

### C-2. Module 처리 상태 천이 (Page 4)

```
pending  ──▶  inspecting  ──▶  planning  ──▶  executing
                                                 │
                                                 ├──[L1 자동]──▶  validating  ──▶  done
                                                 │
                                                 └──[L2/L3 미승인]──▶  awaiting_approval
                                                                          │
                                                                          ├──[승인]──▶ executing 재개
                                                                          └──[거부]──▶  skipped

언제든 [실패] → failed
언제든 [사용자 미업로드 skip] → pending → skipped
```

### C-3. 데이터 흐름 천이 (페이지 간)

```
[Page 1]                    line_id
   ↓
[Page 2]                    + PipelineStructure
   ↓
[Page 3]                    + PipelineFull (+ DataLakeEntry 참조)
   ↓
[Page 4]                    + PipelineResults (실시간) + 사용자 승인 토큰
   ↓ Stage 완료 시 자동
[Context Aggregator]        AggregatedContext 생성
   ↓
[Page 5]                    + AnalysisQuestion + user_intent + EDA 결과
   ↓
[Page 6]                    + 모델 추천 + 학습 결과 (model_results)
   ↓
[완료]                       세션 status = "done"
```

---


---

## Phase 3 마무리 — 명세서 전체 완성

### Phase 3 작성 범위 (본 파일)
- Part 8: 컴포넌트 라이브러리 — 22 React 컴포넌트 + props + 트리 + 색상 매핑
- Part 9: 전체 API/자료구조 종합 — 25 엔드포인트 표 + 8 자료구조 표 + 데이터 흐름
- Part 10: 에러 처리 종합 — 페이지별 케이스 + 표준 코드 11종 + 재시도 정책
- Part 11: 테스트 시나리오 — E2E 6 시나리오 + 챌린지 8 회귀 + 단위 7
- Part 12: 데모 시나리오 — 3분/7분/15분 분배 + 4 시나리오 매트릭스 + 베타 환경
- 부록 A: 자료구조 실 JSON 예시 (PipelineFull / AggregatedContext / PipelineStatus)
- 부록 B: API curl 예시 16개
- 부록 C: 상태 천이 다이어그램 (Session / Module / Page 간 데이터 흐름)

### 명세서 전체 완성 — Phase 1 + 2 + 3 통합 확인

| 영역 | Phase 1 (spec-1) | Phase 2 (spec-2) | Phase 3 (spec-3) |
|---|---|---|---|
| 메타 + Executive Summary | ⭕ Part 0 | — | — |
| 공통 설계 원칙 | ⭕ Part 1 (1-1~1-9) | — | — |
| Page 1 (Line 선택) | ⭕ Part 2 | — | — |
| Page 2 (Pipeline 구성) | ⭕ Part 3 | — | — |
| Page 3 (데이터+제약) | ⭕ Part 4 | — | — |
| Page 4 (표준화 진행) | — | ⭕ Part 5 | — |
| Page 5 (분석 목적+EDA) | — | ⭕ Part 6 | — |
| Page 6 (모델링) | — | ⭕ Part 7 | — |
| 컴포넌트 라이브러리 | — | — | ⭕ Part 8 |
| API/자료구조 종합 | — | — | ⭕ Part 9 |
| 에러 처리 종합 | — | — | ⭕ Part 10 |
| 테스트 시나리오 | — | — | ⭕ Part 11 |
| 데모 시나리오 | — | — | ⭕ Part 12 |
| 부록 A (자료구조 JSON) | — | — | ⭕ |
| 부록 B (API curl) | — | — | ⭕ |
| 부록 C (상태 천이) | — | — | ⭕ |

### Phase 3 에서 누적된 설계 결정 사항 요약

> `0_CHANGELOG_v5.md` 는 알파 진입 후 기록 시작 (현재 비어 있음). 본 섹션은 v5 설계 단계에서 누적된 마지막 결정의 요약.

- Phase 3 종합 작성: 컴포넌트 라이브러리 22종 + 25 API 종합 + 에러 처리 + 테스트 + 데모 + 부록 A/B/C
- Part 1-9-9 알파/베타/운영 검증 체계 신설 (3 단계 분리)
- `0_CHANGELOG_v5.md` 정책: 알파 진입 후부터 기록 시작
- 페이지별 prefix 명명 규칙 확정 (step1_line ~ step6_modeling)
- `0_variable_index_v5.md` 신설 (변수 목차, 확장 추적)
- 명세서 spec-1 / spec-2 / spec-3 Phase 별 3 분할 + 인수인계 템플릿

### 다음 단계 — 알파 테스트 진입

명세서 v5 (분할판) 완성. 다음:

1. **알파 단계 진입**
   - 개발자 자체 테스트
   - 환경: `data/lake/kamp/` 더미
   - 검증 항목: Phase 3 의 8 (컴포넌트/API/에러/테스트/데모/부록 A·B·C) + Part 1-9 의 LLM 모니터링 7 지표
   - 발견 사항 → `0_CHANGELOG_v5.md` 즉시 기록 (알파 첫 발견부터 기록 시작)

2. **알파 완료 → 명세 v6 갱신**
   - constraint_keys 5 필드 적정성 (Part 1-9-2)
   - LLM 모니터링 임계 위반 시 활용 영역 축소 (Part 1-9-3)
   - step_key 매칭 정합 (Part 1-9-4)
   - 발견된 누락 케이스 추가

3. **베타 단계** (4 시나리오 시연)
   - 환경 분리: docker-compose.beta.yml 또는 같은 환경 beta session
   - 검증: UX + 시연 흐름 + 차별점 5가지 전달

4. **운영 단계** (실제 SI 고객)
   - KAMP 등록 시나리오 A/B 최종 결정 (Part 1-9-1)

### 최종 산출물 (사용자 검토 대기)

| 파일 | 분량 | 역할 |
|---|---|---|
| `0_project_blueprint_v5.md` | ~1388줄 | 프로젝트 마스터 청사진 |
| `0_pipeline_ui_spec-1_v5.md` | ~1750줄 | Phase 1 — 공통 + Page 1~3 |
| `0_pipeline_ui_spec-2_v5.md` | ~830줄 | Phase 2 — Page 4~6 |
| `0_pipeline_ui_spec-3_v5.md` | ~970줄 | Phase 3 — 종합 + 부록 |
| `0_variable_index_v5.md` | ~370줄 | 변수 목차 |
| `0_CHANGELOG_v5.md` | ~92줄 | 변경 이력 |

---

**이전 파일**: `0_pipeline_ui_spec-2_v5.md` (Phase 2)
**다음 파일**: 없음 (명세서 마무리)

**작성**: 2026-05-27 spec-3 v5 (Claude Opus 4.7, 분할 + 인수인계 + 명세서 전체 완성)
