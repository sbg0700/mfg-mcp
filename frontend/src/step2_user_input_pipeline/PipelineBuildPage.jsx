import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { get, put } from '../api.js'
import StageBox from './StageBox.jsx'
import Toast from '../components/Toast.jsx'

// Page 2 — Pipeline 구성 (spec-1 Part 3, 드래그앤드롭).
// D-212: 좌측 = 4기능 팔레트(process/quality/maintenance/reference). 실데이터 미바인딩.
//   기능 카드를 Stage에 드롭 → 모듈 {function} 추가 (dataset_role 미설정, chain/attached null,
//   중첩 없음 = v1 평면). 데이터 선택은 Page 3에서. 모듈은 function만 보유.
const FUNCTIONS = [
  { id: 'process', label: '공정 (process)' },
  { id: 'quality', label: '품질 (quality)' },
  { id: 'maintenance', label: '설비·보전 (maintenance)' },
  { id: 'reference', label: '참조 (reference)' },
]

export default function PipelineBuildPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const sid = params.get('session') || ''
  const [lineId, setLineId] = useState('')
  const [lineDef, setLineDef] = useState(null)         // 해당 Line catalog: {stages, ...}
  const [byNode, setByNode] = useState({})             // node_id → [{function}] (D-212: 데이터 미바인딩)
  const [toast, setToast] = useState('')
  const [saving, setSaving] = useState(false)
  const [loadErr, setLoadErr] = useState('')

  // 진입 시 세션과 카탈로그를 같이 불러와서 line_id 매칭 + 구조 복원
  useEffect(() => {
    if (!sid) return
    Promise.all([get(`/sessions/${sid}`), get('/lines')])
      .then(([sess, linesResp]) => {
        const lid = sess.line_id || sess.pipeline_full?.line_id || ''
        setLineId(lid)
        const lines = linesResp.lines || []
        const def = lines.find((l) => l.line_id === lid)
        if (!def) {
          setLoadErr(`Line '${lid}'을(를) 카탈로그에서 찾을 수 없습니다.`)
          return
        }
        setLineDef(def)

        // 이전에 저장된 structure 복원 — 모듈은 function만 (D-212: dataset_role 미사용)
        const restored = {}
        const stages = sess.pipeline_full?.stages || []
        for (const s of stages) {
          restored[s.node_id] = (s.modules || []).map((m) => ({ function: m.function }))
        }
        setByNode(restored)
      })
      .catch((e) => setLoadErr(e.message || '세션/카탈로그 로드 실패'))
  }, [sid])

  function onPaletteDragStart(e, fn) {
    e.dataTransfer.setData('application/json', JSON.stringify({ function: fn }))
    e.dataTransfer.effectAllowed = 'copy'
  }

  function onDrop(targetNodeId, payload) {
    if (!lineDef || !payload?.function) return
    const stage = lineDef.stages.find((s) => s.node_id === targetNodeId)
    if (!stage) return
    const cur = byNode[targetNodeId] || []
    // max_modules 초과만 차단 (같은 function 중복 허용 — Page 3에서 각자 다른 데이터 바인딩)
    if (cur.length >= stage.max_modules) {
      setToast(`이 Stage는 최대 ${stage.max_modules}개까지만 배치할 수 있습니다.`)
      return
    }
    setByNode({ ...byNode, [targetNodeId]: [...cur, { function: payload.function }] })
  }

  function onRemove(nodeId, idx) {
    const cur = (byNode[nodeId] || []).slice()
    cur.splice(idx, 1)
    setByNode({ ...byNode, [nodeId]: cur })
  }

  async function onNext() {
    if (!lineDef) return
    // 빈 Stage 제외 — 모듈 1+ 있는 노드만 stages에 포함
    const stages = lineDef.stages
      .map((s, idx) => ({
        stage_order: idx,
        node_id: s.node_id,
        modules: (byNode[s.node_id] || []).map((m, mi) => ({
          index: mi,
          function: m.function,   // D-212: dataset_role 미포함 (데이터 바인딩은 Page 3)
        })),
      }))
      .filter((s) => s.modules.length > 0)

    if (stages.length === 0) {
      setToast('최소 1개 Stage에 1개 이상의 모듈이 필요합니다.')
      return
    }

    setSaving(true)
    try {
      await put(`/sessions/${sid}/structure`, { line_id: lineId, stages })
      navigate(`/pipeline/${import.meta.env.VITE_DL_UI_V2 ? 'data-v2' : 'data'}?session=${sid}`)
    } catch (e) {
      setToast(`저장 실패: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  if (!sid) {
    return (
      <div>
        세션 ID가 없습니다. <a href="/">처음으로</a>
      </div>
    )
  }
  if (loadErr) return <div className="error-text">⚠ {loadErr}</div>
  if (!lineDef) return <div className="muted">로딩 중…</div>

  const totalModules = Object.values(byNode).reduce((n, arr) => n + arr.length, 0)
  const filledStages = lineDef.stages.filter((s) => (byNode[s.node_id] || []).length > 0).length

  return (
    <div>
      <h1>{lineDef.display_name} — 파이프라인 구성</h1>
      <p className="muted">
        왼쪽 기능 팔레트에서 기능을 끌어와 오른쪽 Stage 박스에 놓으세요. 데이터 선택은 다음 단계(Page 3).
        (현재 {totalModules}개 모듈 / {filledStages} Stage 채움)
      </p>

      <div className="pipeline-grid">
        <div className="catalog-panel">
          <h3>기능 팔레트</h3>
          <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>
            4개 기능을 Stage로 드래그하세요. (데이터는 Page 3)
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {FUNCTIONS.map((f) => (
              <div
                key={f.id}
                className={`module-card fn-${f.id} draggable`}
                draggable
                onDragStart={(e) => onPaletteDragStart(e, f.id)}
                title={f.label}
              >
                <span className="module-fn">{f.id}</span>
                <span className="module-ds">{f.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="stage-column">
          {lineDef.stages.map((s, idx) => (
            <div key={s.node_id}>
              <StageBox
                stage={s}
                index={idx}
                modules={byNode[s.node_id] || []}
                onDrop={onDrop}
                onRemove={onRemove}
              />
              {idx < lineDef.stages.length - 1 && <div className="arrow-down">↓</div>}
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <button className="btn btn-primary" onClick={onNext} disabled={saving}>
          {saving ? '저장 중…' : '다음 → (Page 3)'}
        </button>
      </div>

      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  )
}
