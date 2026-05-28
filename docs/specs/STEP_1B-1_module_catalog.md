# STEP 1B-1 구현 명세서 — Module Catalog 기반 (Claude Code 인계용)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정했고, 이 문서대로 본진(`~/FINAL/manufacturing-mcp/`)에서 구현한다.
> **작성**: 2026-05-28. STEP 1A(오류수정)·STEP 1(Validator 4종+의미그룹) 완료 직후.

---

## 0. 시작 전 필독 (컨텍스트 로딩)

구현 전 반드시 다음을 순서대로 읽어 맥락을 흡수한다. 이 문서만 보고 구현하지 말 것.

1. `CLAUDE.md` — 설계 헌법 (절대 규칙). 다른 모든 것에 우선.
2. `docs/decisions.md` — 결정 이력 D-01~D-42. 특히 D-32~D-42 (의미그룹·Validator·step_key).
3. `0_project_blueprint_v5.md` Part 2(6페이지 비전), Part 4-3(Planner 확장), 부록 A(카탈로그 초안).
4. `0_variable_index_v5.md` §3(Line), §4(Node 18종), §6(OPERATION_PERMISSION), §11(카탈로그 파일).

### 절대 어기면 안 되는 원칙 (헌법 요약)
- **"LLM은 제안, 규칙이 결정"**. LLM은 해석·순서·이유만. 작업 선택·변환·검증은 결정론.
- **외부 API 호출 절대 금지** (Claude/GPT/Gemini). 로컬 Ollama만.
- **모달리티 5번째 추가 금지** (timeseries/inspection-image/event-log/order 4종 고정).
- **OPERATION_PERMISSION 12종 외 새 작업을 LLM이 생성 불가** (가드레일이 차단).
- **`★`(별표) 마크업 사용 금지**. 강조는 굵게(`**`) 또는 인용(`>`).

---

## 1. STEP 1B-1 범위 (이번 작업)

STEP 1B 전체는 3개로 분할했고, 이번은 그중 **1B-1 (카탈로그 기반)**이다.

```
STEP 1B-1 (이번)  카탈로그 + Planner constraints 활성화 + Validator constraint 검증
STEP 1B-2 (다음)  /api/execute_pipeline (Resumable Orchestrator) + Context Aggregator
STEP 1B-3 (이후)  Mini UI 6 페이지
```

**1B-1에서 만드는 것 4가지:**
1. `catalogs/lines.yaml` — 3 Line × Node × Module 구조 (부록 A 기반)
2. `catalogs/modules.yaml` — Node별 도메인 지식 (**constraint_keys 구조만, typical_ranges 값 금지**)
3. Planner 프롬프트 확장 — `module_context` + `constraints` 활성화 (시그니처는 이미 있음, 내용이 비어있음)
4. Validator에 5번째 검증 "constraint 위반 검증" 추가 (**사용자 입력 constraints 기준, 카탈로그 디폴트 아님**)

**UI는 이번 범위 아님.** `/api/lines` 엔드포인트(카탈로그 조회)까지만 백엔드로 만들고, 화면은 STEP 1B-3.

---

## 2. ★핵심 설계 결정★ — typical_ranges 금지, constraint_keys만

이게 이번 작업에서 가장 중요한 제약이다. **절대 혼동하지 말 것.**

### 하지 말 것 (잘못된 방향)
```yaml
# ❌ 절대 이렇게 하지 말 것 — 정상 범위 "값"을 카탈로그에 디폴트로 박기
injection_molding:
  typical_ranges:
    injection_velocity: [40, 70]   # ❌ 공장마다 다름. 디폴트로 박으면 위험.
    pack_pressure: [80, 120]       # ❌
```

### 할 것 (올바른 방향)
```yaml
# ⭕ 제약 "항목 구조(키)"만 제공. 실제 값은 사용자가 1-2 페이지(Page 3)에서 입력.
injection_molding:
  constraint_keys:                 # 어떤 제약 항목이 있는지 "구조"만
    - { key: injection_velocity, unit: "mm/s", type: range }
    - { key: pack_pressure,      unit: "MPa",  type: range }
    - { key: cycle_time,         unit: "sec",  type: range }
  # 값(예: [40,70])은 여기 없음. 사용자가 Page 3 ConstraintForm에서 입력.
```

**이유**: "사출 속도 정상범위 40~70"을 카탈로그에 디폴트로 박으면, 공장마다 설비·재료가 달라 그 값이 틀릴 때 오히려 시스템이 잘못된 판단을 한다. 카탈로그는 **"사출 공정엔 이런 제약 항목들이 있다"는 구조(가이드)만** 제공하고, **실제 범위 값은 사용자가 입력**한다. 이것이 헌법 "규칙이 결정"의 연장 — 카탈로그는 구조를 제안, 값은 사용자가 결정.

> 이 결정은 blueprint v4에서 확정됨 (line 809/866/944의 "typical_ranges 디폴트 제거"). 이번 명세는 그것을 따른다.

---

## 3. 작업 1 — `catalogs/lines.yaml`

### 위치
`repo/catalogs/lines.yaml` (신규. `catalogs/` 디렉터리도 신규 생성)

### 내용
`0_project_blueprint_v5.md` 부록 A의 YAML 초안을 그대로 본진에 옮긴다.
3 Line × 18 Node × 34 Module 슬롯. 각 Module은 `{function, hint_dataset}` 형태.

구조 (부록 A 발췌, 전체는 부록 A 참조):
```yaml
- line_id: module_1_metal_processing
  display_name: "금속 가공·검사 라인"
  max_stages: 6
  stages:
    - node_id: primary_forming
      display_name: "1차 성형"
      max_modules: 2
      available_modules:
        - { function: maintenance, hint_dataset: "L3_mold_condition" }
        - { function: maintenance, hint_dataset: "L3_mold_anomaly" }
    # ... (부록 A의 나머지 Node 전부)
```

### 헤더 (variable_index §11 권장 형식)
```yaml
# catalogs/lines.yaml
# ──────────────────────────────────────
# 정의: 3 Line × Node × Module 슬롯 카탈로그 (사전정의 파이프라인 구조)
# 사용처: backend /api/lines, agents/planner (module_context), Page 2 CatalogPanel
# 확장 정책: 새 Line/Node 추가 가능. 5번째 모달리티는 금지(무관 — 여긴 공정축).
# 정합: blueprint 부록 A, variable_index §3·§4
# ──────────────────────────────────────
```

### Function 축 (4종) — 여기서 처음 등장
각 module의 `function`은 process/quality/maintenance/reference 4종 중 하나.
이것은 **권한 L1/L2/L3와 완전히 다른 차원**이다 (분석 목적 축).
- `process` — 공정 최적화 (수율·속도)
- `quality` — 품질 판정 (양/불, 결함)
- `maintenance` — 예지보전 (이상 감지)
- `reference` — 참조·주문 (생산량 등)

---

## 4. 작업 2 — `catalogs/modules.yaml`

### 위치
`repo/catalogs/modules.yaml` (신규)

### 내용
Node별 도메인 지식. **constraint_keys 구조 + recommended_models만.** typical_ranges 금지(§2).

```yaml
# catalogs/modules.yaml
# ──────────────────────────────────────
# 정의: Node별 도메인 지식 (constraint_keys 구조 + recommended_models)
# 사용처: agents/planner (module_context), Validator (constraint 검증), Page 3 ConstraintForm, Page 6 모델추천
# 확장 정책: typical_ranges 값 디폴트 금지(D 결정). 구조(키)만. 값은 사용자 입력.
# 정합: blueprint Part 4-3, variable_index §11
# ──────────────────────────────────────

injection_molding:
  display_name: "사출 성형"
  function_hints: [process, quality, maintenance]
  constraint_keys:
    - { key: injection_velocity, unit: "mm/s", type: range }
    - { key: pack_pressure,      unit: "MPa",  type: range }
    - { key: cycle_time,         unit: "sec",  type: range }
  recommended_models:
    - { name: "RandomForestRegressor", task: regression, when: "process 최적화" }
    - { name: "IsolationForest",       task: anomaly,     when: "maintenance 이상감지" }

cnc_cutting:
  display_name: "CNC 절삭"
  function_hints: [process, maintenance]
  constraint_keys:
    - { key: servo_load,    unit: "%",   type: range }
    - { key: spindle_speed, unit: "rpm", type: range }
  recommended_models:
    - { name: "RandomForestClassifier", task: classification, when: "품질 판정" }

# ... 나머지 Node (최소 5개부터 시작: injection_molding/cnc_cutting/press_forming/
#     semiconductor_inspect(검사)/pdm. 점진 확장 — 18개 다 안 채워도 됨)
```

### 시작 범위: 5개 Node 우선
18개 다 채우지 말고 **5개부터** (injection_molding, cnc_cutting, press_forming, semiconductor_inspect, pdm).
이 5개가 4 모달리티 더미를 커버한다. 나머지는 점진 확장 (한 줄씩 추가).

### recommended_models 주의
모델 이름은 **추천 풀(후보)**일 뿐. Page 6에서 LLM이 이 풀 안에서만 추천(환각 방어).
실제 학습은 STEP 1B-2/3 이후. 여기선 카탈로그에 후보만 정의.

---

## 5. 작업 3 — Planner 프롬프트 확장 (module_context + constraints 활성화)

### 현재 상태 (본진 코드 직접 확인)
`agents/planner/planner.py`의 `plan()`은 **이미 `constraints` 파라미터를 받지만 안 쓴다**:
```python
async def plan(data_profile: dict, constraints: dict | None = None, model: str | None = None) -> dict:
    constraints = constraints or {}   # 받지만 프롬프트·후보생성에 미사용 (지금)
```
프롬프트(system/prompt)에도 candidate_operations만 있고 constraints/module_context 없음.

### 할 것
1. **시그니처에 `module_context` 추가** (옵션, 기존 호출 그대로 동작):
```python
async def plan(data_profile: dict, constraints: dict | None = None,
               module_context: dict | None = None, model: str | None = None) -> dict:
```
`module_context` 예시: `{"function": "process", "node_id": "injection_molding", "constraint_keys": [...]}`

2. **constraints를 후보 생성에 활용** — `_candidate_operations`에서 사용자 제약 위반 컬럼에 작업 후보 추가:
```python
# constraints = {"injection_velocity": [40, 70], ...}  (사용자가 Page 3에서 입력한 값)
# 위반 컬럼 → remove_outlier 후보 추가 (L2). 단 "위반 판정"은 결정론(Validator/규칙)이 하고
# 여기선 후보만 추가. blueprint line 105/128-129 흐름 참조.
```

3. **프롬프트에 module_context를 "참고 맥락"으로만 주입** (판단 재료 아님):
```python
prompt = (
    f"dataset_id: {dataset_id}\n"
    f"flags: {data_profile.get('deterministic_flags', [])}\n"
    f"candidate_operations: {json.dumps(candidates, ensure_ascii=False)}\n"
    f"context: 이 데이터는 '{module_context.get('node_id')}' 공정의 "
    f"'{module_context.get('function')}' 목적 데이터입니다. (참고용)\n"   # 맥락만
)
```
**중요**: module_context는 LLM이 순서·이유를 더 잘 정하게 돕는 "참고 맥락"이다.
LLM이 이걸로 새 작업을 만들거나 권한을 바꾸면 안 된다 (가드레일이 여전히 차단).

### 환각 방어 유지 확인
- 후보(candidates)는 여전히 규칙이 추림. module_context가 후보를 늘리지 않음.
- constraints 위반 → 후보 추가는 "규칙"이 함 (결정론). LLM 아님.

---

## 6. 작업 4 — Validator "constraint 위반 검증" 추가 (5번째 검증)

### 현재 상태
`agents/validator/validator.py`는 4종 검증(compliance/transform/integrity/regression).
`validate(execution, plan, profile)` 시그니처.

### 할 것
**5번째 검증 `_check_constraints` 추가** — 사용자 입력 constraints 기준으로 검증:
```python
def _check_constraint_violation(results, constraints, profile):
    """검증5 — 사용자가 Page 3에서 입력한 constraints를 처리 결과가 지키는가.
    ★카탈로그 디폴트(typical_ranges)가 아니라 사용자 입력 constraints 기준★ (§2)."""
    issues = []
    if not constraints:
        return issues   # 제약 없으면 검증 안 함 (1층 단일모드는 constraints 없음)
    # processed 데이터에서 각 constraint key의 범위 위반 행 수를 결정론으로 계산
    # 위반이 남아있으면 issue (severity: medium — 사용자 검토 권장)
    # 예: injection_velocity [40,70] 인데 처리 후에도 80 값이 N개 남음 → 위반
    return issues
```

`validate()` 시그니처에 `constraints` 추가:
```python
async def validate(execution, plan=None, profile=None, constraints=None) -> dict:
    ...
    issues += _check_constraint_violation(results, constraints or {}, profile)
    # checks dict에 "constraint" 항목 추가
```

### 주의
- constraints가 비면(1층 단일 데이터셋 모드) 이 검증은 skip. 회귀 없음.
- 위반 판정은 **결정론**(범위 비교 산수). LLM 안 씀.
- 기준은 **사용자 입력 constraints**. 카탈로그 typical_ranges 아님(없으니까).

---

## 7. 작업 5 — `/api/lines` 엔드포인트 (카탈로그 조회만)

### 위치
`backend/main.py`에 추가 (STEP 1B-2의 라우터 분리 전, 일단 main.py에).

```python
@app.get("/api/lines")
async def lines_endpoint() -> dict:
    """Line·Node·Module 카탈로그 조회 (Page 2 CatalogPanel용). lines.yaml 파싱."""
    import yaml, os
    path = os.path.join(ROOT, "catalogs", "lines.yaml")
    with open(path, encoding="utf-8") as f:
        return {"lines": yaml.safe_load(f)}
```
`requirements.txt`에 `PyYAML` 추가 필요.

UI는 이번 범위 아님. 엔드포인트가 200 + 카탈로그 JSON 반환하면 충분.

---

## 8. 절대 하지 말 것 (금지 목록)

- ❌ `typical_ranges`(정상범위 값)를 카탈로그에 디폴트로 넣기 → `constraint_keys`(구조)만
- ❌ 5번째 모달리티 추가
- ❌ OPERATION_PERMISSION에 없는 작업을 LLM이 만들게 하기
- ❌ module_context를 LLM 판단 재료로 주기 (참고 맥락만)
- ❌ constraint 위반 판정을 LLM에게 시키기 (결정론 산수로)
- ❌ 외부 API 호출
- ❌ UI 구현 (이번 범위 아님 — 1B-3)
- ❌ Mini UI/React/드래그앤드롭 (1B-3)
- ❌ /api/execute_pipeline, Context Aggregator (1B-2)

---

## 9. 완료 검증 기준 (체크리스트)

구현 후 다음을 검증한다:

- [ ] `catalogs/lines.yaml` 3 Line 모두 정의, `yaml.safe_load` 파싱 성공
- [ ] `catalogs/modules.yaml` 최소 5개 Node, **typical_ranges 값 없음**(constraint_keys만)
- [ ] `GET /api/lines` 200 + 카탈로그 JSON 반환
- [ ] `plan(profile, constraints={...}, module_context={...})` 호출 시:
  - [ ] constraints 위반 컬럼에 remove_outlier 후보 추가됨 (규칙)
  - [ ] module_context가 프롬프트에 참고 맥락으로 들어감
  - [ ] module_context 없이 호출해도 기존대로 동작 (회귀 없음)
- [ ] Validator `_check_constraint_violation` 동작:
  - [ ] constraints 주면 위반 검출, 안 주면 skip
  - [ ] 위반 판정이 결정론(LLM 안 씀)
- [ ] 기존 1층 동작 회귀 없음 (4 모달리티 inspect→plan→execute→validate 정상)
- [ ] 전체 `python3 -m py_compile` 통과

---

## 10. 커밋 + 인계 방식

### git 커밋 메시지 (영어)
작업을 논리 단위로 나눠 커밋. 예:
```
feat(STEP1B-1): add lines.yaml + modules.yaml catalogs (constraint_keys, no typical_ranges)
feat(STEP1B-1): activate module_context + constraints in Planner
feat(STEP1B-1): add constraint-violation check to Validator (5th check)
feat(STEP1B-1): add GET /api/lines endpoint
```

### 작업 흐름 (Claude Code)
1. 위 0번 필독 문서 읽기
2. 작업 1~5 순서대로 구현 (각 작업 후 문법 검증)
3. 9번 체크리스트 검증
4. 논리 단위로 커밋
5. `docs/decisions.md`에 D-43~ 추가 (이번 결정 기록)
6. `0_variable_index_v5.md` 갱신 (catalogs 파일 실재화, constraint 검증 추가)
7. push

### 완료 후 claude.ai 세션에 보고할 것
- 각 체크리스트 항목 결과
- catalogs/lines.yaml, modules.yaml 내용 일부
- plan()이 constraints/module_context를 쓰는 것 검증 로그
- Validator constraint 검증 동작 로그
→ claude.ai 세션이 검증하고 STEP 1B-2로 진행 결정

---

## 부록 — 현재 코드 상태 (인계 시점 사실)

- `agents/planner/planner.py` `plan(data_profile, constraints=None, model=None)` — constraints 받지만 미사용
- `agents/validator/validator.py` `validate(execution, plan=None, profile=None)` — 4종 검증
- `harness/guardrails.py` OPERATION_PERMISSION 12종 (L1 3 / L2 6 / L3 3)
- `agents/inspector/inspector.py` `inspect(dataset_id, model=None, modality="timeseries")`
- `mcp-servers/timeseries/semantic.py` — 의미그룹 분류기 (이미 있음)
- `backend/main.py` — /api/lineage 까지 구현됨. ROOT 변수 존재 (sys.path 설정에 사용)
- 4 모달리티 MCP 서버 7도구 동일 계약, step_key 기반 승인, lineage 인메모리
