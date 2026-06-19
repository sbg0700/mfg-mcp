import { useState } from 'react'
import { post } from '../api.js'

// STEP 3b-3 자연어 EDA — 시스템 정체성 화면.
//   ① 자연어 입력 → POST /eda/freeform
//   ② "awaiting_approval"이면 코드 미리보기 + 승인/취소 (ApprovalCard 발상)
//   ③ 승인 → POST /eda/freeform/approve → 실행 결과 + lineage_id
//   거부/실패/취소는 명확한 에러 박스로.

// ── 결과 가독화 헬퍼 ────────────────────────────────────────────────
const STAT_KO = {
  mean: '평균', avg: '평균', std: '표준편차', var: '분산', min: '최솟값',
  max: '최댓값', median: '중앙값', sum: '합계', count: '개수', size: '개수',
  nunique: '고유수', first: '첫값', last: '끝값', '25%': '1사분위',
  '50%': '중앙값', '75%': '3사분위', q1: '1사분위', q3: '3사분위',
}
const labelToken = (t) => STAT_KO[String(t).toLowerCase()] || String(t)

// "('Cycle_Time', 'mean')" → "Cycle_Time 평균",  "mean" → "평균"
function humanizeKey(k) {
  const s = String(k)
  const m = s.match(/^\(\s*(.+?)\s*\)$/)   // 튜플 문자열
  if (m) {
    const parts = m[1].split(',').map((p) => p.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean)
    if (parts.length === 2) return `${parts[0]} ${labelToken(parts[1])}`
    return parts.join(' ')
  }
  return labelToken(s)
}

const isNum = (v) => typeof v === 'number' && Number.isFinite(v)
function fmtVal(v) {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) return '—'                  // NaN/Inf
    if (Number.isInteger(v)) return v.toLocaleString()
    const a = Math.abs(v)
    if (a !== 0 && (a < 0.001 || a >= 1e6)) return v.toExponential(2)
    return Number(v.toFixed(a < 1 ? 3 : 2)).toLocaleString()
  }
  if (typeof v === 'boolean') return v ? '참' : '거짓'
  return String(v)
}

const isPlain = (v) => v === null || ['number', 'string', 'boolean'].includes(typeof v)

// 임의 dict/list/scalar → [{label, value}] 행으로 평탄화 (중첩 라벨은 " · " 결합)
function flattenRows(v, prefix = '', out = [], depth = 0) {
  if (out.length >= 200 || depth > 4) return out
  if (isPlain(v)) { out.push({ label: prefix || '값', value: v }); return out }
  if (Array.isArray(v)) {
    v.slice(0, 50).forEach((x, i) => flattenRows(x, prefix ? `${prefix}[${i}]` : `[${i}]`, out, depth + 1))
    return out
  }
  if (typeof v === 'object') {
    for (const [k, val] of Object.entries(v)) {
      const lbl = prefix ? `${prefix} · ${humanizeKey(k)}` : humanizeKey(k)
      flattenRows(val, lbl, out, depth + 1)
      if (out.length >= 200) break
    }
  }
  return out
}

function ResultTable({ v }) {
  // DataFrame shape: {columns, rows, n_rows_total, truncated}
  if (v && typeof v === 'object' && Array.isArray(v.columns) && Array.isArray(v.rows)) {
    return (
      <div className="result-table-wrap">
        <table className="result-table">
          <thead><tr>{v.columns.map((c, i) => <th key={i}>{humanizeKey(c)}</th>)}</tr></thead>
          <tbody>
            {v.rows.map((row, ri) => (
              <tr key={ri}>{row.map((cell, ci) => (
                <td key={ci} className={isNum(cell) ? 'num' : ''}>{fmtVal(cell)}</td>
              ))}</tr>
            ))}
          </tbody>
        </table>
        {v.truncated && (
          <div className="muted" style={{ marginTop: 4 }}>
            전체 {Number(v.n_rows_total).toLocaleString()}행 중 상위 {v.rows.length}행 표시
          </div>
        )}
      </div>
    )
  }
  if (isPlain(v)) return <div className="result-scalar">{fmtVal(v)}</div>
  const rows = flattenRows(v)
  if (!rows.length) return <div className="muted">표시할 값이 없습니다.</div>
  return (
    <table className="result-table">
      <thead><tr><th>항목</th><th>값</th></tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}><td>{r.label}</td><td className={isNum(r.value) ? 'num' : ''}>{fmtVal(r.value)}</td></tr>
        ))}
      </tbody>
    </table>
  )
}

function FreeformResult({ result, sessionId }) {
  // result 객체: {result, result_type, lineage_id, code, query}
  const v = result.result
  const [summary, setSummary] = useState(null)   // {summary, key_points} | {failed:true}
  const [sumBusy, setSumBusy] = useState(false)

  async function onSummarize() {
    if (sumBusy) return
    setSumBusy(true)
    try {
      const r = await post(`/analyze/${sessionId}/eda/freeform/summary`, {
        query: result.query || '', result: v, result_type: result.result_type,
      })
      if (r.llm_status === 'ok' && r.summary) setSummary({ summary: r.summary, key_points: r.key_points || [] })
      else setSummary({ failed: true })
    } catch {
      setSummary({ failed: true })
    } finally {
      setSumBusy(false)
    }
  }

  return (
    <div className="freeform-result">
      <div className="freeform-result-head">
        <span className="muted">
          실행 결과 (lineage: <code>{(result.lineage_id || '').slice(0, 8)}</code>,
          type: <code>{result.result_type}</code>)
        </span>
        <button className="btn btn-sm" onClick={onSummarize} disabled={sumBusy}>
          {sumBusy ? 'AI 요약 중…' : 'AI 요약'}
        </button>
      </div>

      {summary?.summary && (
        <div className="freeform-summary">
          <p>{summary.summary}</p>
          {summary.key_points?.length > 0 && (
            <ul>{summary.key_points.map((p, i) => <li key={i}>{p}</li>)}</ul>
          )}
        </div>
      )}
      {summary?.failed && (
        <div className="muted" style={{ marginBottom: 6 }}>AI 요약 실패 — 아래 표로 확인하세요.</div>
      )}

      <ResultTable v={v} />

      <div className="muted freeform-note">
        ※ 표준화(정규화)된 컬럼의 값은 절대량이 아니라 <strong>상대 비교용 값</strong>입니다.
      </div>

      <details className="freeform-raw">
        <summary className="muted">원본 JSON 보기</summary>
        <pre className="result-json">
          {typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v)}
        </pre>
      </details>
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
      {result && <FreeformResult result={result} sessionId={sessionId} />}
    </div>
  )
}
