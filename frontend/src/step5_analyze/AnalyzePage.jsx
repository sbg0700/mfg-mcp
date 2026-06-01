import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { get, post } from '../api.js'
import Toast from '../components/Toast.jsx'
import QuestionRadioGroup from './QuestionRadioGroup.jsx'

// Page 5 — 분석목적 + EDA (spec-2 Part 6).
// 추천(LLM)·선택은 실동작, EDA 차트는 골격 (실제 차트는 STEP 2·3).
//   - GET /analyze/{id}/questions → 추천 + 전체 옵션
//   - POST /analyze/{id}/select   → user_intent 갱신 + function_axis
//   - EDA 영역은 AggregatedContext.key_findings 텍스트로만 (실차트는 STEP 2·3)
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
        }
      })
      .catch((e) => setLoadErr(e.message || '분석 데이터 로드 실패'))
      .finally(() => setLoading(false))
  }, [sid])

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
        4단 표준화 결과(AggregatedContext)를 LLM이 보고 분석 목적을 추천합니다.
        <code>available_options</code> 외 추천은 환각 방어 코드가 제거합니다 (D-91).
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

      <section className="eda-skeleton">
        <h2>EDA 결과 (골격)</h2>
        <p className="muted">
          1B-2b 단계에서 결정론으로 추출된 주요 발견 ({kf.length}개)을 표시합니다.
          실제 EDA 차트(박스플롯·히스토그램·FFT 등)는 다음 단계(STEP 2·3)에서 실데이터로 동적 생성됩니다.
        </p>
        {kf.length === 0 ? (
          <div className="muted">findings 없음 (Page 4 표준화 결과 비어있음)</div>
        ) : (
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
        )}
        <div className="muted skeleton-note">
          ※ 차트 영역은 STEP 2·3에서 recharts 등으로 실데이터 시각화 예정.
        </div>
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
