# STEP 3a 구현 명세서 — Page 5 EDA 실엔진 (LLM 판단 + 코드 실행)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정. STEP 2(옵션 카드) 완료 후 STEP 3(실엔진)의 첫 단계.
> **작성**: 2026-06-02. STEP 3 = 골격을 실동작으로 바꾸는 마지막 큰 산.
> **브랜치**: `feature/step3-eda-ml` (이 브랜치에서만 작업).
> **구현 순서**: 설계는 통합(전체 그림), 구현·검증은 **3a-1(LLM 판단 EDA + 기본 차트) → 3a-2(자연어 코드 생성 EDA + 안전 설계)** 단계.

---

## 0. ★작업 시작 전 (필독)★

### 브랜치 확인 (가장 먼저)
```bash
git branch     # * feature/step3-eda-ml 여야 함
```
커밋·push 모두 이 브랜치로. main 직접 push 금지. git checkout 되돌리기·reset 금지.

### 컨텍스트 로딩
1. `CLAUDE.md` — 설계 헌법 ("LLM 제안, 규칙 결정").
2. `docs/decisions.md` — D-01~D-117.
3. `0_project_blueprint_v5.md` — Part 6 (Page 5 EDA).
4. `0_pipeline_ui_spec-2_v5.md` — **Part 6-4(EDA 차트 4 Function 매핑), 6-5(데이터 규모 가드 7종), 6-6(자연어 요약 LLM)**.
5. STEP 3a 진단 보고 (아래 1장 요약).
6. 1B-2b(AggregatedContext), 1B-3c(Page 5 골격), STEP 2a(_maybe_load_df_for_preview 패턴).

### ★핵심 원칙 — EDA·모델링 단계의 LLM (절대 안 흐려짐)★
전처리(Page 1~4)는 LLM 0이지만, **EDA·모델링(뒷단)은 LLM이 판단·제안하는 영역**이다. 3원칙:
```
① LLM이 판단   — 표준화된 데이터를 보고 "어떤 EDA/차트가 필요한지" 추천 (제안)
② 코드가 실행   — 그 추천에 따라 차트 데이터·통계를 결정론으로 계산 (LLM 0, numpy+pandas)
③ 모델링 전 전처리(스케일링/표준화) — LLM은 호출만, 수행은 코드단 (LLM 개입 최소)
```
→ **function_axis별 차트 고정 매핑은 ❌.** spec-2 Part 6-4 매핑은 **LLM 참고 가이드**일 뿐 강제 규칙 아님.
LLM이 데이터 특성을 보고 그 가이드를 참고/판단해 필요한 EDA를 추천한다.

### 원칙 — 데이터 전송 vs UI 라이브러리
- **"외부 API/데이터 전송 0"** = 절대 규칙 (Ollama 로컬만). 변함없음.
- **UI/시각화 npm 라이브러리(recharts 등)** = 로컬 번들, 런타임 데이터 전송 0 → 위 원칙과 무관 → 제한 없음.
- 따라서 **프론트 차트(3b)는 recharts 사용.** (단 3b 작업 — 3a는 백엔드 차트 데이터만)

### 절대 원칙
- EDA 차트 데이터 = `data/processed/{dataset_id}__processed.parquet` 직접 재로드 (진단 확정).
  AggregatedContext엔 분포 없음, MCP 7도구는 분포 미제공(8번째 도구 추가 = 헌법 위반 ❌).
- 결정론 차트 계산은 LLM 0 (numpy+pandas). 같은 입력 → 같은 차트 (재현성).
- scipy 도입 안 함 — FFT는 numpy 내장(`numpy.fft`)으로. 고급 신호처리는 나중 필요시.
- 회귀 0: 기존 /select, /questions, aggregated_context.user_intent 흐름 보존.
- inspection-image 모달리티는 EDA 제외 (skeleton 유지).

---

## 1. 배경 — STEP 3a 진단 결과 요약 (근거)

| 영역 | 현재 | STEP 3a |
|---|---|---|
| EDA 차트 엔드포인트 | 0건 (grep 확인) | 신설 `/api/analyze/{id}/eda/*` |
| Page 5 EDA 표시 | key_findings 텍스트만 (1B-3c 골격), 차트 라이브러리 0 | (3b에서 recharts 렌더 — 3a는 데이터만) |
| AggregatedContext | key_findings 텍스트 + before/after 스칼라. **분포 없음** | LLM 판단 입력으로 활용 + parquet 메타 보강 |
| MCP 7도구 | 분포 미제공 (describe/quantile 없음) | **안 건드림** (계약 보존) |
| 데이터 로딩 | execute_pipeline에서 read. processed/backup.parquet 디스크 상존 | EDA는 `__processed.parquet` 1회 재로드 |
| 라이브러리 | numpy 2.1.3(fft 내장)/pandas/pyarrow. **scipy/sklearn 없음** | numpy만 (scipy 도입 X) |

**확정 설계:**
- `__processed.parquet` 직접 로드 → 차트 데이터 결정론 계산
- 신규 결정론 엔드포인트 (STEP 2a `_maybe_load_df_for_preview` 패턴)
- 모달리티 분기 (timeseries/order=numeric, event-log=카테고리/시퀀스, inspection-image=제외)

---

## 2. STEP 3a 전체 구조 (설계 통합)

```
[Page 5 EDA 흐름]
  /select에서 function_axis 결정 (기존, 회귀 보존)
       ↓
  ── 3a-1: LLM 판단 EDA (기본) ──────────────────────
  ① LLM 판단: parquet 메타 + AggregatedContext + function_axis
              → "어떤 차트가 필요한지" 추천 (제안)
              환각 방어: 허용 차트 타입 집합(CHART_TYPES) 필터
       ↓
  ② 코드 실행: 추천된 차트의 데이터·통계 결정론 계산 (numpy+pandas, LLM 0)
              데이터 규모 가드 7종 적용
       ↓
  ③ LLM 자연어 요약: stats+findings → 한국어 2~3문장 (가치 ④, 환각 방어)
       ↓
  ── 3a-2: 자연어 코드 생성 EDA (안전 설계) ───────────
  ④ 사용자 자연어 입력 ("FAIL 케이스만 분포 보여줘")
       ↓
  ⑤ LLM 코드 생성: 자연어 → pandas/numpy 분석 코드 (제안)
       ↓
  ⑥ 안전 검증: AST 화이트리스트 (허용 연산만) + 샌드박스
       ↓
  ⑦ L2/L3 승인: 사용자가 코드 미리보기 + 승인 (옵션 카드 발상)
       ↓
  ⑧ 실행 + lineage 기록 ("사용자가 이 분석 코드를 승인·실행")
```

**구현 단계:**
- **3a-1**: ①②③ (LLM 판단 + 결정론 차트 + 자연어 요약). 먼저 완성·검증.
- **3a-2**: ④~⑧ (자연어 코드 생성 + 안전 설계). 3a-1 검증 후.

---

## 3. 허용 차트 타입 (CHART_TYPES — 코드 고정, 환각 방어)

새 모듈 `agents/eda/chart_types.py` (또는 backend 내). spec-2 Part 6-4 기반:
```python
# 허용 차트 타입 — 코드 고정 (LLM이 생성 X, 환각 방어 필터용)
CHART_TYPES = {
    "fft_spectrum":     {"label": "FFT 주파수 스펙트럼", "modality": ["timeseries"], "needs": "numeric_signal"},
    "boxplot_by_label": {"label": "타겟 라벨별 박스플롯", "modality": ["timeseries","order","event-log"], "needs": "numeric+label"},
    "histogram":        {"label": "히스토그램", "modality": ["timeseries","order"], "needs": "numeric"},
    "class_distribution":{"label": "클래스 분포 막대", "modality": ["event-log","order"], "needs": "categorical"},
    "correlation_bar":  {"label": "타겟 상관계수 막대", "modality": ["timeseries","order"], "needs": "numeric_multi"},
    "scatter":          {"label": "산점도 (핵심 2변수)", "modality": ["timeseries","order"], "needs": "numeric_multi"},
    "pareto":           {"label": "파레토 차트", "modality": ["event-log","order"], "needs": "categorical_count"},
    "rms_trend":        {"label": "RMS 트렌드", "modality": ["timeseries"], "needs": "numeric_signal"},
}
CHART_TYPE_IDS = frozenset(CHART_TYPES.keys())   # LLM 추천 환각 방어 필터

# function_axis별 기본 차트 가이드 (LLM 참고용 — 강제 아님, spec-2 Part 6-4)
FUNCTION_CHART_GUIDE = {
    "maintenance": {"primary": ["fft_spectrum"], "secondary": ["rms_trend"]},
    "quality":     {"primary": ["boxplot_by_label", "class_distribution"], "secondary": ["histogram"]},
    "process":     {"primary": ["boxplot_by_label"], "secondary": ["correlation_bar", "scatter"]},
    "reference":   {"primary": ["pareto"], "secondary": ["histogram"]},
}
```
> LLM은 FUNCTION_CHART_GUIDE를 **참고**해 데이터 특성에 맞는 차트를 추천. 추천 결과는 CHART_TYPE_IDS로 필터(환각 방어). 가이드 밖 차트도 LLM이 데이터 보고 제안 가능(단 CHART_TYPE_IDS 안에서).

---

## 4. 3a-1: LLM 판단 EDA + 결정론 차트

### 4-1. 신규 엔드포인트 — LLM 차트 추천 (판단)
`backend/main.py`:
```python
@app.post("/api/analyze/{session_id}/eda/plan")
async def eda_plan(session_id: str) -> dict:
    """LLM이 어떤 EDA 차트가 필요한지 판단·추천 (제안). 환각 방어 = CHART_TYPE_IDS 필터."""
    session = get_session(session_id)
    if session is None: raise HTTPException(404, ...)
    ctx = session.get("aggregated_context", {})
    function_axis = ctx.get("user_intent", {}).get("function_axis_focus", "process")
    modality = session.get("modality") or _infer_modality(session)
    dataset_id = session.get("dataset_id")

    # parquet 메타 (LLM 판단 입력 — 분포 대략, 컬럼 종류)
    profile = _build_eda_profile(dataset_id, modality)   # 결정론 (아래 4-2)

    # LLM 판단: profile + AggregatedContext + function_axis → 차트 추천
    model = session.get("model") or OLLAMA_MODEL
    recommended = _llm_recommend_charts(profile, ctx, function_axis, modality, model)
    # 환각 방어: CHART_TYPE_IDS + 모달리티 적합성 필터
    valid = [c for c in recommended
             if c.get("chart_type") in CHART_TYPE_IDS
             and modality in CHART_TYPES[c["chart_type"]]["modality"]]
    # LLM 실패/빈 결과 → function 가이드로 폴백 (graceful)
    if not valid:
        guide = FUNCTION_CHART_GUIDE.get(function_axis, {})
        valid = [{"chart_type": ct, "reason": "function 기본 가이드"}
                 for ct in guide.get("primary", []) if ct in CHART_TYPE_IDS]
    session["eda_plan"] = valid
    save_session(session_id, session)
    return {"function_axis": function_axis, "modality": modality,
            "recommended_charts": valid, "profile": profile}
```

### 4-2. parquet 메타 프로파일 (결정론 — LLM 판단 입력)
`agents/eda/eda_engine.py` (신규):
```python
def _build_eda_profile(dataset_id, modality) -> dict:
    """processed.parquet을 읽어 LLM 판단용 메타 생성 (결정론, 분포 대략)."""
    import pandas as pd, numpy as np
    path = f"data/processed/{dataset_id}__processed.parquet"
    if not os.path.exists(path):
        return {"available": False, "reason": "표준화 결과 없음"}
    df = pd.read_parquet(path)
    cols = []
    for c in df.columns:
        s = df[c]
        is_num = pd.api.types.is_numeric_dtype(s)
        info = {"name": c, "dtype": str(s.dtype), "is_numeric": is_num,
                "n_unique": int(s.nunique(dropna=True)), "null_count": int(s.isna().sum())}
        if is_num:
            info["range"] = [float(s.min()), float(s.max())]  # 분포 대략
        cols.append(info)
    return {"available": True, "rows": int(len(df)), "n_cols": len(df.columns),
            "columns": cols, "modality": modality}
```
> 이 프로파일이 LLM의 "어떤 차트?" 판단 입력. 컬럼 종류(연속/범주), 카디널리티, 범위 → LLM이 보고 추천.

### 4-3. LLM 차트 추천 프롬프트 (판단·제안)
```python
def _llm_recommend_charts(profile, ctx, function_axis, modality, model) -> list[dict]:
    """LLM이 데이터 특성 보고 필요한 차트 추천. 제안만 — 환각 방어는 호출부에서 필터."""
    system = (
        "제조 데이터 EDA 분석가. 표준화된 데이터의 프로파일과 분석 목적을 보고, "
        "어떤 차트가 분석에 필요한지 추천한다. "
        f"가능한 chart_type은 다음만: {list(CHART_TYPE_IDS)}. "
        "이 목록 밖 차트는 추천 금지. 각 추천에 chart_type, target_column(해당시), reason. JSON 배열만."
    )
    user = {
        "profile": profile, "function_axis": function_axis, "modality": modality,
        "function_guide": FUNCTION_CHART_GUIDE.get(function_axis, {}),
        "key_findings": ctx.get("key_findings", [])[:10],
    }
    # generate_json (1B-2b 패턴, B3 에러 표면화 적용)
    return generate_json(system, user, model=model)  # 실패 시 _llm_failed 마커 → 호출부 폴백
```

### 4-4. 결정론 차트 데이터 생성 (코드 실행 — LLM 0)
신규 엔드포인트 + 엔진:
```python
@app.post("/api/analyze/{session_id}/eda/render")
async def eda_render(session_id: str, req: EdaRenderReq) -> dict:
    """승인된 차트들의 데이터·통계를 결정론 계산 (LLM 0). req.charts = eda_plan에서."""
    session = get_session(session_id); ...
    dataset_id = session.get("dataset_id"); modality = ...
    df = _load_processed_df(dataset_id)   # parquet 1회 로드
    results = []
    for chart in req.charts:
        ct = chart.get("chart_type")
        if ct not in CHART_TYPE_IDS:   # 환각 방어
            continue
        data = compute_chart_data(df, ct, chart, modality)  # 결정론 (아래)
        results.append({"chart_type": ct, "data": data})
    session["eda_results"] = results
    save_session(session_id, session)
    return {"charts": results}
```
```python
# agents/eda/eda_engine.py — 결정론 차트 계산 (LLM 0, numpy+pandas)
def compute_chart_data(df, chart_type, chart_spec, modality) -> dict:
    df = _apply_scale_guards(df, chart_type)   # 데이터 규모 가드 (아래 4-5)
    if chart_type == "histogram":
        col = chart_spec["target_column"]; s = df[col].dropna()
        counts, edges = np.histogram(s, bins="auto")
        return {"bins": edges.tolist(), "counts": counts.tolist(),
                "stats": {"mean": float(s.mean()), "std": float(s.std())}}
    if chart_type == "boxplot_by_label":
        col = chart_spec["target_column"]; label = chart_spec.get("label_column")
        groups = {}
        for g, sub in df.groupby(label)[col] if label else [("all", df[col])]:
            q = np.percentile(sub.dropna(), [0, 25, 50, 75, 100])
            groups[str(g)] = {"min": q[0], "q1": q[1], "median": q[2], "q3": q[3], "max": q[4]}
        return {"groups": groups}
    if chart_type == "fft_spectrum":
        col = chart_spec["target_column"]; sig = df[col].dropna().to_numpy()
        sig = _sliding_window_mean_spectrum(sig)   # 가드: sliding window 평균 (numpy.fft)
        freqs = np.fft.rfftfreq(len(sig)); mag = np.abs(np.fft.rfft(sig))
        return {"freqs": freqs.tolist(), "magnitude": mag.tolist()}
    if chart_type == "class_distribution":
        col = chart_spec["target_column"]; vc = df[col].value_counts()
        return {"labels": [str(k) for k in vc.index.tolist()], "counts": vc.tolist()}
    if chart_type == "correlation_bar":
        target = chart_spec["target_column"]
        num = df.select_dtypes("number")
        corr = num.corr()[target].drop(target).abs().sort_values(ascending=False)
        return {"columns": corr.index[:20].tolist(), "values": corr.values[:20].tolist()}
    if chart_type == "pareto":
        col = chart_spec["target_column"]; vc = df[col].value_counts().head(50)
        cum = (vc.cumsum() / vc.sum() * 100)
        return {"labels": [str(k) for k in vc.index], "counts": vc.tolist(),
                "cumulative_pct": cum.tolist()}
    # scatter, rms_trend 등 동일 패턴
    return {}
```

### 4-5. 데이터 규모 가드 7종 (spec-2 Part 6-5)
```python
def _apply_scale_guards(df, chart_type) -> "DataFrame":
    """실데이터 대비 가드. synthetic은 작아 발동 안 하지만 코드는 큰 데이터 대비."""
    # row > 1M → stride sampling (1~10K)
    if len(df) > 1_000_000:
        stride = len(df) // 10_000
        df = df.iloc[::stride]
    return df

def _sliding_window_mean_spectrum(sig, window=4096):
    """FFT 가드: sliding window 평균 스펙트럼 (spec-2 Part 6-5)."""
    if len(sig) <= window:
        return sig
    # window 단위로 잘라 평균 (긴 신호 대비)
    n = len(sig) // window
    return sig[:n*window].reshape(n, window).mean(axis=0)
```
가드 7종 (spec-2): row>1M 샘플링 / 변수>30 상위20 / 이미지 썸네일(EDA제외라 N/A) /
불균형<10% strip오버레이(프론트) / 카테고리30+ 상위50+Others / 한글CSV cp949(parquet이라 N/A) / FFT sliding window.
→ 백엔드 관련(row>1M, 변수>30, 카테고리30+, FFT)은 여기서. 시각화 가드(strip오버레이)는 3b.

### 4-6. LLM 자연어 요약 (가치 ④ — spec-2 Part 6-6)
```python
@app.post("/api/analyze/{session_id}/eda/summary")
async def eda_summary(session_id: str, req: EdaSummaryReq) -> dict:
    """차트 stats + findings → 한국어 2~3문장 요약 (LLM, 환각 방어: 숫자 그대로)."""
    session = get_session(session_id); ...
    system = ("제조 데이터 분석 해설가. stats와 findings를 한국어 2~3문장으로. "
              "숫자는 입력값 그대로 인용. 새 추론·새 숫자 금지. JSON {summary, key_points}.")
    user = {"chart_type": req.chart_type, "stats": req.stats,
            "findings": req.findings, "user_purpose": session.get("analysis_purpose")}
    result = generate_json(system, user, model=session.get("model") or OLLAMA_MODEL)
    return result   # B3 에러 표면화
```

---

## 5. 3a-2: 자연어 코드 생성 EDA (안전 설계)

> ★우리 시스템 핵심 가치 "AI가 코드를 짠다"의 완성형. 단 안전 설계가 필수.★
> ★한글 자연어 지원 확인됨 (gemma 3 한국어 토크나이저 개선, SK텔레콤 4B 한국어 실증).
>   단 e4b 실제 코드 생성 품질은 PoC로 검증 (아래 5-5).★

### 5-1. 신규 엔드포인트 — 자연어 → 코드 생성
```python
@app.post("/api/analyze/{session_id}/eda/freeform")
async def eda_freeform(session_id: str, req: EdaFreeformReq) -> dict:
    """사용자 자연어 → LLM 분석 코드 생성 → AST 검증 → 미리보기 (실행은 승인 후)."""
    session = get_session(session_id); ...
    dataset_id = session.get("dataset_id")
    profile = _build_eda_profile(dataset_id, session.get("modality"))
    # LLM 코드 생성 (제안)
    code = _llm_generate_eda_code(req.user_query, profile, session.get("model") or OLLAMA_MODEL)
    # ★안전 검증 — AST 화이트리스트★
    ok, reason = _validate_eda_code(code)
    if not ok:
        return {"status": "rejected", "reason": reason, "code": code}
    # L2/L3 승인 대기 — 코드 미리보기 반환 (실행 안 함)
    session["pending_eda_code"] = {"code": code, "query": req.user_query}
    save_session(session_id, session)
    return {"status": "awaiting_approval", "code": code, "query": req.user_query}
```

### 5-2. LLM 코드 생성 (제안)
```python
def _llm_generate_eda_code(user_query, profile, model) -> str:
    """사용자 자연어 → pandas/numpy 분석 코드. 제안만 (실행 X, 검증·승인 후)."""
    system = (
        "제조 데이터 분석 코드 생성기. 사용자 요청을 pandas/numpy 코드로 변환. "
        "규칙: df는 이미 로드됨(읽기 전용). 결과는 result 변수에 dict로 저장. "
        "허용: pandas/numpy 읽기 연산, 집계, 필터, 통계. "
        "금지: import, 파일 I/O, 네트워크, exec/eval, df 수정, 시스템 호출. "
        "코드만 출력 (설명·마크다운 금지)."
    )
    user = f"데이터 프로파일: {profile}\n사용자 요청(한국어): {user_query}"
    return generate(system, user, model=model)   # 텍스트 코드
```

### 5-3. ★AST 화이트리스트 검증 (안전 핵심)★
`agents/eda/code_sandbox.py` (신규):
```python
import ast

ALLOWED_NODES = {  # 허용 AST 노드 (읽기 전용 분석만)
    ast.Module, ast.Expr, ast.Assign, ast.Name, ast.Load, ast.Store,
    ast.Constant, ast.Call, ast.Attribute, ast.Subscript, ast.Index,
    ast.BinOp, ast.Compare, ast.BoolOp, ast.UnaryOp, ast.List, ast.Dict,
    ast.Tuple, ast.Slice, ast.keyword, ast.comprehension, ast.ListComp,
    # 연산자들
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Eq, ast.NotEq,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.And, ast.Or, ast.Not, ast.USub,
}
FORBIDDEN_NAMES = {"import", "__import__", "exec", "eval", "open", "compile",
                   "globals", "locals", "getattr", "setattr", "delattr",
                   "os", "sys", "subprocess", "socket", "__builtins__"}
ALLOWED_ROOT_NAMES = {"df", "result", "pd", "np"}   # 사용 가능한 최상위 이름

def _validate_eda_code(code: str) -> tuple[bool, str]:
    """AST 화이트리스트 — 허용 노드·이름만. import/파일/네트워크/exec 차단."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"구문 오류: {e}"
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            return False, f"허용되지 않은 연산: {type(node).__name__}"
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return False, f"금지된 이름: {node.id}"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False, "import 금지"
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return False, "dunder 접근 금지"
    return True, "ok"
```
> 옵션 카드의 "허용 집합 필터"와 같은 발상 — LLM 생성 코드를 **허용된 연산만** 통과시킴.
> import·파일·네트워크·exec·dunder 전부 차단. df는 읽기 전용 사본.

### 5-4. 승인 + 샌드박스 실행 + lineage
```python
@app.post("/api/analyze/{session_id}/eda/freeform/approve")
async def eda_freeform_approve(session_id: str, req: ApproveCodeReq) -> dict:
    """L2/L3 승인 → 샌드박스 실행 → lineage 기록. (옵션 카드 승인 발상)"""
    session = get_session(session_id)
    pending = session.get("pending_eda_code")
    if not pending or not req.approved:
        return {"status": "cancelled"}
    code = pending["code"]
    ok, reason = _validate_eda_code(code)   # 실행 직전 재검증 (이중)
    if not ok:
        return {"status": "rejected", "reason": reason}
    df = _load_processed_df(session["dataset_id"])   # 읽기 전용 사본
    result = _sandbox_exec(code, df)   # 제한된 네임스페이스 실행 (아래)
    # lineage 기록 — "사용자가 이 분석 코드를 승인·실행" (추적성)
    _record_lineage(session, transformation_type="eda_freeform_code",
                    params={"query": pending["query"], "code": code, "approved": True})
    return {"status": "executed", "result": result}

def _sandbox_exec(code, df):
    """제한된 네임스페이스에서 실행 — builtins 차단, df/pd/np만."""
    import pandas as pd, numpy as np
    safe_globals = {"__builtins__": {}}   # builtins 전면 차단
    safe_locals = {"df": df.copy(), "pd": pd, "np": np, "result": None}
    # 타임아웃 가드 (signal 또는 별도 스레드 — 무한 루프 방지)
    exec(compile(code, "<eda>", "exec"), safe_globals, safe_locals)
    return safe_locals.get("result")
```
> **3중 안전**: ① AST 화이트리스트(생성 시) ② 실행 직전 재검증 ③ builtins 차단 네임스페이스 + df 사본.
> L2/L3 승인 = 사용자가 코드 미리보기 후 명시 승인. lineage 기록 = 감사 가능 (SI 컴플라이언스).

### 5-5. ★PoC — 한글 자연어 코드 생성 품질 검증 (구현 전 필수)★
3a-2 본 구현 전, 다음 PoC로 e4b/26b의 한글→코드 능력 확인:
```
테스트 케이스 (한국어 입력 → 기대 코드):
1. "FAIL 케이스만 골라서 값 분포 보여줘"
   → df[df['PASS_YN']=='FAIL']['value'].describe() 류
2. "각 클래스별 평균을 비교해줘"
   → df.groupby('label').mean() 류
3. "상위 10개 결함 유형을 세줘"
   → df['defect_type'].value_counts().head(10) 류

검증: e4b가 위를 AST 통과하는 안전한 코드로 생성하는가?
      26b는? (8GB 타임아웃 고려 — 자연어 EDA는 e4b 권장 결론 가능)
PoC 결과로 3a-2 실현성·모델 권장 확정. e4b 품질 부족 시 → 차트 추천(3a-1)까지만, 자연어 코드는 보류.
```

---

## 6. 절대 하지 말 것
- ❌ function_axis별 차트 고정 매핑 (LLM 판단 + 코드 실행이 원칙. 가이드는 참고용)
- ❌ MCP 7도구에 분포/통계 추가 (8번째 도구 = 헌법 위반). parquet 직접 로드로.
- ❌ scipy/scikit-learn 도입 (3a는 numpy만. FFT는 numpy 내장. ML은 3c)
- ❌ LLM 생성 코드를 검증 없이 실행 (AST 화이트리스트 + 샌드박스 + 승인 필수)
- ❌ 차트 데이터 계산에 LLM 사용 (결정론. LLM은 추천·요약만)
- ❌ inspection-image EDA (skeleton 유지)
- ❌ 기존 /select, /questions, user_intent 흐름 변경 (회귀 0)
- ❌ 외부 API/데이터 전송 (Ollama 로컬만). 단 recharts 등 UI 라이브러리는 3b에서 OK
- ❌ 문서 별표(★) (코드 주석 ★는 OK)

---

## 7. 검증 (완료 기준)

### 3a-1 (LLM 판단 EDA + 결정론 차트)
- [ ] `/api/analyze/{id}/eda/plan` — LLM이 차트 추천, CHART_TYPE_IDS 필터, 모달리티 적합성 검증
- [ ] LLM 실패/빈 결과 → function 가이드 폴백 (graceful)
- [ ] `_build_eda_profile` — processed.parquet 메타 (컬럼 종류/범위/카디널리티)
- [ ] `/api/analyze/{id}/eda/render` — 결정론 차트 데이터 (LLM 0)
- [ ] 차트별 데이터 정확: histogram(bins/counts), boxplot(5수치), fft(freqs/mag),
      class_distribution(labels/counts), correlation_bar, pareto(cumulative)
- [ ] 데이터 규모 가드: row>1M 샘플링, FFT sliding window, 카테고리 상위N
- [ ] 모달리티 분기: timeseries(numeric), event-log(카테고리), inspection-image(제외)
- [ ] `/api/analyze/{id}/eda/summary` — 자연어 요약 (숫자 그대로, 환각 방어)
- [ ] LLM grep: eda_engine.py 결정론 함수(compute_chart_data)에 generate 호출 0

### 3a-2 (자연어 코드 생성 EDA)
- [ ] **PoC 먼저**: e4b 한글 3케이스 → 안전 코드 생성 확인 (26b 비교)
- [ ] `/api/analyze/{id}/eda/freeform` — 자연어 → 코드 생성 → AST 검증 → 미리보기
- [ ] AST 화이트리스트: import/파일/네트워크/exec/dunder 차단 (악성 코드 5종 테스트)
- [ ] 승인 → 샌드박스 실행 (builtins 차단, df 사본) → result 반환
- [ ] lineage 기록 (query+code+approved)
- [ ] 위험 코드 거부: "import os; os.system('rm')" → rejected

### 회귀 + 통합
- [ ] 기존 /select, /questions, user_intent 흐름 보존 (회귀 0)
- [ ] Page 1~4 영향 0
- [ ] curl end-to-end: select → eda/plan → eda/render → summary (3a-1)
- [ ] LLM 0 재현성: 같은 입력 → 같은 차트 데이터 (결정론 부분)

### 문서
- [ ] decisions.md D-118~ (EDA LLM 판단+코드 실행, 자연어 코드 생성 안전 설계)
- [ ] 0_variable_index_v5.md (CHART_TYPES, eda 엔드포인트, code_sandbox)
- [ ] 별표(★) 0건

---

## 8. 커밋 + 인계

### 작업 흐름
1. 0장 (브랜치 확인 + 컨텍스트 + 3원칙)
2. **3a-1 먼저**: chart_types.py → eda_engine.py(profile+compute) → eda/plan·render·summary 엔드포인트
3. 3a-1 검증 (curl + 결정론 재현성 + 회귀)
4. **3a-2 다음**: PoC(한글 코드 생성) → code_sandbox.py(AST) → freeform 엔드포인트 → 샌드박스 실행
5. 3a-2 검증 (악성 코드 거부 + 승인 흐름 + lineage)
6. **전체 검증 후** 논리 단위 커밋 (feature/step3-eda-ml, checkout/reset 금지):
   ```
   feat(STEP3a-1): add EDA chart types + deterministic chart engine (parquet reload)
   feat(STEP3a-1): add LLM chart recommendation + render + summary endpoints
   feat(STEP3a-2): add freeform NL-to-code EDA with AST whitelist sandbox
   feat(STEP3a-2): add code approval flow + lineage recording
   docs(STEP3a): record D-118~ EDA LLM-judges-code-executes + variable_index
   ```
7. **push는 claude.ai 검증 후** (feature/step3-eda-ml로).

### 완료 후 claude.ai에 보고
- 7장 체크리스트 (3a-1, 3a-2 각각)
- chart_types.py + eda_engine.py 핵심 코드
- **PoC 결과**: e4b/26b 한글 자연어 → 코드 생성 품질 (3케이스)
- 차트 데이터 출력 예시 (실데이터 또는 synthetic, function별)
- AST 검증: 악성 코드 5종 거부 로그
- 자연어 EDA end-to-end (자연어 → 코드 → 승인 → 실행 → lineage)
- 회귀 0 + LLM 0 재현성 확인
- `git branch` + `git log --oneline` + `git log --format='%an <%ae>' -1` (sbg0700 확인)

---

## 부록 — 헌법 정합 (왜 이 설계)
- **3원칙 구현**: LLM 판단(차트 추천) + 코드 실행(결정론 차트) + 전처리는 코드단. 헌법 "LLM 제안, 규칙 실행"의 뒷단 적용.
- **차트 고정 매핑 거부**: function 가이드는 LLM 참고용. 데이터 특성을 LLM이 보고 판단 → 유연성 + 우리 가치(AI가 분석을 설계).
- **"AI가 코드를 짠다" 완성**: 자연어 EDA(3a-2)가 시스템 정체성의 핵심. 단 3중 안전(AST/샌드박스/승인) + lineage로 "AI 자율 + 사람 통제 + 추적"을 구현 — SI 컴플라이언스.
- **데이터 전송 0 유지**: 모든 LLM 로컬 Ollama. recharts는 UI 라이브러리(데이터 전송 무관, 3b).
- **회귀 안전**: EDA는 기존 골격(skeleton) 자리를 실엔진으로 대체. /select·/questions 계약 불변.
- **parquet 직접 로드**: AggregatedContext·MCP가 분포 미보유 → processed.parquet이 표준 진입점 (헌법 7도구 계약 보존).
