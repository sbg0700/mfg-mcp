// 승인 카드 — pending.pending_steps 를 step_key 단건으로 승인.
// STEP 2b (D-110): available_options 있는 step은 옵션 카드 4개 + 결정론 미리보기 노출.
//   - 카드형(B) UX: label + 미리보기 행수 변화/가중치 + 설명 + 주의사항
//   - 강제 선택: 옵션 안 고르면 승인 버튼 비활성. 전체 승인도 미선택 step 있으면 비활성
//   - class_weight에 "권장" 배지 (가장 안전한 디폴트 가이드)
// 옵션 없는 step은 기존 yes/no 그대로 (회귀 0 — available_options 빈 배열이면 옵션 영역 안 그림)
// L1은 자동(여기 안 옴), L2=주황(승인 권장), L3=빨강(주의).
const PERM_COLOR = { L2: '#ea580c', L3: '#dc2626' }
const RECOMMENDED_OPTION = 'class_weight'   // 강제 선택의 부담을 완화하는 안전 가이드

export default function ApprovalCard({
  pending, approvedKeys, busy,
  selectedOptions = {},        // STEP 2b: {step_key: option_id}
  onSelectOption,              // STEP 2b: (step_key, option_id) => void
  onApprove, onApproveAll, onResume,
}) {
  if (!pending) return null
  const approved = new Set(approvedKeys || [])
  const steps = pending.pending_steps || []
  const remaining = steps.filter((s) => !approved.has(s.step_key))
  const allApproved = remaining.length === 0
  // 전체 승인 가드 — 옵션 있는 미승인 step 중 선택 안 한 게 있으면 비활성 (강제 선택)
  const hasUnselectedOptionStep = remaining.some(
    (s) => Array.isArray(s.available_options)
        && s.available_options.length > 0
        && !selectedOptions[s.step_key]
  )

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
          const hasOptions = Array.isArray(s.available_options) && s.available_options.length > 0
          const selected = selectedOptions[s.step_key] || null
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
                ) : !hasOptions ? (
                  /* 옵션 없는 step — 기존 yes/no 그대로 (회귀 0) */
                  <button
                    className="btn"
                    disabled={busy}
                    onClick={() =>
                      onApprove(s.step_key, pending.stage_order, pending.module_index, null)
                    }
                  >
                    승인
                  </button>
                ) : null /* 옵션 있는 step의 승인 버튼은 아래 OptionCardGroup 안에 */}
              </div>
              {s.rationale && (
                <div className="approval-rationale muted">{s.rationale}</div>
              )}
              {hasOptions && !isApproved && (
                <OptionCardGroup
                  step={s}
                  selected={selected}
                  busy={busy}
                  onSelect={(optId) => onSelectOption?.(s.step_key, optId)}
                  onApprove={() =>
                    onApprove(s.step_key, pending.stage_order, pending.module_index, selected)
                  }
                />
              )}
            </li>
          )
        })}
      </ul>
      <div className="approval-actions">
        <button
          className="btn"
          onClick={() =>
            onApproveAll(
              steps.filter((s) => !approved.has(s.step_key)),
              pending.stage_order, pending.module_index,
            )
          }
          disabled={busy || allApproved || hasUnselectedOptionStep}
          title={
            hasUnselectedOptionStep
              ? '옵션 선택이 필요한 단계가 있습니다 — 카드를 클릭해 옵션을 1개 선택하세요'
              : ''
          }
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


// ─────────────────────────────────────────────────────────────────────
// OptionCardGroup — balance_classes 등 available_options 있는 step의 옵션 UI.
// 결정론 미리보기(preview.previews[opt_id])를 그대로 표시 (LLM 0, STEP 2a).
// ─────────────────────────────────────────────────────────────────────
function OptionCardGroup({ step, selected, busy, onSelect, onApprove }) {
  const preview = step.preview || {}
  const cur = preview.current
  const previews = preview.previews || {}

  if (preview.applicable === false) {
    return (
      <div className="opt-warn muted">
        {preview.reason || '옵션 적용 불가 — 데이터 분포 확인 필요'}
      </div>
    )
  }

  return (
    <div className="opt-group">
      {cur && (
        <div className="opt-current muted">
          현재 분포:{' '}
          {Object.entries(cur.counts).map(([k, v]) => `${k} ${v}`).join(' / ')}
          {cur.minority_ratio != null && (
            <> {' '}(소수 클래스 {(cur.minority_ratio * 100).toFixed(2)}%)</>
          )}
        </div>
      )}
      <div className="opt-cards">
        {step.available_options.map((opt) => {
          const pv = previews[opt.id] || {}
          const isSel = selected === opt.id
          return (
            <button
              key={opt.id}
              type="button"
              className={`opt-card ${isSel ? 'selected' : ''}`}
              disabled={busy}
              onClick={() => onSelect(opt.id)}
            >
              <div className="opt-card-head">
                <span className="opt-label">{opt.label}</span>
                {opt.id === RECOMMENDED_OPTION && (
                  <span className="opt-badge" title="가장 안전한 디폴트">권장</span>
                )}
              </div>
              <div className="opt-preview">
                {Number.isFinite(pv.rows_after)
                  ? (pv.rows_delta === 0
                      ? `행수 유지 (${pv.rows_after}행)`
                      : `${pv.rows_after}행 (${pv.rows_delta > 0 ? '+' : ''}${pv.rows_delta})`)
                  : '미리보기 없음'}
              </div>
              {opt.id === 'class_weight' && pv.weights && (
                <div className="opt-sub muted">
                  가중치 최대 ~{Math.max(...Object.values(pv.weights)).toFixed(2)}배
                </div>
              )}
              {opt.description && (
                <div className="opt-desc muted">{opt.description}</div>
              )}
              {opt.caution && (
                <div className="opt-caution">⚠ {opt.caution}</div>
              )}
            </button>
          )
        })}
      </div>
      <div className="opt-actions">
        <button
          className="btn"
          disabled={busy || !selected}
          onClick={onApprove}
          title={selected ? '' : '옵션을 1개 선택해야 승인됩니다 (강제 선택)'}
        >
          {selected ? `'${selected}' 선택 적용` : '옵션을 선택하세요'}
        </button>
      </div>
    </div>
  )
}
