# 명세: inspection-image 모달리티 (2번째 MCP 서버)

## 핵심 원리: 7개 도구 계약 재사용
timeseries와 ★동일한 7개 도구 이름·입출력 계약★. 로직만 이미지용:
| 도구 | timeseries | inspection-image |
|---|---|---|
| list_columns | CSV 컬럼·dtype | 이미지 속성(width/height/mode/format/label) 분포 |
| detect_encoding | cp949/utf-8 | PNG/JPG + RGB/L/RGBA 모드 |
| sample | 앞 N행 | 이미지 N장 속성 |
| apply_preprocessing | 마스킹 정제 | 모드통일·리사이즈 (권한 게이트 동일) |

## 데이터 단위
- dataset_id = 이미지 폴더 (timeseries는 CSV 파일)
- "컬럼" = 이미지 속성 / "행" = 이미지 파일
- 라벨 = 하위 폴더명 또는 .txt 동명 페어

## 감지하는 챌린지
- 해상도 혼재 (width/height mixed_dtype_suspected)
- 컬러모드 혼재 (RGB/L/RGBA)
- 폴더명=라벨, .txt 페어 라벨

## 실데이터 교체
IMAGE_DATA_ROOT 환경변수만 실제 KAMP 경로로. 더미가 실구조 모사라 무손실.

## 검증됨
- [x] wafer_defect 해상도 혼재 감지 (width {357,296})
- [x] 6클래스 라벨 인식, .txt 페어 감지
- [x] 같은 Planner/Executor 흐름 + 권한 게이트 + lineage 동작
- [x] 7종 도구 = timeseries와 100% 동일 계약
