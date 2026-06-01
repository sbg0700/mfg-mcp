// 분석목적 선택 — LLM 추천 + 전체 옵션 + 직접 입력.
const PURPOSE_KO = {
  anomaly_detection: '이상 탐지 (Anomaly Detection)',
  quality_classification: '품질 예측·분류 (Quality)',
  process_optimization: '공정 최적화 (Process Optimization)',
  predictive_maintenance: '예지보전 (Predictive Maintenance)',
  demand_forecasting: '생산량/수요 예측 (Demand Forecasting)',
  statistical_comparison: '통계·SPC 비교 (Statistical Comparison)',
}

export default function QuestionRadioGroup({
  recommendations, allOptions, selected, onSelect, freeInput, onFreeInput,
}) {
  const recOptions = new Set((recommendations || []).map((r) => r.option))
  const remaining = (allOptions || []).filter((o) => !recOptions.has(o))

  return (
    <div className="qrg">
      {recommendations && recommendations.length > 0 && (
        <section className="qrg-section">
          <h3>LLM 추천 ({recommendations.length})</h3>
          <ul className="qrg-list">
            {recommendations.map((r) => (
              <li key={r.option} className="qrg-row qrg-recommended">
                <label>
                  <input
                    type="radio"
                    name="purpose"
                    value={r.option}
                    checked={selected === r.option}
                    onChange={() => onSelect(r.option)}
                  />
                  <span className="qrg-rank">rank {r.rank}</span>
                  <strong>{PURPOSE_KO[r.option] || r.option}</strong>
                </label>
                {r.rationale_ko && (
                  <div className="qrg-rationale muted">{r.rationale_ko}</div>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
      <section className="qrg-section">
        <h3>전체 옵션</h3>
        <ul className="qrg-list">
          {remaining.map((o) => (
            <li key={o} className="qrg-row">
              <label>
                <input
                  type="radio"
                  name="purpose"
                  value={o}
                  checked={selected === o}
                  onChange={() => onSelect(o)}
                />
                <span>{PURPOSE_KO[o] || o}</span>
              </label>
            </li>
          ))}
        </ul>
      </section>
      <section className="qrg-section">
        <h3>또는 직접 입력 (free_input)</h3>
        <textarea
          className="qrg-free"
          placeholder="자유 입력 — LLM이 위 옵션 중 하나로 매핑 시도 (참고용 텍스트)"
          rows={2}
          value={freeInput || ''}
          onChange={(e) => onFreeInput(e.target.value)}
        />
      </section>
    </div>
  )
}
