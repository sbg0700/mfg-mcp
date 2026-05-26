# 명세: Validator 에이전트 (4단)

## 목적
ExecutionResult 검증. 컴플라이언스(lineage 누락) 확인 + 다음 행동 라우팅.

## 검증 규칙
- done 단계에 lineage_id 없으면 → 컴플라이언스 위반 (issues)
- 라우팅: failed→retry_or_human / pending→await_approval / lineage누락→fix_lineage / OK→ready_for_ml

## 검증됨
- [x] lineage 있는 정상 → passed=True, ready_for_ml
- [x] lineage 누락 → passed=False, fix_lineage + issue 메시지

## TODO (Sprint 2)
- ready_for_ml 시 ML 추천 단계로 연결
- 변환 결과 통계적 무결성 검증 (분포 이상 감지)
