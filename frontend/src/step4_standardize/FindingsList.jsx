// 완료 결과 표시 — AggregatedContext(1B-2b) 의 key_findings + validator 검증 요약.
// finding.detail 에 "172/800" 같은 핵심 수치가 들어있으므로 그대로 노출 (D-67).
const SEVERITY_COLOR = {
  high: '#dc2626',
  medium: '#f59e0b',
  low: '#64748b',
  info: '#64748b',
}

export default function FindingsList({ aggregatedContext, moduleResults }) {
  if (!aggregatedContext) return null
  const kf = aggregatedContext.key_findings || []
  const sc = aggregatedContext.stage_chain || []

  // 모듈 단위 validator passed/checks 요약 (모듈 1개 가정 — 다수면 첫 번째 노출)
  const moduleKeys = moduleResults ? Object.keys(moduleResults) : []
  const firstVal = moduleKeys.length > 0 ? moduleResults[moduleKeys[0]]?.validation : null

  return (
    <div className="findings-section">
      <h2>✓ 파이프라인 완료</h2>

      {firstVal && (
        <div className="validator-summary">
          <span className="muted">검증:</span>
          <span className={firstVal.passed ? 'badge-ok' : 'badge-warn'}>
            {firstVal.passed ? '통과' : '경고'}
          </span>
          {Object.entries(firstVal.checks || {}).map(([k, v]) => (
            <span key={k} className={`check-chip ${v ? 'check-ok' : 'check-bad'}`}>
              {k}: {v ? '✓' : '⚠'}
            </span>
          ))}
        </div>
      )}

      <h3 style={{ marginTop: 16 }}>주요 발견 ({kf.length})</h3>
      {kf.length === 0 ? (
        <div className="muted">특이사항 없음.</div>
      ) : (
        <ul className="findings-list">
          {kf.map((f, i) => (
            <li key={i} className="finding-row">
              <span
                className="severity-tag"
                style={{ background: SEVERITY_COLOR[f.severity] || '#475569' }}
              >
                {f.severity}
              </span>
              <span className="finding-type muted">{f.type}</span>
              <span className="finding-detail">{f.detail}</span>
            </li>
          ))}
        </ul>
      )}

      {sc.length > 0 && (
        <>
          <h3 style={{ marginTop: 16 }}>단계 함의 (Page 5/6 컨텍스트)</h3>
          <ul className="stage-implications">
            {sc.map((s) => (
              <li key={s.stage_order}>
                <strong>단계 {s.stage_order + 1} ({s.node_id})</strong>
                {' — '}
                <span className="muted">{s.downstream_implication}</span>
                {s.main_findings?.length > 0 && (
                  <div className="muted" style={{ fontSize: 12, marginLeft: 16 }}>
                    findings: {s.main_findings.join(', ')}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
