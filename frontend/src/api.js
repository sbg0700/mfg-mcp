// frontend/src/api.js — 최소 fetch 래퍼.
// Vite dev proxy가 /api 를 backend(8000)로 보냄 (vite.config.js).

const BASE = '/api'

export async function api(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const e = new Error(err.detail || err.message || `HTTP ${res.status}`)
    e.status = res.status
    throw e
  }
  return res.json()
}

export const get = (path) => api(path)
export const post = (path, body) =>
  api(path, { method: 'POST', body: JSON.stringify(body ?? {}) })
export const put = (path, body) =>
  api(path, { method: 'PUT', body: JSON.stringify(body ?? {}) })

// ── DL-3b — /api/datalake/* 클라이언트 (additive — 위 기존부 무수정, D-181/D-184) ──
// vid×function×site 3축 AND 필터는 백엔드 list_entries가 수행 (D-166).
export const dlList = (filters = {}) => {
  const q = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v != null && v !== ''),
  ).toString()
  return get(`/datalake/list${q ? `?${q}` : ''}`)
}
export const dlColumns = (id) => get(`/datalake/${encodeURIComponent(id)}/columns`)
