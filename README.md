# manufacturing-mcp

**GYEOL** — Generative Yield Engine for On-prem LLM

SI 기업용 **MCP·Agent·로컬 LLM 기반 제조 데이터 전처리 자동화 시스템**.

> "기존 ETL은 사람이 코드를 짠다 / 우리는 AI가 코드를 짠다."

로컬 LLM(gemma4)이 데이터를 검사·계획하고, 결정론 엔진이 변환·검증하며, 사람이 승인 게이트에서 결정합니다. 모든 전처리·분석·학습은 lineage로 추적되어 **IATF 16949 / 21 CFR Part 11** 감사 요건에 대응합니다.

## 현재 상태

4개 모달리티(시계열·검사이미지·이벤트로그·주문)를 **카탈로그 기반 데이터 레이크**로 연결한 **6단계 엔드투엔드 파이프라인**. 기본 실행은 합성 더미 데이터로 동작하며, 실데이터 레이크는 카탈로그(`datalake.entries`)를 통해 별도 연결됩니다.

```
Ollama(gemma4) → MCP(4 모달리티) → Inspector → Planner → [사람 승인] → Executor → Validator → Aggregator → EDA · ML
```

- 검사·계획·차트/모델 추천: 로컬 LLM
- 변환·검증·학습: 결정론 (LLM 0 — 재현·감사 가능)
- 승인 게이트: 사람이 L2/L3 작업 승인
- 전처리·분석·학습 전 단계 lineage 기록
- 데이터 레이크: 카탈로그(`datalake.entries`)가 datalake_id → data_path를 매핑, anti-silent-drop 원칙으로 원본 보존

## 주요 기능

- **이상치 제거(remove_outlier)**: 제약 기반, 사람 승인 후 제거 + lineage + 전후 CSV (원본 레이크 무접촉)
- **EDA**: 자동 차트 추천 + 자연어 분석 요청(LLM 코드 생성 → 승인 → 샌드박스 실행)
- **모델링**: sklearn/xgboost 학습, 피처 중요도, 결과 추적
- **추적성**: 세션별 누적 lineage 뷰(작업·제거 행수·승인·시각)

## 빠른 시작 (리눅스 호스트)

전제: NVIDIA Container Toolkit + `docker run --gpus all` 동작 확인.

```bash
# 0) 더미 데이터 생성 (최초 1회 — git 미포함 생성물; 실데이터 레이크는 카탈로그로 별도 연결)
python3 data/synthetic/generate.py

# 1) 모델 선택 (.env)
cp .env.example .env       # 기본 gemma4:e4b

# 2) 백엔드 스택 기동 (ollama · postgres · MCP 4종 · backend) — 프런트는 미포함
docker compose up -d --build

# 3) Ollama 모델 받기 (최초 1회)
docker exec -it mfg-ollama ollama pull gemma4:e4b
#   필요 시: ollama pull gemma4:26b + .env의 OLLAMA_MODEL 교체

# 4) 프론트엔드 (compose 외 — 별도 기동, 기본 5173)
cd frontend && npm install && npm run dev
#   데이터 레이크 재설계 UI 사용 시: VITE_DL_UI_V2=true npm run dev

# 5) 확인
#    백엔드 헬스체크:  curl http://localhost:8000/api/health
#    프론트엔드:       http://localhost:5173
```

> 모델별 추론 특성은 제한 스펙(RTX 3070 8GB)에서 측정·검증되었습니다 (`scripts/` 측정 코드·자료). e4b는 VRAM 내 완전 적재로 실용적이며, 26b는 24GB+ GPU를 전제로 합니다.

## 구조

| 경로 | 역할 | 상태 |
|---|---|---|
| `CLAUDE.md` | 설계 헌법 (Claude Code 기준) | ★필독 |
| `docs/decisions.md` | 설계 결정 기록 (D-번호) | SSOT |
| `mcp-servers/{timeseries,inspection-image,event-log,order}/` | 모달리티별 MCP 도구 7종 | 동작 |
| `agents/inspector/` | 프로파일 수집 + LLM 해석 | 동작 |
| `agents/planner/` | 작업 후보(규칙) + 순서(LLM) | 동작 |
| `agents/executor/` | 결정론 변환 (LLM 0) | 동작 |
| `agents/validator/` | 사전·사후 검증 (LLM 0) | 동작 |
| `agents/aggregator/` | 단계 컨텍스트 종합 | 동작 |
| `agents/eda/` | 차트 추천·요약·자연어 코드 생성 | 동작 |
| `agents/ml/` | 모델 추천·학습 | 동작 |
| `harness/` | lineage·가드레일·스키마검증·컨텍스트 | 경량 동작 |
| `backend/` | FastAPI 오케스트레이션 + 엔드포인트 | 동작 |
| `backend/catalog.py`, `backend/datalake_api.py` | 데이터 레이크 카탈로그 계층·API | 동작 |
| `frontend/` | React 6단계 파이프라인 (Vite, compose 외) | 동작 |
| `frontend/src/step3_dl_v2/` | 데이터 레이크 재설계 UI (`/pipeline/data-v2`, `VITE_DL_UI_V2`) | 동작 |
| `catalogs/` | 라인·모듈·typical_ranges·추천 모델 풀·`datalake_manifest.yaml` | 동작 |
| `data/synthetic/` | 8가지 챌린지 더미 생성기 | 동작 |
| `tools/` | 전후 CSV 내보내기·레이크 적재(ingest)·백업 유틸 | 동작 |
| `tests/` | pytest 스위트 (DL e2e 등) | 동작 |
| `scripts/` | 측정·발표 자료 (제한 스펙 LLM 벤치마크) | 동작 |
| `docs/archive/` | 구버전 인계서 | ⚠️ 따르지 말 것 |

## 파이프라인 6단계 (프론트엔드)

| 페이지 | 라우트 | 역할 |
|---|---|---|
| 1 | `/` | 라인(공정 흐름) 선택 |
| 2 | `/pipeline/build` | 파이프라인 구조 구성 (Stage별 function·역할) |
| 3 | `/pipeline/data` · `/pipeline/data-v2` | 데이터 선택 + 제약 입력 (구버전 / 레이크 재설계 공존, `VITE_DL_UI_V2`로 분기) |
| 4 | `/pipeline/run` | 실행·표준화 (승인 게이트) |
| 5 | `/pipeline/analyze` | EDA |
| 6 | `/pipeline/model` | 모델링 |

## 작업 분담 (거버넌스)

- **설계 결정 / 게이트 판정 / 문서**: Claude.ai (Master) → `CLAUDE.md` + `docs/decisions.md`
- **구현·실행·검증**: Claude Code (이 헌법과 `docs/specs/` 명세를 따름)
- **push·tag·라이브 쓰기·환경 설정**: 인간 권한자
