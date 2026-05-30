import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { get, put } from '../api.js'
import CatalogPanel from './CatalogPanel.jsx'
import StageBox from './StageBox.jsx'
import Toast from '../components/Toast.jsx'

// Page 2 — Pipeline 구성 (spec-1 Part 3, 드래그앤드롭).
// 좌: 카탈로그 (선택한 Line의 Node별 available_modules)
// 우: Stage 박스들 (Line.stages 순서, ↓ 화살표로 시간순)
// 드래그앤드롭으로 모듈 배치 후 "다음" → PUT /sessions/{id}/structure → Page 3 이동.
export default function PipelineBuildPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const sid = params.get('session') || ''
  const [lineId, setLineId] = useState('')
  const [lineDef, setLineDef] = useState(null)         // 해당 Line catalog: {stages, ...}
  const [byNode, setByNode] = useState({})             // node_id → [{function, dataset_role}]
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

        // 이전에 저장된 structure 복원
        const restored = {}
        const stages = sess.pipeline_full?.stages || []
        for (const s of stages) {
          restored[s.node_id] = (s.modules || []).map((m) => ({
            function: m.function,
            dataset_role: m.dataset_role || m.hint_dataset || '',
          }))
        }
        setByNode(restored)
      })
      .catch((e) => setLoadErr(e.message || '세션/카탈로그 로드 실패'))
  }, [sid])

  function onDrop(targetNodeId, payload) {
    if (!lineDef || !payload?.function) return
    // 검증 1: source_node_id !== target_node_id → 노드 불일치
    if (payload.source_node_id && payload.source_node_id !== targetNodeId) {
      const stage = lineDef.stages.find((s) => s.node_id === targetNodeId)
      setToast(`다른 공정 노드의 모듈은 추가할 수 없습니다 (대상: ${stage?.display_name || targetNodeId}).`)
      return
    }
    const stage = lineDef.stages.find((s) => s.node_id === targetNodeId)
    if (!stage) return
    const cur = byNode[targetNodeId] || []
    // 검증 2: max_modules 초과
    if (cur.length >= stage.max_modules) {
      setToast(`이 Stage는 최대 ${stage.max_modules}개까지만 배치할 수 있습니다.`)
      return
    }
    // 검증 3: 같은 (function + dataset_role) 중복
    const dup = cur.find(
      (m) => m.function === payload.function && m.dataset_role === payload.hint_dataset,
    )
    if (dup) {
      setToast('이미 추가된 모듈입니다.')
      return
    }
    setByNode({
      ...byNode,
      [targetNodeId]: [...cur, { function: payload.function, dataset_role: payload.hint_dataset }],
    })
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
          function: m.function,
          dataset_role: m.dataset_role,
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
      navigate(`/pipeline/data?session=${sid}`)
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
        왼쪽 카탈로그에서 모듈을 끌어와 오른쪽 Stage 박스에 놓으세요. (현재 {totalModules}개 모듈 / {filledStages} Stage 채움)
      </p>

      <div className="pipeline-grid">
        <CatalogPanel lineDef={lineDef} />

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
