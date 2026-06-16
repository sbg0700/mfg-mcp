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

// ── DL-3c — 제약 폼 (additive, D-167/D-189/D-190/D-191) ──
// POST = "메모리 업데이트(영속)" 전용 — insert_constraint 경유(D-179). 빈 spec(null) = delete(D-191).
export const dlConstraintPost = (id, body) =>
  post(`/datalake/${encodeURIComponent(id)}/constraints`, body)
// merge view = 머지 3케이스(세션>prefill>빈칸) — prefill 은 제안만(재승인 게이트, D-167)
export const dlConstraintMerge = (sid, moduleKey, datalakeId) =>
  get(`/datalake/sessions/${encodeURIComponent(sid)}/constraint_merge` +
      `?module_key=${encodeURIComponent(moduleKey)}&datalake_id=${encodeURIComponent(datalakeId)}`)
// v2 PUT full — constraints_v2(canonical) 동반, 백엔드가 엔진용 구 shape 로 다운컨버트(D-189)
export const dlSessionPutFull = (sid, pipelineFull) =>
  put(`/datalake/sessions/${encodeURIComponent(sid)}/full`, { pipeline_full: pipelineFull })
