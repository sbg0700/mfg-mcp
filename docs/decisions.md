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
**코드 한 줄 안 바꾸고** 이미지 모달리티에 그대로 적용. MCP 서버 1개만 새 로직으로 추가.
→ "공정마다 새로 짤 필요 없음" 영업 메시지가 코드로 증명됨.

### 더미 이미지 챌린지 (KAMP 모사)
- wafer_defect: 6클래스 폴더라벨, 해상도 혼재, RGBA, SCATCH 4자리 padding
- welding_bead: .txt 동명 페어, 대용량 grayscale
- press_aluminum: 혼합구조(샘플 라벨X + 학습용 라벨O), 사이즈 변동

## 2026-05-26 (이어서) — 최종 목적지 명확화 + event-log 모달리티 착수

### **최종 목적지 (프로젝트 북극성) — 잊지 말 것**
지금은 "데이터셋 1개 → 모달리티 판단 → 전처리"의 모달리티 단위 처리다.
최종 목적지는 **공장 단위 통합**:
  A공장 ─┬─ 주문생산 라인 (order)
         ├─ 검사 라인 (inspection-image)
         ├─ 예지보전 라인 (timeseries)
         └─ 이벤트로그 라인 (event-log)
  → 4개 각기 다른 데이터가 **하나의 목적(예: 에너지 비용 최적화)** 아래 표준화·통합
  → **A공장 표준 대시보드**로 출력

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
현재 "LLM 계획 → 그대로 실행"이고 **결과 검증이 비어있음** (Harness 4번째 요소 후반부).
증거: wafer_defect EXECUTE 시 clean_masking이 width/height에 **중복 제안**됨 (normalize_mode 2회).
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

### order 구현 완료 — **4개 모달리티 전부 완성** (2026-05-26)
- mcp-servers/order (포트 8104): timeseries tools 복제 + ORDER_DATA_ROOT 교체
- 더미: order_demand_cp949.csv (CP949+한글헤더, 1000행)
- order는 CSV라 Executor의 timeseries 경로 재사용 (_resolve에 modality 분기)
- CP949 인코딩 흡수 검증 완료

### **마일스톤: 4개 모달리티 완성 (1층 = 모달리티 표준화 완료)**
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
1층(모달리티 표준화) 위에 **공정 축(Line/Node/Module)이 처음으로 카탈로그로 정의**됨.
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
세션 상태 머신이 처음으로 실동작. 다중 Stage·Module을 **suspend ↔ approve ↔ resume**으로
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
**"MCP 표준화 → 4단 판단 기록 → EDA/모델링 컨텍스트"** 전파 흐름이 결정론으로 보장됨.
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

## 2026-05-29 — STEP 1B-3a: Frontend 골격 + Page 1·2 + 세션 엔드포인트 보강

명세: `docs/specs/STEP_1B-3a_frontend_page1_2.md` (claude.ai 세션에서 확정).
1B-3 분할 — 3a(이번): React+Vite 골격 + Page 1·2 + 세션 엔드포인트, 3b: Page 3·4, 3c: Page 5·6 UI.

| # | 결정 | 사유 |
|---|---|---|
| D-74 | `/api/sessions/create`는 `line_id`와 `pipeline_full` **둘 다** 허용 (어느 하나 필수) | Page 1은 line_id만 가능, 기존 직접 호출(curl 테스트, 1B-2a 인계 검증)은 pipeline_full로 회귀 없이 동작 |
| D-75 | 세션 dict 최상위에 `line_id` 별도 저장 | GET /sessions/{id}와 Page 2가 line_id를 즉시 조회 — pipeline_full 안에서 매번 파싱하는 번거로움 회피 |
| D-76 | React 18 + Vite + react-router-dom 최소 의존성. Tailwind/차트 라이브러리 금지 | 빌드 의존성/빌드 시간 최소화. dev서버는 121ms 부팅, 프로덕션 빌드 173KB(57KB gzip) |
| D-77 | 드래그앤드롭은 HTML5 native (의존성 0) | react-dnd 같은 라이브러리 추가 안 함. dataTransfer로 {function, hint_dataset, source_node_id} 전달 |
| D-78 | Page 2 검증 규칙: 같은 노드만 / max_modules 이하 / 중복 금지 / 1+ 모듈 1+ Stage 필수 | spec-1 Part 3-6. 드롭 시 즉시 토스트로 거부, "다음" 클릭 시 최소 모듈 강제 |
| D-79 | Function 색상: process=파랑, quality=초록, maintenance=주황, reference=회색 | spec-1 Part 3-3. CSS 변수(--c-process 등)로 단일 소스 관리 |
| D-80 | dev 모드는 Vite 별도 컨테이너(docker-compose 미수정), 백엔드와 같은 docker network(`manufacturing-mcp_default`)로 proxy target = `http://mfg-backend:8000` | "docker compose 변경 최소화" 정책 준수. `VITE_API_TARGET` 환경변수로 호스트 직접 실행도 지원 |
| D-81 | 기존 `frontend/index.html` 다크 대시보드 → `_legacy_dashboard.html`로 보관, 백엔드 `/` 가 그대로 서빙 | 회귀 0. 레거시 데모는 backend:8000/ 에서, 새 React 앱은 vite:5173/에서 분리 |

### 구현 산출물
- 백엔드 (`backend/main.py`):
  - `POST /api/sessions/create` 수정 — `line_id` 또는 `pipeline_full` 둘 다 허용
  - `GET /api/sessions/{session_id}` 신규 — public_view + line_id 보강
  - `PUT /api/sessions/{session_id}/structure` 신규 — Page 2 출력 저장
  - `FRONTEND` 경로를 `_legacy_dashboard.html`로 변경 (레거시 보존)
- 프론트엔드 (`frontend/`, React+Vite):
  ```
  package.json, vite.config.js, index.html, .gitignore
  src/
    main.jsx, App.jsx, api.js, styles.css
    components/{Breadcrumb, ModelDropdown, Toast, ModuleCard}.jsx
    step1_line/LineSelectPage.jsx
    step2_user_input_pipeline/{PipelineBuildPage, CatalogPanel, StageBox}.jsx
  ```

### 검증 결과 (명세 §8 체크리스트)
- 백엔드 5개:
  - `POST /sessions/create {line_id}` → uuid + line_id 반환
  - `POST /sessions/create {pipeline_full}` 회귀 → 동작
  - `GET /sessions/{id}` → 복원 (없으면 404)
  - `PUT /sessions/{id}/structure` → status="structured", stage_count/module_count 반환
  - `GET /api/models` 기존 그대로 (변경 없음)
- 프론트엔드:
  - `docker run node:20-alpine npm install` 65 packages 12초
  - `npm run build` 성공 — 173 KB JS(57 KB gzip), 3.6 KB CSS, 빌드 667ms
  - `npm run dev` 121ms 부팅, Vite 5173에서 React 앱 서빙
  - Vite proxy로 `/api/lines` → 3 Line JSON 반환 정상
  - Vite가 `/src/*.jsx` 트랜스폼해서 서빙 정상 (PipelineBuildPage.jsx 26 KB 응답)
- 통합 Page 1 → Page 2 시뮬레이션 (curl로 Vite proxy):
  - Page 1: POST /sessions/create {line_id} → session_id
  - Page 2 entry: GET /sessions/{id} → status=created, stages=[]
  - Page 2 PUT /structure: 2 stage, 3 module 저장 → status=structured
  - Page 2 새로고침: GET → 저장한 stages·modules 그대로 복원
  - 1B-2a 호환: pipeline_full 직접 호출도 그대로 동작

### STEP 1B-3a 완료 마일스톤
처음으로 **브라우저 가능한 React 앱**이 등장. Page 1 라인 선택 → Page 2 드래그앤드롭으로 파이프라인 구성 → 세션에 PipelineStructure 저장까지 실동작.
다음: STEP 1B-3b (Page 3 데이터·제약 입력 + Page 4 표준화 진행/승인) — 1B-2a 폴링 흐름을 UI로 노출.

## 2026-05-29 — STEP 1B-3b: Page 3 (데이터·제약 입력) + Page 4 (표준화 진행/승인)

명세: `docs/specs/STEP_1B-3b_page3_4.md` (claude.ai 세션에서 확정).
1B-2a 폴링 흐름(suspend/approve/resume)이 처음으로 UI 카드로 사용자에게 노출됨.

| # | 결정 | 사유 |
|---|---|---|
| D-82 | **데이터 비종속성** — Page 3·4 어떤 코드도 특정 데이터의 파일명·컬럼명에 하드코딩 ❌ | KAMP 등 실데이터 교체 시 코드 변경 0. `/api/datasets/all`은 디렉터리 스캔, modules.yaml constraint_keys는 구조만(typical_ranges 값 0, D-43 일관) |
| D-83 | Page 3·4 UI는 폴링형 (SSE 미사용) — D-51 일관 | execute_pipeline 응답이 곧 상태 전환. 별도 폴링 루프는 옵션. GET /sessions/{id} 는 새로고침 복원용 |
| D-84 | Page 3 modality 결정 = 백엔드 `_resolve_modality`와 동일 규칙 (D-54) — `frontend/src/lib/modality.js` 단일 소스 | UI 데이터셋 필터링이 실제 백엔드 실행 modality와 일치해야 데이터 선택이 의미있음. 자동 modality 분류(D-40)는 여전히 미룸 |
| D-85 | 데이터 업로드 버튼은 자리(placeholder)만 — 실제 업로드 로직 ❌ (이번 범위 밖) | 기존 데이터셋 선택만으로 데모 전체 흐름 완성. 업로드는 STEP 3 |
| D-86 | 승인 카드: L2=주황, L3=빨강, L1=비표시 (자동 실행) | 권한 등급별 시각 구분, L1은 게이트 없으니 승인 카드에 안 옴 |
| D-87 | "전체 승인" + "승인 후 계속" 분리 — approve는 누적, resume은 execute_pipeline 재호출 (D-56 폴링형) | 사용자가 일부만 승인하고 멈출 수도 있게 분리. 모든 step 승인된 후에만 "계속" 활성화 |
| D-88 | Page 4 완료 시 finding.detail 전체를 그대로 노출 (Aggregator key_findings → FindingsList) | "172/800 위반" 같은 핵심 수치를 UI가 다시 가공하지 않음. detail은 결정론 산수 결과(D-67) 그대로 |
| D-89 | 알람 배너: 사용자에게 "Page 3 으로 돌아가기" 또는 "무시" 선택 — LLM은 알람만, 결정은 사용자 (D-55) | 알람을 UI에서 막거나 강제하지 않음. 환각 방어 메커니즘 일관 |
| D-90 | (알려진 한계 → **D-93에서 해결 완료**, STEP 1B-3c) Page 3 제약 폼이 modules.yaml의 추상 constraint_key(예: `injection_velocity`)를 보여줘 실 컬럼명(`'1ST INJECTION VELOCITY'`)과 매핑이 안 됐던 한계. STEP 1B-3c에서 `GET /datasets/{id}/columns`로 실 컬럼 드롭다운 매핑 도입으로 해소. 172/800이 다시 표시됨 | 추상 키 vs 실 컬럼명 불일치는 KAMP/실데이터 도입 시 더 두드러져 빨리 해결 필요했음. 데이터 비종속성(D-82) 유지 — MCP `/list_columns`(7도구) 위임으로 파일 헤더에서 동적 |

### 구현 산출물
- 백엔드 (`backend/main.py`) 3개 엔드포인트:
  - `GET /api/datasets/all` — 4 모달리티 fan out (디렉터리 스캔)
  - `GET /api/modules` — modules.yaml 조회 (constraint_keys 소스)
  - `PUT /api/sessions/{sid}/full` — PipelineFull 저장, status="ready"
- 프론트엔드:
  ```
  src/lib/modality.js
  src/step3_user_input_data/{DataConstraintPage, DatasetSelector, ConstraintForm}.jsx
  src/step4_standardize/{StandardizePage, ApprovalCard, AlarmBanner, FindingsList}.jsx
  ```
- `src/main.jsx`: `/pipeline/data` (Page 3 실재), `/pipeline/run` (Page 4 실재), `/pipeline/analyze`·`/pipeline/model` (Page 5·6 placeholder)
- `src/styles.css` — Page 3·4 컴포넌트 스타일 (대비/상태/severity 색상)

### 검증 결과 (명세 §8 체크리스트, end-to-end via Vite proxy)
- 백엔드:
  - `/api/datasets/all` 4 모달리티 반환 (timeseries 6 / image 3 / event-log 3 / order 1, 총 13)
  - `/api/modules` 5 Node (injection_molding 4 constraint_keys / 그 외 3개씩)
  - `PUT /sessions/{id}/full` → status="ready", modules_total/with_data/with_constraints 통계
  - 기존 엔드포인트 회귀 0 (Page 2 PUT structure / execute_pipeline / approve / aggregate_context / pipeline_full 직접 호출 모두 동작)
- Page 3 (시뮬레이션):
  - GET /sessions/{id} 로 Page 2 structure 복원 → 각 모듈 카드 렌더
  - GET /datasets/all 로 modality별 데이터셋 드롭다운 채움
  - GET /modules 로 node의 constraint_keys 폼 자동 생성
  - 빈 칸 허용 (raw min/max → null 변환), 미선택 모듈 datalake_id=null
  - 데이터 업로드 버튼 클릭 시 "추후 STEP에서 지원" 토스트
- Page 4 (핵심) — full flow:
  - "실행" → POST /execute_pipeline → `status=awaiting_approval`, pending 6 step_keys (remove_outlier + normalize_group ×5)
  - 승인 카드에서 [L2] 권한 + operation + target_column / semantic_group + rationale 노출
  - 개별 승인 6회 → approved_count=6 누적
  - "승인 후 계속" → POST /execute_pipeline → `status=completed`, completed_module_keys=['0.0'], passed=True
  - GET /aggregate_context/{id} → 6 findings, `[medium] constraint_violation — '1ST INJECTION VELOCITY' 범위 [40.0, 70.0] 위반 172/800행`
  - **172/800이 finding.detail 그대로 화면에 렌더됨 (FindingsList) — D-67/D-88 일관**
  - stage_chain.downstream_implication: "사용자 제약 위반 잔여. 모델링 전 추가 정제 또는 제약 완화 검토. 시퀀스/프로파일 그룹 정규화 적용 (추세/형상 보존)..."
  - 새로고침 → GET /sessions/{id} status=completed 그대로 복원 가능
- 빌드/회귀:
  - `npm run build` — 51 modules, 187 KB JS (61 KB gzip), 7.7 KB CSS, 661ms
  - 4 모달리티(timeseries/order/image/event-log) 회귀 없음

### STEP 1B-3b 완료 마일스톤
사용자 비전의 **MCP 표준화 흐름이 UI로 처음 노출**됨. 1B-2a Orchestrator의 suspend/approve/resume이 승인 카드 + "계속" 버튼으로 자연스럽게 표현. 1B-2c Validator의 6종 검증 결과(특히 D-67 constraint 원본 기준 172/800)가 그대로 Page 4 화면에 시각화. 다음: STEP 1B-3c (Page 5 분석목적/EDA + Page 6 모델링) — UI만, 실엔진 STEP 2·3에서.

## 2026-06-01 — STEP 1B-3c: Page 5(분석목적/EDA) + Page 6(모델링) + Page 3 개선 (D-90 해결)

명세: `docs/specs/STEP_1B-3c_page5_6.md`. STEP 1B-3 마지막 단계.
**범위 경계**: "LLM이 분석 목적·모델을 추천하는 것까지" 실동작. EDA 차트·실제 ML 학습은 STEP 2·3.

| # | 결정 | 사유 |
|---|---|---|
| D-91 | Page 5 분석목적 추천 환각 방어 — `ANALYSIS_PURPOSES`(6종 고정) 외 LLM 추천은 코드로 제거 | spec-2 Part 6 일관. LLM이 새 옵션을 만들어도 endpoint가 필터링. rationale_ko는 facts(key_findings/function_axis_summary) 인용 권장 |
| D-92 | Page 6 모델 추천 환각 방어 — `recommended_models`(modules.yaml) 풀 외 + fit_score 1~5 외 LLM 응답은 코드로 제거 | 새 모델 이름 환각 / 점수 폭주 차단. 사용자가 보는 추천은 항상 풀 내 + 1~5 |
| D-93 | (D-90 해결) Page 3 제약 폼이 데이터셋 선택 시 `GET /api/datasets/{id}/columns`로 실 컬럼 목록을 받아 드롭다운으로 매핑 | 추상 키(injection_velocity) vs 실 컬럼명(`1ST INJECTION VELOCITY`) 불일치 해소. 실 컬럼 매핑 후 Validator가 172/800 그대로 검출 확인 |
| D-94 | `/api/datasets/{id}/columns`는 MCP `/list_columns`(7도구 표준)에 위임 + dtype 필터 (numeric only) | 데이터 비종속성(D-82) 유지 — 파일 헤더 동적 스캔. 범위 제약은 수치 컬럼에만 의미 있음 |
| D-95 | EDA 차트는 골격(차트 라이브러리 미도입) — key_findings 텍스트 + "STEP 2·3 예정" 안내만 | 1B-3a/3b에서 차트 라이브러리 안 들임(D-76 일관). 추천(LLM)까지가 본 STEP 범위 |
| D-96 | Page 6 학습 버튼은 골격(모달 안내) — 실 train 엔드포인트 호출 안 함 | 실 ML 엔진(fit/predict/지표)은 STEP 3. 1B-3c는 추천까지 |
| D-97 | `_slim_ctx`로 AggregatedContext 4영역만(key_findings/function_axis_summary/stage_chain/pipeline_constraints) LLM에 주입 | agent_records의 큰 본문 제외해 토큰 절약. 추천에 필요한 결정론 추출 결과만 |
| D-98 | `_VRAM_HEAVY_MODELS = {CNNClassifier, EfficientNet, ResNet, ViT, BERT}` — advisory_only=true로 분류해 Page 6에서 "권고만" 섹션 표시 | 본 환경(RTX 3070 8GB) 실행 불가 모델은 추천하되 학습 버튼 비활성. 사용자가 SI 환경 결정 시 참고 |

### 구현 산출물

백엔드 (`backend/main.py`) 4개 엔드포인트:
- `GET /api/datasets/{dataset_id}/columns` (D-93/94) — MCP `/list_columns` 위임 + numeric 필터
- `GET /api/analyze/{session_id}/questions` (D-91) — LLM 분석목적 추천 (AggregatedContext 기반)
- `POST /api/analyze/{session_id}/select` — user_intent 갱신 + function_axis 반환
- `GET /api/model/{session_id}/recommend` (D-92) — LLM 모델 추천 (recommended_models 풀 + fit_score 1~5)

백엔드 헬퍼:
- `_slim_ctx(ctx)` — 토큰 절약용 4영역 추출
- `_collect_recommended_models(session)` — pipeline 노드들의 recommended_models 합집합
- `_PURPOSE_FUNCTION` 매핑 (spec-2 Part 6-4 결정론)
- `ANALYSIS_PURPOSES` (6종 고정 풀)
- `_VRAM_HEAVY_MODELS` (advisory_only 분류)

프론트엔드:
- `src/step3_user_input_data/ConstraintForm.jsx` — 실 컬럼 드롭다운 + rows 기반 폼으로 재작성
- `src/step3_user_input_data/DataConstraintPage.jsx` — 데이터셋 선택 시 `/columns` 호출, constraintRows 리스트 상태로 전환
- `src/step5_analyze/AnalyzePage.jsx` — 추천 + 전체 + 직접 입력 + 선택 저장 + EDA 골격
- `src/step5_analyze/QuestionRadioGroup.jsx` — LLM 추천 카드 + 일반 라디오 + free_input textarea
- `src/step6_modeling/ModelingPage.jsx` — 추천 모델 카드(fit_score 정렬) + 권고만 섹션 + 추천 외 풀 안내
- `src/step6_modeling/ModelCard.jsx` — fit_score 별 + rationale + context_reflections + 학습 버튼
- `src/step6_modeling/TrainSkeletonModal.jsx` — "STEP 3 예정" 안내 모달
- `src/main.jsx` — /pipeline/analyze, /pipeline/model 라우트 실재화 (placeholder 제거)
- `src/styles.css` — Page 3 실컬럼 row / Page 5 qrg·eda-skeleton / Page 6 model-card·modal 스타일

### 검증 결과 (명세 §6 체크리스트, end-to-end via Vite proxy)
- **D-93 D-90 해결 검증** (가장 중요):
  - GET `/datasets/cnc_machine_injection/columns` → 32 numeric 컬럼 중 `1ST INJECTION VELOCITY` 포함
  - Page 3 PUT /full with `{"1ST INJECTION VELOCITY":[40,70]}` (실 컬럼명)
  - Page 4 execute → completed → aggregated_context
  - **key_findings에 `[medium] '1ST INJECTION VELOCITY' 범위 [40.0, 70.0] 위반 172/800행`** 그대로 노출 (1B-3b의 "일치 컬럼 없음" 회피 → D-90 해결)
- **D-91 Page 5 LLM 추천**:
  - 2 recommendations (rank 1: anomaly_detection, rank 2: process_optimization), 모두 ANALYSIS_PURPOSES 안
  - rationale_ko가 facts 인용 ("'1ST INJECTION VELOCITY' 범위 위반(중간)...", "시퀀스 및 프로파일 그룹 정규화가 적용...")
  - select → user_intent = `{analysis_purpose:'anomaly_detection', function_axis_focus:'maintenance', free_input:'이상치 위주로'}` (1B-2b None 자리 채워짐)
- **D-92 Page 6 LLM 모델 추천**:
  - available_models 3개 (RandomForestRegressor / IsolationForest / XGBoostClassifier — injection_molding 노드 풀)
  - LLM 추천 1개: `[4/5] IsolationForest`, rationale "사용자 목적이 'anomaly_detection'이므로 이상 감지 모델인 IsolationForest 가 가장 적합...", context_reflections 3건 (anomaly_detection / constraint_violation / sequence_normalized)
  - 추천 이름이 모두 available_models 안 (환각 방어), fit_score 1~5 안 (범위 가드)
- 1층 `/api/execute` 회귀 0 (mct_tool_manage_clean passed=True)
- `npm run build` 성공 — 51 → 56 modules transformed, 198 KB JS (64.5 KB gzip), 9.9 KB CSS, 691ms
- 워킹 트리 clean (untracked: 본 spec md만)

### STEP 1B-3c 완료 마일스톤 = STEP 1B 전체 완료
6 페이지 UI가 처음으로 끝까지 도는 상태:
**Line 선택 → 파이프라인 구성 → 데이터·제약(실 컬럼) → 표준화 실행/승인/검증/집계 → 분석 목적 추천·선택 → 모델 추천**
- LLM 가치 영역 5개 중 ③(분석목적)·⑤(모델) 실현
- 환각 방어 메커니즘 7곳 모두 동작 (available_options/available_models 외 차단 + fit_score 1~5 + key_findings 인용 강제)
- D-90 해결 완료 — 실 컬럼 기반 제약으로 172/800이 다시 화면에 표시
- EDA 차트·실 ML 학습은 STEP 2·3에서 후속

다음: STEP 2(옵션 카드 + Planner OptionTree) / STEP 3(EDA 실엔진 + ML 학습 + 공장 단위 통합/RAG).

## 2026-06-01 — STEP 1B-3d: LLM model 전달 + 에러 표면화 보강 (B1/B2/B3) + 8GB VRAM 모델 전략 정정

명세: `docs/specs/STEP_1B-3d_llm_model_fixes.md`. 1B-3c 검증 중 발견된 버그 3개를 잡고, 영업 표현을 8GB VRAM 현실에 맞게 정정.

### 발견된 버그 (1B-3c 검증 중)
사용자가 웹 드롭다운에서 `gemma4:26b`를 골라도 실제 추론은 `e4b`로 진행되는 게 `ollama ps`로 확인됨. 진단 3갈래:
- **B1**: `/api/analyze/{id}/questions`, `/api/model/{id}/recommend` 가 `model` 파라미터를 안 받고 `generate()`에 안 넘김 → 항상 `OLLAMA_MODEL`(e4b) 폴백.
- **B2**: 프론트 `ModelDropdown.selected`가 로컬 useState에만 살고 어떤 API 호출에도 안 실림. 백엔드의 `req.model` 필드는 이미 존재했지만 클라가 안 보냈음.
- **B3**: `backend/llm.py generate()`가 HTTP 에러를 `{"_llm_error":..}` "정상 JSON"으로 위장 반환 → 호출부의 `json.loads`가 성공하고 키만 부재 → LLM 실패가 "빈 결과"로 둔갑. 깨진 JSON의 재시도/보정도 없음.

| # | 결정 | 사유 |
|---|---|---|
| D-99 | (B1+B2) 세션에 model 저장 — `sessions/create.model` 필드 + `PUT /sessions/{id}/model` + `session_store.public_view`에 model 노출 + `execute_pipeline`은 `session["model"] or req.model` 우선 + `/analyze` `/model` 엔드포인트가 `session.get("model")`을 `generate(...,model=)`에 전달. 프론트 `ModelDropdown`은 변경 시 `localStorage('preferred_model')` 저장 + 세션 있으면 `PUT /sessions/{sid}/model` 즉시 반영. `LineSelectPage`는 `POST /sessions/create`에 `localStorage.preferred_model` 동봉 | 매 호출에 model을 싣는 방식 대신 "이 세션은 이 두뇌(model)로 돈다" 라는 선언적 모델. 페이지/엔드포인트 추가될 때마다 model 인자 흘리는 부담 0 |
| D-100 | (8GB VRAM 모델 전략 정정) 기존 "운영=26b / 개발=e4b" 표현 폐기. 8GB(RTX 3070) 현실: e4b(10GB)도 초과 → 일부 CPU 오프로딩(68%/32% CPU/GPU 분배 확인). 26b(20GB)는 대부분 CPU → 매우 느림(/analyze 120s 타임아웃 발생). **데모/개발 = e4b**, **26b 운영 = 24GB+ GPU(RTX 4090/A100 등) 전제**. 영업 시 "8GB 데모 머신에서 26b 자랑 금지" | 측정: e4b /analyze 5.0s vs 26b /analyze 120s(타임아웃) — x24+ 격차. e4b pipeline 46.6s vs 26b pipeline 274.2s — x5.9 격차. 코드로 GPU 할당 강제 불가 — 물리 8GB 한계. SI 견적·배포 권장사양에 정직하게 반영 |
| D-101 | (B3) `generate()` 위장 `_llm_error` 폐기 → 명확한 `_llm_failed: True` 마커 + `error` + `model_attempted` 필드. 새 `_try_parse_llm(raw)` 헬퍼: 직접 `json.loads` 실패 시 `_coerce_json`(코드펜스/앞뒤 텍스트 제거 후 첫 `{...}` 추출)으로 재파싱. `generate_json()` 묶음 헬퍼(재시도 2회 + 보정). `/analyze` `/model` 엔드포인트가 `_try_parse_llm`을 호출해 `_llm_failed`면 `llm_status="failed" + llm_error + model_used` 응답. 프론트 `AnalyzePage`/`ModelingPage`가 `llm_status==='failed'` 시 명확히 "LLM 응답 실패 — 시도 모델 X · ollama 컨테이너/모델 pull/타임아웃 확인" 배너 표시. 정상 시엔 `(모델: gemma4:e4b)` 라벨도 표시 | "LLM 다운 = 빈 결과로 둔갑"이 가장 위험한 버그였음. 호출부 코드는 그대로면서 신호만 명확화 (Planner/judge의 폴백 정신 유지) |
| D-102 | (Inspector/Planner/llm_judge_data_necessity는 건드리지 말 것) — 이미 정상적으로 `model` 인자 받아 generate에 전달 중 (1B-2a 진단 시 확인) | "정상 작동 중인 코드는 손대지 말 것" 정신. 회귀 위험 0 |

### 구현 산출물
- 백엔드:
  - `backend/llm.py` 재작성 — `_llm_failed` 마커 + `_coerce_json` + `_try_parse_llm` + `generate_json`. 기존 `generate(prompt, system, fmt_json, model)` 시그니처 유지(회귀 0)
  - `backend/main.py`:
    - `CreateSessionReq.model: str | None = None` 추가
    - `sessions_create`: `req.model` 저장 + 응답에 `model` 반환
    - `PUT /api/sessions/{sid}/model` (`SessionModelReq.model`) 신규 — 빈 문자열이면 세션 model 해제
    - `execute_pipeline`: `model = session.get("model") or req.model` 우선순위 적용 (Inspector/Planner/judge 3 호출 자리 전부 `model=model`)
    - `analyze_questions`, `model_recommend`: `model = session.get("model")` + `generate(..., model=model)` + `_try_parse_llm`로 파싱 + `llm_status/llm_error/model_used` 응답 필드
  - `backend/session_store.py`: `public_view`에 `model` 필드 노출
- 프론트엔드:
  - `frontend/src/components/ModelDropdown.jsx` — localStorage('preferred_model') 저장 + 세션 있으면 즉시 PUT 반영, "(세션: gemma4:26b)" 표시
  - `frontend/src/step1_line/LineSelectPage.jsx` — POST /sessions/create 시 localStorage.preferred_model 동봉
  - `frontend/src/step5_analyze/AnalyzePage.jsx`, `frontend/src/step6_modeling/ModelingPage.jsx` — `llm_status==='failed'` 시 명확한 에러 배너, 정상 시 `(모델: X)` 라벨

### 검증 결과 (실측, host에서 Vite proxy 통해)
- **B1+B2 e4b 경로** (세션 model 미설정 → 환경변수 폴백):
  - Page 4 pipeline = **46.6s**, /analyze = **5.0s**, /model = **9.8s**
  - `ollama ps` → `gemma4:e4b  10 GB  68%/32% CPU/GPU` 확인
  - llm_status=ok, recommendations 정상 (anomaly_detection rank 1, process_optimization rank 2)
- **B2 26b 드롭다운 변경**:
  - `PUT /sessions/{sid}/model {model:"gemma4:26b"}` → `GET /sessions/{sid}.model == "gemma4:26b"` 영속화 확인
  - Page 4 pipeline = **274.2s** (e4b 대비 x5.9 — CPU 오프로딩 영향)
  - `ollama ps` 후처: `gemma4:26b  20 GB  63%/37% CPU/GPU` — **26b 실 로드 확인**
  - 후속 /analyze 호출은 120s 타임아웃 → `llm_status="failed"` + `model_used="gemma4:26b"` 노출 (B3 동작 — D-100 8GB 현실 일치)
- **B3 잘못된 모델명 시 표면화**:
  - `PUT model: "gemma4:nonexistent-xyz"` 후 Page 5 호출 → `llm_status="failed"`, `llm_error="Client error '404 Not Found' for url 'http://ollama:11434/api/generate'"`, `model_used="gemma4:nonexistent-xyz"`, `recommendations=[]`
  - 1B-3c라면 "빈 추천 0개"로 둔갑했을 시나리오가 이제 "실패 + 시도 모델 + 사유"로 명확히 표면화
- 회귀 0 (1층 `/api/execute` mct_tool_manage_clean passed=True)
- `npm run build` 성공 — 56 modules

### LLM 가치 영역 모델 흐름 (D-99 적용 후)
```
드롭다운 26b 선택 (Page 4 등)
  → ModelDropdown: localStorage('preferred_model') = 'gemma4:26b'
  → PUT /sessions/{sid}/model {"model": "gemma4:26b"}
  → session["model"] = "gemma4:26b"

이후 LLM 호출 (어디서든):
  execute_pipeline   → model = session["model"] or req.model
  /analyze/questions → model = session.get("model")  → generate(...,model=model)
  /model/recommend   → model = session.get("model")  → generate(...,model=model)
  Inspector/Planner/judge → chain으로 model 전달 (이미 정상, D-102)

generate() → Ollama /api/generate (실제 model로 호출)
  실패 시 _llm_failed JSON 마커 → _try_parse_llm → llm_status="failed" 응답
  성공 시 정상 JSON → 환각 방어 필터 → llm_status="ok" + model_used 응답
```

### STEP 1B-3d 완료 마일스톤
드롭다운 → 세션 → LLM 호출 → 실제 모델 로드, 에러는 위장 없이 명확히 표면화. 6 페이지 UI에서 사용자가 선택한 모델이 진짜로 쓰이는 게 `ollama ps`로 증명. 8GB VRAM 한계는 명세에 정직하게 기록. 다음: STEP 2(옵션 카드) / STEP 3(EDA 실엔진 + ML 학습).

## 2026-06-02 — STEP 2a: 옵션 카드 백엔드 (balance_classes 4옵션 + 결정론 미리보기)

명세: `docs/specs/STEP_2a_option_cards_backend.md`. 브랜치: `feature/step2-option-cards`.

진단(이전 턴): balance_classes는 분석만 — `df` 미변경 + `"suggested_strategy"` 문자열 1줄. 옵션이 없어 사용자가 선택할 게 없었음. STEP 2의 자연스러운 첫 후보.

| # | 결정 | 사유 |
|---|---|---|
| D-103 | "Strategy 식별자 방식" — balance_classes는 L2 단일 op 유지, 옵션은 `strategy` 필드 값으로. `OperationType`/`OPERATION_PERMISSION`에 새 op 추가 금지 | normalize_group 선례 재사용. LLM 환각 방어(D-13/D-14 후보 외 작업 생성 금지) 그대로. `step_key`(operation:semantic_group\|target\|"global") 불변 → 기존 승인 누적과 호환 |
| D-104 | 옵션 풀(`BALANCE_OPTIONS`)은 **코드 고정**, 미리보기(`compute_balance_preview`)는 **결정론 산식**. LLM 0 호출 추가 | 옵션 추가에도 LLM 호출 횟수 불변 → 속도 영향 0. Planner는 "balance_classes 필요" 1회 판단 그대로(plan.summary 검증). `available_options`는 Planner 단계 첨부, `preview`는 `execute_pipeline` suspend 직전 df 로드 후 첨부 (2단계 충전) |
| D-105 | strategy 분기: `class_weight`/`skip`/`smote`/`random_under`/(None=레거시). `smote`·`random_under`는 미리보기만 정확, 실제 리샘플링은 STEP 3 ML 단계 표시 | 무거운 리샘플링은 데이터 변형이라 SI 컴플라이언스/검증 부담. 옵션 제시+선택 저장+추적성까지가 STEP 2a 범위. `class_weight`는 메타(가중치 dict)만 기록, df 미변경 → 회귀 안전 |
| D-106 | strategy None일 때 `_op_balance_classes`는 **기존 분석 동작 그대로** (suggested_strategy 권고 문자열) | 회귀 0 강제 — 옵션 선택 안 한 세션·기존 테스트가 모두 정상 동작 (cnc_machine_injection 6 non-balance steps 검증) |
| D-107 | 환각 방어: `ApproveReq.selected_option`이 `BALANCE_OPTION_IDS`(frozenset) 안에만 있을 때 세션에 저장. 허용 외 값(오타·악의·LLM 환각)은 조용히 무시 | LLM이 옵션을 생성하지 않지만, 외부 클라이언트가 임의 값을 보낼 가능성 대비. 검증: `bogus_strategy_xyz` 시도 → 저장 안 됨, 응답 `selected_option=None` |
| D-108 | 미리보기 산식 — sklearn `class_weight='balanced'` (`total/(n_classes*count)`) + imbalanced-learn 기본(SMOTE→majority×n, Under→minority×n) | 실제 라이브러리 동작과 일치. 추정이 정확해야 사용자 결정에 의미 있음 |
| D-109 | lineage `params.selected_option` 기록 — "사용자가 어떤 보정을 선택했는가" 감사 가능 (SI 컴플라이언스) | "AI 자동화 두려움" 해소(D-16) 연장 — 사용자 선택까지 추적 |

### 구현 산출물
- `agents/executor/balance_options.py` (신규) — `BALANCE_OPTIONS` 4종 + `BALANCE_OPTION_IDS` frozenset + `compute_balance_preview(df, col)` 결정론 함수. **LLM import 0**, `from llm` `generate(` grep 0건
- `agents/planner/planner_schemas.py` — `PlanStep`에 `available_options: list[dict]` + `preview: dict` 추가. `step_key` property 불변
- `agents/planner/planner.py` — sys.path에 `agents/executor` 추가, `from balance_options import BALANCE_OPTIONS`. balance_classes step 생성 시 `available_options=BALANCE_OPTIONS` 첨부 (df 없으므로 preview는 후속 단계에서)
- `agents/executor/executor.py`:
  - `_op_balance_classes(df, col, strategy=None)` — strategy 분기 (class_weight/skip/smote/random_under/None=레거시)
  - `execute(plan, approved_keys, modality, selected_options=None)` 신규 파라미터
  - timeseries/order 디스패처에 balance_classes 특수 케이스 (strategy 전달)
  - event-log path도 `_op_balance_classes`로 위임 (DRY) + `selected_options` 전달
  - lineage `params.selected_option` 기록
- `backend/main.py`:
  - `_maybe_load_df_for_preview(dataset_id, modality, pending_steps)` 헬퍼 — balance_classes pending 있을 때만 df 로드 (불필요 I/O 회피)
  - `execute_pipeline` suspend 블록에 `pending_steps_payload` 구성 시 `available_options` + `preview`(balance_classes 한정) 첨부
  - `ApproveReq.selected_option: str | None` 신설. 저장 시 `BALANCE_OPTION_IDS` 필터(환각 방어)
  - `session["selected_options"]: dict[step_key, option_id]` 신설
  - `run_execute` 호출에 `selected_options=session.get("selected_options") or {}` 전달

### 검증 결과 (명세 §7 체크리스트, 실 HTTP)
- **A 산식 정확성** (synthetic 100행 A:97/B:3): class_weight 가중치 `{A:0.5155, B:16.6667}` (=100/(2*97), 100/(2*3)), SMOTE 194(+94), Under 6(-94), skip 100 — 산식 일치. 단일 클래스 → `applicable=False`
- **B Inspector 신호**: event-log `press_forming.csv` → `PASS_YN imbalance_suspected=True, minority_ratio=0.0283`
- **C 옵션·미리보기 노출**: pending balance_classes step에 `available_options` 4개(IDs `{class_weight, smote, random_under, skip}`) + `preview.applicable=True`, `current={counts:{PASS:2915, FAIL:85}, total:3000, majority:2915, minority:85}`, smote `5830(+2830)`, under `170(-2830)` — 실 데이터 산식 정확
- **D approve + resume**: `selected_option=smote` 전달 → `applied_strategy='smote'`, `note: 'smote 선택됨 — 실제 리샘플링은 STEP 3 ML 단계에서 적용 예정'`, validation passed
- **E lineage**: `transformation_type='balance_classes', params.selected_option='smote'` 기록 — 추적성 확보 (D-109)
- **F 환각 방어**: `selected_option='bogus_strategy_xyz'` → 응답 `selected_option=null`, 세션 미저장
- **G 회귀 0**: cnc_machine_injection (timeseries) 6 non-balance steps → 모두 `available_options=[]`, pipeline completed `passed=True`
- **H LLM 호출 횟수 불변**: `plan()` 1회 호출로 옵션 4종까지 첨부 — `generate()` 추가 호출 0 (옵션은 코드 고정 풀)
- **I 별표 사용 0건**: `docs/decisions.md`, `docs/0_variable_index_v5.md` 양쪽 모두 (강조 마커 정책 준수)
- `python3 -m py_compile` 통과 (balance_options.py / planner.py / planner_schemas.py / executor.py / backend/main.py)
- `grep "from llm\|import llm\|generate("` `agents/executor/balance_options.py` → 0건

### 헌법 정합 (왜 이 설계)
- "LLM 제안, 규칙 결정" 발전형: LLM은 "balance_classes 필요" 1회 판단(기존). 옵션 펼치기·미리보기·선택 저장은 결정론. 사용자가 결정 → LLM 호출 0 증가
- Strategy 방식 (A): op를 안 늘려 환각 방어 그대로 (`OperationType`/`OPERATION_PERMISSION` 무변경). normalize_group의 strategy 필드 재사용 선례
- 회귀 안전: strategy None일 때 기존 분석 동작. `step_key` property 불변 → 승인 누적 호환
- 추적성: 선택된 옵션을 lineage에 기록 — "사용자가 SMOTE를 선택했다"가 감사 가능 (SI 컴플라이언스)
- 미리보기 추정: 실제 무거운 리샘플링 없이 정확한 산식으로 행수 예측 → 빠르고 명확. SMOTE/Under의 실제 적용은 STEP 3로 분리

### STEP 2a 완료 마일스톤 (브랜치 작업)
백엔드 옵션 카드 인프라(옵션 풀 + 결정론 미리보기 + 선택 흐름 + Executor 분기 + lineage 기록) 완성.
다음: STEP 2b (Frontend Page 4 ApprovalCard을 옵션 선택 카드로 확장) — 브랜치에서 작업 후 main 머지.

## 2026-06-02 — STEP 2b: 옵션 카드 UI (ApprovalCard 카드형 + 강제 선택)

명세: `docs/specs/STEP_2b_option_cards_frontend.md`. 브랜치: `feature/step2-option-cards`.

STEP 2a 백엔드가 `pending_steps[i]`에 첨부한 `available_options`(4종) + `preview`(결정론 미리보기)를 프론트가 카드형 UI로 노출. 사용자가 명시적으로 1개 선택해야 승인 — "LLM 제안, 사람 결정"을 시각화.

| # | 결정 | 사유 |
|---|---|---|
| D-110 | (UX) 카드형 = 옵션 4개를 가로 그리드 카드로. 각 카드 = label + 미리보기 행수 변화(또는 가중치) + 설명 + 주의사항(⚠) | 라디오만으론 4 옵션의 차이가 한눈에 안 들어옴. 카드형이 행수 변화/주의사항을 같이 보여줘 결정에 필요한 정보 밀도 충족. spec-2 Part 5-5 승인 카드 톤과 정합 |
| D-111 | 강제 선택 — `available_options.length > 0`이고 미승인 step은 옵션 1개 선택해야 승인 버튼 활성. 미선택 시 "옵션을 선택하세요" 라벨로 disable. "전체 승인"도 옵션 미선택 step 있으면 disable | 디폴트 자동 선택은 무심코 넘어가 단일 승인과 차이 0 → 결정의 의미 보존 (헌법 "사람이 결정"의 시각화). selected_option이 lineage(D-109)로 추적되므로 사용자 의식적 선택이 감사 가능 |
| D-112 | "권장" 배지 = `class_weight` 한 카드에만 (가장 안전: 데이터 미변경, 가중치 메타만) | 강제 선택의 부담을 가이드로 완화 — 초보자도 안전한 기본으로 유도하되 선택은 본인. RECOMMENDED_OPTION 상수로 분리, 향후 변경 단일 지점 |
| D-113 | 옵션 카드 클릭 → ApprovalCard 컴포넌트 내부 state가 아니라 부모(StandardizePage) `selectedOptions: {step_key: option_id}` state로 관리. ApprovalCard는 props로 받기만 | 새로고침이나 다른 step 승인 후에도 선택 유지. 부모가 onApproveAll에서 일괄 동봉 가능. 단방향 데이터 흐름 유지 |
| D-114 | `onApprove(step_key, stage_order, module_index, selected_option=null)` 4-arg 시그니처. POST `/api/pipeline/{id}/approve` body에 `selected_option` 동봉. 옵션 없는 step은 `null` (회귀 안전) | STEP 2a 백엔드 `ApproveReq.selected_option` 필드가 받을 준비 완료(D-107 환각 방어 — `BALANCE_OPTION_IDS` 외 무시). 프론트가 null 보내도 백엔드는 기존 분석 동작 (D-106) → 회귀 0 |
| D-115 | 옵션 없는 step(`available_options=[]`)은 기존 yes/no UI 그대로. `OptionCardGroup` 자체 안 그림 | 회귀 0 — cnc_machine_injection의 normalize_group/remove_outlier 등 기존 L2는 영향 없음 (검증 완료) |
| D-116 | 옵션 카드 스타일은 기존 디자인 토큰(`--panel-2`, `--c-process`, `--c-quality`, `--c-maintenance`, `--border`) 재사용. 외부 UI 라이브러리 추가 금지 | spec D-76(Tailwind 등 빌드 의존성 금지) 일관. 선택 상태 = `--c-process`(파랑) 보더, "권장" 배지 = `--c-quality`(초록), 주의사항 = `--c-maintenance`(주황) — 의미 일치 |
| D-117 | `vite.config.js`에 `server.allowedHosts: true` 추가 — Playwright(다른 docker container)에서 `mfg-frontend-dev:5173` 접근 허용 | dev 전용. Vite의 host check는 CORS와 무관한 dev 도구 보호용. 브라우저 자동화 테스트(이번 스크린샷 + 향후 e2e CI) 필수 인프라 |

### 구현 산출물
- `frontend/src/step4_standardize/ApprovalCard.jsx` — 전면 재작성:
  - 새 props `selectedOptions`, `onSelectOption`
  - step 렌더 분기: `hasOptions`이면 `OptionCardGroup`을, 아니면 기존 yes/no 버튼
  - "전체 승인" 가드: `hasUnselectedOptionStep` 있으면 disable + title 안내
  - `OptionCardGroup` 내부 컴포넌트 — 현재 분포 요약 + 4 카드 그리드 + 강제 선택 승인 버튼
- `frontend/src/step4_standardize/StandardizePage.jsx`:
  - `selectedOptions` state (`{step_key: option_id}`)
  - `onSelectOption` 콜백
  - `onApprove` 4-arg 시그니처 — body에 `selected_option` 동봉
  - `onApproveAll` — `selectedOptions[s.step_key]`를 step별로 동봉
  - ApprovalCard에 새 props 전달
- `frontend/src/styles.css` — `.opt-group`/`.opt-cards`/`.opt-card`/`.opt-card-head`/`.opt-label`/`.opt-badge`/`.opt-preview`/`.opt-sub`/`.opt-desc`/`.opt-caution`/`.opt-actions`/`.opt-warn`/`.opt-current` 신설 (기존 토큰만)
- `frontend/vite.config.js` — `allowedHosts: true` (dev 인프라)

### 검증 결과 (명세 §7 체크리스트, 브라우저 + curl)
- **옵션 카드 렌더 (브라우저 스크린샷 captured)**:
  - press_forming(event-log) → Page 4 awaiting_approval → balance_classes step에 **4 카드** (`클래스 가중치 (class_weight)` / `SMOTE 오버샘플링` / `랜덤 언더샘플링` / `보정 안 함 (skip)`) 표시 — Playwright `.opt-card` 개수 = 4
  - 각 카드 미리보기 숫자: class_weight `행수 유지 (3000행)` + `가중치 최대 ~17.65배`, smote `5830행 (+2830)`, random_under `170행 (-2830)`, skip `행수 유지 (3000행)`
  - class_weight에 "권장" 배지 (`.opt-badge` 개수 = 1)
  - 현재 분포: `현재 분포: PASS 2915 / FAIL 85 (소수 클래스 2.83%)`
  - 각 카드에 description (BALANCE_OPTIONS) + ⚠ caution
- **강제 선택**:
  - 미선택 상태 → 카드 그룹 하단 버튼 라벨 `옵션을 선택하세요`, disabled
  - SMOTE 카드 클릭 → 파랑 보더(`.opt-card.selected`) + 버튼 라벨 `'smote' 선택 적용`, enabled. "전체 승인" 버튼도 enabled (1 remaining step has selection)
  - approve → POST body `{step_key, stage_order, module_index, selected_option:"smote"}` → 응답 `selected_option=smote` → resume → `applied_strategy="smote"` + STEP 3 note (백엔드 D-103 일관)
- **회귀 0**:
  - cnc_machine_injection (timeseries) 6 non-balance L2 steps → 모두 `available_options=[]`, OptionCardGroup 안 그림, 기존 yes/no 그대로
  - `selected_option=null` 시 백엔드는 기존 분석 동작(suggested_strategy) — applied_strategy 키 부재 (D-106 회귀 안전)
  - Page 4 status=completed, validation.passed=True
- 다른 페이지(1·2·3·5·6) 변경 0 (스코프 — Page 4만)
- `npm run build` 성공 — 56 modules, 빌드 산출물에 `opt-card`/`opt-badge`/`opt-preview` 클래스 포함
- 강조 마커(별표) 0건 — 문서 정책 준수

### 헌법 정합
- "LLM 제안, 사람 결정"의 시각화: 카드형 + 강제 선택 = 결정의 의미 보존 (D-110/D-111)
- 추적성 연결: 옵션 카드 클릭 → selected_option POST 동봉 → 백엔드 lineage 기록 (STEP 2a D-109) — "사용자가 SMOTE를 의식적으로 선택" 감사 가능
- 환각 방어 사용자 영역: 권장 배지로 디폴트 안전 가이드 유지 (D-112)
- 회귀 안전 (다중 레벨): available_options 빈 step은 OptionCardGroup 안 그림(D-115), 백엔드는 selected_option=null 시 기존 동작(D-106) — 다중 모달리티·다른 L2 영향 0
- 프로토타입-애자일: 기능·정합 위주, 기존 톤(`--panel-2`/`--c-process`/`--c-quality`/`--c-maintenance`) 재사용. 외부 라이브러리 0 (D-76 일관)

### STEP 2b 완료 마일스톤 = STEP 2 전체 완료 (브랜치 작업 종료)
사용자가 옵션 카드 4개에서 의식적으로 1개 선택 → 선택이 lineage까지 기록되는 흐름 완성. STEP 2(옵션 카드) 백엔드+프론트 모두 검증 완료. 브랜치 `feature/step2-option-cards`에서 main 머지 가능.

다음: STEP 3 (EDA 실엔진 + ML 학습 — SMOTE·Under 실제 적용 + 모델 fit) — 별도 브랜치.

## 2026-06-02 — STEP 3a: Page 5 EDA 실엔진 (LLM 판단 + 코드 실행)

명세: `docs/specs/STEP_3a_eda_engine.md`. 브랜치: `feature/step3-eda-ml`.

STEP 2b까지 골격이었던 Page 5 EDA를 실엔진으로. 3a-1(LLM 판단 + 결정론 차트) 완성 후 3a-2(자연어 코드 생성 EDA + 3중 안전) 추가. 차트 데이터는 `data/processed/{dataset_id}__processed.parquet` 직접 재로드. MCP 7도구 계약 무손상, scipy 도입 0.

| # | 결정 | 사유 |
|---|---|---|
| D-118 | EDA 3원칙: ① LLM 판단(어떤 차트 필요한지 추천) ② 코드 실행(결정론 차트 데이터, LLM 0) ③ LLM 자연어 요약(숫자 그대로 인용). function_axis별 차트 고정 매핑 거부 | 헌법 "LLM 제안, 규칙 실행"의 뒷단 적용. 데이터 특성을 LLM이 보고 판단해야 진짜 EDA. function 가이드는 참고용으로만 (`FUNCTION_CHART_GUIDE`) |
| D-119 | EDA 차트 데이터 소스 = `data/processed/{dataset_id}__processed.parquet` 직접 재로드. AggregatedContext에 분포 없음, MCP 7도구는 분포 미제공(8번째 도구 = 헌법 위반) | 진단 결과(컬럼 stats=null/n_unique만 보유, MCP 분포 함수 0개). parquet은 Executor가 4단 후 항상 생성 — 표준 진입점 |
| D-120 | 허용 차트 8종을 `agents/eda/chart_types.py` 코드 상수(`CHART_TYPE_IDS` frozenset)로 고정. LLM 추천은 호출부에서 이 집합으로 필터(환각 방어) | balance_options.py `BALANCE_OPTION_IDS` 패턴 그대로. fft/boxplot/histogram/class_dist/correlation/scatter/pareto/rms_trend 8종 — spec-2 Part 6-4 매핑 |
| D-121 | LLM 추천 실패 / 빈 결과 / modality 부적합 → `FUNCTION_CHART_GUIDE` 폴백(primary 중 modality OK인 것 1~2개) | graceful — LLM이 죽어도 EDA는 보임. 폴백 추천에 `fallback: true` 마커 (UI가 구분 가능) |
| D-122 | scipy/scikit-learn/imbalanced-learn 도입 거부. FFT는 numpy 내장(`np.fft.rfft`), 통계는 pandas (`describe`/`groupby`/`value_counts`), 가드는 자체 함수(`_sliding_window_mean_signal`, `_apply_row_guard`) | 3a 범위에선 불필요. ML 학습(STEP 3c)이 정말 필요할 때 결정 — 미리 도입 X |
| D-123 | `_pick_eda_target(session)` 헬퍼 — `module_results` 정렬 후 첫 비-이미지 모듈의 `(dataset_id, modality)` 반환. inspection-image는 EDA 의미 없음 | spec STEP_3a §1 inspection-image 제외 — 이미지 모달리티는 skeleton 유지. 다중 모듈 파이프라인에서 일관된 대상 선택 |
| D-124 | 데이터 규모 가드 4종 백엔드 적용: row>1M stride 샘플링(`_apply_row_guard`), 카테고리 30+ 상위 50 + Others(`_topn_categories`), FFT sliding window mean(`_sliding_window_mean_signal` window=4096), 점 5000+ stride(scatter) | spec-2 Part 6-5. synthetic은 발동 안 하지만 실데이터(공정 시계열 수백 MB) 대비 필수. 시각화 가드(strip 오버레이)는 프론트(3b) |
| D-125 | (3a-2) 자연어 → 코드 생성 = "AI가 코드를 짠다" 가치의 완성형. 단 3중 안전 필수: ① AST 화이트리스트(생성 시) ② 실행 직전 재검증 ③ builtins 차단 네임스페이스 + df 사본 + SIGALRM 타임아웃 + L2 승인 + lineage | 헌법 "데이터 외부 전송 0" + SI 컴플라이언스(추적 가능). e4b PoC 한국어 3/3 안전 코드 생성 확인 후 채택 |
| D-126 | `ALLOWED_NODES`/`FORBIDDEN_NAMES`/`ALLOWED_ROOT_NAMES`는 `agents/eda/code_sandbox.py`에 frozenset 코드 상수. import/exec/eval/open/os/sys/socket/dunder(`__*`)/private(`_*`)/while/for 일체 금지 | LLM 화이트리스트 패턴 — 허용 집합 외 통과 0. for/while 차단으로 무한 루프도 AST에서 사전 거부 (signal 타임아웃은 보조) |
| D-127 | `_sandbox_exec(code, df, timeout=5)` — `safe_globals={"__builtins__":{}}` + `df.copy()` 사본 + SIGALRM 5초. 결과는 `_coerce_result`로 pd.Series→dict, pd.DataFrame→records(상위 200행), np.ndarray→list 변환 | builtins 전면 차단으로 `getattr`/`__builtins__` 우회 방어. df 사본 = 원본 보호. 결과 직렬화는 UI/JSON 호환 |
| D-128 | (3a-2 lineage) 승인 실행 결과는 `harness.lineage.record(transformation_type="eda_freeform_code", applied_by_agent="user_approved_freeform_eda", user_approval_id=session_id, params={query, code, approved, result_type})` 로 기록. 실행 실패도 lineage 남김(감사) | SI 컴플라이언스 — "사용자가 어떤 한국어 요청을 하고, LLM이 어떤 코드를 짰고, 그것을 승인·실행해 어떤 결과를 봤는가" 완전 추적. 실행 실패도 기록 = 감사 누락 0 |
| D-129 | `/api/analyze/{id}/eda/plan` /render/summary 3개 엔드포인트 추가 + 3a-2의 `/eda/freeform`+`/eda/freeform/approve` 2개. 기존 `/select`/`/questions`/`/aggregate_context` 계약 변경 0 | 회귀 0 — 추가만, 수정 0. session 새 키 `eda_plan`/`eda_results`/`pending_eda_code`/`last_eda_freeform_result` 신설 (기존 키 영향 0) |
| D-130 | `sys.path.insert(0, ROOT/"agents"/"eda")` 추가 (다른 agents 디렉터리와 동일 패턴). `from eda_engine import ...` 절대 import. `agents/` 자체를 path에 넣으면 `inspector` 등이 패키지로 보여 기존 `from inspector import inspect` 깨짐 | 진단 중 실제 발생한 회귀. 디렉터리별 path 추가 규칙(기존 5개) 유지가 안전 |

### 구현 산출물
- `agents/eda/__init__.py` — 패키지 docstring (3원칙 명시)
- `agents/eda/chart_types.py` — `CHART_TYPES`(8종), `CHART_TYPE_IDS` frozenset, `FUNCTION_CHART_GUIDE`(참고용)
- `agents/eda/eda_engine.py` — `processed_path`/`load_processed_df`, `_apply_row_guard`/`_topn_categories`/`_sliding_window_mean_signal`(가드 4종), `build_eda_profile`(LLM 입력), `llm_recommend_charts`(LLM 추천), `filter_recommendations`+`fallback_charts_from_guide`(환각 방어 + 폴백), `compute_chart_data`(LLM 0, 8 chart 모두), `llm_chart_summary`(자연어 요약, 숫자 인용 강제)
- `agents/eda/code_sandbox.py` — `ALLOWED_NODES`(31)/`FORBIDDEN_NAMES`(18)/`ALLOWED_ROOT_NAMES`(6), `validate_eda_code`(AST 화이트리스트), `sandbox_exec`(builtins 차단 + df 사본 + SIGALRM 5s), `_coerce_result`(pd/np → JSON 직렬화), `llm_generate_eda_code`(자연어 → 코드 제안)
- `backend/main.py` — `_pick_eda_target`(헬퍼), 5 신규 엔드포인트:
  - `POST /api/analyze/{sid}/eda/plan` (LLM 추천 + 환각 방어 + 폴백)
  - `POST /api/analyze/{sid}/eda/render` (결정론 차트 데이터)
  - `POST /api/analyze/{sid}/eda/summary` (자연어 요약)
  - `POST /api/analyze/{sid}/eda/freeform` (자연어 → 코드 → AST 검증 → 미리보기)
  - `POST /api/analyze/{sid}/eda/freeform/approve` (승인 → 샌드박스 실행 → lineage)
- `backend/main.py` 상단 — `sys.path.insert(0, ROOT/"agents"/"eda")` 추가

### 검증 결과 (명세 §7 체크리스트, 실 데이터 + 실 HTTP + LLM)

3a-1 (LLM 판단 EDA + 결정론 차트):
- `/eda/plan` end-to-end (event-log press_forming.csv, quality 축, e4b): LLM 9초 → 2 차트 추천 (`class_distribution`+`PASS_YN`, `boxplot_by_label`+`PASS_YN`) — 한국어 reason 정확 (불균형 시각화, 변수별 분포 차이로 불량 원인 분석)
- `/eda/render` 결정론: class_distribution → `PASS 2915 / FAIL 85`. boxplot_by_label → PASS 5수치(70.56/109.995/120.03/130.24/180.79), FAIL 5수치(68.0/113.85/122.16/129.69/149.13). 모두 정확
- 결정론 재현성: 같은 spec 2회 호출 → 응답 byte-identical (`diff` 통과)
- 환각 방어: 허용 외 `chart_type` → render는 `error` 반환, summary는 HTTP 400
- modality 가드: event-log에 `histogram` 요청 → `error: modality 'event-log' 미지원`
- `/eda/summary` end-to-end (e4b, 4초): `"품질 분류 분석 결과, PASS가 2915건, FAIL이 85건으로 ... 소수 클래스인 FAIL의 비율이 2.83%에 불과합니다."` — 입력 숫자만 인용, 새 숫자 0
- LLM 0 audit: `compute_chart_data` AST 검사로 `generate` 호출 0개 확인. `chart_types.py` import 0건 (pure 상수)

3a-2 (자연어 코드 생성 EDA):
- PoC (구현 전 e4b 한글 3 케이스): 3/3 모두 AST 통과 + 의미 일치
  - `FAIL ... PRESS_FORCE 분포` → `df[df['PASS_YN']=='FAIL']['PRESS_FORCE'].describe().to_dict()`
  - `클래스별 평균 비교` → `df.groupby('PASS_YN')['PRESS_FORCE'].mean().to_dict()`
  - `상위 10 ITEM_CODE` → `df['ITEM_CODE'].value_counts().head(10)`
- 악성 5종 AST 거부 (단위 + endpoint 양쪽): `import os`, `__import__`, `open`, `exec`, `df.__class__.__bases__[0].__subclasses__()` — 모두 명확한 사유로 거부
- 적대적 NL endpoint 1 (`/etc/passwd 열어줘`): LLM e4b 자체가 거부 — code는 `result = {"error": "파일 시스템 접근 ... 허용되지 않습니다"}` 안전한 dict 메시지 (AST 통과, 실행 시 거부 메시지만 반환). 1차 방어(system prompt) 작동
- 적대적 NL endpoint 2 (`os 모듈 import 환경변수`): LLM이 무시하고 안전한 EDA 코드(unique count + mean) 생성. system prompt 우회 방어
- `/eda/freeform` end-to-end (e4b 11초, `FAIL PRESS_FORCE 평균/표준편차`): `result = {mean_press_force: df[...]['PRESS_FORCE'].mean(), std_press_force: ...std()}` 생성 → AST 통과 → 미리보기 반환
- `/eda/freeform/approve` 실행: sandbox → `{mean: 120.4452, std: 13.8226}` (boxplot FAIL 그룹 q1/q3와 일관)
- lineage 기록: `transformation_type=eda_freeform_code`, `applied_by_agent=user_approved_freeform_eda`, `user_approval_id={session_id}`, `params={query, code, approved, result_type}` — `/api/lineage?dataset_id=press_forming.csv` 조회로 확인
- 샌드박스 안전성: `df.copy()` 사용 검증 (sandbox 안에서 `df.drop(...)` 실행 후 외부 df 컬럼 수 불변), for/while 루프 = `ALLOWED_NODES`에 없어 AST 단계 차단

회귀 + 통합:
- `/api/analyze/{sid}/questions` 정상 (e4b 3초, quality_classification 추천) — 기존 D-91 환각 방어 보존
- `/api/analyze/{sid}/select` 정상 (function_axis=quality 반환)
- `/api/aggregate_context/{sid}` 정상 (key_findings 보존)
- Page 4 `/api/execute_pipeline` 정상 (press_forming.csv → suspend → approve → completed, balance_classes selected_option=class_weight 적용)
- 다른 페이지(1·2·3·4·6) 코드 변경 0 — 신규 엔드포인트만 추가
- 강조 마커(별표) 0건 — 문서 정책 준수

### 헌법 정합
- "LLM 제안, 규칙 결정"의 EDA 적용 — 차트 추천은 LLM(자율) / 차트 데이터는 코드(결정론) / 자연어 코드는 LLM(자율) + AST(통제)
- 외부 API 0 / 데이터 전송 0: 모든 LLM 호출 로컬 ollama. parquet은 컨테이너 내부 디스크
- MCP 7도구 계약 보존: parquet 직접 로드로 우회 — MCP에 분포/통계 도구 추가 0
- 추적성 (D-128): 사용자 자연어 → LLM 코드 → 승인 → 실행 결과 → lineage 한 줄에 완전 보존
- 옵션 카드 D-107(`BALANCE_OPTION_IDS`) 패턴 일관: 허용 집합(`CHART_TYPE_IDS`, `ALLOWED_NODES`)을 코드로 고정 → LLM 출력은 그 집합 안만 통과 (환각·코드 인젝션 동시 방어)

### STEP 3a 완료 마일스톤 (브랜치 작업)
EDA 골격 → 실엔진 완료. 사용자가 표준화된 데이터에 대해:
  ① LLM이 적합한 차트 추천 (한국어 reason) → ② 코드가 결정론 차트 데이터 계산 → ③ LLM이 한국어 요약
  ④ 사용자가 자유 한국어로 분석 요청 → ⑤ LLM이 코드 작성 → ⑥ AST 검증 + 사용자 승인 → ⑦ 샌드박스 실행 → ⑧ lineage 기록
"AI가 코드를 짠다"가 EDA에서 실제 동작하며, 3중 안전 + 감사 가능. 다음: STEP 3b (프론트 recharts 시각화 + freeform UI) / STEP 3c (실 ML 학습 — SMOTE/Under 실 적용 + 모델 fit) — 별도 브랜치.

## 2026-06-02 — STEP 3b: Page 5 EDA 차트 UI (recharts)

명세: `docs/specs/STEP_3b_eda_charts_ui.md`. 브랜치: `feature/step3-eda-ml`.

STEP 3a 백엔드 5 엔드포인트(/eda/plan·render·summary·freeform·freeform/approve)가 만든 데이터를 사용자 화면으로. AnalyzePage의 eda-skeleton 한 블록만 교체, 다른 페이지·다른 영역 0. 자연어 EDA UI(코드 미리보기 + 승인/취소)로 "AI가 코드를 짠다" 시스템 정체성을 화면으로 완성.

| # | 결정 | 사유 |
|---|---|---|
| D-131 | `recharts ^3.8.1` 도입. 빌드 타임 번들에 포함되어 **런타임 외부 호출 0** → 헌법 §1.3(외부 API 0)/§1.4(데이터 외부 전송 0) 모두 충족 | 차트 라이브러리 자작 회피. React 18 호환 + CSS 변수 지원(`stroke="var(--c-process)"`)으로 기존 다크 토큰 일관 |
| D-132 | `step5_analyze/charts/ChartCard.jsx` 디스패처 + 컴포넌트 8개 (Histogram/BoxPlot/FftSpectrum/RmsTrend/ClassDistribution/CorrelationBar/Pareto/Scatter). `CHART_COMPONENTS` 매핑 dict | 차트 타입 추가 시 변경 단일 지점. 에러 분기(`chart.error` 우선 → `data.error` → 미지원 chart_type)도 디스패처가 처리 |
| D-133 | BoxPlot = `ComposedChart` + stacked Bar(투명 q1 + 보이는 q3-q1) + `ErrorBar`(min~max 수염, median 중심). 커스텀 Tooltip으로 5수치 + n 표시 | recharts에 박스플롯 내장 컴포넌트 없음. SVG 자작 대신 recharts 일관 유지. "그룹별 분포 비교" 목적 충분 — 정밀 SVG 박스는 폴리싱 단계 (D-79 일관) |
| D-134 | EDA 실행은 **사용자 명시 클릭** ("EDA 실행" 버튼) — `/eda/plan` 자동 호출 X. 버튼 라벨 동적("차트 추천·생성 중…" / "EDA 재실행") | /plan LLM 호출 9초 — /select 직후 자동이면 사용자가 "왜 멈춰있나" 인지 못함. 명시 클릭 = 로딩 표시 명확 + 사용자 의도 보호 |
| D-135 | 자연어 EDA UI = **입력 → /freeform → 코드 미리보기(monospace) → 승인/취소 → /freeform/approve → 결과(JSON pre) + lineage_id 표시**. ApprovalCard L2 톤(`border-left: 3px solid --c-maintenance`) | STEP 2b 옵션 카드 패턴 차용 — "AI 제안, 사람 결정". lineage_id 표시 = "이 분석이 기록됐다"가 사용자에게 보임 (SI 신뢰). 코드 미리보기 monospace + 승인 전 실행 0 |
| D-136 | AI 요약(`/eda/summary`)은 차트별 "AI 요약" 버튼 **클릭 시만** 호출. 일괄 자동 호출 X | LLM 비용 절제 (e4b 4초/요청, N개 차트 일괄이면 사용자가 기다림 인지 못함). 버튼 클릭 = 사용자 의도 + 로딩 표시 명확. 결과는 카드 내부 하단 `.chart-summary` 영역에 표시 |
| D-137 | recharts 다크 톤 — 공통 `AXIS/GRID/TOOLTIP_STYLE` 객체에 CSS 변수(`var(--muted)`/`var(--border)`/`var(--panel-2)`) 주입. function_axis 의미 색 매핑(`COLORS.process/quality/maintenance/reference`) | 다른 페이지(`--panel`·`--panel-2`·`--border`)와 톤 일관. 차트별 fill = function 의미: histogram/scatter=process, class_distribution=quality, fft/rms/pareto cum=maintenance |
| D-138 | `useEffect` 초기화 시 `aggregated.user_intent`에서 `savedResult`도 복원. 새로고침/재방문 후에도 "EDA 실행" 버튼 표시 | 기존엔 `selected`만 복원(라디오 체크), `savedResult`는 null이라 "EDA 실행" 버튼이 숨어 사용자가 "선택 저장"을 또 눌러야 했음. 복원 한 줄 추가로 UX 정합. 회귀 0 (추가만) |
| D-139 | 기존 key_findings 텍스트는 `<details><summary>키 핀딩 N개 — 1B-2b 결정론 추출</summary>` 접어 보존. skeleton-note 문구는 제거 | 회귀 0 보강 — 1B-3c가 만든 finding 표시 자체는 유용하므로 폴딩 영역으로. 기본은 차트(STEP 3b)가 주, findings는 보조 |
| D-140 | styles.css는 **신규 클래스만 추가** (`.eda-charts`/`.chart-grid`/`.chart-card`/`.chart-card-head`/`.chart-footer`/`.chart-error`/`.btn-sm`/`.chart-summary`/`.chart-keypoints`/`.freeform-eda`/`.freeform-input`/`.freeform-approve`/`.code-preview`/`.freeform-actions`/`.freeform-result`/`.result-json`/`.findings-details`). 기존 `.eda-skeleton`/`.skeleton-note` 등은 미수정(렌더 0이지만 정의 보존 = 회귀 0) | 디자인 토큰(`--panel`/`--panel-2`/`--border`/`--c-*`/`--bg`/`--text`/`--muted`) 재사용. 외부 UI 라이브러리 0 (D-76·D-116 일관) |

### 구현 산출물
- `frontend/package.json` — `recharts: ^3.8.1` 추가
- `frontend/src/step5_analyze/charts/` 신규 (9 파일):
  - `common.js` — AXIS/GRID/TOOLTIP_STYLE/COLORS/CHART_HEIGHT 공통 상수
  - `ChartCard.jsx` — 디스패처 + ChartError + ChartFooter + AI 요약 훅(`/eda/summary` 클릭)
  - `Histogram.jsx`·`BoxPlot.jsx`·`FftSpectrum.jsx`·`RmsTrend.jsx`·`ClassDistribution.jsx`·`CorrelationBar.jsx`·`Pareto.jsx`·`Scatter.jsx`
- `frontend/src/step5_analyze/FreeformEda.jsx` — 자연어 입력 + /freeform → 코드 미리보기 → 승인/취소 → /freeform/approve → 결과 + lineage_id
- `frontend/src/step5_analyze/AnalyzePage.jsx` — eda-skeleton 블록 교체(eda-charts 섹션), runEda 함수(/plan → /render), savedResult 복원(D-138), key_findings를 details로 접음(D-139)
- `frontend/src/styles.css` — STEP 3b 클래스 신규 추가 (기존 미수정)

### 검증 결과 (명세 §9 체크리스트, 브라우저 e2e + curl)
3b-1 차트 렌더:
- `npm install recharts` 성공 (3.8.1, 41 packages)
- `npm run build` 성공 (776 modules, 606kB gzip 186kB) — recharts 정상 번들링
- **브라우저 SVG 렌더 (Playwright 1.60.0)**:
  - event-log 세션(press_forming.csv + quality_classification, e4b 추천): `class_distribution(BarChart)` + `boxplot_by_label(ComposedChart+ErrorBar)` 2 카드 → 각 카드에 SVG 1개 정상 렌더, label/축/툴팁 다크 톤
  - timeseries 세션(cnc_machine_injection + anomaly_detection, e4b 추천): `fft_spectrum(LineChart)` + `rms_trend(LineChart)` 2 카드 → 각 SVG 정상
- **8 chart_type 강제 render(curl)**: timeseries에서 6/8 정상(histogram·boxplot·fft·rms·correlation_bar·scatter), 2/8 modality 가드 정상 거부(class_distribution·pareto = categorical 전용)
- 폴백 분기: LLM 실패 시 `function_guide` 폴백 + 안내 메시지 (`llm_status === 'failed'` 검출)
- 에러 분기: 항목 error/data.error → `.chart-error` 박스 (차트 영역 비움)

3b-2 AI 요약:
- "AI 요약" 버튼 클릭(e4b ~4초) → `summary` + `key_points` 카드 내부 하단 표시
- 실측 출력: `"전체 3000건의 데이터 중 PASS 비율이 97.83% (2915건), FAIL 비율이 2.83% (85건)을 차지하며..."` — 입력 숫자 그대로 인용 (환각 방어 작동)

3b-3 자연어 EDA (시스템 정체성):
- 입력 `"FAIL 케이스만 골라서 PRESS_FORCE 평균과 표준편차 보여줘"` → /freeform (e4b 11초)
- 코드 미리보기 (monospace, 승인 전 실행 0):
  ```
  fail_press_force = df[df['PASS_YN'] == 'FAIL']['PRESS_FORCE']
  result = {"mean_press_force_fail": fail_press_force.mean(), "std_press_force_fail": fail_press_force.std()}
  ```
- "승인 후 실행" 클릭 → /freeform/approve → `{mean_press_force_fail: 120.4452, std_press_force_fail: 13.8226}` 표시
- `lineage_id` 표시(`2514e719...`) — 사용자가 감사 가능성을 시각적으로 확인

회귀:
- /select 흐름 보존: radio 6개(ANALYSIS_PURPOSES) 정상 렌더, 선택 후 저장 정상
- "다음 → (Page 6 모델링)" 링크 보존 1개
- QuestionRadioGroup 미수정
- 다른 페이지(1·2·3·4·6) 코드 0 줄 변경
- 기존 `.eda-skeleton`/`.skeleton-note` CSS 정의는 보존(렌더 안 하나 회귀 0 — 추가만)
- 강조 마커(별표) 0건 — 문서 정책 준수 (docs/decisions.md / docs/0_variable_index_v5.md 모두)

### 헌법 정합
- "AI 제안, 사람 결정"의 EDA 화면 완성 — 차트 추천은 LLM, 차트 데이터는 코드, 자연어 코드는 LLM + AST + 사용자 승인 + lineage. UI가 이 흐름을 그대로 보여줌
- 데이터 외부 전송 0 — recharts는 빌드 타임 번들(런타임 외부 호출 0). LLM은 로컬 ollama
- 회귀 안전 (다중 레벨): skeleton 한 블록만 교체 / styles 신규 클래스만 / 다른 페이지 0 / package.json recharts만 추가
- 옵션 카드 D-110/D-111 패턴 일관 — 자연어 EDA "승인 후 실행" 강제 클릭(승인 전 실행 0)이 옵션 카드 강제 선택과 동일 발상

### STEP 3b 완료 마일스톤 (브랜치 작업)
사용자가 표준화된 데이터에 대해: ① EDA 실행 클릭 → ② LLM이 차트 추천 → ③ recharts로 시각화 → ④ "AI 요약" 클릭으로 한국어 해설 → ⑤ 자연어로 자유 분석 요청 → ⑥ AI 코드 미리보기 → ⑦ 승인 → ⑧ 실행 결과 + lineage 표시. STEP 3a 백엔드의 5 엔드포인트가 모두 화면으로 연결.

다음: STEP 3c (실 ML 학습 — SMOTE/Under 실 적용 + 모델 fit) — 별도 브랜치.

## 2026-06-02 — STEP 3c: Page 6 ML 학습 실엔진 (백엔드)

명세: `docs/specs/STEP_3c_ml_training_engine.md`. 브랜치: `feature/step3-eda-ml`.

STEP 3b까지 골격이었던 Page 6 학습("학습 시작" → 모달 안내)을 실엔진으로. /recommend(1B-3c)는 그대로 보존, /train만 신설. task별 분기(지도/비지도), 파라미터 화이트리스트(clamp+notice), OOM 가드, 백그라운드 + 폴링, lineage 추적까지. 모두 결정론 (random_state=42).

| # | 결정 | 사유 |
|---|---|---|
| D-141 | `scikit-learn==1.5.2`, `xgboost==2.1.3`, `imbalanced-learn==0.12.4`, `joblib==1.4.2` 도입 (CPU 학습). lightgbm 미도입(추천 풀에 없음) | 트리 모델은 CPU + 26GB RAM 충분 — GPU 8GB(LLM 전용)와 무관. backend Dockerfile 재빌드로 4 패키지 임포트 성공 확인 |
| D-142 | `agents/ml/train_models.py` `TRAIN_MODELS` 4종 매핑(RandomForestRegressor/Classifier, XGBoostClassifier, IsolationForest) + `TRAINABLE_MODEL_NAMES` frozenset. advisory_only(CNNClassifier 등)는 매핑에 없음 → /train 400 자동 거부 | balance_options `BALANCE_OPTION_IDS`(D-107) / chart_types `CHART_TYPE_IDS`(D-120) 패턴 일관. modules.yaml.recommended_models 풀과 1:1(advisory 제외) |
| D-143 | task별 분기: regression(R²/RMSE + importance), classification(Acc/F1/이진AUC + confusion + importance), anomaly(n_anomaly/anomaly_ratio + score_distribution + importance None). 지도는 타겟 필요, 비지도(IsolationForest)는 타겟 없음 | 각 모델이 제대로 작동. 비지도에 타겟 강요하면 모순. confusion은 classification만, score 분포는 anomaly만 |
| D-144 | `agents/ml/param_whitelist.py` `ALLOWED_PARAMS` — 모델별 범위(tuple)/허용 목록(list)/`"fixed"`. `validate_and_clamp_params`는 범위 초과 시 clamp + `notices` 알림. 무조건 파기 X | 비현실값(환각/낭비)만 거름. 적합한 범위(10~500 등)는 통과 → 학습 품질 영향 0. /train/validate로 사용자 사전 확인(D-149). 옵션 카드 D-111 "결정의 의미 보존" 일관 |
| D-145 | `RANDOM_STATE = 42` 전역 고정. 사용자/LLM이 다른 random_state 보내도 무시(notice) + 42 유지. train_test_split, RF/XGB/IF의 random_state, OOM 가드의 row 샘플링 모두 42 | 재현성 — 같은 데이터 + 같은 params → 같은 metrics + 같은 importance hash. TEST 4에서 2회 학습 byte-identical(metrics/CM/importance) 확인 |
| D-146 | OOM 가드 2종: 카테고리 컬럼 unique > `CATEGORY_MAX_UNIQUE=100` → one-hot 폭발 방지로 제외(notice); 행 > `ROW_SAMPLE_THRESHOLD=200_000` → 결정론 샘플링(notice) | 실데이터 대비(synthetic 무발동). ITEM_CODE(2535 unique) one-hot이 OOM 주원인 — 검증에서 정상 발동 확인. CPU 학습이라 8GB VRAM 무관 |
| D-147 | `POST /train` → `_TRAIN_JOBS[job_id]` 인메모리 등록 + `asyncio.create_task(_run_train_job)` 백그라운드. 학습 본체는 `await asyncio.to_thread(run_training, ...)` — CPU 블로킹이 이벤트 루프 안 막음 | TEST 10에서 학습 중 /health 35ms, /train/status 17ms 응답 확인. 동기 학습 호출이 polling/다른 요청을 차단하지 않음 |
| D-148 | 학습 성공·실패 모두 `harness.lineage.record(transformation_type="model_train")`. 성공: `{model_name, task, metrics, params_used, notices, model_path, session_id}`. 실패: `{model_name, error, status:"failed", session_id}`. `applied_by_agent="user_approved_train"`, `user_approval_id=session_id`, `can_rollback=False`(학습은 rollback 의미 X) | 3a-2 freeform(D-128) 패턴 일관 — "어떤 모델, 어떤 파라미터, 어떤 결과/실패" 완전 추적. TEST 11에서 성공 4 + 실패 1(잘못된 타겟) 모두 lineage 기록 확인 |
| D-149 | `POST /train/validate` — 학습 전 파라미터 검증 endpoint. `{safe_params, notices, needs_confirmation}` 반환. 프론트(3d)가 notices를 사용자에게 보여주고 "조정 진행 / 취소" 결정 받게 | TEST 5에서 `n_estimators=100000 → 500`, `max_depth=99 → 30`, `random_state=999 → 42`, `foobar 무시` 4종 notice 정상 반환. 옵션 카드 강제 선택(D-111) 발상 — 사용자 인지 확보 |
| D-150 | `agents/ml/` 신규 패키지(`__init__.py`, `train_models.py`, `param_whitelist.py`, `train_engine.py`). `sys.path.insert(0, ROOT/"agents"/"ml")` — 디렉터리별 path 추가 패턴(D-130 동일) | `agents/` 자체를 path에 넣으면 기존 `from inspector import inspect` 회귀(D-130에서 발생). 디렉터리별 path 규칙으로 회귀 0. 절대 import(`from train_models import ...`) |

### 구현 산출물
- `backend/requirements.txt` — sklearn/xgboost/imbalanced-learn/joblib 추가 (4행)
- `agents/ml/__init__.py` — 패키지 docstring (3원칙)
- `agents/ml/train_models.py` — `TRAIN_MODELS`(4종 dict) + `TRAINABLE_MODEL_NAMES`(frozenset)
- `agents/ml/param_whitelist.py` — `RANDOM_STATE=42`, `ALLOWED_PARAMS`(4 모델 × 4 파라미터), `validate_and_clamp_params(name, requested) → (safe, notices)`
- `agents/ml/train_engine.py` — `CATEGORY_MAX_UNIQUE=100`, `ROW_SAMPLE_THRESHOLD=200_000`, `MODELS_ROOT`, `prepare_features`(타겟 분리 + OOM 가드 + one-hot + 결측 0), `feature_importance`, `run_training`(task 분기 + 직렬화)
- `backend/main.py` — `sys.path.insert agents/ml` + `TrainReq` + `_TRAIN_JOBS` + `_train_target_or_400` + `_run_train_job`(asyncio.to_thread + lineage 성공/실패) + 4 신규 엔드포인트:
  - `POST /api/model/{sid}/train/validate` (사전 확인, D-149)
  - `POST /api/model/{sid}/train` (백그라운드 시작, job_id 반환)
  - `GET /api/model/{sid}/train/status?job_id=` (폴링)
  - `GET /api/model/{sid}/train/result?job_id=` (결과)

### 검증 결과 (명세 §11 체크리스트, 실 HTTP + 다회 학습)
학습 엔진 (task 분기):
- 도커 재빌드 후 `import sklearn/xgboost/imblearn/joblib` 성공 (1.5.2 / 2.1.3 / 0.12.4 / 1.4.2)
- **분류** RandomForestClassifier(target=PASS_YN): Acc 0.972, F1 0.958, AUC 0.532, CM `[[0,17],[0,583]]` (불균형 데이터 영향), top3 importance TEMP/PRESS_FORCE/CYCLE_TIME, lineage `7026887f`
- **회귀** RandomForestRegressor(target=PRESS_FORCE): R² -0.13, RMSE 15.45, top features TEMP/CYCLE_TIME, lineage `f9606edd`
- **비지도** IsolationForest(target=None, timeseries 800행): n_anomaly=40, anomaly_ratio=0.05(contamination 0.05 그대로), score_distribution 30bin, importance None(IF), lineage `d30ef3ff`
- 재현성(TEST 4): RFClassifier 2회 학습 metrics/CM/top5 importance hash 완전 동일 (`2bbc6d8260699d06`)
- advisory_only(CNNClassifier) → HTTP 400 `"학습 불가 모델 (advisory_only 또는 미지원)"`
- 환각 모델(NeuralOracleXYZ) → HTTP 400

화이트리스트 + OOM 가드:
- /train/validate(n_estimators=100000, max_depth=99, random_state=999, foobar=42) → safe_params `{n_estimators:500, max_depth:30, random_state:42}` + notices 4개("최대 500으로 조정", "최대 30으로 조정", "42로 고정", "허용 파라미터가 아님 — 무시") + `needs_confirmation:true`
- 고차원 카테고리 자동 제외: ITEM_CODE(2535) / LOT No.(800) / TimeStamp(800) → notice 표시 (정상 발동)
- row 20만+ 가드: synthetic 데이터(3000/800행)에선 미발동 — 코드 경로 확인됨

백그라운드 + 폴링:
- POST /train → job_id 즉시 반환(running 상태)
- GET /train/status → running → completed 전이 (TEST 10에서 17ms 응답)
- GET /train/result → 학습 결과 (metrics, confusion/score_dist, importance, notices, lineage_id)
- **이벤트 루프 비차단**: 학습 진행 중 /health 35ms, /train/status 17ms 응답 (asyncio.to_thread 정상 동작)

lineage + 회귀:
- 성공 학습 → `model_train` entry: `{model_name, task, metrics, params_used, notices, model_path, session_id}` 기록
- 실패 학습(잘못된 타겟 'NONEXISTENT_COL') → status:"failed" + lineage `{model_name, error, status:"failed"}` 기록 (감사 누락 0)
- /api/lineage?dataset_id=press_forming.csv → 8 entries 중 6 `model_train` (성공 + 실패 모두 포함)
- /api/model/{sid}/recommend 정상 (LLM 추천 + fit_score + advisory_only 마킹 — 회귀 0)
- Page 1~5(/select·/questions·/eda/*·/execute_pipeline·/pipeline/approve 등) 영향 0 — 신규 엔드포인트만 추가

문서:
- decisions.md D-141~D-150 추가
- variable_index_v5.md STEP 3c 본문 섹션 추가
- 강조 마커(별표) 0건 — 문서 정책 준수 (decisions.md / variable_index_v5.md 모두)

### 헌법 정합
- "LLM 제안, 규칙 결정" 모델링 적용: LLM 추천(/recommend, 기존 1B-3c) + 코드 학습(scikit-learn/xgboost 결정론) + 규칙 안전 거름(화이트리스트 clamp+notice)
- 데이터 외부 전송 0: 모든 학습 로컬 CPU. LLM은 로컬 ollama
- "AI 자율 + 사람 통제 + 추적": LLM이 모델 추천 → 사용자가 파라미터 선택(노티스 보고 결정) → 학습 → lineage 기록
- 8GB VRAM 정합: 트리 모델은 CPU+26GB RAM. GPU(LLM 8GB)와 분리 → 학습이 LLM 병목 안 받음 / advisory_only(CNN) 자동 거부로 VRAM 폭주 방지
- 회귀 안전 (다중 레벨): /recommend 불변 / Page 1~5 영향 0 / sys.path 디렉터리별 패턴(D-130 일관) / 신규 엔드포인트만 추가
- 옵션 카드(D-110/D-111) 패턴 일관: 파라미터 화이트리스트 clamp+notice는 "사용자 인지 후 결정"의 모델링 적용. 무조건 파기 X(옵션 카드도 디폴트 자동 선택 X)

### STEP 3c 완료 마일스톤 (브랜치 작업, 백엔드)
사용자가 표준화된 데이터에 대해 LLM 추천 모델을 선택하면: ① 파라미터 사전 검증(`/train/validate`) → ② 백그라운드 학습(`/train`) → ③ 폴링(`/status`) → ④ 결과 조회(`/result`)로 task별 메트릭(confusion / R² / score 분포 + feature importance) + lineage_id 반환. 화이트리스트가 비현실값 거르고, OOM 가드가 고차원 카테고리 자동 제외. 모두 결정론 + 감사 가능.

다음: STEP 3d (Page 6 학습 UI — TrainSkeletonModal 교체 + recharts confusion/score chart + lineage 표시) — 별도 브랜치 가능.

## 2026-06-02 — STEP 3d: Page 6 학습 UI (TrainModal)

명세: `docs/specs/STEP_3d_training_ui.md`. 브랜치: `feature/step3-eda-ml`.

STEP 3c 학습 백엔드(4 엔드포인트 + lineage)를 화면으로. TrainSkeletonModal(25줄 골격)을 TrainModal로 교체 — task 분기(지도 vs 비지도), 폴링, 시각화(confusion CSS 그리드 + 3b 차트 재사용), lineage 표시까지. ModelingPage·ModelCard·/recommend 모두 보존 (회귀 0).

| # | 결정 | 사유 |
|---|---|---|
| D-151 | `TrainSkeletonModal.jsx` 삭제 + `TrainModal.jsx` 신설(교체). ModelingPage는 import 교체 + `sessionId={sid}` prop 추가 + skeleton-note 안내문 제거. ModelCard / /recommend 미변경 | 명세 §6 — "교체 = TrainSkeletonModal 한 컴포넌트". 회귀 0: `onTrain(rec)`/executable·advisory 분리·"← Page 4로 돌아가기" 링크 모두 보존. 25줄 dead code 보존하면 cruft — `git rm`이 깔끔 |
| D-152 | `GET /api/model/{sid}/data_profile` 신설 — `build_eda_profile`(3a, LLM 0) 그대로 호출, 컬럼 메타만 반환. `/eda/plan`(LLM e4b 9초) 재호출 회피 | 타겟 드롭다운에 LLM 불필요(parquet 메타만). 명세 §2 — "Page 6에서 /eda/plan 재호출 비효율". `_pick_eda_target`(3a) 재사용 — 비-이미지 모듈 자동 선택. LLM 0 audit: data_profile은 generate 호출 0 |
| D-153 | TrainModal task 분기: 지도(`regression`/`classification`) = 타겟 컬럼 드롭다운(/data_profile + 필터) + KPI(R²/RMSE 또는 Acc/F1/AUC) + (분류만)confusion matrix + feature importance / 비지도(`anomaly`) = 타겟 없음 + contamination 슬라이더(0.01~0.5, step 0.01) + KPI(전체/이상치/이상 비율/contamination) + score 분포 | 각 모델에 맞는 입력·결과. 비지도(IsolationForest)에 타겟 강요 안 함(D-143 백엔드 분기와 정합). 사용자 인지 명확 — 모달에 "task" 라벨 표시 |
| D-154 | Confusion Matrix = 자체 CSS 그리드 + 색 농도(`agents/eda`/3b recharts 의존성 0). 대각선(정답) = `--c-quality` 초록 농도 `rgba(22,163,74, 0.15+ratio*0.55)`, 오답 = `--c-maintenance` 주황 농도 `rgba(234,88,12, 0.10+ratio*0.45)`. 셀 hover 툴팁 + 대각선 셀 font-weight 강조 | recharts에 heatmap 컴포넌트 없음 — SVG/외부 라이브러리 도입 회피(D-118 일관). CSS Grid `gridTemplateColumns: auto repeat(N, 1fr)`로 n×n + 라벨 헤더·행 자동. 불균형 시각화(FAIL 못 잡음 = 좌하단 비대각) 즉시 보임 |
| D-155 | 3b 차트 재사용: `Histogram`(score 분포 — bins/counts 형태 1:1), `CorrelationBar`(feature importance — 어댑터 `{target_column:'중요도', columns:features, values:importances}`). 단 `ChartCard` 디스패처(`CHART_TYPE_IDS` frozenset)는 **EDA 전용 유지** — Page 6은 컴포넌트만 import | 환각 방어 contract(D-120/D-132) 보호 — CHART_TYPES에 train 차트 추가하면 EDA LLM이 학습 chart_type을 추천해 의미 충돌. 컴포넌트만 재사용(데이터 어댑터로 형태 맞춤) → 코드 재사용 + contract 분리 |
| D-156 | 폴링: `setInterval` 1초 간격(`/train/status` → 완료 시 `/train/result`). cleanup 다중 안전 — (a) 모달 unmount `useEffect` cleanup, (b) 사용자 닫기 클릭 `closeAndStop`, (c) 새 학습 시작 시 `stopPolling` 재설정, (d) "다시 학습"·완료 모두 stopPolling. `pollRef = useRef(null)` + `clearInterval(pollRef.current); pollRef.current=null` 패턴 | 메모리 누수 0. 진행 표시 `train-progress`에 job_id 8자 표시(D-148 lineage 추적과 일관). React Hooks 규칙 준수 — early return은 모든 useState/useEffect 호출 후 (`if (!model) return null`을 hooks 뒤로) |
| D-157 | 타겟 컬럼 필터 (지도): regression → `c.is_numeric === true`(예: PRESS_FORCE, INJECTION VELOCITY 같은 숫자). classification → `!c.is_numeric \|\| c.n_unique <= 10`(저카디널리티/범주 — PASS_YN 같은 라벨). 드롭다운 항목 라벨 `"PASS_YN (범주 2종)"`/`"PRESS_FORCE (숫자)"` 명확 | UX — 잘못된 타겟 선택 사전 방지. ITEM_CODE(2535종) 같은 ID 컬럼은 분류 후보로 통과되지만(필터가 약함) OOM 가드(D-146)가 추가 안전. 회귀에 PASS_YN 같은 string은 백엔드 ValueError로 failed lineage |
| D-158 | TrainModal 입력 단계 → 폴링 진행 → 결과 단계 흐름. 결과에 `notices`(화이트리스트 clamp+OOM 가드 알림) + `lineage_id` 표시. "다시 학습"으로 결과 초기화 + 같은 모달 재사용 (모달 닫지 않고 재시도) | 옵션 카드 D-111/D-135 패턴 — 사용자 결정 흐름 단일 모달 내 완결. lineage_id 8자 표시는 3a-2 freeform 결과(D-135) 패턴 일관. "완료" = closeAndStop으로 폴링 정리 + 모달 닫기 |

### 구현 산출물
- `backend/main.py` — `GET /api/model/{sid}/data_profile` 신규(`build_eda_profile` 호출, LLM 0)
- `frontend/src/step6_modeling/TrainModal.jsx` 신규 — task 분기 + 폴링 cleanup + TrainResult 내부 컴포넌트 + Kpi 내부 컴포넌트
- `frontend/src/step6_modeling/charts/ConfusionTable.jsx` 신규 — CSS 그리드 + 색 농도(대각선/오답) + 셀 hover title
- `frontend/src/step6_modeling/ModelingPage.jsx` 수정 — import 교체(`TrainSkeletonModal` → `TrainModal`), `sessionId={sid}` 전달, skeleton-note 제거
- `frontend/src/step6_modeling/TrainSkeletonModal.jsx` 삭제 (`git rm`, dead code)
- `frontend/src/styles.css` — 신규 클래스(`.train-modal`/`.train-field`/`.train-notices`/`.train-progress`/`.train-result`/`.train-chart-block`/`.train-lineage`/`.metrics-grid`/`.kpi-card`/`.kpi-accent`/`.kpi-label`/`.kpi-value`/`.confusion-wrap`/`.confusion-title`/`.confusion-grid`/`.cm-corner`/`.cm-head`/`.cm-rowhead`/`.cm-cell`/`.cm-diag`/`.cm-off`). 기존 클래스 미수정

### 검증 결과 (명세 §9 체크리스트, 브라우저 e2e + curl)
task별 모달 UI (Playwright):
- 지도 분류 RandomForestClassifier(press_forming.csv + quality_classification): 타겟 드롭다운 `ITEM_CODE(범주 2535종)/LOT_NO(범주 60종)/PASS_YN(범주 2종)` — 분류 필터 작동. PASS_YN 선택 후 학습 → confusion 4 cells(2×2 PASS/FAIL) + 대각선 2개(초록 농도) + 4 KPIs(Accuracy/F1/AUC/학습-검증) + importance SVG(CorrelationBar 재사용) + lineage `bcdc2265`
- 지도 회귀 RandomForestRegressor(cnc_machine_injection + process_optimization): 타겟 드롭다운 `1ST INJECTION VELOCITY(숫자)/2ND.../3RD...` — **회귀 필터 numeric만 작동**(범주 컬럼 비표시). 학습 → KPI(R²/RMSE/학습-검증) + importance SVG + confusion 부재(정상)
- 비지도 IsolationForest(cnc_machine_injection + predictive_maintenance): 타겟 드롭다운 없음(target select 0개), contamination 슬라이더(1개) + 슬라이더 값 변경 동작. 학습 → histogram SVG 1개(Histogram 재사용) + confusion 0개 + 4 KPIs(전체/이상치/이상 비율/contamination)
- /data_profile end-to-end(LLM 0): 0.5초 미만 응답, `available:true` + columns 6개 + dataset_id/modality

폴링 + 결과:
- POST /train → job_id → setInterval 1초 폴링 /status → completed 전이 → /result 자동 호출 → result state set
- "⏳ 학습 진행 중… (1초 폴링, job 8자)" 표시 가시 확인
- 모달 닫기(완료 또는 backdrop) → cleanup → modal count = 0 확인
- React Hooks 규칙 준수 검증 — `if (!model) return null`를 hooks 뒤로 이동 후 "Expected static flag was missing" 경고 0건

시각화:
- ConfusionTable: CSS 그리드, 대각선 `--c-quality` 농도(`rgba(22,163,74,a)`) / 오답 `--c-maintenance` 농도(`rgba(234,88,12,a)`), 셀 hover에 `실제 X → 예측 Y: V` 표시
- score 분포: Histogram 재사용(bins/counts 1:1, column='anomaly_score')
- feature importance: CorrelationBar 재사용(어댑터 `{target_column:'중요도', columns, values}`)
- notices: "안전 조정·가드 알림" 박스(`.train-notices`, L2 톤 maintenance 좌측 보더). 화이트리스트(D-144) + OOM(D-146) clamp/제외 메시지 표시
- lineage_id 8자 표시(`.train-lineage code`) — SI 추적성 시각화

화이트리스트 알림:
- "파라미터 확인"(/train/validate) → notices 영역 표시 + safe_params 노출. notices가 빈 경우 "조정 사항 없음. 안전 범위 통과."

회귀 0:
- `/recommend` 정상(rec 키 8개 그대로: name/fit_score/rationale_ko/context_reflections/task/when/from_node/advisory_only)
- `/eda/render` 정상(class_distribution 차트 data PASS 2915/FAIL 85)
- `frontend/src/step5_analyze/charts/ChartCard.jsx` diff 0줄 — `CHART_TYPE_IDS` 환각 방어 contract 보존(D-120 일관)
- Page 1~5(`step1_line/`/`step2_user_input_pipeline/`/`step3_user_input_data/`/`step4_standardize/`/`step5_analyze/`) 코드 변경 0
- styles.css 기존 클래스 미수정(139줄 추가만)
- `git diff --stat`: backend/main.py(+27), step6_modeling/ModelingPage.jsx(±11), TrainSkeletonModal(-25 삭제), styles.css(+138) — STEP 3d 범위만
- 강조 마커(별표) 0건 — 문서 정책 준수 (decisions.md / variable_index_v5.md)

### 헌법 정합
- "LLM 제안, 규칙 결정"의 학습 UI 완성: LLM 모델 추천(/recommend, 기존) → 사용자 타겟/contamination 선택 → 코드 학습(결정론, random_state=42) → 시각화 + lineage
- 데이터 외부 전송 0: /data_profile은 parquet 직접 읽기, recharts는 빌드 타임 번들. LLM은 로컬 ollama
- 추적성 시각화: lineage_id 표시 + notices 박스로 "어떤 안전 조정이 일어났는가" 사용자에게 가시화 — SI 컴플라이언스
- 회귀 안전 (다중 레벨): TrainSkeletonModal 1개만 교체 / styles.css 신규만 / Page 1~5 0 / ChartCard 디스패처 무변경(CHART_TYPE_IDS 보호) / /recommend·/eda/* 모두 보존
- 차트 재사용 + contract 분리(D-155): 3b 컴포넌트 재사용으로 중복 0, ChartCard 디스패처는 EDA 환각 방어 contract 그대로 — 재사용과 contract 보호 양립

### STEP 3d 완료 마일스톤 (브랜치 작업, 프론트엔드)
사용자가 Page 5에서 분석 목적을 선택하면 Page 6에서: ① LLM이 적합한 모델을 추천(fit_score) → ② 모델 카드의 "학습 시작" 클릭 → ③ task별 입력(지도=타겟 드롭다운 / 비지도=contamination 슬라이더) → ④ "파라미터 확인"으로 notices 사전 확인 → ⑤ "학습 시작" → 1초 폴링 → ⑥ 결과: KPI 카드 + (분류)confusion CSS 그리드 / (회귀)R²/RMSE / (비지도)score 분포 + feature importance + notices 박스 + lineage_id 표시. STEP 3 전체(3a EDA + 3b EDA UI + 3c 학습 백엔드 + 3d 학습 UI) 완성.

다음: 별도 브랜치 — main 머지 또는 후속 기능(파라미터 수동 입력 UI · 모델 비교 · 추론 엔드포인트 등).

## 2026-06-08 — datalake-redesign R1: 명세 patch (Master 저작 → CC 적용)

명세: BLUEPRINT(설계 SSOT) §5 매핑표를 본진 명세에 반영. 순수 문서·코드 0. 브랜치: `feature/datalake-redesign`.
대상: spec-1 §1-2/§1-5/§1-6/§1-9-1/Part3/§4-3, blueprint Part4-2, variable_index §8.

| # | 결정 | 사유 |
|---|---|---|
| D-159 | 물리경로 A/B 폐기 → **DB catalog 단일 진입점**. `data_path` 컬럼이 경로 추상화 → 셀렉·엔진은 `datalake_id`만 인지, 물리경로는 `data/lake/<id>/`로 귀결(선택 아님). **D-53 supersede** (D-53 "datalake_id=기존 dataset_id 직접 사용, 카탈로그 미도입 전제"는 카탈로그 도입으로 폐기) | A/B는 결정 항목이 아니었음. 합성데이터 미생성·KAMP 외부폴더 → 마이그레이션 대상 0(클린 출발). KAMP·신규 대등 = 핵심 메시지("어떤 데이터가 와도") 정합 |
| D-160 | catalog = **정규화 3테이블**(asyncpg): `datalake.entries`(타입드 인덱스 컬럼) + `datalake.columns`(per-column) + `datalake.constraints`(per datalake_id+column). 단일 JSONB metadata 폐기. 비대칭 수용: catalog=DB / session·lineage=인메모리(Sprint 2 postgres) | anti-silent-conversion — 런타임 슬롯/폴더 추론 대신 권위 컬럼. Silent 변환이 SI 장애 주원인 → 타입드 인덱스로 구조 차단. 멱등·비파괴(CREATE IF NOT EXISTS, DROP 금지) |
| D-161 | `datalake.columns.column_kind = scalar \| group`. FFT 광폭/숫자헤더(L3 vibration, 컬럼=주파수값 수천)는 per-column 부적합 → **컬럼-그룹 descriptor**(`fft_spectrum: N개 numeric-header, 단위·범위`). 제약도 집계/대역형 | R0 KAMP 확인 + 사용자 확인 완료. per-column 폼이 수천 컬럼에 깨짐 → 그룹 단위로 구조화 |
| D-162 | `vid`(가상 그룹 ID) = **공정 흐름(라인) 단위·단일**(1 데이터셋=1 흐름). 인계서 `hash(process+module)`에서 라인 단위로 교정. `reusable_flag`로 후속 다대다(reference 공유) 무손실 확장. `function`/`site`는 vid 내 별도 필터 컬럼(vid 종속 아님). 전파 3곳(스키마→`_build_agent_record`→`_build_stage_chain`), 결정론·LLM 0(D-59 유지) | Page 1 라인 선택이 자연스러운 흐름 경계. 단일 시작 + flag로 확장 = 무손실. 흐름·계보 컨텍스트의 기반 |
| D-163 | **modality 결정론 라우터** `datalake.get(id) → {data_path, modality}`. 기존 `_resolve`(timeseries/order) + 이미지 경로 + event-log 경로 3곳 통합. LLM 0 | 데이터→엔진 경계 단일 해석점. 모달리티 분기 중복 제거, 환각 방어(결정론) |
| D-164 | **엔진 보존 이음매(additive seam)** — 데이터→엔진 경계(`dataset_id→파일경로`)만 `datalake.get`으로 추상화. 뒤의 `pd.read_csv → Inspector·Planner·Executor·Validator·학습`은 변경 0. **D-66/D-67 validator(제약=원본 backup parquet 직접 대조) 변형 0 계승** — 신규 resolve 아님, lineage 보존 | 검증된 엔진 불변 = 롤백 최소화(PROTOCOL §3). 구 경로 생존. D-67의 "원본 기준 검증"은 정확성·추적성 자산이라 그대로 |
| D-165 | Page 2 모델 = **4 function 모듈(P/Q/M/R) 배치** + P 체인(`chain_order`) + M/Q→P 묶음(`attached_to`). module 스키마 +`vid`/+`chain_order`/+`attached_to`. 기존 `(function,dataset_role)` 중복 차단 규칙 폐기(같은 function 복수 허용). 이중 처리: MCP=개별 주체 / EDA=흐름 내 위치 | 사용자 비전의 공정 흐름 구성. 데이터셋 드래그가 아니라 기능 슬롯 배치 → 데이터 바인딩은 Page 3 분리 |
| D-166 | Page 3 셀렉 = **vid × function × site 메타필터 → 카드 UI** → 제한 목록 셀렉. 기존 modality+function 드롭다운 대체 | vid로 흐름 범위 한정 → 카드로 선택지 축소. 메타 기반 진입 |
| D-167 | 제약 가드 = **무조건 유저 입력**(시스템 제안 0, D-43 강화). prefill = `datalake.constraints`(유저 과거 승인값) **제안만** — 잠금/자동적용 금지, 매칭돼도 **항상 재승인 게이트**. 키 스코프 = `datalake_id+column`. 머지 = **세션 오버라이드 > 카탈로그 prefill(재승인) > 빈칸**. 변경 시 "이번만 vs 메모리 업데이트(영속)" 질문. 불변식: catalog 제약 = 제안이지 디폴트 아님 (물리 컬럼명 `column_name`/`constraint_spec` — D-171) | SI는 고객사 머신별 limit을 모름 → 선택권 유저. 캐시 자동 고정 = 사실상 시스템 디폴트 = D-43 위반. 재승인으로 "LLM/시스템 제안, 사람 결정" 보존 |
| D-168 | validator **"제약 공백/상태 알람"** 신설(데이터-미업로드 알람과 대칭). 승인 게이트 = Page 3 입력 시점 / 상태 알람 = validator 시점. MCP `/check_constraints` = 죽은 코드(미호출) 명시 | 제약 미입력/공백을 validator가 표면화 — 데이터 알람과 동일 패턴. 검증 책임 위치 명확화 |
| D-169 | EDA **slim stage_chain** — `eda_engine.py` payload에 `node_id + downstream_implication`만 1키 + system prompt 1줄 추가. `main_findings`는 `key_findings`와 중복이라 생략. 상류(aggregator/main) 0. 결정론 `compute_chart_data` 무관(D-59 생명선 0) | 현 EDA가 stage_chain을 빌드만 하고 미소비 — main.py가 이미 ctx 통째로 넘기는데 안 꺼내 씀. e4b/26b JSON 안정성·8GB 토큰 위해 slim. "작은 엔진 손"(additive) |
| D-170 | `AggregatedContext` +`analysis_groups`(additive, shape는 DL-4 확정). 원칙 잠금: **이종 매핑 부재 + lineage 흐름 컨텍스트 = 상보** — 이종 데이터를 스키마로 융합 안 함(개별 주체 유지), vid/stage_chain/lineage로 흐름·계보 관계 부여(+@ 컨텍스트). 데이터 비종속(D-82) → 메타 기반 catalog로 진화 | 융합 없이 흐름·계보로 관계 부여 = 안전한 +@. lineage 흐름 컨텍스트 강화는 후속 추가기능. 적재도구 메타 자동생성으로 "파일 넣고 한 번 적재=끝" 비종속성 유지 |
| D-171 | `datalake.constraints` 컬럼 `column`/`constraint`는 PostgreSQL **예약어** → 따옴표 없는 컬럼명으로 CREATE TABLE syntax error. **rename**: `column`→`column_name`, `constraint`→`constraint_spec` (DDL·PK·CRUD 전부). 따옴표 우회 대신 rename 채택 | 모든 CRUD에서 따옴표 강제 = silent foot-gun(따옴표 누락 시 깨짐) = anti-silent-conversion 철학 위배. rename은 의미 불변(키 스코프 = datalake_id+column_name, D-167 무변), 영구 따옴표 부채 0. R1 §1-5 DDL 잠재버그 교정 |
| D-172 | `catalog.upsert_entry` = **full-record-replace 시맨틱**(`ON CONFLICT(datalake_id) DO UPDATE SET 모든 컬럼=EXCLUDED`). 부분 필드 호출 시 미지정 컬럼이 NULL로 덮임. **계약: 호출자는 항상 완전한 레코드 전달**(부분 변경은 targeted UPDATE). registered_at만 UPDATE SET 제외(최초값 보존) | DL-2 적재도구가 매번 전체 메타 생성·upsert(D-82 "파일 넣고 한 번 적재=끝")라 full-replace가 의도된 올바른 동작 — 재적재 = 메타 전체 갱신. COALESCE 보존은 오히려 재적재 시 필드 정리 불가로 부정확. 부분 upsert = misuse → anti-silent-conversion상 계약 명문화. DL-1 A7 투명보고에서 식별 |

### 정합 확인
- D-53 supersede 명시(D-159), D-66/D-67 변형 0 계승 명시(D-164), D-43 강화(D-167), D-59 생명선 보존(D-163/169), D-82 진화(D-170).
- spec-1 §1-2/§1-5/§1-6/§1-9-1/Part3/§4-3 + blueprint Part4-2 + variable_index §8 동기 패치.
- 코드 0 — 본 블록은 R1(문서) 산출. 구현은 DL-1~DL-5.

### R1 완료 = DL-1 진입 가능
다음: DL-1(DB 연결 + catalog 접근 계층). 진입 선결(PROTOCOL §3/§4): ① `.env` DB 접속(127.0.0.1:5432, 자격=시크릿) ② 변경 전 build+smoke green ③ 공유 PG(byeonggab89) 첫 쓰기 전 백업.

## 2026-06-09 — datalake-redesign DL-2 진입: id·메타 권위 + 스키마 확장 (Master 저작 → CC 적용)

명세: DL-2(KAMP 적재) 진입 결정. CC dry-run 실측 근거(파일시스템 추론 신뢰 불가 — id 3건 silent divergence, order 휴리스틱 오분류, vibration 라벨 오류). 브랜치: `feature/datalake-redesign`.

| # | 결정 | 사유 |
|---|---|---|
| D-173 | **메타 권위 = `catalogs/datalake_manifest.yaml`(SSOT, repo 추적).** 적재도구의 파일시스템 추론(파일명 유도 `datalake_id`·폴더 파싱 `vid`) 폐기. `datalake_id`·`vid`(module 기준)·`modality`·`function`·`site` = manifest 명시값 권위. 휴리스틱(L접두사·module_N·포맷)은 manifest 작성용 **seed**일 뿐 — dry-run 검토 대상. ingest는 manifest **읽기만**(파생 0). manifest의 DB-미적재 필드(node·capture)는 ingest가 **명시적 화이트리스트로 처리**(`entry.get()` silent drop 금지 = anti-silent). per-column scalar 이름·dtype은 파일 헤더 실측(사실 읽기), group descriptor는 manifest 권위 + 파일 검산. BLUEPRINT §3 "ingest 자동 도출" refine. | 파일시스템 추론은 폴더명 접미(`_image`/`_quality`)·비ASCII만으로 silent 어긋남(34건 중 3건 실현, function 폴백이 은폐 → 더 위험). IATF·CFR(감사·재현성) 타깃에서 id·modality silent 오도 불가. `hint_dataset`(Page 2 참조)을 권위로 = Page 2↔catalog 바인딩 정의상 일치. 선언적 manifest row 추가 = D-82("파일 넣고 한 번 적재=끝") 정합 |
| D-174 | **entries 스키마 확장 (+`format` +`company`).** `format TEXT`(원본 파일 포맷, #11 lineage — canonical utf-8 정규화 후 원본 추적), `company TEXT`(멀티테넌트 필터 차원, `site` 형제). D-160 "12 타입드 컬럼" → 14컬럼 확장. 멱등·비파괴: 기존 테이블(DL-1 생성)은 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`(DROP 0, PROTOCOL §3), CREATE문 동기 갱신. `company` index 추가. 구현(catalog.py MIGRATION_SQL/upsert_entry)은 요청 A. | `format` — ingest가 xlsx를 encoding칸에 silent 혼입(dry-run `enc=xlsx` 실측), 정규화 후 원본 format·encoding 둘 다 보존하려면 분리 필수(#11). `company` — 멀티테넌트 SI 제품 전제, 다른 회사=다른 `datalake_id`라 PK 무관 순수 필터. 빈 테이블(0행)이라 ALTER 무비용 = 추가 최적시점 |
| D-175 | **capture·node = manifest provenance만, DB 컬럼 미추가.** 멀티캡처/재현(같은 라인 다른 캡처 무손실 보존)은 **PK=`(datalake_id, capture)` 복합 + `data_path` 계층(`data/lake/<id>/<capture>/`) + 재적재 dedup 동반 설계 = 별도 트랙(도래 시)**. 현 KAMP=단일 캡처라 의미 0. | 현 D-172(PK `datalake_id` 단일 + full-record-replace upsert)에선 같은 id 다른 캡처 = 덮어씀(재현 0) → capture 단순 컬럼 추가는 반쪽 함정. 진짜 멀티캡처는 D-159/160/172 재설계라 DL-2 범위 밖, reusable_flag(D-162)와 동일 무손실 확장 전략으로 예약. node = D-166 필터축 아님(파이프라인 슬롯 속성)이라 entries 부적합, lines.yaml 실재 |
| D-176 | **D-161 라벨 정정 (`fft_spectrum`→`waveform`).** L3 vibration(`vibration_fault_sim`/`sim2`)은 FFT가 아니라 **raw 시간영역 waveform** — 헤더 숫자=시간오프셋[s](step→fs 488/800Hz, 1열=캡처 timestamp), 윈도 0~4.195s/2.559s. `column_kind=group` descriptor 실질 불변(1 scalar + N group), 라벨만 정정 + `group_desc`={axis:`time_offset_s`, `fs_hz`, `window`}. D-161 구조 결정(광폭=group, per-column 금지) 전부 유지. | "range 4.195 Hz"는 진동 물리 난센스 → 시간영역 확정(헤더 실측). R0 "FFT 광폭"은 도구 하드코딩 라벨을 옮긴 초안 → 두 트랙 독립 실측으로 waveform 이중확인. 감사·재현성 타깃에서 물리적으로 틀린 메타 라벨 불가 |
| D-177 | **R0 가정 3건 실측 정정.** (1) "order 0건(데모 제외)" → **order 1건 실재**(order_planning, function=reference, module_3 set). modality=order 명시(휴리스틱 timeseries 오분류 교정), id=module_3 기준 semantic(cp949를 id에 안 박음 — encoding 별도 필드), 데모 주흐름 비중심. (2) "대부분 ASCII, cp949 우려 해소" → **cp949 3건**(order_planning·L4_ict_checker·L4_ict_inspection) → encoding 컬럼 기록 + utf-8 정규화. (3) **#15 이종 묶음 2폴더**(L1_mct_tool_improve·L3_mct_condition_inspect = 기술검증결과서 리포트, 8~9 이종 스키마+무헤더 1) = 데모 적재 제외(보류 플래그) → **34→32건**. | dry-run 실측이 R0 가정 교정(쓰기 전 보험 본전). order 미분류 시 timeseries MCP 오라우팅 위험. 리포트 산출물은 ML 데이터셋 아니라 제외해도 "어떤 데이터든" 메시지 훼손 0(나머지 32건 증명) |

### 정합 확인
- D-160 확장(D-174, 12→14컬럼) · D-161 라벨 정정·구조 불변(D-176) · D-172 보존(D-175 capture 보류 근거) · D-82 정합(D-173) · D-43/D-167 불변(적재도구 constraints 미기재 유지) · anti-silent 강화(D-173 silent-drop 금지 / D-174 format).
- spec-1 §1-2/§1-5/§1-6 + blueprint §1.2/§3 + variable_index §8(DataLakeEntry +format/+company, column_kind waveform) 동기 패치 완료.
- 코드 0 — 본 블록은 문서 산출. catalog.py ALTER/upsert + ingest manifest-driven = 요청 A.

### DL-2 다음 단계
요청 A(write-0): `catalogs/datalake_manifest.yaml` 32행 작성 + ingest manifest-driven 리팩터(EXECUTE_ENABLED=False 유지, 복사·INSERT 0, dry-run이 manifest↔1_data 정합 검산). → dry-run 통과 → 요청 B(실적재 = replace_columns + 백업 게이트 + Master greenlight).

## 2026-06-10 — DL-2 B Phase 1 (진입게이트 ①③ 실행 + 백업게이트 재정의)

| # | 결정 | 사유 |
|---|---|---|
| D-178 | DL-2 B 백업 게이트 재정의 — **빈 테이블 additive ALTER는 논리 baseline으로 갈음, 정식 백업은 Phase 2 直前으로 이월.** ③ 라이브 ALTER(entries +format/+company +idx_datalake_company) 시점 datalake 3테이블 0행 → 보호 대상 0 + ALTER가 additive·멱등·가역(`DROP COLUMN/INDEX IF EXISTS`) → pg_dump 없이 진행. 정식 백업 게이트(PROTOCOL §3 "대량 ingest 전 스냅샷")는 데이터가 들어가는 Phase 2(实ingest) 直前으로 이동. 백업 메커니즘 = **python/asyncpg 논리 덤프**(datalake 스코프·TCP·owner=myeongsun 전건) — host pg_dump 미설치 + mfg-postgres가 byeonggab89 rootless 네임스페이스라 `docker exec` 영구 불가(STEP A0/C 실측). | 0행 additive ALTER에 정식 덤프는 보호가치 0(실제 보호점=데이터 적재 시점). docker-exec·host pg_dump 둘 다 환경상 불가 실측 → 논리 덤프가 유일 CC 경로이며 owner 권한으로 누락 0 전건 가능. PROTOCOL §3 취지(데이터 손실 차단) 유지, 게이트 시점만 의미점으로 이동(스킵 아님) |

## 2026-06-11 — datalake-redesign DL-2.5 hardening: 복원드릴·constraints 감사·자동화테스트·설계잠금 (Master 저작 → CC 적용)

명세: DL-2 GATE PASS 직후 pre-DL-3 경화 4건 — ① 복원 드릴(백업 실효성 입증) ② constraints 감사 스키마(approved_by + history) ③ throwaway PG 자동화 pytest ④ 설계 잠금. 라이브 쓰기 = constraints 감사 ALTER 1회(additive·DROP 0, 백업·복원드릴 선행). 브랜치: feature/datalake-redesign.

| # | 결정 | 사유 |
|---|---|---|
| D-179 | constraints에 approved_by 추가, 모든 쓰기/삭제는 동일 트랜잭션에서 datalake.constraints_history(append-only, FK 없음, 앱 레벨 기록)에 action과 함께 적재. 현재 테이블은 last-write-wins 유지(prefill 소스 단순성), 이력은 history가 보존. 불변식: datalake.constraints에 대한 모든 현재·미래 쓰기 경로(DL-3에서 추가될 함수 포함)는 동일 트랜잭션 내 constraints_history append를 의무로 한다. 전용 delete_constraint는 DL-3 구현 시 이 불변식 준수 하에 추가(이월 트래킹). | D-167의 본질=유저 승인 — 주체·시점·이전값 추적 없는 승인은 반쪽. IATF/CFR 맥락(D-173) 정합. 0행 시점 additive ALTER가 최저비용. |
| D-180 | 판별자 type 필수. scalar: {"type":"range","min":num\|null,"max":num\|null,"unit":str\|null} (min/max 중 1개 이상 non-null). group(column_kind=group): {"type":"aggregate","metric":"rms"\|"peak"\|"mean"\|"std","op":"<="\|">=","value":num,"unit":str\|null}. group 제약의 column_name = datalake.columns의 group 행 name (키 정합). 등록 시 type 화이트리스트 검증, 확장은 type 추가로. Page 3 폼은 column_kind로 렌더 분기(scalar=range 폼 / group=aggregate 폼). __dupN 컬럼은 폼에서 원본 헤더명 + 중복 배지로 표기(드롭·은닉 금지). | DL-3 진입 전 shape 미잠금 시 구현 중 즉흥 결정 = 설계잠금 원칙 첫 위반이 됨. |
| D-181 | 백엔드 = 신규 엔드포인트를 /api/dl/* 네임스페이스로 additive 추가, 구 핸들러 무변경·무분기. 프론트 = 신규 Page 2/3을 env 플래그(DL_UI_V2, 기본 off) 뒤 별도 라우트에 마운트, 구 페이지 무변경. DL-5 green 후 구 경로·플래그 제거. | 프론트만 게이트하고 백엔드 핸들러를 공유 분기하는 반쪽 게이트가 회귀의 고전적 원인 — additive 네임스페이스가 PROTOCOL §3 '구 경로 생존'과 구조적으로 정합. |
| D-182 | 게이트 증거 = repo 내 pytest (일회성 터미널 출력 박제). DB 테스트는 throwaway PG(127.0.0.1:55432/dl_test) 전용, ambient PG* env 미사용, 55432 하드 가드(E3 구조화). 개발 반복 쓰기 = throwaway, 라이브 접촉 = 게이트 검증 시점만. DL-3부터 검증 핵심부는 자동화 테스트 동반 필수(제약 머지 3케이스·재승인 게이트). | 정책 선언(근거 본문 내재). |
| D-183 | 복원 드릴(fresh dump → throwaway 복원 → 동등성 검증) 1회 성공 = DL-3 진입 게이트. 이후 모든 재적재·스키마 변경 전 fresh dump 필수, 복원 드릴은 데이터 형상 변경 시(신규 테이블 등) 재실시. | 복원 미검증 백업은 백업이 아님 — constraints는 재생성 불가 데이터의 시작점. |
| D-184 | API 네임스페이스 확정 (D-181 보강) | DL-3 신규 백엔드 엔드포인트 = /api/datalake/* (variable_index·spec-1 §1-3 기정합 — D-181의 /api/dl/* 표기 폐기). D-181 본질 불변: additive, 구 핸들러 무변경·무분기. 프론트 플래그 = import.meta.env.VITE_DL_UI_V2(기본 off), 신규 Page 2/3 별도 라우트 마운트, DL-5 green 후 구 경로·플래그 제거. |
| D-185 | constraint_spec type 화이트리스트 보강 (D-180 보강) | 화이트리스트 = spec §4-4 폼 타입 5종(range/single_value/ratio/list/text) ∪ aggregate(column_kind=group 전용). 근거: D-180 v1(range/aggregate 2종)이 §4-4 constraint_keys 폼 렌더와 충돌 — 폼이 생성하는 값을 저장 계층 화이트리스트가 차단하는 모순 해소. 각 type의 캐노니컬 필드 세부 = DL-3 3c 설계 시 Part 1-2(가)·§4-4 본문과 byte 대조로 확정(즉흥 정의 금지). |

### 정합 확인
- D-167 강화(D-179 감사 추적) · D-161/D-176 group descriptor 정합(D-180 aggregate shape·키잉) · PROTOCOL §3 '구 경로 생존' 정합(D-181 additive 네임스페이스) · D-178 백업 게이트 보강(D-183 복원 드릴).
- 구현 매핑: 자동화 테스트(D-182) = 커밋 ①. catalog MIGRATION_SQL additive + insert_constraint/delete_entry history(D-179) = 커밋 ②. spec-1 §1-5 동기(D-179) = 커밋 ③.
- 라이브 적용: constraints 감사 ALTER 1회(C-2) — count 32/569/0 불변, 타 스키마(agent_logs/lineage/metadata) 미접촉, 멱등 확인.

### DL-2.5 완료 = DL-3 진입 가능
다음: DL-3(constraint_spec shape v1 = D-180 구현 + Page 3 폼 column_kind 렌더 분기 + 제약 머지/재승인 게이트). 진입 게이트(D-183): 복원 드릴 1회 성공 = 충족(2026-06-11). 자동화 테스트 동반 필수(D-182).

## 2026-06-11 — datalake-redesign DL-3a: /api/datalake/* 백엔드 표면 (Master 저작 → CC 적용)

명세: catalog 계층(entries/columns/constraints)을 `/api/datalake/*`로 노출 — additive only(D-181/D-184), 구 핸들러 무변경. register = Mode B 한정. 개발·테스트 전부 throwaway 55432(D-182), 라이브 접촉 0.

| # | 결정 | 사유 |
|---|---|---|
| D-186 | register = Mode B(서버 경로 메타 등록) 한정 — Mode A(파일 업로드)는 이월(데모는 사전 적재 파일 사용, 실시연 여부는 데모 영상 후 속도·성능 보고 재결정). datalake_id = slug(name)([a-z0-9_]), 충돌 시 409(자동 변형 금지 — anti-silent). function_hint는 유저 힌트 입력으로 받아 권위 컬럼 function에 해석·저장(rename 아님, R1 이월 소화). 등록 데이터도 data/lake/<id>/ 귀결 + 동일 catalog 경로(§1-6 불변). spec §4-11의 Mode A 체크 2항목은 이월 표기. | 병갑 확정(2026-06-11). 업로드 전송은 ingest 단건 API화라 DL-3 스코프 초과 — spec 표면과의 차이는 본 결정+체크리스트 이월 표기로 기록해 교차검증 모순 잔재 차단(R1 A/B-잔재 교훈). |
| D-187 | DL-3 API 표면 확장 — GET /api/datalake/{id}/columns · GET·POST /api/datalake/{id}/constraints 3종을 spec §1-3/spec-3 §9-1 표에 additive 행으로 추가. columns = Page 3 폼의 실컬럼 소스(D-90/D-161), constraints GET = prefill 소스, POST = "영속 업데이트" 전용 쓰기 경로(insert_constraint 경유 = D-179 불변식 충족, "이번만"은 세션 저장이라 catalog 미접촉). POST 검증 = D-185 type 화이트리스트 + column_name 실존. | spec 25개 표에 없는 3종이 D-167 prefill/영속 흐름과 D-90 폼 렌더의 필수 전제 — 표면 추가를 결정·표 동기 없이 구현하면 명세↔구현 silent 괴리. |

## 2026-06-12 — datalake-redesign DL-3b: Page 3 v2 셀렉 (Master 발행 → CC 실행)

명세: VITE_DL_UI_V2 플래그 뒤 신규 Page 3 셀렉(카드 UI, catalog 소스), 구 경로 무접촉(D-181/D-184). orphan 가드(3a 룰링 ④ 후속) + SSOT 교차 테스트 동반.

| # | 결정 | 사유 |
|---|---|---|
| D-188 | vid 값 체계 = lines.yaml line_id와 동일 체계 — 실측 확정: line_id 집합 = manifest vid DISTINCT 집합, 부분집합 넘어 **동일 집합(3/3)** {module_1_metal_processing, module_2_forming_joining, module_3_polymer_electronic}. 수치: manifest 전 행 34 = 13+9+12 (excluded 2건 모두 module_1, D-177) → 적재 32 = 11+9+12. 신 Page 3 필터는 session line_id를 vid로 직사용. 교차 정합은 tests/test_ssot_cross.py 상시 박제(D-182) — hint_dataset 34종 dangling 0(excluded 참조 = 알려진 2건 고정), vid 분포 양 기준 모두 assert. | Page 1→3 바인딩 키가 문서상 미보증 — 이중 SSOT 교차 참조의 order_cp949형 사고 재발 차단. |

## 2026-06-13 — datalake-redesign DL-3c: 제약 폼 (Master 발행 → CC 실행, GATE PASS)

명세: 신 Page 3 v2 제약 입력 폼 — 머지 3케이스(세션>prefill>빈칸) + 재승인 게이트(prefill 자동적용 0) + 이번만/메모리 업데이트(영속) 분기 + column_kind 렌더 분기(scalar=range / group=aggregate) + delete + 자동화 테스트 동반(D-182). 라이브 constraints 첫 실쓰기 단계 — fresh dump(D-183) 선행. additive only(엔진·구 jsx 7종·구 핸들러 0접촉).

| # | 결정 | 사유 |
|---|---|---|
| D-189 | constraints shape 신구 호환 = **저장·전달 분리**. catalog 저장 = D-180/D-185 shape(type 판별자). session→엔진 전달 = **range type만** 구 shape `{column_name:[min,max]}`로 다운컨버트(min/max 한쪽 null은 null 그대로 전달 — validator `_bounds` (None,None) skip 거동 활용). 비-range 전 type(aggregate 포함) = 엔진 전달 제외 + 세션 메타 `engine_excluded:[{column_name,type}]` 명시 기록(silent drop 금지). 엔진 파일(planner/validator/main 호출부) diff 0. D-168 알람 접점은 DL-5 전 Master 룰링 예약 — 3c는 메타 기록까지. | planner.py:105·validator.py:113(`_bounds`) 실측 — 구 엔진은 `{col:[min,max]}`만 해석. 임의 변환은 의미 추측 = 즉흥 정의 금지(D-173 계열). D-164 seam 보존. |
| D-190 | canonical 필드 **byte 대조 확정**. 수용 3종: `range`(D-180 — min/max 중 1개 이상 non-null·unit str\|null) / `aggregate`(D-180 — metric∈{rms,peak,mean,std}·op∈{<=,>=}·value num·unit str\|null, column_name=group 컬럼) / `single_value`(`{"type":"single_value","value":num,"unit":str\|null}` — §4-4 NumberInput 실측). `ratio`·`list`·`text` = spec §4-4 placeholder 미정의 → POST 422("canonical 미확정 type") + 폼 구현 시 확정 이월. 허용 외 필드 = 422(anti-silent). | 즉흥 정의 금지(D-185)의 byte 대조가 spec 자체의 미정의를 드러냄 — 무검증 저장 = silent 위험. API 게이트가 화이트리스트(D-185 6종)보다 좁은 건 additive 무모순. **이탈 반영:** PUT v2도 D-185∩D-190 검증 적용(세션도 폼 생성 가능값만). 3a placeholder 테스트(aggregate-on-scalar 200→422) D-190 정합 갱신. |
| D-191 | `delete_constraint` 3c 포함 — "빈칸 영속 업데이트" = delete 경로. `catalog.delete_constraint(datalake_id, column_name, approved_by)` 동일 트랜잭션 history append(action=delete, D-179 불변식), 부재 행 404(silent no-op 금지). POST 빈-spec(None\|{}) = 이 경로 재사용. register 모달 UI(프론트)는 3c 제외 → GATE PASS 후 별도 미니 단계 이월(백엔드 D-186/187 표면 기존 유지). | 빈칸 영속 = 의미상 delete, 누락 시 의미 구멍. 404는 anti-silent 정합. register UI는 분리 가능. |
| D-192 | CC 검증/진단 셸 규율 격상: 모든 파이프라인 셸 `set -o pipefail` 의무 + 도달성·성공 판정은 파이프 종료코드가 아니라 **명시 상태 출력**(HTTP 코드 / row count / grep 매칭)으로. | 3b [STOP]②(테스트 혼입 — 파이프 종료코드 함정)·3c Phase2 진단(`wget\|head`가 항상 0 → 가짜 5173 REACHABLE 오판)에서 동일 함정 2회 재발. 가짜 서버 위장으로 반나절 소모 — 규율 박제 필수. |

## 2026-06-13 — datalake-redesign DL-3.5: columns.ordinal SSOT + dry-run anti-silent 리포트 (Master 발행 → CC 실행, GATE PASS)

명세: A=columns.ordinal(소스 헤더 물리 순서 SSOT, additive) + forward 캡처(replace_columns persist) + backfill(build_record 재사용·name-set fail-loud·멱등) + finalize(NOT NULL+UNIQUE) + get_columns ORDER BY ordinal + spec-1 §1-5 동기. B=ingest dry-run 헤더 anti-silent 리포트(__dupN/__unnamed/상류 .N 출처 분류). additive only(엔진·구경로·datalake_api 0접촉), 라이브=fresh dump(D-183) 선행·2-stop.

| # | 결정 | 사유 |
|---|---|---|
| D-193 | datalake.columns ordinal INT additive 컬럼 = 소스 헤더 물리 순서 SSOT. PK(datalake_id,name) 불변·additive(D-167). forward 캡처 = 공유 헤더 빌드(ingest/register 단일 구현 재사용)가 ordinal=리스트 index 생산 → replace_columns가 persist → ingest execute_load·API register 양 호출자 자동 커버. backfill 후 finalize = SET NOT NULL(미채움 검출) + UNIQUE(datalake_id, ordinal)(중복 차단), 멱등 가드. get_columns ORDER BY name → ordinal. spec-1 §1-5 DDL 동기. | 구 ORDER BY name은 collation 종속 silent 재배열 — 한글 no-op(우연 보존)·ASCII/숫자 활성 재정렬(L1_cnc 10TH<1ST 실증) = anti-silent 위반. ordinal 미저장이 근본 원인. NOT NULL/UNIQUE = 완전성·유일성 fail-loud. 라이브 569 UPDATE: NULL 0·멱등 4회·spot-check 소스순서 확정. |
| D-194 | ordinal backfill 시맨틱 — tools/datalake_ordinal_backfill.py(신규): build_record 재사용으로 헤더 재파싱→정렬 컬럼 리스트, ordinal=enumerate index, (datalake_id,name) 매칭 UPDATE. name-set 불일치 시 sys.exit(3) fail-loud(부분 UPDATE 0). group(waveform)=빌드 산출 순서상 위치(first-member rank, 비연속 group 0 실측). __dupN(ingest 마킹)·.N(상류 pandas)·__unnamed 물리 위치 보존(재정렬·병합 금지). 멱등(2회=동일). 라이브=fresh dump 선행(D-183)·2-stop. | 순서 권위 = 파일 헤더(manifest는 per-column 순서 미보유). ingest 빌드 재사용 = 재구현 발산 방지. name-set fail-loud = 헤더 드리프트 silent 차단. 상류 산물 존중(D-82). |
| D-195 | ingest dry-run anti-silent 리포트 — audit_header_names(): 정확중복→__dupN / 빈헤더→__unnamed(ingest 마킹) vs 상류 pandas .N(X.정수+bare X 동반 판별자) 출처 분류·카운트. .N은 informational(결함 단정·제거·병합 금지 = 상류 보존). write-0. 인터랙티브 차단은 자동화 원칙상 과함→리포트. 실 32셋 __dupN=1·__unnamed=2·.N=5. UI 배지 출처 구분 이연. | __dupN과 상류 .N이 UI 출처 구분 불가 = silent ambiguity. 제거 아닌 표면화가 해. bare-base 동반 판별로 값(0.025)·타임스탬프 false-positive 제거(초안 \.\d+$ 정정). |
| D-196 | DL-4 vid 전파 읽기 지점 = PipelineFull 최상위 `vid`(aggregate() 단일 읽기), catalog.get 라이브 재조회 아님. _build_agent_record·_build_stage_chain 산출물 최상위 `vid` 키 전파(별칭 0). function/site는 vid 종속 아닌 별도 컬럼 경계 유지(record에 function만·site 없음 → vid×function×site 혼동 0). 결정론·LLM 0(D-59), additive(시그니처 vid 인자 치환 외 분기·계산 0), 상류 main.py 0줄. | aggregate()는 동기·순수 dict 변환. catalog.get은 async → 직접 호출 시 async 전염 + main.py 호출부 시그니처 전파 = additive·상류 0줄·결정론 게이트와 자기모순. entries.vid SSOT는 Page-1 라인 선택(D-162)→PipelineFull 경로로 흘러든 동일값이므로 PipelineFull 읽기가 정합. DL-4 프롬프트 "catalog.get(datalake_id).vid" 문구를 읽기 지점 기준으로 정정. 게이트 T1 record/node vid 일치·집합 {L1} 실증. |
| D-197 | vid 런타임 소스 활성화 = 백엔드 session-build에서 pipeline_full에 vid=line_id 적재(D-188 vid=line_id 근거). DL-4(aggregator/eda 전파 배선)의 상류 0줄 경계 밖(main.py 1~2줄)이라 별도 미니 단계 4.1.1로 분리. 현 prod는 session-build가 {line_id,stages}만 생성→vid 미적재→전파값 None(T1b graceful 박제)이 의도된 중간 상태. (b)프론트 직접 송신은 D-188과 중복 비채택, (c)무기한 유지는 prod 전파 무효화 비채택. DL-5 e2e 전 활성화 권장. | DL-4는 파이프(전파) 완성·검증, 입구(소스)는 별도 공사. vid=line_id(D-188)가 SSOT이므로 백엔드 session-build의 line_id→vid 복사가 일관(프론트 재송신 불요). additive·결정론·라이브 쓰기 0. |
| D-198 | 4.1.1 session-build vid 적재(D-197)는 Page-3 /full 핸들러(main.py:415·datalake_api.py:359)의 클라이언트 pipeline_full 통째 교체에 취약 — 클라이언트가 vid 미동반 시 prod가 /full 경로에서 vid None 회귀. session-build 소스 적재만으론 /full을 타는 prod 전 경로 e2e vid 도달 불보장. 해결 = /full 핸들러가 수신 dict에 vid 부재 시 line_id로 보존/재유도(백엔드 SSOT 일관, additive·결정론·LLM 0). frontend 재송신(ⓐ)은 D-188/D-197 "프론트 재송신 비채택"과 모순이라 기각 → ⓑ(백엔드 보존) 채택. 별도 미니단계 4.1.2로 DL-5 e2e 진입 전 필수 선행. | D-197 "session-build SSOT" 전제가 /full overwrite 경로 간과. vid=line_id(D-188) SSOT는 백엔드 일관 유지가 정합 — 클라이언트 vid 권위 위임 = D-188 위반. /full 보존 1지점 = additive seam, compute 불변(D-59). 4.1.1 게이트 ②는 정의 경로(create→structure→aggregate) 충족 PASS, prod 전 경로 완결은 D-198 후속. |
| D-199 | 경계 가드(test_d_boundary_only_mainpy / test_e_boundary) 내구화 = closed-range 핀. 근본결함 = `git diff <baseline> --name-only`가 baseline↔작업트리(한쪽 끝만 고정, `..` 없음) → 각 가드가 후행 단계 변경 누적 흡수(test_d가 4.1.2 datalake_api.py를, test_e가 명명정정 b66291f 리네임을 위반 오판). 수정 = 각 가드를 닫힌 커밋범위 `start..end`(양끝 커밋) diff → 후행 작업·작업트리 편집 면역. test_d→`3343f3a..acc1f4c`(4.1.1 닫힌 범위, allowed는 該범위 historical name `tests/test_vid_source_dl41.py`). test_e→baseline acc1f4c→17f51df 정정(명명정정 2커밋이 acc1f4c↔4.1.2 사이라 acc1f4c는 stale start; 진짜 4.1.2 직전 HEAD=17f51df) + `17f51df..(4.1.2 close 커밋)` 닫음. assert 일체(allowed extra 공집합·forbidden-zone 0접촉·main.py[+datalake_api.py] 포함)는 전부 보존(은퇴 아님), 수정은 range뿐. 검증 내구성: 4.1.3에 future-step 시뮬(가짜 후행 변경→가드 무반응) 필수 포함 — "지금 green" 아닌 "앞으로도 green" 증명(직전 비내구 PASS 재발 차단). 순서 귀결: test_e는 4.1.2 커밋 후에야 닫힘 → 4.1.2 게이트는 functional-green + 경계 2 red를 range-아티팩트로 명시 제외, 4.1.3에서 closed-range 핀으로 green·durable. 커밋 후 untracked dl412 test 추적전환되어 가드 정상 포착. 이후 단계 공통 패턴. | 한쪽 끝 working-tree diff = 단계 N 가드가 N+1 작업을 위반 오판하는 비내구 결함(4.1.1 PASS 후 4.1.2 착수 즉시 red). 닫힌 범위는 역사적 사실이라 영속. 동적 baseline 픽스처(tag 자동산정)=magic silent 실패원(D-192 명시>영리 역행), 프로덕션-only 스코프="정확히 이 파일" 단정 약화 → 둘 다 비채택. baseline 17f51df 정정=측정 약화 아닌 명명정정 커밋이 무효화한 참조점 교정(intent=4.1.2만 측정 보존). 게이트 경계-red 제외=기능회귀 아닌 range 메커닉이라 4.1.2 기능 판정과 분리. |
| D-200 | /full vid 불일치 fail-loud (B2). D-198 absence-preservation(부재→line_id 재유도) 위 elif 1개 additive: 양 핸들러(main.py session_put_full · datalake_api.py dl_session_put_full)에서 derived=pf.line_id or session.line_id, client_vid 존재 & derived 비-None & client_vid≠derived 시 HTTPException(422,"vid mismatch: client '{}' != line '{}'") raise(session["pipeline_full"]=pf 저장 전=모순 미저장). 부재→재유도(D-198 불변)·일치(또는 권위 부재)→존중 no-op. 422=D-190 anti-silent 거부 패턴 일관. 테스트: test_b("존중" 박제)→test_b_full_rejects_vid_mismatch(불일치 422 단정) 교체 + test_b2_full_respects_matching_vid(일치→존중) 신규, test_a/a2/c/d 불변. ★ A+log(클라값 저장+로그·상황별 해결)는 비채택 아닌 production-hardening fallback: 실배포서 정당 mismatch로 hard-stop이 UX 해치면 fail-loud→log+graceful-degrade 단계 다운그레이드. | 정상 플로우(백엔드 박은 vid round-trip)엔 vid==derived→발화 0·UX 무해. mismatch는 edge(버그/stale/조작)뿐 → 저장+로그(A)는 감사 lineage에 모순 잔류(IATF·21CFR 추적무결성 흠), 저장거부(B2)는 원천 차단=anti-silent 정합. pre-production이라 시끄러운 실패가 이득. derived=pf.line_id 우선은 D-198 기존(pf/session line 불일치는 별도 sub-carry, D-200 외). 권위 부재+client_vid=반증불가라 존중(silent 아님). |

┌─ 2026-06-14 — datalake-redesign DL-5a: 엔진 로직-0 불변 가드 (Master 발행 → CC 실행)
│ 명세: 엔진 5종(agents/{inspector,planner,executor,validator,ml})이 R0 baseline
│ (dl-baseline-20260605) 대비 로직 변경 0임을 자동 박제 — DL-5 회귀 게이트 토대.
│ additive(tests/ 신규만), 엔진·구경로·datalake_api 0접촉.
│ | D-201 | 엔진 로직-0 불변 가드 = tests/test_engine_invariance_dl5a.py. 본 단정 =
│   `git diff <R0 deref> -- agents/{inspector,planner,executor,validator,ml}` == 빈 목록
│   (committed+미커밋 드리프트 모두 포착). ★경계 가드(D-199)와 반대 방향: 불변 가드는
│   미래·미커밋 엔진 변경을 잡아야 하므로 한쪽-끝(baseline→worktree)이 정답·닫힌범위 아님.
│   비공허 2중: (a) 대조 단정 = R0 대비 변경 확인된 DL-레이어 파일 diff != 빈 목록(probe 생존),
│   (b) mutation check = 엔진 파일 임시 변경 시 본 단정 RED 실증 후 revert·트리 클린(가드가
│   실제로 문다는 증명). 데이터 seam(datalake.get)·aggregator·EDA는 forbidden-zone 밖
│   (PROTOCOL §3 additive 허용). | 사유: "엔진 변경 0"이 핵심 영업명제 — DL 전체(R0~) 불변을
│   상시 회귀 게이트화. BLUEPRINT §1.5 보존 이음매 = dataset_id→path만 additive, 엔진 내부 0.
│   실측 사전확인 = 엔진 diff vs DL-4(d8500d7) 0. "지금 green" 아닌 "앞으로도 green"(D-199)
│   — mutation check로 비공허 증명. |
└─

  | D-201 보강 (2026-06-14, DL-5a) | test_engine_paths_are_watched 추가 — 엔진 5종 경로가
    각각 추적 파일 ≥1개로 실재함을 git ls-files non-empty 단정. 경로 오타·미래 리네임이 본 단정을
    vacuous-green(미감시를 불변으로 오판)으로 만드는 잔여 벡터 차단. 비공허 실증 = 가짜 경로 임시
    주입 시 RED→revert mutation. | mutation이 inspector 1경로만 RED 실증했던 한계 보완 →
    5/5 경로 감시 확정. "지금 green" 아닌 "앞으로도 green"(D-199) 일관. |

## 2026-06-14 — datalake-redesign DL-5b-seam-2: catalog.get 데이터 seam 배선 + 5a 가드 정제 (Master 발행 → CC 실행, GATE PASS)

  | D-201 재정의 | 엔진 로직-0 가드 = 파일 동결 → compute 동결 + 데이터 seam additive 허용.
    {inspector,planner,validator,ml} R0 byte-동결. executor.py는 R0 대비 diff가 오직 문서화 seam
    additive(data_path 인자+None분기)만 허용, 그 외 RED. 비공허 3중 mutation. ⓒ baseline 이동 비채택. |
    근거: §1.5/§3 "데이터 소스 seam만 additive" 정밀화(약화 아님). |
  | D-203 | catalog.get 데이터 seam. main.py→resolve_dataset_path(id)[catalog.get(PG)→data_path
    dir→실파일 locate→file_path]→executor.execute(...,data_path). executor=+optional data_path=None
    + `path=data_path if data_path is not None else _resolve(...)`. None시 구경로 생존·회귀 0. compute 0.
    inspector/MCP catalog-wiring=phase 2(게이트는 stub). 라이브 env·MCP=명선/병갑 영역. |
    근거: catalog(PG)이 데이터 위치 단일 권위. |

## 2026-06-14 — datalake-redesign DL-5b-e2e: 결정론 전처리 e2e 게이트 + presence 단정 fold (Master 발행 → CC 실행, GATE PASS)

  | D-202 개정 (5b-e2e) | 결정론 e2e 게이트 = 전처리 완주(profile fixture → Planner(LLM stub)
    결정론 plan → execute(data_path 실 KAMP) → validate). 수기=profile fixture(실 29컬럼·flags
    실데이터 충실)뿐, plan은 real Planner 결정론 산출(LLM 순서만→stub시 후보순서 폴백). 완주 단정=
    예외0+산출물(backup/processed parquet·lineage non-empty)+형상(원본 보존·silent drop 0·lineage
    =steps 정합)+결정론 재현(2회 동일). **ML/EDA=게이트 밖** — per-dataset ML 모드는 로컬 LLM
    판단 영역이라 결정론 게이트 고정 부적합(이 셋 무라벨→anomaly 적합하나 fixture 아님). live
    smoke(A)=capstone 이월(Ollama+main.py prod 배선 phase 2 종속). | 사유: 게이트=회귀 보호=
    결정론 전처리 경로. LLM 추론·ML선택은 비결정·LLM도메인→게이트 밖, live/capstone. |

## 2026-06-15 — datalake-redesign DL-5c: DL-5 본체 재정의(프로덕션 seam 배선) (Master 저작 → CC verbatim 적용)

> **D-204** | DL-5 본체 재정의 — "재설계가 실제 작동" = **프로덕션 전 모달리티 seam 배선.** 5a(엔진 로직-0 동결)·5b(seam 부품 `resolver`+`executor` data_path 인자 + e2e 테스트 벤치)는 정의 스코프 달성으로 CLOSE 유효. 단 **프로덕션 배선**(main.py가 `resolve_dataset_path` 호출→`executor.execute(data_path)` + inspector/MCP catalog 경유)은 phase 2로 분리돼 **미이행**. CC 전 체인 실측: 프로덕션 호출부(main.py:222·591)가 data_path 미전달, `resolve_dataset_path` 호출 0 → 전 모달리티가 부재한 `data/synthetic/*` ROOT 읽음(실행 시 not-found). 5b reach/e2e의 "catalog→engine 작동"은 throwaway PG + test call 한정. ENTRY/WORKLOG "5b=재설계 작동 증명"은 부품/테스트 한정 과장(정정 대상). → DL-5 close 본체 = 프로덕션 배선. 단계 분할: **5c-1**(execute 배선, csv 3종 timeseries/order/event-log) · **5c-2**(inspect/MCP 배선, MCP 방식 진입 시 실측·결정) · **5c-3**(image 추후). "8챌린지 회귀"(합성 전제·엔진 동결로 무의미) 게이트 기준 폐기 — 회귀 본질 = "프로덕션이 실 PG lake를 id 기준으로 읽고 전 과정 완주". 합성 미접촉. | 근거: 명선 프레임 "첫 입력부만 치환" 정합 — 치환이 프로덕션 레벨에서 미이행이었음. |

> **D-205** | reparse_header·balance_classes = **ML 학습 관련 미완 기능, 데이터 seam 배선과 무관** → 5c 회귀 대상 제외, 안 건드림. reparse_header = timeseries executor 핸들러 미구현(skip "Sprint 2+"). balance_classes = 전처리 단계(감지→Page4 제안카드→메타 기록)는 작동하나 실 리샘플(SMOTE/class_weight)이 train_engine에서 미소비(model.fit에 class_weight 없음). 둘 다 redesign(데이터층)과 독립 — 향후 ML 학습 단계 구현 시 처리. | 근거: 데이터 흐름 배선과 별개 축. 안 건드린다는 결정을 명문화해 향후 "왜 빠졌나" 재질문 차단(WORKLOG·인계 문서에도 명시). |

## 2026-06-15 — datalake-redesign DL-5c-2: inspect/MCP 프로덕션 seam 배선 (Master 확정 · CC verbatim 적용)

> **D-206** | inspect/MCP 프로덕션 seam 배선 (5c-2). 배선방식 = **(a)변형**: main.py 두 호출부가 `resolve_dataset_path(id)`로 data_path **단일 취득(PG 권위 단일점)** → `run_inspect`·`run_execute` 공통 전달. inspector(inspect + 4 `_mcp_get`)·MCP 3서버 `_resolve`/7종 도구는 **optional data_path 받기만**(PG 비의존 — catalog.get 직접호출 (b)는 PG 권위 분산·테스트 복잡으로 비채택). MCP 7종 계약 시그니처 무파괴(data_path optional additive, CLAUDE §4 보존). **csv 3종만**(timeseries/order/event-log) — image는 resolver(`*.csv` glob)·executor 경로가 csv와 구조 상이(디렉터리/이미지)+5c-1 미배선이라 **5c-3 분리**. 5a 가드: inspector를 byte-동결→**seam 예외 전환**(executor 동형, D-201 재정의 확장) — `agents/inspector/schemas.py`만 동결 유지, `test_inspector_seam_additive_only` 신설(profile/flags 로직 동결·data_path 전파만 허용, 비공허=profile-mutation RED 실증). compute/profile 로직 0접촉이라 "엔진 변경 0"(compute 동결) 유지. **게이트**: MCP HTTP 실기동=live smoke(명선 env 영역), 게이트는 execute_endpoint 실태우기 + `_mcp_get`을 in-process MCP tools 호출로 우회(HTTP 레이어만 우회·데이터 로직 실행). 정합 단정 = inspect profile n_rows == execute backup 행수(동일 실 lake). | 근거: PG 권위 단일(D-164)·계약 보존·명선 "MCP 거쳐 id 쭉쭉" 정합. **carry**: HTTP data_path 직렬화 None→빈문자열 + MCP `_resolve` 빈문자열 처리(csv 무영향=main이 실경로 채움, image·live smoke 전 정리). |

## 2026-06-15 — datalake-redesign DL-5c-3: image 프로덕션 위치 seam 설계 락 (Master 저작 → CC verbatim 적용)

> **D-207** | DL-5c-3 image 프로덕션 위치 seam 배선방식. image = inspection-image modality(7종, ~2.5GB), **단위=디렉터리(파일 아님)**. lake 실구조 5갈래(A flat+동명txt · B subdir+txt · C flat+단일csv · D nested 카테고리 · E class-folder) + L2_auto_console_detect 1종 구조 미실측(빌드 전 디렉터리 단위 1줄 확인). **배선**: ⓐ resolver.py:47(`glob "*.csv"`)는 **csv-only 불변** — image 디렉터리 반환은 main.py `_resolve_seam_path`에 **별도 분기**(modality 인지, catalog data_path 디렉터리 그대로 반환, csv glob **미경유**). 근거 = L2_welding_electrode 라벨 csv 1개가 csv glob에 걸려 데이터로 오인되는 잠복위험 **원천차단** + resolver churn 0. ⓑ executor.py:372 `_execute_image(..., data_path)` additive(execute :202-203 분기 전달, `if data_path else IMAGE_DATA_ROOT` :366, `**/*` recursive :388이라 5갈래 흡수) + **5a 화이트리스트(:123-148) 동시 갱신**(image seam 라인만, 초과·결손 RED). ⓒ MCP image(`mcp-servers/inspection-image/` tools.py:34) `_resolve(dataset_id, data_path=None)` + 7도구 optional(csv 3서버 동형, mcp-servers/는 5a 동결 밖). ⓓ main.py seam에 inspection-image 편입(디렉터리 반환, csv 분기와 별도). **스코프**: 위치만 PG 권위 이관, **라벨 5갈래 해석 미이관**(`_scan` 추론 불변) — D-204 "첫 입력부만 치환" 정합, 라벨 deferred(D-205 패턴, 향후 ML/라벨 단계 재질문 차단). **carry(D-206) 정리**: inspector.py:32 `_mcp_get` data_path None시 **파라미터 미전송**(빈문자열 직렬화 회피) + MCP `_resolve` 미수신=None→구경로. csv 무영향(main이 실경로 채움). **게이트**: image end-to-end inspect→plan→execute→validate(EDA 제외 D-123). 정합 단정 = **n_images(장수) + mode/size 분포**(image엔 n_rows 부재 → csv 정합지표 대체). 비공허 = seam-off(synthetic↔실lake 장수 차) + compute-mutation RED. MCP HTTP 실기동=live smoke=명선 env 영역. **csv 변환 비채택**: image→csv 평탄화는 modality 분리 락(BLUEPRINT §6)·엔진 변경0 위배·공간구조 손실·"어떤 데이터도 전처리" 메시지 약화 → image는 비정형 modality 그대로 유지. | 근거: PG 위치 단일권위(D-164·D-206 연장)·MCP 7종 계약 보존(CLAUDE §4)·D-204 위치배선 본질·modality 분리 락. 명선 "이미지는 별도 라인" 정합. |

D-208 (MCP 라이브 경로 — smoke=b1, 프로덕션 posture deferred)

DL-5 라이브 smoke는 b1(host-run: myeongsun97 user-space에서 MCP 4서버 9101–9104 + backend 18000 자체기동, PG·Ollama는 병갑 컨테이너 TCP 재사용)으로 수행·통과. 근거: 단일 머신(kwonlocalserver)·실 lake 그룹 r-x 읽기 가능(복사 불요)·catalog data_path 32건 전부 상대(읽는 주체 repo-root 종속). b1은 smoke/개발 한정 — CLAUDE §3/§4 "MCP=모달리티 컨테이너" 원칙상 프로덕션 posture 아님. 프로덕션 = b2(컨테이너 + lake bind-mount + catalog 절대경로화)가 원칙 정합이나 본진 추후 결정으로 deferred(b3 inspector 우회는 7종 계약·발표 메시지 손상으로 기각). ★ smoke 통과의 검증 범위 = "host에서 seam이 실 lake 관통"까지(컨테이너 분산배포 정합은 별개, 과장 금지 — D-204 패턴).

D-209 (흐름배선 — 플래그 기반 v2 직행)

Page2 "다음" navigate를 VITE_DL_UI_V2 분기로 전환(on → /pipeline/data-v2, off → /pipeline/data). 플래그 off에서 구 경로 보존 → D-181/184 "구 경로 무변경" 정합. 전환기 v2 자연내비(DL-3 carry) 충족. 변경 = PipelineBuildPage·AlarmBanner 2파일.

D-210 (라이브 배포 부채 — 갱신 시 재기동 규율)

코드 갱신 시 실행 중 서비스(backend·MCP) 재기동 누락이 이번 2층 stale의 근본. "갱신 → 재기동" 규율 + dev 서비스 systemd --user 영속화(MCP·backend, dl-frontend 패턴)를 R-final ①에 편입.

D-211 (Page 3 데이터 잠금 — 깔때기) → D-212로 대체(폐기, Page 2-3 재구성)

3페이지 데이터 카드를 2페이지에서 놓은 dataset_role 하나로 자동 고정(잠금), 후보 목록·function/site 필터 비표시. 사용자 재선택 제거 = "2에서 고른 걸 3에서 또 고르는" 중복 해소. 저장 datalake_id 값/계약 불변(프론트 표시·바인딩만). spec 4-3의 vid×function 후보 피커는 교체. (가) 완전 잠금 채택(변경 버튼 미제공) — 병갑 결정.

D-212 (Page 2-3 흐름 재구성 — 명세 3-2/3-3 원안 복귀)

Page 2 = 4기능 팔레트(데이터 미바인딩, dataset_role 미설정), Page 3 = 회사 선택 후 스테이지별 function으로 데이터 선택. D-211(가, Page 3 잠금) 폐기 — Page 2가 데이터를 안 고르므로 잠글 대상 부재. 백엔드 영향: /structure 무변경(dataset_role 비필수), /datalake/list에 company 1줄, Page 5 무영향, modality 결정론 유지. 병갑 결정.
