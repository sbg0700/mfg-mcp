import { useEffect, useState, useMemo } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { get, post } from '../api.js'
import Toast from '../components/Toast.jsx'
import ApprovalCard from './ApprovalCard.jsx'
import AlarmBanner from './AlarmBanner.jsx'
import FindingsList from './FindingsList.jsx'

// Page 4 — 표준화 진행/승인 (spec-2 Part 5).
// 폴링형(D-51): execute_pipeline 응답이 곧 상태. GET status는 새로고침/복원에만 사용.
//   ready/structured/created → "실행" 버튼
//   running                  → 실행 중 표시 (응답 대기)
//   awaiting_approval        → 승인 카드 (pending_steps)
//   completed                → aggregated_context (key_findings 등) 표시
//   error                    → pre_validation blocking 사유 표시
export default function StandardizePage() {
  const [params] = useSearchParams()
  const sid = params.get('session') || ''
  const [view, setView] = useState(null)        // public_view 형태 (status, pending, alarms, ...)
  const [aggregated, setAggregated] = useState(null)
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState('')
  const [loadErr, setLoadErr] = useState('')
  const [dismissedAlarms, setDismissedAlarms] = useState([])
  // STEP 2b (D-110): 옵션 카드 선택 상태 — {step_key: option_id}. ApprovalCard에 전달.
  const [selectedOptions, setSelectedOptions] = useState({})

  // 진입 시 GET /sessions/{id}로 복원 — 이미 completed면 aggregated_context 같이 가져오기
  useEffect(() => {
    if (!sid) return
    refresh().catch((e) => setLoadErr(e.message || '세션 로드 실패'))
  }, [sid])

  async function refresh() {
    const sess = await get(`/sessions/${sid}`)
    setView(sess)
    if (sess.status === 'completed') {
      try {
        const ctx = await get(`/aggregate_context/${sid}`)
        setAggregated(ctx)
      } catch (_) { /* 결정론이라 다음 호출 때 재시도 */ }
    } else {
      setAggregated(null)
    }
  }

  async function onRun() {
    if (!sid || busy) return
    setBusy(true)
    try {
      const r = await post('/execute_pipeline', { session_id: sid })
      applyExecuteResponse(r)
    } catch (e) {
      setToast(`실행 실패: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  function applyExecuteResponse(r) {
    if (r.session) setView(r.session)
    if (r.status === 'completed') {
      if (r.aggregated_context) setAggregated(r.aggregated_context)
      else { refresh().catch(() => {}) }
    } else if (r.status === 'error') {
      setToast(r.pre_validation
        ? `사전 검증 실패 — high ${r.pre_validation.n_high}건`
        : '실행 오류')
    }
  }

  // STEP 2b: 옵션 카드에서 사용자가 옵션을 1개 클릭할 때 호출 ({step_key: option_id} 누적)
  function onSelectOption(step_key, option_id) {
    setSelectedOptions((prev) => ({ ...prev, [step_key]: option_id }))
  }

  async function onApprove(step_key, stage_order, module_index, selected_option = null) {
    setBusy(true)
    try {
      // STEP 2b: 옵션 있는 step은 selected_option 동봉. 백엔드 STEP 2a가 BALANCE_OPTION_IDS로 필터.
      await post(`/pipeline/${sid}/approve`,
                 { step_key, stage_order, module_index, selected_option })
      // 세션 갱신해 approved_step_keys 반영
      await refresh()
    } catch (e) {
      setToast(`승인 실패: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  async function onApproveAll(remainingSteps, stage_order, module_index) {
    setBusy(true)
    try {
      for (const s of remainingSteps) {
        // STEP 2b: 옵션 있는 step은 selectedOptions에서 꺼냄 (강제 선택 가드는 ApprovalCard가)
        const sel = selectedOptions[s.step_key] || null
        await post(`/pipeline/${sid}/approve`,
                   { step_key: s.step_key, stage_order, module_index, selected_option: sel })
      }
      await refresh()
    } catch (e) {
      setToast(`일괄 승인 실패: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  async function onResume() {
    if (busy) return
    setBusy(true)
    try {
      const r = await post('/execute_pipeline', { session_id: sid })
      applyExecuteResponse(r)
    } catch (e) {
      setToast(`재실행 실패: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const visibleAlarms = useMemo(() => {
    if (!view?.alarms) return []
    return view.alarms.filter((_, i) => !dismissedAlarms.includes(i))
  }, [view, dismissedAlarms])

  if (!sid) return <div>세션 ID가 없습니다. <a href="/">처음으로</a></div>
  if (loadErr) return <div className="error-text">⚠ {loadErr}</div>
  if (!view) return <div className="muted">로딩 중…</div>

  const status = view.status || 'unknown'
  const pending = view.pending
  const completedStages = view.completed_stage_orders || []
  const completedModules = view.completed_module_keys || []
  const stages = view.pipeline_full?.stages || []

  return (
    <div>
      <h1>파이프라인 실행</h1>
      <div className="muted">
        status: <strong className={`status-tag status-${status}`}>{status}</strong>
        {pending && ` · 멈춤: stage ${pending.stage_order + 1} module ${pending.module_index}`}
      </div>

      {/* 알람 배너 */}
      <AlarmBanner
        alarms={visibleAlarms}
        onDismiss={(i) => setDismissedAlarms((prev) => [...prev, i])}
      />

      {/* 단계 진행 카드 */}
      <section className="run-stages">
        {stages.map((s) => {
          const done = completedStages.includes(s.stage_order)
          const isPendingHere = pending && pending.stage_order === s.stage_order
          const moduleSummaries = (s.modules || []).map((m) => {
            const mk = `${s.stage_order}.${m.index}`
            const mDone = completedModules.includes(mk)
            const isPending = pending?.module_key === mk
            const result = view.module_results?.[mk]
            const passed = result?.validation?.passed
            const issues = result?.validation?.issues?.length || 0
            let label = '대기'
            if (mDone && passed === true) label = `✓ 완료 (issues ${issues})`
            else if (mDone && passed === false) label = `⚠ 완료 — 검토 필요 (issues ${issues})`
            else if (isPending) label = '⏸ 승인 대기'
            return { mk, m, label, mDone, isPending }
          })
          return (
            <div
              key={s.stage_order}
              className={`run-stage ${done ? 'stage-done' : ''} ${isPendingHere ? 'stage-pending' : ''}`}
            >
              <div className="run-stage-header">
                <strong>단계 {s.stage_order + 1}: {s.node_id}</strong>
                {done && <span className="badge-ok">완료</span>}
                {isPendingHere && <span className="badge-warn">진행 중</span>}
              </div>
              <ul className="run-modules">
                {moduleSummaries.map(({ mk, m, label }) => (
                  <li key={mk}>
                    <span className={`module-fn fn-${m.function} module-fn-chip`}>{m.function}</span>
                    <span className="muted">{m.dataset_role}</span>
                    {' · '}
                    <span>{label}</span>
                    {!m.datalake_id && (
                      <span className="muted"> (데이터 미업로드)</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </section>

      {/* 액션 — 상태별 분기 */}
      <div style={{ marginTop: 24 }}>
        {(status === 'ready' || status === 'structured' || status === 'created') && (
          <button className="btn btn-primary" onClick={onRun} disabled={busy}>
            {busy ? '실행 중…' : '실행 ▶'}
          </button>
        )}
        {status === 'awaiting_approval' && pending && (
          <ApprovalCard
            pending={pending}
            approvedKeys={view.approved_step_keys}
            busy={busy}
            selectedOptions={selectedOptions}
            onSelectOption={onSelectOption}
            onApprove={onApprove}
            onApproveAll={onApproveAll}
            onResume={onResume}
          />
        )}
        {status === 'error' && (
          <div className="error-text" style={{ marginTop: 16 }}>
            ⚠ 실행 오류. 세션 status=error.
            <div className="muted">
              {view.error || '계획 사전 검증 실패(blocking) 등으로 중단됨.'}
            </div>
          </div>
        )}
        {status === 'completed' && (
          <>
            <FindingsList
              aggregatedContext={aggregated}
              moduleResults={view.module_results}
            />
            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Link
                to={`/pipeline/analyze?session=${sid}`}
                className="btn btn-primary"
                title="Page 5는 STEP 1B-3c에서 구현"
              >
                분석 단계 → (Page 5, 다음 STEP)
              </Link>
            </div>
          </>
        )}
      </div>

      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  )
}
