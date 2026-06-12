// DL-3b — Page 3 v2 데이터 셀렉 카드 (spec-1 §4-3, D-166/D-187).
// 소스 = GET /api/datalake/list (catalog 권위). vid = session line_id 직사용(D-188).
// function 기본값 = module.function, site 옵션 — 3축 AND 는 백엔드 쿼리로 수행.
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

export default function DatalakeCardPicker({ vid, moduleFunction, value, onChange }) {
  const [fnFilter, setFnFilter] = useState(moduleFunction || ALL)
  const [siteFilter, setSiteFilter] = useState(ALL)
  const [options, setOptions] = useState({ functions: [], sites: [] })
  const [entries, setEntries] = useState(null)   // null = 로딩
  const [err, setErr] = useState('')

  // vid 전체 1회 — function/site 드롭다운 옵션 도출용
  useEffect(() => {
    if (!vid) return
    dlList({ vid })
      .then((r) => {
        const es = r.entries || []
        setOptions({
          functions: [...new Set(es.map((e) => e.function).filter(Boolean))].sort(),
          sites: [...new Set(es.map((e) => e.site).filter(Boolean))].sort(),
        })
      })
      .catch((e) => setErr(e.message || 'catalog 로드 실패'))
  }, [vid])

  // 카드 필터 쿼리 — 3축 AND 는 서버(list_entries)가 수행 (D-166)
  useEffect(() => {
    if (!vid) return
    setEntries(null)
    dlList({
      vid,
      function: fnFilter === ALL ? null : fnFilter,
      site: siteFilter === ALL ? null : siteFilter,
    })
      .then((r) => setEntries(r.entries || []))
      .catch((e) => { setErr(e.message || 'catalog 조회 실패'); setEntries([]) })
  }, [vid, fnFilter, siteFilter])

  const selectStyle = { fontSize: 12, marginRight: 8 }
  const cards = useMemo(() => entries || [], [entries])

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
                  borderRadius: 6, minWidth: 180,
                  border: selected ? '2px solid #2563eb' : '1px solid #d1d5db',
                  background: selected ? '#eff6ff' : '#fff',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13 }}>{e.name}</div>
                <div className="muted" style={{ fontSize: 11 }}>
                  {e.datalake_id} · {e.modality} · {fmtSize(e.size_bytes)}
                </div>
                <div className="muted" style={{ fontSize: 11 }}>
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
