# Datalake Redesign — BLUEPRINT (설계 SSOT)

> 이 문서는 datalake-redesign의 **단일 진실 출처(설계)**다. R1 명세 patch는 이 문서를 본진 명세에 적용하는 작업이다.
> 결정의 *근거*까지 담아, 새 챗이 "왜 이렇게"를 다시 묻지 않도록 한다.

---

## 0. 정체성·범위·핵심 메시지
- **무엇:** 데이터 계층(진입·셀렉·자료구조·Page 2/3 연결)만 재작성. 검증 엔진은 변경 0.
- **핵심 메시지:** "어떤 데이터가 와도 AI가 전처리 가능" — **DB catalog 단일 진입점**으로 구조 증명.
- **전제:** 합성데이터 미생성·실 KAMP는 외부폴더 → 마이그레이션할 기존 데이터 없음(클린 출발).

---

## 1. 핵심 아키텍처 결정

### 1.1 A/B 폐기 → DB catalog 단일 진입점
물리 경로 A/B는 **결정 항목이 아니다.** `data_path`가 경로를 추상화하므로 셀렉·엔진은 `datalake_id`만 안다.
물리 경로는 `data/lake/<id>/`로 **귀결**(선택 아님). KAMP·신규 대등 = 핵심 메시지 정합.

### 1.2 정규화 catalog 스키마 (DB / asyncpg)
- **`datalake_entries`** — 타입드 인덱스 컬럼: `datalake_id, source, name, modality, function, site, vid, size_bytes, encoding, format, data_path, reusable_flag, company, registered_at`. (anti-silent-conversion: 런타임 슬롯/폴더 추론 대신 권위 컬럼. `format`=원본 포맷·#11, `company`=멀티테넌트 필터 — D-174.)
- **`datalake_columns`** — per-column `(name, dtype)`. → Page 3가 실 컬럼명으로 폼 렌더 = **D-90 구조적 충족**.
  - **광폭/숫자헤더 데이터(L3 vibration = raw 시간영역 waveform)는 per-column 부적합**(시간오프셋 컬럼 수천). → **컬럼-그룹/행렬 descriptor**(예: `waveform: N개 numeric-header, axis=time_offset_s/fs_hz/window`)로 저장. `column_kind = scalar | group` 구분. (R0 "FFT" 라벨은 헤더 실측으로 waveform 정정 — D-176.)
- **`datalake_constraints`** — per `(datalake_id, column)`. **유저 승인으로만 채움**(시스템/modules.yaml/프로파일 절대 안 채움 = D-43). +approved_by, constraints_history append-only — 모든 쓰기 경로는 동일 트랜잭션 history append 의무 (D-179).
- 비대칭 수용: **catalog=DB / session·lineage=인메모리**(명세상 Sprint 2 postgres).

### 1.3 vid (가상 그룹 ID)
- **공정 흐름(라인) 단위.** Page 1 라인 선택 → vid. (인계서의 `hash(process+module)`에서 라인 단위로 교정.)
- **단일**(1 데이터셋 = 1 흐름). `reusable_flag`로 후속 다대다(reference 공유) 무손실 확장.
- `function`/`site`는 vid **안에서 거르는 별도 컬럼**(vid에 종속 아님).
- 전파 3곳(결정론·LLM-0 = D-59 유지): 스키마 → `_build_agent_record` → `_build_stage_chain`.

### 1.4 modality 결정론 라우터
`datalake.get(id) → {data_path, modality}`. 현 `_resolve`(timeseries/order) + 이미지 경로 + event-log 경로 **3곳을 통합**. LLM 0.

### 1.5 엔진 보존 이음매
데이터→엔진 경계 = `dataset_id → 파일경로` 변환 지점(소수). `datalake.get`으로 추상화. 그 뒤 `pd.read_csv(path) → Inspector~학습`은 **변경 0**. (additive seam.)

---

## 2. UI 모델

### 2.1 Page 2 — 공정 흐름 구성
- 데이터셋 카드 드래그가 아니라, **4 function 모듈(P/Q/M/R)** 을 드래그해 stage에 staging.
- stage = **P 체인(순서)** + **각 P노드의 M/Q 묶음(`attached_to`)**.
  - 기준 스케치: `P1 — P2{+M1} — P3{+Q1} — P4{+Q2,M2,M3}` (M/Q가 특정 P에 부착된 묶음 단위).
- module 스키마: `+ vid`, `+ attached_to`(M/Q→P), `+ chain order`(P). 기존 `(function, dataset_role)` 중복 차단 규칙은 폐기/재정의(같은 function 복수 허용).
- **이중 처리:** MCP 처리 = 파일을 **개별 주체**로 / EDA = **흐름 내 위치 컨텍스트**로.

### 2.2 Page 3 — 메타 기반 셀렉 + 제약
- **셀렉:** `vid × function × site` 메타필터 → **카드 UI** → 제한된 목록에서 셀렉.
- **제약 — 핵심 가드:**
  - 입력 = **무조건 유저** (시스템은 범용 범위조차 제안 0 = D-43). 근거: SI는 고객사 머신별 스펙·limit을 정확히 모름 → 선택권을 유저에게.
  - prefill = `datalake_constraints`(유저 과거 승인값)을 **제안**할 뿐 — **절대 잠금/자동적용 아님**. 흐름/공장/데이터셋 선택이 같아도 **"같은 선택 = 같은 제약" 강제 금지**. 매칭돼도 **항상 재승인 게이트** 통과해야 적용.
  - 키 스코프 = `datalake_id + column`.
  - 머지 = **세션 오버라이드 > 카탈로그 prefill(재승인) > 빈칸(유저 입력)**.
  - 변경 시 = **"이번만" vs "메모리 업데이트(영속)"** 질문.
  - **불변식:** catalog 제약 = *기억 보조(제안)*이지 *권위(디폴트)*가 아니다. (캐시값이 자동으로 굳으면 = 사실상 시스템 디폴트 = D-43 위반.) constraint_spec 캐노니컬 shape = D-180/D-185(type 화이트리스트 = §4-4 5종 ∪ aggregate, group 키잉 = columns group 행 name, __dupN = 원본 헤더명+중복 배지).
- **검증·알람:** 제약 검증 = `validator`가 **원본 backup parquet 직접 대조**(정규화 출력 아님 — 옳음). MCP `/check_constraints`는 죽은 코드(미호출). 알람 = validator 단계의 **"제약 공백/상태 알람"**(데이터-미업로드 알람과 대칭) 신설. 승인 게이트 = Page 3 입력 시점 / 상태 알람 = validator 시점.

### 2.3 EDA flow-context
- 현재 EDA 엔진은 `stage_chain`을 **미소비**(빌드만; 소비처는 Page 5 분석목적뿐).
- → `slim stage_chain`(`node_id + downstream_implication`만; `main_findings`는 `key_findings`와 중복이라 생략)을 `eda_engine.py` payload에 **1키 + system prompt 1줄** 추가. 상류(aggregator/main) 0.
- "작은 엔진 손"(키핑 세트 경미 변경) — 근거: `main.py`가 이미 `ctx`(stage_chain 포함)를 통째 넘기는데 EDA가 안 꺼내 씀.
- 결정론 `compute_chart_data` 무관(D-59 생명선 0). e4b/26b JSON 안정성·8GB 토큰 위해 slim.

---

## 3. 적재 (ingest)
- **`tools/datalake_ingest.py`**(외부 도구): `~/FINAL/1_data` 스캔 → 메타 생성 → `data/lake/<id>/` 복사 + catalog INSERT.
- 메타 출처: `catalogs/datalake_manifest.yaml`(SSOT) 명시값 권위 — `datalake_id`·`vid`(module 기준)·`modality`·`function`·`site`. 휴리스틱(L접두사·module_N·포맷)은 manifest 작성용 seed일 뿐, ingest는 manifest 읽기만(파일시스템 추론 폐기, D-173). per-column 이름·dtype은 파일 헤더 실측.
- KAMP 5.1G — 3 module: **metal / forming_joining / polymer**(=module_1/2/3). `order` modality 1건 실재(function=reference, D-177). cp949 3건 → encoding 기록·utf-8 정규화(D-177). 이종 묶음 2폴더 제외 → 32건(#15-B). `data/lake/`는 외부폴더 → gitignore 무관.
- L3 vibration = raw 시간영역 waveform(컬럼=시간오프셋, 숫자헤더) → 적재도구가 wide/numeric-header 처리(컬럼-그룹 descriptor, §1.2, D-176).
- 멱등 재적재(upsert) + dry-run 먼저.

---

## 4. 원칙
- **이종 매핑 부재 + lineage 흐름 컨텍스트 = 상보.** 이종 데이터를 스키마로 융합하지 않되(개별 주체 유지), vid/stage_chain/lineage로 **흐름·계보 관계**를 부여(+@ 컨텍스트). (lineage 흐름 컨텍스트 강화 = 후속 추가기능.)
- **데이터 비종속(D-82) → 메타 기반 catalog로 진화.** 적재 도구가 메타 자동생성하므로 "파일 넣고 한 번 적재 = 끝"의 비종속성 유지.
- **LLM 제안 · 규칙 결정 · 유저 승인** (D-43, L1/L2/L3 권한 티어).

---

## 5. 본진 명세 매핑 (R1 patch 대상)
| 본진 위치 | 적용 내용 |
|---|---|
| spec-1 §1-2 (자료구조) | DataLakeEntry +vid/site/reusable; PipelineFull module +attached_to/order; AggregatedContext +analysis_groups |
| spec-1 §1-5 (DB 스키마) | 단일 JSONB → 정규화 3테이블(entries/columns/constraints) + 인덱스 |
| spec-1 §1-6 (Data Lake 정책) | 적재 도구·통합 진입점·결정론 modality 라우터 명문화 |
| spec-1 §1-9-1 (시나리오) | A/B 폐기 → DB catalog 단일 진입점 |
| spec-1 Part 3 (Page 2) | 4 function 모듈·P체인·M/Q 묶음 모델 |
| spec-1 §4-3 (Page 3) | vid×function×site 필터·카드 UI·제약 prefill/승인/머지/메모리 가드 |
| blueprint Part 4-2 | datalake.get → data_path 매핑 |
| variable_index | 위 자료구조 항목 갱신 |
| decisions.md | **D-159~** 신규 (스키마/vid/Page2모델/제약가드/라우터/EDA seam/원칙) |

---

## 6. 결정 잠금 목록 (재확인 불요)
DB 채택(정규화) · vid=라인단위·단일 · A/B 폐기 · Page2 P체인+M/Q묶음 · Page3 vid×function×site · 제약=유저입력+prefill제안(잠금금지)+세션>카탈로그>빈칸 · validator 제약알람 · EDA slim stage_chain · modality 라우터 · 이종매핑부재+lineage상보 · 엔진 변경0. **남은 미결 = 없음**(구현 로지스틱스: 포트/DB접근 = R0/DL-1).
