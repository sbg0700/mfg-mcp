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
