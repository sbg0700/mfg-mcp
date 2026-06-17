import { useSearchParams, Link, useLocation } from 'react-router-dom'

export default function Breadcrumb() {
  const [params] = useSearchParams()
  const sid = params.get('session')
  const loc = useLocation()
  const onHome = loc.pathname === '/'
  return (
    <div className="breadcrumb">
      <div className="breadcrumb-row1">
        <span className="brand">GYEOL</span>
        <span className="breadcrumb-sub">| 제조 데이터 파이프라인</span>
      </div>
      {(!onHome || sid) && (
        <div className="breadcrumb-row2">
          {!onHome && <Link to="/" className="muted">← Page 1</Link>}
          {sid && <span className="muted">· 세션 <code>{sid.slice(0, 8)}</code></span>}
        </div>
      )}
    </div>
  )
}
