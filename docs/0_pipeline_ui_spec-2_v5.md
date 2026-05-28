# pipeline_ui_spec-2_v5 — Phase 2 (페이지 4~6, 중간단 + 뒷단, v5)

> **목적**: STEP 1B UI 구현 명세 Phase 2. Page 4 (표준화 진행, 중간단) + Page 5 (분석 목적, 뒷단) + Page 6 (모델링, 뒷단).
>
> **분할 정보**:
> - `0_pipeline_ui_spec-1_v5.md` = Phase 1 (구조 + 공통 + Page 1~3)
> - **spec-2 (본 파일)** = Phase 2 (Page 4~6)
> - `0_pipeline_ui_spec-3_v5.md` = Phase 3 (종합 + 부록)
>
> **Snapshot**: 2026-05-27 v5 (분할판)
>
> **상위 문서**: `0_project_blueprint_v5.md` / `0_CHANGELOG_v5.md` / `0_variable_index_v5.md`
>
> **단계 진입 시 필독 (3 파일)**: 청사진 + CHANGELOG + 본 파일
>
> **이전 Phase**: `0_pipeline_ui_spec-1_v5.md` (Phase 1, 공통 + Page 1~3)
> **다음 Phase**: `0_pipeline_ui_spec-3_v5.md` (Phase 3, 종합)

---

## 이전 단계 검증 (Phase 1 → Phase 2 인수)

### 본 명세 작업 진입 전 필독·검증 항목

- [ ] `0_pipeline_ui_spec-1_v5.md` 숙독 완료 (Part 0 + Part 1 (1-1~1-9) + Part 2~4)
- [ ] `0_CHANGELOG_v5.md` 알파 진입 후 기록 확인 (v5 시점은 비어 있음)
- [ ] `0_variable_index_v5.md` 변수 목차 인지 (특히 §6 OPERATION_PERMISSION / §8 자료구조 / §9 API / §12 환각 방어)
- [ ] Phase 1 의 결정 사항 모두 인지 (아래)

### Phase 1 에서 결정·합의된 사항 (본 Phase 2 가 그대로 적용)

| 항목 | 위치 | 핵심 |
|---|---|---|
| 자료구조 8종 | spec-1 Part 1-2 | LineCatalog / PipelineStructure / PipelineFull / **PipelineResults** / PipelineStatus / AnalysisQuestion / DataLakeEntry / **AggregatedContext** |
| API 25 엔드포인트 | spec-3 Part 9-1 (종합 표) | Phase 2 의 Page 4/5/6 API 흐름 정합 |
| 환각 방어 메커니즘 | spec-1 Part 1-7 + 1-9-7 | 카드 (결정론) + 자연어 (매핑+재확인+confidence<0.7 거부) |
| Data Lake 정책 | spec-1 Part 1-6 | 통합 인터페이스 (Phase 2 의 Page 5 자동 분석 시 활용) |
| LLM 가치 5 영역 | spec-1 Part 1-8 | Phase 2 의 Page 4 = ⑤ / Page 5 = ③④ / Page 6 = AggregatedContext 활용 |
| 검증 체계 알파/베타/운영 | spec-1 Part 1-9-9 | Phase 2 의 검증 항목 = 알파에서 발견·갱신 |

### Phase 1 에서 누적된 설계 결정 (본 Phase 2 가 그대로 적용)

> `0_CHANGELOG_v5.md` 는 알파 진입 후 기록 시작 (현재 비어 있음). 본 섹션은 v5 설계 단계 결정의 요약.

- 본진 코드 확인 결과 적용: OPERATION_PERMISSION 12종 + step_key 안정 식별자 + MCP POST 2개
- Context Aggregator: Page 4 완료 시 자동 트리거, agent_records 보존
- Part 1-9-9 알파/베타/운영 검증: Phase 2 각 페이지 끝에 알파 검증 체크리스트 포함

### Phase 2 작업 시 적용할 사용자 결정 3개

| 결정 | 적용 위치 |
|---|---|
| Page 4 진행률: SSE 기본 + 폴링 폴백 | Part 5-2 |
| Page 4 → 5 이동: 사용자 수동 클릭 | Part 5-9 |
| Page 6 결과: 지표+Confusion+Importance 기본 / 풀 대시보드 확장 | Part 7-6, 7-7 |

### 외부 AI 검증 결과 (Page 5 EDA 차트)

`~/.claude/projects/.../memory/project_eda_charts.md` 메모리에 보존됨. Part 6-4 (EDA 차트 매핑) 에 그대로 흡수.

위 검증 통과 후 본 명세 진입.

---

## Part 5. 페이지 4: 표준화 진행 (중간단)

### 5-1. URL / 화면 mockup

```
URL: /pipeline/run?session=<uuid>
페이지 제목: "표준화 진행"

┌─────────────────────────────────────────────────────────────────────────┐
│ Line 1 / 6개 Stage                                      [모델: e4b ▼]    │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─ 좌측: Stage 진행 ──────┐ ┌─ 우측: 상세 (선택된 Stage/Module) ────┐  │
│ │                          │ │                                         │  │
│ │ Stage 0: 1차 성형  ✓     │ │ Stage 0 / [maintenance] L3_mold_condition│ │
│ │   [maintenance] ✓ 4/4 done│ │                                        │  │
│ │   [maintenance] ⏳ 2/4   │ │ Inspector 결과:                         │  │
│ │   ░░░░░ 50%              │ │   모달리티: timeseries                  │  │
│ │                          │ │   인코딩: utf-8-sig                     │  │
│ │ Stage 1: CNC 절삭 ⏳     │ │   행/열: 1323 × 71                      │  │
│ │   대기 중...             │ │   결정론 flags: []                       │  │
│ │   ░ 0%                   │ │   LLM 해석:                             │  │
│ │                          │ │     modality_guess: timeseries          │  │
│ │ Stage 2: MCT 가공        │ │     concerns: ["INJ_NO 단조 증가 미보장"]│  │
│ │   대기 중...             │ │                                         │  │
│ │                          │ │ ─── 작업 승인 (L2) ───                   │  │
│ │ Stage 3~5: ...           │ │ ┌─ 카드 1 ───────────────────────────┐ │  │
│ │                          │ │ │ clean_masking / target: CV_005      │ │  │
│ │ ⚠️ Stage 0 / [maint.]    │ │ │ 통계 미리보기:                       │ │  │
│ │   데이터 미업로드 알람    │ │ │   object → float64                  │ │  │
│ │   "예지보전 필수 데이터" │ │ │   NaN 0 → 8% (240/3000)             │ │  │
│ │                          │ │ │ [거부]              [승인]           │ │  │
│ │                          │ │ └────────────────────────────────────┘ │  │
│ │                          │ │ [+ 자연어로 수정]                       │  │
│ └──────────────────────────┘ └─────────────────────────────────────────┘  │
│                                                                          │
│ 전체 진행: ░░░░░░░░░ 35% (12/35 step)         [← 이전]   [다음 →]      │
│                                                ↑ 모든 Stage 완료 후 활성  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5-2. 진행률 갱신 메커니즘

권장: SSE (Server-Sent Events) 기본 + 폴링 폴백.

| 방식 | 사용 케이스 | 구현 |
|---|---|---|
| SSE (권장) | 일반 환경 — 실시간 갱신 필요 | `GET /api/pipeline/{session_id}/stream` (EventSource) |
| 폴링 (폴백) | SSE 호환 안 되거나 부하 큰 환경 | `GET /api/pipeline/{session_id}/status` (1초 주기) |

> 구현 주체 결정: 본 명세는 SSE를 1차 권장으로 명시하되, 작업량/효율을 본 후 폴링 방식으로 폴백 가능. 양쪽 모두 같은 응답 자료구조(`PipelineStatus`)를 사용해 클라이언트 코드 교체 비용 최소화.

#### `PipelineStatus` 자료구조

```python
{
  "session_id": str,
  "overall_progress": float,
  "current_stage_order": int,
  "current_module_index": int | None,
  "stages": [
    {
      "stage_order": int,
      "node_id": str,
      "status": "pending"|"running"|"done"|"failed",
      "modules": [
        {
          "function": str,
          "dataset_role": str,
          "status": "pending"|"inspecting"|"planning"|"executing"|"validating"|"done"|"failed"|"awaiting_approval",
          "progress": float,
          "deterministic_flags": list[str],
          "llm_interpretation": dict,
          "pending_approvals": [
            {
              "step_key": str,
              "operation": str,
              "target_column": str | None,
              "permission_level": "L2"|"L3",
              "before_stats": dict,
              "predicted_after_stats": dict,
              "direction_text": str
            }
          ],
          "data_warning": dict | None
        }
      ]
    }
  ]
}
```

### 5-3. 챌린지 발견 표시

Inspector `deterministic_flags` 를 실시간 누적 표시 (좌측 패널 배지):

| Flag | 배지 | 색상 |
|---|---|---|
| `non-utf8 encoding` | "CP949" | 주황 |
| `headerless` | "헤더없음" | 빨강 |
| `mixed dtype in '<col>'` | "혼재" | 노랑 |
| `imbalance_suspected` | "불균형 X%" | 빨강 |
| `multi_sheet_merged` | "멀티시트" | 파랑 |

클릭 시 우측 상세에 해당 컬럼 정보.

### 5-4. LLM 해석 표시

```
┌─ LLM 해석 (gemma4:e4b, 200ms) ──────────────┐
│ modality_guess: timeseries                   │
│ concerns:                                     │
│   - "INJ_NO 컬럼 단조 증가 미보장"            │
│   - "SPC_DATETIME 형식 비표준"                │
│ recommended_next_steps:                      │
│   - "시간순 정렬 후 처리"                     │
└──────────────────────────────────────────────┘
```

> Stage 완료 후 갱신 (실시간 X) — LLM 호출 빈도 제어.

### 5-5. 사용자 승인 카드 (방식 A — 결정론 미리보기)

L2/L3 작업마다 카드. 환각 위험 0 (결정론 계산만).

```
┌─────────────────────────────────────────────────┐
│ Stage 0 / [maintenance] L3_mold_condition       │
│ 작업: clean_masking / 권한: L2                   │
│ step_key: clean_masking:CV_005                   │
│ 대상 컬럼: CV_005                                │
│                                                  │
│ 통계 미리보기 (결정론 계산):                     │
│   현재: object dtype, 3000행 중 240개 마스킹     │
│   변환 후: float64, NaN 8% (240개)              │
│                                                  │
│ 작업 방향:                                       │
│   "*", "**", "***" → NaN 변환 후 float 수치화    │
│                                                  │
│ Lineage 기록: 자동                                │
│                                                  │
│ [거부]                              [승인]       │
└─────────────────────────────────────────────────┘
```

승인 동작 (step_key 기반):
1. `POST /api/pipeline/{session_id}/approve` 호출
2. body: `{ "stage_order": int, "module_index": int, "step_key": str }`
3. 백엔드: `approval_token = f"ui-approved-{step_key}"` 생성
4. Executor: step.step_key 매칭 → 결정론 변환
5. Lineage 자동 기록

거부:
- step `skipped` 표시
- Validator 가 lineage 누락 경고

### 5-6. 자연어 입력 (방식 B — 2단계 환각 방어)

[+ 자연어로 수정] 클릭 시 펼침.

```
┌─────────────────────────────────────────────────┐
│ ─── 자연어로 수정 ───                           │
│ ┌────────────────────────────────────────────┐  │
│ │ 예: "CV_005는 그대로 두고 진행해줘"          │  │
│ │ [LLM에게 전달]                              │  │
│ └────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
        ↓
[POST /api/pipeline/{session_id}/natural_input]
        ↓ LLM 매핑 (OPERATION_PERMISSION 12개 중에서만)
┌─────────────────────────────────────────────────┐
│ LLM 해석 (gemma4:e4b):                          │
│  "CV_005 컬럼에 'drop_column' 적용 요청으로     │
│   해석. 권한 L3 (차단+백업)."                    │
│   confidence: 0.82                               │
│                                                  │
│ [예, 진행]            [아니오, 다시 입력]        │
└─────────────────────────────────────────────────┘
```

환각 방어:
- 출력 = OPERATION_PERMISSION 12개 중 매핑만
- 권한 등급 = guardrails 자동 (LLM 변경 ❌)
- 사용자 재확인 강제 (2단계 게이트)
- confidence < 0.7 시 자동 거부

### 5-7. 데이터 미업로드 알람 (LLM judge)

Stage 처리 시작 시 자동 호출:

```
┌─────────────────────────────────────────────────┐
│ ⚠️ 데이터 미업로드 알람                          │
│ Stage 0 / [maintenance] L3_mold_anomaly         │
│   data_path: null                                │
│                                                  │
│ LLM 판단:                                        │
│   alarm: True                                    │
│   reason: "예지보전 모듈은 이상 임계값이         │
│            필요한 필수 데이터"                    │
│                                                  │
│   [돌아가서 업로드]   [무시하고 skip]             │
└─────────────────────────────────────────────────┘
```

skip 시:
- 해당 모듈 처리 skip
- Validator.next_action: `validation_concern`
- Page 6 모델 추천 시 낮은 신뢰도 표시

### 5-8. Context Aggregator 자동 트리거

```
모든 Stage status == "done" or "skipped"
        ↓
[자동] GET /api/aggregate_context/{session_id}
        ↓
AggregatedContext 생성 (결정론)
        ↓
sessions.results 저장
        ↓
[다음] 버튼 활성화
```

### 5-9. 다음 페이지 이동 (수동 클릭)

자동 이동 안 함 — 사용자가 결과 확인 후 [다음 →] 클릭.

활성 조건:
- 모든 Stage status == "done" or "skipped" or "validation_concern"
- pending_approvals 없음
- AggregatedContext 생성 완료

### 5-10. 에러 처리

| 케이스 | 처리 |
|---|---|
| MCP 서버 down | 모듈 skip + 재시도 |
| Ollama LLM down | LLM 해석 "응답 없음" + 결정론 계속, Validator 낮은 신뢰도 |
| Inspector 실패 | 모듈 failed, 다음 모듈 계속 |
| Planner JSON 파싱 실패 | 규칙 기반 fallback |
| Executor 변환 실패 | rollback + Validator issues 기록 |
| approval_token 만료 | 카드 재표시, 재승인 |
| Context Aggregator 실패 | 재시도 + [다음] 비활성 |

### 5-11. 검증 체크리스트

- [ ] SSE 또는 폴링 연결 + 진행률 실시간 갱신
- [ ] 좌/우 패널 동기화
- [ ] 챌린지 배지 5종
- [ ] LLM 해석 표시
- [ ] 카드 통계 미리보기 정확
- [ ] step_key 기반 승인
- [ ] 자연어 입력 → 매핑 → 재확인
- [ ] confidence < 0.7 자동 거부
- [ ] OPERATION_PERMISSION 외 차단
- [ ] 미업로드 알람
- [ ] Context Aggregator 자동 호출
- [ ] [다음] 활성 조건 정확
- [ ] 자동 이동 ❌
- [ ] 에러 복구

---

## Part 6. 페이지 5: 분석 목적 + 전처리 결과 (뒷단)

### 6-1. URL / 화면 mockup

```
URL: /pipeline/analyze?session=<uuid>

┌─────────────────────────────────────────────────────────────────────────┐
│ Line 1 / 6개 Stage 표준화 완료                          [모델: e4b ▼]    │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─ 자동 질문 (LLM 추천) ─────────────────────────────────────────────┐ │
│ │ 데이터 감지:                                                          │ │
│ │   - Stage 0: process + maintenance                                   │ │
│ │   - Stage 4: quality (PASS_YN 2.85% 불균형)                          │ │
│ │                                                                       │ │
│ │ 추천 분석 목적 (gemma4:e4b):                                         │ │
│ │   ⊙ 품질 예측·분류 (quality) — 추천 1순위                            │ │
│ │     "극심 불균형 라벨 + process 변수 → 분류 적합"                    │ │
│ │   ○ 이상 탐지 (maintenance) — 추천 2순위                             │ │
│ │     "Stage 0 maintenance + 시계열"                                   │ │
│ │   ○ 공정 최적화 (process)                                            │ │
│ │   ○ 예지보전                                                          │ │
│ │   ○ 통계·SPC 분석                                                    │ │
│ │   ○ 직접 입력: [_____________________]                              │ │
│ │                                              [선택 후 EDA 시작]      │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─ EDA 결과 (선택 후) ───────────────────────────────────────────────┐ │
│ │ [Stage 4 / quality / PASS_YN 분포]                                  │ │
│ │   막대: PASS=97% / FAIL=3%                                           │ │
│ │   자연어: "PASS_YN 극심 불균형. SMOTE 또는 class_weight 필수."        │ │
│ │                                                                       │ │
│ │ [Stage 4 / process / VALUE1~30 박스플롯]                            │ │
│ │   양품 vs 불량 (상위 10 변수)                                        │ │
│ │   자연어: "VALUE7, VALUE15 가 불량과 가장 구별."                      │ │
│ │                                                          [다음 →]    │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6-2. 자동 질문 후보 생성 (LLM 가치 영역 ③)

페이지 진입 시:
```
GET /api/analyze/{session_id}/questions
```

백엔드:
1. AggregatedContext 조회
2. LLM 프롬프트:
```
SYSTEM: 제조 데이터 분석 어드바이저. facts 보고 분석 목적 1~2개 추천.
         available_options 외 추천 금지. JSON.
USER: {
  "aggregated_context": {...},
  "available_options": [
    "anomaly_detection", "quality_classification",
    "process_optimization", "predictive_maintenance",
    "demand_forecasting", "statistical_comparison"
  ]
}
```

환각 방어:
- `available_options` 외 추천 ❌
- rationale 은 facts 인용 강제

### 6-3. 사용자 선택 + 자유 입력

라디오 6개 + 자유 입력. 자유 입력 시 LLM 매핑 + 재확인 (Page 4 패턴 재사용).

선택 후:
```
POST /api/analyze/{session_id}/select
body: { "analysis_purpose": str, "free_input": str | None }
```

백엔드: AggregatedContext.user_intent 갱신 + EDA 자동 실행.

### 6-4. EDA 차트 4 Function 매핑 (외부 검증 결과)

선택된 분석 목적에 따라 Function 축 결정 → 해당 차트 자동 생성:

| 분석 목적 | Function 축 | Primary 차트 | Secondary 차트 |
|---|---|---|---|
| 이상 탐지 | maintenance 또는 quality | FFT 주파수 스펙트럼 (정상 vs 이상) | RMS 트렌드 / Spectrogram |
| 품질 예측·분류 | quality | 클래스별 이미지 그리드 (이미지) 또는 박스플롯 (수치) | 클래스 분포 막대 + 해상도/밝기 |
| 공정 최적화 | process | 타겟 라벨별 박스플롯 (상위 N) | 타겟 상관계수 막대 / 핵심 2변수 산점도 |
| 예지보전 | maintenance | FFT 주파수 스펙트럼 | RMS/Envelope 트렌드 |
| 생산량 예측 | order (모달리티) | 시계열 라인 (집계) | 계절성 분해 |
| 통계·SPC | reference | 파레토 차트 | p관리도 / 합부율 트렌드 |

각 차트 옆 결정론 통계 + LLM 자연어 요약.

### 6-5. 데이터 규모별 가드 규칙

| 조건 | 가드 |
|---|---|
| row > 1M | RMS 윈도우 또는 stride sampling 강제 (1~10K 포인트) |
| 변수 > 30 | 타겟 상관도 상위 15~20개만 |
| 이미지 | 썸네일 256~512px + lazy-load. bmp/대용량 → PNG 캐시 |
| 클래스 불균형 < 10% | 박스플롯 strip/swarm 오버레이 |
| 카테고리 30+ | 상위 30~50 + 'Others' |
| 한글 CSV | encoding='cp949' 자동 |
| FFT 입력 | sliding window 평균 스펙트럼 |

차트 라이브러리 (recharts/Chart.js) 선택 시 가드 충족 검증.

### 6-6. EDA 자연어 요약 (LLM 가치 영역 ④)

```
SYSTEM: 제조 데이터 분석 해설가. stats와 findings를 한국어 2~3문장.
         숫자는 입력값 그대로. 새 추론 금지. JSON.
USER: {
  "chart_type": "boxplot_by_label",
  "stats": {...},
  "findings": {AggregatedContext.key_findings 중 해당},
  "user_purpose": "quality_classification"
}
```

응답:
```python
{
  "summary": "VALUE7, VALUE15가 불량 군과 가장 구별. 모델링 feature 우선순위로 활용.",
  "key_points": ["VALUE7 양품/불량 median 차이 큼", "VALUE15 IQR 거의 안 겹침"]
}
```

환각 방어:
- 숫자는 stats 입력값 그대로 인용
- 새 추론 ❌
- 출력 2~3문장 제한

### 6-7. 이상치 처리 시각화

Box plot 강조:
- whisker 밖 점들 색상 표시
- Hover 시 행 정보
- before / after 좌우 비교

Executor.before_stats / after_stats 활용.

### 6-8. 추가 전처리 (Function 컨텍스트 기반)

분석 목적 선택 후 결정론 + 사용자 승인:
- quality_classification + 불균형 → `balance_classes` (L2) 카드
- predictive_maintenance + 시계열 + 결측 → `fill_missing` (시계열 보간) 카드

step_key 기반 승인 패턴 재사용 (Page 4).

### 6-9. API 호출

| 엔드포인트 | 메서드 | 역할 |
|---|---|---|
| `/api/aggregate_context/{session_id}` | GET | 조회 |
| `/api/analyze/{session_id}/questions` | GET | 자동 질문 |
| `/api/analyze/{session_id}/select` | POST | 선택 |
| `/api/analyze/{session_id}/results` | GET | EDA 결과 |
| `/api/pipeline/{session_id}/natural_input` | POST | 자유 입력 매핑 (공유) |

### 6-10. 에러 처리

| 케이스 | 처리 |
|---|---|
| LLM judge 실패 | 기본 후보 4종 표시, "추천 비활성" |
| 매핑 confidence < 0.5 | "직접 라디오 선택" |
| EDA 렌더링 실패 | 가드 자동 적용 + 실패 시 "데이터 규모 확인" |
| 자연어 요약 LLM 실패 | 통계만 표시, 페이지 진행 |
| `available_options` 외 추천 | 차단 + fallback |

### 6-11. 검증 체크리스트

- [ ] `/api/analyze/{id}/questions` 자동 호출
- [ ] 옵션 1~2개 표시 (is_primary 강조)
- [ ] `available_options` 외 차단
- [ ] 라디오 6개 + 자유 입력
- [ ] 자유 입력 매핑 + 재확인
- [ ] 선택 후 EDA 자동 생성
- [ ] 4 Function × 6 차트 매핑 정합
- [ ] 데이터 가드 7종 적용
- [ ] 자연어 요약 (숫자 인용)
- [ ] 2~3문장 길이
- [ ] 이상치 before/after
- [ ] 추가 전처리 카드
- [ ] 분석 목적 변경 시 EDA 재실행
- [ ] [다음] Page 6 이동

---

## Part 7. 페이지 6: 모델링 (뒷단)

### 7-1. URL / 화면 mockup

```
URL: /pipeline/model?session=<uuid>

┌─────────────────────────────────────────────────────────────────────────┐
│ Line 1 / 분석 목적: 품질 예측·분류                       [모델: e4b ▼]   │
├─────────────────────────────────────────────────────────────────────────┤
│ 추천 모델 (Module Catalog + AggregatedContext 기반):                    │
│                                                                         │
│ ┌─ 카드 1 ──────────────────────────────────────────────────────────┐ │
│ │ XGBoost                                          ⭐ 추천 1순위        │ │
│ │ 적합 이유: 다변수 회귀 + 결측 robust + 불균형에 강함                  │ │
│ │ AggregatedContext 반영:                                              │ │
│ │   - 불균형 → class_weight='balanced' 자동                            │ │
│ │   - 결측 8% → 내장 처리                                              │ │
│ │ 예상 시간: ~30초 / 메모리: ~1GB                                      │ │
│ │ 추정 성능: F1 0.80~0.90                                              │ │
│ │ [선택]                                                                │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│ ┌─ 카드 2: LightGBM ... [선택]                                         │ │
│ ┌─ 카드 3: 작은 CNN  ⚠️ 시간 경고 [선택 → 2차 결정]                    │ │
│ ─── 권고만 (실행 불가) ───                                              │
│ • EfficientNet/대형 CNN: VRAM 8GB 초과 → 외부 GPU                      │
│                                                          [학습 시작]    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7-2. 추천 모델 카드 (정보 제공, AggregatedContext 활용)

```
GET /api/model/{session_id}/recommend
```

백엔드:
1. AggregatedContext + Module Catalog recommended_models 조회
2. LLM 적합도 판단:
```
SYSTEM: 제조 모델링 어드바이저. available_models 만 사용. fit_score 1~5.
         새 모델 생성 ❌. rationale은 facts 인용. JSON.
USER: {
  "aggregated_context": {...},
  "user_purpose": "quality_classification",
  "available_models": [{...}, ...]
}
```

환각 방어:
- `available_models` 외 추천 ❌
- fit_score 1~5 범위 강제
- rationale = key_findings 인용 강제

AggregatedContext 자동 반영:
- 불균형 → class_weight 권장
- 결측 → 모델별 처리 전략
- 컬럼 수 → 적합성

### 7-3. 모델 2 depth (CNN 한정 Quick/Full/Skip)

XGBoost/LightGBM/MLP: [선택] 즉시 학습.

작은 CNN: [선택] → 2차 결정 모달:

```
┌─────────────────────────────────────────────────┐
│ 작은 CNN 학습 옵션                                │
│ ⚠️ CNN 학습은 시간이 오래 걸립니다.              │
│                                                  │
│ ⊙ Quick (디렉션 확인용)                          │
│   ~5분 / epoch 5 / 데이터 10%                    │
│   추정 성능: F1 0.60~0.75 (참고용)              │
│   메모리: ~4GB                                   │
│                                                  │
│ ○ Full (실제 활용 가능)                          │
│   ~30분 / epoch 50 / 데이터 100%                 │
│   추정 성능: F1 0.85~0.95                       │
│   메모리: ~6GB                                   │
│                                                  │
│ ○ Skip (권고만, 학습 ❌)                          │
│                                                  │
│ [취소]                              [확인]       │
└─────────────────────────────────────────────────┘
```

### 7-4. 시간 경고 모달 (대형 모델)

```
┌─────────────────────────────────────────────────┐
│ ⚠️ 실행 불가 모델                                 │
│ EfficientNet 은 VRAM 8GB 초과.                   │
│ 권장:                                            │
│   - 작은 CNN (Quick) 으로 디렉션 확인            │
│   - 외부 GPU (24GB+) 환경                        │
│ [확인]                                            │
└─────────────────────────────────────────────────┘
```

### 7-5. 학습 진행 UI

```
POST /api/model/{session_id}/train
body: { "model_name": str, "mode": "quick"|"full"|"skip", "options": dict }
```

진행 (SSE 또는 폴링):
```
┌─────────────────────────────────────────────────┐
│ 학습 진행: XGBoost                               │
│ step 35 / 100  (XGBoost: boosting_round)         │
│ ░░░░░░░░░░░░░░░ 35%                              │
│ train_loss: 0.182 → 0.089                        │
│ val_loss:   0.215 → 0.142                        │
│ 예상 잔여: 12초                                  │
│ [학습 중단]                                      │
└─────────────────────────────────────────────────┘
```

### 7-6. 결과 송출 — 기본 (1번)

```
┌─────────────────────────────────────────────────────────────────┐
│ XGBoost 학습 완료 (28초)                                         │
├─────────────────────────────────────────────────────────────────┤
│ ┌─ 지표 표 ─────────────────────────┐                          │
│ │ Accuracy:  0.892                  │                          │
│ │ Precision: 0.876                  │                          │
│ │ Recall:    0.823                  │                          │
│ │ F1:        0.849                  │                          │
│ │ AUC:       0.913                  │                          │
│ └────────────────────────────────────┘                          │
│ ┌─ Confusion Matrix ──────────────┐                            │
│ │           예측 PASS    예측 FAIL │                            │
│ │ 실제 PASS    8,720         180   │                            │
│ │ 실제 FAIL      45         255    │                            │
│ └──────────────────────────────────┘                            │
│ ┌─ Feature Importance (상위 10) ───────────────────┐            │
│ │ VALUE7   ████████████ 0.182                       │            │
│ │ VALUE15  █████████ 0.146                          │            │
│ │ ...                                                │            │
│ └────────────────────────────────────────────────────┘            │
│ [+ 풀 대시보드]   [다른 모델 학습]    [완료]                    │
└─────────────────────────────────────────────────────────────────┘
```

### 7-7. 풀 대시보드 확장 옵션 (3번 가능성)

[+ 풀 대시보드] 클릭 시 추가:
- ROC Curve (binary 분류)
- 예측 샘플 (실제 vs 예측 표)
- SHAP 분석 (시간 추가 — 모달 확인)
- Precision-Recall Curve (불균형 강조)
- 학습 곡선 (train/val loss)

SHAP 활성 시:
```
┌─────────────────────────────────────────────────┐
│ SHAP 분석                                        │
│ ⚠️ 추가 시간: ~1~3분 (XGBoost 기준)              │
│ [건너뜀]                            [실행]       │
└─────────────────────────────────────────────────┘
```

### 7-8. 학습 결과 저장

1. **DB** (`pipelines.sessions.model_results`): JSON 지표 + Confusion + Importance + metadata
2. **파일 시스템** (`data/lake/model_results/<session_id>/<model_name>/`): parquet/pickle/.pt
3. **Lineage**: "model_trained" transformation 기록

다음 세션 같은 session_id 로 복원 가능.

### 7-9. Lineage 기록 (모델 학습도)

```python
lineage.record(
    dataset_id=...,
    transformation_type="model_trained",
    params={
        "model_name": "XGBoost",
        "mode": "full",
        "hyperparameters": {...},
        "metrics": {"f1": 0.849, ...},
        "trained_at": "...",
        "training_seconds": 28
    },
    applied_by_agent="executor",
    user_approval_id="ui-approved-model-xgboost",
    can_rollback=True
)
```

### 7-10. API 호출

| 엔드포인트 | 메서드 | 역할 |
|---|---|---|
| `/api/model/{session_id}/recommend` | GET | 추천 카드 |
| `/api/model/{session_id}/train` | POST | 학습 트리거 |
| `/api/model/{session_id}/status` | GET | 진행률 (SSE/폴링) |
| `/api/model/{session_id}/results` | GET | 기본 결과 |
| `/api/model/{session_id}/dashboard` | GET | 풀 대시보드 (ROC+SHAP 등) |
| `/api/model/{session_id}/cancel` | POST | 학습 중단 |

### 7-11. 에러 처리

| 케이스 | 처리 |
|---|---|
| LLM 적합도 실패 | 기본 카드 (Module Catalog 그대로) |
| VRAM 초과 (학습 중) | OOM 감지 → 중단 → "Quick 재시도?" |
| 시간 초과 (예상×3) | 자동 중단 + 알림 |
| Importance 추출 실패 | 다른 지표만 |
| Confusion 생성 실패 (회귀) | MAE/RMSE/R² 대체 |
| 모델 저장 실패 | 학습은 성공, 저장 재시도 |
| SHAP 시간 초과 | 자동 중단 + 기본 결과 |
| 사용자 중단 | 즉시 + 부분 결과 |

### 7-12. 검증 체크리스트

- [ ] 추천 카드 표시
- [ ] AggregatedContext 반영 (불균형 → class_weight 등)
- [ ] `available_models` 외 차단
- [ ] 카드별 fit_score / rationale / 시간 / 메모리 / 추정 성능
- [ ] XGBoost/LightGBM/MLP 즉시 학습
- [ ] 작은 CNN 2차 결정 (Quick/Full/Skip)
- [ ] 대형 모델 실행 불가 모달
- [ ] 학습 진행 (step + step_unit + loss — step_unit: CNN=epoch / XGBoost·LightGBM=boosting_round)
- [ ] 기본 결과: 지표 + Confusion + Importance
- [ ] [+ 풀 대시보드] (ROC + SHAP + 예측 샘플)
- [ ] SHAP 시간 경고 모달
- [ ] DB + 파일 시스템 저장
- [ ] Lineage 기록 (model_trained)
- [ ] [다른 모델 학습] 누적 동작
- [ ] [완료] session status = "done"
- [ ] OOM / 시간 초과 / 중단 처리

---


---

## Phase 2 마무리 — 다음 단계 인수인계

### Phase 2 작성 범위 (본 파일)
- Part 5: Page 4 표준화 진행 (중간단) — SSE+폴링 폴백 / 카드+자연어 환각방어 / step_key 승인 / 미업로드 알람 (LLM judge) / Context Aggregator 트리거
- Part 6: Page 5 분석 목적 + EDA (뒷단) — 자동 질문 LLM (가치 ③) / EDA 차트 4 Function 매핑 / 데이터 규모 가드 7종 / 자연어 요약 LLM (가치 ④) / 이상치 시각화 / 추가 전처리
- Part 7: Page 6 모델링 (뒷단) — 추천 카드 (AggregatedContext 활용) / 2 depth (CNN Quick/Full/Skip) / 결과 송출 (지표+Confusion+Importance 기본 + 풀 대시보드 확장) / Lineage 기록

### 다음 단계 (Phase 3, spec-3.md) 가 참조할 결정 사항

**Page 4 동작 (Part 5)**:
- 진행률 갱신: SSE 기본 + 폴링 폴백 (구현 주체 선택)
- PipelineStatus 자료구조 (spec-1 Part 1-2 와 정합)
- 승인 매칭: step_key 기반 (order 아님)
- 자연어 입력 API: `POST /api/pipeline/{id}/natural_input` (confidence < 0.7 거부)
- Context Aggregator 자동 호출 시점: 모든 Stage done 시

**Page 5 동작 (Part 6)**:
- 자동 질문 후보: `available_options` 6종 (anomaly_detection / quality_classification / process_optimization / predictive_maintenance / demand_forecasting / statistical_comparison)
- EDA 차트 4 Function 매핑 — `project_eda_charts.md` 메모리 인용
- 데이터 규모 가드 7종 (row>1M, 변수>30, 이미지, 불균형, 카테고리, 한글, FFT)
- LLM 자연어 요약: facts 인용 + 2~3 문장 제한

**Page 6 동작 (Part 7)**:
- 추천 모델: Module Catalog `recommended_models` + LLM 적합도 (fit_score 1-5)
- 2 depth: 작은 CNN 만 Quick(5분)/Full(30분)/Skip
- VRAM 8GB 초과 모델 (EfficientNet 등): 실행 불가, 권고만
- 결과: 지표+Confusion+Importance 기본 / [+ 풀 대시보드] = ROC + 예측 샘플 + SHAP (시간 경고)
- Lineage: model_trained transformation 기록

### Phase 3 가 수행할 내용 (spec-3.md)

| Part | 내용 | 분량 |
|---|---|---|
| 8 | 컴포넌트 라이브러리 (22종 React) | ~150줄 |
| 9 | 전체 API/자료구조 종합 (25 + 8) | ~150줄 |
| 10 | 에러 처리 종합 (페이지별 + 11 표준 코드) | ~100줄 |
| 11 | 테스트 시나리오 (E2E 6 + 챌린지 8 회귀 + 단위 7) | ~120줄 |
| 12 | 데모 시나리오 (3분/7분/15분 + 베타 환경) | ~100줄 |
| 부록 A | 자료구조 실 JSON 예시 | ~100줄 |
| 부록 B | API curl 예시 16개 | ~80줄 |
| 부록 C | 상태 천이 다이어그램 3종 | ~50줄 |

### 본 단계 (Phase 2) 설계 결정 사항 요약

> `0_CHANGELOG_v5.md` 는 알파 진입 후 기록 시작 (현재 비어 있음). 본 섹션은 v5 설계 단계 결정의 요약.

- Phase 2 작성: Page 4~6 명세 정립 (~820줄)
- 사용자 결정 3개 반영: SSE+폴링 (Page 4), 수동 클릭 (Page 5/6 진입), 결과 송출 조합 (Page 6)
- AggregatedContext 활용: Page 5/6 LLM 프롬프트에 주입 (환각 방어 5% 미만)

### Phase 3 진입 체크리스트

- [ ] 본 Phase 2 명세 숙독 (특히 Part 5-2 SSE, Part 5-5 승인 카드, Part 6-4 EDA 차트, Part 7-2 추천 모델)
- [ ] `0_CHANGELOG_v5.md` 알파 진입 후 기록 확인 (v5 시점은 비어 있음)
- [ ] `0_variable_index_v5.md` §10 컴포넌트 인덱스 확인 (Phase 3 Part 8 작성 입력)
- [ ] Phase 1 + Phase 2 결정 사항 누적 인지

---

**이전 파일**: `0_pipeline_ui_spec-1_v5.md` (Phase 1)
**다음 파일**: `0_pipeline_ui_spec-3_v5.md` (Phase 3)

**작성**: 2026-05-27 spec-2 v5 (Claude Opus 4.7)
