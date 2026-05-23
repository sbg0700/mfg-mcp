# 명세: Planner 에이전트

## 목적
DataProfile(Inspector 출력)을 받아 PreprocessingPlan을 생성한다. 4단 중 2단. 권한: 계획만(실행 없음).

## 핵심 설계 결정 (3가지)
1. **출력은 '계획'이지 '실행'이 아니다.** 데이터를 절대 건드리지 않는다. 실행은 Executor.
2. **각 단계에 권한 등급(L1/L2/L3)을 박는다.** harness/guardrails.py의 OPERATION_PERMISSION이
   단일 소스. LLM은 권한을 바꿀 수 없다.
3. **LLM은 '제안', 규칙은 '검증/보정'.** Inspector flags 기반으로 후보 작업을 결정론적으로
   추리고(_candidate_operations), LLM은 순서·이유만 정한다. 후보가 '진실의 원천'이라
   LLM이 작업을 빠뜨리거나 지어내도 실제 단계는 항상 후보에서 나온다.

## 입출력
- 입력: DataProfile (dict) + constraints (dict, optional)
- 출력: PreprocessingPlan (agents/planner/schemas.py)
  - steps: [{order, operation, target_column, permission_level, rationale, params}]
  - requires_approval: L2/L3 하나라도 있으면 True

## 작업 → 권한 매핑 (guardrails와 동기화 필수)
| 작업 | 권한 | 트리거 |
|---|---|---|
| detect_encoding | L1 | non-utf8 flag |
| reparse_header | L1 | headerless flag |
| compute_stats | L1 | 항상 |
| clean_masking | L2 | mixed_dtype_suspected |
| fill_missing | L2 | null_count > 0 |
| balance_classes | L2 | (Sprint2: 불균형 감지 연동) |
| drop_column / relabel | L3 | (Sprint2) |

## 검증 기준 (완료 = 이게 되면 됨)
- [x] cnc_lathe_masked → clean_masking(L2) + fill_missing(L2) + compute_stats(L1) 생성
- [x] requires_approval=True (L2 포함 시)
- [x] LLM 실패해도 규칙 폴백으로 동일 단계 생성
- [x] LLM이 가짜 작업 주입해도 차단 (후보에 없으면 무시)
- [ ] 26B로 INSPECT+PLAN 시 순서가 합리적 (인코딩/헤더 먼저 → 정리 → 통계) ← 모델 받은 후 확인

## TODO (Sprint 2)
- balance_classes를 Inspector 불균형 감지(PASS_YN 2.85%)와 연동
- Executor로 PreprocessingPlan 전달 (A2A 3단 연결)
- agent_logs.decisions에 계획 기록
