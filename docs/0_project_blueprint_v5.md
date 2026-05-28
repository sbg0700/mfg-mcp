# manufacturing-mcp 프로젝트 통합 설계서 (v5)

> **문서 목적**: 팀원 공유 + AI 컨텍스트 제공용. 프로젝트 정체성·현재 완성도·LLM 통합 패턴·다음 단계(STEP 1B + 옵션 E) 청사진을 사실 기반으로 정리.
>
> **Snapshot**: 2026-05-27 v5 (모든 산출 파일 버전 통일 — blueprint/spec-1/2/3/variable_index 동일 v5).
>
> **v5 변경 요약 (v3 누적)**:
> - Part 4-4 신규: MCP → EDA·모델링 컨텍스트 전파 (Context Aggregator)
> - spec 인용 6곳 → Phase 별 3 분할 (spec-1/2/3) 형태로 갱신
> - 페이지별 prefix 명명 규칙 반영 (step1_line ~ step6_modeling)
> - 추가 문서 링크: 0_variable_index_v5.md, 0_CHANGELOG_v5.md
> - 본 산출물 7 파일 모두 `_v5` 통일 (README 포함, 사용자 합의)
>
> **v3 변경 사항 (v2 대비)**:
> - 가독성 정비: 마크업 별표() 제거, 핵심 강조는 굵게/인용 블록으로 절제 사용
> - 용어 정비: "앞단/중단/뒷단" → "앞단/중간단/뒷단"
> - 드래그앤드롭 UI는 **사용**(자료구조만 list of lists, DAG 그래프 라이브러리는 불필요) — v2의 "드래그앤드롭 없이" 표현 정정
> - L2/L3 승인 표현 일반화 — "1-click"이라는 단정 표현 제거 → "사용자 승인 게이트(구체 UI는 팀원 디벨롭 방안 참조)"
> - MCP 7도구 + 사용자 제약 흐름 명시 (1-2 페이지 입력이 도구로 어떻게 전파되는지)
> - 박스 안 다중 모듈은 일반 원칙으로 격상 (KAMP 6사례는 예증)
> - 4단 Agentic Flow 섹션에 "팀원 구현체, 사용자 검증 필요 지점" 박스 추가
>
> **인용 규칙**: 파일 경로 + 한줄 설명 위주. 보안 노출 제한: 호스트명·DB 자격증명·포트 번호 마스킹.
>
> **위치 약칭**: `repo/` = `manufacturing-mcp/` 본진 루트.

---

## Part 0. Executive Summary

### 한 줄 정체성
SI 기업용 **MCP·Agent·로컬 LLM 기반 제조 데이터 전처리 자동화 시스템**.
차별점: **"기존 ETL은 사람이 코드를 짠다 / 우리는 AI가 코드를 짠다 + 모든 추론 로컬 + 추적 가능"**.

### 한 마디
> 모달리티는 수단, 공장 단위 통합이 북극성.
> 모달리티 4종 표준화(1층) → 사전정의 카탈로그·컨텍스트 누적 파이프라인(STEP 1B/옵션 E) → 공정·목적 기반 통합(2층).

### 현재 완성도 (2026-05-27 기준)

**1층 = 모달리티 표준화 완료** (팀원 구현체 기반):
- 4단 Agentic Flow (Inspector → Planner → Executor → Validator) 전부 실동작
- 4 모달리티 MCP 서버 (timeseries / inspection-image / event-log / order) 전부 7도구 동일 계약
- 3-tier 권한 게이트 + Lineage 자동 기록 동작
- 8 챌린지 더미 데이터 의도적 심음
- Backend FastAPI 3 체인 엔드포인트 (/inspect, /plan, /execute)
- UI 모델 선택 (E4B↔26B 즉석 비교)

**STEP 1B 진입 직전 (다음 작업)**:
1. Harness 결과 검증 강화 (1순위, 사용자 본인 예약)
2. 의미 그룹화 (우려 1: 컬럼명 패턴 → semantic_group)
3. Module Catalog v0.1 (Line/Stage/Node/Module 사전정의 카탈로그)
4. Planner 프롬프트 확장 (module_context + stage_context + constraints 누적)
5. Mini UI 6 페이지 — **드래그앤드롭은 사용**, 다만 DAG 그래프 라이브러리(React Flow) 없이 단순 박스+화살표 + 폼

### 차별점 (정직 버전)
- **실제 AI**: Inspector·Planner가 LLM 활용 + 결정론적 가드레일 결합
- **재사용 증명**: 같은 Agent·Harness·UI 코드로 4 모달리티 동일 처리 (timeseries 코드를 image에 적용 시 0줄 변경)
- **컴플라이언스**: 모든 변환에 Lineage + 사용자 승인 토큰 기록 → SI 영업 핵심
- **로컬 100%**: 외부 API 호출 절대 금지, 단일 8GB VRAM GPU에서 동작
- **사용자 통제**: L2/L3 작업은 사용자 승인 게이트 (구체 UI 형태는 팀원 디벨롭 방안 참조 — Part 5-3 노트)

---

## Part 1. 프로젝트 정체성 + 절대 규칙

### 1-1. CLAUDE.md (설계 헌법)의 절대 규칙

`repo/CLAUDE.md` — 매 세션 가장 먼저 읽는 기준 문서. 다른 문서와 충돌 시 항상 우선.

| # | 절대 규칙 | 이유 |
|---|---|---|
| 1 | 메인 `gemma4:26b`, 스캐폴딩 `gemma4:e4b`. 31B Dense 금지 | RTX 3070 VRAM 제약 |
| 2 | Agent 프레임워크 = 가벼운 수제 Python. Claude Agent SDK·LangGraph 도입 금지 | 로컬 Ollama 호환성 미검증 + 수직 슬라이스 우선 |
| 3 | 외부 API 호출 금지 (Claude / GPT / Gemini) | SI 고객 "데이터 외부 전송 0" 보장이 핵심 |
| 4 | 데이터는 외부로 나가지 않음. 외부 노출은 HTTP/HTTPS 대시보드뿐 | 도커 내부망 통신 |
| 5 | 코드는 호스트 파일시스템. 도커는 실행 환경만 (볼륨 마운트) | 코드 수정 즉시 반영 |

> **우려 사항 (팀원 관제 영역, 실측 수치 기반)**: Gemma 4 (2026-04 출시, Ollama v0.20.0+ 지원) VRAM — `gemma4:26b`=**18GB**, `gemma4:e4b`=**9.6GB** (8GB 초과), `gemma4:e2b`=7.2GB. 8GB RTX 3070 단일 GPU에 GPU 적재 가능한 태그는 **`e2b` 한 가지**. 팀원 결정 옵션: (a) `e2b` 단일, (b) `e2b` inline + `26b` CPU 오프로딩 occasional (1~3 tok/s — 분 단위 지연), (c) GPU 업그레이드 (16GB+), (d) 전체 CPU 폴백. 모델 결정 후 본 표 행 #1 + spec mockup `[모델: e4b ▼]` 표기 일괄 동기화 필요. 알파 진입 시 `ollama pull` 후 실측 검증 (Part 9-6 참조). 본 우려는 확인 후 진행하면 되는 수준.

### 1-2. 모달리티 분할 원칙 (변경 금지)

MCP 서버는 공정이 아니라 **데이터 패턴(모달리티)** 단위로 쪼갠다.

```
manufacturing/
  ├─ timeseries        설비 시계열 (압력·전류·온도·진동)
  ├─ inspection-image  검사 이미지 (결함 분류·검출)
  ├─ event-log         LOT 이벤트 (양·불 판정)
  └─ order             주문·생산량
```

도장에서 만든 MCP가 주조·MCT에 그대로 재사용. 새 공정(Node) 추가해도 **MCP는 안 늘어남**. 이것이 핵심 영업 메시지.

### 1-3. MCP 표준 도구 인터페이스 (7종, 변경 금지)

`repo/CLAUDE.md §4`. 모든 모달리티 서버 공통 시그니처:

| 도구 | 시그니처 | 권한 | 설명 |
|---|---|---|---|
| `list_columns` | `(dataset_id) -> 컬럼명·타입·통계 (컬럼별 메타)` | L1 | 컬럼별 dtype/null/unique/mixed_dtype 자동 감지 |
| `get_schema` | `(dataset_id) -> JSON Schema` | L1 | 스키마 추출 |
| `sample` | `(dataset_id, n=5) -> 샘플 행` | L1 | 요약 샘플 (LLM 컨텍스트 보호) |
| `detect_encoding` | `(file_path) -> 인코딩` | L1 | 인코딩/포맷 감지 |
| `check_constraints` | `(dataset_id, constraints) -> 위반 리스트` | L1 | **사용자 제약(1-2 페이지 입력) 검증** |
| `apply_preprocessing` | `(dataset_id, operations, permission_level)` | L1/L2/L3 | 전처리 실행 (권한 분기) |
| `lineage` | `(dataset_id) -> 변환 체인` | L1 | 계보 조회 |

**시그니처는 4 모달리티 전부 동일**. 모달리티별로는 로직만 달라짐 = 재사용 증명.

#### 1-3-1. 사용자 제약은 어떻게 흘러가나 (피드백 3 반영)

1-2 페이지에서 사용자가 입력한 제약(max 온도, range 등)이 도구로 전파되는 흐름:

```
[1-2 페이지 입력]
사용자 → 폼 입력 → constraints = { mold_temp_c: [20, 400], cycle_time_sec: [15, 180] }
                             ↓
[Backend → MCP]
check_constraints(dataset_id, constraints) → 위반 리스트
                             ↓
[Inspector]
DataProfile.constraints = constraints (전파)
                             ↓
[Planner LLM 프롬프트]
"제약: { mold_temp_c: [20, 400], ... } 을 위반하는 컬럼은?"
                             ↓
[작업 후보 분기]
- 위반 발생 컬럼 → "outlier_clip" 작업 후보 추가 (L2)
- 위반 없는 컬럼 → 기본 작업 후보만
                             ↓
[Executor]
apply_preprocessing(dataset_id, operations, permission_level)
operations 안에 컬럼별 다른 작업 명시
```

#### 1-3-2. L1 권한의 "컬럼별 특성 감지" 의미 (피드백 3 반영)

질문: "L1에서 컬럼별로 다른 특성 감지해서 별도 작용하는 거 맞나?"

답: 정확히는 두 단계로 분리된 동작:

| 단계 | 권한 | 동작 |
|---|---|---|
| 컬럼별 특성 감지 | L1 (자동) | `list_columns`가 각 컬럼마다 dtype/null_count/n_unique/mixed_dtype_suspected/imbalance_suspected를 자동 계산 |
| 컬럼별 다른 작업 후보 생성 | L1 (Planner의 결정론 단계) | Planner가 list_columns 결과를 보고 컬럼마다 다른 작업 후보 추출 (예: mixed_dtype 컬럼만 clean_masking 후보) |
| 컬럼별 작업 실행 | L1/L2/L3 (작업별) | Executor가 권한 분기 후 실제 컬럼별 변환 수행 |

**핵심**: L1은 "결정론 + 자동" 등급이고, 컬럼별 다른 특성 감지는 list_columns 안에서, 컬럼별 다른 작업 후보 생성은 Planner의 규칙 단계에서 일어난다.

---

## Part 2. 시스템 전체 그림 — 사용자 비전 6단계 + 옵션 E

### 2-1. 사용자 비전의 6단계 페이지 시퀀스

```
[1단계] Line 선택
  사용자가 3개 라인 중 하나 선택
  (Line 1 금속 / Line 2 성형 / Line 3 폴리머·전자)
                          ↓
[2단계] Pipeline 구성 (1-1 페이지) — 앞단 (Front Stage)
  Line의 사전정의 Stage 박스가 표시되고,
  각 Stage 박스에 모듈 카탈로그(KAMP 기준 사전정의)에서
  드래그앤드롭으로 Node + Function 모듈을 선택해 배치.
  결과 → LLM 컨텍스트만 전달 (구조만 결정, 데이터 없음)
                          ↓
[3단계] 데이터 + 제약 입력 (1-2 페이지) — 앞단 (Front Stage)
  2단계에서 정해진 각 모듈마다:
   - 데이터 파일 업로드
   - 제약 폼 입력 (max 온도, 데이터 range 등)
  결과 → MCP + LLM 양쪽 컨텍스트로 전달
                          ↓
[4단계] MCP 표준화 진행 — 중간단 (Middle Stage) = 현재 1층 코드
  Stage 순서대로 처리:
   - Inspector → MCP 7도구 호출 → DataProfile
   - 진행률 + 발견 챌린지 + LLM 해석 표시
   - L2/L3 작업 사용자 승인 게이트 (구체 UI는 팀원 디벨롭 방안)
                          ↓
[5단계] 분석 목적 질문 + 전처리 결과 — 뒷단 (Back Stage)
  Stage 안 모듈 정보로 자동 질문 후보 생성
  사용자 선택 → Function 컨텍스트 결정 → 추가 전처리
  EDA/이상치 처리 결과 송출 (차트 + 표 + 자연어 요약)
                          ↓
[6단계] 모델링 — 뒷단 (Back Stage)
  Module Catalog의 recommended_models 추천
  사용자 승인 → 로컬 LLM/소형 ML 학습/추론
  결과 송출 (지표 + confusion matrix + feature importance)
```

### 2-2. 1-1 vs 1-2 페이지 분리 (컨텍스트 흐름)

이 분리가 사용자 비전의 핵심 통찰입니다.

| 페이지 | 사용자 입력 | 결과 컨텍스트 흐름 | 의미 |
|---|---|---|---|
| **1-1 (Pipeline 구성)** | Line 선택 + 사전정의 Stage 박스에 모듈을 드래그앤드롭으로 배치 | LLM 컨텍스트만 — Planner 프롬프트의 `module_context` / `stage_context`에 주입 | 공정의 의미·흐름 결정 (도메인 지식 영역) |
| **1-2 (데이터 + 제약)** | 각 모듈에 파일 업로드 + 제약 폼 (max 온도/range) | MCP + LLM 양쪽 — MCP가 제약을 표준화 시 활용 + LLM도 컨텍스트로 받음 | 실제 데이터 처리 영역 (운영 제약 영역) |

1-1은 도메인/공정 의미 결정, 1-2는 데이터·제약 결정. 둘이 완전히 다른 컨텍스트 흐름.

### 2-3. 옵션 E 자료구조 (단순 예시)

> 아래 자료구조는 단순 예시입니다. 실제로는:
> - 모듈 갯수 / 리스트 갯수 = KAMP 데이터셋 기준 **max 값을 사전 지정**
> - 매핑이 안 되어 비어있는 슬롯 = **LLM으로 넘기지 않음**
> - DAG 그래프 라이브러리는 불필요 (단순 박스 + 화살표 + list of lists)

#### 1-1 페이지 출력 (구조만)

```python
pipeline_structure = {
    "line_id": "module_3_polymer_electronic",
    "stages": [
        {
            "stage_order": 0,
            "node_id": "injection_molding",           # 사전정의 Node
            "modules": [                              # 박스 안 모듈 list (max는 부록 A 카탈로그 기준)
                {"function": "process",      "dataset_role": "injection_optimize"},
                {"function": "quality",      "dataset_role": "injection_production"},
                {"function": "maintenance",  "dataset_role": "mold_anomaly"}
            ]
        },
        {
            "stage_order": 1,
            "node_id": "semiconductor_inspect",
            "modules": [
                {"function": "quality", "dataset_role": "wafer_defect"}
            ]
        }
        # 사용자가 Stage 안 그린 자리는 list에 아예 등장하지 않음 (= LLM에 전달 안 됨)
    ]
}
```

#### 1-2 페이지 출력 (데이터 + 제약 추가)

```python
pipeline_full = {
    # 1-1 구조 그대로 + 각 모듈에 datalake_id / constraints 추가
    "stages": [
        {
            "stage_order": 0,
            "node_id": "injection_molding",
            "modules": [
                {
                    "function": "process",
                    "dataset_role": "injection_optimize",
                    "datalake_id": "kamp_L1_injection_optimize",  # v4 — Data Lake catalog ID
                    "constraints": {                              # 1-2 입력
                        "mold_temp_c": [20, 400],                 # range form (사용자 입력)
                        "cycle_time_sec": [15, 180]
                    }
                },
                {
                    "function": "maintenance",
                    "dataset_role": "mold_anomaly",
                    "datalake_id": null,                          # 데이터 미업로드
                    "constraints": {}
                }
            ]
        }
    ]
}
```

> v3의 `data_path`는 폐기됨. 실제 서버 경로는 `DataLakeEntry.data_path` (백엔드 내부) 로 catalog에서 조회 (사용자 노출 안 함). spec-1 Part 1-6 Data Lake 인터페이스 참조.

### 2-4. 박스 안 다중 모듈 — 일반 원칙 (피드백 6 반영)

**일반 원칙**: 다양한 처리(PdM, Inspection, Process, Order 등)가 **하나의 데이터셋 내에서** 또는 **한 공정 Stage 내에서** 다중으로 걸릴 수 있다. 즉 한 Stage 박스에 1~N개 모듈이 동시에 배치 가능.

이 원칙의 KAMP 실증 사례 (예시):

| 공정 Node (= 박스) | 박스 안 모듈에 들어갈 수 있는 데이터셋 | Function 다중성 |
|---|---|---|
| M1/3 MCT 가공 | `L1_mct_tool_manage` + `L1_mct_tool_improve` (8 xlsx) + `L3_mct_condition_inspect` (9 xlsx) | process + maintenance |
| M3/2 사출 성형 | `L1_injection_optimize` + `L1_injection_production` + `L1_cnc_machine_optimize` | process 다측면 |
| M1/1 1차 성형 | `L3_mold_condition` + `L3_mold_anomaly` | maintenance (2종) |
| M2/4 용접 검사 | `L2_welding_bead` (이미지) + `L2_welding_electrode` (CSV+이미지) | quality 모달리티 혼재 |
| M3/5 반도체 검사 | `L2_auto_console_detect` + `L2_wafer_defect` (둘 다 이미지) | quality 2종 |
| M1/6 PdM 설비 | `L3_rotary_drill` + `L3_solenoid_roughing` + `L3_guideloader_drill` | maintenance 3종 |

위 6사례는 예증이며, 원칙은 일반적으로 적용됩니다. 박스 안 max_modules 수치는 사전정의 카탈로그(부록 A)에서 결정.

### 2-5. 컨텍스트 누적 백엔드 동작 — Resumable Orchestrator (의사 코드)

> **모델**: 1-shot 배치 실행 (1층 `/api/execute` 단일 데이터셋 모드) 아님. STEP 1B `/api/execute_pipeline` 는 세션 상태 머신으로 L2/L3 게이트에서 suspend → SSE `approval_required` 송출 → 사용자 `/approve` POST → resume. Page 4 UX (spec-2 5-5 + spec-3 부록 C-2) 정합.

```python
# backend/main.py 의 /api/execute_pipeline (~70줄, 세션 상태 머신)
async def execute_pipeline(session_id):
    session = load_session(session_id)
    pipeline_full = session.pipeline_full
    # cumulative — /approve 호출마다 추가
    approved_step_keys = session.approved_step_keys  # set[str]
    accumulated_context = session.accumulated_context  # 이전 Stage 누적

    for stage in pipeline_full["stages"]:
        # resume 시 이미 완료된 stage 는 skip
        if stage["stage_order"] in session.completed_stage_orders:
            continue

        # 데이터 미업로드 모듈 LLM judge (알람만, 결정은 사용자)
        missing = [m for m in stage["modules"] if m["datalake_id"] is None]
        if missing:
            alarm = await llm_judge_data_necessity(
                stage=stage,
                missing=missing,
                other_modules=[m for m in stage["modules"] if m["datalake_id"]]
            )
            session.emit_sse({"type": "alarm", "stage_order": stage["stage_order"], "alarm": alarm})
            await session.wait_user_decision()  # 사용자 입력 대기

        # 실제 업로드된 모듈만 처리
        for module in stage["modules"]:
            if module["datalake_id"] is None:
                continue
            module_key = f"{stage['stage_order']}.{module['index']}"
            if module_key in session.completed_module_keys:
                continue

            # Data Lake catalog 조회 (실제 경로는 백엔드 내부 사용)
            entry = datalake.get(module["datalake_id"])

            # Inspector (1-2 제약 함께 전달)
            profile = await inspector.inspect(
                entry.data_path, entry.modality, module["constraints"]
            )
            session.emit_sse({"type": "inspector_done", "module": module_key, "profile": profile})

            # Planner (1-1 컨텍스트 + 누적 stage_context)
            plan = await planner.plan(
                profile,
                module_context={"function": module["function"]},
                stage_context={"previous_stages": accumulated_context}
            )
            session.emit_sse({"type": "plan_ready", "module": module_key, "plan": plan})

            # Executor — step-by-step with L2/L3 suspension
            for step in plan.steps:
                if step.permission_level != "L1" and step.step_key not in approved_step_keys:
                    # suspend — 세션 상태 awaiting_approval
                    session.status = "awaiting_approval"
                    session.save()
                    session.emit_sse({
                        "type": "approval_required",
                        "stage_order": stage["stage_order"],
                        "module_index": module["index"],
                        "step_key": step.step_key,
                        "permission_level": step.permission_level,
                        "preview": step.preview_stats
                    })
                    await session.wait_for_approval(step.step_key)  # blocks until /approve
                    approved_step_keys.add(step.step_key)
                # 승인 받은 step 실행
                result = await executor.execute_step(step, entry.data_path)
                session.save_step_result(result)

            # Validator
            validation = await validator.validate(session.step_results[module_key])
            session.emit_sse({"type": "validator_done", "module": module_key, "validation": validation})
            session.completed_module_keys.add(module_key)

        session.completed_stage_orders.add(stage["stage_order"])
        accumulated_context.append({"stage_order": stage["stage_order"], ...})  # 요약 누적

    # 모두 완료 → Context Aggregator (결정론, LLM 없음)
    session.aggregated_context = context_aggregator.aggregate(session)
    session.status = "completed"
    session.emit_sse({"type": "pipeline_completed"})


# POST /api/pipeline/{session_id}/approve — 단건 승인
async def approve(session_id, body):
    # body: {stage_order: int, module_index: int, step_key: str}
    session = load_session(session_id)
    session.approved_step_keys.add(body["step_key"])
    session.notify_approval(body["step_key"])  # awaiter release
    return {"approved": True}
```

복잡한 그래프 알고리즘 없음. 세션 상태 머신 + step_key 기반 단건 승인 + SSE 이벤트.

**승인 payload 통일**: `/api/pipeline/{id}/approve` body = `{stage_order, module_index, step_key}` (단건). 세션 내부 상태는 `approved_step_keys: set[str]` 누적. 1층 단일 데이터셋 모드 `/api/execute` 의 `approved_steps: list[int]` (order 기반) 는 1층 전용으로 분리 보존.

### 2-6. 빈 슬롯 정책

2가지 상태 분리:

| 상태 | 의미 | 처리 |
|---|---|---|
| **빈 슬롯 (모듈 자체 없음)** | 사용자가 1-1에서 안 그린 stage / 모듈 | 처음부터 없는 것 (LLM에 전달 안 함) |
| **모듈 있음 + 데이터 미업로드** | 1-1에 모듈 박스 두고 1-2에서 파일 업로드만 빠짐 | LLM 판단 → 필수 데이터면 알람, 아니면 skip 처리 |

구분 메커니즘:
- 1-1 출력 = `pipeline.stages[].modules[]`에 모듈 존재 여부
- 1-2 출력 = `module.datalake_id` 값 (null이면 미업로드)
- LLM 판단 기준 = 박스 안 다른 모듈과의 상호 의존성 + 공정 컨텍스트

### 2-7. 박스 안 모듈 통합 정책

박스 A에 `[PdM, Inspection]` 두 모듈 있을 때:

| 단계 | 처리 |
|---|---|
| 1-1 (구조 결정) | 두 모듈을 같은 Stage 박스에 배치 (사용자 의도 = "함께 영향") |
| 1-2 (데이터 + 제약 입력) | 두 모듈 각각 데이터 업로드 + 제약 입력 |
| 4 (MCP 표준화) | 독립 처리 — PdM 따로, Inspection 따로 표준화 |
| Planner 시점 | stage_context 공유 — 같은 Stage 안 다른 모듈의 결과 요약을 LLM 컨텍스트로 공유 |
| 5 (분석 목적) | 사용자가 결정한 분석 목적에 따라 join 키 명시 → 데이터 통합 |

MCP 표준화 시점에는 join 안 함. 5단계에서 사용자 의도 받은 후 join.

---

## Part 3. 1층 구현체 아키텍처 (현재 동작 중)

### 3-1. 전체 컴포넌트 맵

```
┌─────────────┐      ┌────────────────────────┐
│  Frontend   │ ───▶ │  Backend (FastAPI)     │
│ index.html  │      │  /inspect /plan /exec  │
└─────────────┘      └────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐   ┌─────────────┐  ┌──────────┐
       │ Ollama   │   │   Agents    │  │ Postgres │
       │ gemma4   │   │ 4 Agents    │  │ 3 schema │
       └──────────┘   └─────────────┘  └──────────┘
                              │
            ┌────────┬────────┼────────┬────────┐
            ▼        ▼        ▼        ▼        ▼
        ┌────────┐ ┌─────┐ ┌────┐ ┌─────┐ ┌────────┐
        │ MCP    │ │ MCP │ │MCP │ │ MCP │ │Harness │
        │timeser │ │image│ │event│ │order│ │4 모듈  │
        └────────┘ └─────┘ └────┘ └─────┘ └────────┘
            │        │       │       │
            ▼        ▼       ▼       ▼
          [data/synthetic/* — 8 챌린지 더미]
```

### 3-2. 4단 Agentic Flow

> **이 섹션은 팀원이 구현한 1층 코드의 사실 확인을 정리한 것입니다.** 사용자 본인이 직접 수행한 부분이 아니며, 다음 항목에 대해 사용자 검증/확인이 필요할 수 있습니다 (Part 3-2-1 박스 참조). 사실 확인은 byeonggab89 본진의 실제 코드를 직접 읽어 정리한 것이므로 코드 자체와 일치합니다.

각 단의 역할 + 파일 경로:

#### Inspector (1단, 권한 L1, 결정론 + LLM 해석)
- 위치: `repo/agents/inspector/inspector.py`
- 명세: `repo/docs/specs/inspector.md`
- 출력 스키마: `repo/agents/inspector/schemas.py` — `DataProfile` 클래스
- 흐름:
  1. MCP 결정론 도구 호출 (`list_columns`, `get_schema`, `sample`, `detect_encoding`)
  2. 결정론적 flags 계산 (cp949 / headerless / mixed_dtype — LLM 없이도 잡힘)
  3. LLM에 요약만 전달 → JSON 강제 응답 (`modality_guess`, `concerns`, `recommended_next_steps`)
  4. `DataProfile` 반환

#### Planner (2단, 계획만, "후보 = 진실의 원천")
- 위치: `repo/agents/planner/planner.py`
- 스키마: `repo/agents/planner/planner_schemas.py` — `PlanStep`, `PreprocessingPlan`
- 핵심 설계 사상:
  1. 규칙으로 후보 작업 추리기 (Inspector flags 기반, 결정론)
  2. LLM에 "새 작업 지어내기 금지, 순서·이유만 정해라" 강요
  3. 후보(candidates) = 진실의 원천. LLM의 누락/환각 모두 흡수
  4. 권한 등급은 가드레일이 결정, LLM이 못 바꿈
- 후보 작업 매핑 (Inspector flags → 작업 후보):
  - `non-utf8` → `detect_encoding` (L1)
  - `headerless` → `reparse_header` (L1)
  - `mixed_dtype_suspected` → `clean_masking` (L2)
  - `null_count > 0` → `fill_missing` (L2)
  - `imbalance_suspected` → `balance_classes` (L2)
  - (항상) → `compute_stats` (L1)
- STEP 1B 확장 예정: `module_context` + `stage_context` + `constraints` 파라미터 추가

#### Executor (3단, 권한 L1/L2/L3, 결정론 변환 + 권한 게이트)
- 위치: `repo/agents/executor/executor.py`
- 동작:
  1. 모달리티 분기 (`timeseries` / `inspection-image` / `event-log` / `order`)
  2. 변환 전 parquet 백업 (rollback 근거)
  3. 권한 게이트: L2/L3 작업은 사용자 승인 토큰 없으면 `awaiting_approval`
  4. 결정론 변환 (LLM 아님)
  5. Lineage 자동 기록
- 구현된 변환 (1층):
  - `clean_masking` — 마스킹 문자 → NaN → 수치화 (L2)
  - `fill_missing` — 중앙값/최빈값 (L2)
  - `balance_classes` — 불균형 진단 + 보정 전략 제안 (L2)
  - `compute_stats` — 기초 통계 (L1)

#### Validator (4단, 컴플라이언스 검증)
- 위치: `repo/agents/validator/validator.py`
- 출력: `ValidationReport` (passed / n_done / n_failed / n_pending / issues / next_action)
- STEP 1B 확장 예정: 변환 전후 비교 + 계획 무결성 + 회귀 + 롤백 라우팅 (Harness 검증 4종 강화)

#### 3-2-1. 사용자 검증/확인 필요 지점 (피드백 7 반영)

> 아래 항목들은 코드에서 사실 확인된 동작이지만, 사용자의 원래 의도와 일치하는지 별도 검증이 필요할 수 있는 부분입니다.

| # | 검증 필요 항목 | 내용 |
|---|---|---|
| V1 | Inspector의 LLM 응답 JSON 파싱 실패 시 fallback | 모델 미설치/응답 오류 시 `{"_raw": raw, "_note": "..."}` 형태로 반환. 의도된 안전장치인가? 아니면 더 엄격한 에러 처리 필요한가? |
| V2 | Planner의 "후보 = 진실의 원천" 원칙 적용 | LLM이 후보 외 작업을 제안해도 가드레일이 무시함. 이게 사용자 의도와 일치하는가? (지금까지 합의로는 일치) |
| V3 | Executor의 모달리티 분기 (timeseries / image / event-log) | timeseries와 order는 같은 코드 경로(`_resolve`에 modality 분기), image와 event-log는 별도 함수(`_execute_image`, `_execute_eventlog`). 이 구조가 향후 5번째 모달리티 추가 시 확장 가능한가? (현재 결정: 5번째 모달리티 추가 금지) |
| V4 | Validator의 현재 검증 범위 | 현재는 lineage_id 누락만 검출. Harness 검증 4종(변환 전후/무결성/회귀/롤백) 이 추가될 지점이 이 Validator인가, 별도 모듈인가? |
| V5 | 권한 게이트의 토큰 형식 | 현재 `approval_token = "ui-approved-{order}"` 더미 토큰. 실제 사용자 인증/세션 결합 시점은 언제인가? |
| V6 | DataProfile의 `llm_interpretation` 필드 | LLM 출력을 그대로 dict로 저장. 다운스트림(Planner)이 이 필드의 어떤 키를 신뢰하는가? `modality_guess`만? concerns도? |
| V7 | Inspector → Planner의 A2A (Agent-to-Agent) 메시지 패싱 | 현재 backend가 두 Agent를 직접 호출(`run_inspect` → `run_plan`). 이게 향후 멀티 Agent 협업(추가 Agent 도입) 시 어떻게 확장되나? |

각 항목에 대해 사용자(또는 팀원)가 의도와 비교 검토하고 차이 있으면 본 문서에 결정 사항으로 기록.

### 3-3. 4 모달리티 MCP 서버

| 모달리티 | 위치 | 데이터 단위 | 모달리티별 특수 처리 |
|---|---|---|---|
| `timeseries` | `repo/mcp-servers/timeseries/` | CSV 파일 | 인코딩 휴리스틱, headerless 감지, 마스킹 dtype 혼재 감지 |
| `inspection-image` | `repo/mcp-servers/inspection-image/` | 이미지 폴더 (라벨=상위 폴더) | mode/format/해상도 혼재 감지, .txt 동명 페어 |
| `event-log` | `repo/mcp-servers/event-log/` | CSV 또는 Excel(멀티시트) | 멀티시트 outer merge (LOT_NO), 클래스 불균형 감지 |
| `order` | `repo/mcp-servers/order/` | CSV (CP949 흡수) | timeseries와 거의 동일, ORDER_DATA_ROOT만 분리 |

각 서버 구성:
- `server.py` — FastAPI HTTP 라우팅 (7 도구를 엔드포인트로 노출)
- `tools.py` — 7 도구 구현 (모달리티별 로직)
- `Dockerfile` — 컨테이너 빌드
- `requirements.txt` — Python 의존성

7 도구 키 = 4 서버 모두 동일. 상위 Agent 코드는 모달리티별 분기 외에 변경 없음.

### 3-4. Harness 4계층

`repo/harness/` 하위 4개 모듈:

| 모듈 | 위치 | 역할 | 현재 상태 |
|---|---|---|---|
| Context | `repo/harness/context.py` | LLM 컨텍스트 관리 (큰 데이터 직접 주입 금지) | stub |
| Guardrails | `repo/harness/guardrails.py` | `OPERATION_PERMISSION` 단일 소스 — 작업→권한 매핑 | 경량 동작 |
| Lineage | `repo/harness/lineage.py` | 변환 체인 인메모리 저장 (Sprint 2에 PostgreSQL 이전) | 동작 |
| Schema Validation | `repo/harness/schema_validation.py` | 입출력 스키마 검증 | 경량 동작 |

### 3-5. Backend FastAPI (오케스트레이션)

`repo/backend/main.py` — 진입점. 핵심 엔드포인트:

| 엔드포인트 | 메서드 | 역할 |
|---|---|---|
| `/api/health` | GET | LLM + MCP 가용성 |
| `/api/modalities` | GET | 4 MCP 서버 health |
| `/api/datasets?modality=...` | GET | 모달리티별 데이터셋 목록 |
| `/api/models` | GET | Ollama 설치 모델 목록 (UI 드롭다운) |
| `/api/inspect` | GET | 1단 (Inspector) |
| `/api/plan` | GET | 1+2단 (Inspector → Planner) |
| `/api/execute` | POST | 1+2+3단 + `approved_steps` |
| `/api/execute_pipeline` | POST | STEP 1B 신규 — 옵션 E pipeline 객체 받음 |
| `/api/lines` | GET | STEP 1B 신규 — 라인/노드/모듈 카탈로그 조회 |
| `/` | GET | `frontend/index.html` 서빙 |

LLM 클라이언트:
- `repo/backend/llm.py` — Ollama HTTP 래퍼. 모델 교체는 오직 여기 (환경변수 `OLLAMA_MODEL`).

### 3-6. PostgreSQL 스키마 (3개)

`repo/db/init.sql`:

| 스키마 | 테이블 | 역할 |
|---|---|---|
| `metadata` | `datasets` | 데이터셋·모달리티·인코딩 메타 |
| `lineage` | `transformations` | 모든 변환 기록 (SI 컴플라이언스 핵심) |
| `agent_logs` | `decisions` | 에이전트 의사결정 로그 |

### 3-7. 더미 데이터 (8 챌린지 의도적 심음)

위치: `repo/data/synthetic/<modality>/`. 챌린지 매핑은 부록 D 참조.

### 3-8. 환경

- 호스트: 개발서버 1대 / Ubuntu 24.04.4
- GPU: 단일 8GB VRAM GPU
- RAM: 32GB
- Docker + NVIDIA Container Toolkit 검증 완료

> 보안 노출 제한을 위해 호스트명/사용자명/DB 자격증명/포트 번호 등 구체 식별 정보는 본 핸드오버에서 제거함.

---

## Part 4. LLM (Gemma) 통합 패턴

### 4-1. 사용자 비전

> "LLM의 주관적 판단이 아닌, 학습된 세트의, 주어진 형태 내에서 세부적 판단을 로컬 LLM(Gemma4)이 하는 형태로 구현하고 싶어"
> "내가 정의한 Function을 주 축으로 어떻게 활용할 수 있을지에 대한 것을 LLM이 판단하여 사용자에게 의사를 물어보는 그런 형태"

### 4-2. 이미 구현된 메커니즘 4가지

#### (가) Inspector — "결정론 + LLM 해석" 분리
- 결정론적으로 잡히는 것 (encoding/headerless/mixed_dtype)은 LLM 없이 잡음
- LLM에는 요약만 전달 (큰 데이터 직접 주입 금지)
- LLM 응답 = JSON 강제 (`format=json`)
- 위치: `repo/agents/inspector/inspector.py`

#### (나) Planner — "후보 = 진실의 원천"
- 규칙이 후보 작업을 전부 추림 → LLM에 "새 작업 지어내기 금지" 강제
- LLM의 기여 = 순서·이유만
- 후보 외 작업이 LLM 응답에 있어도 실행 안 됨 (가드레일이 차단)
- 위치: `repo/agents/planner/planner.py`

#### (다) Permission Gate — 권한 등급으로 LLM 행동 제한
- L1 자동 / L2 제안+승인 / L3 차단+백업
- L2/L3 작업 = 사용자 승인 토큰 없으면 `awaiting_approval`
- 사용자 승인 → 토큰 반환 → Executor 실행
- 구체 승인 UI 형태는 팀원 디벨롭 방안 참조 (Part 5-3)

#### (라) Validator — 컴플라이언스 검증
- Lineage 누락 = 위반
- LLM이 실수해도 시스템이 잡음

### 4-3. STEP 1B 확장 — Planner 프롬프트

옵션 E 자료구조에 따라 Planner LLM 프롬프트에 컨텍스트 3종 추가:

```
현재 Planner 프롬프트:
  dataset_id, flags, candidate_operations
        ↓
STEP 1B 확장 Planner 프롬프트:
  dataset_id, flags, candidate_operations,
  + module_context (1-1 페이지 출력: function 축 + 도메인 지식)
  + stage_context (이전 Stage 결과 요약 — 컨텍스트 누적)
  + constraints (1-2 페이지 입력: max 온도/range 등)
```

**변경 범위**: `repo/agents/planner/planner.py`의 `system` 프롬프트 ~30줄 확장. 함수 시그니처에 `module_context`, `stage_context`, `constraints` 파라미터 추가 (옵션 = 기존 호출 그대로 동작).

### 4-4. MCP → EDA·모델링 컨텍스트 전파 (v3 patch 신규)

사용자 비전의 핵심 흐름: MCP 4단 Agent 가 표준화하면서 발견한 사실 + 각 에이전트의 판단 기록을 Page 5 (EDA) + Page 6 (모델링) LLM 에 컨텍스트로 전달. 이게 누락되면 1층-2층 분리가 깨진 무의미한 파이프라인.

#### 컨텍스트 누적 구조

```
[1-1 Page] 공정 흐름 + 모듈 구성 (pipeline_structure)
        +
[1-2 Page] 데이터·제약 입력 (pipeline_full)
        +
[Page 4 MCP 표준화] Agent 4단 판단 기록
   - Inspector: deterministic_flags + modality_guess + concerns + recommended_next_steps
   - Planner: candidate_operations + ordered with rationale + llm_summary
   - Executor: applied_steps (before/after_stats + lineage_id)
   - Validator: issues + next_action
        ↓
[Context Aggregator (결정론, 신규)]
   - 위 모든 사실을 결정론 알고리즘으로 추출·구조화
   - LLM 없음 (환각 위험 0)
   - 출력: AggregatedContext
        ↓
   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
   │ Page 5 자동 질문    │   │ Page 5 EDA 요약     │   │ Page 6 모델 추천    │
   │ LLM 프롬프트 입력   │   │ LLM 프롬프트 입력   │   │ LLM 프롬프트 입력   │
   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘
```

#### 환각 방어 메커니즘

| 단계 | LLM 역할 | 결정론 역할 | 정합 |
|---|---|---|---|
| MCP 표준화 | 해석·매핑 | 변환·검증 | 헌법 D-13/D-15 |
| Context Aggregation | 없음 | 추출·구조화 | 환각 위험 0 |
| Page 5 자동 질문 | 후보 중 추천 | 후보 생성 | 사전정의 분석 목적 6종 |
| Page 5 EDA 자연어 요약 | 표현 (숫자 그대로) | 통계 계산 | 숫자 인용 강제 |
| Page 6 모델 추천 | 적합도 판단 | 모델 풀 정의 | Module Catalog recommended_models |

#### 자료구조 (spec-1 Part 1-2 (바) 참조)

AggregatedContext = {
  pipeline_structure (1-1 입력),
  pipeline_constraints (1-2 입력),
  key_findings (결정론 추출),
  agent_records (4단 판단 기록),
  user_intent (Page 5 선택 후 추가)
}

구체 명세는 `0_pipeline_ui_spec-1_v5.md` Part 1-2 (바) + Part 1-3 API + Part 1-9-7 검증 참조 (Phase 별 3 분할: spec-1 공통+Page1~3 / spec-2 Page4~6 / spec-3 종합+부록).

### 4-5. LLM의 "사용자에게 의사 묻기" 형태

두 시점에서 발생:

| 시점 | 형태 | 컨텍스트 |
|---|---|---|
| 4단계 (표준화 진행) L2/L3 | "이 작업을 수행하시겠습니까?" 사용자 승인 게이트 (구체 UI 형태는 팀원 디벨롭 방안) | 이미 구현 (토큰 기반) |
| 4단계 (데이터 미업로드 모듈) | "이 모듈에 데이터가 없습니다. 필수일까요?" 알람 | STEP 1B 신규 |
| 5단계 (분석 목적 질문) | "박스 안 모듈이 [PdM + Inspection] 입니다. 어떤 분석을?" | STEP 1B 신규 |

5단계 질문 생성 방식 = 하이브리드:
- 박스 안 모듈로 후보 자동 생성 (결정론)
- LLM이 1~2개 추천 + 사용자 최종 선택

---

## Part 5. 권한 모델 3-tier (가드레일)

### 5-1. 세 등급

| 등급 | 작업 종류 | 자율성 | 가드레일 |
|---|---|---|---|
| **L1 자동** | 메타·스키마·인코딩 감지, 기초 통계 | 즉시 실행 | 입출력 검증만 |
| **L2 제안+승인** | 결측·이상치·피처 생성, 마스킹 정리, 클래스 보정 | 사용자 승인 필요 | 미리보기 + 되돌리기 |
| **L3 차단+백업** | 컬럼 삭제·라벨 재정의 | 명시 승인 + 백업 | 자동 백업 + Lineage 강제 |

### 5-2. `OPERATION_PERMISSION` 매핑 (단일 소스)

`repo/harness/guardrails.py`에 `OPERATION_PERMISSION` dict. 모든 곳이 이 한 곳만 참조.

**주의**: 작업 목록은 `planner_schemas.py` ↔ `guardrails.py` 양쪽 동기화 필수.

### 5-3. 사용자 승인 게이트 (피드백 2 반영)

**기본 동작 (코드 사실)**:
- `POST /api/execute`의 `approved_steps: list[int]` → Executor가 `step.order`와 매칭
- 매칭된 step만 L2/L3 실행
- 매칭 안 된 step → `awaiting_approval` 상태로 멈춤

> **구체 승인 UI 형태에 대한 주의**: 본 문서 v2까지 "1-click 승인"이라는 표현을 사용했으나, 실제 팀원의 디벨롭 방안은 다른 형태일 수 있습니다. 단순 단일 클릭이 아니라:
>
> - 옵션 비교 카드(A/B/C로 처리 방식 선택)
> - 다단계 확인(미리보기 → 확인 → 적용)
> - 권한 등급별 다른 UI 흐름
>
> 등의 가능성이 있습니다. **본 문서는 백엔드 토큰 기반 게이트 동작만 사실로 보고, 프론트엔드 승인 UI의 구체 형태는 팀원 디벨롭 방안을 1차 소스로 두고 추후 검증 후 본 문서에 반영합니다.** "1-click"이라는 단정 표현은 v3 설계 단계에서 제거했습니다 (v5 누적).

---

## Part 6. 용어 정비 — Line / Node 통일 명시

### 6-1. 통일 표기

| 한국어 | 영문 표기 | 이전 표현 (혼란 유발) | 의미 |
|---|---|---|---|
| **라인 (Line)** | `Line` | 사용자 "공정" / 기존 "모듈" | 큰 그룹 (모듈 1/2/3 같은 제품 라인) |
| **공정 노드 (Node)** | `Node` | 사용자 "모듈" / 기존 "공정" / blueprint v1 "Module" | Line 안 세부 (사출성형, CNC 등). 각 Stage 와 1:1 대응 |
| **단계 (Stage)** | `Stage` | (신규) | UI 박스 단위 (한 박스 = 1 Node 고정, 박스 안에 1~3 Module 슬롯). 빈 슬롯은 "없는 것" 처리 (Part 2-6) |
| **모듈 (Module)** | `Module` | (재정의) | Stage 박스 안의 Function 차원 데이터 슬롯 (process/quality/maintenance/reference) |
| **데이터셋 (Dataset)** | `Dataset` | (그대로) | 실제 raw 파일 |

옵션 E 자료구조의 계층:
```
Line (3 그룹)
  └─ Stage (Line 별 ~5~7개)
       └─ Node (각 Stage = 1 Node)
            └─ Module (Node 안 1~3개, Function 차원)
                 └─ Dataset (Module의 실제 raw 파일)
```

### 6-2. 시스템 흐름 표현 정비

| 이전 표현 (혼란 유발) | 통일 표현 |
|---|---|
| 앞단 / 중단 / 뒷단 | 앞단 (Front Stage) / 중간단 (Middle Stage) / 뒷단 (Back Stage) |
| 1층 / 2층 | 1층 = 모달리티 표준화 / 1.5층 = STEP 1B / 2층 = 공장 통합 (그대로 유지) |
| "1-click 승인" | "사용자 승인 게이트" (구체 UI는 팀원 디벨롭 방안 참조) |

### 6-3. L1/L2/L3 vs Function 축 — 매우 중요한 충돌

코드의 L1/L2/L3 (Permission)와 사용자 첨부 `0_data_overview.md`의 L1~L4 (Function 축)은 완전히 다른 차원.

| 약자 | 코드에서의 의미 (Permission 축) | 사용자 문서의 의미 (Function 축) |
|---|---|---|
| **L1** | 권한: 자동 실행 | Function: process 데이터 (공정 최적화) |
| **L2** | 권한: 제안+승인 | Function: quality 데이터 (품질 검사) |
| **L3** | 권한: 차단+백업 | Function: maintenance 데이터 (예지보전) |
| **L4** | (없음) | Function: reference 데이터 |

문서 작성 시 절대 맥락 없는 "L1" 단독 사용 금지. 명시 표기:
- 권한 의미 → "권한 L1 / L2 / L3" 또는 "Perm-L1 / Perm-L2 / Perm-L3"
- Function 의미 → "Function process / quality / maintenance / reference"

---

## Part 7. 3축 메타데이터 모델 (1+2층 통합)

### 7-1. 같은 데이터셋을 3축으로 본다

| 축 | 좌표 | 누가 쓰나 | 현재 상태 |
|---|---|---|---|
| **Modality (Shape)** | timeseries / inspection-image / event-log / order | MCP 코드 라우팅 | 1층 완료 |
| **Domain (Line × Node)** | 사출성형 / CNC / 프레스 / 검사 등 (18개 Node) | 사용자 1-1 페이지 선택 | STEP 1B 진입 |
| **Function (Purpose)** | process / quality / maintenance / reference | LLM 컨텍스트 주입 (1-1 + 5단계) | STEP 1B 진입 |

### 7-2. 3축 매핑 예시

| 데이터셋 | Modality | Line / Node | Function |
|---|---|---|---|
| `L1_press_forming` | event-log (PASS_YN) | Line 2 / 프레스 성형 | process |
| `L1_cnc_lathe_quality` | timeseries (10.4M행) | Line 1 / CNC 절삭 | process |
| `L2_wafer_defect` | inspection-image (300 png) | Line 3 / 반도체 검사 | quality |
| `L3_blower_vibration` | timeseries (1M행 진동) | Line 2 / 회전기 PdM | maintenance |
| `L1_injection_optimize` | timeseries+event (NGmark) | Line 3 / 사출 성형 | process |
| `L4_ict_checker` | event-log (CP949) | Line 3 / ICT 검사 | reference |

### 7-3. 폴더 구조

```
manufacturing-mcp/
  ├── (기존 그대로) agents / backend / data / db / docker-compose.yml
  │                 frontend / harness / mcp-servers / scripts
  │
  ├── catalogs/                      STEP 1B 신규
  │   ├── lines.yaml                   Line × Stage × Node × Module 카탈로그
  │   ├── modules.yaml                 Node 별 도메인 지식 (constraint_keys 등 — typical_ranges 디폴트는 v4 제거)
  │   └── views/
  │       ├── by_function/             Function 축 보기
  │       ├── by_line/                 Line 축 보기
  │       └── by_modality/             Modality 축 (현재 코드 라우팅)
  │
  └── docs/
      ├── (기존) decisions.md / specs/
      └── specs/
          ├── pipeline_ui-1.md       STEP 1B 신규 — Phase 1 (공통 + Page 1~3)
          ├── pipeline_ui-2.md       STEP 1B 신규 — Phase 2 (Page 4~6)
          └── pipeline_ui-3.md       STEP 1B 신규 — Phase 3 (종합 + 부록)
```

---

## Part 8. 2층 설계 청사진 — 옵션 E

### 8-0. 사전정의 카탈로그 + 드래그앤드롭 UI + 컨텍스트 누적 (옵션 E 핵심)

핵심 단순화:
- DAG 그래프 라이브러리 (React Flow) 불필요 — 사전정의 Stage 박스 + 사용자가 드래그앤드롭으로 모듈 배치
- `list of lists` 자료구조 + 사전정의 카탈로그 max 값
- UI는 폼 기반 위저드 6 페이지 (드래그앤드롭 사용, 자유 DAG 그래프는 없음)
- 컨텍스트 누적 = `accumulated_context` dict 메모리 누적

> **시연 vs 자유 사용 정리 (피드백 1, 4 반영)**:
> - 사용자 비전: 드래그앤드롭으로 자유롭게 모듈 배치
> - 시연 시: KAMP 데이터셋 기준 사전정의된 모듈 카탈로그에서 이어붙여 데모
> - 즉 "드래그앤드롭 UI를 사용"하되 "모듈 카탈로그는 KAMP 기준 사전정의 (자유로운 신규 모듈 추가는 STEP 3 이후)"
> - DAG 그래프 라이브러리(React Flow 등)는 불필요. 단순 박스 + 화살표 + 드래그앤드롭만으로 충분.

### 8-1. 페이지 1: Line 선택

| 항목 | 내용 |
|---|---|
| 입력 | 라디오 버튼 3개 (Line 1 / 2 / 3) |
| 출력 | `line_id` |
| 검증 | 1개 선택 강제 |
| API | `GET /api/lines` — 라인 목록 |
| 컨텍스트 흐름 | (없음, 다음 페이지 입력) |

### 8-2. 페이지 2: Pipeline 구성 (1-1) — 앞단

| 항목 | 내용 |
|---|---|
| 입력 | Line의 사전정의 Stage 박스가 표시되고, 모듈 카탈로그(KAMP 기준)에서 드래그앤드롭으로 모듈을 박스에 배치 |
| UI 요소 | 좌측: 모듈 카탈로그 (Node + Function별 모듈 카드)<br>우측: Line의 Stage 박스들 (사전정의)<br>드래그앤드롭: 카탈로그 → Stage 박스<br>박스 안: 추가된 모듈 카드 표시 (function 라벨 + 데이터셋 hint) |
| 검증 | 데이터셋 max 기준 카탈로그 적용 (부록 A) — 매핑되지 않은 슬롯은 list에 등장 안 함 |
| 출력 | `pipeline_structure` (Part 2-3) |
| 컨텍스트 흐름 | LLM만 (Planner의 `module_context` + `stage_context`) |

### 8-3. 페이지 3: 데이터 + 제약 입력 (1-2) — 앞단

| 항목 | 내용 |
|---|---|
| 입력 | 각 Module마다 데이터 파일 업로드 + 제약 폼 |
| UI 요소 | Module 카드 펼치기 → 내부에:<br>- 파일 업로드 (이미지/CSV/Excel) 또는 Data Lake 데이터셋 선택<br>- 제약 폼 (Node의 `constraint_keys` 구조 가이드, 값은 사용자 입력 — v4 결정: typical_ranges 디폴트 제거)<br>- "고급 사용자" 토글 → YAML 직접 편집 옵션 |
| 검증 | 데이터 미업로드도 허용 (LLM 판단으로 처리) |
| 출력 | `pipeline_full` (Part 2-3) |
| 컨텍스트 흐름 | MCP + LLM 양쪽 (MCP의 `constraints` 파라미터 + Planner의 `constraints`) |

### 8-4. 페이지 4: 표준화 진행 — 중간단

| 항목 | 내용 |
|---|---|
| 동작 | Backend `/api/execute_pipeline` 호출, Stage 순서 처리 |
| UI 요소 | Stage 별 / Module 별 진행률 표시:<br>- 진행률 (0~100%)<br>- 발견된 챌린지 (인코딩, 헤더, dtype, 불균형 등)<br>- LLM 해석 (modality_guess + concerns + recommended_next_steps)<br>- L2/L3 작업 사용자 승인 게이트 (구체 UI는 팀원 디벨롭 방안)<br>- 데이터 미업로드 모듈 알람 (LLM 판단) |
| API | `POST /api/execute_pipeline` |
| 컨텍스트 흐름 | 1-1 + 1-2 컨텍스트가 Planner LLM 프롬프트에 누적 주입 |

### 8-5. 페이지 5: 분석 목적 질문 + 전처리 — 뒷단

| 항목 | 내용 |
|---|---|
| 시스템 동작 | Stage 안 모듈 정보로 자동 질문 후보 생성 |
| UI 예시 | "Stage A에는 maintenance (PdM) + quality (Inspection) 데이터가 있습니다.<br>분석 목적은?<br>  [a] PdM으로 예지보전 (maintenance 중심)<br>  [b] Inspection으로 품질 분류 (quality 중심)<br>  [c] 둘을 결합한 통합 진단 (maintenance + quality)<br>  [d] 직접 입력" |
| 사용자 응답 | 1개 선택 또는 자유 입력 → Function 컨텍스트 결정 |
| 출력 | EDA (차트 + 표) + 이상치 처리 결과 + 자연어 요약 |
| 데이터 join | 이 단계에서 사용자 의도 받은 후 join 키 결정 |
| 컨텍스트 흐름 | Function 컨텍스트가 Planner에 주입 → 추가 전처리 단계 생성 |

### 8-6. 페이지 6: 모델링 — 뒷단

| 항목 | 내용 |
|---|---|
| 시스템 추천 | Module Catalog `recommended_models` 기반 후보 모델 표시 |
| 사용자 승인 | 추천 모델 중 선택 또는 직접 지정 |
| 학습/추론 | 로컬 (RTX 3070):<br>- XGBoost / LightGBM / 소형 CNN = 실제 실행<br>- 대형 CNN = 권고만 (실행 없음) |
| 결과 송출 | 지표 (Acc/F1/AUC) + confusion matrix + feature importance + 그래프 |
| Lineage | 학습 결과도 Lineage에 기록 |

### 8-7. 컨텍스트 흐름 다이어그램

```
┌────────────────────────────────────────────────────────────────┐
│ Page 1: Line 선택                                              │
│         ↓ line_id                                              │
├────────────────────────────────────────────────────────────────┤
│ Page 2 (1-1, 앞단): Pipeline 구성                              │
│  사용자: Stage 박스에 모듈 드래그앤드롭 배치                   │
│         ↓ pipeline_structure                                   │
│         (LLM 컨텍스트만)                                       │
├────────────────────────────────────────────────────────────────┤
│ Page 3 (1-2, 앞단): 데이터 + 제약 입력                         │
│  사용자: 파일 업로드 + 제약 폼                                 │
│         ↓ pipeline_full                                        │
│         (MCP + LLM 양쪽)                                       │
├────────────────────────────────────────────────────────────────┤
│ Page 4 (중간단): 표준화 진행                                   │
│  Backend: Stage 순서 처리                                      │
│   ├─ Inspector (MCP 7 도구 + LLM 해석)                         │
│   ├─ Planner (module_context + stage_context + constraints)    │
│   ├─ Executor (결정론 변환 + Lineage)                          │
│   └─ Validator (검증 + 라우팅)                                 │
│         ↓ pipeline_results (Stage 별 요약 누적)                │
├────────────────────────────────────────────────────────────────┤
│ Page 5 (뒷단): 분석 목적 질문 + 전처리                         │
│  시스템: 박스 안 모듈 기반 질문 후보 자동 생성                 │
│  사용자: Function 분류 선택 (또는 직접 입력)                   │
│         ↓ function_axis 컨텍스트                               │
│  Planner: 추가 전처리 단계 생성 → EDA/이상치 결과              │
├────────────────────────────────────────────────────────────────┤
│ Page 6 (뒷단): 모델링                                          │
│  시스템: Module Catalog recommended_models 추천                │
│  사용자: 승인                                                  │
│  로컬 LLM/ML: 학습 + 추론 + 지표                               │
└────────────────────────────────────────────────────────────────┘
```

### 8-8. STEP 1B 작업 분해

| # | 작업 | 산출물 | 위치 |
|---|---|---|---|
| 1 | `catalogs/lines.yaml` 작성 | 3 Line × Stage × Node × Module 카탈로그 (잠정안 부록 A) | `repo/catalogs/` |
| 2 | `catalogs/modules.yaml` 작성 | 18 Node 도메인 지식 (constraint_keys 구조 — v4 결정: typical_ranges 디폴트 없음) | `repo/catalogs/` |
| 3 | Planner 프롬프트 확장 | `module_context` + `stage_context` + `constraints` 파라미터 | `repo/agents/planner/planner.py` |
| 4 | Backend pipeline 엔드포인트 신규 | `/api/execute_pipeline` + `/api/lines` | `repo/backend/main.py` |
| 5 | LLM 데이터 필수성 판단 함수 | `llm_judge_data_necessity()` | `repo/agents/inspector/` 또는 신규 |
| 6 | Validator 검증 4종 강화 | 변환 전후/무결성/회귀/롤백 | `repo/agents/validator/validator.py` 확장 |
| 7 | 의미 그룹화 (우려 1) | `semantic_group` in `list_columns` (규칙 우선) | `repo/mcp-servers/*/tools.py` |
| 8 | Frontend 6 페이지 Mini UI | HTML + React useState + 드래그앤드롭 (HTML5 native or react-dnd) | `repo/frontend/` 확장 |
| 9 | 5단계 자동 질문 후보 생성 | `build_function_question(stage)` | `repo/agents/planner/function_context.py` (신규) |
| 10 | UI 명세서 (3 분할) | 페이지별 화면·API·자료구조 명세 | `0_pipeline_ui_spec-1/2/3.md` (작업 위치) → `repo/docs/specs/pipeline_ui-1/2/3.md` (본진 이식) |

---

## Part 9. 현재 시스템 점검 체크리스트

### 9-1. 1순위 작업: Harness 결과 검증 강화

`docs/decisions.md` 110~118행에 사용자가 직접 명시:

> 현재 "LLM 계획 → 그대로 실행"이고 결과 검증이 비어있음
> 증거: `wafer_defect` EXECUTE 시 `clean_masking`이 `width/height`에 중복 제안

구현할 4가지:
- [ ] **변환 전후 비교 검증**: dtype 정말 바뀌었나, before/after 측정값 검증
- [ ] **계획 무결성 검증**: 중복 작업 감지 (위 width/height 중복 케이스)
- [ ] **회귀 검증**: 전처리가 데이터를 망치지 않았나 (행 수 급변·통계 이상)
- [ ] **검증 실패 라우팅**: 롤백 / 사람 재검토 / 계획 재생성

### 9-2. STEP 1B 신규 작업 검증

위 Part 8-8의 작업 10개 완료 시점 검증:
- [ ] `catalogs/lines.yaml` 3 Line 모두 정의
- [ ] `/api/lines` 200 응답 + 카탈로그 반환
- [ ] `/api/execute_pipeline` 더미 pipeline으로 동작
- [ ] Planner LLM 프롬프트에 `module_context` 주입 확인
- [ ] Planner LLM 프롬프트에 `stage_context` 누적 확인
- [ ] 데이터 미업로드 모듈 LLM 판단 알람 동작
- [ ] Validator 검증 4종 동작 + 회귀 검증으로 width/height 중복 자동 탐지
- [ ] Mini UI 6 페이지 전부 라우팅 동작 (드래그앤드롭 동작 검증 포함)
- [ ] 5단계 자동 질문 후보 생성 확인

### 9-3. Inspector 검증 (specs/inspector.md, 기존)

- [ ] `order_cp949` 인스펙트 시 flags에 "non-utf8 encoding" 잡힘
- [ ] `mold_anomaly_headerless` 인스펙트 시 "headerless" 잡힘
- [ ] `cnc_lathe_masked` 인스펙트 시 해당 컬럼 `mixed_dtype_suspected=true`
- [ ] LLM이 `modality_guess="timeseries"` 반환 (e4b/26b 모두)
- [ ] 대시보드 표시

### 9-4. 4 모달리티 동작 확인

- [ ] `timeseries`: `mct_tool_manage_clean` → inspect → plan → execute (L1만)
- [ ] `timeseries`: `cnc_lathe_masked` → plan에 `clean_masking` L2 후보 → 승인 → dtype 변환
- [ ] `inspection-image`: `wafer_defect` → modality_guess 정확 → mode/size 통일 권고
- [ ] `event-log`: 더미 → balance_classes L2 후보 → 승인 → 보정 전략
- [ ] `order`: `order_cp949` → 인코딩 자동 감지 → utf-8 정규화

### 9-5. API 엔드포인트

- [ ] `GET /api/health` — 200, llm + mcp_timeseries 응답
- [ ] `GET /api/modalities` — 4 서버 health
- [ ] `GET /api/datasets?modality=event-log` — 더미 파일 목록
- [ ] `GET /api/models` — Ollama 설치 모델
- [ ] `GET /api/inspect` — DataProfile
- [ ] `GET /api/plan` — PreprocessingPlan
- [ ] `POST /api/execute` (approved_steps=[]) — L2/L3 모두 `awaiting_approval`
- [ ] `POST /api/execute` (approved_steps=[1,2,3]) — 실제 변환 + lineage 기록
- [ ] `GET /api/lines` STEP 1B 신규
- [ ] `POST /api/execute_pipeline` STEP 1B 신규

### 9-6. 인프라

- [ ] `docker compose up -d --build` 성공
- [ ] `ollama pull gemma4:e4b` 완료
- [ ] `ollama pull gemma4:26b` 완료 (메모리 분산 동작 검증)
- [ ] PostgreSQL `metadata` / `lineage` / `agent_logs` 스키마 생성됨
- [ ] 4 MCP 서버 컨테이너 전부 up
- [ ] frontend 대시보드 동작

### 9-7. 컴플라이언스

- [ ] 모든 `done` step에 `lineage_id` 존재 (Validator 통과)
- [ ] 변환 전 백업 parquet 파일 존재 (`data/processed/<id>__backup.parquet`)

---

## Part 10. 위험 요소 + 미해결 영역

### 10-1. 진단 (정직 버전)

| 위험 | 내용 | 완화 |
|---|---|---|
| 시간 비용 가설 미실측 | "전처리에 시간이 많이 든다" 가설의 분포 (a)shape / (b)이해 / (c)의사결정 미측정 | SI 엔지니어 인터뷰 + 자기 데이터 측정 |
| 도메인 지식 사전 구축 | Module Catalog의 `domain_knowledge`가 비면 시스템은 일반 ETL 회귀 | 18개 핵심 Node 수동 입력 → 점진 확장 |
| Function 축 정의 모호 | 사용자 문서의 L1~L4 vs 코드의 L1~L3 권한 — 용어 충돌 | 본 핸드오버 Part 6 표기 분리 규칙 |
| 단일 사용자 노트북 의존 | Module Catalog 작성자가 사용자 1명에 집중 | 점진 위임 + 양식화 |
| Mini UI 6 페이지 통합 복잡도 | 페이지 간 상태 관리 (useState 또는 zustand 등) + 드래그앤드롭 라이브러리 선택 | React useState + HTML5 native DnD (또는 react-dnd 경량) |
| KAMP 외 사용자 자기 실데이터 | 사용자 공장이 KAMP 외 공정이면? | "라인 추가해도 MCP 안 늘어남" 메시지 유효, 단 도메인 지식은 사용자 입력 필요 |
| 모델 추천 책임 | 시스템 추천 모델이 결과 나쁘면? | "권고"임을 명시. 최종 채택은 사람. Lineage로 근거 추적 |
| Harness 결과 검증 부재 (현 시점) | wafer_defect 중복 제안 같은 버그 | §9-1의 1순위 작업으로 해결 예정 |

### 10-2. "AI가 코드를 짠다" 메시지의 정직 범위

- 가능: LLM이 Inspector의 해석 생성 (modality_guess / concerns)
- 가능: LLM이 Planner의 작업 순서·이유 생성
- 가능: LLM이 5단계 분석 목적 질문 후보 추천
- 불가: LLM이 작업 후보 자체를 만드는 것 (가드레일이 후보 추림)
- 불가: LLM이 실제 데이터 변환 (Executor가 결정론)
- 불가: LLM이 권한 등급 결정

정직: "AI가 코드를 짠다" = "AI가 전처리 계획을 짠다 + 결정론적 안전망이 잡는다".

---

## Part 11. 로드맵

### 11-1. Sprint 단위

| Sprint | 목표 | 산출물 |
|---|---|---|
| 현재 (1층 완료) | 모달리티 표준화 4종 + 4단 Agent | repo 현 상태 |
| STEP 1A (오류 수정) | 1층 코드 오류 수정 (modality_guess, width/height 중복) | 기존 코드 patch |
| STEP 1B | Harness 검증 + 의미 그룹화 + Module Catalog + Planner 확장 + Mini UI 6 페이지 | `catalogs/` + `pipeline_ui-1/2/3.md` (Phase 별 분할) + `frontend/step1_line ~ step6_modeling/` 확장 |
| STEP 2 | 우려 2 옵션 카드 (불균형 보정 등 L2만, 결정론 미리보기) | Planner 출력 확장 |
| STEP 3 | 자유 DAG UI(React Flow 도입 검토) + 공장 통합 + ML/RAG | Frontend 전면 개편 |

### 11-2. 다음 결정 지점

| 결정 | 권장 |
|---|---|
| Harness 검증 강화 범위 | 4종 전부 (사용자 본인 예약대로) |
| Module Catalog 초기 Node 수 | 18개 (부록 A 잠정안) |
| Function 축 표기 | `process/quality/maintenance/reference` (소문자 영문) |
| Mini UI 기술 스택 | HTML + React useState + HTML5 native DnD (또는 react-dnd 경량 라이브러리) |
| 모달리티 5번째 추가 | 추가 안 함 ("MCP 안 늘어남" 메시지 보호) |
| 사용자 승인 UI 구체 형태 | 팀원 디벨롭 방안 1차 소스 → 추후 본 문서에 반영 |

---

## Part 12. 팀원 협업 가이드

### 12-1. 어디서부터 읽나

1. 이 문서 (`0_project_blueprint_v5.md`) — 전체 그림
2. `repo/CLAUDE.md` — 설계 헌법, 절대 규칙
3. `repo/docs/decisions.md` — 시간순 결정 이력
4. `repo/docs/specs/<agent>.md` — 각 Agent 명세
5. `0_pipeline_ui_spec-1_v5.md` / `-2.md` / `-3.md` — STEP 1B UI 명세 (Phase 별 3 분할, 작업 위치 / 본진 이식 시 `repo/docs/specs/pipeline_ui-1/2/3.md`)
6. 코드 (`repo/agents/`, `repo/mcp-servers/`)

### 12-2. 충돌 시 우선순위

```
CLAUDE.md > 본 핸드오버 > decisions.md > specs/*.md > 코드 주석 > 코드
```

### 12-3. 새 결정은 어디에 기록?

- 작은 결정 (코드 패치) → 코드 주석 + 커밋 메시지
- 큰 결정 (설계 변경) → `repo/docs/decisions.md`에 시간순 추가
- 새 절대 규칙 → `repo/CLAUDE.md` 수정 (신중)
- 본 핸드오버 갱신 = Snapshot 시점 변경 시 (알파 진입 후 첫 변경부터 v6 시작 — `0_CHANGELOG_v5.md` 정책)

### 12-4. 작업 분담 후보

| 역할 | 1순위 작업 |
|---|---|
| 백엔드 개발자 | Harness 결과 검증 강화 (§9-1) + Planner 프롬프트 확장 |
| AI/LLM 엔지니어 | Function Context Injector + 5단계 질문 후보 생성 |
| 도메인 전문가 | Module Catalog 18개 Node 도메인 지식 |
| 프론트엔드 | Mini UI 6 페이지 (드래그앤드롭 포함, 라이브러리 경량) |
| DBA / SRE | PostgreSQL Lineage 이전 (인메모리 → DB) |

---

## Part 13. AI 컨텍스트 사용 가이드

### 13-1. 새 대화 시작 시 1차 컨텍스트

다음 3개 파일을 묶어서 컨텍스트로:
1. `0_project_blueprint_v5.md` (본 문서, v5)
2. `repo/CLAUDE.md`
3. `repo/docs/decisions.md`

추가:
- 코드 작업 시 → `repo/docs/specs/<해당 Agent>.md` + 해당 코드 파일
- LLM 통합 작업 시 → `repo/backend/llm.py` + `repo/agents/inspector/inspector.py`
- STEP 1B 작업 시 → `0_pipeline_ui_spec-1/2/3.md` (해당 Phase) + `0_variable_index_v5.md` + `0_CHANGELOG_v5.md` + `catalogs/lines.yaml`

### 13-2. AI가 착각하기 쉬운 부분

- L1/L2/L3 — 코드의 권한 등급 vs 사용자 문서의 Function 축. 맥락 명시 필수
- 1층 vs 2층 — 현재 동작은 1층. 사용자 비전(드래그앤드롭)은 2층의 일부. STEP 1B는 그 사이 (1.5층)
- 모달리티는 Shape 축 — 공정·목적과 직교
- MCP 서버는 4개로 고정 — 5번째 추가 금지 ("라인 추가해도 안 늘어남" 메시지 보호)
- 외부 API 호출 절대 금지 — Claude/GPT/Gemini API 호출 코드 제안 금지
- Line / Node / Stage / Module / Dataset 용어 — Part 6-1의 표기 엄수
- 1-1 vs 1-2 페이지 분리 — LLM 컨텍스트만 vs MCP+LLM 양쪽
- 드래그앤드롭 UI는 사용 — 다만 DAG 그래프 라이브러리는 불필요 (단순 박스 + 화살표)
- 사용자 승인 게이트의 구체 UI 형태는 팀원 디벨롭 방안 1차 소스

### 13-3. AI가 주관적 판단하면 안 되는 영역

- 작업 후보 자체를 새로 만들기 금지 (가드레일 `OPERATION_PERMISSION` 외 작업)
- 권한 등급 변경 금지 (LLM이 L2 → L1로 임의 강등 등)
- Lineage 기록 생략 금지
- 외부 데이터 인용 금지 (KAMP PDF 외부 모델 지식 등 — 컨텍스트 외 추론)

- 가능: 후보 작업 순서·이유 다듬기 (Planner 패턴)
- 가능: DataProfile의 해석 (Inspector 패턴 — modality_guess / concerns)
- 가능: 사용자에게 질문 생성 ("이 데이터를 quality 목적으로 보시나요?")
- 가능: 데이터 미업로드 모듈의 필수성 판단

---

## 부록 A. KAMP 노드 카탈로그 잠정 매핑 (lines.yaml v0.1 초안)

> **사용자 검토 필요**. 노드명/모듈 수/Function 분류는 1_data_summary.txt 기준 추정.

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
        - { function: maintenance, hint_dataset: "L3_mold_anomaly" }
    - node_id: cnc_cutting
      display_name: "CNC 절삭"
      max_modules: 2
      available_modules:
        - { function: process,     hint_dataset: "L1_cnc_lathe_quality" }
        - { function: maintenance, hint_dataset: "L3_cnc_roughing" }
    - node_id: mct_machining
      display_name: "MCT 가공"
      max_modules: 3
      available_modules:
        - { function: process,     hint_dataset: "L1_mct_tool_manage" }
        - { function: process,     hint_dataset: "L1_mct_tool_improve" }
        - { function: maintenance, hint_dataset: "L3_mct_condition_inspect" }
    - node_id: precision_inspect
      display_name: "정밀 가공·치수 검사"
      max_modules: 2
      available_modules:
        - { function: quality,     hint_dataset: "L2_cnc_load_dimension" }
        - { function: maintenance, hint_dataset: "L3_precision_machine" }
    - node_id: surface_inspect
      display_name: "표면 검사"
      max_modules: 1
      available_modules:
        - { function: quality, hint_dataset: "L2_inspection_image" }
    - node_id: pdm
      display_name: "PdM 설비"
      max_modules: 3
      available_modules:
        - { function: maintenance, hint_dataset: "L3_rotary_drill" }
        - { function: maintenance, hint_dataset: "L3_solenoid_roughing" }
        - { function: maintenance, hint_dataset: "L3_guideloader_drill" }

- line_id: module_2_forming_joining
  display_name: "성형·접합·표면처리·회전기 라인"
  max_stages: 5
  stages:
    - node_id: press_forming
      display_name: "프레스 성형"
      max_modules: 2
      available_modules:
        - { function: process, hint_dataset: "L1_press_forming" }
        - { function: quality, hint_dataset: "L2_press_aluminum" }
    - node_id: welding
      display_name: "용접"
      max_modules: 2
      available_modules:
        - { function: process, hint_dataset: "L1_welding_auto" }
        - { function: process, hint_dataset: "L1_welding_condition" }
    - node_id: welding_inspect
      display_name: "용접 검사"
      max_modules: 2
      available_modules:
        - { function: quality, hint_dataset: "L2_welding_bead" }
        - { function: quality, hint_dataset: "L2_welding_electrode" }
    - node_id: surface_treatment
      display_name: "표면 처리·테이핑"
      max_modules: 1
      available_modules:
        - { function: quality, hint_dataset: "L2_vision_taping" }
    - node_id: rotary_pdm
      display_name: "회전기 PdM"
      max_modules: 2
      available_modules:
        - { function: maintenance, hint_dataset: "L3_blower_vibration" }
        - { function: maintenance, hint_dataset: "L3_elevator_vibration" }

- line_id: module_3_polymer_electronic
  display_name: "폴리머 성형·전자 검사·진동 신호 라인"
  max_stages: 7
  stages:
    - node_id: order_planning
      display_name: "주문 계획"
      max_modules: 1
      available_modules:
        - { function: reference, hint_dataset: "order_cp949" }
    - node_id: injection_molding
      display_name: "사출 성형"
      max_modules: 3
      available_modules:
        - { function: process, hint_dataset: "L1_injection_optimize" }
        - { function: process, hint_dataset: "L1_injection_production" }
        - { function: process, hint_dataset: "L1_cnc_machine_optimize" }
    - node_id: extrusion
      display_name: "압출"
      max_modules: 1
      available_modules:
        - { function: maintenance, hint_dataset: "L3_extrusion_pdm" }
    - node_id: precision_parts
      display_name: "정밀 부품"
      max_modules: 1
      available_modules:
        - { function: maintenance, hint_dataset: "L3_vacuum_pump" }
    - node_id: semiconductor_inspect
      display_name: "반도체 검사"
      max_modules: 2
      available_modules:
        - { function: quality, hint_dataset: "L2_auto_console_detect" }
        - { function: quality, hint_dataset: "L2_wafer_defect" }
    - node_id: ict_inspection
      display_name: "ICT 검사"
      max_modules: 2
      available_modules:
        - { function: reference, hint_dataset: "L4_ict_checker" }
        - { function: reference, hint_dataset: "L4_ict_inspection" }
    - node_id: vibration_simulation
      display_name: "진동 시뮬"
      max_modules: 2
      available_modules:
        - { function: maintenance, hint_dataset: "L3_vibration_fault_sim" }
        - { function: maintenance, hint_dataset: "L3_vibration_fault_sim2" }
```

요약: Line 3개, Node 합 18개, Module(슬롯) 합 34개.

---

## 부록 B. 분석 목적 ↔ Function 매핑

| 사용자가 보는 분석 목적 (5단계 UI 선택지) | 내부 Function 축 | 비고 |
|---|---|---|
| 이상 탐지 (Anomaly Detection) | `maintenance` (주) + `quality` (부) | 시계열 PdM이면 maintenance, 양·불 라벨이면 quality |
| 품질 예측·분류 (Quality Classification) | `quality` | PASS_YN, 결함 분류 |
| 공정 최적화 (Process Optimization) | `process` | 사이클 타임, 다변수 회귀 |
| 예지보전 (Predictive Maintenance) | `maintenance` | 진동·전류 FFT, 베어링 수명 |
| 생산량/수요 예측 (Demand Forecasting) | `order` (모달리티) + `reference` (Function) | 주문량 시계열 |
| 통계·SPC 분석 (Statistical Comparison) | `reference` | ICT 검사 결과 통계 |
| 기타 / 직접 입력 | `custom` | LLM이 자유 텍스트로 받아 후속 처리 |

---

## 부록 C. 4단 Agentic Flow 시퀀스 (옵션 E pipeline 포함)

```
사용자 (브라우저)
   │ Page 2 (1-1): 사용자가 Pipeline 구성 (드래그앤드롭)
   │ Page 3 (1-2): 데이터 + 제약 입력
   │ POST /api/execute_pipeline { pipeline_full }
   ▼
Backend (FastAPI)
   │
   │ for stage in pipeline_full.stages:
   │   ├── 데이터 미업로드 체크 → llm_judge_data_necessity()
   │   │
   │   ├── for module in stage.modules with data:
   │   │   │
   │   │   ├──▶ Inspector.inspect(data_path, modality, constraints)
   │   │   │      ├──▶ MCP <modality>.list_columns / get_schema / sample / detect_encoding
   │   │   │      ├── 결정론 flags 계산
   │   │   │      └──▶ LLM.generate(요약, fmt_json=True)
   │   │   │            → modality_guess / concerns / recommended_next_steps
   │   │   │      ◀── DataProfile
   │   │   │
   │   │   ├──▶ Planner.plan(profile, module_context, stage_context, constraints)
   │   │   │      ├── 규칙: candidate_operations 추리기
   │   │   │      └──▶ LLM.generate(candidates + 1-1 + 1-2 + 누적 컨텍스트, fmt_json=True)
   │   │   │            → ordered (순서·이유만)
   │   │   │      ◀── PreprocessingPlan
   │   │   │
   │   │   ├──▶ Executor.execute(plan, approval_tokens, modality)
   │   │   │      ├── parquet 백업
   │   │   │      └── for each step:
   │   │   │            ├── 권한 게이트 (사용자 승인 토큰 체크)
   │   │   │            ├── 결정론 변환
   │   │   │            └──▶ Harness.lineage.record(...)
   │   │   │      ◀── ExecutionResult
   │   │   │
   │   │   └──▶ Validator.validate(execution)
   │   │          └── lineage / 중복 / 회귀 검증
   │   │          ◀── ValidationReport
   │   │
   │   └── accumulated_context.append(stage_results)
   │
   └── return { pipeline_results }
   ▼
사용자: Page 4 결과 확인 → Page 5 분석 목적 선택 → Page 6 모델링
```

---

## 부록 D. 8 챌린지 ↔ 더미 데이터 매핑

| 챌린지 | 모달리티 | 더미 파일 | 의도 |
|---|---|---|---|
| 1. 인코딩 (CP949) | order | `order_cp949.csv` | utf-8 디폴트 UnicodeDecodeError |
| 2. 헤더 없음 | timeseries | `mold_anomaly_headerless.csv` | `header=None` 필요 |
| 3. dtype 혼재 | timeseries | `cnc_lathe_masked.csv` | `*`, `**`, `***` 마스킹 8% |
| 4. 데이터 규모 | (전체) | 184행 ~ 1M+ 행 더미 | chunking·polars 분기 |
| 5. 이미지 라벨 6종 | inspection-image | wafer/welding/press | 폴더명/.txt 동명/사이드 CSV |
| 6. 클래스 불균형 | timeseries / event-log | `press_imbalance.csv` (2.85%) | One-class / class_weight |
| 7. PK / LoT 키 | event-log | (멀티시트 더미) | LOT_NO outer merge |
| 8. 멀티시트 xlsx | event-log | (더미 xlsx) | sheets 통합 |

---

## 부록 E. 용어집

| 용어 | 정의 |
|---|---|
| MCP | Model Context Protocol — 본 프로젝트에서는 모달리티별 도구 서버 |
| Agentic Flow | 4단 Agent 파이프라인 (Inspector → Planner → Executor → Validator) |
| Line | 큰 그룹 — 모듈 1/2/3 (금속/성형/폴리머·전자) |
| Stage | UI 박스 단위 — 한 박스 = 1 Node 고정, 박스 안에 1~3 Module 슬롯 |
| Node | 공정 노드 — Stage 와 1:1 대응 (사출성형, CNC 등). Stage 박스 하나 = Node 하나 |
| Module | Function 차원 데이터 슬롯 — Stage 박스 안 1~3개 (process/quality/maintenance/reference). 빈 슬롯은 처음부터 없는 것 처리 |
| Dataset | 실제 raw 파일 |
| Modality (모달리티) | 데이터의 형태 축. 4종 |
| Function (Purpose) | 데이터의 목적 축. process / quality / maintenance / reference |
| Permission (L1/L2/L3) | 코드의 권한 등급. Function의 L1~L4와 완전히 다른 차원 |
| Lineage | 변환 체인 — 모든 전처리 단계의 what/when/by-whom 기록 |
| DataProfile | Inspector 출력 객체 |
| PreprocessingPlan | Planner 출력 |
| OPERATION_PERMISSION | `repo/harness/guardrails.py`의 작업→권한 매핑 dict |
| approval_token | L2/L3 작업 승인 토큰 |
| 1층 | 모달리티 표준화 — 목적 무관 (현재) |
| STEP 1B (1.5층) | Harness 검증 + Module Catalog + Planner 확장 + Mini UI 6 페이지 |
| 2층 | 목적 지향 통합 + ML/RAG (STEP 3) |
| 8 챌린지 | 인코딩/헤더/dtype/규모/이미지라벨/불균형/PK/멀티시트 |
| 옵션 E | 사전정의 카탈로그 + 드래그앤드롭 UI + 컨텍스트 누적 — DAG 라이브러리 없이 list of lists |
| 앞단 (Front Stage) | Pipeline 구성 + 데이터·제약 입력 (Page 1~3) |
| 중간단 (Middle Stage) | MCP 표준화 진행 (Page 4) |
| 뒷단 (Back Stage) | 분석 목적 + 모델링 (Page 5~6) |
| 1-1 페이지 | Pipeline 구성 페이지 (LLM 컨텍스트만 전달) |
| 1-2 페이지 | 데이터 + 제약 입력 페이지 (MCP + LLM 양쪽 전달) |
| stage_context | 이전 Stage 결과 요약 누적 (Planner LLM 프롬프트 입력) |
| module_context | 현재 Module의 function 축 + 도메인 지식 (Planner LLM 프롬프트 입력) |

---

## 부록 F. 추가 정보 요청 항목 (v6 갱신 시)

핸드오버 v6 (알파 진입 후 — Harness 검증 강화 + STEP 1B 완료 시점) 갱신 시:

- [ ] Harness 검증 4종 구현 결과 + 발견 버그 목록
- [ ] Module Catalog v0.1 — 18개 Node 도메인 지식 확정
- [ ] Function 축 운영 정의 (각 4가지의 구체 판단 기준 사례)
- [ ] Mini UI 6 페이지 동작 검증 결과 (드래그앤드롭 라이브러리 결정 포함)
- [ ] `/api/execute_pipeline` 더미·실데이터 동작 비교
- [ ] 5단계 자동 질문 후보 생성 정확도
- [ ] 시간 비용 가설 실측 결과 (a)shape vs (b)이해 vs (c)의사결정 비중
- [ ] PaintGuard DevOps 패턴 이식 (어떤 부분 채택?)
- [ ] SI 영업 메시지 최종 카피 (정직 버전 확정)
- [ ] 데모 시연 시간 분배 (3분/7분/15분 시나리오)
- [ ] **사용자 승인 게이트의 구체 UI 형태** (팀원 디벨롭 방안 반영)
- [ ] **Part 3-2-1의 V1~V7 검증 결과** (4단 Agentic Flow 사용자 확인)

---

## 마무리

> 1층(모달리티 표준화)이 완성되어 동작 중이며, 사용자 비전(6단계 페이지 + 1-1/1-2 분리 + 사전정의 카탈로그 + 드래그앤드롭 + 컨텍스트 누적)은 옵션 E로 STEP 1B 안에 코드 거의 변경 없이 흡수 가능합니다. DAG 그래프 라이브러리(React Flow) 같은 무거운 의존성 없이 list of lists 자료구조 + 단순 드래그앤드롭 UI + 폼만으로 사용자 비전 100% 달성.

다음 갱신: 알파 진입 후 (Harness 검증 강화 + STEP 1B 완료 시점) v6.

---

**작성**: 2026-05-27 v5 (Claude Opus 4.7, byeonggab89 본진 코드 직접 확인 + 사용자 6단계 비전 + 옵션 E 합의 + 7가지 피드백 반영 + 산출 7 파일 v5 통일)

**검수 요청**:
- 부록 A의 KAMP Node 매핑 → 사용자 도메인 인지 기준 검토
- Part 3-2-1의 V1~V7 검증 항목 → 사용자/팀원 협업으로 의도 확인
- Part 5-3의 사용자 승인 게이트 구체 UI → 팀원 디벨롭 방안 1차 소스로 추가 보강

**라이선스/공유**: 내부 전용. 외부 공유 시 보안 노출 제한 항목 추가 마스킹 필요시 별도 검토.
