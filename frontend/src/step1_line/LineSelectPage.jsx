import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { get, post } from '../api.js'

// Page 1 — Line 선택 (spec-1 Part 2).
// 1. GET /api/lines → 3 Line 라디오로 표시
// 2. 선택 + "다음" → POST /api/sessions/create {line_id}
// 3. 받은 session_id로 /pipeline/build?session=... 이동
export default function LineSelectPage() {
  const [lines, setLines] = useState([])
  const [picked, setPicked] = useState('')
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    get('/lines')
      .then((d) => setLines(d.lines || []))
      .catch((e) => setError(e.message || '라인 카탈로그 로드 실패'))
  }, [])

  async function onNext() {
    if (!picked || creating) return
    setCreating(true)
    setError('')
    try {
      // STEP 1B-3d B2: 우상단 ModelDropdown이 localStorage('preferred_model')에 저장한 선택을
      // 같이 보낸다. 백엔드가 sessions/create 시 session["model"]에 저장 (D-99).
      const preferredModel = (() => {
        try { return localStorage.getItem('preferred_model') || null } catch { return null }
      })()
      const body = { line_id: picked }
      if (preferredModel) body.model = preferredModel
      const r = await post('/sessions/create', body)
      navigate(`/pipeline/build?session=${r.session_id}`)
    } catch (e) {
      setError(e.message || '세션 생성 실패')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      <h1>라인을 선택하세요</h1>
      <p className="muted">파이프라인을 구성할 공정 라인을 1개 선택합니다. (3 Line × 18 Node, KAMP 기준)</p>

      {error && <div className="error-text" style={{ marginBottom: 12 }}>⚠ {error}</div>}

      <div className="line-list">
        {lines.length === 0 && !error && <div className="muted">로딩 중...</div>}
        {lines.map((ln) => (
          <label key={ln.line_id} className="line-row">
            <input
              type="radio"
              name="line"
              value={ln.line_id}
              checked={picked === ln.line_id}
              onChange={() => setPicked(ln.line_id)}
            />
            <span style={{ marginLeft: 12 }}>
              <strong>{ln.display_name}</strong>
              <span className="muted"> ({ln.max_stages} Stage / 노드 {ln.stages?.length ?? '?'}개)</span>
              <div className="muted" style={{ marginTop: 4, fontSize: 12 }}>
                {(ln.stages || []).slice(0, 4).map((s) => s.display_name).join(' · ')}
                {(ln.stages || []).length > 4 ? ' …' : ''}
              </div>
            </span>
          </label>
        ))}
      </div>

      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <button
          className="btn btn-primary"
          onClick={onNext}
          disabled={!picked || creating}
        >
          {creating ? '세션 생성 중…' : '다음 →'}
        </button>
      </div>
    </div>
  )
}
