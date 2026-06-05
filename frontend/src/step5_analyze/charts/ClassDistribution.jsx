import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { AXIS, GRID, TOOLTIP_STYLE, COLORS, CHART_HEIGHT } from './common'

// data: {column, labels:[], counts:[], others_count?}
export default function ClassDistribution({ data }) {
  const rows = (data.labels || []).map((l, i) => ({ label: l, count: data.counts?.[i] ?? 0 }))
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="label" {...AXIS} />
        <YAxis {...AXIS} />
        <Tooltip wrapperStyle={TOOLTIP_STYLE} contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="count" name={data.column || '카운트'} fill={COLORS.quality} />
      </BarChart>
    </ResponsiveContainer>
  )
}
