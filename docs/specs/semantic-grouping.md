# 명세: 공정 의미 기반 컬럼 그룹화 (우려 1)

## 문제
같은 timeseries 안에서도 INJECTION VELOCITY 1~10은 "사출 시퀀스" 도메인 의미를 가짐.
독립 정규화하면 1→10 시퀀스 추세 소실. → 의미 그룹으로 묶어 처리해야 함.
(모달리티=외형, 의미그룹=도메인, 두 차원 직교)

## 해결 (규칙 우선, 헌법 일관)
mcp-servers/<modality>/semantic.py에 컬럼명 패턴 테이블.
- 규칙(정규식)이 먼저 분류 — 거의 다 여기서 해결
- 미매칭만 unknown → Inspector가 LLM 보조 질의

## 그룹별 전략
| strategy | 대상 | 처리 |
|---|---|---|
| passthrough | 메타(LOT/Time/EQP) | 정규화 안 함 |
| sequence_preserve | 사출 시퀀스 | 그룹 공통 mean/std (추세 보존) |
| profile_group | 보압 프로파일 | 그룹 공통 (형상 보존) |
| single_zscore | 단독 측정값 | 컬럼 독립 |
| label | 판정 컬럼 | 클래스 처리 |

## 흐름
list_columns(semantic_group 부여) → Inspector(profile에 실음) →
Planner(그룹당 normalize_group 1작업, 중복방지) → Executor(_normalize_group 전략별 실행)

## 검증됨
- [x] cnc_machine_injection 35컬럼 → 6그룹 정확 분류 (unknown 0)
- [x] 사출 시퀀스 10컬럼 → 1작업 (중복 방지)
- [x] 그룹 공통 정규화로 시퀀스 추세 보존 실행
- [x] 기존 데이터셋 회귀 없음
