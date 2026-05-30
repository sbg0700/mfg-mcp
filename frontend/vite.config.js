import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// dev: Vite serves UI on 5173, proxies /api to backend.
// target은 환경변수(VITE_API_TARGET)로 변경 가능:
//   - 호스트에서 직접 npm run dev    → 'http://localhost:8000'
//   - docker compose/network 안에서  → 'http://mfg-backend:8000'
// 기본값은 도커 동일 네트워크 시나리오. 호스트 직접 실행 시 VITE_API_TARGET 지정.
// build: outputs to frontend/dist (FastAPI StaticFiles in a later step).
const API_TARGET = process.env.VITE_API_TARGET || 'http://mfg-backend:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
})
