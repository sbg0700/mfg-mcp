# pipeline_ui_spec-1_v5 — Phase 1 (구조 + 공통 설계 + 페이지 1~3, v5)

> **목적**: STEP 1B UI 구현 명세 Phase 1. Page 1~3 (앞단) 화면·API·자료구조 + 공통 설계 원칙 + 검증/모니터링.
>
> **분할 정보**: 본 명세서는 3 파일로 분할됨.
> - **spec-1 (본 파일)** = Phase 1 (구조 + 공통 + Page 1~3)
> - `0_pipeline_ui_spec-2_v5.md` = Phase 2 (Page 4~6)
> - `0_pipeline_ui_spec-3_v5.md` = Phase 3 (종합 + 부록)
>
> **Snapshot**: 2026-05-27 v5 (분할판 + 명명 규칙 + 변수 목차 + CHANGELOG 통합)
>
> **상위 문서**: `0_project_blueprint_v5.md` (프로젝트 마스터)
> **변경 이력**: `0_CHANGELOG_v5.md` (모든 변경 + 정합 추적)
> **변수 목차**: `0_variable_index_v5.md` (확장 가능 항목 인덱스)
>
> **단계 진입 시 필독 (3 파일)**:
> 1. `0_project_blueprint_v5.md` (청사진)
> 2. `0_CHANGELOG_v5.md` (변경 로그)
> 3. 본 파일 (Phase 1 명세)
>
> **다음 Phase**: `0_pipeline_ui_spec-2_v5.md` (Phase 2, Page 4~6)
>
> **명명 규칙 (Step 1~3 합의 — 변수 목차 §5 참조)**:
> - 페이지별 prefix: `step1_line` / `step2_user_input_pipeline` / `step3_user_input_data` / `step4_standardize` / `step5_analyze` / `step6_modeling`
> - 변수 추가 시 `0_variable_index_v5.md` 즉시 갱신

---

## 이전 단계 검증

본 파일은 Phase 1 (시작 단계) — 이전 단계 없음.

### 본 명세 작업 진입 전 필독·검증 항목

- [ ] `0_project_blueprint_v5.md` 숙독 (프로젝트 마스터)
- [ ] `0_CHANGELOG_v5.md` 알파 진입 후 기록 확인 (v5 시점은 비어 있음)
- [ ] `0_variable_index_v5.md` 변수 목차 인지 (특히 §1~5 모달리티/Function/Line/Node/페이지+Prefix)
- [ ] `CLAUDE.md` §1~5 절대 규칙 인지
- [ ] `docs/decisions.md` D-01~31 결정 인지
- [ ] 사용자 비전 6단계 페이지 시퀀스 인지 (blueprint Part 2)
- [ ] 옵션 E (사전정의 카탈로그 + 드래그앤드롭 + 컨텍스트 누적) 인지
- [ ] 4 모달리티 + 4 Function 축 + 3 Line + 18 Node 매핑 인지

### 본 명세 작업 시 적용할 결정 사항

| 영역 | 결정 (사용자 합의) |
|---|---|
| Page 4 진행률 | SSE 기본 + 폴링 폴백 |
| Page 4→5 이동 | 사용자 수동 클릭 |
| Page 6 결과 송출 | 지표+Confusion+Importance 기본 / 풀 대시보드 확장 |
| 드래그앤드롭 라이브러리 | HTML5 native (권장) |
| DnD 그래프 라이브러리 | React Flow ❌ (단순 박스+화살표) |
| Module Catalog typical_ranges | ❌ (사용자 입력 1순위) — `constraint_keys` 도입 |
| Data Lake 정책 | 통합 인터페이스 (작은/큰 분리 없음) |
| L2/L3 승인 UI | 카드 + 자연어 (구체 UI는 팀원 디벨롭 방안 참조) |
| Context Aggregator | 결정론 (LLM 없음, 환각 0) |
| Page 5 EDA 차트 | 외부 AI 검증 4 Function 매핑 (메모리 `project_eda_charts.md` 참조) |
| 알파/베타/운영 검증 | 3 단계 분리 (Part 1-9-9 참조) |

위 검증 통과 후 본 명세 진입.

---

## Part 0. Executive Summary — 6 페이지 흐름 한눈에

```
┌─────────────────────────────────────────────────────────────────┐
│ Page 1: Line 선택 (/)                                            │
│  → 라디오 버튼 3개 → POST 세션 생성 → /pipeline/build            │
├─────────────────────────────────────────────────────────────────┤
│ Page 2: Pipeline 구성 (1-1, /pipeline/build)                     │
│  좌측 카탈로그 + 우측 Stage 박스 + 드래그앤드롭                  │
│  → pipeline_structure 저장 → /pipeline/data                      │
├─────────────────────────────────────────────────────────────────┤
│ Page 3: 데이터 + 제약 입력 (1-2, /pipeline/data)                 │
│  Data Lake에서 데이터 선택 (또는 신규 등록) + 제약 폼            │
│  → pipeline_full 저장 → POST /api/execute_pipeline               │
│  → /pipeline/run                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Page 4: 표준화 진행 (/pipeline/run)                              │
│  Stage 별 진행률 + LLM 해석 + 승인 게이트 (카드+자연어)          │
│  → pipeline_results → /pipeline/analyze                          │
├─────────────────────────────────────────────────────────────────┤
│ Page 5: 분석 목적 + 전처리 (/pipeline/analyze)                   │
│  자동 질문 후보 → 사용자 선택 → EDA/이상치 결과                  │
│  → /pipeline/model                                               │
├─────────────────────────────────────────────────────────────────┤
│ Page 6: 모델링 (/pipeline/model)                                 │
│  추천 모델 카드 → 승인 → 학습 → 지표 표시                        │
└─────────────────────────────────────────────────────────────────┘

각 페이지 좌상단: Line/세션 정보 (breadcrumb)
각 페이지 우상단: 모델 드롭다운 (gemma4:e4b / gemma4:26b)
```

---

## Part 1. 공통 설계 원칙

### 1-1. 기술 스택

권장: 최소 의존성 스택.

| 영역 | 선택 | 이유 |
|---|---|---|
| Frontend 프레임워크 | **React 18 + Vite** | 빠른 dev server + HMR |
| 상태 관리 | **React useState + useReducer** | 페이지 간 상태는 URL/세션 ID + 백엔드 GET 으로 복원 |
| 드래그앤드롭 | **HTML5 native DnD API** (권장) | 의존성 0. 대안: react-dnd 경량 |
| HTTP 클라이언트 | **fetch API** (native) | axios 같은 의존성 추가 불필요 |
| 차트 (Page 5~6) | **recharts** 또는 **Chart.js** | 경량 차트 라이브러리 1개만 |
| 스타일링 | **CSS Modules** 또는 **inline style** | Tailwind 같은 빌드 의존성 회피 |
| Backend | 기존 **FastAPI** 유지 | 변경 없음 |

권장안 — 사용자 검토 시 수정 가능.

### 1-2. 자료구조 종합

본 명세에 등장하는 모든 자료구조를 한 곳에 모음.

#### (가) `LineCatalog` — `GET /api/lines` 응답 (v4 갱신)

```python
{
  "lines": [
    {
      "line_id": str,           # 예: "module_1_metal_processing"
      "display_name": str,      # 예: "금속 가공·검사 라인"
      "max_stages": int,
      "stages": [
        {
          "node_id": str,
          "display_name": str,
          "max_modules": int,
          "available_modules": [
            {
              "function": str,         # "process"|"quality"|"maintenance"|"reference"
              "hint_dataset": str      # UI 가이드 (KAMP 데이터셋 ID)
            }
          ],
          "constraint_keys": [          # v4 신규 — 사용자가 입력할 제약 종류
            {
              "key": str,               # 예: "cycle_time_sec"
              "type": str,              # "range"|"single_value"|"ratio"|"list"|"text"
              "unit": str,              # 예: "초", "°C", "%"
              "label_kr": str,          # 사용자 친화 표시명
              "required_for": [str]     # 어떤 Function에서 필수인지 ["maintenance"]
            }
          ]
        }
      ]
    }
  ]
}
```

> v3의 `typical_ranges` 디폴트 값 제거. Module Catalog는 구조 가이드(`constraint_keys`)만 제공. 실제 값은 사용자가 1-2 페이지에서 입력.

#### (나) `PipelineStructure` — Page 2(1-1) 출력

```python
{
  "session_id": str,
  "line_id": str,
  "vid": str,                      # DL 신규 — 공정 흐름(라인) 단위 가상 그룹 ID (D-162). Page 1 라인 선택에서 결정
  "stages": [
    {
      "stage_order": int,
      "node_id": str,
      "modules": [
        {
          "function": str,         # "process"|"quality"|"maintenance"|"reference" — 같은 function 복수 허용 (D-165)
          "dataset_role": str,
          "chain_order": int | None,   # DL 신규 — P(process) 모듈의 흐름 순서. P가 아니면 None (D-165)
          "attached_to": str | None    # DL 신규 — M/Q 모듈이 부착된 P 모듈 식별자(예: "stageN.idxM"). P/R이면 None (D-165)
        }
      ]
    }
  ]
}
```

빈 슬롯은 list에 등장 안 함. LLM에 전달 안 됨.

#### (다) `PipelineFull` — Page 3(1-2) 출력 (v4 갱신)

```python
{
  "session_id": str,
  "line_id": str,
  "vid": str,                          # DL 신규 — 공정 흐름 가상 그룹 ID (D-162)
  "stages": [
    {
      "stage_order": int,
      "node_id": str,
      "modules": [
        {
          "function": str,
          "dataset_role": str,
          "chain_order": int | None,    # DL 신규 — P 모듈 흐름 순서 (D-165)
          "attached_to": str | None,    # DL 신규 — M/Q→P 부착 (D-165)
          "datalake_id": str | None,    # Data Lake catalog 키. 실제 파일경로는 datalake.get(id)→data_path로 백엔드 조회 (D-159/D-163)
          "constraints": {               # 사용자가 직접 입력 (디폴트 없음, D-43). prefill은 제안일 뿐 항상 재승인 (D-167)
            "<column>": "<value>"        # 키 스코프 = datalake_id+column (D-167)
          }
        }
      ]
    }
  ]
}
```

> v3 `data_path` → `datalake_id`. 실제 파일경로는 `datalake.get(datalake_id)→{data_path, modality}` 결정론 라우터가 조회(D-163, LLM 0). 제약 키는 `datalake_id+column` 스코프(D-167).

#### (라) `PipelineResults` — Page 4 응답, Page 5 입력 (v4 코드 확인 갱신)

```python
{
  "session_id": str,
  "pipeline_results": [
    {
      "stage_order": int,
      "node_id": str,
      "data_warning": dict | None,
      "modules": [
        {
          "function": str,
          "dataset_role": str,
          "profile": DataProfile,         # Inspector 출력
          "plan": PreprocessingPlan,      # Planner 출력 (PlanStep 리스트)
          "execution": ExecutionResult,   # Executor 출력 (StepResult 리스트)
          "validation": ValidationReport  # Validator 출력
        }
      ]
    }
  ]
}
```

PlanStep / StepResult 의 실제 필드 (코드 확인 기반):

```python
class PlanStep:
    order: int
    operation: OperationType    # 12종 (Part 1-9-4 매핑 참조)
    target_column: str | None
    permission_level: "L1"|"L2"|"L3"
    rationale: str
    params: dict
    semantic_group: str | None   # 우려1 — 의미 그룹 작업 시
    group_members: list[str]     # 그룹에 속한 컬럼들
    strategy: str | None         # 그룹 정규화 전략
    step_key: str (property)     # order 무관 안정 식별자 (승인 매칭용)

class StepResult:
    order: int
    operation: str
    target_column: str | None
    permission_level: "L1"|"L2"|"L3"
    status: "done"|"awaiting_approval"|"skipped"|"failed"
    semantic_group: str | None
    step_key: str | None
    detail: str
    lineage_id: str | None
    can_rollback: bool
    before_stats: dict
    after_stats: dict
```

#### (마) `AnalysisQuestion` — Page 5 자동 생성

```python
{
  "stage_order": int,
  "context_summary": str,
  "options": [
    {
      "key": str,
      "label": str,
      "function_axis": str,
      "rationale": str,
      "is_primary": bool      # LLM 1순위 추천 옵션 강조 (mockup·체크리스트 6-11 사용)
    }
  ],
  "free_input_allowed": bool
}
```

#### (바) `AggregatedContext` — MCP → EDA·모델링 컨텍스트 전파 (v4-patch 신규)

사용자 비전의 핵심 흐름. Page 4 (MCP 표준화 완료) 후 Context Aggregator (결정론) 가 생성. Page 5/6 LLM 프롬프트의 컨텍스트로 주입.

```python
{
  "session_id": str,
  
  # 앞단 (1-1, 1-2) 입력 그대로 보존
  "pipeline_structure": PipelineStructure,    # 1-1 (공정 흐름 + 모듈 구성)
  "pipeline_constraints": dict,                # 1-2 (사용자 입력 제약)
  
  # 결정론 추출 (Context Aggregator 알고리즘)
  "key_findings": [
    {
      "type": str,              # "class_imbalance"|"missing_values"|"dtype_mixed"|
                                # "sensor_overflow_suspected"|"transformation_applied"|
                                # "validation_concern"|...
      "stage_order": int,
      "module_function": str,
      "column": str | None,
      "severity": str,          # "high"|"medium"|"low"
      "...case_specific_fields..."
    }
  ],
  
  "function_axis_summary": {
    "process": [{...findings...}],
    "quality": [...],
    "maintenance": [...],
    "reference": [...]
  },
  
  "stage_chain": [
    {
      "stage_order": int,
      "node_id": str,
      "main_findings": list[str],
      "downstream_implication": str
    }
  ],

  # DL 신규 — 흐름·계보 관계 컨텍스트 (이종 매핑 부재 + lineage 상보, D-170)
  # vid 흐름 내 위치 + column-group descriptor(column_kind=group)를 EDA로 표면화.
  # 상세 필드 shape는 DL-4(EDA/aggregator 스레딩)에서 확정 — 본 키는 additive, 결정론(LLM 0).
  "analysis_groups": list[dict] | None,

  # 각 에이전트 판단 기록 (사용자 비전 핵심 — Page 4 의 표준화 과정 전체)
  "agent_records": [
    {
      "stage_order": int,
      "module_function": str,
      "dataset_role": str,
      "inspector": {
        "deterministic_flags": list[str],
        "modality_guess": str,
        "concerns": list[str],
        "recommended_next_steps": list[str]
      },
      "planner": {
        "candidate_operations": list[dict],
        "ordered_with_rationale": [
          {
            "operation": str,
            "rationale": str,
            "permission_level": "L1"|"L2"|"L3",
            "step_key": str
          }
        ],
        "llm_summary": str
      },
      "executor": {
        "applied_steps": [
          {
            "step_key": str,
            "operation": str,
            "before_stats": dict,
            "after_stats": dict,
            "lineage_id": str,
            "status": str
          }
        ],
        "rolled_back": list[str]      # rollback 된 step_keys
      },
      "validator": {
        "passed": bool,
        "issues": list[str],
        "next_action": str            # "ready_for_ml"|"await_approval"|...
      }
    }
  ],
  
  # Page 5 사용자 선택 후 추가
  "user_intent": {
    "analysis_purpose": str,        # "anomaly_detection"|"quality_classification"|...
    "function_axis_focus": str,     # "process"|"quality"|"maintenance"|"reference"
    "free_input": str | None
  } | None
}
```

#### Context Aggregator 동작 원칙

- 결정론 알고리즘 (LLM 없음 — 환각 위험 0)
- 입력: PipelineResults (Page 4 출력)
- 출력: AggregatedContext
- 추출 방식: 구조화 필드 → 임계 비교 + 규칙 → key_findings 생성
- 보존 방식: agent_records 는 원본 거의 그대로 누적 (요약 안 함 — LLM 이 직접 활용)

#### (사) `DataLakeEntry` — Data Lake 데이터셋 단위 (v4 신규)

```python
{
  "datalake_id": str,            # 식별자 (예: "kamp_L1_press_forming")
  "source": str,                 # "kamp" | "user_registered"
  "name": str,                   # 사용자 친화 이름
  "modality": str,               # "timeseries" | "inspection-image" | "event-log" | "order"
  "function": str | None,        # DL — process/quality/maintenance/reference (L1~L4 접두사 시드 + lines.yaml 결정론, 사람 교정 가능)
  "site": str | None,            # DL 신규 — 공장/사이트 (vid 내 별도 필터 컬럼, D-162)
  "vid": str | None,             # DL 신규 — 공정 흐름 가상 그룹 ID (라인 단위, D-162)
  "size_bytes": int,
  "encoding": str | None,
  "reusable_flag": bool,         # DL 신규 — 후속 다대다(reference 공유) 무손실 확장 플래그 (D-162)
  "registered_at": str,          # ISO timestamp
  "data_path": str               # 서버 내부 경로 (data/lake/<id>/, 사용자 노출 안 함)
}
```

### 1-3. API 명세 — Phase 1 범위 (22개 / 전체 25개 종합표는 spec-3 Part 9-1)

> 본 표는 Phase 1 (Page 1~3) + Page 4 STEP 1B 핵심까지 수록. 미수록 3개 (`/api/model/{id}/status`, `/api/model/{id}/dashboard`, `/api/model/{id}/cancel`) 는 Page 6 모델링 전용으로 spec-2 Part 7 + spec-3 Part 9-1 참조.



| # | 엔드포인트 | 메서드 | 페이지 | 역할 |
|---|---|---|---|---|
| 1 | `/api/lines` | GET | 1 | Line/Stage/Node/Module 카탈로그 조회 |
| 2 | `/api/models` | GET | 모든 | Ollama 설치 모델 (드롭다운) |
| 3 | `/api/sessions/create` | POST | 1 | 새 세션 생성 (`line_id` 인자) |
| 4 | `/api/sessions/{session_id}` | GET | 모든 | 세션 상태 복원 |
| 5 | `/api/sessions/{session_id}/structure` | PUT | 2 | `PipelineStructure` 저장 |
| 6 | `/api/sessions/{session_id}/full` | PUT | 3 | `PipelineFull` 저장 |
| **7** | **`/api/datalake/list`** | GET | 3 | **Data Lake 데이터셋 목록 (필터 지원)** |
| **8** | **`/api/datalake/register`** | POST | 3 | **신규 데이터셋 등록 (업로드 또는 경로)** |
| **9** | **`/api/datalake/{id}/metadata`** | GET | 3 | **데이터셋 메타 조회** |
| **10** | **`/api/datalake/{id}`** | DELETE | 3 | **데이터셋 삭제 (등록자 권한)** |
| 11 | `/api/execute_pipeline` | POST | 4 | 전체 파이프라인 실행 (resumable orchestrator) |
| 12 | `/api/pipeline/{session_id}/status` | GET | 4 | 진행률 폴링 (SSE 폴백) |
| **12b** | **`/api/pipeline/{session_id}/stream`** | **SSE** | **4** | **1차 메커니즘 — `inspector_done`/`plan_ready`/`approval_required`/`validator_done`/`pipeline_completed` 이벤트** |
| 13 | `/api/pipeline/{session_id}/approve` | POST | 4 | L2/L3 단건 승인 (`{stage_order, module_index, step_key}`) |
| 14 | `/api/pipeline/{session_id}/natural_input` | POST | 4 | **v4 신규 — 자연어 LLM 매핑** |
| **14b** | **`/api/aggregate_context/{session_id}`** | **GET** | **5, 6 진입 시** | **AggregatedContext 생성/조회 (Context Aggregator 결정론)** |
| 15 | `/api/analyze/{session_id}/questions` | GET | 5 | 분석 목적 질문 후보 |
| 16 | `/api/analyze/{session_id}/select` | POST | 5 | 사용자 선택 + 전처리 트리거 |
| 17 | `/api/analyze/{session_id}/results` | GET | 5 | EDA/이상치 결과 |
| 18 | `/api/model/{session_id}/recommend` | GET | 6 | 추천 모델 목록 |
| 19 | `/api/model/{session_id}/train` | POST | 6 | 학습 트리거 |
| 20 | `/api/model/{session_id}/results` | GET | 6 | 학습 결과 + 지표 |

v3의 `/api/upload` 제거. Data Lake 4개 (`list`/`register`/`metadata`/`delete`) 로 대체. 자연어 입력 (`natural_input`) 1개 추가.

기존 1층 엔드포인트 (`/api/inspect`, `/api/plan`, `/api/execute`) 는 그대로 유지 (단일 데이터셋 모드).

### 1-4. 에러 처리 패턴

#### 응답 코드

| 코드 | 의미 | UX |
|---|---|---|
| 200 | 성공 | 진행 |
| 400 | 클라이언트 입력 오류 | 폼 필드별 에러 |
| 404 | 세션/리소스 없음 | "세션 만료" + Page 1 리다이렉트 |
| 422 | 검증 실패 | 폼 필드별 에러 + 수정 유도 |
| 500 | 서버 오류 | "잠시 후 재시도" + 백엔드 로그 ID |
| 503 | LLM/MCP down | 서비스별 상태 + 자동 재시도 (3회) |

#### 에러 응답 형식

```python
{
  "error": {
    "code": str,
    "message": str,
    "details": dict | None
  }
}
```

#### 공통 에러 케이스

| 케이스 | 발생 페이지 | 처리 |
|---|---|---|
| 세션 만료 | 모든 | Page 1 리다이렉트 + 토스트 |
| 네트워크 단절 | 모든 | 재시도 버튼 + offline 표시 |
| LLM down | 4, 5, 6 | "LLM 응답 지연" + Ollama health 체크 |
| MCP 서버 down | 4 | 해당 모달리티 모듈 skip + 알람 |
| Data Lake 데이터셋 없음 | 3 | 카탈로그 새로고침 + 다시 선택 |

### 1-5. 세션 관리

권장: 백엔드 DB 저장 + localStorage 캐시.

| 항목 | 저장 위치 | 이유 |
|---|---|---|
| `session_id` | localStorage | 새 탭/창에서 작업 이어가기 |
| `PipelineStructure` (Page 2) | DB | 단일 진실의 원천 |
| `PipelineFull` (Page 3) | DB | 〃 |
| Data Lake 데이터셋 자체 | 파일 시스템 + Catalog DB | (1-6 참조) |
| `PipelineResults` (Page 4) | DB | 〃 |
| 모델 학습 결과 | DB + 파일 시스템 (parquet/pickle) | 〃 |

#### DB 스키마 (신규 추가 권장)

```sql
CREATE SCHEMA IF NOT EXISTS pipelines;

CREATE TABLE IF NOT EXISTS pipelines.sessions (
    session_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id       TEXT NOT NULL,
    structure     JSONB,
    full_data     JSONB,
    results       JSONB,
    analysis      JSONB,
    model_results JSONB,
    status        TEXT DEFAULT 'created',
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON pipelines.sessions(status);

-- DL 재설계: Data Lake catalog = 정규화 3테이블 (asyncpg). 단일 JSONB metadata 폐기.
-- anti-silent-conversion: 런타임 슬롯/폴더 추론 대신 권위 타입드 인덱스 컬럼 (D-160).
-- 비대칭 수용: catalog=DB / session·lineage=인메모리(Sprint 2 postgres).
-- 멱등·비파괴: CREATE ... IF NOT EXISTS, DROP 금지 (PROTOCOL §3).
CREATE SCHEMA IF NOT EXISTS datalake;

CREATE TABLE IF NOT EXISTS datalake.entries (
    datalake_id    TEXT PRIMARY KEY,
    source         TEXT NOT NULL,         -- "kamp" | "user_registered"
    name           TEXT NOT NULL,
    modality       TEXT,                  -- 4종 (decode router 입력, D-163)
    function       TEXT,                  -- process/quality/maintenance/reference
    site           TEXT,                  -- 공장/사이트 (vid 내 별도 필터, D-162)
    vid            TEXT,                  -- 공정 흐름 가상 그룹 ID (라인 단위, D-162)
    size_bytes     BIGINT,
    encoding       TEXT,
    data_path      TEXT NOT NULL,         -- data/lake/<id>/ (경로 추상화, D-159)
    reusable_flag  BOOLEAN DEFAULT FALSE, -- 후속 다대다 무손실 확장 (D-162)
    registered_at  TIMESTAMPTZ DEFAULT now()
);

-- per-column 메타. column_kind = scalar | group (FFT 광폭/숫자헤더 = group descriptor, D-161)
CREATE TABLE IF NOT EXISTS datalake.columns (
    datalake_id    TEXT NOT NULL REFERENCES datalake.entries(datalake_id),
    name           TEXT NOT NULL,         -- scalar=컬럼명 / group=그룹명(예: "fft_spectrum")
    dtype          TEXT,
    column_kind    TEXT NOT NULL DEFAULT 'scalar',  -- 'scalar' | 'group'
    group_desc     JSONB,                 -- group일 때만: {n_cols, header_kind:"numeric", unit, range}
    PRIMARY KEY (datalake_id, name)
);

-- 제약. 유저 승인으로만 채움 (시스템/modules.yaml/프로파일 절대 안 채움, D-43/D-167)
CREATE TABLE IF NOT EXISTS datalake.constraints (
    datalake_id    TEXT NOT NULL REFERENCES datalake.entries(datalake_id),
    column         TEXT NOT NULL,         -- 키 스코프 = datalake_id + column (D-167)
    constraint     JSONB NOT NULL,        -- 유저 과거 승인값 (prefill 제안 소스, 잠금 아님)
    approved_at    TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (datalake_id, column)
);

CREATE INDEX IF NOT EXISTS idx_datalake_modality ON datalake.entries(modality);
CREATE INDEX IF NOT EXISTS idx_datalake_source   ON datalake.entries(source);
CREATE INDEX IF NOT EXISTS idx_datalake_vid      ON datalake.entries(vid);
CREATE INDEX IF NOT EXISTS idx_datalake_function ON datalake.entries(function);
CREATE INDEX IF NOT EXISTS idx_datalake_site     ON datalake.entries(site);
```

### 1-6. Data Lake 정책 (DL 재설계 — 전면 재작성)

#### 통합 진입점 원칙 (DB catalog 단일)

데이터 진입·셀렉·엔진 연결은 **`datalake_id` 한 가지**만 안다. 물리 경로는 `data_path` 컬럼이 추상화하므로 셀렉·엔진은 경로를 모른다. 물리 경로는 선택 항목이 아니라 `data/lake/<datalake_id>/`로 **귀결**(KAMP·신규 대등 — 핵심 메시지 정합, D-159).

```
Page 3 데이터 선택 → catalog에서 1개 선택(datalake_id) → datalake.get(id) → {data_path, modality}
```

#### 디렉터리 구조 (flat)

```
data/lake/
  ├── <datalake_id>/          # KAMP·사용자 등록 동일 패턴
  │   └── data.csv (or folder/zip)
  └── ...
```
`data/lake/`는 외부폴더(서버) → gitignore 무관. 마이그레이션할 기존 데이터 없음(합성데이터 미생성, 클린 출발).

#### 적재 (ingest) — 외부 도구

`tools/datalake_ingest.py`: `~/FINAL/1_data` 스캔 → 메타 자동생성 → `data/lake/<id>/` 복사 + catalog INSERT. (DL-2에서 구현·KAMP 5.1G 적재.)

메타 출처(결정론, 사람 교정 가능):
- `modality` = 파일포맷/폴더
- `function` = L1~L4 접두사 시드 + lines.yaml
- `site`
- `vid` = 라인 (D-162)

KAMP 5.1G = 3 module(**metal / forming_joining / polymer** = module_1/2/3). 대부분 일반 CSV+헤더(ASCII). `order` modality 0건(데모 제외 인지). 멱등 재적재(upsert) + dry-run 먼저.

> **★ FFT 광폭/숫자헤더 (L3 vibration):** 컬럼=주파수값(숫자헤더, 수천 개) → per-column 부적합. 적재도구·catalog는 **컬럼-그룹 descriptor**로 등록(`column_kind=group`, 예: `fft_spectrum: N개 numeric-header, 단위·범위`). 제약도 per-column이 아닌 집계/대역형 (D-161, R0 사용자 확인 완료).

#### 결정론 modality 라우터

`datalake.get(datalake_id) → {data_path, modality}` 가 데이터→엔진 경계의 단일 해석점. 기존 `_resolve`(timeseries/order) + 이미지 경로 + event-log 경로 **3곳을 통합**. LLM 0 (D-163). 라우터 뒤 `pd.read_csv(path) → Inspector~학습`은 변경 0(additive seam, D-164).

#### 사용자 신규 등록

등록 API 표면(`/api/datalake/register` Mode A 업로드 / Mode B 서버경로)은 변경 없음(R1 범위 외). 등록 데이터도 `data/lake/<id>/`로 귀결, 같은 catalog INSERT 경로. KAMP는 적재 도구로 사전 등록되어 사용자는 카탈로그에서 선택만.

> 자료구조: `DataLakeEntry`=Part 1-2(사), per-column=`datalake.columns`, 제약=`datalake.constraints` (Part 1-5).

### 1-7. 사용자 승인 UI 정책 (v4 갱신 — 카드 + 자연어 2단계 환각 방어)

본 명세는 백엔드 토큰 게이트 동작을 사실로 보고, 프론트엔드 승인 UI 의 구체 형태는 다음 두 가지로 구성:

#### 방식 A — 카드 형식 (결정론 미리보기)

LLM 환각 위험 0. 기본 UX.

```
┌─────────────────────────────────────────────────┐
│ Stage 0 / 사출 성형 / 작업: clean_masking       │
│ 권한: L2 (사용자 승인 필요)                      │
│                                                  │
│ 통계 미리보기 (결정론 계산):                     │
│   현재: object dtype, 3000행 중 240개 마스킹     │
│   변환 후: float64, NaN 8% (240개)              │
│                                                  │
│ 작업 방향:                                       │
│   "*", "**", "***" → NaN 변환 후 float 수치화    │
│                                                  │
│ [거부]                              [승인]       │
└─────────────────────────────────────────────────┘
```

여러 후보 작업이 있으면 카드 N개 표시 (각 카드별로 승인/거부).

#### 방식 B — 자연어 LLM 소통 (선택적, 2단계 환각 방어)

카드만으로 의사 표현 부족 시 사용. LLM 자유도 출구만 제한으로 환각 방어.

```
┌─────────────────────────────────────────────────┐
│ ─── 자연어로 수정 ───                           │
│ ┌────────────────────────────────────────────┐  │
│ │ "이 컬럼은 그대로 두고 다음 단계만 진행해줘"│  │
│ │ [LLM에게 전달]                             │  │
│ └────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
        ↓
[LLM이 OPERATION_PERMISSION 안의 기존 후보 중 매핑]
        ↓
┌─────────────────────────────────────────────────┐
│ LLM 해석:                                        │
│  "CNC_ServoLoad_1 컬럼에 'drop_column' 작업을   │
│   적용하시겠어요?"                              │
│ [예]  [아니오, 다시 입력]                       │
└─────────────────────────────────────────────────┘
        ↓ "예" 클릭
[결정론 실행 + lineage 기록]
```

**환각 방어 메커니즘 3계층**:
1. LLM 출력 = 기존 `OPERATION_PERMISSION` 작업 중 매핑만 (새 작업 생성 금지)
2. LLM 출력 → 사용자 재확인 강제 (2단계 게이트)
3. 권한 등급 = guardrails 단일 소스 (LLM 변경 불가)

#### `/api/pipeline/{session_id}/natural_input` 요청·응답 (v4 신규)

요청:
```python
{
  "stage_order": int,
  "module_index": int,
  "natural_text": str,
  "context": dict             # 현재 작업 컨텍스트 (선택)
}
```

응답:
```python
{
  "mapped_operation": str,           # OPERATION_PERMISSION의 키
  "target_column": str | None,
  "permission_level": str,           # 매핑된 작업의 권한 (LLM 못 바꿈)
  "confidence": float,               # LLM 매핑 신뢰도 0~1
  "explanation_kr": str,             # 사용자 친화 설명
  "requires_confirmation": bool      # True = 사용자 재확인 강제
}
```

confidence 가 낮으면 (예: <0.7) "다시 입력" 권유 표시.

### 1-8. LLM 가치 활용 로드맵 (v4 신규)

본 시스템에서 LLM은 결정론 시스템의 안전망 안에서 동작하지만, 가치가 빛나는 영역은 점진 확장됨. STEP 별 도입 시점:

#### LLM 가치 확장 5영역

| # | 영역 | 1층 (현재) | STEP 1B | STEP 2 | STEP 3 |
|---|---|---|---|---|---|
| ① | **Stage 간 컨텍스트 누적 추론** ("Stage A PdM 이상 → Stage B quality 영향") | 없음 | 도입 (stage_context 누적) | 확장 | 〃 |
| ② | **도메인 추론** ("이 페트병 사출 사이클타임은 제약 위배") | 없음 | 도입 (constraints + LLM judge) | 확장 | 〃 |
| ③ | **분석 목적 자동 질문** (Page 5) | 없음 | 도입 (Module 조합 기반) | 확장 | 〃 |
| ④ | **EDA 자연어 요약** | 없음 | 부분 도입 | 완성 | 〃 |
| ⑤ | **자연어 ↔ 작업 매핑** (Page 4 방식 B) | 없음 | 부분 도입 (단순 매핑) | 완성 (옵션 카드 연동) | 〃 |

#### 각 영역의 환각 방어 메커니즘

| 영역 | 환각 방어 |
|---|---|
| ① | stage_context 는 요약된 사실만 누적 (raw 데이터 안 들어감). Validator 가 누락된 lineage 검출 |
| ② | constraints = 사용자 입력 = 진실. LLM은 비교만 ("위배 여부") |
| ③ | 질문 후보는 Module Catalog 기반 결정론. LLM은 1~2개 추천 + 사용자 최종 선택 |
| ④ | EDA 수치는 결정론 계산. LLM은 자연어 표현만 |
| ⑤ | LLM 출력 = `OPERATION_PERMISSION` 후보 중 매핑만 + 사용자 재확인 강제 (Part 1-7) |

#### 헌법 정합 확인

decisions.md 의 D-13 (LLM 제안, 규칙 결정) + D-15 (Executor 결정론) 와 정합:
- LLM = 판단/매핑/요약/추천 (5영역 모두)
- 규칙/가드레일 = 검증/필터/실행 (변경 없음)
- Executor = 결정론 변환 (변경 없음)

LLM 가치 확장은 새 권한 부여가 아니라 기존 안전망 안에서의 활용 범위 확대.

#### 모델별 적용 권장

| 모델 | 적용 영역 | 이유 |
|---|---|---|
| `gemma4:e4b` (스캐폴딩) | ①②③의 단순 케이스 | 빠른 응답, 안정 동작 |
| `gemma4:26b` (메인) | ①②③④⑤의 복잡 케이스 | 정확도 우선 |
| 모델 선택 UI (Page 4 우상단) | 사용자가 즉석 비교 | 같은 데이터를 모델별 비교 시연 |

---

## Part 2. 페이지 1: Line 선택

### 2-1. URL / 화면 mockup

```
URL: /
페이지 제목: "공정 라인 선택"

┌────────────────────────────────────────────────────┐
│ manufacturing-mcp                    [모델: e4b ▼]│
├────────────────────────────────────────────────────┤
│                                                    │
│   분석할 공정 라인을 선택하세요                    │
│                                                    │
│   ○ Line 1: 금속 가공·검사 라인                    │
│       1차성형 / CNC 절삭 / MCT 가공 등 6 공정      │
│                                                    │
│   ○ Line 2: 성형·접합·표면처리·회전기 라인         │
│       프레스 / 용접 / 표면처리 등 5 공정           │
│                                                    │
│   ○ Line 3: 폴리머 성형·전자 검사·진동 신호 라인   │
│       사출 / ICT 검사 / 진동 시뮬 등 7 공정        │
│                                                    │
│                                  [다음 →]          │
└────────────────────────────────────────────────────┘
```

### 2-2. 사용자 액션

1. 페이지 진입 → `GET /api/lines` 자동 호출 → 카탈로그 로드 후 라디오 버튼 3개 렌더링
2. 사용자가 라디오 1개 선택
3. "다음" 버튼 활성화
4. "다음" 클릭 → 세션 생성 + Page 2 이동

### 2-3. API 호출

#### `GET /api/lines`
응답: Part 1-2 (가) 형식.

#### `POST /api/sessions/create`
요청: `{ "line_id": str }`
응답: `{ "session_id": str, "line_id": str, "status": "created" }`

### 2-4. 응답 처리 + 다음 페이지 이동

```javascript
async function handleNext() {
  const response = await fetch("/api/sessions/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ line_id: selectedLineId })
  });
  if (!response.ok) {
    showError(await response.json());
    return;
  }
  const { session_id } = await response.json();
  localStorage.setItem("mfg_session_id", session_id);
  navigate(`/pipeline/build?session=${session_id}`);
}
```

### 2-5. 에러 케이스

| 케이스 | 처리 |
|---|---|
| `/api/lines` 응답 없음 | "카탈로그 로드 실패" + 재시도 |
| Line 미선택 + "다음" | 버튼 비활성 |
| `/api/sessions/create` 실패 | 토스트 + 재시도 |

### 2-6. 검증 체크리스트

- [ ] `GET /api/lines` 200 + 3 Line 응답
- [ ] 라디오 버튼 3개 렌더링
- [ ] 미선택 상태 "다음" 비활성
- [ ] 선택 후 "다음" 활성
- [ ] `POST /api/sessions/create` 200 + UUID 반환
- [ ] localStorage 에 `mfg_session_id` 저장
- [ ] Page 2 리다이렉트
- [ ] 모델 드롭다운 정상 표시

---

## Part 3. 페이지 2 (1-1): Pipeline 구성

### 3-1. URL / 화면 mockup

```
URL: /pipeline/build?session=<uuid>
페이지 제목: "공정 흐름 구성"

┌─────────────────────────────────────────────────────────────────────────┐
│ Line 1: 금속 가공·검사 라인   세션: <uuid 앞 8자>     [모델: e4b ▼]    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ 모듈 카탈로그 (좌) ─┐  ┌─ 공정 흐름 (우, 시간순) ────────────────┐  │
│  │                       │  │                                          │  │
│  │ 1차 성형              │  │  Stage 0: 1차 성형                      │  │
│  │   [maintenance]       │  │  ┌───────────────────────────────┐      │  │
│  │   L3_mold_condition   │  │  │ [maintenance] L3_mold_condition│     │  │
│  │   ─────────────────   │  │  │ [maintenance] L3_mold_anomaly │      │  │
│  │   [maintenance]       │  │  └───────────────────────────────┘      │  │
│  │   L3_mold_anomaly     │  │           ↓                              │  │
│  │                       │  │  Stage 1: CNC 절삭                       │  │
│  │ CNC 절삭              │  │  ┌───────────────────────────────┐      │  │
│  │   [process] ...       │  │  │ [process] L1_cnc_lathe_quality│      │  │
│  │                       │  │  └───────────────────────────────┘      │  │
│  │ MCT 가공              │  │           ↓                              │  │
│  │   ...                 │  │  Stage 2: MCT 가공                       │  │
│  │                       │  │  ┌───────────────────────────────┐      │  │
│  │ (더 보기 ▼)            │  │  │ (드래그해서 모듈 추가)         │      │  │
│  └───────────────────────┘  │  └───────────────────────────────┘      │  │
│                              │           ↓                              │  │
│                              │  Stage 3~5: ...                          │  │
│                              └──────────────────────────────────────────┘  │
│                                                                         │
│                                                  [← 이전]   [다음 →]    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3-2. 좌측 카탈로그 패널 (DL 재설계)

좌측은 데이터셋이 아니라 **4 function 모듈 팔레트**(P/Q/M/R):
- process(파랑) / quality(초록) / maintenance(주황) / reference(회색)
- 각 카드 `draggable={true}`. 데이터 바인딩은 Page 3에서 수행(여기선 function 슬롯만 배치).

### 3-3. 우측 Stage 박스 + 흐름 모델 (DL 재설계)

stage 구성 = **P 체인(순서) + 각 P노드의 M/Q 묶음**.
- P(process) 모듈: `chain_order`로 흐름 순서 형성 (P1 — P2 — P3 …).
- M/Q 모듈: 특정 P에 `attached_to`로 부착(묶음 단위).
- R(reference): 흐름 비종속(부착 없음).
- 기준 스케치: `P1 — P2{+M1} — P3{+Q1} — P4{+Q2,M2,M3}`.

**같은 function 복수 허용**(D-165) — 기존 `(function, dataset_role)` 중복 차단 규칙 폐기.

**이중 처리:** MCP 표준화 = 파일을 개별 주체로 / EDA = 흐름 내 위치 컨텍스트로(vid·stage_chain, Part 1-2 바).

### 3-4. 드래그앤드롭 동작 명세 (DL 재설계)

HTML5 native DnD. 드롭 시 module 객체에 `{function, chain_order|None, attached_to|None}` 기록.
- P 모듈 드롭 → 해당 stage P 체인 끝에 `chain_order` 부여.
- M/Q 모듈 드롭 → 부착할 P 선택(UI) → `attached_to` 설정.
- `max_modules` 초과 시 드롭 거부 + 토스트.
- **중복 차단 폐기:** 같은 function 복수 허용(D-165). 부착 무결성만 검증(M/Q는 같은 stage 내 존재하는 P에만 부착).
- 제거: 카드 [×] / Delete 키. P 제거 시 그 P에 부착된 M/Q의 `attached_to` 정리.

> 전환기: 신규 Page 2 경로는 feature-gate로 구 경로와 병존, DL-5 green 후 구 경로 제거(PROTOCOL §3).

### 3-5. 상태 천이

```
초기 진입:
  GET /api/sessions/{id} → structure 있으면 복원, 없으면 빈 stages
        ↓
사용자 드래그앤드롭:
  setStages(...)
        ↓
"다음" 클릭:
  PUT /api/sessions/{id}/structure → Page 3 이동
```

### 3-6. 검증 규칙

| 규칙 | 강제 시점 | UX |
|---|---|---|
| 빈 Stage 허용 (list에 등장 안 함) | 저장 시 자동 | OK |
| 최소 1+ Stage 에 1+ 모듈 필요 | "다음" 클릭 시 | "최소 1개 모듈" 토스트 |
| `max_modules` 초과 금지 | 드롭 시 | 거부 + 토스트 |
| 같은 Stage 중복 모듈 금지 | 드롭 시 | 거부 + 토스트 |

### 3-7. API 호출

#### `PUT /api/sessions/{session_id}/structure`
요청: Part 1-2 (나) 형식.
응답: `{ "session_id": str, "status": "data" }`

### 3-8. 다음 페이지 이동

```javascript
async function handleNext() {
  if (!validateAtLeastOneModule(stages)) {
    toast("최소 1개 모듈을 추가해주세요");
    return;
  }
  const response = await fetch(`/api/sessions/${session_id}/structure`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ line_id, stages })
  });
  if (!response.ok) {
    showError(await response.json());
    return;
  }
  navigate(`/pipeline/data?session=${session_id}`);
}
```

### 3-9. 에러 케이스

| 케이스 | 처리 |
|---|---|
| 세션 없음 | Page 1 리다이렉트 |
| 드롭 검증 실패 | 토스트 |
| `PUT structure` 실패 | 토스트 + 재시도 |
| 0 모듈 "다음" | 차단 |

### 3-10. 검증 체크리스트

- [ ] 카탈로그 렌더링 (좌측)
- [ ] `max_stages` 만큼 빈 박스 (우측)
- [ ] 카드 드래그 동작
- [ ] 박스 드롭 → 모듈 추가
- [ ] `max_modules` 초과 거부
- [ ] 중복 모듈 거부
- [ ] 다른 Node 모듈 거부
- [ ] [×] 제거 동작
- [ ] 새로고침 복원
- [ ] "다음" → Page 3 이동
- [ ] 0 모듈 차단
- [ ] 화살표 표시
- [ ] function 색상 구분

---

## Part 4. 페이지 3 (1-2): 데이터 + 제약 입력 (v4 전면 재작성)

### 4-1. URL / 화면 mockup

```
URL: /pipeline/data?session=<uuid>
페이지 제목: "데이터 선택 + 제약 입력"

┌─────────────────────────────────────────────────────────────────────────┐
│ Line 1 / 6개 모듈                                       [모델: e4b ▼]    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Stage 0: 1차 성형                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ [maintenance] L3_mold_condition                          [▼ 펼침]│    │
│  │   ┌─ 데이터 선택 ──────────────────────────────────────┐         │    │
│  │   │ ▼ Data Lake 에서 선택                             │         │    │
│  │   │   ⊙ KAMP / L3_mold_condition (0.4 MB)            │         │    │
│  │   │   ○ KAMP / L3_mold_anomaly (325 MB)              │         │    │
│  │   │   ─── 또는 ───                                    │         │    │
│  │   │   ○ [+ 새 데이터셋 등록]                          │         │    │
│  │   └────────────────────────────────────────────────────┘         │    │
│  │   ┌─ 제약 입력 ────────────────────────────────────────┐         │    │
│  │   │ cycle_time_sec (초) [범위]    [__15__] ~ [__180__] │         │    │
│  │   │ mold_temp_c (°C)    [범위]    [__20__] ~ [__400__] │         │    │
│  │   │ max_null_ratio (%)  [비율]    [__10__]             │         │    │
│  │   │ [+ 제약 추가]      [고급: YAML 편집]               │         │    │
│  │   │                                                      │         │    │
│  │   │ ⚠️ maintenance 모듈은 constraint_keys 입력 필요 (LLM 알람)│       │    │
│  │   └────────────────────────────────────────────────────┘         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ [maintenance] L3_mold_anomaly                          [▶ 접힘]│    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Stage 1: CNC 절삭                                                      │
│  ...                                                                    │
│                                                                         │
│                                                  [← 이전]   [다음 →]    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4-2. 모듈 카드 펼치기 UI

- 모든 모듈 카드는 기본 접힘 상태
- 카드 우측 [▼] 클릭 시 펼침 (데이터 선택 + 제약 입력 노출)
- 한 번에 여러 카드 펼침 가능
- 펼친 카드 안에 ([데이터 선택] + [제약 입력]) 영역

### 4-3. 데이터 선택 영역 (DL 재설계 — 전면 재작성)

#### vid × function × site 메타필터 → 카드 UI

Page 3 진입 시 `vid`(Page 1·2에서 결정) 기준으로 catalog를 거른 뒤, `function`·`site` 메타필터로 좁힌 **카드 목록**에서 선택:
```
GET /api/datalake/list?vid=<vid>&function=<module.function>&site=<optional>
```
응답 `entries`(Part 1-2 사)를 카드로 표시(이름/modality/크기). 제한된 목록에서 1개 선택 → `datalake_id` 바인딩.

#### 신규 등록 모달

등록 API 표면 변경 없음(Mode A 업로드 / Mode B 서버경로, Part 1-6). 등록 후 catalog 갱신 + 자동 선택.

#### 제약 — 핵심 가드 (D-167)

- **입력 = 무조건 유저.** 시스템은 범용 범위조차 제안 0 (D-43 강화). 근거: SI는 고객사 머신별 스펙·limit을 정확히 모름 → 선택권을 유저에게.
- **prefill = `datalake.constraints`(유저 과거 승인값) 제안일 뿐** — 절대 잠금/자동적용 아님. 흐름/공장/데이터셋이 같아도 "같은 선택 = 같은 제약" 강제 금지. 매칭돼도 **항상 재승인 게이트** 통과해야 적용.
- 키 스코프 = `datalake_id + column`.
- **머지 우선순위 = 세션 오버라이드 > 카탈로그 prefill(재승인) > 빈칸(유저 입력).**
- 변경 시 = "이번만" vs "메모리 업데이트(영속)" 질문.
- **불변식:** catalog 제약 = 기억 보조(제안)이지 권위(디폴트)가 아니다. 캐시값 자동 고정 = 사실상 시스템 디폴트 = D-43 위반.

#### 검증·알람

- 제약 검증 = `validator`가 **원본 backup parquet 직접 대조**(정규화 출력 아님 — D-67 계승, 변형 0). MCP `/check_constraints`는 죽은 코드(미호출).
- 알람 = validator 단계의 **"제약 공백/상태 알람"**(데이터-미업로드 알람과 대칭) 신설(D-168). 승인 게이트 = Page 3 입력 시점 / 상태 알람 = validator 시점.

### 4-4. 제약 입력 폼 (v4 전면 재작성)

#### `constraint_keys` 기반 폼 렌더링

LineCatalog의 `constraint_keys` (Part 1-2 (가)) 를 보고 폼 자동 생성.

```javascript
function renderConstraintForm(constraint_keys, currentConstraints, onChange) {
  return constraint_keys.map(spec => {
    const value = currentConstraints[spec.key];
    switch (spec.type) {
      case "range":
        return <RangeInput
          label={spec.label_kr}
          unit={spec.unit}
          min={value?.[0]}
          max={value?.[1]}
          onChange={(min, max) => onChange(spec.key, [min, max])}
        />;
      case "single_value":
        return <NumberInput
          label={spec.label_kr}
          unit={spec.unit}
          value={value}
          onChange={v => onChange(spec.key, v)}
        />;
      case "ratio":
        return <RatioInput ... />;
      case "list":
        return <ListInput ... />;
      case "text":
        return <TextInput ... />;
    }
  });
}
```

#### 필수성 표시

`constraint_keys[].required_for` 가 현재 모듈의 `function` 을 포함하면 폼 옆에 별표 표시.

```
cycle_time_sec (초) *  [범위]   [_______] ~ [_______]
   ↑
   maintenance 모듈에서 필수 (별표)
```

#### 사용자 입력 디폴트 정책

**디폴트 값 없음**. 사용자가 처음 들어가면 빈 폼. `datalake.constraints` prefill이 있으면 **제안으로만** 표시(잠금 아님, 항상 재승인 — §4-3 제약 가드, D-167).

이유: 페트병/볼펜대 등 제품마다 typical_ranges 다름. 사전 디폴트는 오히려 혼동. 사용자가 자기 데이터에 맞게 입력. 캐시 제안을 자동 고정하면 사실상 시스템 디폴트가 되어 D-43 위반.

#### 제약 추가/삭제

- `constraint_keys` 외 제약은 [+ 제약 추가] 로 사용자 정의 추가
- 각 필드 [×] 로 삭제

### 4-5. LLM judge 알람 정책 (v4 신규, 헌법 정합)

#### 알람 발생 시점

사용자가 "다음 →" 클릭 시 LLM judge 가 미입력 제약 검사:

```python
# backend의 의사 코드
async def check_constraints_necessity(pipeline_full):
    alarms = []
    for stage in pipeline_full.stages:
        for module in stage.modules:
            missing_required = []
            # 1. 결정론 규칙: required_for 명시된 제약 미입력
            for spec in constraint_keys_of(stage.node_id):
                if module.function in spec.required_for:
                    if spec.key not in module.constraints:
                        missing_required.append(spec)
            
            if missing_required:
                # 2. LLM judge: 정말 필요한지 데이터 특성 보고 판단
                judgement = await llm.generate(
                    system="제조 데이터 분석가. 미입력 제약의 필요성 판단.",
                    prompt=f"Node: {stage.node_id}, Function: {module.function}, "
                           f"Missing: {missing_required}. 필수입니까?",
                    fmt_json=True
                )
                # judgement = { "alarm": bool, "reason": str }
                if judgement["alarm"]:
                    alarms.append({
                        "stage_order": stage.stage_order,
                        "module_index": ...,
                        "missing": missing_required,
                        "reason": judgement["reason"]
                    })
    return alarms
```

#### UX

알람이 있으면 "다음 →" 전 모달:

```
┌─────────────────────────────────────────────────┐
│ 필수 제약 미입력 (LLM 판단)                      │
│                                                  │
│ Stage 0 / 1차 성형 / [maintenance] L3_mold_anomaly│
│   누락: cycle_time_sec, mold_temp_c              │
│   이유: 예지보전 모듈은 이상 임계값이 필요합니다 │
│                                                  │
│ [돌아가서 입력]            [무시하고 진행]       │
└─────────────────────────────────────────────────┘
```

"무시하고 진행" 시: Page 4 표준화 진행, 단 Validator가 낮은 신뢰도 표시.

#### 헌법 정합

- LLM = 판단 ("필요한가?")
- 사용자 = 최종 결정 (입력하거나 무시)
- MCP/Executor = 결정론 표준화 (사용자 제약 사용 또는 데이터 통계 fallback)

decisions.md D-13/D-15 정신 완전 일치.

### 4-6. 고급 사용자 YAML 편집

[고급: YAML 편집] 버튼 → 모달 → YAML 직접 편집:

```yaml
cycle_time_sec: [15, 180]
mold_temp_c: [20, 400]
max_null_ratio: 0.1
required_columns:
  - INJ_ID
  - weight
```

저장 시 YAML 파싱 → constraints dict. 파싱 실패 시 에러.

### 4-7. 검증 규칙

| 규칙 | 강제 시점 | UX |
|---|---|---|
| 데이터 미선택 모듈 허용 | 저장 시 통과 | 빈 표시 (LLM judge 별도) |
| `required_for` 제약 미입력 | "다음" 클릭 시 LLM judge | 알람 모달 |
| 제약 값 타입 검증 | 폼 입력 시 | 필드별 에러 |
| YAML 파싱 실패 | YAML 저장 시 | 모달 안 에러 |
| 신규 등록 시 100MB 초과 (Mode A) | 업로드 시 | 토스트 + Mode B 권유 |

### 4-8. API 호출

#### `PUT /api/sessions/{session_id}/full`
요청: Part 1-2 (다) 형식.
응답: `{ "session_id": str, "status": "data", "alarms": [...] | None }`

> 응답 status는 `"data"` 유지 (부록 C-1 천이도와 정합). `"running"` 으로 전환되는 시점은 사용자가 별도 `POST /api/execute_pipeline` 호출 후. PUT /full 자체는 저장 + LLM judge 알람 생성만 수행. LLM judge는 동기 호출이라 응답 지연 ~500ms (gemma4 모델 latency 의존 — Sub-batch B 우려 노트 참조). 알람 있으면 응답에 alarms 포함. 클라이언트가 모달 표시.

#### `POST /api/execute_pipeline`
요청: `{ "session_id": str, "model": str (옵션) }`
응답: `{ "status": "started", "estimated_seconds": int }`

### 4-9. 다음 페이지 이동

```javascript
async function handleNext() {
  // 1. PipelineFull 저장 + 알람 체크
  const saveResponse = await fetch(`/api/sessions/${session_id}/full`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pipelineFull)  // PipelineFull 전체 (line_id + stages 포함)
  });
  if (!saveResponse.ok) {
    showError(await saveResponse.json());
    return;
  }
  const result = await saveResponse.json();
  
  // 2. 알람 처리
  if (result.alarms && result.alarms.length > 0) {
    const decision = await showAlarmModal(result.alarms);
    if (decision === "go_back") return;  // 사용자가 돌아가서 입력
  }
  
  // 3. Pipeline 실행 트리거
  const runResponse = await fetch("/api/execute_pipeline", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, model: selectedModel })
  });
  if (!runResponse.ok) {
    showError(await runResponse.json());
    return;
  }
  
  // 4. Page 4 이동
  navigate(`/pipeline/run?session=${session_id}`);
}
```

### 4-10. 에러 케이스

| 케이스 | 처리 |
|---|---|
| 세션 없음 | Page 1 리다이렉트 |
| Data Lake 조회 실패 | "카탈로그 로드 실패" + 재시도 |
| 신규 등록 실패 (파일 크기 초과) | 토스트 + Mode B 권유 |
| 신규 등록 실패 (서버 경로 없음) | 토스트 + 경로 재입력 |
| LLM judge 실패 (Ollama down) | 알람 skip + Validator 가 책임 (낮은 신뢰도) |
| `PUT full` 실패 | 토스트 + 재시도 (작업 보존) |

### 4-11. 검증 체크리스트

- [ ] Page 2 모듈들 Stage 순서대로 표시
- [ ] 모듈 카드 펼침/접힘
- [ ] Data Lake 드롭다운 로드 (`GET /api/datalake/list`)
- [ ] 데이터셋 선택 → 메타 표시 (모달리티/인코딩)
- [ ] 신규 등록 모달 동작
- [ ] Mode A (파일 업로드) 동작
- [ ] Mode B (서버 경로) 동작
- [ ] 등록 후 카탈로그 자동 갱신
- [ ] `constraint_keys` 기반 폼 자동 생성
- [ ] `required_for` 모듈에 별표 표시
- [ ] 디폴트 값 없음 (빈 폼)
- [ ] 제약 추가/삭제 동작
- [ ] YAML 편집 모달
- [ ] "다음" 클릭 시 LLM judge 호출
- [ ] 알람 모달 표시
- [ ] "무시하고 진행" 시 Page 4 이동 + Validator 신뢰도 낮춤
- [ ] 새로고침 후 상태 복원

---

## Part 1-9. 검증·피드백·모니터링 항목 (v4 신규 — 사전 인지)

본 섹션은 명세서의 **결정 사항이 아니라 검증·피드백·모니터링 대상**. 팀원이 사전에 인지하고 작업 중·작업 후 확인할 항목들.

### 1-9-1. KAMP 적재 (DL 재설계 — 물리경로 A/B 폐기)

v4의 "시나리오 A(데이터 이전) vs B(메타만)" 물리경로 선택지는 **폐기**(D-159). `data_path` 컬럼이 경로를 추상화하므로 물리 경로는 결정 항목이 아니라 `data/lake/<id>/`로 귀결한다. 합성데이터 미생성·실 KAMP는 외부폴더라 마이그레이션할 기존 데이터가 없다(클린 출발).

적재는 `tools/datalake_ingest.py`(외부 도구)가 `~/FINAL/1_data` 스캔 → 메타 자동생성 → `data/lake/<id>/` 복사 + catalog INSERT 단일 경로로 처리(Part 1-6). 멱등 재적재(upsert) + dry-run 먼저. `DATA_ROOT` 환경변수 분기 논의는 무효(단일 진입점).

### 1-9-2. constraint_keys 사후 검증 (실데이터 피드백)

`LineCatalog.constraint_keys` 의 5필드 (`{key, type, unit, label_kr, required_for}`) 는 v4 잠정안. 실데이터로 검증 후 갱신.

#### 검증 시점

```
[STEP 1B 구현]
  ↓
[KAMP 5 데이터셋 시험]
  press_imbalance / cnc_lathe_quality / mold_anomaly / wafer_defect / order_cp949
  ↓
[constraint_keys v0.1 적용 후 피드백]
  - 누락 필드 식별
  - type 부적합 사례 (range vs single_value 적정?)
  - required_for 매핑 정확도
  - label_kr 자연스러움
  ↓
[constraint_keys v0.2 갱신]
  ↓
[STEP 1B 완료 + v4 명세 patch]
```

#### 검증 체크리스트
- [ ] 18개 Node 모두 폼 자동 생성 동작
- [ ] 각 폼 필드 type (range/single_value/ratio/list/text) 적정
- [ ] required_for 가 maintenance 외 케이스에도 정합
- [ ] label_kr 한국어 표시 자연스러움
- [ ] 누락 필드 없나 (특히 사출/CNC/PdM 의 도메인 특화 제약)

### 1-9-3. LLM 개입 수준 모니터링

본 시스템에서 LLM은 결정론 가드레일 안에서만 동작 (헌법 D-13/D-15). STEP 1B 도입 LLM 확장 영역의 환각 모니터링 필수.

#### 모니터링 지표 7개

| LLM 호출 지점 | 환각 위험 | 모니터링 지표 | 임계치 |
|---|---|---|---|
| Inspector `modality_guess` | 낮음 | 4 모달리티 외 응답 비율 | < 5% |
| Inspector `concerns` | 낮음 | 응답 길이 (너무 길면 의심) | < 200자 |
| Planner `ordered` (순서) | 낮음 | 후보 외 작업 등장 비율 | 0% (가드레일 차단) |
| LLM judge `constraint_keys 입력 완결성` | 중간 | 사용자 입력 vs LLM 판단 일치율 | > 70% |
| LLM judge `데이터 미업로드 필수성` | 중간 | 〃 | > 70% |
| Page 4 자연어 매핑 (`natural_input`) | 중상 | 사용자 재확인 거부 비율 | < 30% (높으면 매핑 문제) |
| Page 5 분석 목적 질문 추천 | 중간 | 추천 채택률 (vs 자유 입력) | > 50% |

#### 측정 방법
- 모든 LLM 호출 → `agent_logs.decisions` 테이블에 input/output 기록 (이미 DB 스키마 있음)
- 주간 집계 → 임계 위반 알람

#### 임계 위반 시 행동
- LLM 활용 영역 축소 (해당 호출 지점 제거 또는 가드레일 강화)
- 모델 변경 (e4b → 26b)
- 프롬프트 수정 + 재테스트

### 1-9-4. step_key 매칭 검증 (코드 확인 신규 발견)

#### order vs step_key 차이

코드 확인 결과 `PlanStep` 에는 `order` (실행 순서) 와 `step_key` (안정 식별자) 두 가지가 있음.

| 항목 | order | step_key |
|---|---|---|
| 값 | 1, 2, 3... | `"clean_masking:CNC_ServoLoad_1"` 같은 문자열 |
| 안정성 | LLM 이 매번 다르게 배열 → 불안정 | operation + target 기반 → 안정 |
| 용도 | UI 표시 순서 | 승인 매칭, lineage 식별 |

#### 명세 정합 확인 필요
- [ ] 클라이언트 승인 요청에 `step_key` 사용 (`approved_step_keys: list[str]`)
- [ ] Executor 가 `step.step_key` 와 매칭 (코드는 이미 그렇게 구현됨 확인 필요)
- [ ] Page 4 UI 가 step_key 를 식별자로 사용 (order는 표시만)

### 1-9-5. MCP 7도구 HTTP 메서드 (코드 확인 신규)

| 도구 | HTTP 메서드 | 비고 |
|---|---|---|
| `/health` | GET | 표준 |
| `/tools` | GET | 도구 목록 |
| `/datasets` | GET | 모달리티 데이터셋 목록 |
| `/list_columns` | GET | dataset_id 쿼리 파라미터 |
| `/get_schema` | GET | 〃 |
| `/sample` | GET | dataset_id + n 쿼리 |
| `/detect_encoding` | GET | dataset_id 쿼리 |
| **`/check_constraints`** | **POST** | body: `{dataset_id, constraints}` |
| **`/apply_preprocessing`** | **POST** | body: `{dataset_id, operations, permission_level}` |
| `/lineage` | GET | dataset_id 쿼리 |

#### 명세 정합 확인 필요
- [ ] Backend 가 POST 도구 호출 시 body 정확히 전달
- [ ] Page 3 의 constraints 폼 입력 → check_constraints body 매핑 정확

### 1-9-6. OPERATION_PERMISSION 실제 매핑 (코드 확인 신규)

권한 등급별 작업 목록 (`harness/guardrails.py` 실제):

```python
L1 (자동, 즉시):
  - detect_encoding   # 인코딩 정규화
  - reparse_header    # 헤더 재파싱
  - compute_stats     # 기초 통계

L2 (제안+승인):
  - clean_masking     # 마스킹 → NaN → 수치화
  - fill_missing      # 결측치 채움
  - remove_outlier    # 이상치 제거
  - create_feature    # 피처 생성
  - balance_classes   # 클래스 불균형 보정
  - normalize_group   # 의미 그룹 단위 정규화 (우려1)

L3 (차단+백업):
  - drop_column       # 컬럼 삭제
  - relabel           # 라벨 재정의
  - merge_external    # 외부 데이터 병합
```

#### 명세 정합 확인 필요
- [ ] Planner 가 12개 작업 후보 모두 활용
- [ ] Validator 가 누락 시 lineage 위반 검출
- [ ] Page 4 UI 가 12개 작업 모두 표시 가능

### 1-9-7. Context Aggregator 검증 (v4-patch 신규)

사용자 비전 핵심: MCP 발견 사실 + 4단 에이전트 판단 기록 → Page 5/6 LLM 컨텍스트로 정확히 전파되는지.

#### 검증 항목

| 검증 | 방법 | 임계 |
|---|---|---|
| key_findings 추출 누락 | KAMP 5 데이터셋 × 4 Function 시험 | 누락률 < 5% |
| agent_records 보존 정합성 | PipelineResults 원본 vs AggregatedContext 비교 | 100% (손실 0) |
| LLM 프롬프트 주입 정확성 | Page 5/6 LLM 호출 로그 분석 | AggregatedContext 모든 필드 주입 확인 |
| 환각 방어 | Page 5/6 LLM 출력에 AggregatedContext 외 내용 등장 빈도 | < 5% |
| 결정론 안정성 | 같은 입력 → 같은 AggregatedContext 출력 | 100% 재현 |

#### 환각 방어 메커니즘 통합 검증

| Page | LLM 입력 | 허용 출력 범위 | 검증 |
|---|---|---|---|
| 5 자동 질문 | AggregatedContext + available_options | sample available_options 중 1~2개 | available 외 제안 시 차단 |
| 5 EDA 요약 | AggregatedContext stats + key_findings | facts 인용한 자연어 2~3문장 | 새 추론·예측 시 차단 |
| 6 모델 추천 | AggregatedContext + available_models | available_models 중 N개 + fit_score | available 외 추천 시 차단 |

### 1-9-8. 사전·사후 검증 프로세스 (구현 중 오류 잡기)

본 명세서를 따라 구현 시 발생 가능한 오류를 사전 인지하기 위한 체크리스트:

#### 구현 사전 확인 (작업 시작 전)
- [ ] 1-9-1 KAMP 적재 = DB catalog 단일 진입점 (물리경로 A/B 폐기, D-159)
- [ ] 1-9-3 LLM 모니터링 지표 측정 인프라 준비
- [ ] 1-9-4 step_key 매칭 정합 확인
- [ ] 1-9-5 MCP POST 메서드 정합 확인
- [ ] 1-9-6 OPERATION_PERMISSION 12개 작업 확인

#### 구현 중 확인 (각 페이지 작업 시)
- [ ] Page 2 (Pipeline 구성) — DnD 동작 + max_modules 강제
- [ ] Page 3 (데이터+제약) — constraint_keys 폼 동작 + LLM judge 알람
- [ ] Page 4 (표준화) — step_key 기반 승인 + 카드/자연어 환각 방어
- [ ] Page 5 (분석 목적) — 자동 질문 생성 + 채택률 측정
- [ ] Page 6 (모델링) — 로컬 학습 + 지표 표시

#### 구현 사후 확인 (검증 단계)
- [ ] 1-9-2 constraint_keys 실데이터 피드백 → v0.2 갱신
- [ ] 1-9-3 LLM 모니터링 지표 측정 → 임계 위반 시 활용 영역 축소
- [ ] E2E 시연 시나리오 동작 (3분/7분/15분)
- [ ] Lineage 추적 정확성

> 알파/베타/운영 단계별 상세 검증 체계 + Phase 3 의 8 검증 항목 매핑은 Part 1-9-9 참조.

### 1-9-9. 알파/베타/운영 단계별 검증 체계 (v4-patch 신규)

Phase 3 의 검증 항목 (컴포넌트/API/에러/테스트/데모/부록 A·B·C) 은 사전 결정이 아니라 알파 테스트 + 베타 시연 단계에서 발견·갱신하는 항목. 3 단계 검증 체계로 명시.

#### 알파 단계 (개발자 자체 테스트)

- 데이터: KAMP 더미 (`data/synthetic/` 또는 `data/lake/kamp/`)
- 사용자: 개발자 본인 (구현 주체)
- 환경: 같은 docker-compose, 새 session_id
- 목표: 기본 동작 + 명세 정합 + 환각 방어 작동
- 검증 항목 (Phase 3 + Part 1-9 통합):
  - [ ] Part 8 컴포넌트 props 형식 정합 (구현 중 갱신)
  - [ ] Part 9 API 응답 형식 정밀화 (실제 호출 후 갱신)
  - [ ] Part 10 에러 케이스 새 발견 추가 (실제 에러 발생 시)
  - [ ] Part 11 단위 테스트 + E2E 시나리오 자체 동작
  - [ ] 부록 A 자료구조 JSON 실제 값과 정합
  - [ ] 부록 B curl 예시 응답 정합
  - [ ] 부록 C 상태 천이 누락 발견
  - [ ] Part 1-9-3 LLM 모니터링 7 지표 측정 (e4b/26b)
  - [ ] Part 1-9-4 step_key 매칭 정합
  - [ ] Part 1-9-2 constraint_keys 5 필드 적정성 (KAMP 5 데이터셋)
  - [ ] Part 1-9-7 Context Aggregator 환각 방어 (LLM 출력 5% 미만)

#### 베타 단계 (4 시나리오 시연)

- 데이터: 4 시나리오 (사용자 합의)
  - 시나리오 B: press_imbalance (불균형 시연)
  - 시나리오 D: wafer_defect (이미지 6 클래스 + CNN)
  - 시나리오 A: 사출 통합 (multi-Function)
  - 시나리오 C: cnc_lathe_masked (dtype 혼재)
- 사용자: 팀원 (시연 참관자)
- 환경: docker-compose.beta.yml 또는 같은 환경 + beta session_id 분리
- 목표: UX + 시연 흐름 + 차별점 전달
- 검증 항목:
  - [ ] Part 12 데모 시나리오 시간 분배 정확 (3분/7분/15분)
  - [ ] UX 자연스러움 (드래그앤드롭 / 카드 승인 / 자연어 입력)
  - [ ] 차별점 5가지 전달 ("AI가 코드를 짠다" / "로컬 100%" / "재사용" / "추적" / "사용자 통제")
  - [ ] 알파에서 못 잡은 케이스 발견
  - [ ] 시연 흐름 매끄러움 + 청중 질문 대응
  - [ ] 모달리티 4종 모두 시연 가능

#### 운영 단계 (실제 SI 고객)

- 데이터: 고객 자기 데이터 (Data Lake 신규 등록)
- 사용자: 공장 관리자 (비전문가)
- 환경: 운영용 docker-compose (별도 서버 권장)
- 목표: 실용성 + 가치 증명
- 검증 항목:
  - [ ] Part 1-9-1 KAMP 적재 = DB catalog 단일 진입점 (물리경로 A/B 폐기 확정, D-159)
  - [ ] Part 1-9-5 MCP POST 메서드 정합 (실 데이터 흐름)
  - [ ] Part 1-9-6 OPERATION_PERMISSION 12 작업 모두 사용 검증
  - [ ] Context Aggregator 환각 방어 < 5% 유지
  - [ ] 실제 가치 측정 (모델 정확도 / 시연 효과 / 시간 절약)
  - [ ] 고객 피드백 → 명세 v5 갱신

#### 단계별 환경 분리

| 단계 | 환경 | 데이터 위치 | session 분리 |
|---|---|---|---|
| 알파 | `docker-compose.yml` (개발) | `data/synthetic/` 또는 `data/lake/kamp/` | 새 session_id |
| 베타 | `docker-compose.beta.yml` 또는 같은 환경 + beta tag | `data/lake/beta/` 또는 KAMP 4 시나리오 | beta-prefix session_id |
| 운영 | 운영용 docker-compose (별도 서버 권장) | `data/lake/registered/<고객명>/` | 고객별 session_id 분리 |

#### 검증 사이클

```
명세 작성 (현재)
   ↓
[알파 단계]
   - 명세 → 코드 → 자체 테스트 → 명세 갱신
   - Phase 3 8 검증 항목 모두 알파에서 발견·갱신
   - 1~2주 반복
   ↓
[베타 단계]
   - 알파 통과 → 4 시나리오 시연 → 팀원 피드백 → 명세 갱신
   - UX + 시연 흐름 검증
   - 1주 반복
   ↓
[운영 단계]
   - 베타 통과 → 실제 고객 → 실용성 검증
   - 명세 v5 갱신 (실 사용 피드백)
```

Phase 3 의 8 검증 항목은 모두 알파 단계에서 발견·갱신. 명세서 v5 는 알파 진입 시점의 잠정안, 알파 통과 후 v6 갱신.

---


---

## Phase 1 마무리 — 다음 단계 인수인계

### Phase 1 작성 범위 (본 파일)
- Part 0: Executive Summary (6 페이지 흐름 한눈에)
- Part 1: 공통 설계 원칙 (1-1 기술스택 ~ 1-8 LLM 가치 활용 로드맵)
- Part 2: Page 1 (Line 선택)
- Part 3: Page 2 (Pipeline 구성, 1-1, 앞단)
- Part 4: Page 3 (데이터 + 제약, 1-2, 앞단)
- Part 1-9: 검증·피드백·모니터링 (9 하위 섹션, 알파/베타/운영 포함)

### 다음 단계 (Phase 2, spec-2.md) 가 참조할 결정 사항

**자료구조 (Part 1-2)**:
- `LineCatalog` / `PipelineStructure` / `PipelineFull` / `PipelineResults` / `PipelineStatus` / `AnalysisQuestion` / `DataLakeEntry` / **`AggregatedContext`** (사용자 비전 핵심 — MCP 발견 사실 + 4단 에이전트 판단 기록 → EDA·모델링 LLM 컨텍스트로 전파)

**API 명세**:
- 21 엔드포인트 spec-1 Part 1-3 (1~20+14b). 전체 25 종합표는 spec-3 Part 9-1 참조 (1~25).
- Phase 2 의 Page 4/5/6 API 흐름 정합 확인 필수
- 특히 `/api/aggregate_context/{id}` (Page 4→5 자동 트리거)

**환각 방어 메커니즘 (Part 1-7 + Part 1-9-7)**:
- 카드 (결정론 미리보기, 환각 위험 0)
- 자연어 입력 (OPERATION_PERMISSION 12종 매핑만 + 사용자 재확인 강제 + confidence < 0.7 자동 거부)
- Phase 2 의 Page 4 카드+자연어, Page 5 자동 질문, Page 6 모델 추천 모두 동일 패턴

**Data Lake 정책 (Part 1-6)**:
- `data/lake/<datalake_id>/` flat — DB catalog 단일 진입점 (물리경로 A/B 폐기, D-159)
- Mode A (업로드, 100MB 이하) / Mode B (서버 경로, 대용량) — 사용자 입장 단일 동작
- 적재도구(`tools/datalake_ingest.py`) 메타 자동생성 + catalog INSERT, KAMP·신규 대등 (Part 1-9-1·1-6)

**LLM 가치 활용 로드맵 (Part 1-8)**:
- 5 영역 — ① Stage 컨텍스트 누적 / ② 도메인 추론 / ③ 자동 질문 / ④ EDA 요약 / ⑤ 자연어 매핑
- STEP 1B (도입): ①②③
- STEP 2 (확장): ④⑤
- Phase 2 의 Page 5 = ③④, Page 4 = ⑤ 일부 적용

**검증 체계 (Part 1-9-9)**:
- 알파 (개발자) / 베타 (4 시나리오 시연) / 운영 (고객) 3 단계
- Phase 2/3 의 검증 항목은 모두 알파 단계에서 발견·갱신
- Phase 2 작성 시 각 페이지 끝에 알파 검증 체크리스트 포함

**용어 통일 (Part 6 — `0_project_blueprint_v5.md` 참조)**:
- Line / Stage / Node / Module / Dataset (5 계층)
- L1/L2/L3 = 권한 등급 (Function 축 L1~L4 와 다름 — 맥락 명시 필수)

### Phase 2 가 수행할 내용 (spec-2.md)

| Part | 페이지 | 핵심 |
|---|---|---|
| 5 | Page 4 표준화 진행 (중간단) | SSE+폴링 폴백 / 카드+자연어 환각방어 / step_key 승인 / 미업로드 알람 / Context Aggregator 트리거 |
| 6 | Page 5 분석 목적 + EDA (뒷단) | 자동 질문 LLM (가치 ③) / EDA 차트 4 Function 매핑 (외부 검증) / 데이터 규모 가드 7종 / 자연어 요약 LLM (가치 ④) / 이상치 시각화 / 추가 전처리 |
| 7 | Page 6 모델링 (뒷단) | 추천 카드 (AggregatedContext 활용) / 2 depth (CNN Quick/Full/Skip) / 결과 송출 (지표+Confusion+Importance 기본 + 풀 대시보드 확장) |

### 본 단계 (Phase 1) 설계 결정 사항 요약

> `0_CHANGELOG_v5.md` 는 알파 진입 후부터 기록 시작 (현재 비어 있음). 본 섹션은 v5 설계 단계에서 누적된 핵심 결정의 요약.

- 사용자 6 통찰 반영: typical_ranges 제거, Data Lake 통합, 카드+자연어 2단 환각 방어, LLM 로드맵
- 본진 코드 확인 후 OPERATION_PERMISSION 12종 정확화 + step_key 안정 식별자 매칭
- AggregatedContext 자료구조 추가 (사용자 비전 핵심 — MCP → EDA·모델링 컨텍스트 전파)
- Part 1-9-9 알파/베타/운영 검증 체계 신설

### Phase 2 진입 체크리스트

- [ ] 본 Phase 1 명세 숙독 (특히 Part 1-2 자료구조 + Part 1-7 환각 방어)
- [ ] `0_CHANGELOG_v5.md` 알파 진입 후 기록 확인 (v5 시점은 비어 있음)
- [ ] `0_variable_index_v5.md` 의 API/자료구조 인덱스 확인
- [ ] 사용자 결정 3개 (SSE+폴링, 수동 클릭, 결과 송출 조합) 인지
- [ ] 외부 AI EDA 차트 검증 결과 (`project_eda_charts.md` 메모리) 인지

---

**다음 파일**: `0_pipeline_ui_spec-2_v5.md` (Phase 2, Page 4~6)

**작성**: 2026-05-27 spec-1 v5 (Claude Opus 4.7, 분할 + 명명 규칙 + 인수인계 템플릿)
