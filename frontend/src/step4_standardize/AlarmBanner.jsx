// 미업로드 모듈 알람 배너 — llm_judge_data_necessity 결과(1B-2a, D-55).
// LLM은 문구만 만들고, 결정은 사용자. "무시" 또는 "Page 3에서 추가".
import { Link, useSearchParams } from 'react-router-dom'

export default function AlarmBanner({ alarms, onDismiss }) {
  const [params] = useSearchParams()
  const sid = params.get('session') || ''
  if (!alarms || alarms.length === 0) return null
  return (
    <div className="alarm-banner">
      {alarms.map((a, i) => (
        <div key={i} className="alarm-row">
          <span>⚠</span>
          <div style={{ flex: 1 }}>
            <strong>단계 {(a.stage_order ?? 0) + 1}{a.node_id ? ` (${a.node_id})` : ''}</strong>
            <span className="muted"> · {(a.alarm?.missing || []).join(', ')} 미업로드</span>
            <div className="alarm-text">{a.alarm?.alarm_ko}</div>
            <div className="muted" style={{ fontSize: 12 }}>
              LLM 판단(참고): likely_essential = {String(a.alarm?.likely_essential)}
              · 흐름 결정은 사용자
            </div>
          </div>
          <div className="alarm-actions">
            <Link to={`/pipeline/${import.meta.env.VITE_DL_UI_V2 ? 'data-v2' : 'data'}?session=${sid}`} className="btn">Page 3 으로 돌아가기</Link>
            {onDismiss && (
              <button className="btn" onClick={() => onDismiss(i)}>무시</button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
