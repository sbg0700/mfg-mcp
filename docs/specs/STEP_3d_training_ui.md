# STEP 3d 구현 명세서 — Page 6 학습 UI (TrainModal)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정. STEP 3c(ML 학습 백엔드) 완료·push 직후.
> **작성**: 2026-06-02. 3c 학습 엔진을 화면으로 — Page 6 실동작 완성.
> **브랜치**: `feature/step3-eda-ml` (이 브랜치에서만 작업).
> **커밋·push는 Claude Code가 진행** (Co-Authored-By는 settings로 제거됨, 작성자 sbg0700). push는 claude.ai 검증 후.

---

## 0. ★작업 시작 전 (필독)★

### 브랜치·폴더 확인
```bash
git branch     # * feature/step3-eda-ml
pwd            # ~/FINAL/manufacturing-mcp
```
커밋·push 이 브랜치로 (Co-Author 없음). main 직접 push 금지. git checkout/reset 금지.

### 컨텍스트 로딩
1. `CLAUDE.md`, `docs/decisions.md` (D-01~D-150).
2. `docs/specs/STEP_3c_ml_training_engine.md` — 학습 백엔드 (이번의 입력).
3. STEP 3d 진단 보고 (아래 1장 요약 — 4 엔드포인트 + task별 결과 + 차트 재사용).
4. STEP 3b(charts/ Histogram·CorrelationBar·common.js), 1B-3c(ModelingPage 골격).

### 절대 원칙
- 백엔드 학습 4 엔드포인트(validate/train/status/result)는 **그대로.** 타겟 드롭다운용 경량 엔드포인트 1개만 신설.
- **교체 = TrainSkeletonModal 한 컴포넌트.** ModelingPage·ModelCard·/recommend 보존 (회귀 0).
- **task별 분기**: 지도(regression/classification)=타겟 드롭다운+confusion/metrics / 비지도(anomaly)=타겟 없음+contamination+score 분포.
- **3b 차트 재사용**: Histogram(score 분포), CorrelationBar(feature importance). 단 **ChartCard 디스패처는 EDA 전용 유지** (CHART_TYPE_IDS 환각 방어 contract 보호 — 학습 차트 추가 금지). Page 6은 컴포넌트만 import.
- confusion matrix = 자체 CSS 그리드 + 색 농도 (recharts heatmap 없음). 외부 heatmap 라이브러리 금지.
- styles.css 신규 클래스만 추가 (기존 수정 X). 다크 톤 유지. 폴리싱은 별도 단계.
- 문서 별표(★) 금지.

---

## 1. 배경 — STEP 3d 진단 결과 요약 (근거)

| 영역 | 현재 | STEP 3d |
|---|---|---|
| TrainSkeletonModal | 골격 안내 모달 (25줄) | TrainModal로 재작성 (실제 학습) |
| ModelingPage/ModelCard | /recommend 표시 + onTrain(rec) | **보존** (회귀 0) |
| 학습 4 엔드포인트 | validate/train/status/result 완비 | 폴링 흐름으로 사용 |
| rec.task | regression/classification/anomaly | 모달 UI 분기 |
| 학습 결과 | task별 (confusion/score_distribution/importance) | KPI 카드 + 차트 |
| 3b 차트 | Histogram, CorrelationBar | score 분포·importance에 재사용 (어댑터) |
| confusion matrix | recharts heatmap 없음 | 신규 CSS 그리드 (ConfusionTable) |
| 타겟 컬럼 소스 | /eda/plan profile (LLM 9초 비용) | **신규 경량 GET /data_profile (LLM 0)** |

**확정 설계 (claude.ai):**
- confusion matrix = (A) 자체 CSS 그리드 + 색 농도 (대각선 초록=정답, 오답 주황)
- 타겟 드롭다운 = (나) 경량 `/data_profile` 엔드포인트 신설 (LLM 0, build_eda_profile만)

### 4 엔드포인트 req/res (진단)
```
POST /train/validate  req TrainReq{model_name, target_column?, params, contamination}
  → {safe_params, notices:[...], needs_confirmation}  / 400(advisory/미지원)
POST /train           req TrainReq → {job_id, status:"running", model_name, dataset_id}
GET  /train/status?job_id=X → {job_id, status:"running"|"completed"|"failed", error?}
GET  /train/result?job_id=X
  → running: {status:"running"}
  → 완료: {status, model_name, result:{...task별...}, error?, lineage_id}
```

### task별 결과 (진단 §④)
```
공통: {status, model_name, task, n_features_used, feature_names, params_used, notices, model_path, lineage_id}
regression:     metrics{r2, rmse, n_train, n_test} + feature_importance[{feature,importance}]
classification: metrics{accuracy, f1, n_train, n_test, auc?} + confusion_matrix{labels,matrix} + feature_importance
anomaly:        metrics{n_total, n_anomaly, anomaly_ratio, contamination} + score_distribution{bins,counts} (importance None)
```

---

## 2. 신규 백엔드 — 경량 /data_profile (LLM 0)

`backend/main.py`:
```python
@app.get("/api/model/{session_id}/data_profile")
async def model_data_profile(session_id: str) -> dict:
    """타겟 컬럼 드롭다운용 — build_eda_profile만 호출 (LLM 0, parquet 읽기). EDA plan과 별개."""
    session = get_session(session_id)
    if session is None: raise HTTPException(404, ...)
    dataset_id = _pick_eda_target(session)   # 3a 재사용
    if dataset_id is None:
        return {"available": False, "reason": "데이터 없음"}
    from eda_engine import build_eda_profile
    profile = build_eda_profile(dataset_id, session.get("modality"))
    return {"available": profile.get("available", False),
            "dataset_id": dataset_id, "columns": profile.get("columns", [])}
```
> LLM 0 — parquet 메타만. /eda/plan(LLM 9초)을 Page 6에서 재호출하는 비효율 회피.

---

## 3. TrainModal — task별 분기 (핵심)

`frontend/src/step6_modeling/TrainModal.jsx` (TrainSkeletonModal 교체):
```jsx
import { useState, useEffect, useRef } from 'react'
import { get, post } from '../api'
import { ConfusionTable } from './charts/ConfusionTable'
import { Histogram } from '../step5_analyze/charts/Histogram'         // 재사용 (score 분포)
import { CorrelationBar } from '../step5_analyze/charts/CorrelationBar' // 재사용 (importance)

export default function TrainModal({ model, sessionId, onClose }) {
  if (!model) return null
  const supervised = model.task === 'regression' || model.task === 'classification'

  const [columns, setColumns] = useState([])
  const [target, setTarget] = useState(null)
  const [contamination, setContamination] = useState(0.05)
  const [validateInfo, setValidateInfo] = useState(null)   // notices 사전 확인
  const [job, setJob] = useState(null)        // {job_id, status}
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const pollRef = useRef(null)

  // 타겟 드롭다운용 컬럼 로드 (지도만)
  useEffect(() => {
    if (!supervised) return
    get(`/model/${sessionId}/data_profile`)
      .then(r => {
        const cols = r.columns || []
        // task별 타겟 후보 필터
        const candidates = model.task === 'regression'
          ? cols.filter(c => c.is_numeric)
          : cols.filter(c => c.n_unique <= 10 || !c.is_numeric)   // 분류: 저카디널리티/범주
        setColumns(candidates)
      })
      .catch(e => setError(e.message))
  }, [sessionId, supervised, model.task])

  // 폴링 cleanup
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  async function onValidate() {
    setBusy(true); setError(null)
    try {
      const r = await post(`/model/${sessionId}/train/validate`, buildReq())
      setValidateInfo(r)   // notices + needs_confirmation
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function onTrain() {
    setBusy(true); setError(null); setResult(null)
    try {
      const r = await post(`/model/${sessionId}/train`, buildReq())
      setJob({ job_id: r.job_id, status: 'running' })
      startPolling(r.job_id)
    } catch (e) { setError(e.message); setBusy(false) }
  }

  function startPolling(jobId) {
    pollRef.current = setInterval(async () => {
      try {
        const s = await get(`/model/${sessionId}/train/status?job_id=${jobId}`)
        if (s.status !== 'running') {
          clearInterval(pollRef.current)
          const res = await get(`/model/${sessionId}/train/result?job_id=${jobId}`)
          if (res.status === 'completed') setResult(res)
          else setError(res.error || '학습 실패')
          setBusy(false)
        }
      } catch (e) { clearInterval(pollRef.current); setError(e.message); setBusy(false) }
    }, 1000)   // 1초 간격
  }

  function buildReq() {
    return { model_name: model.name,
             target_column: supervised ? target : null,
             params: {},   // 기본 — 사용자 파라미터 입력은 추후(폴리싱). 화이트리스트가 거름
             contamination: supervised ? 0.05 : contamination }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal train-modal" onClick={e => e.stopPropagation()}>
        <h2>학습 — {model.name} <span className="muted">(fit {model.fit_score}/5, {model.task})</span></h2>

        {/* 입력 단계 (결과 전) */}
        {!result && (
          <>
            {supervised ? (
              <div className="train-field">
                <label>타겟 컬럼</label>
                <select value={target || ''} onChange={e => setTarget(e.target.value)} disabled={busy}>
                  <option value="">선택...</option>
                  {columns.map(c => (
                    <option key={c.name} value={c.name}>
                      {c.name} ({c.is_numeric ? '숫자' : `범주 ${c.n_unique}종`})
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <div className="train-field">
                <label>이상 비율 (contamination): {contamination}</label>
                <input type="range" min="0.01" max="0.5" step="0.01"
                       value={contamination} disabled={busy}
                       onChange={e => setContamination(parseFloat(e.target.value))} />
                <p className="muted">데이터에서 이상치로 가정할 비율 (IsolationForest)</p>
              </div>
            )}

            {/* 파라미터 조정 알림 (validate 후) */}
            {validateInfo?.notices?.length > 0 && (
              <div className="train-notices">
                <strong>파라미터 안전 조정:</strong>
                <ul>{validateInfo.notices.map((n, i) => <li key={i} className="muted">{n}</li>)}</ul>
              </div>
            )}

            <div className="modal-actions">
              <button className="btn" onClick={onValidate}
                      disabled={busy || (supervised && !target)}>파라미터 확인</button>
              <button className="btn btn-primary" onClick={onTrain}
                      disabled={busy || (supervised && !target)}>
                {busy ? '학습 중...' : '학습 시작'}
              </button>
              <button className="btn" onClick={onClose} disabled={busy}>닫기</button>
            </div>
            {job?.status === 'running' && <div className="muted train-progress">학습 진행 중... (폴링)</div>}
          </>
        )}

        {error && <div className="chart-error">⚠ {error}</div>}

        {/* 결과 단계 */}
        {result && <TrainResult result={result} onClose={onClose} onRetrain={() => { setResult(null); setJob(null) }} />}
      </div>
    </div>
  )
}
```

---

## 4. TrainResult — task별 결과 시각화

```jsx
function TrainResult({ result, onClose, onRetrain }) {
  const r = result.result || {}
  const task = r.task
  const m = r.metrics || {}
  return (
    <div className="train-result">
      <h3>학습 완료 — {r.model_name}</h3>

      {/* KPI 카드 (task별 메트릭) */}
      <div className="metrics-grid">
        {task === 'regression' && (<>
          <Kpi label="R²" value={m.r2?.toFixed(3)} />
          <Kpi label="RMSE" value={m.rmse?.toFixed(2)} />
          <Kpi label="학습/검증" value={`${m.n_train}/${m.n_test}`} />
        </>)}
        {task === 'classification' && (<>
          <Kpi label="Accuracy" value={(m.accuracy*100)?.toFixed(1) + '%'} />
          <Kpi label="F1" value={m.f1?.toFixed(3)} />
          {m.auc != null && <Kpi label="AUC" value={m.auc?.toFixed(3)} />}
        </>)}
        {task === 'anomaly' && (<>
          <Kpi label="전체" value={m.n_total} />
          <Kpi label="이상치" value={m.n_anomaly} />
          <Kpi label="이상 비율" value={(m.anomaly_ratio*100)?.toFixed(1) + '%'} />
        </>)}
      </div>

      {/* confusion matrix (분류) */}
      {r.confusion_matrix && (
        <ConfusionTable labels={r.confusion_matrix.labels} matrix={r.confusion_matrix.matrix} />
      )}

      {/* score 분포 (비지도) — Histogram 재사용 */}
      {r.score_distribution && (
        <Histogram data={{ ...r.score_distribution, column: 'anomaly_score',
                           stats: {} }} />
      )}

      {/* feature importance — CorrelationBar 재사용 (어댑터) */}
      {r.feature_importance && (
        <CorrelationBar data={{
          target_column: '중요도',
          columns: r.feature_importance.map(x => x.feature),
          values: r.feature_importance.map(x => x.importance),
        }} />
      )}

      {/* 조정 알림 */}
      {r.notices?.length > 0 && (
        <div className="train-notices muted">
          {r.notices.map((n, i) => <div key={i}>· {n}</div>)}
        </div>
      )}

      {/* lineage (추적성) */}
      <div className="muted train-lineage">lineage: {result.lineage_id?.slice(0, 8)} · 학습 결과 추적 기록됨</div>

      <div className="modal-actions">
        <button className="btn" onClick={onRetrain}>다시 학습</button>
        <button className="btn btn-primary" onClick={onClose}>완료</button>
      </div>
    </div>
  )
}

function Kpi({ label, value }) {
  return <div className="kpi-card"><div className="kpi-label muted">{label}</div>
    <div className="kpi-value">{value ?? '—'}</div></div>
}
```

---

## 5. ConfusionTable — 자체 CSS 그리드 (신규)

`frontend/src/step6_modeling/charts/ConfusionTable.jsx` (신규):
```jsx
export function ConfusionTable({ labels, matrix }) {
  const n = labels.length
  const max = Math.max(1, ...matrix.flat())
  return (
    <div className="confusion-wrap">
      <div className="muted confusion-title">Confusion Matrix (행=실제, 열=예측)</div>
      <div className="confusion-grid" style={{ gridTemplateColumns: `auto repeat(${n}, 1fr)` }}>
        <div className="cm-corner"></div>
        {labels.map(l => <div key={`h${l}`} className="cm-head">{l}</div>)}
        {matrix.map((row, i) => (
          <Fragment key={`r${i}`}>
            <div className="cm-rowhead">{labels[i]}</div>
            {row.map((v, j) => {
              const ratio = v / max
              const isDiag = i === j   // 대각선 = 정답
              const bg = isDiag
                ? `rgba(22,163,74,${0.15 + ratio*0.55})`    // --c-quality 초록 농도
                : `rgba(234,88,12,${0.10 + ratio*0.45})`    // --c-maintenance 주황 농도
              return <div key={`c${i}-${j}`} className="cm-cell"
                          style={{ background: v ? bg : 'transparent' }}
                          title={`실제 ${labels[i]} → 예측 ${labels[j]}: ${v}`}>{v}</div>
            })}
          </Fragment>
        ))}
      </div>
    </div>
  )
}
```
> 대각선(정답)=초록 농도, 오답=주황 농도. 값 클수록 진하게. recharts 무관, 의존성 0.
> import { Fragment } from 'react' 필요.

---

## 6. ModelingPage 연결 (최소 수정)

```jsx
// import 교체
import TrainModal from './TrainModal'   // was TrainSkeletonModal

// 렌더 (sessionId 전달)
<TrainModal model={trainModel} sessionId={sid} onClose={() => setTrainModel(null)} />

// skeleton-note 안내문 (실엔진 도입됨 — 제거 또는 갱신)
```
> ModelCard·onTrain(rec)·executable/advisory 분리는 그대로 (회귀 0).

---

## 7. styles.css 추가 (신규 클래스만)
```css
/* 학습 모달 (STEP 3d) */
.train-modal { max-width: 720px; }
.train-field { margin: 12px 0; }
.train-field label { display: block; font-size: 13px; margin-bottom: 4px; }
.train-field select, .train-field input[type=range] { width: 100%; background: var(--panel-2);
  border: 1px solid var(--border); color: var(--text); padding: 8px; border-radius: 6px; }
.train-notices { margin: 12px 0; background: var(--panel-2); padding: 10px; border-radius: 6px;
  border-left: 3px solid var(--c-maintenance); font-size: 12px; }
.train-progress { margin-top: 8px; }
.train-result h3 { margin-bottom: 12px; }
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 8px; margin-bottom: 16px; }
.kpi-card { background: var(--panel-2); padding: 10px; border-radius: 6px; text-align: center; }
.kpi-label { font-size: 11px; }
.kpi-value { font-size: 20px; font-weight: 700; color: var(--c-process); }
.train-lineage { font-size: 11px; margin-top: 12px; }
/* confusion matrix */
.confusion-wrap { margin: 16px 0; }
.confusion-title { font-size: 12px; margin-bottom: 6px; }
.confusion-grid { display: inline-grid; gap: 2px; }
.cm-corner, .cm-head, .cm-rowhead, .cm-cell { padding: 8px 12px; text-align: center; font-size: 13px; }
.cm-head, .cm-rowhead { color: var(--muted); font-weight: 600; font-size: 11px; }
.cm-cell { min-width: 48px; border-radius: 4px; color: var(--text); }
```

---

## 8. 절대 하지 말 것
- ❌ 학습 4 엔드포인트(validate/train/status/result) 변경 (그대로 사용)
- ❌ ModelingPage·ModelCard·/recommend 변경 (회귀 0 — import·렌더만 최소 수정)
- ❌ ChartCard 디스패처에 학습 차트 추가 (CHART_TYPE_IDS 환각 방어 contract — EDA 전용 유지)
- ❌ 비지도(anomaly)에 타겟 드롭다운 표시 (task 분기)
- ❌ confusion matrix를 외부 heatmap 라이브러리로 (자체 CSS만)
- ❌ /eda/plan을 Page 6에서 재호출 (경량 /data_profile 사용 — LLM 0)
- ❌ 폴링 cleanup 누락 (setInterval → clearInterval, 모달 닫힘/언마운트 시)
- ❌ Page 1~5 변경 / styles.css 기존 클래스 수정
- ❌ 문서 별표(★)

---

## 9. 검증 (완료 기준)

### task별 모달 UI
- [ ] 지도 분류(RF/XGB Classifier) → 타겟 드롭다운(저카디널리티 컬럼) → 학습 → confusion matrix + Acc/F1/AUC + importance
- [ ] 지도 회귀(RF Regressor) → 타겟 드롭다운(숫자 컬럼) → 학습 → R²/RMSE KPI + importance
- [ ] 비지도(IsolationForest) → 타겟 드롭다운 없음 + contamination 슬라이더 → 학습 → 이상비율 KPI + score 분포(Histogram)
- [ ] /data_profile로 타겟 컬럼 로드 (LLM 0, 빠름)

### 폴링 + 결과
- [ ] 학습 시작 → /train job_id → 1초 폴링 /status → completed → /result
- [ ] 폴링 중 "학습 진행 중..." 표시
- [ ] 모달 닫힘/언마운트 시 setInterval cleanup (메모리 누수 0)
- [ ] 학습 실패 → 에러 표시 (graceful)

### 시각화
- [ ] confusion matrix: CSS 그리드, 대각선 초록/오답 주황 농도, 셀 hover 툴팁
- [ ] score 분포: Histogram 재사용 (비지도)
- [ ] feature importance: CorrelationBar 재사용 (어댑터 변환)
- [ ] notices 박스 (화이트리스트 조정 알림)
- [ ] lineage_id 표시

### 화이트리스트 알림
- [ ] "파라미터 확인"(/validate) → notices 표시 (needs_confirmation)

### 회귀
- [ ] ModelingPage/ModelCard/recommend 보존
- [ ] ChartCard EDA 디스패처 무변경 (CHART_TYPE_IDS 그대로)
- [ ] Page 1~5 영향 0
- [ ] styles.css 기존 클래스 미수정 (신규만)

### 문서
- [ ] decisions.md D-151~ (TrainModal task 분기, confusion CSS, /data_profile, 차트 재사용)
- [ ] 0_variable_index_v5.md (TrainModal, ConfusionTable, /data_profile)
- [ ] 별표(★) 0건

---

## 10. 작업 흐름 + 커밋
1. 0장 (브랜치·폴더 + 컨텍스트)
2. 백엔드 /data_profile (LLM 0) → npm 빌드 환경 확인
3. ConfusionTable(신규) → TrainModal(task 분기 + 폴링) → ModelingPage 연결 → styles
4. **전체 완성 후 검증** (9장 — task 3종 + 폴링 + 시각화 + 회귀)
5. **검증 후 논리 단위 커밋** (feature/step3-eda-ml, checkout/reset 금지):
   ```
   feat(STEP3d): add lightweight data_profile endpoint (LLM 0, target dropdown)
   feat(STEP3d): add ConfusionTable (CSS grid heatmap)
   feat(STEP3d): replace TrainSkeletonModal with TrainModal (task branching + polling)
   feat(STEP3d): reuse Histogram/CorrelationBar for score/importance + styles
   docs(STEP3d): record D-151~ training UI + variable_index
   ```
   - Co-Author 없음 (settings). 작성자 sbg0700.
6. **push는 claude.ai 검증 후.**

### 완료 후 claude.ai에 보고
- 9장 체크리스트
- TrainModal(task 분기) + ConfusionTable 코드
- **브라우저 스크린샷**: 지도 분류(confusion+metrics), 지도 회귀(R²+importance), 비지도(score 분포) 각 1개 + 타겟 드롭다운 + 폴링 진행
- 학습 end-to-end (모델 선택 → 타겟/contamination → 학습 → 결과 + lineage)
- 폴링 cleanup 확인
- 회귀 0 (ModelingPage/ChartCard/Page 1~5)
- `git branch` + `git log --oneline` + `git log --format='%an <%ae>' -1` (sbg0700, Co-Author 없음)

---

## 부록 — 헌법 정합 (왜 이 설계)
- **3c 학습 엔진을 화면으로**: LLM 모델 추천(기존) → 사용자 타겟 선택 → 코드 학습(결정론) → 결과. Page 6 실동작 완성.
- **task 분기 UI**: 지도(타겟+confusion) vs 비지도(contamination+score). 각 모델이 맞는 입력·결과 — 비지도에 타겟 강요 안 함.
- **차트 재사용 + contract 보호**: 3b Histogram/CorrelationBar 재사용하되 ChartCard 디스패처(CHART_TYPE_IDS 환각 방어)는 안 건드림 — 코드 재사용과 contract 분리.
- **confusion CSS 그리드**: recharts heatmap 없음 → 자체 구현. 대각선 초록/오답 주황으로 불균형 문제(FAIL 못 잡음) 시각화 — 보정 전후 데모에 활용 가능.
- **경량 /data_profile**: 타겟 드롭다운에 LLM 불필요 → parquet 메타만 (LLM 0). /eda/plan 재호출 비효율 회피.
- **추적성**: lineage_id 표시 — 학습 결과 감사 기록 (SI 컴플라이언스).
- **회귀 안전**: TrainSkeletonModal 1개 교체. 나머지 보존.
