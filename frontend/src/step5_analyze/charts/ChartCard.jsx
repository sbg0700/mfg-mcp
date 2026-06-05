import { useState } from 'react'
import { post } from '../../api.js'
import Histogram from './Histogram.jsx'
import BoxPlot from './BoxPlot.jsx'
import FftSpectrum from './FftSpectrum.jsx'
import RmsTrend from './RmsTrend.jsx'
import ClassDistribution from './ClassDistribution.jsx'
import CorrelationBar from './CorrelationBar.jsx'
import Pareto from './Pareto.jsx'
import Scatter from './Scatter.jsx'

// 디스패치 테이블 — 8 chart_type → 컴포넌트
const CHART_COMPONENTS = {
  histogram: Histogram,
  boxplot_by_label: BoxPlot,
  fft_spectrum: FftSpectrum,
  rms_trend: RmsTrend,
  class_distribution: ClassDistribution,
  correlation_bar: CorrelationBar,
  pareto: Pareto,
  scatter: Scatter,
}

function ChartError({ label, message }) {
  return (
    <div className="chart-card">
      <div className="chart-card-head">
        <strong>{label || '차트'}</strong>
      </div>
      <div className="chart-error">⚠ {message}</div>
    </div>
  )
}

// 차트 부속 정보: others_count / peak_freq / mean·std
function ChartFooter({ data }) {
  if (!data) return null
  const parts = []
  if (data.others_count) parts.push(`+기타 ${data.others_count}개`)
  if (data.stats?.peak_freq != null)
    parts.push(`peak ≈ ${Number(data.stats.peak_freq).toFixed(4)}`)
  if (data.stats?.mean != null && data.stats?.std != null)
    parts.push(`mean ${data.stats.mean.toFixed(2)} / std ${data.stats.std.toFixed(2)}`)
  if (data.stats?.n != null) parts.push(`n=${data.stats.n}`)
  if (data.n != null && data.stats?.n == null) parts.push(`n=${data.n}`)
  if (!parts.length) return null
  return <div className="chart-footer muted">{parts.join(' · ')}</div>
}

export default function ChartCard({ chart, sessionId }) {
  const [summary, setSummary] = useState(null)
  const [keyPoints, setKeyPoints] = useState([])
  const [summaryBusy, setSummaryBusy] = useState(false)
  const [summaryErr, setSummaryErr] = useState(null)

  // 1) 항목 자체 에러 (modality 미스매치 / 허용 외 chart_type 등) — 백엔드가 data 없이 error 필드
  if (chart.error) return <ChartError label={chart.label} message={chart.error} />
  const data = chart.data || {}
  // 2) compute 시 발생한 데이터 에러 (no numeric column 등)
  if (data.error) return <ChartError label={chart.label} message={data.error} />

  const Comp = CHART_COMPONENTS[chart.chart_type]
  if (!Comp) return <ChartError label={chart.label} message={`미지원 차트: ${chart.chart_type}`} />

  async function onSummary() {
    setSummaryBusy(true); setSummaryErr(null)
    try {
      // /eda/summary는 chart_type + stats (data 전체로 충분 — 백엔드는 dict 임의 수용)
      const r = await post(`/analyze/${sessionId}/eda/summary`, {
        chart_type: chart.chart_type,
        stats: data,
        findings: [],
      })
      if (r.llm_status === 'failed') {
        setSummaryErr(`LLM 실패: ${r.llm_error || '알 수 없음'}`)
        setSummary(null); setKeyPoints([])
      } else {
        setSummary(r.summary || '')
        setKeyPoints(r.key_points || [])
      }
    } catch (e) {
      setSummaryErr(e.message || '요약 호출 실패')
    } finally {
      setSummaryBusy(false)
    }
  }

  return (
    <div className="chart-card">
      <div className="chart-card-head">
        <strong>{chart.label || chart.chart_type}</strong>
        <button className="btn-sm" onClick={onSummary} disabled={summaryBusy} title="LLM이 차트 stats를 한국어로 요약">
          {summaryBusy ? 'AI 요약 중…' : 'AI 요약'}
        </button>
      </div>
      <Comp data={data} />
      <ChartFooter data={data} />
      {(summary || summaryErr) && (
        <div className="chart-summary">
          {summaryErr ? (
            <div className="chart-error">⚠ {summaryErr}</div>
          ) : (
            <>
              <div>{summary}</div>
              {keyPoints.length > 0 && (
                <ul className="chart-keypoints">
                  {keyPoints.map((p, i) => <li key={i}>{p}</li>)}
                </ul>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
