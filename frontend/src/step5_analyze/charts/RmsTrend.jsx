import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { AXIS, GRID, TOOLTIP_STYLE, COLORS, CHART_HEIGHT, fmtAxis } from './common'

// data: {column, window_size, rms:[], indices:[]}
export default function RmsTrend({ data }) {
  const rows = (data.indices || []).map((idx, i) => ({ idx, rms: data.rms?.[i] ?? 0 }))
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="idx" {...AXIS} />
        <YAxis {...AXIS} tickFormatter={fmtAxis} />
        <Tooltip wrapperStyle={TOOLTIP_STYLE} contentStyle={TOOLTIP_STYLE} />
        <Line type="monotone" dataKey="rms" stroke={COLORS.maintenance} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
