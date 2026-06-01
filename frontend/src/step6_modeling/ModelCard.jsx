// 모델 카드 — fit_score를 별로, rationale + context_reflections + task/when 표시.
function Stars({ score }) {
  const filled = '★'.repeat(score)
  const empty = '☆'.repeat(5 - score)
  return <span className="model-stars" title={`fit_score=${score}/5`}>{filled}{empty}</span>
}

export default function ModelCard({ rec, onTrain }) {
  return (
    <div className={`model-card ${rec.advisory_only ? 'advisory' : ''}`}>
      <div className="model-card-head">
        <Stars score={rec.fit_score} />
        <strong className="model-name">{rec.name}</strong>
        <span className="muted model-meta">
          ({rec.task} · {rec.when || '?'})
        </span>
        <span className="muted model-source">[from {rec.from_node}]</span>
      </div>
      {rec.rationale_ko && <div className="model-rationale">{rec.rationale_ko}</div>}
      {rec.context_reflections && rec.context_reflections.length > 0 && (
        <ul className="model-reflections">
          {rec.context_reflections.map((c, i) => (
            <li key={i} className="muted">↳ {c}</li>
          ))}
        </ul>
      )}
      <div className="model-actions">
        {rec.advisory_only ? (
          <span className="badge-warn">권고만 — VRAM 등 제약으로 본 환경에서 실행 불가</span>
        ) : (
          <button className="btn btn-primary" onClick={() => onTrain(rec)}>
            학습 시작 ▶
          </button>
        )}
      </div>
    </div>
  )
}
