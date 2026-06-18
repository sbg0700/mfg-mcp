import { useState, useEffect, useRef } from 'react'
import { get, post } from '../api.js'
import ConfusionTable from './charts/ConfusionTable.jsx'
// 3b 차트 재사용 (ChartCard 디스패처는 EDA 전용 — D-132 contract 보호. 컴포넌트만 import)
import Histogram from '../step5_analyze/charts/Histogram.jsx'
import CorrelationBar from '../step5_analyze/charts/CorrelationBar.jsx'

// STEP 3d TrainModal — TrainSkeletonModal 교체.
// task 분기:
//   - 지도(regression/classification): 타겟 컬럼 드롭다운 + params(추후) + confusion/metrics
//   - 비지도(anomaly, IsolationForest): 타겟 없음 + contamination 슬라이더 + score 분포
// 폴링: /train → 1초 /status → /result. setInterval cleanup 필수.
//
// props: { model: rec, sessionId, onClose }
//   rec = {name, task, fit_score, when, from_node, rationale_ko?, advisory_only}

function Kpi({ label, value, accent }) {
  return (
    <div className={`kpi-card ${accent ? 'kpi-accent' : ''}`}>
      <div className="kpi-label muted">{label}</div>
      <div className="kpi-value">{value ?? '—'}</div>
    </div>
  )
}

function TrainResult({ result, onClose, onRetrain }) {
  const r = result?.result || {}
  const task = r.task
  const m = r.metrics || {}
  return (
    <div className="train-result">
      <h3>학습 완료 — {r.model_name} <span className="muted" style={{ fontWeight: 400 }}>({task})</span></h3>

      <div className="metrics-grid">
        {task === 'regression' && (
          <>
            <Kpi label="R²" value={m.r2 != null ? Number(m.r2).toFixed(3) : null} accent />
            <Kpi label="RMSE" value={m.rmse != null ? Number(m.rmse).toFixed(2) : null} />
            <Kpi label="학습/검증" value={`${m.n_train ?? '—'} / ${m.n_test ?? '—'}`} />
          </>
        )}
        {task === 'classification' && (
          <>
            <Kpi label="Accuracy" value={m.accuracy != null ? (m.accuracy * 100).toFixed(1) + '%' : null} accent />
            <Kpi label="F1" value={m.f1 != null ? Number(m.f1).toFixed(3) : null} />
            {m.auc != null && <Kpi label="AUC" value={Number(m.auc).toFixed(3)} />}
            <Kpi label="학습/검증" value={`${m.n_train ?? '—'} / ${m.n_test ?? '—'}`} />
          </>
        )}
        {task === 'anomaly' && (
          <>
            <Kpi label="전체" value={m.n_total ?? '—'} />
            <Kpi label="이상치" value={m.n_anomaly ?? '—'} accent />
            <Kpi label="이상 비율" value={m.anomaly_ratio != null ? (m.anomaly_ratio * 100).toFixed(1) + '%' : null} />
            <Kpi label="contamination" value={m.contamination != null ? Number(m.contamination).toFixed(3) : null} />
          </>
        )}
      </div>

      {/* 분류: confusion matrix */}
      {r.confusion_matrix && (
        <ConfusionTable
          labels={r.confusion_matrix.labels}
          matrix={r.confusion_matrix.matrix}
        />
      )}

      {/* 비지도: score 분포 — Histogram 재사용 (data.bins/counts 1:1) */}
      {r.score_distribution && (
        <div className="train-chart-block">
          <div className="muted confusion-title">Anomaly Score 분포 (IsolationForest)</div>
          <Histogram data={{
            column: 'anomaly_score',
            bins: r.score_distribution.bins,
            counts: r.score_distribution.counts,
          }} />
        </div>
      )}

      {/* RF/XGB: feature importance — CorrelationBar 재사용 (어댑터) */}
      {Array.isArray(r.feature_importance) && r.feature_importance.length > 0 && (
        <div className="train-chart-block">
          <div className="muted confusion-title">Top Feature Importance</div>
          <CorrelationBar data={{
            target_column: '중요도',
            columns: r.feature_importance.map((x) => x.feature),
            values: r.feature_importance.map((x) => x.importance),
          }} />
        </div>
      )}

      {/* 조정 알림 (화이트리스트 clamp + OOM 가드 notices) */}
      {Array.isArray(r.notices) && r.notices.length > 0 && (
        <div className="train-notices">
          <strong>안전 조정·가드 알림</strong>
          <ul>
            {r.notices.map((n, i) => <li key={i} className="muted">{n}</li>)}
          </ul>
        </div>
      )}

      {/* lineage (감사 — SI 컴플라이언스) */}
      <div className="muted train-lineage">
        lineage: <code>{(result.lineage_id || '').slice(0, 8) || '—'}</code> · 학습 결과 추적 기록됨
      </div>

      <div className="modal-actions">
        <button className="btn" onClick={onRetrain}>다시 학습</button>
        <button className="btn btn-primary" onClick={onClose}>완료</button>
      </div>
    </div>
  )
}

export default function TrainModal({ model, sessionId, onClose }) {
  // ★Hooks 규칙: 모든 useState/useEffect는 early return 전에 호출되어야 한다.
  //   ModelingPage가 model=null → TrainModal로 항상 렌더하므로, null일 때는
  //   hooks 호출 후 마지막에 return null. (React "static flag missing" 경고 방지)
  const supervised = model?.task === 'regression' || model?.task === 'classification'

  const [columns, setColumns] = useState([])
  const [profileErr, setProfileErr] = useState('')
  const [target, setTarget] = useState('')
  const [contamination, setContamination] = useState(0.05)
  const [validateInfo, setValidateInfo] = useState(null)
  const [job, setJob] = useState(null)         // {job_id, status}
  const [result, setResult] = useState(null)   // /train/result completed payload
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const pollRef = useRef(null)

  // 타겟 드롭다운 — 지도 학습에만 필요. /data_profile 호출 (LLM 0).
  useEffect(() => {
    if (!model || !supervised) return
    let cancelled = false
    get(`/model/${sessionId}/data_profile`)
      .then((r) => {
        if (cancelled) return
        const cols = r.columns || []
        const candidates = model.task === 'regression'
          ? cols.filter((c) => c.is_numeric)                                // 회귀: 숫자
          : cols.filter((c) => !c.is_numeric || c.n_unique <= 10)           // 분류: 저카디널리티/범주
        setColumns(candidates)
        if (!r.available) setProfileErr(r.reason || '데이터 프로파일 불가')
      })
      .catch((e) => { if (!cancelled) setProfileErr(e.message || '컬럼 로드 실패') })
    return () => { cancelled = true }
  }, [model, sessionId, supervised, model?.task])

  // 폴링 cleanup — 모달 닫힘/언마운트 시 setInterval 정리 (메모리 누수 방지)
  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [])

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  function buildReq() {
    return {
      model_name: model.name,
      target_column: supervised ? (target || null) : null,
      params: {},  // 기본값 — 사용자 파라미터 입력은 폴리싱 단계. 백엔드 화이트리스트가 보정
      contamination: supervised ? 0.05 : contamination,
    }
  }

  async function onValidate() {
    if (busy) return
    setBusy(true); setError(null); setValidateInfo(null)
    try {
      const r = await post(`/model/${sessionId}/train/validate`, buildReq())
      setValidateInfo(r)
    } catch (e) {
      setError(e.message || '파라미터 확인 실패')
    } finally {
      setBusy(false)
    }
  }

  async function onTrain() {
    if (busy) return
    setBusy(true); setError(null); setResult(null); setJob(null)
    try {
      const r = await post(`/model/${sessionId}/train`, buildReq())
      setJob({ job_id: r.job_id, status: 'running' })
      startPolling(r.job_id)
    } catch (e) {
      setError(e.message || '학습 시작 실패')
      setBusy(false)
    }
  }

  function startPolling(jobId) {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const s = await get(`/model/${sessionId}/train/status?job_id=${jobId}`)
        setJob({ job_id: jobId, status: s.status })
        if (s.status !== 'running') {
          stopPolling()
          const res = await get(`/model/${sessionId}/train/result?job_id=${jobId}`)
          if (res.status === 'completed') {
            setResult(res)
          } else {
            setError(res.error || s.error || '학습 실패')
          }
          setBusy(false)
        }
      } catch (e) {
        stopPolling()
        setError(e.message || '폴링 실패')
        setBusy(false)
      }
    }, 1000)
  }

  function onRetrain() {
    stopPolling()
    setResult(null)
    setJob(null)
    setError(null)
    setValidateInfo(null)
  }

  function closeAndStop() {
    stopPolling()
    onClose()
  }

  if (!model) return null   // 모든 hooks 호출 후의 안전 null 가드

  const canTrain = !busy && (!supervised || !!target)

  return (
    <div className="modal-backdrop" onClick={closeAndStop}>
      <div className="modal train-modal" onClick={(e) => e.stopPropagation()}>
        <h2>
          학습 — {model.name}{' '}
          <span className="muted" style={{ fontSize: 13, fontWeight: 400 }}>
            (fit {model.fit_score}/5, task {model.task})
          </span>
        </h2>

        {!result && (
          <>
            {supervised ? (
              <div className="train-field">
                <label htmlFor="train-target">타겟 컬럼 {model.task === 'regression' ? '(숫자)' : '(저카디널리티)'}</label>
                <select
                  id="train-target"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  disabled={busy || columns.length === 0}
                >
                  <option value="">선택...</option>
                  {columns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name} ({c.is_numeric ? '숫자' : `범주 ${c.n_unique}종`})
                    </option>
                  ))}
                </select>
                {profileErr && <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>⚠ {profileErr}</p>}
                {!profileErr && columns.length === 0 && (
                  <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>적합 컬럼이 없습니다.</p>
                )}
              </div>
            ) : (
              <div className="train-field">
                <label htmlFor="train-contam">
                  이상 비율 (contamination): <code>{contamination.toFixed(2)}</code>
                </label>
                <input
                  id="train-contam"
                  type="range"
                  min="0.01"
                  max="0.5"
                  step="0.01"
                  value={contamination}
                  disabled={busy}
                  onChange={(e) => setContamination(parseFloat(e.target.value))}
                />
                <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                  데이터에서 이상치로 가정할 비율 (IsolationForest 결정 경계)
                </p>
              </div>
            )}

            {validateInfo && (
              <div className="train-notices">
                <strong>파라미터 안전 확인</strong>
                {validateInfo.notices && validateInfo.notices.length > 0 ? (
                  <ul>
                    {validateInfo.notices.map((n, i) => <li key={i} className="muted">{n}</li>)}
                  </ul>
                ) : (
                  <p className="muted" style={{ fontSize: 12 }}>조정 사항 없음. 안전 범위 통과.</p>
                )}
                <p className="muted" style={{ fontSize: 11, marginTop: 4 }}>
                  safe_params: <code>{JSON.stringify(validateInfo.safe_params)}</code>
                </p>
              </div>
            )}

            <div className="modal-actions">
              <button className="btn" onClick={onValidate} disabled={!canTrain}>
                파라미터 확인
              </button>
              <button className="btn btn-primary" onClick={onTrain} disabled={!canTrain}>
                {busy && job?.status === 'running' ? '학습 중…' : '학습 시작'}
              </button>
              <button className="btn" onClick={closeAndStop} disabled={busy}>
                닫기
              </button>
            </div>

            {job?.status === 'running' && (
              <div className="muted train-progress">⏳ 학습 진행 중…</div>
            )}
          </>
        )}

        {error && <div className="chart-error" style={{ marginTop: 12 }}>⚠ {error}</div>}

        {result && (
          <TrainResult result={result} onClose={closeAndStop} onRetrain={onRetrain} />
        )}
      </div>
    </div>
  )
}
