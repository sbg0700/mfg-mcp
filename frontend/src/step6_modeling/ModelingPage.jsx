import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { get } from '../api.js'
import Toast from '../components/Toast.jsx'
import ModelCard from './ModelCard.jsx'
import TrainModal from './TrainModal.jsx'

// Page 6 — 모델링 (spec-2 Part 7).
// 추천(LLM, recommended_models 풀에서 fit_score)은 실동작.
// STEP 3c 학습 실엔진(task 분기 + 화이트리스트 + 폴링 + lineage) + STEP 3d UI.
export default function ModelingPage() {
  const [params] = useSearchParams()
  const sid = params.get('session') || ''
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadErr, setLoadErr] = useState('')
  const [toast, setToast] = useState('')
  const [trainModel, setTrainModel] = useState(null)

  useEffect(() => {
    if (!sid) return
    setLoading(true)
    get(`/model/${sid}/recommend`)
      .then((r) => setData(r))
      .catch((e) => setLoadErr(e.message || '모델 추천 로드 실패'))
      .finally(() => setLoading(false))
  }, [sid])

  if (!sid) return <div>세션 ID가 없습니다. <a href="/">처음으로</a></div>
  if (loadErr) return <div className="error-text">⚠ {loadErr}</div>
  if (loading) return <div className="muted">LLM이 모델을 추천하는 중… (10~30초)</div>

  const recs = data?.recommendations || []
  const available = data?.available_models || []
  const executable = recs.filter((r) => !r.advisory_only)
  const advisory = recs.filter((r) => r.advisory_only)
  // 추천에 나오지 않은 available 모델 (참고용 풀)
  const otherAvailable = available
    .filter((a) => !recs.find((r) => r.name === a.name))

  return (
    <div>
      <h1>모델링 — 추천</h1>
      <p className="muted">
        AggregatedContext(key_findings)와 분석 목적
        {data?.user_purpose && <> (<code>{data.user_purpose}</code>)</>}을 보고
        LLM이 <code>recommended_models</code> 풀 안에서 적합도(fit_score 1~5)를 매깁니다.
        풀 외 추천 / fit_score 1~5 외 값은 환각 방어 코드가 제거합니다 (D-92).
      </p>

      {data?.llm_status === 'failed' ? (
        <div className="error-text" style={{ marginBottom: 12 }}>
          ⚠ LLM 응답 실패 — {data.llm_error || '알 수 없는 오류'}
          {data.model_used && (
            <div className="muted" style={{ fontSize: 12 }}>
              시도 모델: <code>{data.model_used}</code> · ollama 컨테이너/모델 pull/타임아웃 확인
            </div>
          )}
        </div>
      ) : data?.error ? (
        <div className="error-text" style={{ marginBottom: 12 }}>
          ⚠ LLM 응답 오류: {data.error}
        </div>
      ) : null}
      {data?.llm_status === 'ok' && data?.model_used && (
        <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          (모델: <code>{data.model_used}</code>)
        </div>
      )}
      {data?.note && (
        <div className="muted" style={{ marginBottom: 12 }}>{data.note}</div>
      )}

      <section className="model-section">
        <h2>실행 가능 모델 ({executable.length})</h2>
        {executable.length === 0 ? (
          <div className="muted">현재 환경에서 실행 가능한 추천 모델이 없습니다.</div>
        ) : (
          <div className="model-list">
            {executable.map((rec) => (
              <ModelCard key={rec.name} rec={rec} onTrain={setTrainModel} />
            ))}
          </div>
        )}
      </section>

      {advisory.length > 0 && (
        <section className="model-section">
          <h2>권고만 (실행 불가) — VRAM 초과 등</h2>
          <div className="model-list">
            {advisory.map((rec) => (
              <ModelCard key={rec.name} rec={rec} onTrain={() => {}} />
            ))}
          </div>
        </section>
      )}

      {otherAvailable.length > 0 && (
        <section className="model-section other-available">
          <h3>추천에 나오지 않은 available 풀 ({otherAvailable.length})</h3>
          <ul className="muted" style={{ fontSize: 13 }}>
            {otherAvailable.map((m) => (
              <li key={`${m.name}.${m.from_node}`}>
                <code>{m.name}</code> ({m.task} · {m.when} · {m.from_node})
                {m.advisory_only && ' [advisory_only]'}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div style={{ marginTop: 24 }}>
        <Link to={`/pipeline/run?session=${sid}`} className="btn">
          ← Page 4로 돌아가기
        </Link>
      </div>

      <TrainModal model={trainModel} sessionId={sid} onClose={() => setTrainModel(null)} />
      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  )
}
