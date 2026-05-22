# 명세: Inspector 에이전트

## 목적
raw 데이터를 받아 DataProfile을 생성한다. 4단 파이프라인의 1단. 권한 L1(자동).

## 설계 원칙
- **결정론적 프로파일링은 MCP 도구가** 한다 (list_columns/get_schema/sample/detect_encoding).
- **LLM(Gemma)은 해석만** 한다: 모달리티 추정, 의심점, 다음 단계 제안.
- 큰 데이터를 LLM에 직접 넣지 않는다 (Harness §컨텍스트관리). 요약·샘플만.
- → 작은 모델(E4B)로도 안정 동작하도록 LLM 부담 최소화.

## 입출력
- 입력: `dataset_id: str`
- 출력: `DataProfile` (agents/inspector/schemas.py)

## 동작 순서
1. MCP `/list_columns`, `/get_schema`, `/sample`, `/detect_encoding` 호출
2. 결정론적 flags 계산 (cp949 인코딩 / headerless / mixed dtype)
3. 요약을 LLM에 전달 → `{modality_guess, concerns, recommended_next_steps}` JSON
4. 합쳐서 DataProfile 반환

## 검증 기준 (수직 슬라이스 완료 = 이게 되면 됨)
- [ ] `order_cp949` 인스펙트 시 flags에 "non-utf8 encoding" 잡힘
- [ ] `mold_anomaly_headerless` 인스펙트 시 "headerless" 잡힘
- [ ] `cnc_lathe_masked` 인스펙트 시 해당 컬럼 mixed_dtype_suspected=true
- [ ] LLM이 modality_guess="timeseries" 반환 (e4b/26b 모두)
- [ ] 대시보드(localhost:8000)에 위 결과가 표시됨

## TODO (Sprint 2)
- agent_logs.decisions 테이블에 의사결정 기록
- Planner로 DataProfile 전달 (A2A 메시지 패싱)
