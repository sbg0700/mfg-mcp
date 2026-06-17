import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { get, put } from '../api.js'
import StageBox from './StageBox.jsx'
import Toast from '../components/Toast.jsx'

// Page 2 — 파이프라인 구성 (가로 단계 흐름 + 하단 기능 팔레트 + 단계 안 P-M 중첩).
// 모델: byNode[node_id] = [{uid, function, attached_to}]  (데이터 미바인딩 — Page 3에서 선택)
//   P(process): 세로 체인. 저장 시 chain_order = P 등장 순서.
//   M/Q(maintenance/quality): 특정 P에 부착(attached_to = 그 P의 uid → 저장 시 P의 chain_order).
//   R(reference): 독립.
// 저장 PUT /structure: 모듈 {index, function, chain_order(P만), attached_to(M/Q만)}.
//   dataset_role 미설정(데이터는 Page 3). 백엔드는 structure 를 verbatim 저장(무변경).
const FUNCTIONS = [
  { id: 'process',     ko: '공정',      en: 'process',     icon: '⚙️' },
  { id: 'quality',     ko: '품질',      en: 'quality',     icon: '🔍' },
  { id: 'maintenance', ko: '설비·보전', en: 'maintenance', icon: '🔧' },
  { id: 'reference',   ko: '참조',      en: 'reference',   icon: '📘' },
]
const ATTACHABLE = new Set(['quality', 'maintenance'])

export default function PipelineBuildPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const sid = params.get('session') || ''
  const [lineId, setLineId] = useState('')
  const [lineDef, setLineDef] = useState(null)
  const [byNode, setByNode] = useState({})        // node_id → [{uid, function, attached_to}]
  const [toast, setToast] = useState('')
  const [saving, setSaving] = useState(false)
  const [loadErr, setLoadErr] = useState('')
  const uidRef = useRef(0)
  const newUid = () => `m${uidRef.current++}`

  // 진입 시 세션 + 카탈로그 로드, 저장된 구조(있으면) 복원 — chain_order/attached_to → 중첩 재구성
  useEffect(() => {
    if (!sid) return
    Promise.all([get(`/sessions/${sid}`), get('/lines')])
      .then(([sess, linesResp]) => {
        const lid = sess.line_id || sess.pipeline_full?.line_id || ''
        setLineId(lid)
        const def = (linesResp.lines || []).find((l) => l.line_id === lid)
        if (!def) { setLoadErr(`Line '${lid}'을(를) 카탈로그에서 찾을 수 없습니다.`); return }
        setLineDef(def)

        const restored = {}
        for (const s of sess.pipeline_full?.stages || []) {
          const mods = s.modules || []
          const pByChain = new Map()
          const rebuilt = mods.map((m) => {
            const uid = newUid()
            if (m.function === 'process' && m.chain_order != null) pByChain.set(m.chain_order, uid)
            return { uid, function: m.function, attached_to: null, _att: m.attached_to }
          })
          for (const rm of rebuilt) {
            if (ATTACHABLE.has(rm.function) && rm._att != null) rm.attached_to = pByChain.get(rm._att) ?? null
            delete rm._att
          }
          restored[s.node_id] = rebuilt
        }
        setByNode(restored)
      })
      .catch((e) => setLoadErr(e.message || '세션/카탈로그 로드 실패'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sid])

  function onPaletteDragStart(e, fn) {
    e.dataTransfer.setData('application/json', JSON.stringify({ function: fn }))
    e.dataTransfer.effectAllowed = 'copy'
  }

  // 단계에 모듈 추가 (max_modules 초과 시 거부 + 토스트). 추가 성공 여부 반환.
  function addModule(nodeId, mod) {
    const stage = lineDef.stages.find((s) => s.node_id === nodeId)
    if (!stage) return false
    const cur = byNode[nodeId] || []
    if (cur.length >= stage.max_modules) {
      setToast(`이 단계는 최대 ${stage.max_modules}개까지만 배치할 수 있습니다.`)
      return false
    }
    setByNode({ ...byNode, [nodeId]: [...cur, mod] })
    return true
  }

  // 단계 본문 일반 드롭: P/R = 추가, M·Q = 마지막 P에 부착(P 없으면 토스트).
  function onDropStage(nodeId, payload) {
    const fn = payload?.function
    if (!fn) return
    if (fn === 'process' || fn === 'reference') {
      addModule(nodeId, { uid: newUid(), function: fn, attached_to: null })
      return
    }
    const ps = (byNode[nodeId] || []).filter((m) => m.function === 'process')
    if (ps.length === 0) { setToast('공정(P)을 먼저 배치하세요 — 품질·보전은 공정에 부착됩니다.'); return }
    addModule(nodeId, { uid: newUid(), function: fn, attached_to: ps[ps.length - 1].uid })
  }

  // P 카드 위 드롭: M·Q = 그 P에 부착 / P·R = 일반 추가.
  function onDropP(nodeId, pUid, payload) {
    const fn = payload?.function
    if (!fn) return
    if (ATTACHABLE.has(fn)) addModule(nodeId, { uid: newUid(), function: fn, attached_to: pUid })
    else addModule(nodeId, { uid: newUid(), function: fn, attached_to: null })
  }

  // 모듈 제거 — P 제거 시 그 P에 부착된 M/Q 도 함께 제거(dangling 방지).
  function onRemove(nodeId, uid) {
    const cur = byNode[nodeId] || []
    const target = cur.find((m) => m.uid === uid)
    let next = cur.filter((m) => m.uid !== uid)
    if (target?.function === 'process') next = next.filter((m) => m.attached_to !== uid)
    setByNode({ ...byNode, [nodeId]: next })
  }

  async function onNext() {
    if (!lineDef) return
    const stages = lineDef.stages.map((s, idx) => {
      const mods = byNode[s.node_id] || []
      const chainOf = new Map(mods.filter((m) => m.function === 'process').map((m, i) => [m.uid, i]))
      const modules = mods.map((m, i) => {
        const base = { index: i, function: m.function }
        if (m.function === 'process') return { ...base, chain_order: chainOf.get(m.uid), attached_to: null }
        if (ATTACHABLE.has(m.function)) {
          return { ...base, chain_order: null, attached_to: chainOf.has(m.attached_to) ? chainOf.get(m.attached_to) : null }
        }
        return { ...base, chain_order: null, attached_to: null }   // reference
      })
      return { stage_order: idx, node_id: s.node_id, modules }
    }).filter((s) => s.modules.length > 0)

    if (stages.length === 0) { setToast('최소 1개 단계에 1개 이상의 모듈이 필요합니다.'); return }

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

  if (!sid) return <div>세션 ID가 없습니다. <a href="/">처음으로</a></div>
  if (loadErr) return <div className="error-text">⚠ {loadErr}</div>
  if (!lineDef) return <div className="muted">로딩 중…</div>

  const totalModules = Object.values(byNode).reduce((n, arr) => n + arr.length, 0)
  const filledStages = lineDef.stages.filter((s) => (byNode[s.node_id] || []).length > 0).length

  return (
    <div className="p2-wrap">
      <div className="p2-header">
        <h1>{lineDef.display_name}</h1>
        <p className="muted">
          파이프라인 구성 — 아래 기능을 끌어 단계에 놓으세요. 데이터 선택은 다음 단계(Page 3).
          <span className="p2-counter"> {totalModules}개 모듈 · {filledStages}/{lineDef.stages.length}단계 채움</span>
        </p>
      </div>

      <div className="flow-row">
        {lineDef.stages.map((s, idx) => (
          <div key={s.node_id} className="flow-cell">
            <StageBox
              stage={s}
              index={idx}
              modules={byNode[s.node_id] || []}
              onDropStage={onDropStage}
              onDropP={onDropP}
              onRemove={onRemove}
            />
            {idx < lineDef.stages.length - 1 && <div className="flow-arrow">→</div>}
          </div>
        ))}
      </div>

      <div className="palette-bar">
        <span className="palette-label">기능 팔레트</span>
        {FUNCTIONS.map((f) => (
          <div key={f.id} className={`palette-card fn-${f.id}`} draggable
               onDragStart={(e) => onPaletteDragStart(e, f.id)} title={f.en}>
            <span className="palette-icon">{f.icon}</span>
            <span className="palette-text">
              <span className="palette-ko">{f.ko}</span>
              <span className="palette-en">{f.en}</span>
            </span>
          </div>
        ))}
        <button className="btn btn-primary palette-next" onClick={onNext} disabled={saving}>
          {saving ? '저장 중…' : '다음 → (Page 3)'}
        </button>
      </div>

      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  )
}
