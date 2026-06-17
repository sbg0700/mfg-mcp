// DL-3b — Page 3 v2 데이터 셀렉 카드 (spec-1 §4-3, D-166/D-187/D-211).
// 소스 = GET /api/datalake/list (catalog 권위). vid = session line_id 직사용(D-188).
// D-211 깔때기 잠금: datasetRole(Page 2에서 놓은 datalake_id)이 오면 후보 목록·필터를
//   숨기고 그 1건으로 자동 고정(잠금). 미지정 시 종전 3축(vid+function+site) 카드 피커.
import { useEffect, useMemo, useState } from 'react'
import { dlList } from '../api.js'

function fmtSize(n) {
  if (n == null) return '?'
  let v = Number(n)
  for (const u of ['B', 'KB', 'MB']) {
    if (v < 1024) return `${u === 'B' ? v : v.toFixed(1)}${u}`
    v /= 1024
  }
  return `${v.toFixed(1)}GB`
}

const ALL = '__all__'

export default function DatalakeCardPicker({ vid, moduleFunction, datasetRole, value, onChange }) {
  const locked = !!datasetRole                  // D-211: dataset_role 있으면 잠금 모드
  const [fnFilter, setFnFilter] = useState(moduleFunction || ALL)
  const [siteFilter, setSiteFilter] = useState(ALL)
  const [options, setOptions] = useState({ functions: [], sites: [] })
  const [entries, setEntries] = useState(null)   // null = 로딩
  const [err, setErr] = useState('')

  // vid 전체 1회 — function/site 드롭다운 옵션 도출용 (잠금 모드에선 드롭다운 비표시 → 생략)
  useEffect(() => {
    if (!vid || locked) return
    dlList({ vid })
      .then((r) => {
        const es = r.entries || []
        setOptions({
          functions: [...new Set(es.map((e) => e.function).filter(Boolean))].sort(),
          sites: [...new Set(es.map((e) => e.site).filter(Boolean))].sort(),
        })
      })
      .catch((e) => setErr(e.message || 'catalog 로드 실패'))
  }, [vid, locked])

  // 카드 필터 쿼리 — 잠금 모드는 vid 전체에서 dataset_role 1건을 찾으므로 fn/site 미적용.
  // 미잠금 모드는 종전 3축 AND(서버 list_entries 수행, D-166).
  useEffect(() => {
    if (!vid) return
    setEntries(null)
    dlList(locked
      ? { vid }
      : { vid,
          function: fnFilter === ALL ? null : fnFilter,
          site: siteFilter === ALL ? null : siteFilter })
      .then((r) => setEntries(r.entries || []))
      .catch((e) => { setErr(e.message || 'catalog 조회 실패'); setEntries([]) })
  }, [vid, locked, fnFilter, siteFilter])

  const selectStyle = { fontSize: 12, marginRight: 8 }
  const cards = useMemo(() => entries || [], [entries])

  // 잠금 모드: 받은 목록에서 datalake_id === dataset_role 인 단일 항목만.
  const lockedEntry = useMemo(
    () => (locked && entries ? entries.find((e) => e.datalake_id === datasetRole) || null : null),
    [locked, entries, datasetRole])

  // 잠금 모드 자동 선택 — 마운트/로드 시 1회(기존 클릭과 동일한 onChange). value 가드로 무한루프 차단.
  useEffect(() => {
    if (!locked || !lockedEntry) return
    if (value !== lockedEntry.datalake_id) {
      // 자가검증: 자동 선택 datalake_id 가 dataset_role 과 일치하는지 1줄 로그
      // eslint-disable-next-line no-console
      console.log(`[D-211 lock] auto-select=${lockedEntry.datalake_id} dataset_role=${datasetRole} match=${lockedEntry.datalake_id === datasetRole}`)
      onChange(lockedEntry)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked, lockedEntry, value])

  // ── 잠금 모드 렌더 (후보 숨김·필터 숨김·변경 불가) ─────────────────────────
  if (locked) {
    return (
      <div className="dlv2-picker" style={{ marginTop: 6 }}>
        {err && <div className="error-text">⚠ {err}</div>}
        {entries === null ? (
          <div className="muted">catalog 로딩 중…</div>
        ) : !lockedEntry ? (
          <div className="error-text" style={{ padding: '8px 10px', borderRadius: 6,
                          border: '1px solid #f59e0b', background: '#fffbeb', color: '#92400e' }}>
            ⚠ 데이터를 찾을 수 없습니다 — Page 2에서 지정한 데이터(dataset_role=
            <code>{datasetRole}</code>)가 이 라인(vid={vid}) catalog 에 없습니다.
          </div>
        ) : (
          <div
            style={{
              textAlign: 'left', padding: '8px 10px', borderRadius: 6, minWidth: 180,
              display: 'inline-block',
              border: '2px solid #2563eb', background: '#eff6ff', color: '#1f2937',
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 13 }}>
              {lockedEntry.name}
              <span style={{ marginLeft: 6, fontSize: 10, padding: '1px 6px', borderRadius: 8,
                             background: '#dbeafe', border: '1px solid #2563eb', color: '#1e3a8a' }}>
                Page 2에서 고정
              </span>
            </div>
            <div style={{ fontSize: 11, color: '#475569' }}>
              {lockedEntry.datalake_id} · {lockedEntry.modality} · {fmtSize(lockedEntry.size_bytes)}
            </div>
            <div style={{ fontSize: 11, color: '#475569' }}>
              function={lockedEntry.function || '?'} · site={lockedEntry.site || '?'}
            </div>
          </div>
        )}
      </div>
    )
  }

  // ── 미잠금(종전) 렌더 — 3축 후보 카드 피커 ──────────────────────────────────
  return (
    <div className="dlv2-picker" style={{ marginTop: 6 }}>
      <div style={{ marginBottom: 6 }}>
        <label className="muted" style={{ fontSize: 12, marginRight: 4 }}>function</label>
        <select style={selectStyle} value={fnFilter} onChange={(e) => setFnFilter(e.target.value)}>
          <option value={ALL}>(전체)</option>
          {options.functions.map((f) => <option key={f} value={f}>{f}</option>)}
        </select>
        <label className="muted" style={{ fontSize: 12, marginRight: 4 }}>site</label>
        <select style={selectStyle} value={siteFilter} onChange={(e) => setSiteFilter(e.target.value)}>
          <option value={ALL}>(전체)</option>
          {options.sites.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <span className="muted" style={{ fontSize: 11 }}>
          vid={vid} (Page 1 라인 = vid 직사용, D-188)
        </span>
      </div>
      {err && <div className="error-text">⚠ {err}</div>}
      {entries === null ? (
        <div className="muted">catalog 로딩 중…</div>
      ) : cards.length === 0 ? (
        <div className="muted">조건에 맞는 데이터셋이 없습니다 (필터를 넓혀 보세요).</div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {cards.map((e) => {
            const selected = value === e.datalake_id
            return (
              <button
                key={e.datalake_id}
                type="button"
                onClick={() => onChange(selected ? null : e)}
                style={{
                  textAlign: 'left', cursor: 'pointer', padding: '8px 10px',
                  borderRadius: 6, minWidth: 180, color: '#1f2937',
                  border: selected ? '2px solid #2563eb' : '1px solid #d1d5db',
                  background: selected ? '#eff6ff' : '#fff',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13 }}>{e.name}</div>
                <div style={{ fontSize: 11, color: '#475569' }}>
                  {e.datalake_id} · {e.modality} · {fmtSize(e.size_bytes)}
                </div>
                <div style={{ fontSize: 11, color: '#475569' }}>
                  function={e.function || '?'} · site={e.site || '?'}
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
