# STEP 2a 구현 명세서 — 백엔드 옵션 카드 (OptionTree + 결정론 미리보기)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정했고, 이 문서대로 본진(`~/FINAL/manufacturing-mcp/`)에서 구현한다.
> **작성**: 2026-06-02. STEP 1B 완료 후 STEP 2 첫 단계.
> **브랜치**: `feature/step2-option-cards` (이 브랜치에서만 작업).

---

## 0. ★작업 시작 전 (필독)★

### 브랜치 확인 (가장 먼저)
```bash
git branch     # * feature/step2-option-cards 여야 함. 아니면 git checkout feature/step2-option-cards
```
커밋·push 모두 이 브랜치로. main 직접 push 금지. git checkout 되돌리기·reset 금지.

### 컨텍스트 로딩
1. `CLAUDE.md` — 설계 헌법 ("LLM 제안, 규칙 결정").
2. `docs/decisions.md` — D-01~D-102.
3. `docs/0_project_blueprint_v5.md` — Part 7(STEP 2 로드맵 line 1066), Part 5-3(승인 게이트).
4. STEP 2 진단 보고 (이 명세 작성의 근거 — 아래 1장에 요약).
5. 1B-2a(Orchestrator suspend-and-return), 1B-2c(Validator), 1B-3b(승인 카드) 산출물.

### 절대 원칙
- 기존 백엔드(Planner/Executor/승인 흐름) **그대로 활용.** 그 위에 옵션을 얹는다.
- 외부 API 0, 모달리티 4종, 문서 별표(★) 금지(코드 주석 ★는 OK).
- **헌법 정합**: LLM은 "balance_classes 필요" 1회 판단만(기존 그대로). 옵션 펼치기·미리보기는 **결정론**(LLM 0). 옵션 추가해도 LLM 호출 횟수 불변 → 속도 영향 없음.

---

## 1. 배경 — STEP 2 진단 결과 요약 (근거)

진단(feature/step2-option-cards에서 확인)으로 밝혀진 현재 상태:

| 영역 | 현재 | STEP 2a 확장 |
|---|---|---|
| `balance_classes` (executor) | 분석만 — df 미변경 + `"suggested_strategy"` 문자열 1줄 | 옵션 4종으로 펼침 + strategy별 분기 |
| `PlanStep` 스키마 | `strategy: str \| None` **이미 존재** (normalize_group이 사용 중) | strategy를 "선택된 옵션 id"로 재사용 + `available_options` 추가 |
| `step_key` property | (operation, semantic_group\|target\|"global") 기준 — 옵션이 안 바꿈 | **그대로** (승인 누적 호환) |
| `execute_pipeline` 승인 | 단건 yes/no (step_key 누적) | `ApproveReq.selected_option` 추가 |
| `OPERATION_PERMISSION` | balance_classes=L2, 세부 전략 op 0건 | **안 건드림** (옵션=strategy 방식이라 op 안 늘림) |

**확정 설계 = (A) Strategy 식별자 방식 (침습 최소):**
- balance_classes는 L2 단일 op 유지. 옵션(class_weight/SMOTE/...)은 **strategy 필드의 값**.
- guardrails·OperationType **갱신 불필요** (op 안 늘림 → LLM 환각 방어 그대로).
- 옵션 풀은 **코드 고정 목록** (LLM이 생성 X). 환각 방어 = 백엔드가 허용 옵션 집합으로 필터.

---

## 2. STEP 2 범위 + 분할

```
STEP 2a (이번)  백엔드 — Planner OptionTree 출력 + 결정론 미리보기 엔진 + balance_classes 4옵션
STEP 2b (다음)  프론트 — 옵션 카드 UI (Page 4 승인 카드를 옵션 선택 카드로 확장)
```
백엔드 먼저 — UI(2b)가 옵션 트리·미리보기를 받아야 그릴 게 있음.

### 이번(2a)에 만드는 것
1. **OptionTree 생성** — Planner가 balance_classes step에 `available_options` 배열 첨부
2. **결정론 미리보기 엔진** — 각 옵션 적용 시 결과(행수 변화 등)를 계산 (LLM 0, pandas)
3. **옵션 선택 흐름** — `ApproveReq.selected_option` + 세션 저장 + Executor 분기
4. **balance_classes 4옵션** — class_weight / SMOTE / RandomUnderSample / skip

### 옵션 범위 (claude.ai 확정)
- 대상: **balance_classes만** (명확한 L2 = 선택지가 의미 있는 작업). 다른 L2(fill_missing 등)는 추후.
- 실행 범위: **옵션 제시 + 결정론 미리보기 + 선택 저장 = 실동작.**
  - class_weight / skip = 가벼움 → 실제 처리 (가중치 메타 기록 / df 유지)
  - SMOTE / RandomUnderSample = 무거움 → 미리보기(추정) + 선택 저장까지, 실제 리샘플링 적용은
    표시("ML 단계 STEP 3에서 적용") — 단 미리보기 추정치는 정확히 계산.

---

## 3. OptionTree 자료구조 (옵션 풀 정의)

### 3-1. balance_classes 옵션 4종 (코드 고정 — 환각 방어)
새 모듈 `agents/executor/balance_options.py` (또는 executor 내 상수). 옵션 풀:
```python
# agents/executor/balance_options.py
BALANCE_OPTIONS = [
    {
        "id": "class_weight",
        "label": "클래스 가중치 (class_weight)",
        "description": "데이터를 바꾸지 않고, 학습 시 소수 클래스에 가중치 부여. 가장 안전.",
        "effect": "rows_unchanged",      # 미리보기 분기용
        "weight": "light",               # 실행 부하
        "caution": "데이터 분포 그대로. 모델이 가중치를 지원해야 함.",
    },
    {
        "id": "smote",
        "label": "SMOTE 오버샘플링",
        "description": "소수 클래스를 합성 샘플로 늘려 균형. 데이터 증가.",
        "effect": "minority_up",
        "weight": "heavy",
        "caution": "합성 샘플이 추가됨 — 원본 아님. 과적합 주의.",
    },
    {
        "id": "random_under",
        "label": "랜덤 언더샘플링",
        "description": "다수 클래스를 줄여 균형. 데이터 급감.",
        "effect": "majority_down",
        "weight": "heavy",
        "caution": "다수 클래스 정보 손실. 데이터가 적으면 비권장.",
    },
    {
        "id": "skip",
        "label": "보정 안 함 (skip)",
        "description": "불균형을 인지하되 보정하지 않고 그대로 진행.",
        "effect": "none",
        "weight": "none",
        "caution": "모델이 다수 클래스에 편향될 수 있음.",
    },
]
BALANCE_OPTION_IDS = {o["id"] for o in BALANCE_OPTIONS}   # 환각 방어 필터용
```
> 이 목록은 **코드 고정**. LLM이 옵션을 생성하지 않음. → 옵션 추가해도 LLM 호출 0 증가 (속도 무관).

### 3-2. 결정론 미리보기 엔진
새 함수 `compute_balance_preview(df, col)` — 각 옵션 적용 시 결과를 **계산**(LLM 0):
```python
# agents/executor/balance_options.py
def compute_balance_preview(df, col: str) -> dict:
    """클래스 분포 기반으로 각 옵션의 결과를 결정론 계산. 미리보기용.
    실제 리샘플링을 돌리지 않고 행수 변화를 '추정'한다 (정확한 산식)."""
    vc = df[col].value_counts()
    counts = {str(k): int(v) for k, v in vc.items()}
    total = int(len(df))
    if len(vc) < 2:
        return {"applicable": False, "reason": "단일 클래스 — 불균형 보정 불가", "previews": []}
    majority = int(vc.max()); minority = int(vc.min())
    n_classes = len(vc)
    # 가중치 추정 (class_weight='balanced' 산식: total / (n_classes * count))
    weights = {str(k): round(total / (n_classes * int(v)), 2) for k, v in vc.items()}
    previews = {
        "class_weight": {
            "rows_after": total, "rows_delta": 0,
            "detail": f"행수 유지 ({total}행). 소수 클래스 가중치 최대 ~{max(weights.values())}배.",
            "weights": weights,
        },
        "smote": {
            # 모든 클래스를 majority에 맞춤 (imbalanced-learn 기본)
            "rows_after": majority * n_classes,
            "rows_delta": majority * n_classes - total,
            "detail": f"소수 클래스 합성 → 각 클래스 {majority}행, 총 {majority*n_classes}행 "
                      f"(+{majority*n_classes - total}).",
        },
        "random_under": {
            "rows_after": minority * n_classes,
            "rows_delta": minority * n_classes - total,
            "detail": f"다수 클래스 축소 → 각 클래스 {minority}행, 총 {minority*n_classes}행 "
                      f"({minority*n_classes - total}).",
        },
        "skip": {
            "rows_after": total, "rows_delta": 0,
            "detail": "보정 안 함. 불균형 그대로 유지.",
        },
    }
    return {
        "applicable": True,
        "current": {"counts": counts, "total": total,
                    "minority_ratio": round(minority / total, 4)},
        "previews": previews,
    }
```
> 미리보기는 **추정 산식**(imbalanced-learn 기본 동작 기준). 실제 SMOTE를 돌리지 않으므로 빠름.
> 유저에게 "이 옵션 고르면 행수가 이렇게 변한다"를 명확한 숫자로 제공 (claude.ai 강조).

---

## 4. Planner — balance_classes step에 옵션 첨부

### 4-1. PlanStep 스키마 확장 (available_options 추가)
`agents/planner/planner_schemas.py`:
```python
class PlanStep(BaseModel):
    order: int
    operation: OperationType
    target_column: str | None = None
    permission_level: Literal["L1", "L2", "L3"]
    rationale: str = ""
    params: dict[str, Any] = Field(default_factory=dict)
    semantic_group: str | None = None
    group_members: list[str] = Field(default_factory=list)
    strategy: str | None = None              # 기존 — 옵션 방식이면 "선택된 옵션 id"
    available_options: list[dict] = Field(default_factory=list)   # ← 신규: 옵션 풀
    preview: dict = Field(default_factory=dict)                   # ← 신규: 결정론 미리보기
    # step_key property 그대로 (옵션이 step_key 안 바꿈 — 승인 호환)
```
> `available_options`·`preview`는 옵션이 있는 step(balance_classes)에만 채워짐. 다른 step은 빈 채로.

### 4-2. Planner가 balance_classes에 옵션·미리보기 첨부
`agents/planner/planner.py` — plan() 안에서 balance_classes step 생성 시:
```python
# balance_classes step을 만들 때 (기존 candidate 처리 루프 또는 후처리)
if op == "balance_classes":
    from agents.executor.balance_options import BALANCE_OPTIONS, compute_balance_preview
    step_dict["available_options"] = BALANCE_OPTIONS
    # 미리보기는 df가 필요 — Planner가 df 접근 가능하면 여기서, 아니면 execute 시점에 (아래 5-2)
```
> ★주의: Planner가 실제 df에 접근하는지 확인. 진단상 Planner는 data_profile(컬럼 메타)를 받음.
> df 원본이 없으면 미리보기는 **execute_pipeline 단계(df 로드 후)에서 계산**해 pending에 실음 (5-2).
> → 권장: 옵션 풀은 Planner가, 미리보기는 execute_pipeline의 suspend 직전에 (df 있을 때).

---

## 5. execute_pipeline — 옵션 노출 + 선택 + 분기

### 5-1. pending에 옵션·미리보기 노출
`backend/main.py` execute_pipeline의 suspend-and-return 지점 — balance_classes가 unapproved일 때
pending_steps[i]에 옵션·미리보기 첨부:
```python
# suspend 직전, unapproved step 중 balance_classes에 미리보기 계산
for s in unapproved:
    if s.get("operation") == "balance_classes" and s.get("target_column"):
        from agents.executor.balance_options import compute_balance_preview, BALANCE_OPTIONS
        # df는 이 시점에 로드돼 있음 (inspect 단계에서). 없으면 로드.
        preview = compute_balance_preview(df, s["target_column"])
        s_pending = {... 기존 필드 ...,
                     "available_options": BALANCE_OPTIONS,
                     "preview": preview}
    else:
        s_pending = {... 기존 필드 ...}  # 옵션 없는 step은 그대로
```
> pending["plan"] 전체가 이미 응답에 실리므로(진단 line 511), 프론트가 옵션·미리보기를 받을 경로 확보됨.

### 5-2. ApproveReq에 selected_option 추가
`backend/main.py`:
```python
class ApproveReq(BaseModel):
    step_key: str
    stage_order: int | None = None
    module_index: int | None = None
    selected_option: str | None = None    # ← 신규 (옵션 없는 작업은 None)

@app.post("/api/pipeline/{session_id}/approve")
async def pipeline_approve(session_id: str, req: ApproveReq) -> dict:
    session = get_session(session_id)
    if session is None: raise HTTPException(404, ...)
    if req.step_key not in session["approved_step_keys"]:
        session["approved_step_keys"].append(req.step_key)
    # 옵션 선택 저장 (환각 방어 — 허용 옵션만)
    if req.selected_option:
        from agents.executor.balance_options import BALANCE_OPTION_IDS
        if req.selected_option in BALANCE_OPTION_IDS:
            session.setdefault("selected_options", {})[req.step_key] = req.selected_option
        # 허용 외 옵션은 무시 (저장 안 함) — 환각/오류 방어
    save_session(session_id, session)
    return {"approved": True, "step_key": req.step_key,
            "selected_option": session.get("selected_options", {}).get(req.step_key),
            "approved_count": len(session["approved_step_keys"])}
```
> 세션에 `selected_options: dict[step_key, option_id]` 신설. step_key는 안 바뀌므로 기존 승인과 호환.

### 5-3. Executor가 선택된 옵션으로 분기
`agents/executor/executor.py`의 `_op_balance_classes` — 선택된 strategy로 분기:
```python
def _op_balance_classes(df, col, strategy=None):
    """[L2] 선택된 옵션(strategy)으로 분기. strategy 없으면 분석만(기존 동작 유지 — 회귀 방지)."""
    before = _col_stats(df[col])
    vc = df[col].value_counts()
    ratios = {str(k): round(int(v)/len(df), 4) for k, v in vc.items()}
    if strategy == "class_weight":
        # 데이터 미변경 + 가중치 메타 기록 (실제 가중치는 ML 단계에서 사용)
        n = len(vc); total = len(df)
        weights = {str(k): round(total/(n*int(v)), 2) for k, v in vc.items()}
        after = {**_col_stats(df[col]), "class_ratios": ratios,
                 "applied_strategy": "class_weight", "class_weights": weights}
        return df, before, after
    elif strategy == "skip":
        after = {**_col_stats(df[col]), "class_ratios": ratios, "applied_strategy": "skip"}
        return df, before, after
    elif strategy in ("smote", "random_under"):
        # 무거운 리샘플링 — 미리보기는 이미 제공됨. 실제 적용은 ML 단계(STEP 3) 표시.
        after = {**_col_stats(df[col]), "class_ratios": ratios,
                 "applied_strategy": strategy,
                 "note": f"{strategy} 선택됨 — 실제 리샘플링은 ML 단계(STEP 3)에서 적용"}
        return df, before, after   # df 미변경 (STEP 2a 범위)
    else:
        # strategy 없음 — 기존 동작 (분석만). 회귀 방지.
        after = {**_col_stats(df[col]), "class_ratios": ratios,
                 "suggested_strategy": "사용자 선택 필요 (옵션 카드)"}
        return df, before, after
```
> execute_pipeline이 Executor 호출 시 `session["selected_options"].get(step_key)`를 strategy로 전달.
> strategy 없으면 기존 분석 동작 유지 → **회귀 0** (옵션 선택 안 한 경우/다른 모달리티 호환).

### 5-4. Lineage에 선택 기록
선택된 옵션은 lineage에 기록 (SI 추적성 — "사용자가 어떤 보정을 선택했는가"). 기존 lineage 훅 활용.

---

## 6. 절대 하지 말 것
- ❌ OperationType Literal·OPERATION_PERMISSION에 새 op 추가 (옵션=strategy 방식 — op 안 늘림)
- ❌ step_key property 변경 (승인 누적 호환 깨짐)
- ❌ 옵션 풀을 LLM이 생성 (코드 고정 — 환각 방어)
- ❌ strategy 없을 때 동작 변경 (기존 분석 동작 유지 — 회귀 방지)
- ❌ 실제 SMOTE/언더샘플 리샘플링 강제 실행 (미리보기는 추정, 실제는 STEP 3)
- ❌ 다른 L2(fill_missing 등) 옵션화 (이번은 balance_classes만)
- ❌ Inspector/Validator/normalize_group 등 무관 로직 변경
- ❌ 외부 API, 5번째 모달리티, 문서 별표(★)

---

## 7. 검증 (완료 기준)

### OptionTree + 미리보기
- [ ] `agents/executor/balance_options.py` — BALANCE_OPTIONS 4종 + compute_balance_preview
- [ ] balance_classes step에 available_options(4종) + preview(행수 추정) 첨부
- [ ] 미리보기 숫자 정확: class_weight(행수 유지+가중치), smote(majority×n), random_under(minority×n), skip(유지)
- [ ] 단일 클래스 컬럼 → applicable:false (보정 불가 안내)

### 선택 + 분기
- [ ] `ApproveReq.selected_option` 추가, 허용 옵션(BALANCE_OPTION_IDS)만 저장 (환각 방어)
- [ ] 세션 `selected_options[step_key]=option_id` 저장
- [ ] Executor가 strategy로 분기: class_weight→가중치메타, skip→유지, smote/under→선택기록(df유지+STEP3표시)
- [ ] strategy 없으면 기존 분석 동작 (회귀 0)

### 통합 + 회귀
- [ ] event-log 불균형 데이터(press_imbalance 2.85%)로 end-to-end:
      execute_pipeline → awaiting_approval(balance_classes에 옵션·미리보기) →
      approve(selected_option="smote") → resume → completed(applied_strategy 기록)
- [ ] LLM 호출 횟수 옵션 추가 전후 동일 (Planner 1회 — 속도 영향 0 확인)
- [ ] 기존 1B 파이프라인 회귀 0 (normalize_group, 다른 L2 정상)
- [ ] curl 검증 로그 첨부

### 문서
- [ ] decisions.md D-103~ 기록 (옵션 카드 strategy 방식, 미리보기 추정, 회귀 방지)
- [ ] 0_variable_index_v5.md 갱신 (PlanStep.available_options/preview, selected_options, ApproveReq)
- [ ] 별표(★) 0건

---

## 8. 커밋 + 인계

### 작업 흐름
1. 0장 (브랜치 확인 + 컨텍스트 로딩)
2. balance_options.py(옵션+미리보기) → 스키마 → Planner 첨부 → execute_pipeline 노출 → approve → executor 분기
3. **전체 완성 후** 7장 검증 (curl end-to-end + 회귀)
4. **검증 후** 논리 단위 커밋 (feature/step2-option-cards 브랜치, 중간 커밋·checkout 금지):
   ```
   feat(STEP2a): add balance_classes option pool + deterministic preview engine
   feat(STEP2a): extend PlanStep with available_options/preview + planner attach
   feat(STEP2a): add selected_option to approve flow + executor strategy branch
   docs(STEP2a): record D-103~ option-card strategy method + variable_index
   ```
5. **push는 claude.ai 검증 후** (feature/step2-option-cards로).

### 완료 후 claude.ai에 보고
- 7장 체크리스트 결과
- balance_options.py 코드 (옵션 4종 + 미리보기 산식)
- 미리보기 출력 예시 (press_imbalance 2.85% → 각 옵션 행수 추정)
- selected_option 흐름 + executor 분기 코드
- end-to-end curl 로그 (옵션 노출 → smote 선택 → applied_strategy 기록)
- LLM 호출 횟수 불변 확인 (속도 영향 0)
- 회귀 0 확인
- `git branch` (feature/step2-option-cards) + `git log --oneline -6`
- `git log --format='%an <%ae>' -1` (작성자 sbg0700 확인 — Design Chat 아닌지)

---

## 부록 — 헌법 정합 (왜 이 설계인가)
- **"LLM 제안, 규칙 결정" 발전형**: LLM은 "balance_classes 필요" 1회 판단(기존). 옵션 펼치기·미리보기는
  결정론. 사용자가 결정. → LLM 호출 0 증가 (속도 무관) + 사용자 통제 강화.
- **strategy 방식 (A)**: op를 안 늘려 환각 방어 그대로. strategy 필드 재사용(normalize_group 선례).
- **회귀 안전**: strategy 없으면 기존 분석 동작. step_key 불변으로 승인 누적 호환.
- **추적성**: 선택된 옵션을 lineage 기록 — "사용자가 SMOTE를 선택했다"가 감사 가능 (SI 컴플라이언스).
- **미리보기 추정**: 실제 무거운 리샘플링 없이 정확한 산식으로 행수 예측 → 빠르고 유저에게 명확.
