# 명세: event-log 모달리티 (3번째 MCP 서버, 포트 8103)

## 핵심: 7개 도구 계약 재사용 (timeseries/image와 동일)
로직만 event-log용. dataset_id = CSV 또는 Excel(멀티시트).

## event-log 특유 처리
| 챌린지 | 감지 | 처리 |
|---|---|---|
| 멀티시트 통합 (챌린지8) | read_notes.multi_sheet_merged | LOT_NO 기준 outer merge |
| 클래스 불균형 (챌린지6) | imbalance_suspected (소수<10%) | balance_classes(L2) |
| LOT NaN 메타 (챌린지3) | null_count | fill_missing(L2) |

## 더미 (KAMP 모사, Excel+CSV 혼재)
- press_forming.csv: PASS_YN 2.83% 극심 불균형
- mct_tool_improve.xlsx: 멀티시트 3개(온도/압력/품질), 시트마다 구조 다름
- injection_lot.csv: LOT 첫 행 Step -2/-1 NaN 메타 40행

## 검증됨
- [x] PASS_YN 불균형 감지 (소수비율 0.0283) → balance_classes 제안
- [x] 멀티시트 3개 → LOT_NO 기준 11컬럼 통합
- [x] balance_classes L2 승인 게이트 + lineage
- [x] 7종 도구 = timeseries 100% 동일 계약

## 실데이터 교체
EVENTLOG_DATA_ROOT 만 실제 KAMP 경로로.
