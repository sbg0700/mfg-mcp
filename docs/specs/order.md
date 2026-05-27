# 명세: order 모달리티 (4번째 MCP 서버, 포트 8104)

## 핵심: CSV 모달리티 = timeseries 거의 그대로 재사용
order는 CSV 기반이라 timeseries tools.py를 복제하고 ORDER_DATA_ROOT만 교체.
→ "같은 데이터 형태(CSV)면 도구를 거의 그대로 재사용"의 가장 강한 증명.

## order 특유 챌린지
- ★CP949 인코딩 + 한글 헤더 (챌린지1): 인코딩 자동 감지/정규화
- 주문 다변량 → 생산량 예측 (ML 단계 연결점)

## 더미 (KAMP 모사)
- order_demand_cp949.csv: CP949 인코딩, 한글 헤더(제품코드/제품명/주문량...), 1000행

## 검증됨
- [x] CP949 인코딩 감지 (detect_encoding → cp949)
- [x] 한글 컬럼 정상 인식
- [x] Executor 인코딩 흡수 (utf-8-sig→cp949 폴백)
- [x] 7종 도구 = timeseries 100% 동일 (복제)

## 실데이터 교체
ORDER_DATA_ROOT 만 실제 KAMP 경로로.
