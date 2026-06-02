# 0_variable_index_v5 — manufacturing-mcp 변수 목차 (v5)

> **목적**: 추후 공정·MCP 도구·작업·API·컴포넌트 등 확장 가능한 항목 추가 시 한눈에 영향 범위 파악. 책의 목차처럼 변수명 list + 각 변수의 정의/사용 위치 인덱스.
>
> **갱신 정책**: 변수 추가/제거/이동 시 본 파일 즉시 갱신 + `0_CHANGELOG_v5.md` 에 변경 사유 + 영향 파일 + 기초 설계도 정합 기록.
>
> **작성일**: 2026-05-27 (Phase 1+2+3 완료 + 재구조화 요청 반영)

---

## 사용법

1. **새 변수 추가 (예: 신규 모달리티/MCP 도구/작업)**
   1. 해당 섹션에 1줄 추가
   2. 각 줄: `<변수명>` + 정의 위치 + 사용 위치들 + 관련 명세 위치
   3. `0_CHANGELOG_v5.md` 에 변경 이력 기록

2. **변수 위치 확인 (예: "Function 축이 어디서 사용되나?")**
   - 해당 섹션 → "사용처" 컬럼 확인 → 영향 코드/명세 즉시 파악

3. **기초 설계도와의 정합**
   - 4 파일 기준: `CLAUDE.md` / `decisions.md` / `0_project_blueprint_v5.md` / 본 파일
   - 신규 항목은 위 4 파일 정합 보장 필수

---

## 1. 모달리티 (Modality, 4종 고정)

> **확장 정책**: 5번째 모달리티 추가 ❌ (CLAUDE.md §1). 영업 메시지 "MCP 안 늘어남" 보호.

| 모달리티 | 정의 위치 (서버) | 도구 위치 | 데이터 위치 | 명세 |
|---|---|---|---|---|
| `timeseries` | `mcp-servers/timeseries/server.py` | `mcp-servers/timeseries/tools.py` | `data/lake/kamp/L1_press_forming/`, `L1_cnc_lathe_quality/` 등 (시나리오 A 가정, spec-1 Part 1-9-1 결정 대기) | spec-1.md Part 1-3 |
| `inspection-image` | `mcp-servers/inspection-image/server.py` | `mcp-servers/inspection-image/tools.py` | `data/lake/kamp/L2_wafer_defect/`, `L2_welding_bead/` 등 (시나리오 A 가정) | 〃 |
| `event-log` | `mcp-servers/event-log/server.py` | `mcp-servers/event-log/tools.py` | `data/lake/kamp/<event-log 더미>/` (시나리오 A 가정) | 〃 |
| `order` | `mcp-servers/order/server.py` | `mcp-servers/order/tools.py` | `data/lake/kamp/order_cp949/` (시나리오 A 가정) | 〃 |

각 MCP 서버 = FastAPI HTTP, 같은 7도구 계약 (CLAUDE.md §4).

---

## 2. Function 축 (4종)

> **확장 정책**: 새 Function 축 추가 가능. 단 사용자 정의 분석 목적(custom)은 별도 처리 (LLM 매핑 후 4종 중 하나로 흡수).

| Function | 정의 (예정) | 사용처 | UI 라벨 |
|---|---|---|---|
| `process` | `catalogs/functions.yaml` (예정) | `agents/planner/planner.py` (module_context), spec-1.md Part 4-3 | `step5_analyze/` QuestionRadioGroup |
| `quality` | 〃 | 〃 | 〃 |
| `maintenance` | 〃 | 〃 | 〃 |
| `reference` | 〃 | 〃 | 〃 |

주의: 코드의 권한 등급 (L1/L2/L3) 과 완전히 다른 차원. blueprint Part 6-3 참조.

---

## 3. Line (3종, KAMP 기준)

> **확장 정책**: 새 Line 추가 가능 (사용자 자기 공정). `catalogs/lines.yaml` 에 추가.

| Line ID | Display | Max Stages | 정의 |
|---|---|---|---|
| `module_1_metal_processing` | 금속 가공·검사 라인 | 6 | `catalogs/lines.yaml` (STEP 1B-1, 실재) |
| `module_2_forming_joining` | 성형·접합·표면처리·회전기 라인 | 5 | 〃 |
| `module_3_polymer_electronic` | 폴리머 성형·전자 검사·진동 신호 라인 | 7 | 〃 |

---

## 4. 공정 노드 (Node, 18종)

> **확장 정책**: Line 별로 추가 가능. `catalogs/lines.yaml` 의 stages 배열에 추가.

### Line 1 — 금속 가공·검사 (6 Node)
| Node ID | Display | Max Modules | hint_datasets |
|---|---|---|---|
| `primary_forming` | 1차 성형 | 2 | L3_mold_condition, L3_mold_anomaly |
| `cnc_cutting` | CNC 절삭 | 2 | L1_cnc_lathe_quality, L3_cnc_roughing |
| `mct_machining` | MCT 가공 | 3 | L1_mct_tool_manage, L1_mct_tool_improve, L3_mct_condition_inspect |
| `precision_inspect` | 정밀 가공·치수 검사 | 2 | L2_cnc_load_dimension, L3_precision_machine |
| `surface_inspect` | 표면 검사 | 1 | L2_inspection_image |
| `pdm` | PdM 설비 | 3 | L3_rotary_drill, L3_solenoid_roughing, L3_guideloader_drill |

### Line 2 — 성형·접합·표면처리·회전기 (5 Node)
| Node ID | Display | Max Modules | hint_datasets |
|---|---|---|---|
| `press_forming` | 프레스 성형 | 2 | L1_press_forming, L2_press_aluminum |
| `welding` | 용접 | 2 | L1_welding_auto, L1_welding_condition |
| `welding_inspect` | 용접 검사 | 2 | L2_welding_bead, L2_welding_electrode |
| `surface_treatment` | 표면 처리·테이핑 | 1 | L2_vision_taping |
| `rotary_pdm` | 회전기 PdM | 2 | L3_blower_vibration, L3_elevator_vibration |

### Line 3 — 폴리머 성형·전자 검사·진동 신호 (7 Node)
| Node ID | Display | Max Modules | hint_datasets |
|---|---|---|---|
| `order_planning` | 주문 계획 | 1 | order_cp949 |
| `injection_molding` | 사출 성형 | 3 | L1_injection_optimize, L1_injection_production, L1_cnc_machine_optimize |
| `extrusion` | 압출 | 1 | L3_extrusion_pdm |
| `precision_parts` | 정밀 부품 | 1 | L3_vacuum_pump |
| `semiconductor_inspect` | 반도체 검사 | 2 | L2_auto_console_detect, L2_wafer_defect |
| `ict_inspection` | ICT 검사 | 2 | L4_ict_checker, L4_ict_inspection |
| `vibration_simulation` | 진동 시뮬 | 2 | L3_vibration_fault_sim, L3_vibration_fault_sim2 |

총 18 Node × 34 Module 슬롯.

---

## 5. 페이지 + Prefix (6종, 새 명명 규칙)

> **확장 정책**: 페이지 추가 시 prefix 형식 `step<N>_<주제>` 유지.

| Page | Prefix | 역할 | 단계 |
|---|---|---|---|
| 1 | `step1_line` | Line 선택 | 진입 |
| 2 | `step2_user_input_pipeline` | Pipeline 구성 (1-1) | 앞단 |
| 3 | `step3_user_input_data` | 데이터+제약 입력 (1-2) | 앞단 |
| 4 | `step4_standardize` | MCP 표준화 진행 | 중간단 |
| 5 | `step5_analyze` | 분석 목적 + EDA | 뒷단 |
| 6 | `step6_modeling` | 모델링 | 뒷단 |

### 적용 위치

#### 프론트엔드 (디렉터리)
```
frontend/
  ├── step1_line/                        # Page 1
  │   ├── LineSelectPage.tsx
  │   ├── LineRadioGroup.tsx
  │   └── index.ts
  ├── step2_user_input_pipeline/          # Page 2
  │   ├── PipelineBuildPage.tsx
  │   ├── CatalogPanel.tsx
  │   ├── StageBox.tsx
  │   ├── ModuleCard.tsx
  │   └── index.ts
  ├── step3_user_input_data/              # Page 3
  │   ├── DataConstraintPage.tsx
  │   ├── DatasetSelector.tsx
  │   ├── ConstraintForm.tsx
  │   ├── UploadModal.tsx
  │   └── index.ts
  ├── step4_standardize/                  # Page 4
  │   ├── StandardizePage.tsx
  │   ├── ApprovalCard.tsx
  │   ├── NaturalInput.tsx
  │   ├── AlarmBanner.tsx
  │   ├── LLMInterpretationPanel.tsx
  │   └── index.ts
  ├── step5_analyze/                      # Page 5
  │   ├── AnalyzePage.tsx
  │   ├── QuestionRadioGroup.tsx
  │   ├── ChartPanel.tsx
  │   ├── DataGuardWrapper.tsx
  │   └── index.ts
  └── step6_modeling/                     # Page 6
      ├── ModelingPage.tsx
      ├── ModelCard.tsx
      ├── TwoDepthDecisionModal.tsx
      ├── TrainingProgress.tsx
      ├── ResultsDashboard.tsx
      ├── SHAPModal.tsx
      └── index.ts
```

#### 백엔드 (라우터 파일)
```
backend/routers/
  ├── step1_line.py             # GET /api/lines, POST /api/sessions/create
  ├── step2_user_input_pipeline.py  # PUT /api/sessions/{id}/structure
  ├── step3_user_input_data.py  # /api/datalake/*, PUT /api/sessions/{id}/full
  ├── step4_standardize.py      # /api/execute_pipeline, /api/pipeline/{id}/*, /api/aggregate_context/{id} (Page 4 완료 시 자동 트리거)
  ├── step5_analyze.py          # /api/analyze/{id}/*
  └── step6_modeling.py         # /api/model/{id}/*
```

---

## 6. OPERATION_PERMISSION (12종)

> **단일 소스**: `harness/guardrails.py`. Planner 와 양쪽 동기화 필수.
> **확장 정책**: 새 작업 추가 시 `harness/guardrails.py` + `agents/planner/planner_schemas.py` (OperationType) 둘 다 갱신. Planner LLM이 새 작업 생성 ❌ (가드레일이 차단).

### L1 (자동 실행, 3종)
| 작업 | 설명 | 정의 |
|---|---|---|
| `detect_encoding` | 인코딩 정규화 (cp949 → utf-8) | `harness/guardrails.py` |
| `reparse_header` | 헤더 재파싱 (header=None 후 처리) | 〃 |
| `compute_stats` | 기초 통계 | 〃 |

### L2 (제안+승인, 6종)
| 작업 | 설명 | 정의 |
|---|---|---|
| `clean_masking` | 마스킹 문자(`*`, `**`, `***`) → NaN → 수치화 | `harness/guardrails.py` |
| `fill_missing` | 결측치 채움 | 〃 |
| `remove_outlier` | 이상치 제거 | 〃 |
| `create_feature` | 피처 생성 | 〃 |
| `balance_classes` | 클래스 불균형 보정 (STEP 2a: 옵션 4종 — class_weight/smote/random_under/skip via strategy 필드, D-103) | 〃 |
| `normalize_group` | 의미 그룹 단위 정규화 (우려1) | 〃 |

### L3 (차단+백업, 3종)
| 작업 | 설명 | 정의 |
|---|---|---|
| `drop_column` | 컬럼 삭제 | `harness/guardrails.py` |
| `relabel` | 라벨 재정의 | 〃 |
| `merge_external` | 외부 데이터 병합 | 〃 |

---

## 7. MCP 7도구 (모달리티 공통)

> **확장 정책**: 8번째 도구 추가 시 본 파일 + spec Part 1-3 + CLAUDE.md §4 + 모든 모달리티 서버 갱신. 검토 신중.

| 도구 | 권한 | HTTP 메서드 | 정의 | 명세 |
|---|---|---|---|---|
| `list_columns` | L1 | GET | `mcp-servers/*/tools.py` | spec-1.md Part 1-3 |
| `get_schema` | L1 | GET | 〃 | 〃 |
| `sample` | L1 | GET | 〃 | 〃 |
| `detect_encoding` | L1 | GET | 〃 | 〃 |
| **`check_constraints`** | L1 | **POST** | 〃 | 〃 |
| **`apply_preprocessing`** | L1/L2/L3 | **POST** | 〃 | 〃 |
| `lineage` | L1 | GET | 〃 | 〃 |

POST 2개 (check_constraints, apply_preprocessing) — body 에 dataset_id + constraints/operations 전달.

---

## 8. 자료구조 (8종)

> **확장 정책**: 새 자료구조 추가 시 spec Part 1-2 갱신.

| 자료구조 | 정의 | 생성 시점 | 저장 |
|---|---|---|---|
| `LineCatalog` | spec-1.md Part 1-2 (가) | 시스템 정적 | `catalogs/lines.yaml` (실재, STEP 1B-1) |
| `PipelineStructure` | spec-1.md Part 1-2 (나) | Page 2 출력 | DB `sessions.structure` (JSONB) |
| `PipelineFull` | spec-1.md Part 1-2 (다) | Page 3 출력 | DB `sessions.full_data` + 파일 시스템 |
| **`PipelineSession` | STEP 1B-2a 명세 §2 | `/api/sessions/create` 시점 | **`backend/session_store.py::_SESSIONS` 인메모리 (D-52, Sprint 2에 postgres) |
| `PipelineResults` | spec-1.md Part 1-2 (라) | Page 4 출력 | DB `sessions.results` + `lineage.transformations` |
| `PipelineStatus` | spec-2.md Part 5-2 | Page 4 실시간 | 메모리 (현재 폴링; SSE는 1B-3) |
| `AnalysisQuestion` | spec-1.md Part 1-2 (마) | Page 5 자동 생성 | DB `sessions.analysis` |
| `DataLakeEntry` | spec-1.md Part 1-2 (사) | 등록 시점 | DB `datalake.entries` |
| **`AggregatedContext` | spec-1.md Part 1-2 (바) | execute_pipeline 완료 직후 자동 트리거 (D-63) | **실재 (STEP 1B-2b): `session["aggregated_context"]` 인메모리 캐시, Sprint 2에 postgres |

특히 `AggregatedContext` 의 `agent_records` 필드 = MCP 4단 판단 기록 보존 (사용자 비전 핵심).

### `PipelineSession` 필드 (STEP 1B-2a 실재 인메모리)
| 필드 | 타입 | 역할 |
|---|---|---|
| `session_id` | str(uuid4) | 키 |
| `pipeline_full` | dict | 1-1 + 1-2 출력 (`line_id`, `stages[]`) |
| `status` | str | `created`/`running`/`awaiting_approval`/`completed`/`error` |
| `approved_step_keys` | list[str] | 누적 승인 (set은 JSON 직렬화 안 됨 → list) |
| `completed_stage_orders` | list[int] | resume 시 skip |
| `completed_module_keys` | list[str] | "stage.idx" 형식, resume 시 skip |
| `pending` | dict\|None | suspend 시 멈춘 지점 (`{stage_order, module_key, dataset_id, plan, pending_steps[]}`) |
| `module_results` | dict | `module_key → {profile, plan, execution, validation, modality, dataset_id}` |
| `accumulated_context` | list[dict] | Stage 요약 누적 (1B-2b Aggregator 입력) |
| `alarms` | list[dict] | `llm_judge_data_necessity` 기록 (stage당 1회) |
| `aggregated_context` | dict | STEP 1B-2b — Context Aggregator 결과 캐시 (`completed` 직후 자동 생성, 결정론) |
| `model` | str \| None | STEP 1B-3d B2 — 이 세션이 사용할 Ollama 모델 (D-99). None이면 환경변수 `OLLAMA_MODEL` 폴백. `PUT /sessions/{id}/model` 또는 `sessions/create.model`로 설정 |
| `selected_options` | dict[step_key, option_id] | STEP 2a (D-103/107) — 옵션 카드 선택 결과. `ApproveReq.selected_option`이 `BALANCE_OPTION_IDS` 안의 값이면 `{step_key: option_id}`로 저장. `run_execute`에 전달돼 `_op_balance_classes(strategy=...)` 분기 |

### `AggregatedContext` 필드 (STEP 1B-2b 실재, 5영역 + user_intent)
spec-1 Part 1-2 (바) 정합. 생성: `agents/aggregator/context_aggregator.py::aggregate(session)` (결정론, LLM 0).

| 영역 | 필드 | 비고 |
|---|---|---|
| A | `pipeline_structure` | session.pipeline_full 그대로 (1-1 + 1-2 입력 보존) |
| A | `pipeline_constraints` | `{"stage.idx": {...constraints}}` — D-65 표기 |
| B | `key_findings` | 결정론 추출 (Inspector flags + Executor done steps + Validator issues). type ∈ {class_imbalance, missing_values, dtype_mixed, transformation_applied, sequence_normalized, constraint_violation, validation_concern} |
| C | `function_axis_summary` | `{process,quality,maintenance,reference}` 4키 고정, finding 분류 |
| D | `stage_chain` | `[{stage_order, node_id, main_findings, downstream_implication}]` — 함의는 사전정의 7종 템플릿 매핑 |
| E | `agent_records` | 4단 기록 원본 보존 (Inspector/Planner/Executor/Validator 손실 0) |
| F | `user_intent` | 이번 범위 항상 `None` (Page 5 미구현, D-64) |

---

## 9. API 엔드포인트 (25종)

> 종합 표는 spec-3.md Part 9-1 참조. 페이지별로:

| Prefix | API 엔드포인트 |
|---|---|
| `step1_line` | `GET /api/lines` **실재 (1B-1)**, `GET /api/models` **실재**, `POST /api/sessions/create` **실재 (1B-2a, 1B-3a 확장: line_id 또는 pipeline_full)** |
| `step2_user_input_pipeline` | **실재 (1B-3a)** `GET /api/sessions/{id}`, `PUT /api/sessions/{id}/structure` |
| `step3_user_input_data` | **실재 (1B-3b/1B-3c)** `GET /api/datasets/all`, `GET /api/modules`, `GET /api/datasets/{id}/columns` (D-93), `PUT /api/sessions/{id}/full` · (예정, STEP 3) `GET /api/datalake/list`, `POST /api/datalake/register`, `GET /api/datalake/{id}/metadata`, `DELETE /api/datalake/{id}` |
| `step4_standardize` | **실재 (STEP 1B-2a)** `POST /api/execute_pipeline`, `GET /api/pipeline/{id}/status`, `POST /api/pipeline/{id}/approve` · **실재 (STEP 1B-2b)** `GET /api/aggregate_context/{id}` · (예정) `GET /api/pipeline/{id}/stream` (SSE, 1B-3), `POST /api/pipeline/{id}/natural_input` |
| `step5_analyze` | **실재 (1B-3c)** `GET /api/analyze/{id}/questions` (LLM purpose recommend, D-91), `POST /api/analyze/{id}/select` (user_intent 갱신) · (예정, STEP 3) `GET /api/analyze/{id}/results` (실 EDA) |
| `step6_modeling` | **실재 (1B-3c)** `GET /api/model/{id}/recommend` (LLM model recommend + fit_score 1~5, D-92) · (예정, STEP 3) `POST /api/model/{id}/train`, `GET /api/model/{id}/status`, `GET /api/model/{id}/results`, `GET /api/model/{id}/dashboard`, `POST /api/model/{id}/cancel` |

**추가 정책**: 새 엔드포인트 추가 시 본 파일 + spec Part 1-3/9 + 해당 라우터 파일 갱신.

### STEP 1B-2a 4 엔드포인트 (Resumable Orchestrator, 폴링형)
| 메서드 | 경로 | 입력 | 반환 | 비고 |
|---|---|---|---|---|
| POST | `/api/sessions/create` | `{pipeline_full}` | `{session_id, status:"created"}` | uuid4 |
| POST | `/api/execute_pipeline` | `{session_id, model?}` | `{status, pending?, session, aggregated_context?}` | suspend-and-return (D-51). 재호출로 resume. completed 시 `aggregated_context` 포함 (D-63) |
| GET  | `/api/pipeline/{sid}/status` | (path) | `public_view(session)` | 폴링 — SSE 미사용 |
| POST | `/api/pipeline/{sid}/approve` | `{step_key, stage_order?, module_index?}` | `{approved, approved_count, ...}` | step_key 누적, resume 트리거 안 함 (D-56) |

### STEP 1B-2b 1 엔드포인트 (Context Aggregator, 결정론)
| 메서드 | 경로 | 입력 | 반환 | 비고 |
|---|---|---|---|---|
| GET | `/api/aggregate_context/{sid}` | (path) | `AggregatedContext` (5영역 + user_intent=None) | LLM 호출 0 (D-59). 캐시 있으면 그대로 반환. 같은 입력 → 같은 출력 100% |

### STEP 1B-3a 2 엔드포인트 (세션 조회/구조 저장)
| 메서드 | 경로 | 입력 | 반환 | 비고 |
|---|---|---|---|---|
| GET | `/api/sessions/{sid}` | (path) | `public_view(session) + line_id` | Page 2 진입/새로고침 복원. 404 처리 |
| PUT | `/api/sessions/{sid}/structure` | `{line_id, stages[]}` | `{session_id, status:"structured", stage_count, module_count}` | Page 2 드래그앤드롭 출력 저장. 데이터/제약은 Page 3에서 |

`POST /api/sessions/create` 시그니처 갱신(1B-3a, D-74): `{line_id?, pipeline_full?}` 둘 중 1개 필수. line_id만 오면 빈 stages로 초기화, pipeline_full 그대로 호출도 회귀 없음.

### STEP 1B-3b 3 엔드포인트 (Page 3 카탈로그/저장)
| 메서드 | 경로 | 입력 | 반환 | 비고 |
|---|---|---|---|---|
| GET | `/api/datasets/all` | — | `{datasets_by_modality:{timeseries[], inspection-image[], event-log[], order[]}}` | 4 MCP 서버 fan out (디렉터리 스캔, D-82). 한 서버 다운돼도 빈 리스트로 반환 |
| GET | `/api/modules` | — | `{modules: <modules.yaml>}` | Page 3 constraint 폼 + Page 6 모델 추천 소스. 5 Node × constraint_keys 구조 |
| PUT | `/api/sessions/{sid}/full` | `{pipeline_full}` | `{session_id, status:"ready", modules_total, modules_with_data, modules_with_constraints}` | Page 3 출력 PipelineFull 저장. execute_pipeline 처리 대상 |

### STEP 1B-3c 4 엔드포인트 (실 컬럼 + Page 5/6 LLM 추천)
| 메서드 | 경로 | 입력 | 반환 | 비고 |
|---|---|---|---|---|
| GET | `/api/datasets/{id}/columns` | `?modality, &numeric_only=true` | `{dataset_id, modality, columns:[{name,dtype,semantic_group,null_count}], n_total, n_numeric}` | D-93/94 — MCP `/list_columns`(7도구) 위임. Page 3 실 컬럼 드롭다운 소스. D-90 해결 |
| GET | `/api/analyze/{sid}/questions` | (path) | `{recommendations:[{option,rank,rationale_ko}], all_options, llm_status, llm_error?, model_used}` | D-91 — LLM 분석목적 추천. ANALYSIS_PURPOSES(6종) 외 코드로 차단. 1B-3d B1+B3: 세션 model 사용 + llm_status 표면화 (D-99, D-101) |
| POST | `/api/analyze/{sid}/select` | `{analysis_purpose, free_input?}` | `{analysis_purpose, function_axis, free_input}` | user_intent 갱신 (AggregatedContext의 1B-2b None 자리). `_PURPOSE_FUNCTION` 결정론 매핑 |
| GET | `/api/model/{sid}/recommend` | (path) | `{recommendations:[{name,fit_score(1~5),rationale_ko,context_reflections,task,when,from_node,advisory_only}], available_models, user_purpose, llm_status, llm_error?, model_used}` | D-92 — LLM 모델 추천. recommended_models(modules.yaml) 풀 + fit_score 1~5 외 코드로 차단. `advisory_only` (VRAM 초과 등)는 권고만 표시. 1B-3d B1+B3: 세션 model 사용 + llm_status 표면화 (D-99, D-101) |

### STEP 1B-3d 1 엔드포인트 (세션 model 저장 — B2)
| 메서드 | 경로 | 입력 | 반환 | 비고 |
|---|---|---|---|---|
| PUT | `/api/sessions/{sid}/model` | `{model}` | `{session_id, model}` | D-99 — 드롭다운 선택을 세션에 영속화. `model=""` 보내면 해제(환경변수 폴백). 이후 모든 LLM 호출이 `session["model"]` 사용 |

`POST /api/sessions/create` 시그니처 갱신(1B-3d, D-99): 옵션 `model: str | None = None` 추가 — 세션 생성 시 사용자 선호 모델을 같이 받아 저장 (LineSelectPage가 `localStorage.preferred_model` 동봉).
`PipelineSession` 필드에 `model: str|None` 추가 — `session_store.public_view`에 노출. `execute_pipeline`은 `session.get("model") or req.model` 우선순위로 Inspector/Planner/judge에 전달.

### STEP 2a 옵션 카드 (브랜치 `feature/step2-option-cards`, D-103~D-109)
- `PlanStep` 필드 신설 (`agents/planner/planner_schemas.py`):
  - `available_options: list[dict]` — balance_classes step에만 채움(`BALANCE_OPTIONS` 4종). 다른 step은 빈 list (회귀 0)
  - `preview: dict` — 결정론 미리보기 (행수 추정). execute_pipeline suspend 단계에서 채움
  - `step_key` property 불변 — `(operation, semantic_group|target|"global")` 그대로 → 기존 승인 누적 호환
- `ApproveReq` 확장: `selected_option: str | None = None`. 환각 방어 — `BALANCE_OPTION_IDS` 안의 값만 저장
- 신규 모듈 `agents/executor/balance_options.py` — `BALANCE_OPTIONS`, `BALANCE_OPTION_IDS`, `compute_balance_preview(df, col)`. LLM import 0
- `executor.execute(plan, approved_keys, modality, selected_options)` 신규 파라미터 — None이면 기존 동작 (회귀 0)
- `_op_balance_classes(df, col, strategy=None)` — strategy(class_weight/skip/smote/random_under/None) 분기. SMOTE·Under는 미리보기 추정만(STEP 3 실 적용)
- lineage: `params.selected_option=<id>` 기록 — 추적성 (D-109)

#### `balance_options.py` 심볼 (LLM 0)
| 심볼 | 역할 |
|---|---|
| `BALANCE_OPTIONS` | 4 옵션 dict 리스트 — id/label/description/effect/weight/caution. 코드 고정 (LLM 생성 ❌) |
| `BALANCE_OPTION_IDS` | frozenset — `ApproveReq.selected_option` 환각 방어 필터 |
| `compute_balance_preview(df, col)` | 결정론 산식 — class_weight(sklearn 'balanced'), smote(majority×n), random_under(minority×n), skip(유지). 단일 클래스 → `applicable=False` |

### STEP 2b 옵션 카드 UI (브랜치 `feature/step2-option-cards`, D-110~D-117)
- `ApprovalCard.jsx` props 확장:
  - `selectedOptions: {step_key: option_id}` — 부모(StandardizePage) 단일 출처 (D-113)
  - `onSelectOption(step_key, option_id)` — 카드 클릭 콜백
  - `onApprove`/`onApproveAll`은 selected_option을 4번째 인자/per-step으로 동봉
- `OptionCardGroup` 내부 컴포넌트 (ApprovalCard.jsx 안에 정의):
  - `preview.current` 분포 요약(예: "현재 분포: PASS 2915 / FAIL 85 (소수 클래스 2.83%)")
  - 4 카드 그리드 (`.opt-cards` repeat(auto-fit, minmax(180px,1fr))) — 각 카드 label/preview/sub(가중치)/desc/caution
  - `RECOMMENDED_OPTION = "class_weight"` → "권장" 배지 (D-112)
  - 강제 선택 가드: `disabled={busy || !selected}` (D-111)
- `StandardizePage.jsx`:
  - `selectedOptions` state
  - `onApprove(sk, so, mi, selected_option=null)` 4-arg — POST body에 `selected_option` 동봉 (D-114)
  - "전체 승인" 가드: `hasUnselectedOptionStep` 있으면 disable
- `frontend/vite.config.js` `allowedHosts: true` (dev infra, D-117)
- 회귀 0: `available_options.length === 0`이면 OptionCardGroup 안 그림, 기존 yes/no 그대로 (D-115)

### STEP 3a EDA 실엔진 (브랜치 `feature/step3-eda-ml`, D-118~D-130)
LLM 판단(차트 추천) + 코드 실행(결정론 차트 데이터) + LLM 자연어 요약 + 자연어 코드 EDA(3중 안전).

| 엔드포인트 | req | res 핵심 |
|---|---|---|
| `POST /api/analyze/{sid}/eda/plan` | `{function_axis?: str}` | `{available, function_axis, modality, dataset_id, recommended_charts:[{chart_type,target_column?,label_column?,reason_ko}], profile:{rows,n_cols,columns}, llm_status, model_used}`. 폴백 시 항목에 `fallback:true` (D-121) |
| `POST /api/analyze/{sid}/eda/render` | `{charts:[{chart_type, ...}]}` | `{charts:[{chart_type, label, data:{...}}]}`. 항목별 `error` 또는 `data.error` (modality 가드/compute 실패) |
| `POST /api/analyze/{sid}/eda/summary` | `{chart_type, stats, findings?}` | `{summary, key_points, llm_status}`. bogus chart_type → 400 |
| `POST /api/analyze/{sid}/eda/freeform` | `{user_query}` | `{status: "awaiting_approval"\|"rejected"\|"llm_failed", code?, reason?, query?, model_used}` |
| `POST /api/analyze/{sid}/eda/freeform/approve` | `{approved: bool}` | `{status: "executed"\|"cancelled"\|"exec_failed"\|"rejected_at_exec"\|"no_pending", result?, result_type?, lineage_id?, code?, query?, error?, reason?}` |

`agents/eda/` 신규 패키지:
| 모듈 | 핵심 심볼 |
|---|---|
| `chart_types.py` | `CHART_TYPES`(8종 spec), `CHART_TYPE_IDS`(frozenset 환각 방어), `FUNCTION_CHART_GUIDE`(참고/폴백), `is_chart_modality_ok` |
| `eda_engine.py` | `processed_path`/`load_processed_df`(parquet 직접 로드, D-119), `_apply_row_guard`/`_topn_categories`/`_sliding_window_mean_signal`(가드 4종 D-124), `build_eda_profile`(LLM 입력), `llm_recommend_charts`(추천 LLM), `filter_recommendations`+`fallback_charts_from_guide`(환각 방어 + 폴백), `compute_chart_data`(LLM 0, 8 chart 모두), `llm_chart_summary`(요약 LLM) |
| `code_sandbox.py` | `ALLOWED_NODES`(31)/`FORBIDDEN_NAMES`(18)/`ALLOWED_ROOT_NAMES`(6) 세 frozenset(D-126), `validate_eda_code`(AST 화이트리스트), `sandbox_exec`(__builtins__={} + df.copy() + SIGALRM 5s, D-127), `_coerce_result`(pd/np → JSON), `llm_generate_eda_code`(자연어 → 코드 제안) |

신규 `PipelineSession` 키 (기존 키 미변경 — 회귀 0, D-129):
| 키 | 채워지는 시점 |
|---|---|
| `eda_plan` | `/eda/plan` — 환각 방어 필터 통과한 추천 차트 list |
| `eda_results` | `/eda/render` — 차트별 data 또는 error |
| `pending_eda_code` | `/eda/freeform` 승인 대기 — `{code, query, dataset_id, modality}` |
| `last_eda_freeform_result` | `/eda/freeform/approve` 성공 시 — `{query, code, result, result_type, lineage_id}` |

`backend/main.py`:
- `_pick_eda_target(session) -> (dataset_id, modality)` — `module_results` 정렬 후 첫 비-이미지 모듈 (D-123)
- `sys.path.insert(0, ROOT/"agents"/"eda")` — 디렉터리별 path 패턴 유지 (D-130, `agents/`만 넣으면 `from inspector import inspect` 회귀)
- Pydantic req 모델: `EdaPlanReq`/`EdaRenderReq`/`EdaSummaryReq`/`EdaFreeformReq`/`EdaApproveCodeReq`

### STEP 3b EDA 차트 UI (브랜치 `feature/step3-eda-ml`, D-131~D-140)
STEP 3a 백엔드를 사용자 화면으로. AnalyzePage의 eda-skeleton 한 블록만 교체 — 다른 페이지·다른 영역 0.

| 파일 | 역할 |
|---|---|
| `frontend/package.json` | `recharts: ^3.8.1` 신규 deps (D-131, 빌드 타임 번들 — 런타임 외부 호출 0) |
| `step5_analyze/charts/common.js` | `AXIS`·`GRID`·`TOOLTIP_STYLE`·`COLORS`·`CHART_HEIGHT` 공통 recharts props (CSS 변수 다크 톤, D-137) |
| `step5_analyze/charts/ChartCard.jsx` | 디스패처 — `CHART_COMPONENTS` 매핑 + `ChartError`/`ChartFooter` + AI 요약 훅(`/eda/summary` 클릭, D-136) |
| `step5_analyze/charts/Histogram.jsx` | BarChart (bins 중점→x, counts→y, fill=process) |
| `step5_analyze/charts/BoxPlot.jsx` | **ComposedChart + ErrorBar** — stacked Bar(투명 q1 + 보이는 q3-q1) + ErrorBar(median±[low,high]) + 커스텀 Tooltip 5수치+n (D-133) |
| `step5_analyze/charts/FftSpectrum.jsx` | LineChart (freqs→x, magnitude→y, stroke=maintenance) |
| `step5_analyze/charts/RmsTrend.jsx` | LineChart (indices→x, rms→y, stroke=maintenance) |
| `step5_analyze/charts/ClassDistribution.jsx` | BarChart (labels→x, counts→y, fill=quality) |
| `step5_analyze/charts/CorrelationBar.jsx` | BarChart layout="vertical" (columns→y, values→x, 동적 높이) |
| `step5_analyze/charts/Pareto.jsx` | ComposedChart Bar(counts, reference) + Line(cumulative_pct, maintenance) dual-YAxis 0~100% |
| `step5_analyze/charts/Scatter.jsx` | ScatterChart (x,y 페어, fill=process opacity 0.55) |
| `step5_analyze/FreeformEda.jsx` | 자연어 → `/eda/freeform` → 코드 미리보기(monospace) → 승인/취소 → `/eda/freeform/approve` → 결과+lineage_id (D-135, ApprovalCard L2 톤 차용) |
| `step5_analyze/AnalyzePage.jsx` | `runEda()`(`/plan` → `/render`), `savedResult` user_intent 복원(D-138), eda-skeleton 블록 → `<section className="eda-charts">` 교체, key_findings는 `<details>` 폴딩(D-139). Page 6 링크 보존 |
| `frontend/src/styles.css` | 신규 클래스만 추가(D-140) — `.eda-charts`/`.chart-grid`/`.chart-card`/`.chart-card-head`/`.chart-footer`/`.chart-error`/`.btn-sm`/`.chart-summary`/`.chart-keypoints`/`.freeform-eda`/`.freeform-input`/`.freeform-approve`/`.code-preview`/`.freeform-actions`/`.freeform-result`/`.result-json`/`.findings-details`. 기존 클래스 미수정 |

UX 흐름 (D-134 명시 클릭 모델):
1. /select 후 (`savedResult` 존재) → "EDA 실행" 버튼 노출
2. 클릭 → `/plan` (LLM e4b ~9초) → `recommended_charts` 받음 → 즉시 `/render` (결정론) → 차트 N개 렌더
3. 차트별 "AI 요약" 버튼 클릭 → `/summary` (LLM e4b ~4초) → 카드 내부 하단 표시
4. 자연어 EDA: 입력 → "분석 요청" → 코드 미리보기 → "승인 후 실행" → 결과 + lineage_id 표시

### `backend/llm.py` 헬퍼 (1B-3d B3, D-101)
| 심볼 | 역할 |
|---|---|
| `generate(prompt, system?, fmt_json?, model?)` | Ollama /api/generate 래퍼. HTTP 에러 시 `{"_llm_failed": True, error, hint, model_attempted}` 마커 JSON 문자열 반환 (위장 안 함) |
| `_coerce_json(raw)` | LLM 출력에서 JSON 견고 추출: 코드펜스 제거 + 첫 `{...}` 추출. 실패 시 None |
| `_try_parse_llm(raw)` | `generate()` 결과를 dict로 변환. `_llm_failed` 마커 보존. 호출부가 dict.get("_llm_failed")만 체크하면 됨 |
| `generate_json(prompt, system?, model?, retries=2)` | `generate` + `_try_parse_llm` + 재시도. 호출부 권장 진입점 |

---

## 10. React 컴포넌트 (22종)

> 종합은 spec-3.md Part 8 참조. 페이지별로:

| Prefix | 컴포넌트 |
|---|---|
| (공통, 모든 페이지 — `frontend/step_common/`) | `ModelDropdown`, `Breadcrumb`, `ProgressBar` (Page 4·6 진행률 공용) |
| `step1_line` | `LineRadioGroup` |
| `step2_user_input_pipeline` | `StageBox` (DnD), `ModuleCard` (draggable), `CatalogPanel` |
| `step3_user_input_data` | `ModuleCard` (expandable), `DatasetSelector`, `ConstraintForm`, `UploadModal` |
| `step4_standardize` | `ApprovalCard`, `NaturalInput` (Page 4·5 공용), `AlarmBanner`, `LLMInterpretationPanel` |
| `step5_analyze` | `QuestionRadioGroup`, `ChartPanel`, `DataGuardWrapper` |
| `step6_modeling` | `ModelCard`, `TwoDepthDecisionModal`, `TrainingProgress`, `ResultsDashboard`, `SHAPModal`, `ModuleCard` (재사용) |

---

## 11. 카탈로그 파일 (`catalogs/`)

> **STEP 1B-1에서 1순위 2개 실재화** (lines.yaml + modules.yaml). 나머지는 단계별 추가.

| 파일 | 상태 | 내용 | 우선순위 | 명세 정의 |
|---|---|---|---|---|
| `catalogs/lines.yaml` | **실재 (STEP 1B-1)** | Line 3 × Stage × Node × Module 슬롯 (위 §3, §4) | 1순위 | spec-1.md Part 1-2 (가), blueprint 부록 A |
| `catalogs/modules.yaml` | **실재 (STEP 1B-1, 5 Node)** | Node 별 도메인 지식 (constraint_keys 구조만, **typical_ranges 디폴트 금지** — D-43) | 1순위 | spec-1.md Part 1-2 (가) constraint_keys |
| `catalogs/modalities.yaml` | 예정 | 4 모달리티 정의 (UI 메타) | 2순위 | 위 §1 |
| `catalogs/functions.yaml` | 예정 | 4 Function 축 + 분석 목적 매핑 | 2순위 | 위 §2 + blueprint 부록 B |
| `catalogs/data_guards.yaml` | 예정 | Page 5 데이터 규모 가드 7종 | 3순위 | spec-2.md Part 6-5 |
| `catalogs/recommended_models.yaml` | 예정 | 모델 추천 풀 | 3순위 | spec-2.md Part 7-2 |

각 파일 헤더 권장 형식:
```yaml
# <파일명>
# ──────────────────────────────────────────────────────
# 정의: <무엇을 정의하는가>
# 사용처: <어디서 사용되는가 — 코드 파일 list>
# 확장 정책: <추가/변경 시 주의 사항>
# 정합: <CLAUDE.md / decisions.md / 명세서 참조>
# ──────────────────────────────────────────────────────

<내용>
```

---

## 12. 환각 방어 메커니즘 위치

> **확장 정책**: 새 LLM 호출 지점 추가 시 반드시 환각 방어 메커니즘 명시 + 본 표 갱신.

| 위치 | 메커니즘 | 명세 위치 |
|---|---|---|
| Inspector | LLM = 해석만 (modality_guess/concerns/next_steps), JSON 강제 | spec-1.md Part 4-2 (가) |
| Planner | 후보 = 진실의 원천. LLM = 순서·이유만. 새 작업 ❌ | spec-1.md Part 4-2 (나) |
| Context Aggregator | 결정론 (LLM 없음, 환각 위험 0) | blueprint Part 4-4 + spec-1.md Part 1-9-7 |
| Page 4 승인 카드 | 통계 미리보기 = 결정론 계산만 | spec-1.md Part 1-7 + spec-2.md Part 5-5 |
| Page 4 자연어 입력 | 매핑 = OPERATION_PERMISSION 12종 중 1개만 + 사용자 재확인 강제 | spec-1.md Part 1-7 + spec-2.md Part 5-6 |
| Page 5 자동 질문 | `available_options` 6중 1~2 추천만 | spec-2.md Part 6-2 |
| Page 5 EDA 자연어 요약 | 숫자 입력값 그대로 인용 + 새 추론 ❌ + 2~3문장 제한 | spec-2.md Part 6-6 |
| Page 6 모델 추천 | `available_models` 만 + fit_score 1-5 범위 강제 | spec-2.md Part 7-2 |
| LLM judge (미업로드 알람) | 알람/스킵 판단만, 결정은 사용자 | spec-1.md Part 4-5 |
| LLM judge (constraint_keys 필수성) | 알람만, 입력은 사용자 | spec-1.md Part 4-5 |

---

## 12.5. Validator 검증 (사전+사후 양방향, STEP 1B-2c 갱신)

> **단일 소스**: `agents/validator/validator.py`. **LLM 호출 0** (생명선).
> **확장 정책**: 7번째 검증 추가 시 본 표 + Validator 본 파일 + 명세 갱신.

### 사전 검증 (Executor 전, STEP 1B-2c 신규)
| 검증 | 헬퍼 | 입력 | 무엇을 보나 | 도입 |
|---|---|---|---|---|
| 사전 | `validate_plan` | plan, profile | 순서 규칙(_ORDER_RANK) + 작업 충돌(drop_column+같은컬럼) + L3 정보성. blocking 기준은 high(충돌)만 | **D-70 (STEP 1B-2c)** |

### 사후 검증 6종 (Executor 후, STEP 1B-2c 갱신)
| 검증 | 헬퍼 | 입력 | 무엇을 보나 | 도입 |
|---|---|---|---|---|
| 1. 컴플라이언스 | `_check_compliance` | results | done 단계의 lineage 누락 | D-36 (STEP 1) |
| 2. 변환 결과 | `_check_transform_result` | results | fill_missing 결측 감소, normalize 멤버 수 등 | D-36 |
| 3. 계획 무결성 | `_check_plan_integrity` | results, plan | 같은 작업 중복(operation+target) | D-36 |
| 4. 회귀 | `_check_regression` | results, profile | 행 급감(50% 이상 손실) | D-36 |
| 5. constraint | `_check_constraint_violation` | execution, constraints | 사용자 constraints 범위 위반 행 수. **원본 backup_path 기준** (D-43, **D-67**) | D-48 → 수정 D-67 |
| 6. **output_health | `_check_output_health` | execution | Inf 발생 / 변환된 컬럼 std==0 / 그룹 정규화 사후조건 이탈(블록 mean≈0, std≈1). "고장 감지"만, "정상성 판단" X(Page 5 LLM으로) | **D-68/D-69 (STEP 1B-2c) |

`validate(execution, plan=None, profile=None, constraints=None)` — constraints 비면 5번, output_path 없으면 6번 skip (회귀 0).
`validate_plan(plan, profile=None)` — sync. 반환 `{plan_ok, plan_issues, blocking, n_high, n_medium, n_low}`.

---

## 13. 검증 체계 (알파/베타/운영)

> spec-1.md Part 1-9-9 참조. 요약:

| 단계 | 데이터 | 사용자 | 검증 우선 |
|---|---|---|---|
| 알파 | KAMP 더미 (`data/lake/kamp/` — 시나리오 A 가정, 알파 시 1-9-1 결정 확정) | 개발자 본인 | Phase 3 의 8 검증 항목 모두 (컴포넌트/API/에러/테스트/데모/부록 A·B·C) + LLM 모니터링 7 지표 + 데이터 경로 시나리오 A/B 최종 결정 |
| 베타 | 4 시나리오 (B/D/A/C) | 팀원 시연 | UX + 시연 흐름 + 차별점 5가지 전달 |
| 운영 | 고객 자기 데이터 (`data/lake/registered/`) | 공장 관리자 | 실용성 + 가치 + KAMP 등록 시나리오 A/B 결정 |

---

## 14. 문서 인덱스

본 프로젝트의 문서 파일들 (v5 통일):

진입 가이드: **`0_README_v5.md`** (가장 먼저 읽기)


| 문서 | 위치 | 역할 |
|---|---|---|
| `0_project_blueprint_v5.md` | `/home/byeonggab89/FINAL/manufacturing-mcp/` | 프로젝트 마스터 청사진 (Line/Function/3축 모델/LLM 통합 패턴) |
| `0_pipeline_ui_spec-1_v5.md` | 〃 | Phase 1 — 공통 설계 + Page 1~3 |
| `0_pipeline_ui_spec-2_v5.md` | 〃 | Phase 2 — Page 4~6 |
| `0_pipeline_ui_spec-3_v5.md` | 〃 | Phase 3 — 종합 + 부록 |
| `0_variable_index_v5.md` | 〃 | 본 파일 — 변수 목차 |
| `0_CHANGELOG_v5.md` | 〃 | 변경 이력 (기초 설계도 정합) |
| `CLAUDE.md` | `/home/byeonggab89/FINAL/manufacturing-mcp/` | 설계 헌법 |
| `docs/decisions.md` | 〃 | 결정 기록 |

### 단계 진입 시 필독 (사용자 합의)

각 Phase 진입 시 3 파일 필독:
1. `0_project_blueprint_v5.md` (청사진)
2. `0_CHANGELOG_v5.md` (변경 로그)
3. 해당 Phase 명세서 (`0_pipeline_ui_spec-1_v5.md` / `-2.md` / `-3.md`)

추가: 변수 추가/변경 작업 시 본 파일 (`0_variable_index_v5.md`) 도 필독.

---

## 갱신 이력 (간단)

> 상세 이력은 `0_CHANGELOG_v5.md` 참조.

- 2026-05-27: 신규 작성 (Phase 1+2+3 완료 + 사용자 재구조화 요청 반영)
- 2026-05-28: STEP 1B-1 반영 — catalogs/lines.yaml·modules.yaml 실재화 (§11), Validator 5번째 검증 표 추가 (§12.5), D-43~D-50 결정
- 2026-05-28: STEP 1B-2a 반영 — `PipelineSession` 실재 (§8), 폴링형 4 엔드포인트 표 (§9), D-51~D-58 결정
- 2026-05-28: STEP 1B-2b 반영 — `AggregatedContext` 실재 (§8 5영역 표), `/api/aggregate_context` 엔드포인트 (§9), D-59~D-65 결정 (LLM 호출 0 생명선)
- 2026-05-28: STEP 1B-2c 반영 — Validator 사전+사후 양방향 (§12.5 갱신), D-66 해결(constraint 원본 기준), D-67~D-73 결정. `ExecutionResult.backup_path` 신설
- 2026-05-29: STEP 1B-3a 반영 — React+Vite frontend 실재화 (Page 1·2), 세션 GET/PUT structure 엔드포인트 추가 (§9), D-74~D-81 결정. 기존 `frontend/index.html` → `_legacy_dashboard.html` 보존
- 2026-05-29: STEP 1B-3b 반영 — Page 3·4 실재화 (§5), `/api/datasets/all`·`/api/modules`·`PUT /sessions/{id}/full` 3 엔드포인트 (§9), D-82~D-89 결정. 데이터 비종속성 정책(D-82) 명시
- 2026-06-01: STEP 1B-3c 반영 — Page 3 실 컬럼 폼(D-90 해결, D-93), Page 5·6 실재화 (LLM 추천), 4 엔드포인트 (§9). D-91~D-98 결정. STEP 1B 전체 완료
- 2026-06-01: STEP 1B-3d 반영 — LLM model 전달 버그 3개(B1/B2/B3) 수정. `PipelineSession.model` 필드 + `PUT /sessions/{id}/model` 엔드포인트 (§9). `backend/llm.py` `_llm_failed` 마커 + `_try_parse_llm` + `generate_json` (§9). D-99~D-102 결정. 8GB VRAM 모델 전략 정정 — 데모/개발=e4b, 26b 운영=24GB+ GPU 전제
- 2026-06-02: STEP 2a 반영 (브랜치 `feature/step2-option-cards`) — balance_classes 옵션 카드 4종 + 결정론 미리보기. `PlanStep.available_options/preview` + `PipelineSession.selected_options` + `ApproveReq.selected_option` (환각 방어). `agents/executor/balance_options.py` 신규. D-103~D-109 결정. LLM 호출 횟수 불변(옵션 풀 코드 고정), strategy None=레거시 동작(회귀 0)
- 2026-06-02: STEP 2b 반영 (브랜치 `feature/step2-option-cards`) — Page 4 ApprovalCard 옵션 카드 UI(카드형 + 강제 선택 + 권장 배지). `OptionCardGroup` 컴포넌트, `selectedOptions` state, `selected_option` POST body 동봉. `vite.config.js allowedHosts: true` (Playwright dev infra). D-110~D-117 결정. 회귀 0(available_options 빈 step은 기존 yes/no 그대로)
- 2026-06-02: STEP 3a 반영 (브랜치 `feature/step3-eda-ml`) — Page 5 EDA 골격을 실엔진으로. 3a-1 LLM 차트 추천(`/eda/plan`) + 결정론 차트 데이터(`/eda/render`, 8 chart 종 — fft/boxplot/histogram/class_dist/correlation/scatter/pareto/rms_trend) + LLM 자연어 요약(`/eda/summary`). 3a-2 자연어 코드 EDA(`/eda/freeform` + `/eda/freeform/approve`) + 3중 안전(AST 화이트리스트 + builtins 차단 샌드박스 + 사용자 승인 + lineage). `agents/eda/__init__.py`·`chart_types.py`(`CHART_TYPES`·`CHART_TYPE_IDS` frozenset·`FUNCTION_CHART_GUIDE`)·`eda_engine.py`(`build_eda_profile`·`compute_chart_data`·`llm_recommend_charts`·`llm_chart_summary`·가드 4종)·`code_sandbox.py`(`ALLOWED_NODES`·`FORBIDDEN_NAMES`·`validate_eda_code`·`sandbox_exec`) 신규. `_pick_eda_target` 헬퍼 + `sys.path.insert(0, ROOT/"agents"/"eda")` (D-130). D-118~D-130 결정. parquet 직접 로드(MCP 7도구 계약 무손상) / scipy 미도입(numpy.fft) / inspection-image EDA 제외 / 회귀 0(`/select`·`/questions`·`/aggregate_context` 불변)
- 2026-06-02: STEP 3b 반영 (브랜치 `feature/step3-eda-ml`) — Page 5 EDA 차트 UI 실엔진. recharts ^3.8.1 도입(빌드 타임 번들, 런타임 외부 호출 0). `step5_analyze/charts/` 9 파일(ChartCard 디스패처 + 8 차트 컴포넌트 + common.js). BoxPlot은 ComposedChart + ErrorBar(D-133). `FreeformEda.jsx` 자연어 EDA UI(코드 미리보기 → 승인/취소 → 결과+lineage_id). AnalyzePage skeleton 한 블록만 교체 + savedResult 복원(D-138) + key_findings details 폴딩(D-139). styles.css 신규 클래스만(D-140). D-131~D-140 결정. 사용자 명시 클릭 모델(D-134, /plan 자동 호출 X), AI 요약 차트별 클릭만(D-136). 회귀 0(/select·QuestionRadioGroup·"다음→Page 6" 링크·다른 페이지 모두 보존)
