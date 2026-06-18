import {
  ComposedChart, Bar, ErrorBar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { AXIS, GRID, TOOLTIP_STYLE, COLORS, CHART_HEIGHT } from './common'

// data: {target_column, label_column, groups:{<label>:{min,q1,median,q3,max,n}}}
// recharts에 박스플롯 내장 X — ComposedChart 구성:
//   - stacked Bar: 투명 q1 + 보이는 q3-q1 = 박스(q1~q3)
//   - ErrorBar:   수염(median±whiskerLow/High) → min~max 범위
//   - tooltip:    5수치(min/q1/median/q3/max) + n
function BoxTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  // payload[].payload는 행 dict (label/q1/boxHeight/...)
  const row = payload[0]?.payload
  if (!row) return null
  return (
    <div style={{ ...TOOLTIP_STYLE, padding: '6px 10px' }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{row.label} (n={row.n})</div>
      <div>max: {row.max.toFixed(3)}</div>
      <div>q3: {row.q3.toFixed(3)}</div>
      <div>median: {row.median.toFixed(3)}</div>
      <div>q1: {row.q1.toFixed(3)}</div>
      <div>min: {row.min.toFixed(3)}</div>
    </div>
  )
}

// Y축 눈금 = 천단위 구분 + 소수 2자리 (실데이터 이상치 큰 값이 "1000004"로 깨져 보이던 것 정상화)
const fmtTick = (v) => Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })

export default function BoxPlot({ data }) {
  const groups = data.groups || {}
  const rows = Object.entries(groups).map(([label, g]) => ({
    label,
    min: g.min, q1: g.q1, median: g.median, q3: g.q3, max: g.max, n: g.n,
    boxHeight: g.q3 - g.q1,
    // ErrorBar는 [low, high] 배열 형태(중심에서 음수·양수 오프셋)
    // 중심을 median으로 두면 수염은 [median-min, max-median]
    medianMid: g.median,
    whisker: [g.median - g.min, g.max - g.median],
  }))
  // YAxis 범위 = 모든 그룹의 min~max
  const allMin = rows.length ? Math.min(...rows.map((r) => r.min)) : 0
  const allMax = rows.length ? Math.max(...rows.map((r) => r.max)) : 1
  const pad = (allMax - allMin) * 0.05 || 1
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="label" {...AXIS} />
        <YAxis {...AXIS} domain={[allMin - pad, allMax + pad]} tickFormatter={fmtTick} />
        <Tooltip content={<BoxTooltip />} />
        {/* base = q1 (투명) */}
        <Bar dataKey="q1" stackId="box" fill="transparent" isAnimationActive={false} />
        {/* 박스 = q3-q1 (보임) */}
        <Bar
          dataKey="boxHeight"
          stackId="box"
          fill={COLORS.process}
          fillOpacity={0.6}
          stroke={COLORS.process}
          isAnimationActive={false}
        />
        {/* 수염 = ErrorBar (median 중심 [low, high]) — 별도 보조 Bar에 부착 */}
        <Bar dataKey="medianMid" fill="transparent" isAnimationActive={false}>
          <ErrorBar
            dataKey="whisker"
            width={6}
            strokeWidth={1.5}
            stroke={COLORS.maintenance}
            direction="y"
          />
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  )
}
