# 명세: Validator (4단, 검증 강화)

## 역할
Executor 결과를 사후 검증. "LLM은 제안, 규칙이 결정"의 후반부 — 결과를 결정론적으로 검증.

## 4종 검증
| 검증 | 무엇을 | 심각도 예시 |
|---|---|---|
| 컴플라이언스 | done 단계에 lineage 있나 | 누락=high |
| 변환 결과 | fill_missing 후 결측 줄었나, normalize 됐나 | 실패=high |
| 계획 무결성 | 중복 작업(width/height 중복), 그룹 이중처리 | 중복=medium |
| 회귀 | 행 급감 등 데이터 손상 | 50%+ 손실=high |

## 입력/출력
- 입력: ExecutionResult + (선택) PreprocessingPlan + DataProfile
- 출력: {passed, checks(4종), issues[], next_action}

## 라우팅 (next_action)
- ready_for_ml: 통과 → ML 단계로
- review_recommended: 경미한 이슈
- await_approval: 승인 대기
- retry_or_human: 실패/심각 → 재시도·사람개입

## 검증됨
- [x] 4종 검증 동작 (정상 데이터 통과 + 결함 데이터 4종 다 잡음)
- [x] width/height 중복 감지 (계획 무결성)
- [x] /api/execute에 연결, 대시보드 VALIDATION RESULT 표시
