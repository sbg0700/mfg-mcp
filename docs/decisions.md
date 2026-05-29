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

## 2026-05-27 (이어서) — lineage/데이터셋 저장 검증 + 조회 엔드포인트

### 검증 결과
- 데이터셋 저장: data/processed/에 <ds>__backup.parquet + <ds>__processed.parquet (4개 데이터셋 8파일 확인)
- lineage: 인메모리 _STORE에 변환별 기록 (의미그룹/전략/멤버수/승인ID/롤백여부) — 7건 정상
- 사출 정규화 검증: 1ST INJECTION VELOCITY 평균=-1.412 (0 아님) = 그룹공통 정규화로 시퀀스 추세 보존 증명

| # | 결정 | 사유 |
|---|---|---|
| D-41 | /api/lineage 조회 엔드포인트 추가 | lineage가 기록만 되고 볼 수 없던 문제. 추적가능성(SI 컴플라이언스) 가시화 |
| D-42 | backend도 from harness import lineage (executor와 동일 경로) | 같은 _STORE 공유 보장 (경로 다르면 별도 store 생성됨) |

### 알려진 한계 (추후)
- lineage 인메모리 → 컨테이너 재시작 시 소실. Sprint 2에서 PostgreSQL로 이전 (D-41 관련)
- processed parquet 다운로드/미리보기 UI 없음 → 2층에서

## 2026-05-28 — STEP 1B-1: Module Catalog (lines.yaml + modules.yaml) + Planner·Validator 확장

명세: `docs/specs/STEP_1B-1_module_catalog.md` (claude.ai 세션에서 확정).

| # | 결정 | 사유 |
|---|---|---|
| D-43 | 카탈로그에 typical_ranges 디폴트 값 금지, constraint_keys 구조만 | 정상범위는 공장·설비·재료마다 달라 디폴트가 틀리면 잘못된 판단 유발. "규칙이 결정"의 연장 — 카탈로그는 구조 제안, 값은 사용자 입력 |
| D-44 | `catalogs/lines.yaml` = blueprint 부록 A 그대로 (3 Line × 18 Node × 34 Module) | 사전정의 파이프라인 구조 단일 소스. Page 2 CatalogPanel + /api/lines가 이 파일 하나만 읽음 |
| D-45 | `catalogs/modules.yaml` 5 Node부터 시작 (injection_molding/cnc_cutting/press_forming/semiconductor_inspect/pdm) | 4 모달리티 더미를 커버하는 최소셋. 나머지 13 Node는 한 줄씩 점진 확장 |
| D-46 | `module_context`는 LLM '참고 맥락'으로만 주입 (판단 재료 아님) | 후보(candidates)가 진실의 원천 유지. LLM이 module_context로 새 작업/권한 못 만듦 (가드레일 유지) |
| D-47 | constraints는 규칙(`_candidate_operations`)이 후보 추가에 사용, LLM 아님 | constraint 키와 일치하는 컬럼이 데이터에 있으면 remove_outlier 후보 추가 — 결정론 |
| D-48 | Validator 5번째 검증 `_check_constraint_violation` — 처리 후 parquet에서 범위 위반 행 수 산수 | 사용자 입력 constraints 기준 (카탈로그 typical_ranges 아님 — 없음). LLM 안 씀 |
| D-49 | constraints 비면(1층 단일모드) 5번째 검증 skip | 기존 4 모달리티 회귀 0 — checks.constraint=True (위반 없음으로 통과) |
| D-50 | `/api/execute`에 constraints/module_context 옵션 필드 추가 (기본 None) | UI 없이도 endpoint로 검증 가능. 기존 호출(`{dataset_id,modality,approved_keys}`)는 그대로 동작 |

### 구현 산출물
- `catalogs/lines.yaml` (3 Line × 18 Node × 34 Module — 부록 A 그대로)
- `catalogs/modules.yaml` (5 Node, constraint_keys 구조만, typical_ranges 0)
- `agents/planner/planner.py` — `_candidate_operations(profile, constraints)`, `plan(...,module_context=...)`
- `agents/validator/validator.py` — `_check_constraint_violation`, `validate(...,constraints=...)`
- `backend/main.py` — `GET /api/lines`; `POST /api/execute`에 constraints/module_context 옵션
- `backend/requirements.txt` — PyYAML 명시 (런타임 컨테이너는 이미 보유 중)

### 검증 결과 (명세 §9 체크리스트)
- 3 Line / 18 Node / 34 Module 모두 정의, yaml.safe_load 파싱 성공
- modules.yaml 5 Node, typical_ranges 부재(코드 검사로 확인)
- `GET /api/lines` 200 + 카탈로그 JSON 반환 (실 endpoint hit)
- `plan(profile, constraints, module_context)`: constraints 위반 가능 컬럼 → remove_outlier 후보 추가, module_context는 프롬프트에 '참고용' 라인으로만 들어감, 옵션 빈 호출은 기존대로 동작
- `_check_constraint_violation`: cnc_machine_injection의 1ST INJECTION VELOCITY [40,70] → 172/800행 위반 결정론 검출, severity=medium
- 4 모달리티(timeseries/inspection-image/event-log/order) 회귀 0 — passed=True, checks 5종 모두 통과

### STEP 1B-1 완료 마일스톤
1층(모달리티 표준화) 위에 ★공정 축(Line/Node/Module)이 처음으로 카탈로그로 정의★됨.
이게 2층(공장 단위 통합)으로 가는 가교 — 사용자는 이제 "어떤 라인의 어떤 노드 데이터인지" 명시 가능,
시스템은 그 맥락에서 constraints를 받아 결정론적으로 검증.
다음: STEP 1B-2 (Resumable Orchestrator + Context Aggregator) → STEP 1B-3 (Mini UI 6페이지).

## 2026-05-28 — STEP 1B-2a: Resumable Orchestrator (폴링형) + 미업로드 알람

명세: `docs/specs/STEP_1B-2a_orchestrator.md` (claude.ai 세션에서 확정).
스코프 분할: 1B-2a(이번, Orchestrator+judge) / 1B-2b(다음, Context Aggregator) / 1B-3(이후, UI+SSE).

| # | 결정 | 사유 |
|---|---|---|
| D-51 | suspend-and-return + 폴링 (blueprint의 blocking awaiter `wait_for_approval` 채택 안 함) | SSE/이벤트루프 awaiter는 디버깅 복잡. 폴링은 상태머신을 dict로 직접 관찰 가능, 1B-3에서 UI가 SSE를 얹기 전까지 단순함 우선 |
| D-52 | 세션 상태는 인메모리 dict (`backend/session_store.py`, `_SESSIONS`) | lineage 패턴(D-41) 동일. postgres 이전은 Sprint 2 |
| D-53 | `pipeline_full.modules[].datalake_id` = 기존 dataset_id 직접 사용 (Data Lake catalog 미도입) | 카탈로그 레이어는 1B-3 이후. 지금은 4 모달리티 더미 dataset_id로 충분 |
| D-54 | modality 결정 — module.modality 명시 > node_id 매핑(검사/주문) > timeseries 폴백 | 자동 modality 분류(D-40)는 여전히 미룸. 명시/매핑이 안전 |
| D-55 | `llm_judge_data_necessity`는 알람 문구만 생성, 흐름 제어 0 | 환각 방어 연장(D-13, D-46) — 알람은 session["alarms"] 기록만, missing 모듈은 무조건 skip하고 진행. 판단 실패 시 likely_essential=False 안전 폴백 |
| D-56 | `/approve`는 step_key 단건 누적, resume은 클라이언트가 `/execute_pipeline` 재호출로 트리거 | blocking 모델의 awaiter release(`notify_approval`) 안 씀. completed_module_keys/completed_stage_orders로 멱등 skip |
| D-57 | 1층 `/api/execute`(단일 데이터셋) 시그니처 보존, 파이프라인은 별도 엔드포인트로 분리 | 회귀 0 보장 — 4 모달리티 검증된 1층 경로 그대로 |
| D-58 | 세션 응답에 `public_view(session)` — `pipeline_full` 포함, JSON 직렬화 가능 형태만 | 디버그/폴링 시 UI에 풍부한 진행 정보 제공 |

### 구현 산출물
- `backend/session_store.py` (신규) — `create_session`/`get_session`/`save_session`/`public_view`
- `agents/planner/data_necessity.py` (신규) — `llm_judge_data_necessity(stage, missing, uploaded, model)`
- `backend/main.py` — 4 엔드포인트 추가:
  - `POST /api/sessions/create` (pipeline_full 주입 → session_id)
  - `POST /api/execute_pipeline` (resumable, suspend-and-return)
  - `GET  /api/pipeline/{session_id}/status` (폴링)
  - `POST /api/pipeline/{session_id}/approve` (step_key 누적)
- `backend/main.py` 내부 헬퍼: `_resolve_modality(module, node_id)`

### 검증 결과 (명세 §9 체크리스트)
- `POST /api/sessions/create` → uuid4 session_id 반환
- 1차 `/api/execute_pipeline`: cnc_machine_injection (constraints `{"1ST INJECTION VELOCITY":[40,70]}`) → `status=awaiting_approval`, pending 6 step_keys(remove_outlier + normalize_group ×5), alarm 1건(stage 0, missing maintenance 모듈)
- `/approve` ×6 → `approved_step_keys` 누적 [1..6]
- 2차 `/api/execute_pipeline` → 멈췄던 module 0.0부터 resume → `status=completed`, completed_stage_orders=[0], 알람 1건 유지(재알람 없음), validation.passed=True
- `/api/pipeline/{id}/status` 폴링 → completed/pending=None/alarms=1 그대로
- 1층 `/api/execute` 회귀 0 (mct_tool_manage_clean → passed=True, 5종 checks 모두 통과)
- 2번째 모달리티(order/order_demand_cp949) 파이프라인 단일 호출 완료(L1만, passed=True)
- `python3 -m py_compile` 통과 (main, session_store, data_necessity, planner, validator, executor, inspector)
- 외부 API 호출 0, 모달리티 4종 유지 (5번째 미추가)

### LLM judge 실제 출력 (참고)
입력: stage `injection_molding`, missing `maintenance/?`, uploaded `process/cnc_machine_injection`
LLM 응답(요약): `{"likely_essential": false, "alarm_ko": "현재 'process/cnc_machine_injection' 모듈만 업로드되어 주입 성형 공정 자체의 작동 과정에 대한 정보는 충분합니다. 따..."}`
→ 흐름은 missing 모듈을 그대로 skip하고 진행 (LLM이 결정 못 함).

### STEP 1B-2a 완료 마일스톤
세션 상태 머신이 처음으로 실동작. 다중 Stage·Module을 ★suspend ↔ approve ↔ resume★으로
폴링 처리. 1층 단일 데이터셋 경로(`/api/execute`)와 공존. 1B-3 UI에서 SSE 얹기 직전 단계.
다음: STEP 1B-2b (Context Aggregator — 4단 판단 기록을 EDA/모델링으로 전파).

## 2026-05-28 — STEP 1B-2b: Context Aggregator (결정론) + AggregatedContext 전파

명세: `docs/specs/STEP_1B-2b_context_aggregator.md` (claude.ai 세션에서 확정).
1B-2의 마지막 조각 — Orchestrator(1B-2a)가 채운 세션 기록을 결정론으로 집계해
Page 5/6 LLM 프롬프트의 컨텍스트 소스(`AggregatedContext`)를 만든다.

| # | 결정 | 사유 |
|---|---|---|
| D-59 | Context Aggregator는 LLM 호출 0 (생명선) — 추론 엔진 import 0, 모델 호출 0 | blueprint Part 4-4 "환각 위험 0" 메커니즘의 핵심. LLM이 1줄이라도 끼면 본 컴포넌트 존재 이유가 무너짐. `grep "from llm\|import llm\|generate("` 0건으로 검증 |
| D-60 | `agent_records`는 원본 거의 그대로 보존 (요약 X) | Page 5/6 LLM이 직접 활용하는 컨텍스트. 손실 0이 spec-1 §1-9-7의 검증 기준 |
| D-61 | `key_findings` 추출은 규칙·임계 비교·정규식만 | 같은 입력 → 같은 출력 100% 재현. 직접 호출 2회 deepequal 통과 |
| D-62 | `downstream_implication`은 finding type → 한 줄 함의 템플릿 매핑 | 사전정의 7종 템플릿 (`class_imbalance`/`missing_values`/`dtype_mixed`/`transformation_applied`/`constraint_violation`/`validation_concern`/`sequence_normalized`). finding 없으면 "특이사항 없음." |
| D-63 | execute_pipeline 완료 직후 자동 트리거 + 캐시 (`session["aggregated_context"]`) | blueprint Part 2-5 마지막 줄 정합. 결정론이라 재호출 안전, 캐시는 성능용 |
| D-64 | `user_intent`는 이번 범위 항상 None (Page 5 미구현) | 스키마 자리만 두고 채우지 않음 — 1B-3 이후 Page 5 분석목적 UI에서 채움 |
| D-65 | `pipeline_constraints` 키 형식 = `"stage_order.module_index"` (module_key 형식 일관) | session의 `completed_module_keys`·`pending.module_key`와 동일 표기 |
| D-66 | 정규화(normalize_group) 후 데이터에 원시 단위 constraint를 적용하면 무의미한 위반이 나옴(예: [40,70] mm/s 제약 vs z-score 값 → 800/800 위반). 현재 Aggregator가 constraint_violation + sequence_normalized를 둘 다 기록해 충돌을 드러냄(추적가능성). Validator의 "정규화 컬럼 제약검증 skip 또는 원본 기준 적용"은 STEP 2~3에서 해결. 지금은 알려진 한계. | 1B-2b 검증 부산물 — Aggregator가 모순을 가시화한다는 사례 자체가 본 컴포넌트의 가치 증명. 즉시 해결책은 다음 단계 |

### 구현 산출물
- `agents/aggregator/__init__.py` (신규 패키지 마커)
- `agents/aggregator/context_aggregator.py` (신규) — 핵심 함수 `aggregate(session) -> AggregatedContext`
  - 영역 A: `pipeline_structure` + `pipeline_constraints` (앞단 입력 보존)
  - 영역 B: `key_findings` (규칙 추출 — Inspector flags + Executor done steps + Validator issues)
  - 영역 C: `function_axis_summary` (process/quality/maintenance/reference)
  - 영역 D: `stage_chain` (main_findings + downstream_implication 템플릿)
  - 영역 E: `agent_records` (4단 기록 원본 보존)
  - 영역 F: `user_intent = None`
- `backend/main.py` — sys.path에 `agents/aggregator` 추가 + execute_pipeline 자동 트리거 + `GET /api/aggregate_context/{session_id}` 추가

### 검증 결과 (명세 §7 체크리스트, 실 HTTP 호출)
- 자동 트리거: completed 응답에 `aggregated_context` 포함 확인
- `GET /api/aggregate_context/{id}`: 5영역 + `user_intent=None` 반환
- key_findings 추출: `constraint_violation` × 1 + `sequence_normalized` × 5 = 6개 (cnc_machine_injection 시연 케이스)
- agent_records 보존 정합성: Inspector flags / Planner 7 steps / Executor 7 results / Validator passed=True 모두 원본 일치
- function_axis_summary: `process=6`, `quality/maintenance/reference=0` (테스트 모듈이 process라 정상)
- stage_chain.downstream_implication: 템플릿 매핑 동작 (constraint_violation + sequence_normalized 템플릿 조합)
- 결정론 재현 100%: endpoint 2회 + 직접 호출 2회 모두 deepequal 통과
- LLM 호출 0건: `grep "from llm\|import llm\|generate("` → exit 1, stdout 비어있음
- 외부 HTTP 라이브러리 0건: `grep "httpx\|requests\.\|urllib\|openai\|anthropic"` → 0건
- 1층 `/api/execute` 회귀 0 (mct_tool_manage_clean → passed=True, 5종 checks)
- 모달리티 4종 유지 (timeseries/inspection-image/event-log/order)
- `python3 -m py_compile` 통과

### 발견된 흥미로운 사실 (검증 부산물)
1B-1에서 본 `1ST INJECTION VELOCITY` constraint `[40, 70]` 위반은 1B-1 단독 테스트에선 172/800행이었는데,
1B-2b 파이프라인에서는 800/800행 위반으로 나옴. 이유: `normalize_group`이 `1ST INJECTION VELOCITY`를
포함한 `injection_sequence` 그룹을 z-score 정규화 → 원시 [40,70] 범위가 정규화된 값에 적용 불가.
Aggregator의 stage_chain.main_findings에 `sequence_normalized(low)` + `constraint_violation(medium)`이
같이 등장하므로 Page 5/6 LLM이 이 순서 충돌을 인지할 수 있게 됨 — 본 컴포넌트의 가치 사례.

### STEP 1B-2b 완료 마일스톤
1B-2 (Orchestrator + Aggregator) 모두 끝. 사용자가 비전했던
★"MCP 표준화 → 4단 판단 기록 → EDA/모델링 컨텍스트"★ 전파 흐름이 결정론으로 보장됨.
다음: STEP 1B-3 (Mini UI 6 페이지) — 지금까지 만든 모든 엔드포인트를 UI로 묶어 시연 가능 형태.

## 2026-05-28 — STEP 1B-2c: Validator 강화 (사전+사후 양방향) + D-66 해결

명세: `docs/specs/STEP_1B-2c_validator_hardening.md` (claude.ai 세션에서 확정).
1B-2b에서 발견한 D-66(정규화 후 원시 단위 constraint 위반 misfire)을 해결하고,
Validator를 사전(Executor 전)+사후(Executor 후) 양방향으로 강화한다.

| # | 결정 | 사유 |
|---|---|---|
| D-67 | constraint 검증은 **원본 backup_path 기준** (processed 아님) | D-66 해결. 사용자 제약은 원시 측정 단위 기준이므로 정규화 전 원본에서 검증해야 정확. z-score 정규화는 단조변환이라 "원본 제약을 원본에서 검증"과 "정규화된 제약을 정규화 데이터에서 검증"은 수학적 동치(원본이 단순). 그룹 공통 정규화로 후자는 μ/σ 어긋남 문제까지 있어 더 복잡 |
| D-68 | Validator는 **"고장 감지"만**, "정상성 판단"·"분포 해석"은 안 함 (Page 5 EDA로) | 검증 layer 분리. 100% 단언 가능한 것(Inf/std==0/그룹 사후조건 이탈)만 결정론으로 잡고, "이 분포가 정상인가/모델링에 적합한가"는 의미 해석이라 LLM(Page 5)으로. typical_ranges 금지(D-43)의 일관성 |
| D-69 | output_health 그룹 정규화 사후조건은 **그룹 단위로만** 검사 (개별 컬럼 평균 0 강제 ❌) | 그룹 공통 정규화는 컬럼 간 추세를 보존하기 위해 컬럼 평균 0이 아닐 수 있음(예: 1ST INJECTION VELOCITY=-1.412 정상). 개별 평균 0 강제하면 추세 보존의 증거를 고장으로 오판. 그룹 멤버 합쳐 z-score 사후조건(평균 0, std 1)만 ±0.1 허용으로 확인 |
| D-70 | 사전 검증 `validate_plan(plan, profile)` 신규 — 결정론 (순서/충돌/L3) | Executor 전에 "계획 자체"의 타당성 한 번 더 거름. blocking 기준은 high(작업 충돌)만, 순서 의심(medium)·L3(low)은 경고만(과한 차단 회피). 영업 메시지를 "사후"에서 "사전+사후 양방향"으로 강화 |
| D-71 | std==0 감지는 **변환에 닿은 컬럼**에 한해 — 원래 상수 컬럼 false positive 회피 | execution.results의 done step에서 target_column / group_members 집합을 만든 후 그 집합 안에서만 검사 |
| D-72 | ExecutionResult에 `backup_path` 필드 추가 + executor가 채우기 (timeseries/order, event-log) | D-67 전제. 이미지 모달리티는 parquet 아니라 None |
| D-73 | 사전 검증 blocking 시 — `/api/execute`는 실행 중단 + 결과 반환, `/api/execute_pipeline`은 해당 모듈 차단 + 세션 error | 1B-2a 폴링 흐름과 일관. 실 정상 계획에서는 발생 안 함(LLM이 후보 외 작업 못 만드는 환각 방어 + 가드레일 덕분) |

### 구현 산출물
- `agents/executor/executor_schemas.py` — `ExecutionResult.backup_path` 필드 추가
- `agents/executor/executor.py` — timeseries/order, event-log 경로에서 backup_path 변수 추출 + ExecutionResult에 포함
- `agents/validator/validator.py`:
  - `_check_constraint_violation` 수정 — backup_path 우선, processed 폴백(레거시 안전)
  - `validate_plan(plan, profile)` 신규 — 순서 규칙(_ORDER_RANK) + 작업 충돌(dropped 집합) + L3 정보성
  - `_check_output_health(execution)` 신규 — Inf, std==0(touched_cols 한정), 그룹 정규화 사후조건
  - `validate()` — 5종 → 6종(`output_health` 추가)
- `backend/main.py`:
  - `/api/execute` — run_plan 후 validate_plan, blocking이면 실행 중단 + 결과 반환
  - `/api/execute_pipeline` — 모듈 루프 안에서 run_plan 후 validate_plan, blocking이면 모듈 차단 + 세션 error

### 검증 결과 (명세 §6 체크리스트, 실 HTTP 호출)
- **LLM 호출 0건**: `grep -nE "from llm|import llm|generate\("` validator.py → exit 1, stdout 비어있음 ✅
- **D-66 해결**: cnc_machine_injection [40,70] → **172/800 위반** (1B-2b의 800/800에서 정확한 원본 기준으로 수정) ✅
  - 결과의 `source` 필드 = `"원본(backup)"`
- **validate_plan 정상 계획**: plan_ok=True, n_high=0
- **validate_plan 결함주입**: drop_column + 같은 컬럼 변환 → `plan_conflict(high)`, blocking=True
- **validate_plan 순서 역행**: normalize→encoding → `plan_order(medium)`, blocking=False (경고만, 과한 차단 회피)
- **output_health 정상**: 1ST INJECTION VELOCITY 개별 평균=-1.412여도 통과 (그룹 평균 ≈0/std≈1 검사 통과로 추세 보존 인정)
- **output_health 결함주입**: 상수 컬럼 정규화 시뮬 → std==0 감지(high)
- **파이프라인 회귀**: 1B-2a/2b 시나리오에서 backup_path 사용 + Aggregator key_findings도 172/800 갱신됨
- **4 모달리티 회귀 없음**: timeseries / order / event-log / inspection-image
- `python3 -m py_compile` 통과

### 핵심 효과
1. D-66 흔적 제거 — 사용자 제약 검증이 의미 있는 수로 정확하게(172/800)
2. Validator가 "사전+사후 양방향" → 영업 메시지 강화 ("LLM이 틀려도 Executor 전후 모두 잡음")
3. 출력 고장 감지는 100% 단언 가능한 것만 — Page 5 EDA LLM 영역과 깔끔히 분리
4. 개별 컬럼 평균 0 강제 안 함 → 그룹 정규화의 추세 보존 특성을 고장으로 오판하지 않음

### STEP 1B-2c 완료 마일스톤
1B-2 패키지(2a Orchestrator + 2b Aggregator + 2c Validator 강화) 완전 종료.
사후뿐 아니라 사전 검증까지 가지면서 "LLM은 제안, 규칙이 결정"의 결정론 영역이 양방향으로 완비됨.
다음: STEP 1B-3 (Mini UI 6 페이지) — 백엔드 모든 엔드포인트를 UI로 결합해 시연 가능 형태.
