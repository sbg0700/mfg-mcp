# STEP 3c 구현 명세서 — Page 6 ML 학습 실엔진 (백엔드)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정. STEP 3b(EDA 차트 UI) 완료·push 직후.
> **작성**: 2026-06-02. STEP 3의 가장 무거운 산 — 실제 ML 학습.
> **브랜치**: `feature/step3-eda-ml` (이 브랜치에서만 작업).
> **커밋·push는 Claude Code가 진행** (메시지·본문 설명 작성 포함). settings.local.json attribution으로 Co-Authored-By 제거됨. 작성자 sbg0700. push는 claude.ai 검증 후.

---

## 0. ★작업 시작 전 (필독)★

### 브랜치·폴더 확인 (가장 먼저)
```bash
git branch     # * feature/step3-eda-ml 여야 함
pwd            # ~/FINAL/manufacturing-mcp (레포 루트)
```
커밋·push는 이 브랜치로 (Co-Author 없음). main 직접 push 금지. git checkout 되돌리기·reset 금지.

### 컨텍스트 로딩
1. `CLAUDE.md` — 설계 헌법 ("LLM 제안, 규칙 결정").
2. `docs/decisions.md` — D-01~D-140.
3. `0_project_blueprint_v5.md` — Part 7 (Page 6 모델링).
4. `0_pipeline_ui_spec-2_v5.md`, `0_pipeline_ui_spec-3_v5.md` — 학습 엔드포인트(/train·status·cancel), 메트릭.
5. STEP 3c 진단 보고 (아래 1장 요약).
6. STEP 3a(eda_engine load_processed_df, code_sandbox 화이트리스트 패턴), 1B-2a(suspend-and-return 폴링), harness/lineage.

### ★핵심 원칙 — 모델링 단계의 LLM (EDA와 동일)★
```
① LLM이 판단   — "이 데이터/목적엔 어떤 모델이 적합한지" 추천 (제안, 이미 /recommend에 구현)
② 코드가 실행   — 실제 학습은 scikit-learn/xgboost 결정론 (LLM 0). random_state=42 재현성
③ 파라미터 제안 — LLM/사용자가 제안, 화이트리스트(규칙)가 안전 범위만 통과
```
학습 자체는 LLM 0 (결정론 ML). LLM은 모델 추천(기존)·파라미터 힌트만.

### 절대 원칙
- `/recommend` 엔드포인트는 **그대로** (회귀 0). /train만 신설.
- 학습 데이터 = `load_processed_df`(3a 재사용) — 표준화 완료본. random_state=42 고정(재현성).
- **task별 분기 필수**: 지도(regression/classification)=타겟 필요+confusion / 비지도(anomaly, IsolationForest)=타겟 없음+score 분포.
- **advisory_only 모델(CNN 등)은 학습 거부** (이미 _VRAM_HEAVY_MODELS 마킹됨).
- **파라미터 화이트리스트**: 안전 범위만 통과. 초과 시 무조건 파기 X → 상한 조정 + 사용자 알림 + 사용자 결정.
- **OOM 가드**: 고차원 카테고리 one-hot 제한, row 샘플링, 파라미터 범위.
- 학습 결과·실패 모두 lineage 기록 (transformation_type="model_train").
- scikit-learn + xgboost + imbalanced-learn 도입 (joblib 포함). lightgbm 미도입(추천 풀에 없음).
- 문서 별표(★) 금지 (코드 주석 ★는 OK).

---

## 1. 배경 — STEP 3c 진단 결과 요약 (근거)

| 영역 | 현재 | STEP 3c |
|---|---|---|
| /recommend | 환각 방어(화이트리스트+fit_score 1~5, D-92). advisory_only 마킹 | **그대로** (회귀 0) |
| /train | 0건 (grep) | 신설: POST /train + GET /train/status + GET /train/result |
| 모델 8종 | RF×2, XGB, IF(실학습) + CNN(advisory_only). task 3종 | _TRAIN_MODELS 매핑 dict |
| Page 6 프론트 | TrainSkeletonModal (실학습 미연결) | (3d에서 교체 — 3c는 백엔드) |
| 데이터 로딩 | load_processed_df (3a) | 그대로 재사용 (표준화 완료본) |
| lineage | harness.lineage.record (3a-2) | transformation_type="model_train" |
| 라이브러리 | sklearn/xgboost 0건 | requirements 추가 (sklearn+xgboost+imbalanced-learn+joblib) |
| 리소스 | RAM 26GB 여유, **ML은 CPU**(GPU 8GB 무관), synthetic 부담 0 | OOM 가드는 고차원 카테고리·실데이터 대비 |

**핵심 발견 — ML 학습은 CPU로 돈다 → 8GB VRAM 병목(LLM용)과 무관.** 트리 모델은 26GB RAM 여유에서 편하게. 단 OOM 가드(카테고리 one-hot 등)는 실데이터 대비 필요.

**확정 설계 (claude.ai):**
- 백그라운드 + 폴링 (suspend-and-return 패턴, 진행률 표시)
- 타겟 드롭다운 + LLM 힌트 (지도만)
- 파라미터 화이트리스트 (조정+알림+사용자결정)
- task별 분기 (지도 vs 비지도 IsolationForest)

---

## 2. STEP 3c 전체 구조

```
[Page 6 — /recommend로 모델 추천 (기존, 회귀 0)]
       ↓ 사용자가 모델 선택 + "학습 시작"
  ① task 판정: regression/classification(지도) vs anomaly(비지도 IsolationForest)
       ↓
  ② 지도: 타겟 컬럼 필요 (드롭다운, LLM 힌트)
     비지도: 타겟 없음, contamination(이상 비율) 설정
       ↓
  ③ 파라미터 화이트리스트 검증 (LLM/사용자 제안 → 안전 범위)
     초과 시 → 조정안 + 사용자 알림 (학습 전 확인)
       ↓
  ④ OOM 사전 가드 (카테고리 one-hot 제한, row 샘플링)
       ↓
  ⑤ POST /train → job_id 반환 (백그라운드 학습 시작)
       ↓
  ⑥ GET /train/status (폴링) → 진행률/상태
       ↓
  ⑦ 완료 → GET /train/result → 메트릭 + (지도)confusion / (비지도)score 분포 + feature importance
       ↓
  ⑧ lineage 기록 (model_train, 결과·실패 모두)
```

**구현 분할 (선택적):**
- 핵심: ①~⑧ 한 번에 (학습 엔진 + 폴링 + 가드 + lineage)
- 3d(프론트)에서 진행률·결과 화면

---

## 3. 학습 모델 매핑 (코드 고정)

새 패키지 `agents/ml/` (3a EDA 패턴 일관). `agents/ml/train_models.py`:
```python
from sklearn.ensemble import (RandomForestRegressor, RandomForestClassifier,
                              IsolationForest)
from xgboost import XGBClassifier

# 학습 가능 모델 매핑 (코드 고정 — LLM이 생성 X)
_TRAIN_MODELS = {
    "RandomForestRegressor":  {"cls": RandomForestRegressor,  "task": "regression",     "supervised": True},
    "RandomForestClassifier": {"cls": RandomForestClassifier, "task": "classification", "supervised": True},
    "XGBoostClassifier":      {"cls": XGBClassifier,          "task": "classification", "supervised": True},
    "IsolationForest":        {"cls": IsolationForest,        "task": "anomaly",        "supervised": False},
}
TRAINABLE_MODEL_NAMES = frozenset(_TRAIN_MODELS.keys())   # 환각 방어 필터
# advisory_only(CNNClassifier 등)는 여기 없음 → 학습 거부
```

---

## 4. 파라미터 화이트리스트 (안전 범위 + 조정)

`agents/ml/param_whitelist.py` (3a-2 code_sandbox 화이트리스트 발상):
```python
# 모델별 허용 파라미터 + 안전 범위 (ML 실무 합리적 범위 — 적합한 값은 다 통과)
ALLOWED_PARAMS = {
    "RandomForestRegressor":  {"n_estimators": (10, 500), "max_depth": (2, 30),
                               "min_samples_split": (2, 50), "random_state": "fixed"},
    "RandomForestClassifier": {"n_estimators": (10, 500), "max_depth": (2, 30),
                               "min_samples_split": (2, 50), "class_weight": ["balanced", None],
                               "random_state": "fixed"},
    "XGBoostClassifier":      {"n_estimators": (10, 500), "max_depth": (2, 20),
                               "learning_rate": (0.01, 0.3), "random_state": "fixed"},
    "IsolationForest":        {"n_estimators": (10, 500), "contamination": (0.001, 0.5),
                               "random_state": "fixed"},
}
RANDOM_STATE = 42   # 재현성 고정 (모든 모델)

def validate_and_clamp_params(model_name, requested: dict) -> tuple[dict, list[str]]:
    """제안 파라미터를 화이트리스트로 검증. 범위 초과 시 상한/하한으로 조정(clamp).
    반환: (안전 파라미터, 조정 알림 메시지 리스트). 무조건 파기 X — 조정 후 사용자에게 알림."""
    spec = ALLOWED_PARAMS.get(model_name, {})
    safe = {"random_state": RANDOM_STATE}   # 항상 고정
    notices = []
    for key, val in (requested or {}).items():
        if key not in spec:
            notices.append(f"'{key}'는 허용 파라미터가 아님 — 무시")
            continue
        rule = spec[key]
        if rule == "fixed":
            continue   # random_state 등 — 고정값 유지
        if isinstance(rule, tuple):   # 범위 (lo, hi)
            lo, hi = rule
            if val < lo:
                safe[key] = lo; notices.append(f"'{key}' {val} → 최소 {lo}로 조정")
            elif val > hi:
                safe[key] = hi; notices.append(f"'{key}' {val} → 최대 {hi}로 조정 (안전 범위)")
            else:
                safe[key] = val
        elif isinstance(rule, list):   # 허용 값 목록
            safe[key] = val if val in rule else rule[0]
    return safe, notices
```
> 화이트리스트 = 비현실값(환각/낭비)만 거름. 적합한 범위(10~500 등)는 통과 → 모델링 품질 영향 0.
> 초과 시 무조건 파기 X → clamp + notices(알림). 프론트(3d)가 notices를 사용자에게 보여주고
> "조정 진행 / 취소"를 사용자가 결정 (학습 전 확인 단계).

---

## 5. OOM 사전 가드

`agents/ml/train_engine.py`:
```python
CATEGORY_MAX_UNIQUE = 100    # one-hot 시 고유값 상한 (초과 → 제외 또는 상위N)
ROW_SAMPLE_THRESHOLD = 200_000   # 행 초과 → 샘플링

def prepare_features(df, target_col, supervised) -> tuple:
    """학습 전 feature 준비 + OOM 가드. 결정론 (random_state=42 샘플링)."""
    notices = []
    # row 가드 (실데이터 대비)
    if len(df) > ROW_SAMPLE_THRESHOLD:
        df = df.sample(ROW_SAMPLE_THRESHOLD, random_state=42)
        notices.append(f"행 {len(df)}+ → {ROW_SAMPLE_THRESHOLD} 샘플링")
    # 타겟 분리 (지도만)
    y = None
    if supervised:
        if target_col is None or target_col not in df.columns:
            raise ValueError(f"지도학습 타겟 컬럼 필요: '{target_col}' 없음")
        y = df[target_col]; X = df.drop(columns=[target_col])
    else:
        X = df   # 비지도 — 타겟 없음
    # 카테고리 OOM 가드
    cat_cols = X.select_dtypes(include=["object", "category"]).columns
    for c in cat_cols:
        nun = X[c].nunique()
        if nun > CATEGORY_MAX_UNIQUE:
            X = X.drop(columns=[c])   # 고차원 카테고리 제외 (one-hot 폭발 방지)
            notices.append(f"'{c}' 고유값 {nun}+ → one-hot 폭발 방지로 제외")
    # 남은 카테고리만 one-hot, 숫자만 사용
    X = pd.get_dummies(X, drop_first=True)
    X = X.select_dtypes(include=["number", "bool"]).fillna(0)
    return X, y, notices
```
> 고차원 카테고리(ITEM_CODE 899 등) one-hot 폭발 = OOM 주원인 → 100 초과 시 제외.
> row 20만+ → 샘플링. 둘 다 notices로 사용자에게 알림.

---

## 6. 학습 엔진 + task 분기

`agents/ml/train_engine.py`:
```python
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score, confusion_matrix,
                             r2_score, mean_squared_error, silhouette_score)
import numpy as np, joblib, os

def run_training(dataset_id, model_name, target_col, params, contamination=0.05) -> dict:
    """실제 학습 (결정론, LLM 0). task별 분기. random_state=42."""
    from eda_engine import load_processed_df
    meta = _TRAIN_MODELS[model_name]   # 호출부에서 TRAINABLE 검증 후
    df = load_processed_df(dataset_id)
    if df is None:
        return {"status": "error", "error": "표준화 데이터 없음"}

    X, y, prep_notices = prepare_features(df, target_col, meta["supervised"])
    safe_params, param_notices = validate_and_clamp_params(model_name, params)
    ModelCls = meta["cls"]

    if meta["task"] == "regression":   # 지도 — 회귀
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
        model = ModelCls(**safe_params); model.fit(Xtr, ytr)
        pred = model.predict(Xte)
        metrics = {"r2": float(r2_score(yte, pred)),
                   "rmse": float(np.sqrt(mean_squared_error(yte, pred))),
                   "n_train": len(Xtr), "n_test": len(Xte)}
        result = {"metrics": metrics, "feature_importance": _importance(model, X.columns)}

    elif meta["task"] == "classification":   # 지도 — 분류
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        model = ModelCls(**safe_params); model.fit(Xtr, ytr)
        pred = model.predict(Xte)
        labels = sorted(y.unique().tolist())
        metrics = {"accuracy": float(accuracy_score(yte, pred)),
                   "f1": float(f1_score(yte, pred, average="weighted")),
                   "n_train": len(Xtr), "n_test": len(Xte)}
        # AUC (이진만)
        if len(labels) == 2 and hasattr(model, "predict_proba"):
            proba = model.predict_proba(Xte)[:, 1]
            metrics["auc"] = float(roc_auc_score(yte, proba))
        cm = confusion_matrix(yte, pred, labels=labels).tolist()
        result = {"metrics": metrics, "confusion_matrix": {"labels": [str(l) for l in labels], "matrix": cm},
                  "feature_importance": _importance(model, X.columns)}

    else:   # 비지도 — anomaly (IsolationForest), 타겟 없음
        safe_params["contamination"] = max(0.001, min(0.5, contamination))
        model = ModelCls(**safe_params); model.fit(X)
        scores = model.decision_function(X)    # 이상 점수
        pred = model.predict(X)                # 1=정상, -1=이상
        n_anom = int((pred == -1).sum())
        # score 분포 (히스토그램 — 3a chart 패턴)
        counts, edges = np.histogram(scores, bins=30)
        metrics = {"n_total": len(X), "n_anomaly": n_anom,
                   "anomaly_ratio": round(n_anom / len(X), 4),
                   "contamination": safe_params["contamination"]}
        result = {"metrics": metrics,
                  "score_distribution": {"bins": edges.tolist(), "counts": counts.tolist()},
                  "feature_importance": None}   # IF는 importance 없음

    # 모델 직렬화 (선택 — params에 경로 기록)
    model_path = f"data/models/{dataset_id}__{model_name}.joblib"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)

    result["status"] = "completed"
    result["model_name"] = model_name
    result["task"] = meta["task"]
    result["params_used"] = safe_params
    result["notices"] = prep_notices + param_notices   # 조정/가드 알림
    result["model_path"] = model_path
    return result

def _importance(model, columns):
    if hasattr(model, "feature_importances_"):
        imp = sorted(zip(columns, model.feature_importances_.tolist()),
                     key=lambda x: -x[1])[:20]
        return [{"feature": c, "importance": float(v)} for c, v in imp]
    return None
```

---

## 7. 엔드포인트 — 백그라운드 + 폴링

`backend/main.py`:
```python
import uuid, asyncio

class TrainReq(BaseModel):
    model_name: str
    target_column: str | None = None     # 지도만 (비지도는 None)
    params: dict = {}                     # LLM/사용자 제안 (화이트리스트로 거름)
    contamination: float = 0.05           # 비지도(IsolationForest)만

# 학습 job 저장 (인메모리 — 세션과 별개)
_TRAIN_JOBS: dict[str, dict] = {}

@app.post("/api/model/{session_id}/train")
async def model_train(session_id: str, req: TrainReq) -> dict:
    """학습 시작 — 백그라운드 task 생성, job_id 즉시 반환."""
    session = get_session(session_id)
    if session is None: raise HTTPException(404, ...)
    # 환각/advisory 방어
    from train_models import TRAINABLE_MODEL_NAMES
    if req.model_name not in TRAINABLE_MODEL_NAMES:
        raise HTTPException(400, f"학습 불가 모델 (advisory_only 또는 미지원): {req.model_name}")
    dataset_id = _pick_eda_target(session)   # 3a 재사용 (비-이미지 모듈)
    if dataset_id is None:
        raise HTTPException(400, "학습 대상 데이터 없음")

    job_id = str(uuid.uuid4())
    _TRAIN_JOBS[job_id] = {"status": "running", "session_id": session_id,
                           "model_name": req.model_name, "result": None, "error": None}
    # 백그라운드 실행 (블로킹 학습을 thread에)
    asyncio.create_task(_run_train_job(job_id, dataset_id, req))
    return {"job_id": job_id, "status": "running", "model_name": req.model_name}

async def _run_train_job(job_id, dataset_id, req):
    try:
        from train_engine import run_training
        # CPU 블로킹 → thread executor (이벤트 루프 안 막음)
        result = await asyncio.to_thread(
            run_training, dataset_id, req.model_name, req.target_column,
            req.params, req.contamination)
        _TRAIN_JOBS[job_id]["status"] = result.get("status", "completed")
        _TRAIN_JOBS[job_id]["result"] = result
        # lineage 기록 (성공)
        from harness.lineage import record as lineage_record
        lineage_record(dataset_id=dataset_id, transformation_type="model_train",
            params={"model_name": req.model_name, "task": result.get("task"),
                    "metrics": result.get("metrics"), "params_used": result.get("params_used"),
                    "notices": result.get("notices"), "model_path": result.get("model_path")},
            applied_by_agent="user_approved_train", user_approval_id=req_session(job_id),
            can_rollback=False)
    except Exception as e:
        _TRAIN_JOBS[job_id]["status"] = "failed"
        _TRAIN_JOBS[job_id]["error"] = str(e)
        # lineage 기록 (실패도 — 감사 누락 0)
        from harness.lineage import record as lineage_record
        lineage_record(dataset_id=dataset_id, transformation_type="model_train",
            params={"model_name": req.model_name, "error": str(e), "status": "failed"},
            applied_by_agent="user_approved_train", can_rollback=False)

@app.get("/api/model/{session_id}/train/status")
async def train_status(session_id: str, job_id: str) -> dict:
    job = _TRAIN_JOBS.get(job_id)
    if job is None: raise HTTPException(404, "job not found")
    return {"job_id": job_id, "status": job["status"], "model_name": job["model_name"],
            "error": job.get("error")}

@app.get("/api/model/{session_id}/train/result")
async def train_result(session_id: str, job_id: str) -> dict:
    job = _TRAIN_JOBS.get(job_id)
    if job is None: raise HTTPException(404, "job not found")
    if job["status"] == "running":
        return {"job_id": job_id, "status": "running"}
    return {"job_id": job_id, "status": job["status"],
            "result": job.get("result"), "error": job.get("error")}
```
> 백그라운드 = asyncio.to_thread (CPU 블로킹 학습이 이벤트 루프 안 막게). 폴링 = status/result.
> 진행률 세밀화(boosting_round 등)는 3d에서 필요 시 — 일단 running/completed/failed 상태.

---

## 8. 파라미터 사전 검증 엔드포인트 (선택 — 학습 전 알림)
학습 전 화이트리스트 조정 내용을 사용자가 미리 보게:
```python
@app.post("/api/model/{session_id}/train/validate")
async def train_validate(session_id: str, req: TrainReq) -> dict:
    """학습 전 파라미터 화이트리스트 검증 — 조정 내용을 사용자에게 미리 알림."""
    from param_whitelist import validate_and_clamp_params
    safe, notices = validate_and_clamp_params(req.model_name, req.params)
    return {"safe_params": safe, "notices": notices,
            "needs_confirmation": len(notices) > 0}
```
> 프론트(3d): notices 있으면 "LLM이 X 추천 → 안전 범위 Y로 조정. 진행/취소?" 사용자 결정.

---

## 9. requirements 추가
`backend/requirements.txt`:
```
scikit-learn==1.5.2
xgboost==2.1.3
imbalanced-learn==0.12.4
joblib==1.4.2
```
> CPU 학습으로 충분 (GPU 8GB는 LLM용, ML과 무관). lightgbm 미도입(추천 풀에 없음).
> 도커 재빌드 필요 (backend 컨테이너).

---

## 10. 절대 하지 말 것
- ❌ /recommend 변경 (회귀 0 — /train만 신설)
- ❌ advisory_only 모델(CNN 등) 학습 (TRAINABLE_MODEL_NAMES 외 거부)
- ❌ 비지도(IsolationForest)에 타겟 요구 (task 분기 — 비지도는 타겟 없음)
- ❌ 파라미터 화이트리스트 우회 (범위 밖 값 그대로 학습)
- ❌ 화이트리스트 초과 시 무조건 파기 (조정 + 알림 + 사용자 결정)
- ❌ random_state 미고정 (42 고정 — 재현성)
- ❌ 고차원 카테고리 one-hot 무방비 (OOM 가드 필수)
- ❌ CPU 블로킹 학습을 이벤트 루프에서 직접 (asyncio.to_thread)
- ❌ 학습 실패 lineage 누락 (성공·실패 모두 기록)
- ❌ Page 1~5 변경 / 기존 엔드포인트 변경
- ❌ lightgbm 도입 (추천 풀에 없음)
- ❌ 문서 별표(★)

---

## 11. 검증 (완료 기준)

### 학습 엔진 (task 분기)
- [ ] requirements 추가 + 도커 재빌드 + import 성공 (sklearn/xgboost)
- [ ] 지도 회귀: RandomForestRegressor + 타겟(예: PRESS_FORCE) → R²/RMSE + feature importance
- [ ] 지도 분류: RandomForestClassifier/XGBoost + 타겟(예: PASS_YN) → Acc/F1/(이진)AUC + confusion matrix
- [ ] 비지도: IsolationForest (타겟 없음) → 이상치 비율 + anomaly score 분포 (confusion 없음)
- [ ] random_state=42 → 같은 데이터 2회 학습 시 동일 결과 (재현성)
- [ ] advisory_only(CNN) → 학습 거부 (400)
- [ ] 환각 모델명 → 거부

### 화이트리스트 + OOM 가드
- [ ] params={n_estimators: 100000} → 500으로 조정 + notice ("최대 500으로 조정")
- [ ] 허용 외 파라미터 → 무시 + notice
- [ ] 고차원 카테고리(unique 100+) → one-hot 제외 + notice
- [ ] row 20만+ → 샘플링 + notice (synthetic은 미발동 확인)
- [ ] /train/validate → notices 반환 (사용자 사전 확인용)

### 백그라운드 + 폴링
- [ ] POST /train → job_id 즉시 반환 (running)
- [ ] GET /train/status → running → completed 전이
- [ ] GET /train/result → 완료 시 메트릭/confusion/score 분포
- [ ] CPU 학습이 이벤트 루프 안 막음 (학습 중 다른 요청 응답)

### lineage + 회귀
- [ ] 학습 성공 → lineage (model_train, metrics, params_used, notices)
- [ ] 학습 실패 → lineage 기록 (감사 누락 0)
- [ ] /recommend 보존 (회귀 0)
- [ ] Page 1~5 영향 0

### 문서
- [ ] decisions.md D-141~ (학습 엔진, task 분기, 화이트리스트, OOM 가드, 폴링)
- [ ] 0_variable_index_v5.md (agents/ml/, _TRAIN_MODELS, ALLOWED_PARAMS, /train 엔드포인트)
- [ ] 별표(★) 0건

---

## 12. 작업 흐름 + 커밋
1. 0장 (브랜치·폴더 + 컨텍스트 + 3원칙)
2. requirements 추가 + 도커 재빌드
3. agents/ml/ (train_models → param_whitelist → train_engine) → /train 엔드포인트 → /validate
4. **전체 완성 후 검증** (11장 — task 3종 학습 + 화이트리스트 + OOM + 폴링 + lineage + 회귀)
5. **검증 후 논리 단위 커밋** (feature/step3-eda-ml, checkout/reset 금지):
   ```
   chore(STEP3c): add sklearn/xgboost/imbalanced-learn to requirements
   feat(STEP3c): add ML train engine with task branching (supervised/unsupervised)
   feat(STEP3c): add param whitelist (clamp+notice) + OOM guards
   feat(STEP3c): add background train job + polling endpoints + lineage
   docs(STEP3c): record D-141~ ML training engine + variable_index
   ```
   - Co-Authored-By 없음 (settings). 작성자 sbg0700 확인.
6. **push는 claude.ai 검증 후** (feature/step3-eda-ml로).

### 완료 후 claude.ai에 보고
- 11장 체크리스트
- train_engine.py 핵심 (task 분기) + param_whitelist.py
- 학습 결과 예시: 지도 분류(Acc/F1/confusion), 지도 회귀(R²/RMSE), 비지도(이상비율/score 분포) — 각 1개
- 화이트리스트 동작: n_estimators=100000 → 500 조정 + notice
- OOM 가드: 고차원 카테고리 제외 notice
- 폴링: job_id → status → result 흐름 (curl)
- 재현성: random_state=42 동일 결과
- lineage (성공+실패) + 회귀 0
- `git branch` + `git log --oneline` + `git log --format='%an <%ae>' -1` (sbg0700, Co-Author 없음)

---

## 부록 — 헌법 정합 (왜 이 설계)
- **3원칙**: LLM 모델 추천(기존)·파라미터 힌트 / 코드가 실제 학습(결정론, random_state=42) / 화이트리스트가 안전 범위 거름. "LLM 제안, 규칙 결정"의 모델링 적용.
- **task 분기**: 지도(타겟+confusion) vs 비지도 IsolationForest(타겟 없음+score). 각 모델이 제대로 작동 — 비지도에 타겟 강요하면 모순.
- **화이트리스트 = 비현실값만 거름**: 적합 범위(10~500)는 통과, 환각/낭비값만 조정. 무조건 파기 X → 사용자 결정. 옵션 카드·AST 화이트리스트와 같은 발상.
- **OOM 가드**: 고차원 카테고리 one-hot 폭발(주원인) 방지. 실데이터 대비. CPU 학습이라 8GB VRAM 무관.
- **추적성**: 학습 성공·실패 lineage 기록 — "어떤 모델, 어떤 파라미터, 어떤 결과" 감사 가능 (SI 컴플라이언스).
- **회귀 안전**: /recommend 불변. /train만 신설. Page 1~5 무영향.
- **8GB 정합**: 트리 모델은 CPU+26GB RAM. GPU(LLM용 8GB)와 분리 → 학습이 LLM 병목 안 받음.
