# 명세: Executor 에이전트

## 목적
PreprocessingPlan의 각 단계를 실제로 실행한다. 4단 중 3단. 데이터를 진짜로 변환.

## 핵심 설계 결정 (4가지)
1. **실제로 데이터를 변환한다.** Inspector/Planner는 보기만 했지만 Executor는 CSV를 읽어
   정제하고 결과를 저장(parquet)한다.
2. **권한 게이트가 핵심.** L1 즉시 실행 / L2·L3는 approval_token 없으면 awaiting_approval로 멈춤.
3. **모든 변환을 lineage 기록 + 변환 전 백업** → 되돌리기(rollback) 가능. SI 컴플라이언스.
4. **변환 로직은 결정론적 Python (LLM 아님).** LLM은 Planner에서 '무엇을' 정했고,
   Executor는 '안전하게 실행'만.

## 입출력
- 입력: PreprocessingPlan (dict) + approval_tokens ({step_order: token})
- 출력: ExecutionResult (agents/executor/executor_schemas.py)
  - results: [{order, operation, status, detail, lineage_id, before/after_stats}]
  - pending_approvals: 승인 대기 step order
  - output_path: 정제 결과 저장 위치

## 구현된 변환 (수직 슬라이스)
| 작업 | 권한 | 동작 |
|---|---|---|
| clean_masking | L2 | 마스킹 문자(*,**,***) → NaN → 수치화 |
| fill_missing | L2 | 수치=중앙값, 그외=최빈값 |
| balance_classes | L2 | 클래스 비율 분석 + 전략 제안 (리샘플링은 ML단계) |
| compute_stats | L1 | 기초 통계 (변환 없음) |

## 검증 기준 (완료 = 이게 되면 됨)
- [x] 승인 토큰 없으면 L2가 awaiting_approval로 멈춤
- [x] 승인 토큰 있으면 L2 실행됨 (clean_masking: str→float64, 마스킹 240개→NaN)
- [x] 모든 실행 단계에 lineage_id 기록
- [x] 변환 전 원본 백업 (rollback 근거)
- [x] schemas 이름 충돌 해결 (planner_schemas/executor_schemas로 고유화)

## TODO (Sprint 2)
- rollback 실제 실행 엔드포인트 (백업 parquet → 복원)
- balance_classes를 ML 단계의 실제 리샘플링과 연결
- lineage를 PostgreSQL schema:lineage로 (현재 인메모리)

## ⚠️ 교훈 (버그 기록)
agents/planner/schemas.py 와 agents/executor/schemas.py 가 둘 다 'schemas'라
sys.path에 동시 등재 시 import 충돌. → 파일명을 planner_schemas/executor_schemas로 고유화.
각 에이전트 모듈 이름은 전역에서 고유해야 함.
