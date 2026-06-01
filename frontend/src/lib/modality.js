// 모듈/노드 → modality 결정.
// 백엔드 _resolve_modality(backend/main.py, D-54) 와 동일한 규칙을 클라이언트에서도 적용.
// 우선순위: module.modality > node_id 매핑 > "timeseries" 폴백.
const NODE_MODALITY = {
  semiconductor_inspect: 'inspection-image',
  surface_inspect: 'inspection-image',
  welding_inspect: 'inspection-image',
  order_planning: 'order',
}

export function resolveModality(module, nodeId) {
  if (module && module.modality) return module.modality
  if (nodeId && NODE_MODALITY[nodeId]) return NODE_MODALITY[nodeId]
  return 'timeseries'
}
