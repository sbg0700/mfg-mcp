import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { get, put } from '../api.js'
import { resolveModality } from '../lib/modality.js'
import Toast from '../components/Toast.jsx'
import DatasetSelector from './DatasetSelector.jsx'
import ConstraintForm from './ConstraintForm.jsx'

// Page 3 — 데이터·제약 입력 (spec-1 Part 4).
// STEP 1B-3c (D-90 해결): 제약폼이 데이터셋의 실제 컬럼 드롭다운으로 동작.
// Page 2 structure 복원 → 각 모듈에 데이터셋 + 제약(실 컬럼) 입력 → pipeline_full → PUT /full → Page 4.
export default function DataConstraintPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const sid = params.get('session') || ''
  const [structure, setStructure] = useState(null)
  const [linesCatalog, setLinesCatalog] = useState([])
  const [datasetsByModality, setDatasetsByModality] = useState({})
  const [modulesCatalog, setModulesCatalog] = useState({})
  const [moduleState, setModuleState] = useState({})       // {mk: {datalake_id, constraintRows}}
  const [columnsByDataset, setColumnsByDataset] = useState({})   // cache: {dataset_id: [{name,dtype}]}
  const [toast, setToast] = useState('')
  const [saving, setSaving] = useState(false)
  const [loadErr, setLoadErr] = useState('')

  // 초기 로드 — 세션 + 카탈로그
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

        // 복원 — 저장된 (datalake_id, constraints dict) → (datalake_id, constraintRows 리스트)
        const restored = {}
        const datasetsToFetch = new Set()
        for (const s of pf.stages || []) {
          for (const m of s.modules || []) {
            const mk = `${s.stage_order}.${m.index}`
            const rows = Object.entries(m.constraints || {}).map(([col, v]) => ({
              column: col,
              min: Array.isArray(v) && v[0] != null ? String(v[0]) : '',
              max: Array.isArray(v) && v[1] != null ? String(v[1]) : '',
            }))
            restored[mk] = {
              datalake_id: m.datalake_id || null,
              constraintRows: rows,
            }
            if (m.datalake_id) {
              datasetsToFetch.add(JSON.stringify({
                d: m.datalake_id,
                mod: resolveModality(m, s.node_id),
              }))
            }
          }
        }
        setModuleState(restored)
        // 복원된 데이터셋의 컬럼도 비동기 로드
        for (const j of datasetsToFetch) {
          const { d, mod } = JSON.parse(j)
          fetchColumns(d, mod)
        }
      })
      .catch((e) => setLoadErr(e.message || '로드 실패'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sid])

  async function fetchColumns(datasetId, modality) {
    if (!datasetId) return
    if (columnsByDataset[datasetId]) return    // 캐시 hit
    try {
      const r = await get(`/datasets/${encodeURIComponent(datasetId)}/columns?modality=${encodeURIComponent(modality)}`)
      setColumnsByDataset((prev) => ({ ...prev, [datasetId]: r.columns || [] }))
    } catch (e) {
      setToast(`컬럼 조회 실패 (${datasetId}): ${e.message}`)
      setColumnsByDataset((prev) => ({ ...prev, [datasetId]: [] }))
    }
  }

  const lineDef = useMemo(() => {
    if (!structure) return null
    return linesCatalog.find((l) => l.line_id === structure.line_id) || null
  }, [structure, linesCatalog])

  function setForModule(mk, patch) {
    setModuleState((prev) => ({ ...prev, [mk]: { ...(prev[mk] || {}), ...patch } }))
  }

  function rowsToConstraints(rows) {
    const out = {}
    for (const r of rows || []) {
      if (!r.column) continue
      const minS = (r.min ?? '').trim()
      const maxS = (r.max ?? '').trim()
      if (!minS && !maxS) continue
      const minN = minS === '' ? null : Number(minS)
      const maxN = maxS === '' ? null : Number(maxS)
      out[r.column] = [
        Number.isFinite(minN) ? minN : null,
        Number.isFinite(maxN) ? maxN : null,
      ]
    }
    return out
  }

  async function onNext() {
    if (!structure || !lineDef) return
    const stages = structure.stages.map((s) => ({
      stage_order: s.stage_order,
      node_id: s.node_id,
      modules: (s.modules || []).map((m) => {
        const mk = `${s.stage_order}.${m.index}`
        const st = moduleState[mk] || {}
        return {
          index: m.index,
          function: m.function,
          modality: resolveModality(m, s.node_id),
          dataset_role: m.dataset_role,
          datalake_id: st.datalake_id || null,
          constraints: rowsToConstraints(st.constraintRows),
        }
      }),
    }))
    setSaving(true)
    try {
      await put(`/sessions/${sid}/full`, {
        pipeline_full: { line_id: structure.line_id, stages },
      })
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
        각 모듈에 데이터셋을 연결 후, 그 데이터셋의 <strong>실제 컬럼</strong>에 제약을 매핑합니다 (D-90 해결).
        미선택 모듈은 Page 4에서 알람 대상이 됩니다.
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
                  const dsCols = st.datalake_id ? (columnsByDataset[st.datalake_id] || []) : []
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
                        onChange={(v) => {
                          setForModule(mk, { datalake_id: v })
                          if (v) fetchColumns(v, modality)
                        }}
                      />
                      <ConstraintForm
                        datasetSelected={Boolean(st.datalake_id)}
                        columns={dsCols}
                        hintKeys={ckeys}
                        rows={st.constraintRows || []}
                        onChange={(rows) => setForModule(mk, { constraintRows: rows })}
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
