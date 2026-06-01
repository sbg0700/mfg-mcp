import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { get, put } from '../api.js'
import { resolveModality } from '../lib/modality.js'
import Toast from '../components/Toast.jsx'
import DatasetSelector from './DatasetSelector.jsx'
import ConstraintForm from './ConstraintForm.jsx'

// Page 3 — 데이터·제약 입력 (spec-1 Part 4).
// Page 2 structure 복원 → 각 모듈에 데이터셋 + 제약 입력 → pipeline_full 완성 → PUT /full → Page 4.
export default function DataConstraintPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const sid = params.get('session') || ''
  const [structure, setStructure] = useState(null)   // pipeline_full from Page 2 (skeleton)
  const [linesCatalog, setLinesCatalog] = useState([])
  const [datasetsByModality, setDatasetsByModality] = useState({})
  const [modulesCatalog, setModulesCatalog] = useState({})  // modules.yaml content
  const [moduleState, setModuleState] = useState({})  // {"so.idx": {datalake_id, constraintsRaw}}
  const [toast, setToast] = useState('')
  const [saving, setSaving] = useState(false)
  const [loadErr, setLoadErr] = useState('')

  // 진입 시 4종 동시 로드
  useEffect(() => {
    if (!sid) return
    Promise.all([
      get(`/sessions/${sid}`),
      get('/lines'),
      get('/datasets/all'),
      get('/modules'),
    ])
      .then(([sess, linesResp, datasetsResp, modulesResp]) => {
        const pf = sess.pipeline_full || { line_id: sess.line_id, stages: [] }
        setStructure(pf)
        setLinesCatalog(linesResp.lines || [])
        setDatasetsByModality(datasetsResp.datasets_by_modality || {})
        setModulesCatalog(modulesResp.modules || {})

        // 복원: 이전 Page 3에서 저장한 적 있으면 datalake_id + constraints 복원
        const restored = {}
        for (const s of pf.stages || []) {
          for (const m of s.modules || []) {
            const mk = `${s.stage_order}.${m.index}`
            const raw = {}
            for (const [k, v] of Object.entries(m.constraints || {})) {
              if (Array.isArray(v) && v.length >= 2) {
                raw[k] = { min: v[0] != null ? String(v[0]) : '', max: v[1] != null ? String(v[1]) : '' }
              }
            }
            restored[mk] = {
              datalake_id: m.datalake_id || null,
              constraintsRaw: raw,
            }
          }
        }
        setModuleState(restored)
      })
      .catch((e) => setLoadErr(e.message || '로드 실패'))
  }, [sid])

  // line 카탈로그에서 현재 라인 정의
  const lineDef = useMemo(() => {
    if (!structure) return null
    return linesCatalog.find((l) => l.line_id === structure.line_id) || null
  }, [structure, linesCatalog])

  function setForModule(mk, patch) {
    setModuleState((prev) => ({ ...prev, [mk]: { ...(prev[mk] || {}), ...patch } }))
  }

  // raw constraintsRaw ({key:{min,max}}) → 백엔드 형식 ({key:[min,max]}) 변환.
  // 둘 다 비면 키 자체 생략. 한쪽만 있으면 다른쪽은 null로(개방형 범위 허용).
  function toBackendConstraints(raw) {
    const out = {}
    for (const [k, v] of Object.entries(raw || {})) {
      const minS = (v?.min ?? '').toString().trim()
      const maxS = (v?.max ?? '').toString().trim()
      if (!minS && !maxS) continue
      const minN = minS === '' ? null : Number(minS)
      const maxN = maxS === '' ? null : Number(maxS)
      // 숫자 변환 실패는 그대로 null로 (백엔드 _bounds가 None으로 흡수)
      out[k] = [Number.isFinite(minN) ? minN : null, Number.isFinite(maxN) ? maxN : null]
    }
    return out
  }

  async function onNext() {
    if (!structure || !lineDef) return
    // pipeline_full 완성: stage 그대로 + 각 module에 modality/datalake_id/constraints 채움
    const stages = structure.stages.map((s) => {
      const nodeId = s.node_id
      return {
        stage_order: s.stage_order,
        node_id: nodeId,
        modules: (s.modules || []).map((m) => {
          const mk = `${s.stage_order}.${m.index}`
          const st = moduleState[mk] || {}
          return {
            index: m.index,
            function: m.function,
            modality: resolveModality(m, nodeId),
            dataset_role: m.dataset_role,
            datalake_id: st.datalake_id || null,
            constraints: toBackendConstraints(st.constraintsRaw),
          }
        }),
      }
    })

    setSaving(true)
    try {
      const r = await put(`/sessions/${sid}/full`, {
        pipeline_full: { line_id: structure.line_id, stages },
      })
      // PUT 응답에 modules_with_data가 0이어도 이동 — Page 4가 알람 처리
      void r
      navigate(`/pipeline/run?session=${sid}`)
    } catch (e) {
      setToast(`저장 실패: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  if (!sid) return <div>세션 ID가 없습니다. <a href="/">처음으로</a></div>
  if (loadErr) return <div className="error-text">⚠ {loadErr}</div>
  if (!structure || !lineDef) return <div className="muted">로딩 중…</div>

  return (
    <div>
      <h1>{lineDef.display_name} — 데이터·제약 입력</h1>
      <p className="muted">
        각 모듈에 데이터셋을 연결하고 (선택), 모달리티에 맞는 제약 조건을 입력합니다.
        데이터 미선택 모듈은 Page 4에서 알람 대상이 됩니다.
      </p>

      <div className="page3-stage-list">
        {structure.stages.map((stage) => {
          const nodeDef = lineDef.stages.find((n) => n.node_id === stage.node_id)
          const nodeMod = modulesCatalog[stage.node_id] || {}
          const ckeys = nodeMod.constraint_keys || []
          return (
            <section key={stage.node_id} className="page3-stage-card">
              <h2 className="page3-stage-title">
                Stage {stage.stage_order + 1}: {nodeDef?.display_name || stage.node_id}
              </h2>
              <div className="page3-modules">
                {(stage.modules || []).map((m) => {
                  const mk = `${stage.stage_order}.${m.index}`
                  const modality = resolveModality(m, stage.node_id)
                  const datasets = datasetsByModality[modality] || []
                  const st = moduleState[mk] || {}
                  return (
                    <div key={mk} className="page3-module">
                      <div className="page3-module-header">
                        <span className={`module-fn fn-${m.function} module-fn-chip`}>
                          {m.function}
                        </span>
                        <span className="muted">
                          dataset_role: {m.dataset_role || '?'}
                        </span>
                      </div>
                      <DatasetSelector
                        modality={modality}
                        datasets={datasets}
                        value={st.datalake_id}
                        onChange={(v) => setForModule(mk, { datalake_id: v })}
                      />
                      <ConstraintForm
                        constraintKeys={ckeys}
                        value={st.constraintsRaw}
                        onChange={(v) => setForModule(mk, { constraintsRaw: v })}
                      />
                      <button
                        className="btn"
                        style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}
                        onClick={() => setToast('데이터 업로드는 추후 STEP에서 지원됩니다.')}
                        type="button"
                      >
                        + 데이터 업로드 (추후 지원)
                      </button>
                    </div>
                  )
                })}
              </div>
            </section>
          )
        })}
      </div>

      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <button className="btn btn-primary" onClick={onNext} disabled={saving}>
          {saving ? '저장 중…' : '다음 → (Page 4 실행)'}
        </button>
      </div>

      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  )
}
