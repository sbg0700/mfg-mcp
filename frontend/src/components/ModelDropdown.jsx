import { useEffect, useState } from 'react'
import { get } from '../api.js'

// GET /api/models — 백엔드의 기존 응답 형태: {installed: [...], default: "..."}.
// LLM이 다운돼서 installed가 비어있을 수 있음 — 그 경우 "모델 정보 없음" 표시.
export default function ModelDropdown() {
  const [models, setModels] = useState([])
  const [selected, setSelected] = useState('')
  const [err, setErr] = useState('')

  useEffect(() => {
    get('/models')
      .then((d) => {
        const list = d.installed || d.models || []
        setModels(list)
        setSelected(d.default || list[0] || '')
      })
      .catch((e) => setErr(e.message || 'no models'))
  }, [])

  if (err || !models.length) return <span className="muted">모델: 불러올 수 없음</span>

  return (
    <label className="muted" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      모델:
      <select value={selected} onChange={(e) => setSelected(e.target.value)}>
        {models.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>
    </label>
  )
}
