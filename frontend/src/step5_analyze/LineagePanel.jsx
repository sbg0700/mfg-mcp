import { useState } from 'react'
import { get } from '../api.js'

// 세션 누적 lineage(변환 이력) 보기 — 추적성 시연/캡처용.
// GET /lineage/session/{sid} : record별 작업종류·대상컬럼·제거행수·시각·승인.
// 인메모리 저장이라 백엔드 재기동 시 소실(같은 세션 캡처 전제).

const OP_KO = {
  remove_outlier: '이상치 제거',
  eda_freeform_code: '자유분석 코드',
  impute_missing: '결측 대치',
  drop_column: '컬럼 삭제',
  balance_classes: '클래스 균형',
}
function opLabel(t) {
  const s = String(t || '')
  if (OP_KO[s]) return OP_KO[s]
  const base = s.split(':')[0]               // normalize_group:zscore → normalize_group
  return OP_KO[base] ? `${OP_KO[base]} (${s.split(':')[1] || ''})` : s
}
function fmtTime(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString('ko-KR', { hour12: false })
  } catch { return iso }
}

export default function LineagePanel({ sessionId }) {
  const [chain, setChain] = useState(null)   // record[]
  const [meta, setMeta] = useState(null)     // {n_records, datasets}
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function load() {
    if (busy) return
    setBusy(true); setError(null)
    try {
      const r = await get(`/lineage/session/${sessionId}`)
      setChain(r.chain || [])
      setMeta({ n_records: r.n_records || 0, datasets: r.datasets || [] })
    } catch (e) {
      setError(e.message || '조회 실패')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="lineage-panel">
      <div className="lineage-head">
        <h3>변환 이력 (Lineage)</h3>
        <button className="btn btn-sm" onClick={load} disabled={busy}>
          {busy ? '불러오는 중…' : chain ? '새로고침' : '이력 불러오기'}
        </button>
      </div>
      <p className="muted">
        이 세션에서 AI/사용자가 적용한 모든 변환의 누적 기록입니다. (감사·추적성 시연)
      </p>

      {error && <div className="chart-error">⚠ {error}</div>}

      {chain && (chain.length === 0 ? (
        <div className="muted">기록된 변환이 없습니다. (전처리/자유분석 실행 후 다시 조회)</div>
      ) : (
        <div className="result-table-wrap">
          <div className="muted" style={{ marginBottom: 6 }}>
            총 {meta?.n_records}건 · 데이터셋 {meta?.datasets?.length}개
          </div>
          <table className="result-table">
            <thead>
              <tr>
                <th>#</th><th>작업</th><th>대상 컬럼</th><th>제거 행수</th>
                <th>시각</th><th>승인</th><th>lineage</th>
              </tr>
            </thead>
            <tbody>
              {chain.map((r, i) => (
                <tr key={r.lineage_id || i}>
                  <td className="num">{i + 1}</td>
                  <td>{opLabel(r.transformation_type)}</td>
                  <td>{r.target_column || '—'}</td>
                  <td className="num">
                    {Number.isFinite(r.removed_rows) ? Number(r.removed_rows).toLocaleString() : '—'}
                  </td>
                  <td>{fmtTime(r.applied_at)}</td>
                  <td>{r.approved ? '승인됨' : '자동'}</td>
                  <td><code>{(r.lineage_id || '').slice(0, 8)}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </section>
  )
}
