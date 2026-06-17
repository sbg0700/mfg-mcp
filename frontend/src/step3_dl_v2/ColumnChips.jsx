// DL-3b — 선택 데이터셋 실컬럼 칩 (소스 = GET /api/datalake/{id}/columns, D-90/D-161).
// __dupN = 원본 헤더명 + 중복 배지 표기 — 드롭·은닉 금지 (D-180).
// group 컬럼 = 배지 표기만 (aggregate 제약 폼은 3c 범위).
const DUP_RE = /^(.*)__dup(\d+)$/

export default function ColumnChips({ columns }) {
  if (!columns || columns.length === 0) return null
  const chip = {
    display: 'inline-block', padding: '2px 8px', margin: '2px 4px 2px 0',
    borderRadius: 10, fontSize: 11, background: '#f3f4f6', border: '1px solid #e5e7eb',
    color: '#1f2937',   // 밝은 칩 배경에 묻히지 않도록 어두운 글자 (다크 테마 대비)
  }
  const badge = {
    marginLeft: 4, padding: '0 5px', borderRadius: 8, fontSize: 10,
    background: '#fde68a', border: '1px solid #f59e0b', color: '#1f2937',
  }
  const groupBadge = { ...badge, background: '#ddd6fe', border: '1px solid #8b5cf6' }
  return (
    <div style={{ margin: '6px 0' }}>
      <span className="muted" style={{ fontSize: 11, marginRight: 6 }}>
        컬럼 {columns.length}개:
      </span>
      {columns.map((c) => {
        const m = DUP_RE.exec(c.name)
        return (
          <span key={c.name} style={chip} title={`${c.name} (${c.dtype || '?'})`}>
            {m ? m[1] : c.name}
            {m && <span style={badge}>중복{m[2]}</span>}
            {c.column_kind === 'group' && (
              <span style={groupBadge}>group:{c.group_desc?.kind || '?'}</span>
            )}
          </span>
        )
      })}
    </div>
  )
}
