import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App.jsx'
import LineSelectPage from './step1_line/LineSelectPage.jsx'
import PipelineBuildPage from './step2_user_input_pipeline/PipelineBuildPage.jsx'
import DataConstraintPage from './step3_user_input_data/DataConstraintPage.jsx'
import StandardizePage from './step4_standardize/StandardizePage.jsx'
import AnalyzePage from './step5_analyze/AnalyzePage.jsx'
import ModelingPage from './step6_modeling/ModelingPage.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App><LineSelectPage /></App>} />
      <Route path="/pipeline/build" element={<App><PipelineBuildPage /></App>} />
      <Route path="/pipeline/data" element={<App><DataConstraintPage /></App>} />
      <Route path="/pipeline/run" element={<App><StandardizePage /></App>} />
      <Route path="/pipeline/analyze" element={<App><AnalyzePage /></App>} />
      <Route path="/pipeline/model" element={<App><ModelingPage /></App>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </BrowserRouter>
)
