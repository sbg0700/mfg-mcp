# STEP 3b 구현 명세서 — Page 5 EDA 차트 UI (recharts)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정. STEP 3a(EDA 백엔드 실엔진) 완료·push 직후.
> **작성**: 2026-06-02. STEP 3a가 만든 차트 데이터를 화면으로.
> **브랜치**: `feature/step3-eda-ml` (이 브랜치에서만 작업).
> **커밋·push는 Claude Code가 진행** (커밋 메시지·본문 설명 작성 포함). 단 settings.local.json의 attribution 설정으로 Co-Authored-By 트레일러는 제거됨. 작성자는 sbg0700.

---

## 0. ★작업 시작 전 (필독)★

### 브랜치·폴더 확인 (가장 먼저)
```bash
git branch     # * feature/step3-eda-ml 여야 함
pwd            # ~/FINAL/manufacturing-mcp (레포 루트) 여야 함
```
커밋·push는 이 브랜치로 (Claude Code 진행, Co-Author 없음). main 직접 push 금지. git checkout 되돌리기·reset 금지.

### 컨텍스트 로딩
1. `CLAUDE.md` — 설계 헌법.
2. `docs/specs/STEP_3a_eda_engine.md` — 백엔드 EDA 엔드포인트 (이번의 입력).
3. STEP 3b 진단 보고 (아래 1장 요약 — 5 엔드포인트 응답 구조 + 차트 8종 data 형태).
4. 1B-3c(AnalyzePage 골격), STEP 2b(ApprovalCard 승인 카드 패턴 — 자연어 EDA 승인에 차용).

### 절대 원칙
- 백엔드(STEP 3a)는 **그대로.** 프론트만. 백엔드 변경 금지.
- **교체 범위 = AnalyzePage.jsx의 `<section className="eda-skeleton">` 한 블록만.**
  /select 흐름, QuestionRadioGroup, "다음→Page 6" 링크는 **보존 (회귀 0).**
- **recharts 도입** — `npm i recharts` (데이터 전송 0이라 헌법 무관, D-118. React 18 호환).
- 다른 페이지(1·2·3·4·6) 변경 금지. styles.css는 **신규 클래스만 추가** (기존 수정 X).
- 기능 위주 + 기존 다크 톤 유지. 전면 리디자인·화려한 애니메이션 금지 (UI 폴리싱은 별도 단계).
- LLM 요약(/eda/summary)은 사용자 클릭 시 호출 (e4b 4초/요청 — 일괄 자동 호출 X).
- 문서 별표(★) 금지 (코드 주석 ★는 OK).

---

## 1. 배경 — STEP 3b 진단 결과 요약 (근거)

### 교체 지점
- `AnalyzePage.jsx:129-160` `<section className="eda-skeleton">` 한 블록 교체 (skeleton-note 줄 포함).
- /select 응답 `{session_id, analysis_purpose, function_axis, free_input}` → `savedResult` state (보존).
- api.js: 범용 `get/post/put`만 (엔드포인트별 헬퍼 0). HTTP 에러는 `err.detail` → `e.message` 도달.

### 3a 엔드포인트 5개 (request → response)
```
POST /eda/plan      req {} (or {function_axis})
  → {available, function_axis, modality, dataset_id,
     recommended_charts:[{chart_type, target_column?, label_column?, reason_ko}],
     profile:{rows, n_cols, columns:[...]}, llm_status:"ok"|"failed", model_used}
  → graceful: {available:false, reason} / llm 실패 시 폴백(fallback:true 마커)

POST /eda/render    req {charts:[...]}  (= plan의 recommended_charts 그대로 전달 가능)
  → {charts:[{chart_type, label, data:{...차트별...}}]}
  → 항목별 error: {error:"modality '..' 미지원" | "허용되지 않은 chart_type" | "compute 실패"}

POST /eda/summary   req {chart_type, stats, findings?}
  → {llm_status:"ok", summary:"...", key_points:[...], model_used}
  → llm 실패: {llm_status:"failed", summary:"", key_points:[]} (200)
  → bogus chart_type: HTTP 400 {detail}

POST /eda/freeform  req {user_query:"한국어 자연어"}
  → status별 분기 (모두 200):
     "awaiting_approval": {code:"result = df...", query, model_used, dataset_id, modality}
     "rejected": {reason, code?, query?}  (AST 거부 등)
     "llm_failed": {error, model_used}

POST /eda/freeform/approve  req {approved:bool}
  → "executed": {result, result_type, lineage_id, code, query}
  → "cancelled" / "rejected_at_exec":{reason} / "exec_failed":{error, lineage_id}
  → "no_pending":{reason}
```

### 차트 8종 data 구조 → recharts 매핑
| chart_type | data 키 | recharts |
|---|---|---|
| histogram | `{column, bins:[N+1], counts:[N], stats:{mean,std,min,max,n}}` | BarChart (bins 중점→x, counts→y) |
| boxplot_by_label | `{target_column, label_column, groups:{<label>:{min,q1,median,q3,max,n}}}` | **ComposedChart + ErrorBar** (확정 ↓ 3-3) |
| fft_spectrum | `{column, freqs:[], magnitude:[], stats:{window_len, peak_freq}}` | LineChart (freqs→x, magnitude→y) |
| rms_trend | `{column, window_size, rms:[], indices:[]}` | LineChart (indices→x, rms→y) |
| class_distribution | `{column, labels:[], counts:[], others_count?}` | BarChart (labels→x, counts→y) |
| correlation_bar | `{target_column, columns:[], values:[]}` | BarChart horizontal (columns→y, values→x) |
| pareto | `{column, labels:[], counts:[], cumulative_pct:[], others_count?}` | ComposedChart (Bar=counts, Line=cumulative, dual Y) |
| scatter | `{x_column, y_column, x:[], y:[], n}` | ScatterChart (x,y→[{x,y}]) |

> 차트 항목에 `error` 또는 `data.error` 있으면 → 에러 박스 우선 표시(차트 영역 비움).
> `others_count` → "+기타 N개" 푸터. `stats.peak_freq` → "peak ≈ X Hz" 캡션. histogram stats → mean/std 칩.

### 디자인 토큰 (styles.css)
`--c-process #2563eb(파랑) / --c-quality #16a34a(초록) / --c-maintenance #ea580c(주황) / --c-reference #64748b(회색) / --panel #1e293b / --panel-2 #273449 / --border #334155 / --text #e2e8f0 / --muted #94a3b8`. recharts는 CSS 변수 지원(`fill="var(--c-process)"`).

---

## 2. STEP 3b 구조 (설계)

```
[Page 5 — /select 후]
  savedResult 존재 → "EDA 실행" 버튼 (사용자 클릭 모델)
       ↓ 클릭
  ① POST /eda/plan → recommended_charts + profile + llm_status
       ↓
  ② POST /eda/render (recommended_charts 전달) → charts[].data
       ↓
  ③ recharts로 차트 N개 렌더 (ChartCard 디스패처 — chart_type별 컴포넌트)
       ↓
  ④ 각 차트 "AI 요약" 버튼 → POST /eda/summary → summary + key_points (클릭 시)

[자연어 EDA 카드 (3a-2 UI) — 별도]
  ⑤ 입력창 "예: FAIL 케이스만 분포 보여줘" + "분석 요청" 버튼
       ↓ POST /eda/freeform
  ⑥ status==="awaiting_approval" → 코드 미리보기(monospace) + "승인/취소" (ApprovalCard 패턴)
       ↓ POST /eda/freeform/approve {approved}
  ⑦ status==="executed" → result 표시 (JSON 또는 표/막대)
     rejected/llm_failed → 에러 박스
```

**UX 결정: "EDA 실행" 버튼 명시 클릭 모델** (자동 호출 X). 이유:
- /eda/plan은 LLM 호출(e4b 9초) — /select 직후 자동 실행하면 사용자가 기다림 인지 못함.
- 버튼 클릭 → "차트 추천 중..." 로딩 표시 → 명확. (단 로딩 문구는 모델별 시간 — 백로그2 고려, 일단 "추천 중...")

---

## 3. 차트 컴포넌트 (recharts)

### 3-1. ChartCard 디스패처
`frontend/src/step5_analyze/charts/ChartCard.jsx` (신규):
```jsx
import { Histogram } from './Histogram'
import { BoxPlot } from './BoxPlot'
import { FftSpectrum } from './FftSpectrum'
// ... 8종 import

const CHART_COMPONENTS = {
  histogram: Histogram,
  boxplot_by_label: BoxPlot,
  fft_spectrum: FftSpectrum,
  rms_trend: RmsTrend,
  class_distribution: ClassDistribution,
  correlation_bar: CorrelationBar,
  pareto: Pareto,
  scatter: Scatter,
}

export function ChartCard({ chart, sessionId }) {
  // 에러 우선 분기
  if (chart.error) return <ChartError label={chart.label} message={chart.error} />
  const data = chart.data || {}
  if (data.error) return <ChartError label={chart.label} message={data.error} />

  const Comp = CHART_COMPONENTS[chart.chart_type]
  if (!Comp) return <ChartError label={chart.label} message="미지원 차트" />

  return (
    <div className="chart-card">
      <div className="chart-card-head">
        <strong>{chart.label}</strong>
        <button className="btn-sm" onClick={() => onSummary(chart, sessionId)}>AI 요약</button>
      </div>
      <Comp data={data} />
      <ChartFooter data={data} />   {/* others_count, peak_freq, stats 칩 */}
      {/* AI 요약 결과 표시 영역 (클릭 시 /eda/summary) */}
    </div>
  )
}
```

### 3-2. recharts 다크 톤 공통 (모든 차트 적용)
```jsx
// 공통 props (각 차트에서 재사용)
const AXIS = { stroke: "var(--muted)", fontSize: 12 }
const GRID = { stroke: "var(--border)", strokeOpacity: 0.4 }
const TOOLTIP_STYLE = { background: "var(--panel-2)", border: "1px solid var(--border)", color: "var(--text)" }
// 예: <CartesianGrid {...GRID} /> <XAxis {...AXIS} /> <Tooltip wrapperStyle={TOOLTIP_STYLE} />
```

### 3-3. ★BoxPlot — ComposedChart + ErrorBar (확정 방식)★
recharts에 박스플롯 내장 없음 → ComposedChart로 구성:
```jsx
import { ComposedChart, Bar, ErrorBar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export function BoxPlot({ data }) {
  // groups:{<label>:{min,q1,median,q3,max,n}} → recharts data 변환
  const rows = Object.entries(data.groups || {}).map(([label, g]) => ({
    label,
    // 박스(q1~q3): base=q1, boxHeight=q3-q1 (Bar의 stacked로 표현)
    q1: g.q1, boxHeight: g.q3 - g.q1, median: g.median,
    // 수염(min~max): ErrorBar용 [median-min, max-median] 또는 [low,high]
    whiskerLow: g.median - g.min, whiskerHigh: g.max - g.median,
    min: g.min, max: g.max, n: g.n,
  }))
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={rows}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="label" {...AXIS} />
        <YAxis {...AXIS} />
        <Tooltip wrapperStyle={TOOLTIP_STYLE}
                 formatter={(v, name, p) => boxTooltip(p.payload)} />
        {/* 투명 base(q1) + 보이는 박스(boxHeight) = stacked bar로 q1~q3 박스 */}
        <Bar dataKey="q1" stackId="box" fill="transparent" />
        <Bar dataKey="boxHeight" stackId="box" fill="var(--c-process)" fillOpacity={0.6}>
          {/* median 선 + min~max 수염을 ErrorBar로 */}
          <ErrorBar dataKey="whiskerHigh" width={4} stroke="var(--c-maintenance)" direction="y" />
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  )
}
```
> ErrorBar로 수염(min~max), stacked Bar(투명 q1 + 보이는 q3-q1)로 박스, tooltip에 5수치 전부.
> 정밀 박스플롯은 아니지만 "그룹별 분포 비교" 목적 충분 (D-확정). 정밀 SVG는 폴리싱 단계.
> 라벨 그룹 30+ 가드 → 백엔드가 상위 30만 줌. UI에 "상위 30개 그룹" 노트(others/n 있으면).

### 3-4. 나머지 7종 (간단 패턴)
```jsx
// Histogram — BarChart (bins 중점 계산)
const rows = data.counts.map((c, i) => ({ x: ((data.bins[i]+data.bins[i+1])/2).toFixed(2), count: c }))
// <BarChart data={rows}><Bar dataKey="count" fill="var(--c-process)" /></BarChart>

// FftSpectrum / RmsTrend — LineChart
// fft: data.freqs.map((f,i)=>({freq:f, mag:data.magnitude[i]}))  <Line dataKey="mag" dot={false} stroke="var(--c-maintenance)"/>

// ClassDistribution — BarChart (labels=x, counts=y, fill quality 초록)
// CorrelationBar — BarChart layout="vertical" (columns=y, values=x)
// Pareto — ComposedChart (Bar counts + Line cumulative_pct, 우측 YAxis yAxisId="pct")
// Scatter — ScatterChart (data.x[i],data.y[i] → [{x,y}])
```
각 차트: ResponsiveContainer 높이 ~280px, 공통 AXIS/GRID/TOOLTIP, function_axis 색 매핑.

### 3-5. ChartError / ChartFooter
```jsx
function ChartError({ label, message }) {
  return <div className="chart-card"><strong>{label || "차트"}</strong>
    <div className="chart-error">⚠ {message}</div></div>
}
function ChartFooter({ data }) {
  return (<div className="chart-footer muted">
    {data.others_count ? `+기타 ${data.others_count}개 ` : ""}
    {data.stats?.peak_freq ? `peak ≈ ${data.stats.peak_freq} Hz ` : ""}
    {data.stats?.mean != null ? `mean ${data.stats.mean.toFixed(2)} / std ${data.stats.std.toFixed(2)}` : ""}
  </div>)
}
```

---

## 4. AnalyzePage 통합 (skeleton 교체)

### 4-1. state + EDA 실행
```jsx
const [edaPlan, setEdaPlan] = useState(null)       // /plan 결과
const [edaCharts, setEdaCharts] = useState(null)   // /render 결과
const [edaLoading, setEdaLoading] = useState(false)
const [edaError, setEdaError] = useState(null)

async function runEda() {
  setEdaLoading(true); setEdaError(null)
  try {
    const plan = await post(`/analyze/${sid}/eda/plan`, {})
    if (!plan.available) { setEdaError(plan.reason || "EDA 불가"); return }
    setEdaPlan(plan)
    const rendered = await post(`/analyze/${sid}/eda/render`, { charts: plan.recommended_charts })
    setEdaCharts(rendered.charts)
  } catch (e) { setEdaError(e.message) }
  finally { setEdaLoading(false) }
}
```

### 4-2. skeleton 블록 교체 (129-160 대체)
```jsx
{/* 기존 eda-skeleton 자리 — EDA 실엔진으로 교체 */}
<section className="eda-charts">
  <h2>EDA 분석</h2>
  {!savedResult ? (
    <p className="muted">먼저 분석 목적을 선택하세요.</p>
  ) : (
    <>
      <button className="btn btn-primary" onClick={runEda} disabled={edaLoading}>
        {edaLoading ? "차트 추천·생성 중..." : "EDA 실행"}
      </button>
      {edaPlan?.llm_status === "failed" && (
        <div className="muted">※ LLM 추천 실패 — 기본 가이드 차트로 대체</div>
      )}
      {edaError && <div className="chart-error">⚠ {edaError}</div>}
      {edaCharts && (
        <div className="chart-grid">
          {edaCharts.map((c, i) => <ChartCard key={i} chart={c} sessionId={sid} />)}
        </div>
      )}
    </>
  )}

  {/* 자연어 EDA 카드 (3a-2) */}
  <FreeformEda sessionId={sid} />
</section>
```
> key_findings 표시는 제거(skeleton). 필요하면 profile 요약으로 대체 가능하나, 핵심은 차트.
> "다음 → Page 6" 링크(163-168)는 그대로 보존.

---

## 5. 자연어 EDA UI (3a-2 — 우리 핵심 가치 화면)

`frontend/src/step5_analyze/FreeformEda.jsx` (신규):
```jsx
export function FreeformEda({ sessionId }) {
  const [query, setQuery] = useState("")
  const [pending, setPending] = useState(null)   // awaiting_approval 코드
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function onRequest() {
    setBusy(true); setError(null); setResult(null); setPending(null)
    try {
      const r = await post(`/analyze/${sessionId}/eda/freeform`, { user_query: query })
      if (r.status === "awaiting_approval") setPending(r)
      else if (r.status === "rejected") setError(`거부됨: ${r.reason}`)
      else if (r.status === "llm_failed") setError(`LLM 실패: ${r.error}`)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function onApprove(approved) {
    setBusy(true)
    try {
      const r = await post(`/analyze/${sessionId}/eda/freeform/approve`, { approved })
      if (r.status === "executed") { setResult(r); setPending(null) }
      else if (r.status === "cancelled") setPending(null)
      else setError(r.reason || r.error || "실행 실패")
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="freeform-eda">
      <h3>자연어로 분석 요청</h3>
      <p className="muted">데이터에 대해 궁금한 걸 한국어로. AI가 분석 코드를 생성하고, 승인 후 실행합니다.</p>
      <div className="freeform-input">
        <input value={query} onChange={e => setQuery(e.target.value)}
               placeholder="예: FAIL 케이스만 골라서 분포 보여줘" disabled={busy} />
        <button className="btn" onClick={onRequest} disabled={busy || !query.trim()}>분석 요청</button>
      </div>

      {/* 코드 미리보기 + 승인 (ApprovalCard 발상 — AI가 짠 코드를 사람이 승인) */}
      {pending && (
        <div className="freeform-approve">
          <div className="muted">AI가 생성한 분석 코드 (승인하면 실행):</div>
          <pre className="code-preview">{pending.code}</pre>
          <div className="freeform-actions">
            <button className="btn btn-primary" onClick={() => onApprove(true)} disabled={busy}>승인 후 실행</button>
            <button className="btn" onClick={() => onApprove(false)} disabled={busy}>취소</button>
          </div>
        </div>
      )}

      {error && <div className="chart-error">⚠ {error}</div>}
      {result && <FreeformResult result={result} />}
    </div>
  )
}

function FreeformResult({ result }) {
  // result.result = dict/int/list 등. result_type에 따라 표/값 표시
  return (
    <div className="freeform-result">
      <div className="muted">실행 결과 (lineage: {result.lineage_id?.slice(0,8)}):</div>
      <pre className="result-json">{JSON.stringify(result.result, null, 2)}</pre>
    </div>
  )
}
```
> 코드 미리보기(monospace) → 승인/취소 = 우리 "AI가 코드를 짜되 사람이 승인 + 추적" 철학의 화면.
> lineage_id 표시 = "이 분석이 기록됐다"를 사용자에게 보여줌 (SI 신뢰).

---

## 6. styles.css 추가 (신규 클래스만 — 기존 수정 X)
```css
/* EDA 차트 (STEP 3b) — 기존 다크 톤 유지 */
.eda-charts { margin-top: 24px; background: var(--panel); padding: 16px 18px; border-radius: 8px; }
.chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 12px; margin-top: 12px; }
.chart-card { background: var(--panel-2); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
.chart-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.chart-footer { font-size: 11px; margin-top: 6px; }
.chart-error { color: var(--c-maintenance); font-size: 13px; padding: 8px; }
.btn-sm { font-size: 11px; padding: 2px 8px; }
/* AI 요약 */
.chart-summary { margin-top: 8px; font-size: 12px; border-top: 1px solid var(--border); padding-top: 8px; }
/* 자연어 EDA */
.freeform-eda { margin-top: 20px; border-top: 1px solid var(--border); padding-top: 16px; }
.freeform-input { display: flex; gap: 8px; margin-top: 8px; }
.freeform-input input { flex: 1; background: var(--panel-2); border: 1px solid var(--border);
  color: var(--text); padding: 8px; border-radius: 6px; }
.freeform-approve { margin-top: 12px; background: var(--panel-2); padding: 12px; border-radius: 6px;
  border-left: 3px solid var(--c-maintenance); }   /* L2 톤 — 승인 필요 */
.code-preview { background: var(--bg); padding: 10px; border-radius: 4px; font-family: monospace;
  font-size: 12px; overflow-x: auto; color: var(--text); }
.freeform-actions { display: flex; gap: 8px; margin-top: 10px; }
.freeform-result { margin-top: 12px; }
.result-json { background: var(--bg); padding: 10px; border-radius: 4px; font-family: monospace;
  font-size: 12px; overflow-x: auto; }
```

---

## 7. variable_index 보강 (진단에서 발견한 누락 정리)
STEP 3a 본문 섹션이 variable_index에 누락됨(풋터 1줄만). STEP 2a/2b 패턴에 맞춰 보강 + STEP 3b 추가:
- [ ] `### STEP 3a EDA 실엔진 (D-118~D-130)` 본문 섹션 추가:
  5 엔드포인트(/eda/plan·render·summary·freeform·freeform/approve) 표 + agents/eda/ 모듈
  (chart_types/eda_engine/code_sandbox) + 새 세션 키(eda_plan/eda_results/pending_eda_code 등)
  + CHART_TYPES/CHART_TYPE_IDS/FUNCTION_CHART_GUIDE/ALLOWED_NODES 상수
- [ ] `### STEP 3b EDA 차트 UI (D-131~)` 본문 섹션 추가:
  ChartCard/8 차트 컴포넌트/FreeformEda + recharts 의존성 + 신규 styles 클래스

---

## 8. 절대 하지 말 것
- ❌ 백엔드(STEP 3a) 변경 (프론트만)
- ❌ eda-skeleton 외 영역 변경 (/select, QuestionRadioGroup, Page6 링크 보존 — 회귀 0)
- ❌ 다른 페이지(1·2·3·4·6) 변경
- ❌ styles.css 기존 클래스 수정 (신규만 추가)
- ❌ LLM 요약 일괄 자동 호출 (사용자 클릭 시만 — e4b 4초/요청)
- ❌ 자연어 EDA에서 승인 없이 결과 표시 (반드시 코드 미리보기 → 승인 → 실행)
- ❌ recharts 외 차트 라이브러리 추가 (chart.js/d3 등 X)
- ❌ 문서 별표(★) (코드 주석 ★는 OK)
- ❌ git checkout/reset/rebase (되돌리기 금지). main 직접 push 금지

---

## 9. 검증 (완료 기준 — 사용자에게 보고)

### 차트 렌더 (3b-1)
- [ ] `npm i recharts` 후 build 성공
- [ ] /select 후 "EDA 실행" 버튼 → /plan → /render → 차트 렌더
- [ ] 차트 8종 각각 렌더 확인 (synthetic 또는 실데이터):
      histogram(bar), boxplot(ComposedChart+ErrorBar), fft(line), rms(line),
      class_distribution(bar), correlation(horizontal bar), pareto(bar+line dual-Y), scatter
- [ ] 다크 톤 적용 (축/격자/툴팁 var 색상)
- [ ] 에러 분기: 항목 error/data.error → 에러 박스 (차트 영역 비움)
- [ ] others_count "+기타 N개", peak_freq "peak ≈", histogram mean/std 칩
- [ ] LLM 추천 실패 → 폴백 차트 + "기본 가이드" 안내

### AI 요약 (3b-2)
- [ ] 차트 "AI 요약" 버튼 → /eda/summary → summary + key_points 표시 (클릭 시만)
- [ ] 요약 LLM 실패 → 에러 표시 (graceful)

### 자연어 EDA (3b-3 — 핵심)
- [ ] 입력 "FAIL 케이스만 분포 보여줘" → /freeform → 코드 미리보기 표시
- [ ] "승인 후 실행" → /freeform/approve → result 표시 + lineage_id
- [ ] "취소" → 코드 사라짐 (실행 안 함)
- [ ] AST 거부(악성 입력) → "거부됨" 메시지
- [ ] 코드 미리보기는 monospace, 승인 전 실행 안 됨

### 회귀
- [ ] /select 흐름 보존 (분석 목적 선택 → function_axis)
- [ ] QuestionRadioGroup, "다음→Page 6" 링크 보존
- [ ] 다른 페이지(1·2·3·4·6) 영향 0
- [ ] styles.css 기존 클래스 미변경 (신규만)

### 문서
- [ ] decisions.md D-131~ (STEP 3b: recharts, ChartCard, BoxPlot ComposedChart, FreeformEda UI)
- [ ] variable_index: STEP 3a 본문 섹션 보강 + STEP 3b 섹션 추가
- [ ] 별표(★) 0건

---

## 10. 작업 흐름 + 커밋

### 작업 흐름
1. 0장 (브랜치·폴더 확인 + 컨텍스트)
2. `npm i recharts`
3. 차트 컴포넌트(charts/ 8종 + ChartCard) → AnalyzePage skeleton 교체 → FreeformEda → styles
4. variable_index 보강 (STEP 3a + 3b)
5. **전체 완성 후 검증** (9장 — 브라우저 차트 8종 + 자연어 EDA + 회귀)
6. **검증 후 논리 단위 커밋** (feature/step3-eda-ml 브랜치, checkout/reset 금지):
   ```
   feat(STEP3b): add recharts EDA chart components (8 types + ComposedChart boxplot)
   feat(STEP3b): replace AnalyzePage skeleton with EDA charts + freeform NL EDA UI
   feat(STEP3b): add EDA chart styles (dark tone, existing tokens)
   docs(STEP3b): record D-131~ chart UI + variable_index STEP 3a/3b sections
   ```
   - 커밋 메시지·본문 설명은 작성하되, **Co-Authored-By는 settings로 제거됨** (작성자 sbg0700 확인).
7. **push는 claude.ai 검증 후** (feature/step3-eda-ml로). push 전 사용자 확인.

### 완료 후 claude.ai에 보고
- 9장 체크리스트 (3b-1/2/3)
- ChartCard + BoxPlot(ComposedChart) + FreeformEda 코드
- **브라우저 스크린샷**: 차트 그리드 (8종 중 렌더된 것) + 자연어 EDA 코드 미리보기 + 결과
- 자연어 EDA end-to-end (입력 → 코드 → 승인 → 결과 + lineage)
- 회귀 0 (다른 페이지 + /select)
- `git branch` + `git log --oneline` + `git log --format='%an <%ae>' -1` (sbg0700 + Co-Author 없는지 확인)

---

## 부록 — 헌법 정합 (왜 이 설계)
- **3a 백엔드를 화면으로**: LLM 판단(차트 추천) + 코드 실행(결정론 데이터)이 recharts로 시각화.
- **자연어 EDA 화면 = 시스템 정체성**: "AI가 코드를 짠다"가 코드 미리보기 + 승인 + lineage 표시로 완성.
  사용자가 AI 생성 코드를 보고 승인 → "AI 자율 + 사람 통제 + 추적"이 눈에 보임 (SI 신뢰).
- **recharts = 데이터 전송 0 무관**: 로컬 번들, 런타임 외부 호출 0 (D-118). UI 라이브러리 제한 없음.
- **회귀 안전**: skeleton 한 블록만 교체. /select·다른 페이지 불변.
- **BoxPlot ComposedChart**: recharts 일관성 유지(SVG 자작 회피). 정밀 박스플롯은 폴리싱 단계.
- **LLM 클릭 호출**: /summary는 사용자 클릭 시만 (e4b 4초 — 일괄 자동 호출하면 느림). LLM 절제.
