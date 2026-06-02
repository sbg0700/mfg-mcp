import {
  ScatterChart, Scatter as RScatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { AXIS, GRID, TOOLTIP_STYLE, COLORS, CHART_HEIGHT } from './common'

// data: {x_column, y_column, x:[], y:[], n}
export default function Scatter({ data }) {
  const xs = data.x || []
  const ys = data.y || []
  const rows = xs.map((x, i) => ({ x, y: ys[i] }))
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <ScatterChart margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
        <CartesianGrid {...GRID} />
        <XAxis type="number" dataKey="x" name={data.x_column} {...AXIS} />
        <YAxis type="number" dataKey="y" name={data.y_column} {...AXIS} />
        <Tooltip wrapperStyle={TOOLTIP_STYLE} contentStyle={TOOLTIP_STYLE} cursor={{ strokeDasharray: '3 3' }} />
        <RScatter
          name={`${data.x_column} vs ${data.y_column}`}
          data={rows}
          fill={COLORS.process}
          fillOpacity={0.55}
          isAnimationActive={false}
        />
      </ScatterChart>
    </ResponsiveContainer>
  )
}
