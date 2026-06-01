import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App.jsx'
import LineSelectPage from './step1_line/LineSelectPage.jsx'
import PipelineBuildPage from './step2_user_input_pipeline/PipelineBuildPage.jsx'
import DataConstraintPage from './step3_user_input_data/DataConstraintPage.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App><LineSelectPage /></App>} />
      <Route path="/pipeline/build" element={<App><PipelineBuildPage /></App>} />
      <Route path="/pipeline/data" element={<App><DataConstraintPage /></App>} />
      {/* Page 4 placeholder — 다음 커밋(1B-3b Page 4)에서 실제 구현 */}
      <Route path="/pipeline/run" element={<App><Placeholder title="Page 4 (1B-3b 다음)" /></App>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </BrowserRouter>
)

function Placeholder({ title }) {
  return (
    <div>
      <h1>{title}</h1>
      <p className="muted">이 페이지는 다음 단계에서 구현됩니다.</p>
    </div>
  )
}
