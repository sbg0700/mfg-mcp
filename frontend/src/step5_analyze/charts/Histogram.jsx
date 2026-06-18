import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { AXIS, GRID, TOOLTIP_STYLE, COLORS, CHART_HEIGHT, fmtAxis } from './common'

// data: {column, bins:[N+1], counts:[N], stats:{mean,std,min,max,n}}
// bins 중점을 x 라벨로, counts를 y로. (BarChart 한 개 막대 시리즈)
export default function Histogram({ data }) {
  const rows = (data.counts || []).map((c, i) => {
    const lo = data.bins[i]
    const hi = data.bins[i + 1]
    const mid = (lo + hi) / 2
    return { x: mid.toFixed(2), count: c }
  })
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="x" {...AXIS} />
        <YAxis {...AXIS} tickFormatter={fmtAxis} />
        <Tooltip wrapperStyle={TOOLTIP_STYLE} contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="count" name={data.column || '빈도'} fill={COLORS.process} />
      </BarChart>
    </ResponsiveContainer>
  )
}
