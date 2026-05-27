# 결정 기록 (Decision Log)

> 설계 대화(Claude.ai)에서 내려진 확정 결정을 시간순으로 기록.
> 인계서 갱신 시 이 내용을 반영할 것.

## 2026-05-22 — 수직 슬라이스 착수 결정

| # | 결정 | 사유 | 인계서 충돌 |
|---|---|---|---|
| D-01 | 메인 모델 **gemma4:26b**, 스캐폴딩 **gemma4:e4b** | RTX 3070 VRAM 8GB. 31B는 ~20GB 필요해 불가. 26B MoE는 18GB지만 활성 3.8B라 8GB+RAM 분산으로 동작, 31B의 97% 성능 | S2 "31B Dense" 폐기 |
| D-02 | **31B Dense 금지** | VRAM 8GB로 불가. (인계서 "Q4 ~16GB"는 사실오류, 실제 ~20GB) | S2/P1 수정 필요 |
| D-03 | 프레임워크 **수제 Python → 이후 LangGraph** | Claude Agent SDK의 로컬 Ollama 호환성 미검증 리스크. 수직 슬라이스부터 관통 후 LangGraph 이전 | S10/P5 "Claude Agent SDK" 폐기 |
| D-04 | **모달리티 분할 유지** (timeseries/image/event-log/order) | 실데이터 34개가 4개로 깔끔히 라우팅됨(검증 완료). 핵심 영업 메시지 | (변경 없음, 인계서 S12와 일치) |
| D-05 | 8가지 챌린지를 더미에 의도적으로 심음 | "깨끗한 합성 데이터의 함정" 회피. 현장 고통점 시연 | (data_summary [5] 채택) |
| D-06 | DB schema **3개만** (metadata/lineage/agent_logs) | 수직 슬라이스 스코프. 나머지 3개는 Sprint 2 | (인계서 6개 중 3개로 축소) |
| D-07 | 백엔드 **FastAPI 하나** (tRPC/React Flow 연기) | 3주 MVP 스코프. 프론트 본격화는 Sprint 2 | (인계서 풀스택 중 일부 연기) |
| D-08 | 코드는 호스트, 도커는 실행만 (볼륨 마운트) | 코드 즉시 반영 + git은 호스트 레벨 | (표준 방식 확정) |
| D-09 | 스캐폴드는 Git 레포 구조로 | 맥↔리눅스 동기화 + 협업 + 버전관리 | — |
| D-10 | MCP 도구 7종 인터페이스는 인계서 S13 그대로 채택 | 잘 정의됨. 더미 MCP의 계약으로 사용 | (S13 채택) |

## 환경 (확정, 2026-05-22)
- 호스트: kwonlocalserver / Ubuntu 24.04.4 / RTX 3070 8GB / 32GB RAM
- 드라이버 580.159.03 / Docker 29.4.1 / NVIDIA Container Toolkit 1.19.0 (설치됨)
- GPU 패스스루 컨테이너 검증 완료

## 2026-05-22 (오후) — Planner 추가 (Agentic Flow 2단)

| # | 결정 | 사유 |
|---|---|---|
| D-11 | Planner는 '계획'만, 실행은 Executor | 3-tier 권한의 핵심 — 사람이 계획을 보고 승인 |
| D-12 | 각 PlanStep에 권한등급 박기 | Executor 분기 + UI 승인버튼 자동화의 근거 |
| D-13 | LLM은 제안, 규칙이 검증/보정 (후보=진실의원천) | 작은 모델의 환각/누락 방어. LLM이 권한·작업을 못 바꿈 |
| D-14 | guardrails.OPERATION_PERMISSION을 권한 단일소스로 | planner schemas와 동기화. reparse_header/clean_masking/balance_classes 추가 |

### 발견·수정한 버그
- guardrails 매핑에 clean_masking 등 3개 누락 → Planner가 핵심 단계를 조용히 누락.
  원인: 스캐폴드 때 guardrails를 먼저 만들고 Planner를 나중에 설계해 작업목록 불일치.
  교훈: 작업 목록은 schemas(planner)와 guardrails 양쪽 동기화 검증을 CI에 넣을 것.

## 2026-05-24 — Executor + Validator 추가 (Agentic Flow 3·4단 완성)

| # | 결정 | 사유 |
|---|---|---|
| D-15 | Executor가 실제 데이터 변환 (결정론적 Python) | LLM이 데이터 직접 변환은 위험·비결정적. LLM은 계획만 |
| D-16 | L2/L3는 approval_token 게이트 통과해야 실행 | "AI 자동화 두려움" 해소. SI 영업 핵심 |
| D-17 | 변환 전 백업(parquet) + lineage 기록 강제 | rollback 가능 + 컴플라이언스(재현·추적) |
| D-18 | Validator가 lineage 누락을 컴플라이언스 위반으로 검출 | 기록 안 된 변환 차단 |
| D-19 | schemas 파일명 고유화 (planner_schemas/executor_schemas) | 동일 'schemas' 이름 import 충돌 버그 수정 |

### 발견·수정한 버그
- agents/planner/schemas.py ↔ agents/executor/schemas.py 이름 충돌.
  sys.path에 둘 다 등재되니 planner가 executor의 schemas를 잘못 import.
  → 파일명 고유화로 해결. (importlib 동적로드는 pydantic 타입참조가 깨져 실패 → 파일명 변경이 정답)
- 교훈: 에이전트별 모듈 이름은 전역 고유해야. CI에 모듈명 중복 검사 추가 고려.

## 2026-05-24 (이어서) — UI 모델 선택 기능

| # | 결정 | 사유 |
|---|---|---|
| D-20 | llm.generate에 model 파라미터 추가 (요청별 모델) | .env 재시작 없이 UI에서 즉시 교체 |
| D-21 | 대시보드에 모델 드롭다운 (E4B 빠름 / 26B 정밀·느림 라벨) | 같은 데이터를 모델별 비교 시연 가능 |
| D-22 | /api/models 엔드포인트 (Ollama 설치 모델 목록) | UI가 동적으로 모델 목록 표시 |

→ 데모 가치: "같은 데이터를 E4B vs 26B로 즉석 비교"가 발표 시나리오 한 컷이 됨.

## 2026-05-26 — 두 번째 모달리티 inspection-image 추가 (재사용성 실증)

| # | 결정 | 사유 |
|---|---|---|
| D-23 | inspection-image MCP 서버 추가 (포트 8102) | 모달리티 분할의 핵심 차별점 "재사용" 실증 |
| D-24 | 7개 도구 계약을 timeseries와 100% 동일하게 | 같은 계약 = Agent 코드 변경 0. 이게 재사용의 실체 |
| D-25 | 더미는 KAMP 실구조 모사 (폴더=라벨, .txt페어, 해상도/모드 혼재) | IMAGE_DATA_ROOT 한 줄로 실데이터 교체 가능 |
| D-26 | Inspector/Executor에 modality 라우팅 | modality 파라미터만 바꾸면 같은 코드가 양쪽 처리 |
| D-27 | 이미지 작업 의미 매핑 (clean_masking→모드통일, fill_missing→해상도통일) | CSV 작업명을 이미지 의미로 재해석, 권한·lineage 계약 유지 |

### 핵심 증명
timeseries에서 만든 Agent(Inspector→Planner→Executor)·Harness·권한모델·대시보드를
★코드 한 줄 안 바꾸고★ 이미지 모달리티에 그대로 적용. MCP 서버 1개만 새 로직으로 추가.
→ "공정마다 새로 짤 필요 없음" 영업 메시지가 코드로 증명됨.

### 더미 이미지 챌린지 (KAMP 모사)
- wafer_defect: 6클래스 폴더라벨, 해상도 혼재, RGBA, SCATCH 4자리 padding
- welding_bead: .txt 동명 페어, 대용량 grayscale
- press_aluminum: 혼합구조(샘플 라벨X + 학습용 라벨O), 사이즈 변동

## 2026-05-26 (이어서) — 최종 목적지 명확화 + event-log 모달리티 착수

### ★최종 목적지 (프로젝트 북극성) — 잊지 말 것★
지금은 "데이터셋 1개 → 모달리티 판단 → 전처리"의 모달리티 단위 처리다.
최종 목적지는 ★공장 단위 통합★:
  A공장 ─┬─ 주문생산 라인 (order)
         ├─ 검사 라인 (inspection-image)
         ├─ 예지보전 라인 (timeseries)
         └─ 이벤트로그 라인 (event-log)
  → 4개 각기 다른 데이터가 ★하나의 목적(예: 에너지 비용 최적화)★ 아래 표준화·통합
  → ★A공장 표준 대시보드★로 출력

두 층으로 구분 (혼동 금지):
  1층 = 모달리티 표준화 (지금): 각 데이터를 깨끗한 분석가능 형태로. 목적 무관, 데이터 품질 관점.
  2층 = 목적 지향 통합 (나중): 전처리된 4개를 목적(에너지최적화)에 맞게 결합·피처링. ML/RAG와 함께.
순서: 모달리티 4개(1층) → 공장 통합·목적·ML/RAG(2층). 현재 1층 진행 중.

| # | 결정 | 사유 |
|---|---|---|
| D-28 | 프로젝트 북극성 = 공장 단위 통합 (모달리티는 수단) | 4개 모달리티 완성이 "공장의 모든 라인 처리 가능"의 전제 |
| D-29 | 전처리 표준화(1층)와 목적 통합(2층) 분리 | 1층은 목적 무관 품질 정제, 2층은 목적 의존 결합 |
| D-30 | event-log 더미 = Excel 멀티시트 + CSV 혼재 | 실데이터가 혼재 형태. 멀티시트 통합이 시그니처 챌린지 |
| D-31 | event-log에서 balance_classes(L2) 최초 실사용 | PASS_YN 2.85% 극심 불균형 감지→보정 제안→승인 (새 데모 시나리오) |

### Harness 검증 강화 — 다음 스텝으로 예약 (잊지 말 것)
현재 "LLM 계획 → 그대로 실행"이고 ★결과 검증이 비어있음★ (Harness 4번째 요소 후반부).
증거: wafer_defect EXECUTE 시 clean_masking이 width/height에 ★중복 제안★됨 (normalize_mode 2회).
모달리티 4개 완성 후 구현할 것:
  - 변환 전후 비교 검증 (dtype 정말 바뀌었나, 결과 측정)
  - 계획 무결성 검증 (중복 작업 감지 — 위 width/height 중복)
  - 회귀 검증 (전처리가 데이터를 망치지 않았나)
  - 검증 실패 시 롤백/사람 재검토 라우팅
이게 "LLM이 틀려도 시스템이 잡는다"는 SI 신뢰성 메시지의 핵심.

### event-log 구현 완료 (2026-05-26)
- mcp-servers/event-log (포트 8103): 7개 도구 계약 동일, 멀티시트/불균형/NaN 로직
- balance_classes(L2) 최초 실사용: PASS_YN 2.83% 감지→보정 제안→승인
- 멀티시트 Excel 통합 (LOT_NO outer merge) — 챌린지 8 해결
- Inspector flag: 불균형/멀티시트/NaN메타 감지 추가
- 3개 모달리티(timeseries/image/event-log) 동작. order만 남음.

### order 구현 완료 — ★4개 모달리티 전부 완성★ (2026-05-26)
- mcp-servers/order (포트 8104): timeseries tools 복제 + ORDER_DATA_ROOT 교체
- 더미: order_demand_cp949.csv (CP949+한글헤더, 1000행)
- order는 CSV라 Executor의 timeseries 경로 재사용 (_resolve에 modality 분기)
- CP949 인코딩 흡수 검증 완료

### ★마일스톤: 4개 모달리티 완성 (1층 = 모달리티 표준화 완료)★
timeseries / inspection-image / event-log / order 모두 동작.
같은 Agent·Harness·권한·대시보드로 4가지 데이터 형태(CSV/이미지폴더/Excel멀티시트/CP949) 처리.
→ "어떤 라인 데이터가 와도 처리 가능" = 공장 단위 통합(2층)의 전제 조건 충족.
다음: Harness 검증 강화 → 공장 통합·목적·ML/RAG (2층).

## 2026-05-27 — STEP 1: Validator 완성 + 우려1(의미 그룹) 동시 구현

| # | 결정 | 사유 |
|---|---|---|
| D-32 | 의미 그룹 패턴을 모달리티별 MCP 서버 안에 (semantic.py) | "전용 공구함" 개념 일치. 각 도메인 패턴은 그 서버가 앎 |
| D-33 | 규칙(정규식) 우선 + LLM은 unknown만 보조 | modality_guess 오판 교훈 — LLM 분류는 못 믿음 |
| D-34 | normalize_group: 그룹당 1작업 (멤버 N개여도) | 중복 방지 + 시퀀스/프로파일 의미 보존 |
| D-35 | 시퀀스/프로파일은 그룹 공통 mean/std 정규화 | 컬럼 독립 정규화 시 추세·형상 소실 방지 (우려1 핵심) |
| D-36 | Validator 4종 검증 (컴플라이언스/변환/무결성/회귀) | "LLM이 틀려도 시스템이 잡는다" — Q1 약점 해결 |
| D-37 | Validator를 /api/execute에 연결 + 대시보드 표시 | 4단계(Inspector→Planner→Executor→Validator) 실동작 완성 |

### STEP 1 완료 — 4단계 Agentic Flow 진짜 완성
- 우려1: cnc_machine_injection 35컬럼→6그룹, 사출시퀀스10개→1작업(추세보존)
- Validator: 정상통과 + 결함4종(중복/누락/손실/변환실패) 모두 잡음 검증
- width/height 중복 버그 = 계획무결성 검증으로 잡힘 (우려1+Validator 동시효과)
- 다음: STEP 2 (Planner OptionTree — 우려2)

## 2026-05-27 (이어서) — 승인 반복 버그 수정 (step_key 기반)

### 버그: "승인하고 실행"이 무한 반복
증상: 사출 데이터(normalize_group 5개) EXECUTE 시 승인해도 일부만 완료, 나머지 계속 대기.
원인: 승인이 order(순서번호) 기준인데, Planner가 매 EXECUTE마다 LLM으로 계획 재생성 →
      LLM이 작업 순서를 비결정적으로 배열 → 승인한 order가 다른 작업을 가리킴.

| # | 결정 | 사유 |
|---|---|---|
| D-38 | 승인을 order(가변) → step_key(안정) 기반으로 변경 | LLM 순서 비결정성에도 승인이 안 어긋남 |
| D-39 | step_key = "operation:semantic_group(or target_column)" | 순서 무관 안정적 식별자 |
| D-40 | modality_guess 검증은 자동분류 기능과 한 묶음으로 미룸 | 지금은 사용자가 모달리티 명시 → guess는 참고용. 자동분류 때 검증 동반 |

수정 범위: planner_schemas(step_key property), planner(plan에 주입),
backend(approved_keys), executor(approved_keys set 기반 전 경로), frontend(step_key 체크박스).
검증: LLM 순서 바꿔도 승인 유지(all_done=True), 4개 모달리티 회귀 없음.

### STEP 1.5 예고 (팀원 검토 반영 — Module Catalog)
의미그룹화는 "이 컬럼이 무엇"까지만. "정상범위/공정소속/추천모델" 도메인지식 = Module Catalog 필요.
조정: ① Catalog는 규칙이 쓰는 지식(LLM 판단재료 아님) ② slot contract는 YAML 필드만(자동분류때 활성화)
③ STEP1 닫고 Module Catalog는 STEP 1.5 분리 ④ 노드 5개(사출/CNC/프레스/검사/PdM)로 시작
→ Validator에 5번째 "도메인 범위 검증" 추가 예정. 드래그앤드롭 UI는 STEP 3.
