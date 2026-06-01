// 모듈별 데이터셋 드롭다운 — 해당 모듈의 modality에 매칭되는 데이터셋만 보여줌.
// 디렉터리 스캔 결과(/api/datasets/all)에서 modality 키로 골라낸다. 데이터 비종속 (D-82).
export default function DatasetSelector({ modality, datasets, value, onChange }) {
  const list = datasets || []
  return (
    <label className="dataset-selector">
      <span className="muted" style={{ marginRight: 8 }}>데이터셋:</span>
      <select value={value || ''} onChange={(e) => onChange(e.target.value || null)}>
        <option value="">(미선택 — 알람 대상)</option>
        {list.map((d) => (
          <option key={d} value={d}>{d}</option>
        ))}
      </select>
      <span className="muted" style={{ marginLeft: 8, fontSize: 12 }}>
        modality: {modality} · {list.length}개
      </span>
    </label>
  )
}
