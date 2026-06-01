// constraint_keys 폼 — modules.yaml의 node 정의 기준으로 min/max 2칸 입력.
// 빈 칸 허용(제약 없으면 비움). 입력은 모두 문자열 → 부모가 저장 시 number로 변환.
// ★typical_ranges 디폴트 0 (D-43) — placeholder도 두지 않는다 (오해 방지).
export default function ConstraintForm({ constraintKeys, value, onChange }) {
  if (!constraintKeys || constraintKeys.length === 0) {
    return (
      <div className="constraint-form">
        <h4 className="constraint-title">제약 조건</h4>
        <div className="muted">이 노드에 정의된 constraint_keys 가 없습니다 (modules.yaml).</div>
      </div>
    )
  }
  function update(key, side, raw) {
    const cur = value || {}
    const entry = cur[key] || { min: '', max: '' }
    const next = { ...entry, [side]: raw }
    onChange({ ...cur, [key]: next })
  }
  return (
    <div className="constraint-form">
      <h4 className="constraint-title">제약 조건 <span className="muted" style={{fontSize:11}}>(빈 칸 허용)</span></h4>
      <table className="constraint-table">
        <tbody>
          {constraintKeys.map((c) => {
            const entry = value?.[c.key] || { min: '', max: '' }
            return (
              <tr key={c.key}>
                <td className="constraint-key">{c.key}</td>
                <td>
                  <input
                    className="constraint-input"
                    type="text"
                    inputMode="decimal"
                    value={entry.min}
                    placeholder="min"
                    onChange={(e) => update(c.key, 'min', e.target.value)}
                  />
                </td>
                <td className="muted">~</td>
                <td>
                  <input
                    className="constraint-input"
                    type="text"
                    inputMode="decimal"
                    value={entry.max}
                    placeholder="max"
                    onChange={(e) => update(c.key, 'max', e.target.value)}
                  />
                </td>
                <td className="constraint-unit muted">{c.unit}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
