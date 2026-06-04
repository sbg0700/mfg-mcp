import { Fragment } from 'react'

// STEP 3d ConfusionTable — recharts heatmap 부재 대응 자체 CSS 그리드.
// 대각선(정답)=초록(--c-quality) 농도, 오답=주황(--c-maintenance) 농도.
// 값 클수록 진하게. 의존성 0.
//
// props:
//   labels: ["FAIL", "PASS"]
//   matrix: [[0,17],[0,583]]   (행=실제, 열=예측)
export default function ConfusionTable({ labels, matrix }) {
  if (!labels?.length || !matrix?.length) return null
  const n = labels.length
  const max = Math.max(1, ...matrix.flat())

  return (
    <div className="confusion-wrap">
      <div className="muted confusion-title">Confusion Matrix · 행=실제, 열=예측</div>
      <div
        className="confusion-grid"
        style={{ gridTemplateColumns: `auto repeat(${n}, minmax(56px, 1fr))` }}
      >
        <div className="cm-corner" />
        {labels.map((l) => (
          <div key={`h-${l}`} className="cm-head" title={`예측: ${l}`}>{l}</div>
        ))}
        {matrix.map((row, i) => (
          <Fragment key={`r-${i}`}>
            <div className="cm-rowhead" title={`실제: ${labels[i]}`}>{labels[i]}</div>
            {row.map((v, j) => {
              const ratio = v / max
              const isDiag = i === j
              const bg = v
                ? isDiag
                  ? `rgba(22, 163, 74, ${0.15 + ratio * 0.55})`   // quality 초록
                  : `rgba(234, 88, 12, ${0.10 + ratio * 0.45})`   // maintenance 주황
                : 'transparent'
              return (
                <div
                  key={`c-${i}-${j}`}
                  className={`cm-cell ${isDiag ? 'cm-diag' : 'cm-off'}`}
                  style={{ background: bg }}
                  title={`실제 ${labels[i]} → 예측 ${labels[j]}: ${v}`}
                >
                  {v}
                </div>
              )
            })}
          </Fragment>
        ))}
      </div>
    </div>
  )
}
