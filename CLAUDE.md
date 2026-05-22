# CLAUDE.md — 설계 헌법 (Project Constitution)

> 이 파일은 Claude Code가 **매 세션 가장 먼저 읽는** 기준 문서입니다.
> 여기 적힌 결정은 **확정 사항**이며, 사용자가 명시적으로 바꾸자고 하기 전까지
> 변경하지 마십시오. 다른 문서(특히 `docs/archive/` 의 인계서)와 충돌하면
> **항상 이 파일이 우선**합니다.

---

## 0. 한 줄 정체성

SI 기업에 판매할, **MCP·Agent·로컬 LLM 기반 제조 데이터 전처리 자동화 시스템**.
차별점: "기존 ETL은 사람이 코드를 짠다 / 우리는 AI가 코드를 짠다."

---

## 1. 절대 규칙 (Hard Rules) — 위반 금지

1. **모델: `gemma4:26b` (메인) / `gemma4:e4b` (스캐폴딩·개발용).**
   - ❌ **31B Dense 금지.** 이 머신은 RTX 3070 = VRAM **8GB**. 31B는 못 돌린다.
   - 모델 이름은 코드에 하드코딩하지 말고 **항상 `OLLAMA_MODEL` 환경변수**에서 읽는다.
     (모델 교체를 한 곳에서만 하기 위함 — `backend/llm.py` 참조)

2. **Agent 프레임워크: 가벼운 수제(homemade) Python 우선.**
   - ❌ **Claude Agent SDK 도입 금지** (로컬 Ollama 호환성 미검증 리스크).
   - ❌ 지금 단계에서 **LangGraph 도입 금지.** 수직 슬라이스가 끝까지 도는 것을
     먼저 확인한 뒤, 에이전트 단계가 복잡해질 때 LangGraph로 이전한다.

3. **외부 API 호출 금지.** Claude/GPT/Gemini API를 절대 호출하지 않는다.
   모든 추론은 로컬 Ollama로만. (SI 고객 "데이터 외부 전송 0" 보장이 핵심)

4. **데이터는 외부로 나가지 않는다.** 외부로 노출되는 것은 웹 대시보드(HTTP/HTTPS)뿐.
   LLM ↔ MCP ↔ DB는 모두 도커 내부망 통신.

5. **코드는 호스트 파일시스템에 둔다. 도커는 실행 환경만 제공한다.**
   컨테이너는 이 레포 폴더를 **볼륨 마운트**해서 실행한다. 코드를 이미지 안에 굽지 않는다.
   (개발 중 코드 수정이 즉시 반영되도록)

---

## 2. 현재 스코프 (수직 슬라이스 = 3주 MVP 1단계)

**목표:** 아래 한 줄이 `docker compose up` 으로 떠서, 브라우저에서 결과가 보이는 것.

```
Ollama(gemma4:e4b) → MCP timeseries 서버(1개) → Inspector 에이전트 → FastAPI → 더미 대시보드
```

### 지금 "진짜로" 동작해야 하는 것
- `data/synthetic/generate.py` — 8가지 챌린지를 의도적으로 심은 더미 데이터 생성
- `mcp-servers/timeseries/` — MCP 표준 도구 7종 (아래 §4)
- `agents/inspector/` — MCP 도구로 프로파일 수집 + LLM이 해석/판단
- `backend/` — FastAPI 오케스트레이션 + 대시보드 서빙
- `frontend/index.html` — Inspector 결과 표시
- `db/init.sql` — schema 3개 (metadata / lineage / agent_logs)

### 지금은 "골격만" (TODO 주석으로 비워둠)
- `agents/planner|executor|validator/` — 인터페이스만, 구현은 Sprint 2
- `mcp-servers/inspection-image|event-log|order/` — README placeholder만
- `harness/` — lineage·guardrails는 가벼운 실동작, context는 stub

### 지금 만들지 말 것 (Sprint 2~3로 연기)
- tRPC + Express 백엔드 (지금은 FastAPI 하나로 충분)
- React Flow 드래그&드롭 캔버스
- DB schema 6개 전부 (지금 3개만)
- MinIO (지금 로컬 Parquet 파일)
- MCP 서버 4개를 각각 독립 컨테이너로 (지금 1개만)

---

## 3. 모달리티 분할 원칙 (변경 금지)

MCP 서버는 **공정이 아니라 데이터 패턴(모달리티)** 단위로 쪼갠다.

```
manufacturing/
  ├─ timeseries        설비 시계열 (압력·전류·온도·진동)   ← 지금 구현
  ├─ inspection-image  검사 이미지 (결함 분류·검출)        ← Sprint 2
  ├─ event-log         LOT 이벤트 (양·불 판정)             ← Sprint 2
  └─ order             주문·생산량                          ← Sprint 2
```

→ 도장에서 만든 MCP가 주조·MCT에 그대로 재사용된다. 새 공정 추가 시 MCP는 안 늘어난다.
이것이 핵심 영업 메시지이므로 흔들지 않는다.

---

## 4. MCP 표준 도구 인터페이스 (7종, 모든 MCP 서버 공통)

인계서 S13에서 채택. 모든 모달리티 서버가 이 7개를 동일 시그니처로 제공한다.

| 도구 | 시그니처 | 권한 | 설명 |
|---|---|---|---|
| `list_columns` | `(dataset_id) -> 컬럼명·타입·통계` | L1 | 메타 조회 |
| `get_schema` | `(dataset_id) -> JSON Schema` | L1 | 스키마 추출 |
| `sample` | `(dataset_id, n=5) -> 샘플 행` | L1 | 요약 샘플 |
| `detect_encoding` | `(file_path) -> 'utf-8'|'cp949'|...` | L1 | 인코딩 감지 |
| `check_constraints` | `(dataset_id, constraints) -> 위반 리스트` | L1 | 제약 검증 |
| `apply_preprocessing` | `(dataset_id, operations, permission_level) -> 결과` | L1/L2/L3 | 전처리 실행 |
| `lineage` | `(dataset_id) -> 변환 체인` | L1 | 계보 조회 |

> 프로토타입에서는 위 도구를 **HTTP 엔드포인트(FastAPI)** 로 구현한다(수제 우선).
> 이것은 "진짜 MCP 프로토콜"의 stand-in이며, **계약(7개 시그니처)이 동일하므로**
> 나중에 실제 MCP 프로토콜로 무손실 교체 가능하다. 계약을 깨지 마라.

---

## 5. 3-tier 권한 모델 (가드레일)

| 등급 | 작업 | 자율성 | 가드레일 |
|---|---|---|---|
| L1 자동 | 메타·스키마·인코딩 감지, 기초 통계 | 즉시 실행 | 입출력 검증만 |
| L2 제안+승인 | 결측·이상치·피처 생성 | 1-click 승인 | 미리보기 + 되돌리기 |
| L3 차단+백업 | 컬럼 삭제·라벨 재정의 | 명시 승인 + 백업 | 자동 백업 + Lineage 강제 |

→ 모든 변환은 `schema:lineage` 에 기록을 강제한다.

---

## 6. 기술 스택 (확정)

- Python 3.11+ / FastAPI / pydantic / pandas / pyarrow
- PostgreSQL 16 + pgvector
- Ollama (추론 엔진)
- Docker Compose (오케스트레이션, 볼륨 마운트 방식)
- 프론트: 지금은 단일 `index.html` (Sprint 2에 React 도입)

---

## 7. 구버전 경고

`docs/archive/` 안의 인계서(`handover_system_architecture.txt`,
`data_summary.txt`)는 **2026-05-21 작성된 구버전 참고자료**다.
유용한 데이터 정보는 많지만, 아래 항목은 **이미 폐기된 결정**이므로 따르지 마라:

- ❌ S2 "Gemma 4 31B Dense" → ✅ 26B MoE / E4B (VRAM 8GB 제약)
- ❌ S2 "31B Q4 ~16GB" → 사실 오류. 실제 ~20GB
- ❌ S10/P5 "Claude Agent SDK" → ✅ 수제 Python → 이후 LangGraph

데이터셋 정보(34개 데이터셋, 8가지 챌린지, 모달리티 라우팅)는 **유효**하므로 참고해도 좋다.

---

## 8. 작업 방식

- 설계 결정은 **별도 설계 대화(Claude.ai)** 에서 내려져 이 파일과 `docs/decisions.md` 에 기록된다.
- Claude Code는 이 헌법과 `docs/specs/` 의 명세를 **따르기만** 한다.
- 새로운 큰 결정이 필요하면 임의로 정하지 말고 **사용자에게 설계 대화로 가져가라고 안내**한다.
