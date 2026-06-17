// DL-3b — Page 3 v2 데이터 셀렉 카드 (spec-1 §4-3, D-166/D-212).
// 소스 = GET /api/datalake/list (catalog 권위). vid = session line_id 직사용(D-188).
// 필터 = vid + 모듈 function(고정) + 페이지 company(상단 셀렉터, 전체면 null=미적용).
// D-212: D-211(가) 잠금 폐기 — Page 2가 데이터를 안 고르므로 사용자가 카드로 직접 선택.
//   (잠금 모드·자동선택·"Page 2에서 고정" 배지·카드별 function/site 드롭다운 모두 제거.)
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

export default function DatalakeCardPicker({ vid, moduleFunction, company, value, onChange }) {
  const [entries, setEntries] = useState(null)   // null = 로딩
  const [err, setErr] = useState('')

  // 카드 필터 쿼리 — vid + function(모듈 고정) + company(상단 셀렉터). 4축 AND 는 서버 수행(D-166).
  useEffect(() => {
    if (!vid) return
    setEntries(null)
    dlList({ vid, function: moduleFunction || null, company: company || null })
      .then((r) => setEntries(r.entries || []))
      .catch((e) => { setErr(e.message || 'catalog 조회 실패'); setEntries([]) })
  }, [vid, moduleFunction, company])

  const cards = useMemo(() => entries || [], [entries])

  return (
    <div className="dlv2-picker" style={{ marginTop: 6 }}>
      <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>
        function={moduleFunction || '?'}(모듈 고정)
        {company ? ` · company=${company}` : ' · company=전체'} · vid={vid}
      </div>
      {err && <div className="error-text">⚠ {err}</div>}
      {entries === null ? (
        <div className="muted">catalog 로딩 중…</div>
      ) : cards.length === 0 ? (
        <div className="muted">조건에 맞는 데이터셋이 없습니다.</div>
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
