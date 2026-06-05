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
