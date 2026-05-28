# 0_README_v5 — manufacturing-mcp 프로젝트 진입 가이드

> **본 파일 목적**: 처음 보는 팀원 / 새 AI 세션이 이 프로젝트를 ★어떤 파일부터, 어떤 순서로, 어떤 조합으로★ 읽을지 안내.
>
> **이걸 가장 먼저 읽으세요.** 모든 다른 산출물의 진입점.
>
> **버전**: v5 (2026-05-27). 다른 산출물 6개와 버전 통일.

---

## 1. 프로젝트 한 줄 소개

SI 기업용 **MCP·Agent·로컬 LLM 기반 제조 데이터 전처리 자동화 시스템**.

차별점: "기존 ETL은 사람이 코드를 짠다 / 우리는 AI가 코드를 짠다 + 모든 추론 로컬 + 추적 가능".

---

## 2. 산출물 7 파일 일람

| 파일 | 분량 | 역할 |
|---|---|---|
| **`0_README_v5.md`** | 본 파일 | 진입 가이드 |
| `0_project_blueprint_v5.md` | ~1380줄 | 프로젝트 마스터 청사진 (비전·아키텍처·3축 모델·LLM 통합 패턴) |
| `0_pipeline_ui_spec-1_v5.md` | ~1750줄 | Phase 1 UI 명세 — 공통 설계 + Page 1~3 |
| `0_pipeline_ui_spec-2_v5.md` | ~820줄 | Phase 2 UI 명세 — Page 4~6 |
| `0_pipeline_ui_spec-3_v5.md` | ~980줄 | Phase 3 UI 명세 — 종합 + 부록 (컴포넌트·API·에러·테스트·데모) |
| `0_variable_index_v5.md` | ~370줄 | 변수 목차 (확장 가능 항목 인덱스) |
| `0_CHANGELOG_v5.md` | 92줄 | 변경 이력 (알파 단계 이후 기록 시작) |

본진 코드 정합 기준:
- `/home/byeonggab89/FINAL/manufacturing-mcp/CLAUDE.md` (설계 헌법)
- `/home/byeonggab89/FINAL/manufacturing-mcp/docs/decisions.md` (결정 이력)

---

## 3. 역할별 읽기 순서

### 케이스 A — 신규 팀원 (프로젝트 전반 이해)

**목적**: 큰 그림 잡기.

| 순서 | 파일 | 분량 | 추출 포인트 |
|---|---|---|---|
| 1 | `0_README_v5.md` | 본 파일 | 진입 가이드 |
| 2 | `0_project_blueprint_v5.md` | 전체 | 정체성 / 사용자 6단계 페이지 시퀀스 / 옵션 E (사전정의 카탈로그+드래그앤드롭+컨텍스트 누적) / 3축 모델 (Modality×Line·Node×Function) / LLM 통합 패턴 / 헌법 정합 |
| 3 | `0_variable_index_v5.md` | 전체 | 4 모달리티 / 4 Function / 3 Line / 18 Node / 페이지별 prefix / OPERATION_PERMISSION 12종 / MCP 7도구 / 자료구조 8종 / API 25 / 환각 방어 위치 |
| 4 | `0_CHANGELOG_v5.md` | 전체 (짧음) | 변경 이력 정책 (알파 이후 시작) / 단계 진입 시 필독 3 파일 |
| 5 | `0_pipeline_ui_spec-1_v5.md` | Part 0~1 만 | 6 페이지 흐름 + 공통 설계 원칙 |
| 6 | 본진 `CLAUDE.md` + `decisions.md` | — | 설계 헌법 + 결정 이력 |

**완료 체크리스트**:
- [ ] 사용자 6단계 페이지 시퀀스를 머릿속에 그릴 수 있다
- [ ] L1/L2/L3 가 ★권한★ 이고 L1~L4 가 ★Function 축★ 임을 구분한다 (다른 차원!)
- [ ] 4 모달리티 (timeseries/inspection-image/event-log/order) 가 ★5번째 추가 ❌★ 정책임을 안다
- [ ] OPERATION_PERMISSION 12종이 ★단일 소스 (harness/guardrails.py)★ 임을 안다
- [ ] Phase 1+2+3 분할 구조 (spec-1/2/3) 를 이해한다
- [ ] CHANGELOG 는 ★알파 이후★ 변경 기록용 임을 안다

---

### 케이스 B — 특정 페이지 구현 개발자

**목적**: 특정 페이지 명세 정확히 이해 + 즉시 구현 진입.

| 순서 | 파일 | 사용 범위 | 이유 |
|---|---|---|---|
| 1 | `0_project_blueprint_v5.md` | Part 0~1 만 | 빠른 큰 그림 |
| 2 | `0_CHANGELOG_v5.md` | 전체 | 최신 변경 (알파 진입 후) |
| 3 | 해당 Phase 명세 (전체) | — | 상세 명세 |
| 3-1 | Page 1~3 → `0_pipeline_ui_spec-1_v5.md` | 전체 | Phase 1 + Part 1-9 검증 |
| 3-2 | Page 4~6 → `0_pipeline_ui_spec-2_v5.md` | 전체 | Phase 2 |
| 4 | `0_pipeline_ui_spec-3_v5.md` 부록 A/B | 해당 페이지 | 실 JSON / curl 예시 |
| 5 | `0_variable_index_v5.md` § 5/9/10 | 해당 prefix/API/컴포넌트 | 영향 범위 |
| 6 | 본진 해당 코드 | — | 실 구현 |

**페이지별 본진 코드 위치**:
- Page 1 (Line 선택): `frontend/step1_line/` + `backend/routers/step1_line.py`
- Page 2 (Pipeline 구성): `frontend/step2_user_input_pipeline/` + `backend/routers/step2_user_input_pipeline.py`
- Page 3 (데이터+제약): `frontend/step3_user_input_data/` + `backend/routers/step3_user_input_data.py`
- Page 4 (표준화): `frontend/step4_standardize/` + `backend/routers/step4_standardize.py` + `agents/` 전체
- Page 5 (분석 목적): `frontend/step5_analyze/` + `backend/routers/step5_analyze.py` + Context Aggregator (신규)
- Page 6 (모델링): `frontend/step6_modeling/` + `backend/routers/step6_modeling.py` + 학습 모듈

---

### 케이스 C — 알파 테스트 진행자

**목적**: Phase 3 의 8 검증 항목 + Part 1-9 의 LLM 모니터링 7 지표 측정 / 갱신.

| 순서 | 파일 | 사용 범위 |
|---|---|---|
| 1 | `0_pipeline_ui_spec-1_v5.md` Part 1-9 | 검증·피드백·모니터링 9 하위 섹션 (1-9-1~1-9-9) |
| 2 | `0_pipeline_ui_spec-3_v5.md` Part 11 | E2E 6 + 챌린지 8 회귀 + 단위 7 |
| 3 | `0_variable_index_v5.md` §13 | 알파/베타/운영 단계 정의 |
| 4 | `0_CHANGELOG_v5.md` | 알파 진입 후 첫 기록 시작 |
| 5 | 발견 사항 → `0_CHANGELOG_v5.md` 즉시 추가 |

---

### 케이스 D — 변수 추가 / MCP 도구 추가 / 새 작업 추가

**목적**: 확장 시 영향 범위 파악 + 정합 보장 갱신.

| 순서 | 파일 | 사용 범위 |
|---|---|---|
| 1 | `0_variable_index_v5.md` 해당 섹션 | 추가 영역 파악 |
| 2 | `0_variable_index_v5.md` "확장 정책" | 해당 영역 추가 제약 (예: 모달리티 5번째 ❌) |
| 3 | 본진 코드 수정 | `harness/guardrails.py` (작업 추가) 등 |
| 4 | `0_variable_index_v5.md` 갱신 | 1줄 추가 |
| 5 | `0_CHANGELOG_v5.md` 갱신 | 변경 사유 + 영향 파일 + 정합 |
| 6 | 영향 파일 (blueprint / spec) 갱신 | 필요 시 |

---

### 케이스 E — AI 컨텍스트 새 챗 로딩 (가장 효율)

새 챗 / Claude / Gemma 등에 본 프로젝트를 컨텍스트로 주입할 때.

| 작업 종류 | 로딩 파일 (최소) | 로딩 파일 (추가 시) |
|---|---|---|
| 전반 이해 | README + blueprint + CHANGELOG + variable_index | spec-1 Part 0~1 |
| Phase 1 작업 | README + blueprint + CHANGELOG + spec-1 | variable_index |
| Phase 2 작업 | README + blueprint + CHANGELOG + spec-2 | spec-1 Part 1-2/1-3/1-7 |
| Phase 3 작업 | README + blueprint + CHANGELOG + spec-3 | spec-1 + spec-2 인수인계 |
| 알파 테스트 | README + spec-1 Part 1-9 + spec-3 Part 11 + CHANGELOG | — |
| 변수 추가 | README + variable_index + CHANGELOG | 영향 파일 |

---

## 4. AI 컨텍스트 로딩용 프롬프트 (복붙)

새 챗 시작 시 아래를 그대로 복사:

```
나는 manufacturing-mcp 프로젝트의 [역할: 개발자 / 알파 테스터 / 변수 추가 작업자]
로 작업한다. 본 프로젝트는 SI 기업용 MCP·Agent·로컬 LLM 기반 제조 데이터 전처리
자동화 시스템이다.

다음 파일들을 컨텍스트로 첨부하니, 우선순위에 따라 읽어달라:

[필수 - 모든 작업 공통]
1. 0_README_v5.md (진입 가이드, 본 파일)
2. 0_project_blueprint_v5.md (프로젝트 마스터 청사진)
3. 0_CHANGELOG_v5.md (변경 이력 + 단계 진입 정책)
4. 0_variable_index_v5.md (변수 목차 - 확장 가능 항목 인덱스)

[작업별 필독 - 위 필수 다음으로 읽기]
- Phase 1 작업 (공통 + Page 1~3): 0_pipeline_ui_spec-1_v5.md
- Phase 2 작업 (Page 4~6): 0_pipeline_ui_spec-2_v5.md (+ spec-1 결정사항)
- Phase 3 작업 (종합/부록): 0_pipeline_ui_spec-3_v5.md (+ spec-1, spec-2)
- 알파 테스트: spec-1 Part 1-9 + spec-3 Part 11
- 변수 추가: variable_index 해당 섹션

[본진 코드 정합 기준 - 필요 시]
- /home/byeonggab89/FINAL/manufacturing-mcp/CLAUDE.md (설계 헌법, 절대 규칙)
- /home/byeonggab89/FINAL/manufacturing-mcp/docs/decisions.md (결정 이력 D-01~31)

[중요 규칙]
1. 별표(★) 마크업 사용 금지. 강조는 굵게(**) 또는 인용 블록(>).
2. "L1/L2/L3" 단독 사용 금지 - 권한(harness/guardrails)인지 Function 축인지
   맥락 명시 필수.
3. 모달리티 4개 (timeseries/inspection-image/event-log/order) 5번째 추가 금지.
4. OPERATION_PERMISSION 12종 외 새 작업 LLM이 생성하지 못함 (가드레일).
5. 외부 API 호출 절대 금지 (Claude/GPT/Gemini) - 모든 추론 로컬 Ollama.
6. CHANGELOG 는 알파 진입 이후 변경만 기록 (설계 단계 작업 기록 ❌).
7. 페이지별 prefix: step1_line / step2_user_input_pipeline / step3_user_input_data
   / step4_standardize / step5_analyze / step6_modeling

[현재 상태]
- 설계 v5 완성 (모든 산출 파일 _v5 명시)
- 알파 단계 미진입 (CHANGELOG 비어 있음)
- 본진 코드: /home/byeonggab89/FINAL/manufacturing-mcp/ (단, 직접 접근 불필요 -
  명세서로 충분)

작업 시작: [작업 내용을 여기 명시]
```

---

## 5. 중요 규칙 (모든 작업에 적용)

### 5-1. 마크업
- 별표(★) 사용 금지 — 굵게(**) 또는 인용 블록(>) 사용
- 한국어 우선, 코드/식별자는 영문 그대로

### 5-2. 용어 (변수 목차 §6 참조)

| 약자 | 의미 | 주의 |
|---|---|---|
| L1/L2/L3 (권한) | 코드의 권한 등급 (harness/guardrails.py OPERATION_PERMISSION) | 맥락 없이 단독 사용 금지 |
| L1~L4 (Function) | 사용자 문서의 데이터 분류 축 (process/quality/maintenance/reference) | 위와 ★완전히 다른 차원★ |
| Line | 큰 그룹 (모듈 1/2/3 같은 제품 라인) — 3종 고정 |  |
| Stage | UI 박스 단위 — Line별 max_stages 정의 |  |
| Node | Stage 안 세부 공정 — 18종 |  |
| Module | Node 안 Function 차원 데이터 슬롯 — 1~3개 |  |
| Dataset | 실제 raw 파일 |  |

### 5-3. 절대 규칙 (CLAUDE.md §1)
1. 메인 `gemma4:26b` / 스캐폴딩 `gemma4:e4b`. 31B Dense 금지 (RTX 3070 VRAM 8GB)
2. Agent 프레임워크 = 가벼운 수제 Python. Claude Agent SDK / LangGraph 도입 금지
3. **외부 API 호출 금지** (Claude/GPT/Gemini) — SI 고객 "데이터 외부 전송 0"
4. 데이터는 외부로 나가지 않음 — 도커 내부망만
5. 코드는 호스트, 도커는 실행만 (볼륨 마운트)

### 5-4. 모달리티 분할 (변경 금지)
- 4 모달리티 (timeseries / inspection-image / event-log / order)
- 5번째 추가 ❌ — "MCP 안 늘어남" 영업 메시지 보호

### 5-5. 환각 방어 (변수 목차 §12 참조)
- LLM = 판단·해석·매핑·요약 (제안 수준)
- 결정론 = 사실 추출·실제 변환·검증 (실행)
- 가드레일이 LLM 의 새 작업 생성 ❌, 권한 변경 ❌

### 5-6. CHANGELOG 사용 (CHANGELOG_v5 참조)
- 기록 ⭕: 알파/베타/운영 단계 발견된 변경
- 기록 ❌: 설계 단계 작성 과정 (v1~v5)
- 형식: 시간순 + 변경 내용 + 이유 + 영향 파일 + 정합

---

## 6. 현재 상태 (2026-05-27)

| 항목 | 상태 |
|---|---|
| 설계 v5 | ⭕ 완성 (7 파일 통일) |
| 본진 코드 1층 (4 Agent + 4 MCP) | ⭕ 동작 (팀원 byeonggab89 구현) |
| 알파 단계 | 미진입 (CHANGELOG 비어 있음) |
| 베타 단계 | 미진입 |
| 운영 단계 | 미진입 |

---

## 7. 다음 액션

### 사용자 (병갑님)
- 7 파일 전체 검토
- 알파 단계 진입 결정 시 본 README 외 작업 진입

### 팀원
- 케이스 A 부터 읽기 (전반 이해)
- 자기 역할에 맞는 케이스 B~D 후속

### AI 컨텍스트 (새 챗)
- 위 §4 의 복붙 박스 그대로 사용
- 작업 종류 명시 → 해당 파일 첨부 → 작업 진입

---

## 8. 산출물 관계도

```
[진입]
0_README_v5.md  ←── 가장 먼저
  │
  ├─→ [큰 그림]
  │   0_project_blueprint_v5.md  (1380줄, 마스터 청사진)
  │     └─→ 6 페이지 비전 + 3축 모델 + LLM 통합 패턴
  │
  ├─→ [변수 인덱스]
  │   0_variable_index_v5.md  (370줄)
  │     └─→ 모달리티/Function/Line/Node/API/컴포넌트 모든 변수
  │
  ├─→ [변경 이력]
  │   0_CHANGELOG_v5.md  (92줄, 알파 이후 시작)
  │     └─→ 변경 정책 + 정합 기준
  │
  └─→ [상세 명세 (Phase 별)]
      0_pipeline_ui_spec-1_v5.md  (1750줄, Phase 1)
        └─→ 공통 설계 (1-1~1-9) + Page 1~3
      0_pipeline_ui_spec-2_v5.md  (820줄, Phase 2)
        └─→ Page 4 (표준화) + Page 5 (분석 목적) + Page 6 (모델링)
      0_pipeline_ui_spec-3_v5.md  (980줄, Phase 3)
        └─→ 컴포넌트 + API/자료구조 종합 + 에러 + 테스트 + 데모 + 부록
```

---

**작성**: 2026-05-27 v5 (Claude Opus 4.7, 신규 진입 가이드)
**갱신 정책**: 명세 v5 → v6 갱신 시 본 README 도 함께 갱신
