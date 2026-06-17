// DL-3b/3c — 신규 Page 3 v2: 데이터 셀렉(카드, catalog 소스) + 제약 폼 (spec-1 §4-3/§4-4).
// VITE_DL_UI_V2 플래그 뒤 별도 라우트(/pipeline/data-v2)에 마운트 — 구 Page 3 무접촉.
// - 데이터 소스 = GET /api/datalake/list (vid = session line_id 직사용, D-188)
// - 컬럼 소스 = GET /api/datalake/{id}/columns (D-90/D-161, __dupN 배지 = ColumnChips)
// - 제약 폼 = ConstraintFormV2 (3c, D-167/D-180/D-190/D-191): column_kind 렌더 분기 +
//   prefill 재승인 게이트(merge view 소스) + [이번만]/[메모리 업데이트(영속)] 분기 모달
// - 저장 = PUT /api/datalake/sessions/{sid}/full — constraints_v2(canonical) 동반,
//   백엔드가 엔진용 구 shape {col:[min,max]} 로 다운컨버트 + engine_excluded 메타 (D-189)
// - register 모달 UI = 3c 범위 외 (D-191 — 백엔드 Mode B 는 3a 완비, D-186)
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { get, dlList, dlColumns, dlConstraintMerge, dlSessionPutFull } from '../api.js'
import { resolveModality } from '../lib/modality.js'
import Toast from '../components/Toast.jsx'
import ConstraintFormV2 from './ConstraintFormV2.jsx'
import DatalakeCardPicker from './DatalakeCardPicker.jsx'
import ColumnChips from './ColumnChips.jsx'

const COMPANY_ALL = '__all__'   // D-212: 상단 회사 셀렉터 "전체"(필터 미적용) 센티넬

// 3b 세션 호환 — 구 shape {col:[min,max]} → canonical range (충실 변환, silent drop 0)
function upconvertLegacy(constraints) {
  const out = {}
  for (const [col, v] of Object.entries(constraints || {})) {
    if (Array.isArray(v)) {
      out[col] = { type: 'range', min: v[0] ?? null, max: v[1] ?? null, unit: null }
    }
  }
  return out
}

export default function DataSelectPageV2() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const sid = params.get('session') || ''
  const [structure, setStructure] = useState(null)
  const [linesCatalog, setLinesCatalog] = useState([])
  // {mk: {datalake_id, modality, cmap, merged}} — modality 는 catalog entry 권위(D-163),
  // cmap = {col: canonical_spec}(세션 적용분), merged = constraint_merge rows(prefill 제안 소스)
  const [moduleState, setModuleState] = useState({})
  const [columnsByDataset, setColumnsByDataset] = useState({})
  const [toast, setToast] = useState('')
  const [saving, setSaving] = useState(false)
  const [loadErr, setLoadErr] = useState('')
  // D-212: 상단 회사 셀렉터 — 옵션 = 현재 vid 데이터의 distinct company, 기본 "전체"(필터 없음)
  const [company, setCompany] = useState(COMPANY_ALL)
  const [companyOptions, setCompanyOptions] = useState([])

  useEffect(() => {
    if (!sid) return
    Promise.all([get(`/sessions/${sid}`), get('/lines')])
      .then(([sess, linesResp]) => {
        const pf = sess.pipeline_full || { line_id: sess.line_id, stages: [] }
        setStructure(pf)
        setLinesCatalog(linesResp.lines || [])
        const restored = {}
        for (const s of pf.stages || []) {
          for (const m of s.modules || []) {
            const mk = `${s.stage_order}.${m.index}`
            restored[mk] = {
              datalake_id: m.datalake_id || null,
              modality: m.modality || null,
              // 복원: constraints_v2(canonical) 우선, 부재 시 3b 구 shape 업컨버트
              cmap: m.constraints_v2 || upconvertLegacy(m.constraints),
              merged: null,
            }
            if (m.datalake_id) {
              fetchColumns(m.datalake_id)
              fetchMerge(mk, m.datalake_id)
            }
          }
        }
        setModuleState(restored)
      })
      .catch((e) => setLoadErr(e.message || '로드 실패'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sid])

  // D-212: 현재 vid(라인) 데이터의 distinct company → 셀렉터 옵션. 비거나 1종이어도 무해.
  useEffect(() => {
    const vid = structure?.line_id
    if (!vid) return
    dlList({ vid })
      .then((r) => {
        const cs = [...new Set((r.entries || []).map((e) => e.company).filter(Boolean))].sort()
        setCompanyOptions(cs)
      })
      .catch(() => setCompanyOptions([]))
  }, [structure?.line_id])

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

  // 머지 3케이스 결과 (D-167) — prefill 은 제안만(재승인 게이트), 값 자동 주입 0
  async function fetchMerge(mk, datalakeId) {
    try {
      const r = await dlConstraintMerge(sid, mk, datalakeId)
      setModuleState((prev) => ({
        ...prev, [mk]: { ...(prev[mk] || {}), merged: r.merged || [] },
      }))
    } catch (e) {
      setToast(`prefill 조회 실패 (${datalakeId}): ${e.message}`)
    }
  }

  const lineDef = useMemo(() => {
    if (!structure) return null
    return linesCatalog.find((l) => l.line_id === structure.line_id) || null
  }, [structure, linesCatalog])

  function setForModule(mk, patch) {
    setModuleState((prev) => ({ ...prev, [mk]: { ...(prev[mk] || {}), ...patch } }))
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
          constraints_v2: st.cmap || {},   // 다운컨버트·engine_excluded 는 백엔드 (D-189)
        }
      }),
    }))
    setSaving(true)
    try {
      const r = await dlSessionPutFull(sid, { line_id: structure.line_id, stages })
      const nEx = (r.engine_excluded || []).length
      if (nEx > 0) {
        setToast(`저장 완료 — 비-range 제약 ${nEx}건은 엔진 전달 제외(메타 기록, D-189)`)
      }
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
        제약은 선택 데이터셋의 <strong>catalog 실컬럼</strong>에 매핑되며,
        카탈로그 prefill 은 <strong>승인 시에만</strong> 적용됩니다 (D-167 재승인 게이트).
      </p>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '4px 0 16px' }}>
        <label className="muted" style={{ fontSize: 13 }}>회사(company)</label>
        <select value={company} onChange={(e) => setCompany(e.target.value)}
                style={{ fontSize: 13, padding: '2px 6px' }}>
          <option value={COMPANY_ALL}>전체</option>
          {companyOptions.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="muted" style={{ fontSize: 12 }}>
          선택한 회사 데이터로 각 공정 카드를 거릅니다 (전체 = 미적용).
        </span>
      </div>

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
                        company={company === COMPANY_ALL ? null : company}
                        value={st.datalake_id}
                        onChange={(entry) => {
                          if (!entry) {
                            setForModule(mk, { datalake_id: null, modality: null,
                                               cmap: {}, merged: null })
                            return
                          }
                          // 데이터셋 변경 = 구 세션 제약 무효 (merge view 도 동일 규칙)
                          setForModule(mk, {
                            datalake_id: entry.datalake_id,
                            modality: entry.modality || null,
                            cmap: {}, merged: null,
                          })
                          fetchColumns(entry.datalake_id)
                          fetchMerge(mk, entry.datalake_id)
                        }}
                      />
                      <ColumnChips columns={allCols} />
                      <ConstraintFormV2
                        datalakeId={st.datalake_id}
                        columns={allCols}
                        merged={st.merged}
                        cmap={st.cmap || {}}
                        onChange={(cmap) => setForModule(mk, { cmap })}
                        onToast={setToast}
                        onPersisted={() => fetchMerge(mk, st.datalake_id)}
                      />
                      <div className="muted" style={{ marginTop: 6, fontSize: 11 }}>
                        신규 등록(register)은 추후 지원 — 현재는 사전 적재 catalog 선택 (D-186/D-191)
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
