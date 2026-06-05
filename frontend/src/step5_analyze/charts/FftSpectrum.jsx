import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { AXIS, GRID, TOOLTIP_STYLE, COLORS, CHART_HEIGHT } from './common'

// data: {column, freqs:[], magnitude:[], stats:{window_len, peak_freq}}
export default function FftSpectrum({ data }) {
  const rows = (data.freqs || []).map((f, i) => ({
    freq: typeof f === 'number' ? Number(f.toFixed(4)) : f,
    mag: data.magnitude?.[i] ?? 0,
  }))
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="freq" {...AXIS} />
        <YAxis {...AXIS} />
        <Tooltip wrapperStyle={TOOLTIP_STYLE} contentStyle={TOOLTIP_STYLE} />
        <Line type="monotone" dataKey="mag" stroke={COLORS.maintenance} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
