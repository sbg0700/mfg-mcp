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
