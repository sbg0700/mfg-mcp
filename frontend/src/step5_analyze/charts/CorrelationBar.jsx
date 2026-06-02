import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { AXIS, GRID, TOOLTIP_STYLE, COLORS, CHART_HEIGHT } from './common'

// data: {target_column, columns:[], values:[]}  — horizontal bar (변수=Y, |corr|=X)
export default function CorrelationBar({ data }) {
  const rows = (data.columns || []).map((c, i) => ({ col: c, val: data.values?.[i] ?? 0 }))
  // 가로 막대 = layout="vertical" (recharts 명칭: X=값, Y=카테고리)
  // 항목 많을 때 카드 안에서 스크롤 없이 보이도록 동적 높이
  const h = Math.max(CHART_HEIGHT, rows.length * 22 + 40)
  return (
    <ResponsiveContainer width="100%" height={h}>
      <BarChart layout="vertical" data={rows} margin={{ top: 4, right: 16, bottom: 4, left: 12 }}>
        <CartesianGrid {...GRID} />
        <XAxis type="number" {...AXIS} domain={[0, 'dataMax']} />
        <YAxis type="category" dataKey="col" width={120} {...AXIS} />
        <Tooltip wrapperStyle={TOOLTIP_STYLE} contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="val" name={`|corr| vs ${data.target_column}`} fill={COLORS.process} />
      </BarChart>
    </ResponsiveContainer>
  )
}
