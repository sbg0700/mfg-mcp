import { useState } from 'react'

// Page 2 단계 카드 — 가로 흐름의 한 칸. 단계 안 모듈을 세로로 표시:
//   P(process) = 세로 체인(chain_order 순), M/Q = 그 P에 부착(attached_to, 들여쓰기),
//   R(reference) = 독립. 드롭 타깃 2종: 단계 본문(일반) + 각 P 카드(M/Q 부착).
const FN_KO = { process: '공정', quality: '품질', maintenance: '설비·보전', reference: '참조' }

function parsePayload(e) {
  try { return JSON.parse(e.dataTransfer.getData('application/json')) } catch { return null }
}

export default function StageBox({ stage, index, modules, onDropStage, onDropP, onRemove }) {
  const [over, setOver] = useState(false)

  function stageDragOver(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; if (!over) setOver(true) }
  function stageDragLeave() { setOver(false) }
  function stageDrop(e) {
    e.preventDefault(); setOver(false)
    const p = parsePayload(e); if (p) onDropStage(stage.node_id, p)
  }
  function pDrop(e, pUid) {
    e.preventDefault(); e.stopPropagation()
    const p = parsePayload(e); if (p) onDropP(stage.node_id, pUid, p)
  }

  const pChain = modules.filter((m) => m.function === 'process')
  const refs = modules.filter((m) => m.function === 'reference')
  const attachedByP = {}
  for (const m of modules) {
    if (m.function === 'quality' || m.function === 'maintenance') {
      if (!attachedByP[m.attached_to]) attachedByP[m.attached_to] = []
      attachedByP[m.attached_to].push(m)
    }
  }

  const Chip = ({ m }) => (
    <div className={`mod-chip fn-${m.function}`}>
      <span><span className="mod-fn">{m.function}</span> · {FN_KO[m.function]}</span>
      <button className="module-remove" onClick={() => onRemove(stage.node_id, m.uid)}
              aria-label="모듈 제거">×</button>
    </div>
  )

  return (
    <div className={`flow-stage ${over ? 'drop-target' : ''}`}
         onDragOver={stageDragOver} onDragLeave={stageDragLeave} onDrop={stageDrop}>
      <div className="flow-stage-header">
        <span className="flow-stage-title">단계 {index + 1}: {stage.display_name}</span>
        <span className="flow-stage-count">{modules.length}/{stage.max_modules}</span>
      </div>
      <div className="flow-stage-body">
        {modules.length === 0 && <div className="flow-empty">여기로<br />기능을 드래그</div>}

        {pChain.map((p, i) => (
          <div key={p.uid}>
            {i > 0 && <div className="mod-chain-arrow">↓</div>}
            <div className="mod-p-wrap"
                 onDragOver={(e) => { e.preventDefault(); e.stopPropagation() }}
                 onDrop={(e) => pDrop(e, p.uid)}>
              <Chip m={p} />
              {(attachedByP[p.uid] || []).length > 0 && (
                <div className="mod-attached">
                  {attachedByP[p.uid].map((mq) => <Chip key={mq.uid} m={mq} />)}
                </div>
              )}
            </div>
          </div>
        ))}

        {refs.length > 0 && (
          <div className="mod-ref-group">
            {refs.map((r) => <Chip key={r.uid} m={r} />)}
          </div>
        )}
      </div>
    </div>
  )
}
