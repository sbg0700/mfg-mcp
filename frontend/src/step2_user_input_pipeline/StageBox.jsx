import { useState } from 'react'
import ModuleCard from '../components/ModuleCard.jsx'

// 우측 Stage 박스 — Line.stages 순서대로 하나씩 렌더.
// HTML5 native drop target. drop 시 부모(PipelineBuildPage)의 onDrop으로 위임.
export default function StageBox({ stage, index, modules, onDrop, onRemove }) {
  const [over, setOver] = useState(false)

  function handleDragOver(e) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'copy'
    if (!over) setOver(true)
  }
  function handleDragLeave() { setOver(false) }
  function handleDrop(e) {
    e.preventDefault()
    setOver(false)
    try {
      const payload = JSON.parse(e.dataTransfer.getData('application/json'))
      onDrop(stage.node_id, payload)
    } catch (_err) {
      // payload 파싱 실패 — 외부 드래그 등, 조용히 무시
    }
  }

  return (
    <div
      className={`stage-box ${over ? 'drop-target' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="stage-header">
        <strong>Stage {index + 1}: {stage.display_name}</strong>
        <span className="muted">
          ({modules.length}/{stage.max_modules})
        </span>
      </div>
      <div className="stage-body">
        {modules.length === 0 && (
          <div className="stage-empty muted">여기로 모듈을 드래그하세요</div>
        )}
        {modules.map((m, mi) => (
          <ModuleCard
            key={`${stage.node_id}.${mi}`}
            function={m.function}
            hint_dataset={m.dataset_role}
            removable
            onRemove={() => onRemove(stage.node_id, mi)}
          />
        ))}
      </div>
    </div>
  )
}
