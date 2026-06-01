// 제약 폼 (D-90 해결, STEP 1B-3c) — 선택한 데이터셋의 실제 컬럼명 드롭다운으로 매핑.
// 입력 형태: rows = [{column, min, max}] (UI 상태)
// 부모는 rows를 받아 백엔드 저장 시 {realCol: [min,max]} 형태로 변환.
// modules.yaml의 constraint_keys는 "권장 항목 (참고)"로만 표시.
export default function ConstraintForm({ columns, hintKeys, rows, onChange, datasetSelected }) {
  function update(i, patch) {
    const next = (rows || []).slice()
    next[i] = { ...(next[i] || {}), ...patch }
    onChange(next)
  }
  function addRow() {
    onChange([...(rows || []), { column: '', min: '', max: '' }])
  }
  function removeRow(i) {
    const next = (rows || []).slice()
    next.splice(i, 1)
    onChange(next)
  }
  const usedCols = new Set((rows || []).map((r) => r.column).filter(Boolean))

  return (
    <div className="constraint-form">
      <h4 className="constraint-title">
        제약 조건 (선택한 데이터셋의 컬럼 기준)
        <span className="muted" style={{ fontSize: 11, marginLeft: 8 }}>
          (D-90 해결 — 실제 컬럼명 매핑)
        </span>
      </h4>
      {!datasetSelected ? (
        <div className="muted">데이터셋을 먼저 선택하세요.</div>
      ) : columns.length === 0 ? (
        <div className="muted">이 데이터셋에는 수치 컬럼이 없습니다 (또는 컬럼 정보를 불러오지 못함).</div>
      ) : (
        <>
          {(rows || []).map((r, i) => (
            <div key={i} className="constraint-row-real">
              <select
                value={r.column || ''}
                onChange={(e) => update(i, { column: e.target.value })}
              >
                <option value="">(컬럼 선택)</option>
                {columns.map((c) => (
                  <option
                    key={c.name}
                    value={c.name}
                    disabled={usedCols.has(c.name) && c.name !== r.column}
                  >
                    {c.name}
                  </option>
                ))}
              </select>
              <input
                type="text"
                className="constraint-input"
                inputMode="decimal"
                placeholder="min"
                value={r.min || ''}
                onChange={(e) => update(i, { min: e.target.value })}
              />
              <span className="muted">~</span>
              <input
                type="text"
                className="constraint-input"
                inputMode="decimal"
                placeholder="max"
                value={r.max || ''}
                onChange={(e) => update(i, { max: e.target.value })}
              />
              <button
                type="button"
                className="btn"
                style={{ padding: '4px 10px', fontSize: 12 }}
                onClick={() => removeRow(i)}
              >
                삭제
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn"
            style={{ marginTop: 4, fontSize: 12 }}
            onClick={addRow}
          >
            + 제약 추가
          </button>
        </>
      )}
      {hintKeys && hintKeys.length > 0 && (
        <div className="constraint-hints muted" style={{ fontSize: 12, marginTop: 8 }}>
          권장 항목 (modules.yaml): {hintKeys.map((k) => k.key).join(', ')} (참고용)
        </div>
      )}
    </div>
  )
}
