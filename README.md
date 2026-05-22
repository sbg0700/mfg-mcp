# manufacturing-mcp

SI 기업용 **MCP·Agent·로컬 LLM 기반 제조 데이터 전처리 자동화 시스템**.
> "기존 ETL은 사람이 코드를 짠다 / 우리는 AI가 코드를 짠다."

현재 단계: **수직 슬라이스 (3주 MVP 1단계)** — timeseries 모달리티 1개가 끝까지 관통.

```
Ollama(gemma4) → MCP timeseries → Inspector 에이전트 → FastAPI → 더미 대시보드
```

## 빠른 시작 (리눅스 호스트에서)

전제: NVIDIA Container Toolkit 설치됨 + `docker run --gpus all` 동작 확인 완료.

```bash
# 0) 더미 데이터 생성 (최초 1회 — git에 미포함, 생성물)
python3 data/synthetic/generate.py

# 1) 모델 선택 (.env)
cp .env.example .env       # 기본 gemma4:e4b (배관 검증용)

# 2) 컨테이너 기동
docker compose up -d --build

# 3) Ollama에 모델 받기 (최초 1회)
docker exec -it mfg-ollama ollama pull gemma4:e4b
#  에이전트 검증 단계에서: ollama pull gemma4:26b  + .env의 OLLAMA_MODEL 교체

# 4) 확인
#    대시보드:  http://localhost:8000
#    헬스체크:  curl http://localhost:8000/api/health
```

## 구조

| 경로 | 역할 | 상태 |
|---|---|---|
| `CLAUDE.md` | 설계 헌법 (Claude Code가 따를 기준) | ★필독 |
| `data/synthetic/` | 8가지 챌린지 심은 더미 생성기 | 동작 |
| `mcp-servers/timeseries/` | MCP 표준 도구 7종 | 동작 |
| `agents/inspector/` | 프로파일 수집 + LLM 해석 | 동작 |
| `agents/{planner,executor,validator}/` | 2~4단 | 골격 (Sprint 2) |
| `harness/` | 스키마검증·컨텍스트·가드레일·Lineage | 경량 동작 |
| `backend/` | FastAPI 오케스트레이션 | 동작 |
| `frontend/index.html` | 더미 대시보드 | 동작 |
| `mcp-servers/{image,event-log,order}/` | 나머지 모달리티 | placeholder (Sprint 2) |
| `docs/archive/` | 구버전 인계서 | ⚠️ 따르지 말 것 |

## 작업 분담
- **설계 결정**: Claude.ai 설계 대화 → `CLAUDE.md` + `docs/decisions.md` 기록
- **구현·실행·디버깅**: Claude Code (이 헌법과 `docs/specs/` 명세를 따름)
