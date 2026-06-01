// 승인 카드 — pending.pending_steps 를 step_key 단건으로 승인.
// L1은 자동(여기 안 옴), L2=주황(승인 권장), L3=빨강(주의).
const PERM_COLOR = { L2: '#ea580c', L3: '#dc2626' }

export default function ApprovalCard({ pending, approvedKeys, busy, onApprove, onApproveAll, onResume }) {
  if (!pending) return null
  const approved = new Set(approvedKeys || [])
  const steps = pending.pending_steps || []
  const remaining = steps.filter((s) => !approved.has(s.step_key))
  const allApproved = remaining.length === 0

  return (
    <div className="approval-card">
      <div className="approval-header">
        <strong>승인 필요</strong>
        <span className="muted">
          · Stage {pending.stage_order + 1} ({pending.node_id})
          · Module {pending.module_index}
          · dataset <code>{pending.dataset_id}</code>
          · modality <code>{pending.modality}</code>
        </span>
      </div>
      <p className="muted">
        이 작업들은 데이터를 변경합니다. 검토 후 승인하세요.
        ({steps.length}개 중 {approved.size}개 승인됨)
      </p>
      <ul className="approval-list">
        {steps.map((s) => {
          const isApproved = approved.has(s.step_key)
          return (
            <li key={s.step_key} className={`approval-step ${isApproved ? 'approved' : ''}`}>
              <div className="approval-step-line">
                <span
                  className="perm-badge"
                  style={{ background: PERM_COLOR[s.permission_level] || '#475569' }}
                >
                  {s.permission_level}
                </span>
                <strong>{s.operation}</strong>
                {s.target_column && <span className="muted"> · {s.target_column}</span>}
                {s.semantic_group && (
                  <span className="muted"> · group: {s.semantic_group}</span>
                )}
                <span style={{ flex: 1 }} />
                {isApproved ? (
                  <span className="approval-mark">✓ 승인됨</span>
                ) : (
                  <button
                    className="btn"
                    disabled={busy}
                    onClick={() => onApprove(s.step_key, pending.stage_order, pending.module_index)}
                  >
                    승인
                  </button>
                )}
              </div>
              {s.rationale && (
                <div className="approval-rationale muted">{s.rationale}</div>
              )}
            </li>
          )
        })}
      </ul>
      <div className="approval-actions">
        <button
          className="btn"
          onClick={() => onApproveAll(steps.filter((s) => !approved.has(s.step_key)),
                                      pending.stage_order, pending.module_index)}
          disabled={busy || allApproved}
        >
          전체 승인 ({remaining.length})
        </button>
        <button
          className="btn btn-primary"
          onClick={onResume}
          disabled={busy || !allApproved}
          title={allApproved ? '' : '남은 step_key를 모두 승인하세요'}
        >
          승인 후 계속 →
        </button>
      </div>
    </div>
  )
}
