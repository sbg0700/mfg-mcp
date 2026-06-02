import { useState } from 'react'
import { post } from '../api.js'

// STEP 3b-3 자연어 EDA — 시스템 정체성 화면.
//   ① 자연어 입력 → POST /eda/freeform
//   ② "awaiting_approval"이면 코드 미리보기 + 승인/취소 (ApprovalCard 발상)
//   ③ 승인 → POST /eda/freeform/approve → 실행 결과 + lineage_id
//   거부/실패/취소는 명확한 에러 박스로.
function FreeformResult({ result }) {
  // result 객체: {result, result_type, lineage_id, code, query}
  const v = result.result
  return (
    <div className="freeform-result">
      <div className="muted" style={{ marginBottom: 6 }}>
        실행 결과 (lineage: <code>{(result.lineage_id || '').slice(0, 8)}</code>,
        type: <code>{result.result_type}</code>)
      </div>
      <pre className="result-json">
        {typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v)}
      </pre>
    </div>
  )
}

export default function FreeformEda({ sessionId }) {
  const [query, setQuery] = useState('')
  const [pending, setPending] = useState(null)  // /freeform awaiting_approval 응답
  const [result, setResult] = useState(null)    // /approve executed 응답
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  function reset() {
    setError(null); setResult(null); setPending(null)
  }

  async function onRequest() {
    if (!query.trim() || busy) return
    setBusy(true); reset()
    try {
      const r = await post(`/analyze/${sessionId}/eda/freeform`, { user_query: query })
      if (r.status === 'awaiting_approval') {
        setPending(r)
      } else if (r.status === 'rejected') {
        setError(`거부됨: ${r.reason || '사유 미상'}${r.code ? `\n생성된 코드 (실행 안 함):\n${r.code}` : ''}`)
      } else if (r.status === 'llm_failed') {
        setError(`LLM 실패: ${r.error || '알 수 없음'}`)
      } else {
        setError(`상태: ${r.status}${r.reason ? ` — ${r.reason}` : ''}`)
      }
    } catch (e) {
      setError(e.message || '요청 실패')
    } finally {
      setBusy(false)
    }
  }

  async function onApprove(approved) {
    if (busy) return
    setBusy(true); setError(null)
    try {
      const r = await post(`/analyze/${sessionId}/eda/freeform/approve`, { approved })
      if (r.status === 'executed') {
        setResult(r); setPending(null)
      } else if (r.status === 'cancelled') {
        setPending(null)
      } else if (r.status === 'exec_failed') {
        setError(`실행 실패: ${r.error || '알 수 없음'} (lineage: ${(r.lineage_id || '').slice(0, 8)})`)
        setPending(null)
      } else if (r.status === 'rejected_at_exec') {
        setError(`실행 직전 거부: ${r.reason || '사유 미상'}`)
        setPending(null)
      } else if (r.status === 'no_pending') {
        setError(`승인할 코드 없음: ${r.reason || ''}`)
        setPending(null)
      } else {
        setError(`상태: ${r.status}`)
        setPending(null)
      }
    } catch (e) {
      setError(e.message || '승인 실패')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="freeform-eda">
      <h3>자연어로 분석 요청</h3>
      <p className="muted">
        궁금한 걸 한국어로 입력. AI가 분석 코드를 생성하고, <strong>승인 후 실행</strong>.
        실행 내역은 lineage에 기록됩니다.
      </p>
      <div className="freeform-input">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') onRequest() }}
          placeholder="예: FAIL 케이스만 골라서 PRESS_FORCE 평균과 표준편차 보여줘"
          disabled={busy || !!pending}
        />
        <button className="btn" onClick={onRequest} disabled={busy || !query.trim() || !!pending}>
          {busy && !pending ? '코드 생성 중…' : '분석 요청'}
        </button>
      </div>

      {pending && (
        <div className="freeform-approve">
          <div className="muted" style={{ marginBottom: 6 }}>
            AI가 생성한 분석 코드 (승인하면 실행. AST 화이트리스트 검증 통과):
          </div>
          <pre className="code-preview">{pending.code}</pre>
          <div className="freeform-actions">
            <button className="btn btn-primary" onClick={() => onApprove(true)} disabled={busy}>
              {busy ? '실행 중…' : '승인 후 실행'}
            </button>
            <button className="btn" onClick={() => onApprove(false)} disabled={busy}>
              취소
            </button>
          </div>
        </div>
      )}

      {error && <div className="chart-error" style={{ whiteSpace: 'pre-wrap' }}>⚠ {error}</div>}
      {result && <FreeformResult result={result} />}
    </div>
  )
}
