import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App.jsx'
import LineSelectPage from './step1_line/LineSelectPage.jsx'
import PipelineBuildPage from './step2_user_input_pipeline/PipelineBuildPage.jsx'
import DataConstraintPage from './step3_user_input_data/DataConstraintPage.jsx'
import StandardizePage from './step4_standardize/StandardizePage.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App><LineSelectPage /></App>} />
      <Route path="/pipeline/build" element={<App><PipelineBuildPage /></App>} />
      <Route path="/pipeline/data" element={<App><DataConstraintPage /></App>} />
      <Route path="/pipeline/run" element={<App><StandardizePage /></App>} />
      {/* Page 5·6 placeholders — 1B-3c에서 구현 */}
      <Route path="/pipeline/analyze" element={<App><Placeholder title="Page 5 (1B-3c)" /></App>} />
      <Route path="/pipeline/model" element={<App><Placeholder title="Page 6 (1B-3c)" /></App>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </BrowserRouter>
)

function Placeholder({ title }) {
  return (
    <div>
      <h1>{title}</h1>
      <p className="muted">이 페이지는 다음 단계(STEP 1B-3c)에서 구현됩니다.</p>
    </div>
  )
}
