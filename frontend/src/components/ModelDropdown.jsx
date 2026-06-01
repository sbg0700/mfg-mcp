import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { get, put } from '../api.js'

// GET /api/models — 백엔드 응답: {installed: [...], default: "..."}.
// STEP 1B-3d B2: 세션이 있으면 PUT /sessions/{id}/model 로 변경 즉시 반영 (D-99).
//   - URL의 ?session=<id> 가 있는 페이지에선 드롭다운 변경이 세션에 저장됨
//   - Page 1처럼 세션이 없으면 로컬 표시만 → 세션 생성 시 함께 전달(LineSelectPage)
export default function ModelDropdown() {
  const [params] = useSearchParams()
  const sid = params.get('session') || ''
  const [models, setModels] = useState([])
  const [selected, setSelected] = useState('')
  const [err, setErr] = useState('')
  const [sessionModel, setSessionModel] = useState(null)
  const [saving, setSaving] = useState(false)

  // 1) 모델 목록 로드 (localStorage > default > 첫 항목)
  useEffect(() => {
    get('/models')
      .then((d) => {
        const list = d.installed || d.models || []
        setModels(list)
        const stored = localStorage.getItem('preferred_model') || ''
        const initial = stored && list.includes(stored)
          ? stored : (d.default || list[0] || '')
        setSelected((cur) => cur || initial)
      })
      .catch((e) => setErr(e.message || 'no models'))
  }, [])

  // 2) 세션이 있으면 세션의 model을 가져와 동기화 (페이지 새로고침/이동 시 반영)
  useEffect(() => {
    if (!sid) { setSessionModel(null); return }
    get(`/sessions/${sid}`)
      .then((s) => {
        const m = s.model || null
        setSessionModel(m)
        if (m) setSelected(m)
      })
      .catch(() => { /* 세션 만료 등 — 표시만 */ })
  }, [sid])

  async function onChange(value) {
    setSelected(value)
    // localStorage에 사용자 기본 선호 저장 — Page 1 세션 생성 때 LineSelectPage가 읽음
    try { localStorage.setItem('preferred_model', value) } catch {}
    if (!sid) return  // 세션 없으면 로컬 표시만 (Page 1) — LineSelectPage가 localStorage 읽어 POST /create에 동봉
    setSaving(true)
    try {
      const r = await put(`/sessions/${sid}/model`, { model: value })
      setSessionModel(r.model || null)
    } catch (e) {
      setErr(e.message || 'session model update failed')
    } finally {
      setSaving(false)
    }
  }

  if (err) return <span className="muted" title={err}>모델: 오류</span>
  if (!models.length) return <span className="muted">모델: 불러올 수 없음</span>

  return (
    <label className="muted" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      모델:
      <select value={selected} onChange={(e) => onChange(e.target.value)} disabled={saving}>
        {models.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>
      {sid && (
        <span className="muted" style={{ fontSize: 11 }}>
          {sessionModel ? `세션: ${sessionModel}` : '(세션 모델 미저장)'}
          {saving && ' · 저장 중…'}
        </span>
      )}
    </label>
  )
}
