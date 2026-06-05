import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { AXIS, GRID, TOOLTIP_STYLE, COLORS, CHART_HEIGHT } from './common'

// data: {column, labels:[], counts:[], cumulative_pct:[], others_count?}
// ComposedChart: Bar = counts (좌측 Y), Line = cumulative_pct (우측 Y)
export default function Pareto({ data }) {
  const rows = (data.labels || []).map((l, i) => ({
    label: l,
    count: data.counts?.[i] ?? 0,
    cum: Number((data.cumulative_pct?.[i] ?? 0).toFixed(1)),
  }))
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="label" {...AXIS} />
        <YAxis yAxisId="left" {...AXIS} />
        <YAxis yAxisId="right" orientation="right" domain={[0, 100]} unit="%" {...AXIS} />
        <Tooltip wrapperStyle={TOOLTIP_STYLE} contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 11, color: 'var(--muted)' }} />
        <Bar yAxisId="left" dataKey="count" name={data.column || '빈도'} fill={COLORS.reference} />
        <Line yAxisId="right" type="monotone" dataKey="cum" name="누적 %" stroke={COLORS.maintenance} dot={false} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
