// DL-3b — 신규 Page 3 v2: 데이터 셀렉(카드, catalog 소스) + 제약 입력 (spec-1 §4-3, D-181/D-184).
// VITE_DL_UI_V2 플래그 뒤 별도 라우트(/pipeline/data-v2)에 마운트 — 구 Page 3 무접촉.
// - 데이터 소스 = GET /api/datalake/list (vid = session line_id 직사용, D-188)
// - 컬럼 소스 = GET /api/datalake/{id}/columns (D-90/D-161, __dupN 배지 = ColumnChips)
// - 제약 폼 = 구 ConstraintForm import 재사용만 (구 파일 무수정 — 3c에서 D-180/D-185
//   type별 폼(column_kind 렌더 분기·prefill)으로 교체 예정)
// - register 모달 UI = 3c 이월 (백엔드 Mode B 는 3a 완비, D-186)
// - 저장 shape = 구 {col: [min,max]} 유지 — 엔진(Planner/Validator) 무변경 (3c 룰링 전 동결)
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { get, put, dlColumns } from '../api.js'
import { resolveModality } from '../lib/modality.js'
import Toast from '../components/Toast.jsx'
import ConstraintForm from '../step3_user_input_data/ConstraintForm.jsx'
import DatalakeCardPicker from './DatalakeCardPicker.jsx'
import ColumnChips from './ColumnChips.jsx'

export default function DataSelectPageV2() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const sid = params.get('session') || ''
  const [structure, setStructure] = useState(null)
  const [linesCatalog, setLinesCatalog] = useState([])
  const [modulesCatalog, setModulesCatalog] = useState({})
  // {mk: {datalake_id, modality, constraintRows}} — modality 는 catalog entry 권위(D-163)
  const [moduleState, setModuleState] = useState({})
  const [columnsByDataset, setColumnsByDataset] = useState({})
  const [toast, setToast] = useState('')
  const [saving, setSaving] = useState(false)
  const [loadErr, setLoadErr] = useState('')

  useEffect(() => {
    if (!sid) return
    Promise.all([get(`/sessions/${sid}`), get('/lines'), get('/modules')])
      .then(([sess, linesResp, modulesResp]) => {
        const pf = sess.pipeline_full || { line_id: sess.line_id, stages: [] }
        setStructure(pf)
        setLinesCatalog(linesResp.lines || [])
        setModulesCatalog(modulesResp.modules || {})
        // 복원 — 구 페이지와 동일 shape ({col: [min,max]})
        const restored = {}
        for (const s of pf.stages || []) {
          for (const m of s.modules || []) {
            const mk = `${s.stage_order}.${m.index}`
            restored[mk] = {
              datalake_id: m.datalake_id || null,
              modality: m.modality || null,
              constraintRows: Object.entries(m.constraints || {}).map(([col, v]) => ({
                column: col,
                min: Array.isArray(v) && v[0] != null ? String(v[0]) : '',
                max: Array.isArray(v) && v[1] != null ? String(v[1]) : '',
              })),
            }
            if (m.datalake_id) fetchColumns(m.datalake_id)
          }
        }
        setModuleState(restored)
      })
      .catch((e) => setLoadErr(e.message || '로드 실패'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sid])

  async function fetchColumns(datalakeId) {
    if (!datalakeId || columnsByDataset[datalakeId]) return
    try {
      const r = await dlColumns(datalakeId)            // catalog 권위 (D-90/D-161)
      setColumnsByDataset((prev) => ({ ...prev, [datalakeId]: r.columns || [] }))
    } catch (e) {
      setToast(`컬럼 조회 실패 (${datalakeId}): ${e.message}`)
      setColumnsByDataset((prev) => ({ ...prev, [datalakeId]: [] }))
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
          // modality = 선택 entry 의 catalog 값 우선(권위, D-163), 미선택 시 구 규칙 폴백
          modality: st.modality || resolveModality(m, s.node_id),
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

  // 카드 셀렉(dlList fetch)은 모듈 단위 마운트로 발화 — 모듈 0개면 발화 자체가 없으므로
  // 침묵 렌더 대신 명시 안내 (Page 2 "다음"을 눌러야 PUT /structure 로 stages 저장됨)
  const nModules = (structure.stages || [])
    .reduce((n, s) => n + ((s.modules || []).length), 0)

  return (
    <div>
      <h1>{lineDef.display_name} — 데이터·제약 입력 <span style={{ fontSize: 13, color: '#2563eb' }}>(DL v2)</span></h1>
      <p className="muted">
        Data Lake catalog(vid={structure.line_id})에서 카드로 선택합니다.
        제약은 선택 데이터셋의 <strong>catalog 실컬럼</strong>에 매핑됩니다 (D-90/D-161).
      </p>

      {nModules === 0 && (
        <div className="error-text" style={{ padding: 12, border: '1px solid #f59e0b',
                                             borderRadius: 6, background: '#fffbeb' }}>
          ⚠ 이 세션에는 Page 2 구조가 저장돼 있지 않습니다
          (stages={`${(structure.stages || []).length}`}, modules=0).
          카드 셀렉은 모듈 단위로 표시됩니다 —{' '}
          <a href={`/pipeline/build?session=${sid}`}>Page 2(파이프라인 구성)</a>에서
          모듈을 추가하고 <strong>"다음"</strong>으로 저장한 뒤 다시 진입하세요.
        </div>
      )}

      <div className="page3-stage-list">
        {structure.stages.map((stage) => {
          const nodeDef = lineDef.stages.find((n) => n.node_id === stage.node_id)
          const ckeys = (modulesCatalog[stage.node_id] || {}).constraint_keys || []
          return (
            <section key={stage.node_id} className="page3-stage-card">
              <h2 className="page3-stage-title">
                Stage {stage.stage_order + 1}: {nodeDef?.display_name || stage.node_id}
              </h2>
              <div className="page3-modules">
                {(stage.modules || []).map((m) => {
                  const mk = `${stage.stage_order}.${m.index}`
                  const st = moduleState[mk] || {}
                  const allCols = st.datalake_id ? (columnsByDataset[st.datalake_id] || []) : []
                  // 제약 폼(range)은 scalar 만 — group(aggregate 폼)은 3c (D-180)
                  const scalarCols = allCols.filter((c) => c.column_kind !== 'group')
                  return (
                    <div key={mk} className="page3-module">
                      <div className="page3-module-header">
                        <span className={`module-fn fn-${m.function} module-fn-chip`}>
                          {m.function}
                        </span>
                        <span className="muted">dataset_role: {m.dataset_role || '?'}</span>
                      </div>
                      <DatalakeCardPicker
                        vid={structure.line_id}
                        moduleFunction={m.function}
                        value={st.datalake_id}
                        onChange={(entry) => {
                          if (!entry) {
                            setForModule(mk, { datalake_id: null, modality: null })
                            return
                          }
                          setForModule(mk, {
                            datalake_id: entry.datalake_id,
                            modality: entry.modality || null,
                          })
                          fetchColumns(entry.datalake_id)
                        }}
                      />
                      <ColumnChips columns={allCols} />
                      <ConstraintForm
                        datasetSelected={Boolean(st.datalake_id)}
                        columns={scalarCols}
                        hintKeys={ckeys}
                        rows={st.constraintRows || []}
                        onChange={(rows) => setForModule(mk, { constraintRows: rows })}
                      />
                      <div className="muted" style={{ marginTop: 6, fontSize: 11 }}>
                        신규 등록(register)은 추후 지원 — 현재는 사전 적재 catalog 선택 (D-186)
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          )
        })}
      </div>

      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <button className="btn btn-primary" onClick={onNext}
                disabled={saving || nModules === 0}>
          {saving ? '저장 중…' : '다음 → (Page 4 실행)'}
        </button>
      </div>

      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  )
}
