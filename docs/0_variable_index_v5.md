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
| `balance_classes` | 클래스 불균형 보정 | 〃 |
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
| ★`PipelineSession` | STEP 1B-2a 명세 §2 | `/api/sessions/create` 시점 | ★`backend/session_store.py::_SESSIONS` 인메모리★ (D-52, Sprint 2에 postgres) |
| `PipelineResults` | spec-1.md Part 1-2 (라) | Page 4 출력 | DB `sessions.results` + `lineage.transformations` |
| `PipelineStatus` | spec-2.md Part 5-2 | Page 4 실시간 | 메모리 (현재 폴링; SSE는 1B-3) |
| `AnalysisQuestion` | spec-1.md Part 1-2 (마) | Page 5 자동 생성 | DB `sessions.analysis` |
| `DataLakeEntry` | spec-1.md Part 1-2 (사) | 등록 시점 | DB `datalake.entries` |
| ★`AggregatedContext` | spec-1.md Part 1-2 (바) | execute_pipeline 완료 직후 자동 트리거 (D-63) | ★실재 (STEP 1B-2b): `session["aggregated_context"]` 인메모리 캐시, Sprint 2에 postgres★ |

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
| ★`aggregated_context` | dict | STEP 1B-2b — Context Aggregator 결과 캐시 (`completed` 직후 자동 생성, 결정론) |

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
| `step1_line` | `GET /api/lines` ★실재 (STEP 1B-1)★, `GET /api/models`, `POST /api/sessions/create` ★실재 (STEP 1B-2a)★ |
| `step2_user_input_pipeline` | `GET /api/sessions/{id}` (예정), `PUT /api/sessions/{id}/structure` (예정) |
| `step3_user_input_data` | `GET /api/datalake/list`, `POST /api/datalake/register`, `GET /api/datalake/{id}/metadata`, `DELETE /api/datalake/{id}`, `PUT /api/sessions/{id}/full` (모두 예정) |
| `step4_standardize` | ★실재 (STEP 1B-2a)★ `POST /api/execute_pipeline`, `GET /api/pipeline/{id}/status`, `POST /api/pipeline/{id}/approve` · ★실재 (STEP 1B-2b)★ `GET /api/aggregate_context/{id}` · (예정) `GET /api/pipeline/{id}/stream` (SSE, 1B-3), `POST /api/pipeline/{id}/natural_input` |
| `step5_analyze` | `GET /api/analyze/{id}/questions`, `POST /api/analyze/{id}/select`, `GET /api/analyze/{id}/results` (예정) |
| `step6_modeling` | `GET /api/model/{id}/recommend`, `POST /api/model/{id}/train`, `GET /api/model/{id}/status`, `GET /api/model/{id}/results`, `GET /api/model/{id}/dashboard`, `POST /api/model/{id}/cancel` (예정) |

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
| `catalogs/lines.yaml` | ★실재 (STEP 1B-1)★ | Line 3 × Stage × Node × Module 슬롯 (위 §3, §4) | 1순위 | spec-1.md Part 1-2 (가), blueprint 부록 A |
| `catalogs/modules.yaml` | ★실재 (STEP 1B-1, 5 Node)★ | Node 별 도메인 지식 (constraint_keys 구조만, **typical_ranges 디폴트 금지** — D-43) | 1순위 | spec-1.md Part 1-2 (가) constraint_keys |
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

## 12.5. Validator 검증 종류 (5종, STEP 1B-1 갱신)

> **단일 소스**: `agents/validator/validator.py`.
> **확장 정책**: 6번째 검증 추가 시 본 표 + Validator 본 파일 + 명세 갱신.

| 검증 | 헬퍼 | 입력 | 무엇을 보나 | 도입 |
|---|---|---|---|---|
| 1. 컴플라이언스 | `_check_compliance` | results | done 단계의 lineage 누락 | D-36 (STEP 1) |
| 2. 변환 결과 | `_check_transform_result` | results | fill_missing 결측 감소, normalize 멤버 수 등 | D-36 |
| 3. 계획 무결성 | `_check_plan_integrity` | results, plan | 같은 작업 중복(operation+target) | D-36 |
| 4. 회귀 | `_check_regression` | results, profile | 행 급감(50% 이상 손실) | D-36 |
| 5. ★constraint | `_check_constraint_violation` | execution, constraints | 사용자 입력 constraints의 범위 위반 행 수 (processed parquet 결정론 산수) — typical_ranges 디폴트 아님 (D-43) | ★D-48 (STEP 1B-1)★ |

`validate(execution, plan=None, profile=None, constraints=None)` — constraints가 비면 5번 검증 skip (회귀 0).

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
