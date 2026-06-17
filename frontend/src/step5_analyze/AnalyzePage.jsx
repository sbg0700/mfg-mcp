import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { get, post } from '../api.js'
import Toast from '../components/Toast.jsx'
import QuestionRadioGroup from './QuestionRadioGroup.jsx'
import ChartCard from './charts/ChartCard.jsx'
import FreeformEda from './FreeformEda.jsx'

// Page 5 — 분석목적 + EDA (spec-2 Part 6).
// 추천(LLM)·선택은 실동작. EDA는 STEP 3a 실엔진(LLM 판단 + 결정론 차트) + STEP 3b recharts.
//   - GET /analyze/{id}/questions → 추천 + 전체 옵션
//   - POST /analyze/{id}/select   → user_intent 갱신 + function_axis
//   - POST /analyze/{id}/eda/plan → LLM 차트 추천 (사용자 클릭 시)
//   - POST /analyze/{id}/eda/render → 결정론 차트 데이터
//   - POST /analyze/{id}/eda/summary → 한국어 요약 (차트별 클릭 시)
//   - POST /analyze/{id}/eda/freeform(+/approve) → 자연어 코드 EDA
const FUNCTION_KO = {
  process: '공정 (Process)',
  quality: '품질 (Quality)',
  maintenance: '유지보전 (Maintenance)',
  reference: '참조 (Reference)',
}

export default function AnalyzePage() {
  const [params] = useSearchParams()
  const sid = params.get('session') || ''
  const [questions, setQuestions] = useState(null)
  const [aggregated, setAggregated] = useState(null)
  const [selected, setSelected] = useState('')
  const [freeInput, setFreeInput] = useState('')
  const [savedResult, setSavedResult] = useState(null)
  const [toast, setToast] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [loadErr, setLoadErr] = useState('')
  // STEP 3b — EDA 실행 상태 (사용자 클릭 모델, D-131)
  const [edaPlan, setEdaPlan] = useState(null)
  const [edaCharts, setEdaCharts] = useState(null)
  const [edaLoading, setEdaLoading] = useState(false)
  const [edaError, setEdaError] = useState('')

  useEffect(() => {
    if (!sid) return
    setLoading(true)
    Promise.all([
      get(`/analyze/${sid}/questions`),
      get(`/aggregate_context/${sid}`).catch(() => null),
    ])
      .then(([qs, ctx]) => {
        setQuestions(qs)
        setAggregated(ctx)
        // 이미 저장된 분석목적이 있으면 복원
        const prior = ctx?.user_intent?.analysis_purpose
        if (prior) {
          setSelected(prior)
          setFreeInput(ctx.user_intent.free_input || '')
          // STEP 3b: savedResult도 복원 — EDA 실행 버튼이 새로고침 후에도 보이게
          setSavedResult({
            analysis_purpose: prior,
            function_axis: ctx.user_intent.function_axis_focus,
            free_input: ctx.user_intent.free_input || null,
          })
        }
      })
      .catch((e) => setLoadErr(e.message || '분석 데이터 로드 실패'))
      .finally(() => setLoading(false))
  }, [sid])

  // STEP 3b — "EDA 실행" 버튼: /plan → /render 순차 호출.
  // 자동 호출 X (e4b 9초 LLM 호출 + render — 사용자 명시 클릭 모델).
  async function runEda() {
    if (edaLoading) return
    setEdaLoading(true); setEdaError(''); setEdaCharts(null); setEdaPlan(null)
    try {
      const plan = await post(`/analyze/${sid}/eda/plan`, {})
      if (!plan.available) {
        setEdaError(plan.reason || 'EDA 대상 없음')
        return
      }
      setEdaPlan(plan)
      const rendered = await post(`/analyze/${sid}/eda/render`, {
        charts: plan.recommended_charts || [],
      })
      setEdaCharts(rendered.charts || [])
    } catch (e) {
      setEdaError(e.message || 'EDA 실행 실패')
    } finally {
      setEdaLoading(false)
    }
  }

  async function onSubmit() {
    if (!selected) {
      setToast('분석 목적을 1개 선택하세요.')
      return
    }
    setSubmitting(true)
    try {
      const r = await post(`/analyze/${sid}/select`, {
        analysis_purpose: selected,
        free_input: freeInput || null,
      })
      setSavedResult(r)
      setToast(`저장됨. function_axis = ${r.function_axis}`)
    } catch (e) {
      setToast(`저장 실패: ${e.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  if (!sid) return <div>세션 ID가 없습니다. <a href="/">처음으로</a></div>
  if (loadErr) return <div className="error-text">⚠ {loadErr}</div>
  if (loading) return <div className="muted">LLM이 분석 목적을 추천하는 중… (10~20초)</div>

  const kf = aggregated?.key_findings || []

  return (
    <div>
      <h1>분석 목적</h1>
      <p className="muted">
        표준화 결과를 보고 분석 목적을 추천합니다.
        허용 목록 밖의 추천은 환각 방어 코드가 자동으로 걸러냅니다.
      </p>

      {questions?.llm_status === 'failed' ? (
        <div className="error-text" style={{ marginBottom: 12 }}>
          ⚠ LLM 응답 실패 — {questions.llm_error || '알 수 없는 오류'}
          {questions.model_used && (
            <div className="muted" style={{ fontSize: 12 }}>
              시도 모델: <code>{questions.model_used}</code> · ollama 컨테이너/모델 pull/타임아웃 확인
            </div>
          )}
        </div>
      ) : questions?.error ? (
        <div className="error-text" style={{ marginBottom: 12 }}>
          ⚠ LLM 응답 오류: {questions.error}
        </div>
      ) : null}
      {questions?.llm_status === 'ok' && questions?.model_used && (
        <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          (모델: <code>{questions.model_used}</code>)
        </div>
      )}

      <QuestionRadioGroup
        recommendations={questions?.recommendations || []}
        allOptions={questions?.all_options || []}
        selected={selected}
        onSelect={setSelected}
        freeInput={freeInput}
        onFreeInput={setFreeInput}
      />

      <div style={{ marginTop: 16, textAlign: 'right' }}>
        <button className="btn btn-primary" onClick={onSubmit} disabled={submitting || !selected}>
          {submitting ? '저장 중…' : '선택 저장 (function_axis 결정)'}
        </button>
      </div>

      {savedResult && (
        <div className="saved-result">
          저장됨: analysis_purpose = <code>{savedResult.analysis_purpose}</code>,
          function_axis = <strong>{FUNCTION_KO[savedResult.function_axis] || savedResult.function_axis}</strong>
        </div>
      )}

      <section className="eda-charts">
        <h2>EDA 분석</h2>
        {!savedResult ? (
          <p className="muted">먼저 위에서 분석 목적을 선택하세요. function_axis가 결정돼야 LLM이 적합한 차트를 추천합니다.</p>
        ) : (
          <>
            <div className="eda-actions">
              <button className="btn btn-primary" onClick={runEda} disabled={edaLoading}>
                {edaLoading ? '차트 추천·생성 중…' : (edaCharts ? 'EDA 재실행' : 'EDA 실행')}
              </button>
              {edaPlan?.llm_status === 'failed' && (
                <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
                  ※ LLM 추천 실패 — function 기본 가이드로 폴백
                </span>
              )}
              {edaPlan?.model_used && (
                <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>
                  (모델: <code>{edaPlan.model_used}</code>, dataset: <code>{edaPlan.dataset_id}</code>)
                </span>
              )}
            </div>
            {edaError && <div className="chart-error">⚠ {edaError}</div>}
            {edaCharts && edaCharts.length === 0 && (
              <div className="muted" style={{ marginTop: 12 }}>추천된 차트가 없습니다. function_axis와 modality 조합을 확인하세요.</div>
            )}
            {edaCharts && edaCharts.length > 0 && (
              <div className="chart-grid">
                {edaCharts.map((c, i) => <ChartCard key={i} chart={c} sessionId={sid} />)}
              </div>
            )}
          </>
        )}

        <FreeformEda sessionId={sid} />

        {kf.length > 0 && (
          <details className="findings-details">
            <summary className="muted">키 핀딩 ({kf.length}개) — 1B-2b 결정론 추출</summary>
            <ul className="findings-list">
              {kf.map((f, i) => (
                <li key={i} className="finding-row">
                  <span
                    className="severity-tag"
                    style={{
                      background:
                        f.severity === 'high' ? '#dc2626' :
                        f.severity === 'medium' ? '#f59e0b' : '#64748b',
                    }}
                  >
                    {f.severity}
                  </span>
                  <span className="finding-type muted">{f.type}</span>
                  <span className="finding-detail">{f.detail}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <Link
          to={`/pipeline/model?session=${sid}`}
          className="btn btn-primary"
        >
          다음 → (Page 6 모델링)
        </Link>
      </div>

      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  )
}
