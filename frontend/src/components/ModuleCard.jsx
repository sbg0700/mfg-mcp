// 공통 ModuleCard — Function 색상 + 드래그 가능 + 제거 버튼.
// Page 2 카탈로그(draggable)와 Stage 박스 안 모듈(removable) 양쪽에서 재사용.
export default function ModuleCard({
  function: fn,
  hint_dataset,
  source_node_id,
  draggable = false,
  removable = false,
  onRemove,
}) {
  function handleDragStart(e) {
    e.dataTransfer.setData(
      'application/json',
      JSON.stringify({ function: fn, hint_dataset, source_node_id }),
    )
    e.dataTransfer.effectAllowed = 'copy'
  }
  return (
    <div
      className={`module-card fn-${fn} ${draggable ? 'draggable' : ''}`}
      draggable={draggable || undefined}
      onDragStart={draggable ? handleDragStart : undefined}
      title={hint_dataset}
    >
      <span className="module-fn">{fn}</span>
      <span className="module-ds">{hint_dataset}</span>
      {removable && (
        <button className="module-remove" onClick={onRemove} aria-label="모듈 제거">×</button>
      )}
    </div>
  )
}
