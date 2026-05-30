import ModuleCard from '../components/ModuleCard.jsx'

// 좌측 카탈로그 — 해당 Line의 Node별로 available_modules 카드를 나열.
// 각 카드는 draggable. dataTransfer payload = {function, hint_dataset, source_node_id}.
export default function CatalogPanel({ lineDef }) {
  return (
    <div className="catalog-panel">
      <h3>카탈로그 — {lineDef.display_name}</h3>
      {lineDef.stages.map((s) => (
        <div key={s.node_id} className="catalog-node">
          <div className="catalog-node-title">
            {s.display_name}{' '}
            <span className="muted">(최대 {s.max_modules}개)</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {s.available_modules.map((m, mi) => (
              <ModuleCard
                key={`${s.node_id}.${mi}`}
                draggable
                function={m.function}
                hint_dataset={m.hint_dataset}
                source_node_id={s.node_id}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
