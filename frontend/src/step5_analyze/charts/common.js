// STEP 3b — recharts 공통 props/유틸 (다크 톤, CSS 변수 사용).
// 색 매핑: function_axis와 헌법 토큰 일치 (--c-process/quality/maintenance/reference).

export const AXIS = { stroke: 'var(--muted)', fontSize: 12 }
export const GRID = { stroke: 'var(--border)', strokeOpacity: 0.4 }
export const TOOLTIP_STYLE = {
  background: 'var(--panel-2)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
  fontSize: 12,
}
export const TOOLTIP_LABEL_STYLE = { color: 'var(--text)' }
export const TOOLTIP_ITEM_STYLE = { color: 'var(--text)' }

// 차트 기본 색 — function_axis 의미 일치
export const COLORS = {
  process: 'var(--c-process)',         // 파랑 — 기본 (histogram, scatter)
  quality: 'var(--c-quality)',         // 초록 — class_distribution
  maintenance: 'var(--c-maintenance)', // 주황 — fft/rms (진동/에너지)
  reference: 'var(--c-reference)',     // 회색 — pareto bar
}

// 차트 카드 공통 높이
export const CHART_HEIGHT = 280
