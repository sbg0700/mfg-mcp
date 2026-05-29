# STEP 1B-2c 구현 명세서 — Validator 강화 (사전+사후 양방향) (Claude Code 인계용)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정했고, 이 문서대로 본진(`~/FINAL/manufacturing-mcp/`)에서 구현한다.
> **작성**: 2026-05-28. STEP 1B-2b(Context Aggregator) 완료·push 직후.

---

## 0. 시작 전 필독 (컨텍스트 로딩)

1. `CLAUDE.md` — 설계 헌법.
2. `docs/decisions.md` — D-01~D-66. 특히 D-32~D-37(Validator 4종), D-43~D-50(1B-1 constraint 검증), D-66(정규화/제약 충돌 — 이번에 해결).
3. `docs/0_project_blueprint_v5.md` Part 4-4 (Context Aggregation 표 — 환각방어 layer 구분), Part 5 (권한 모델).
4. `agents/validator/validator.py` 현재 코드 — 5종 검증(compliance/transform/integrity/regression/constraint). 이번에 확장.

### 이번 작업의 철학 — 검증의 layer 분리 (가장 중요)
이번 작업은 "Validator를 사전+사후 양방향으로 강화"한다. 단 **각 검증이 어느 layer인지 엄격히 지킨다**:

| 질문 | layer | 누가 | 이번 작업? |
|---|---|---|---|
| "계획이 타당한가?" (Executor 전) | 사전 | Validator (결정론) | ⭕ 신규 (작업 2) |
| "결과가 절차적으로 맞나?" | 사후 | Validator (결정론) | 기존 5종 |
| "constraint를 지켰나?" | 사후 | Validator (결정론) | ⭕ 수정 (작업 1 — 원본 기준) |
| "출력이 **고장났나**?" | 사후 | Validator (결정론) | ⭕ 신규 (작업 3 — 고장 감지만) |
| "출력이 **무엇을 말하나**?" (분포 해석) | EDA | Page 5 LLM | ❌ 이번 아님 (미래) |

**핵심 원칙 (헌법 일관)**:
- 이 단계 Validator는 **LLM 0**. 전부 결정론(산수·비교·규칙).
- "고장 감지"(결정론으로 100% 단언 가능)만 한다. **"정상성 판단"·"분포 해석"은 안 한다** → Page 5 EDA LLM으로 분리.
- 임의의 임계값으로 "정상/비정상"을 판정하지 않는다 (typical_ranges 박지 말자던 D-43 논리와 동일 — 공장마다 다른 데이터에 틀린 판정 위험).

---

## 1. STEP 1B-2c 범위 (이번 작업 — 3개 묶음)

```
STEP 1B-2b ✅  Context Aggregator (완료)
STEP 1B-2c (이번)  Validator 강화 3종:
  1. constraint 검증을 원본(__backup) 기준으로 (D-66 해결)
  2. 계획 사전 검증 (Executor 전, 결정론) — 신규
  3. 출력 고장 감지 (사후, 결정론, "정상성 판단" 제외) — 신규
STEP 1B-3 (다음)  Mini UI 6 페이지
```

### 만드는 것
1. **ExecutionResult에 `backup_path` 추가** + executor가 채우기 (작업 1의 전제)
2. **constraint 검증을 `backup_path`(원본) 기준으로 변경** (작업 1)
3. **`validate_plan(plan, profile)` 신규 함수** — Executor 전 사전 검증 (작업 2)
4. **사전 검증을 파이프라인에 연결** — execute / execute_pipeline에서 Executor 전 호출 (작업 2)
5. **`_check_output_health` 신규** — 출력 고장 감지 (작업 3)

---

## 2. 작업 1 — constraint 검증을 원본(`__backup`) 기준으로 (D-66 해결)

### 배경 (D-66)
정규화(normalize_group) 후 데이터에 원시 단위 constraint([40,70] mm/s)를 적용하면
무의미한 위반이 나옴(z-score 값 vs 원시 범위 → 800/800 위반). 사용자가 준 제약은
**원본 측정값 기준**이므로, **정규화 전 원본(`__backup.parquet`)에서 검증**해야 한다.

> 수학적 근거: z-score는 단조변환. "정규화 데이터가 정규화된 제약을 지키나"는
> "원본이 원본 제약을 지켰나"와 동치. 그러니 제약을 변환할 필요 없이 원본에서 검증하면 됨.
> (그룹 공통 정규화라 제약 변환은 μ/σ 어긋남 문제도 있어 더 복잡 — 원본 검증이 정확하고 단순.)

### 2-1. ExecutionResult에 backup_path 추가 (전제)
현재 `executor_schemas.py`에 `output_path`만 있고 `backup_path` 없음. 추가:
```python
# agents/executor/executor_schemas.py
class ExecutionResult(...):
    ...
    output_path: str | None = None      # __processed.parquet (정제 후)
    backup_path: str | None = None       # __backup.parquet (정제 전 원본) — constraint 검증용
```
executor.py에서 backup_path를 ExecutionResult에 담기 (현재 line 180-181에서 backup 저장은 하지만
결과에 안 담음). 3개 경로(timeseries/order 공통, image, event-log) 중 parquet 저장하는 곳:
```python
# line 280 근처 (timeseries/order 경로)
backup_path = os.path.join(OUTPUT_ROOT, f"{dataset_id}__backup.parquet")
return ExecutionResult(dataset_id=dataset_id, results=results,
                       output_path=output_path, backup_path=backup_path, ...)
# event-log 경로(line 502 근처)도 동일하게 backup_path 추가
# image 경로(line 393)는 parquet 아님 → backup_path=None (constraint 검증 대상 아님)
```

### 2-2. _check_constraint_violation을 backup_path 기준으로
현재 `output_path`(processed) 읽는 것을 `backup_path`(원본) 읽도록 변경:
```python
def _check_constraint_violation(execution, constraints):
    if not constraints:
        return []
    # ★D-66: constraint는 원본 측정값 기준 → backup_path(정제 전) 읽음 (processed 아님)
    src_path = execution.get("backup_path") or ""
    if not isinstance(src_path, str) or not src_path.endswith(".parquet"):
        return []      # 이미지 등 비-parquet → 검증 대상 아님
    if not os.path.exists(src_path):
        # backup 없으면 (회귀 안전) processed로 폴백하되, 경고 추가
        src_path = execution.get("output_path") or ""
        if not src_path.endswith(".parquet") or not os.path.exists(src_path):
            return []
    df = pd.read_parquet(src_path)
    # ... 이하 기존 범위 비교 로직 동일 (원본 df에 대해 [lo,hi] 위반 카운트)
```

### 검증
- cnc_machine_injection + constraints={"1ST INJECTION VELOCITY":[40,70]}:
  - 1B-2b에선 800/800 위반(processed 기준)이었음
  - 이번 수정 후 **172/800 위반**(backup 원본 기준)이 나와야 정상 (D-66 해결 확인)

---

## 3. 작업 2 — 계획 사전 검증 `validate_plan` (Executor 전, 신규)

### 철학
지금 Validator는 Executor "후"에만 돈다(사후). LLM이 짠 계획 순서가 이상해도
실행 후에야 잡는다. **Executor "전"에 계획 자체의 타당성을 결정론으로 거른다.**

> 안전장치는 이미 있음(후보는 규칙이 정하니 LLM이 큰 사고 못 침). 사전 검증은
> 그 위에 "순서·충돌"을 한 번 더 거르는 것. 영업 메시지를 "사후"에서 "사전+사후 양방향"으로 강화.

### 위치
`agents/validator/validator.py`에 `validate_plan` 신규 함수 (sync 또는 async, LLM 안 쓰니 sync 가능).

### 검증 항목 (전부 결정론)
```python
def validate_plan(plan: dict, profile: dict | None = None) -> dict:
    """[사전 검증] Executor 실행 전, 계획의 타당성을 결정론으로 검증.
    LLM 0. 순서 규칙 + 작업 충돌 + L3 안전 선행.
    반환: {plan_ok: bool, plan_issues: [...], blocking: bool}"""
    steps = plan.get("steps", [])
    issues = []

    # (a) 순서 규칙 — L1 인코딩/헤더 수정이 L2 정제/정규화보다 뒤에 오면 안 됨
    #     (인코딩 안 고치고 정규화하면 깨진 데이터 정규화). compute_stats는 보통 마지막.
    order_rank = {"detect_encoding": 0, "reparse_header": 0,
                  "clean_masking": 1, "fill_missing": 2, "remove_outlier": 2,
                  "normalize_group": 3, "balance_classes": 3, "create_feature": 3,
                  "compute_stats": 9, "drop_column": 5, "relabel": 5}
    last_rank = -1
    for s in steps:
        r = order_rank.get(s["operation"], 4)
        # compute_stats(9)는 예외 — 언제 와도 됨. 그 외에 rank가 역행하면 경고
        if s["operation"] != "compute_stats" and r < last_rank:
            issues.append({"kind": "plan_order", "severity": "medium",
                           "message": f"순서 의심: {s['operation']}(rank {r})가 앞 작업(rank {last_rank})보다 뒤 — 인코딩/정제 선행 권장"})
        if s["operation"] != "compute_stats":
            last_rank = max(last_rank, r)

    # (b) 작업 충돌 — 같은 컬럼/그룹에 모순 작업 (drop_column 후 그 컬럼을 또 변환 등)
    dropped = set()
    for s in steps:
        if s["operation"] == "drop_column" and s.get("target_column"):
            dropped.add(s["target_column"])
    for s in steps:
        tgt = s.get("target_column")
        if tgt and tgt in dropped and s["operation"] != "drop_column":
            issues.append({"kind": "plan_conflict", "severity": "high",
                           "message": f"충돌: '{tgt}'를 drop_column 하는데 다른 작업({s['operation']})도 그 컬럼 대상"})

    # (c) L3 안전 — L3(drop_column/relabel/merge_external)는 백업 보장 필요.
    #     현재 executor가 항상 백업 뜨므로 통과하지만, plan 차원에서 L3 존재 시 정보성 기록.
    for s in steps:
        if s.get("permission_level") == "L3":
            issues.append({"kind": "plan_l3_notice", "severity": "low",
                           "message": f"L3 작업({s['operation']}) 포함 — 백업·명시 승인 필요"})

    high = [i for i in issues if i["severity"] == "high"]
    return {"plan_ok": len(high) == 0,
            "plan_issues": issues,
            "blocking": len(high) > 0}    # high(충돌)면 실행 차단 권고
```

### 연결 (작업 2-2)
execute / execute_pipeline에서 **Executor 호출 직전**에 `validate_plan` 실행:
```python
# backend/main.py — /api/execute 와 /api/execute_pipeline 양쪽
plan_result = await run_plan(...)
# ★사전 검증 (Executor 전)
from validator import validate_plan
pre = validate_plan(plan_result, profile)
# blocking이면 실행 안 하고 반환 (high 충돌). 아니면 경고만 싣고 진행.
if pre["blocking"]:
    return {"profile": profile, "plan": plan_result,
            "pre_validation": pre, "execution": None,
            "validation": None, "note": "계획 사전 검증 실패(blocking) — 실행 중단"}
# 진행
exec_result = await run_execute(...)
validation = await run_validate(...)
validation["pre_validation"] = pre    # 사후 결과에 사전 결과도 첨부
```

> blocking 기준은 high(작업 충돌)만. 순서 의심(medium)·L3(low)은 경고만 싣고 진행.
> 과하게 막지 않는다 — 대부분은 경고 수준, 진짜 모순(같은 컬럼 drop+변환)만 차단.

---

## 4. 작업 3 — 출력 고장 감지 `_check_output_health` (사후, 신규)

### 철학 — "고장 감지"만, "정상성 판단" 아님
출력 데이터가 **명백히 고장났는지**만 결정론으로 본다. "이 분포가 정상인가/모델링에
적합한가"는 **판단하지 않는다** (그건 Page 5 EDA LLM의 일).

선 긋기: **"100% 틀렸다고 단언 가능"** → 검증. **"해석 필요"** → 안 함(Page 5).
- 표준편차 0 = 다 같은 값 = 변환 실패 → 100% 고장 ✅
- "표준편차가 큰데?" = 원래 그럴 수도 → 해석 필요 ❌ (Page 5)

### 검증 항목 (전부 결정론, processed 데이터 기준)
```python
def _check_output_health(execution: dict) -> list[dict]:
    """검증 — 출력이 명백히 고장났는지 (결정론). '정상성 판단' 아님(Page 5 EDA로).
    processed parquet의 수치 컬럼에 대해 100% 단언 가능한 고장만 감지."""
    import numpy as np
    issues = []
    output_path = execution.get("output_path") or ""
    if not output_path.endswith(".parquet") or not os.path.exists(output_path):
        return issues
    df = pd.read_parquet(output_path)

    # normalize/transform이 적용된 컬럼만 대상 (execution.results에서 추출)
    touched_cols = set()
    for r in execution.get("results", []):
        if r.get("status") == "done":
            touched_cols.update(r.get("group_members", []))
            if r.get("target_column"):
                touched_cols.add(r["target_column"])

    num = df.select_dtypes("number")
    for col in num.columns:
        s = num[col]
        # (a) Inf 발생 — 정규화 결과에 무한대 (0으로 나눔 등)
        inf_mask = np.isinf(s.to_numpy(dtype=float, na_value=np.nan))
        if inf_mask.any():
            issues.append({"kind": "output_health", "severity": "high", "column": col,
                           "message": f"'{col}'에 Inf 발생 — 변환 오류(0으로 나눔 등) 의심"})
        # (b) 표준편차 0 — 변환 후 전부 같은 값 (데이터 죽음). 단 원래 상수 컬럼은 제외 어려우니
        #     '변환이 적용된 컬럼'에 한해 검사 (touched_cols)
        if col in touched_cols and s.notna().sum() > 1 and float(s.std()) == 0.0:
            issues.append({"kind": "output_health", "severity": "high", "column": col,
                           "message": f"'{col}' 변환 후 표준편차 0 — 전부 같은 값(변환 실패) 의심"})

    # (c) 정규화 사후조건 — ★그룹 공통 정규화라 개별 컬럼 평균≈0 강제 금지★
    #     normalize_group(sequence_preserve/profile_group)은 그룹 전체의 평균≈0/표준편차≈1을 봐야 함.
    #     개별 컬럼 평균은 0이 아닐 수 있음(시퀀스 추세 보존의 증거 — 1ST INJECTION VELOCITY=-1.412).
    #     → 그룹 단위로만 검사. 그룹 멤버 전체를 합쳐 평균≈0(±0.1), 표준편차≈1(±0.1) 확인.
    for r in execution.get("results", []):
        if r.get("operation") == "normalize_group" and r.get("status") == "done":
            members = [m for m in r.get("group_members", []) if m in num.columns]
            if len(members) >= 1:
                block = num[members].to_numpy(dtype=float).ravel()
                block = block[~np.isnan(block)]
                if block.size > 1:
                    gmean, gstd = float(np.mean(block)), float(np.std(block))
                    if abs(gmean) > 0.1 or abs(gstd - 1.0) > 0.1:
                        issues.append({"kind": "output_health", "severity": "medium",
                                       "semantic_group": r.get("semantic_group"),
                                       "message": f"그룹 '{r.get('semantic_group')}' 정규화 사후조건 이탈 "
                                                  f"(그룹 평균 {gmean:.3f}, 표준편차 {gstd:.3f} — z-score면 0/1 근처여야)"})
    return issues
```

### ★절대 하지 말 것 (작업 3에서)★
- ❌ "표준편차가 X 이상이면 비정상" 같은 임의 임계값 (typical_ranges 박는 것과 동일 실수)
- ❌ "이 분포가 정상인가" 판단 (Page 5 EDA)
- ❌ 개별 컬럼 평균≈0 강제 (그룹 정규화는 개별 평균 0 아님 — 추세 보존)
- ❌ LLM 호출

### validate에 연결
```python
async def validate(execution, plan=None, profile=None, constraints=None):
    ...
    issues += _check_output_health(execution)    # 6. 출력 고장 감지
    ...
    checks["output_health"] = not any(i["kind"] == "output_health" for i in issues)
```

---

## 5. 절대 하지 말 것 (전체 금지 목록)

- ❌ Validator에 LLM 호출 (이 단계 전부 결정론)
- ❌ "정상성 판단"·"분포 해석" (작업 3은 "고장 감지"만 — 해석은 Page 5)
- ❌ 임의 임계값으로 정상/비정상 판정 (D-43 논리)
- ❌ 개별 컬럼 평균≈0 강제 (그룹 정규화 오판)
- ❌ 사전 검증이 과하게 막기 (high 충돌만 blocking, 나머지 경고)
- ❌ constraint를 processed 기준 검증 (원본 backup 기준 — D-66)
- ❌ Page 5/6 EDA·분포 해석 구현 (미래)
- ❌ 기존 5종 검증 동작 변경 (constraint만 원본 기준으로 수정, 나머지 그대로)

---

## 6. 완료 검증 기준 (체크리스트)

- [ ] ExecutionResult에 backup_path 추가, executor가 채움 (timeseries/order/event-log 경로)
- [ ] **constraint 원본 검증**: cnc_machine_injection [40,70] → **172/800 위반** (800/800 아님 — D-66 해결)
- [ ] **사전 검증 validate_plan**:
  - [ ] 정상 계획 → plan_ok=True
  - [ ] drop_column + 같은 컬럼 변환 주입 → plan_conflict(high), blocking=True
  - [ ] 순서 역행 주입(normalize 후 detect_encoding) → plan_order(medium), 경고만
- [ ] 사전 검증이 execute/execute_pipeline에 연결 (Executor 전 호출, blocking 시 중단)
- [ ] **출력 고장 감지 _check_output_health**:
  - [ ] 정상 출력(cnc_machine_injection) → output_health 통과 (그룹 평균≈0/std≈1 확인)
  - [ ] ★개별 컬럼 평균이 0 아니어도(1ST INJECTION VELOCITY=-1.412) 고장으로 오판 안 함★
  - [ ] (결함주입) 상수 컬럼 정규화 → 표준편차 0 감지(high)
- [ ] **LLM 0 확인**: validator.py에 generate 호출 없음 (grep)
- [ ] 기존 검증 회귀 없음: 4종(compliance/transform/integrity/regression) + 1B-2a/2b pipeline 정상
- [ ] 4 모달리티 회귀 없음
- [ ] `python3 -m py_compile` 통과

### 검증용 시퀀스
```
1) constraint 원본 검증:
   POST /api/execute (cnc_machine_injection, constraints={"1ST INJECTION VELOCITY":[40,70]})
   → validation.checks.constraint=False, issues에 172/800 (800/800 아님)
2) 사전 검증 정상:
   정상 plan → pre_validation.plan_ok=True
3) 사전 검증 차단 (단위테스트):
   validate_plan에 drop_column+같은컬럼 변환 plan 주입 → blocking=True
4) 출력 고장 감지 정상:
   cnc_machine_injection 처리 → output_health 통과, 그룹정규화 사후조건 OK
   (1ST INJECTION VELOCITY 개별 평균 -1.412여도 그룹 평균≈0이라 통과)
5) grep "generate(\|from llm" validator.py → 0건
```

---

## 7. 커밋 + 인계 방식

### 작업 흐름 (1B-2a/2b 교훈)
1. 0번 필독
2. 작업 1~3 구현 (각 작업 후 문법 검증)
3. **전체 완성 후** 6번 체크리스트 검증 (실 HTTP + 결함주입 단위테스트 + grep)
4. **검증 끝나고** 논리 단위 커밋 (중간 커밋·git checkout 되돌리기 금지):
   ```
   feat(STEP1B-2c): add backup_path to ExecutionResult for raw-data constraint check
   fix(STEP1B-2c): validate constraints against raw backup, not normalized output (D-66)
   feat(STEP1B-2c): add validate_plan pre-execution check (order/conflict/L3, deterministic)
   feat(STEP1B-2c): add _check_output_health post-check (failure detection only, no distribution judgment)
   docs(STEP1B-2c): record decisions + variable_index validator update
   ```
5. **push는 claude.ai 검증 후.** 검증 전 commit까지만.
6. `docs/decisions.md` D-67~ 추가 (constraint 원본기준 / 사전검증 / 고장감지 / layer분리),
   `docs/0_variable_index_v5.md` §12 Validator 표 갱신 (사전 + 사후 6종 + output_health)

### 완료 후 claude.ai 세션에 보고할 것
- 6번 체크리스트 결과 (항목별)
- constraint 원본 검증 결과 (172/800 확인 로그)
- `validate_plan` 함수 + 결함주입 테스트 결과 (drop충돌 → blocking)
- `_check_output_health` 함수 (특히 그룹 정규화 사후조건 부분 — 개별평균≈0 강제 안 하는지)
- `grep generate validator.py` → 0건
- `git log --oneline -7` (push 전)
→ claude.ai가 검증하고 STEP 1B-3(Mini UI)로 진행

### ★1B-2a/2b 교훈★
- 전체 완성 → 검증 → 마지막에 논리 단위 커밋 (중간 커밋 X)
- git checkout/reset 되돌리기 쓰지 말 것 (꼬이면 멈추고 보고)
- push는 claude.ai 검증 후

---

## 부록 — 현재 코드 상태 (1B-2b 완료 시점)

- `agents/validator/validator.py`: `validate(execution, plan, profile, constraints)` — 5종 검증
  (compliance/transform/integrity/regression/constraint). `_check_constraint_violation`은
  현재 `output_path`(processed) 읽음 → 작업 1에서 backup_path로 변경.
- `agents/executor/executor.py`: backup 저장은 함(line 180-181, 446)지만 ExecutionResult에 미포함.
  output_path만 담음(line 280, 502). image 경로(393)는 parquet 아님.
- `agents/executor/executor_schemas.py`: ExecutionResult에 output_path만 (backup_path 없음 → 추가).
  results[]에 step_key/before_stats/after_stats/lineage_id/status/semantic_group/group_members.
- `backend/main.py`: /api/execute, /api/execute_pipeline 둘 다 run_plan → run_execute → run_validate.
  → 작업 2에서 run_plan 다음, run_execute 전에 validate_plan 삽입.
- `agents/aggregator/context_aggregator.py`: 결정론 집계 (1B-2b, LLM 0).
- normalize_group: 그룹 공통 mean/std 정규화 (개별 컬럼 평균 0 아님 — 추세 보존).
  results[].group_members에 그룹 멤버 컬럼명, semantic_group에 그룹명.
