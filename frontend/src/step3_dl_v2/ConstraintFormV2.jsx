// DL-3c — Page 3 v2 제약 폼 (D-167/D-180/D-189/D-190/D-191).
// - column_kind 렌더 분기: scalar = range 폼(min~max+unit) / group = aggregate 폼(metric·op·value+unit)
// - prefill 재승인 게이트: merge view(source=prefill)는 "제안 박스"로만 표시(값 미주입) —
//   [승인] 클릭 시에만 세션 cmap 에 적용. 자동 적용 절대 0 (D-167).
// - 저장 분기 모달: [이번만] = 세션만(catalog 미접촉) / [메모리 업데이트] = POST 영속
//   (insert_constraint 경유, D-179). 빈칸 영속 = delete 확인 모달 → POST null (D-191).
// - __dupN = 원본 헤더명 + "중복N" 배지 (3b ColumnChips 패턴 승계, 드롭·은닉 금지).
// 구 ConstraintForm.jsx 무수정 — v2 전용 신규 파일 (D-184 additive).
import { useEffect, useState } from 'react'
import { dlConstraintPost } from '../api.js'

const DUP_RE = /^(.*)__dup(\d+)$/
const AGG_METRICS = ['rms', 'peak', 'mean', 'std']
const AGG_OPS = ['<=', '>=']
const NUMERIC_DTYPES = new Set(['integer', 'float'])
// 제약 가능 = group(aggregate) | 숫자 scalar(integer/float→range). 그 외 비숫자 scalar
// (text/datetime/boolean/unknown/빈값/null) = "범위 제약 대상 아님" (min/max 입력 없음).
const isConstrainable = (c) => c.column_kind === 'group' || NUMERIC_DTYPES.has(c.dtype)
// 관측 통계 숫자 포맷(읽기 쉽게 천단위·소수 2자리). 규격 제안 아닌 데이터 사실 표시(D-43).
const fmtNum = (x) => (x == null ? '' : Number(x).toLocaleString(undefined, { maximumFractionDigits: 2 }))

export function specSummary(spec) {
  if (!spec) return '(없음)'
  if (spec.type === 'range') {
    return `${spec.min ?? '−∞'} ~ ${spec.max ?? '+∞'}${spec.unit ? ` ${spec.unit}` : ''}`
  }
  if (spec.type === 'aggregate') {
    return `${spec.metric} ${spec.op} ${spec.value}${spec.unit ? ` ${spec.unit}` : ''}`
  }
  if (spec.type === 'single_value') {
    return `${spec.value}${spec.unit ? ` ${spec.unit}` : ''}`
  }
  return JSON.stringify(spec)
}

// draft(문자열 입력) → canonical spec | null(빈칸). 비유한 숫자는 null 취급(저장 전 검증은 백엔드).
function draftToSpec(kind, d) {
  const num = (s) => {
    const t = (s ?? '').trim()
    if (t === '') return null
    const n = Number(t)
    return Number.isFinite(n) ? n : null
  }
  const unit = (d.unit ?? '').trim() || null
  if (kind === 'group') {
    const value = num(d.value)
    if (value == null) return null                       // value 없으면 빈칸
    return { type: 'aggregate', metric: d.metric || 'rms', op: d.op || '<=', value, unit }
  }
  const min = num(d.min)
  const max = num(d.max)
  if (min == null && max == null) return null            // 둘 다 빈칸 = 제약 없음 (D-180)
  return { type: 'range', min, max, unit }
}

function specToDraft(kind, spec) {
  if (kind === 'group') {
    return spec && spec.type === 'aggregate'
      ? { metric: spec.metric, op: spec.op, value: String(spec.value ?? ''), unit: spec.unit || '' }
      : { metric: 'rms', op: '<=', value: '', unit: '' }
  }
  return spec && spec.type === 'range'
    ? { min: spec.min != null ? String(spec.min) : '', max: spec.max != null ? String(spec.max) : '', unit: spec.unit || '' }
    : { min: '', max: '', unit: '' }
}

// 폼이 직접 편집 가능한 type 인지 (그 외 — 예: prefill 승인된 single_value — 는 요약+빈칸만)
const editableType = (kind, spec) =>
  !spec || (kind === 'group' ? spec.type === 'aggregate' : spec.type === 'range')

function Modal({ title, children, actions }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div style={{ background: '#fff', borderRadius: 8, padding: 20, minWidth: 360,
                    maxWidth: 480, boxShadow: '0 8px 30px rgba(0,0,0,0.2)', color: '#1f2937' }}>
        <h3 style={{ margin: '0 0 10px', fontSize: 15 }}>{title}</h3>
        <div style={{ fontSize: 13, marginBottom: 14 }}>{children}</div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>{actions}</div>
      </div>
    </div>
  )
}

function ColumnName({ name, kind, groupDesc }) {
  const m = DUP_RE.exec(name)
  const badge = { marginLeft: 4, padding: '0 5px', borderRadius: 8, fontSize: 10,
                  background: '#fde68a', border: '1px solid #f59e0b', color: '#1f2937' }
  const groupBadge = { ...badge, background: '#ddd6fe', border: '1px solid #8b5cf6' }
  return (
    <span style={{ fontWeight: 600, fontSize: 12 }} title={name}>
      {m ? m[1] : name}
      {m && <span style={badge}>중복{m[2]}</span>}
      {kind === 'group' && <span style={groupBadge}>group:{groupDesc?.kind || '?'}</span>}
    </span>
  )
}

/**
 * props:
 *  - datalakeId: 선택된 데이터셋 (없으면 안내만)
 *  - columns: GET /api/datalake/{id}/columns 결과 (catalog 권위)
 *  - merged: GET constraint_merge 결과 rows (prefill 제안 소스 — 값 미주입)
 *  - cmap: {column_name: canonical_spec} — 세션 적용분 (페이지 상태)
 *  - onChange(nextCmap): 세션 적용분 변경 (이번만/승인/빈칸 이번만)
 *  - onToast(msg)
 *  - onPersisted(): 영속 저장/삭제(catalog 쓰기) 성공 후 호출 — 부모가 constraint_merge
 *    재조회로 prefill 제안을 서버 SSOT 와 재동기(stale 제안 잔존 차단, DL-3c fix).
 */
export default function ConstraintFormV2({ datalakeId, columns, merged, cmap,
                                           onChange, onToast, onPersisted }) {
  const [drafts, setDrafts] = useState({})
  const [modal, setModal] = useState(null)   // {col, spec, step: 'branch'|'confirm-delete'}
  const [busy, setBusy] = useState(false)

  // 초기 draft = 세션 적용분(cmap) — dataset 또는 컬럼 '집합' 변경 시에만 전체 재초기화.
  // colsKey(컬럼명 join)로 의존 → 핵심/전체 토글로 집합이 바뀔 때만 재초기화,
  // 부모 리렌더로 columns 배열 참조만 바뀌는 경우(Apply 등)엔 타이핑 보존.
  const colsKey = (columns || []).map((c) => c.name).join('')
  useEffect(() => {
    const next = {}
    for (const c of columns || []) {
      next[c.name] = specToDraft(c.column_kind, cmap?.[c.name])
    }
    setDrafts(next)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datalakeId, colsKey])

  if (!datalakeId) {
    return <p className="muted" style={{ fontSize: 12 }}>데이터셋을 선택하면 제약 폼이 표시됩니다.</p>
  }

  const mergedByCol = {}
  for (const v of merged || []) mergedByCol[v.column_name] = v

  function setDraft(col, patch) {
    setDrafts((prev) => ({ ...prev, [col]: { ...(prev[col] || {}), ...patch } }))
  }

  function applySession(col, spec) {
    const next = { ...(cmap || {}) }
    if (spec == null) delete next[col]
    else next[col] = spec
    onChange(next)
    const kind = (columns || []).find((c) => c.name === col)?.column_kind
    if (editableType(kind, spec)) setDraft(col, specToDraft(kind, spec))
  }

  // [저장] → 분기 모달. 빈칸 + 영속 선택 시 delete 확인 단계로.
  function onSaveClick(col, kind) {
    const c = (columns || []).find((x) => x.name === col)
    if (c && !isConstrainable(c)) return   // 비숫자 scalar = 제약 spec 생성 스킵(draftToSpec 미호출)
    const spec = draftToSpec(kind, drafts[col] || {})
    setModal({ col, spec, step: 'branch' })
  }

  async function persist(col, spec) {
    setBusy(true)
    try {
      await dlConstraintPost(datalakeId, {
        column_name: col, constraint_spec: spec, approved_by: 'user',
      })
      applySession(col, spec)                            // 영속 후 세션도 동일 값 사용
      // catalog 변경 → prefill 제안을 서버 SSOT 와 재동기(삭제값 제안 잔존 차단, DL-3c fix).
      // 부모 fetchMerge 는 내부 catch — 실패해도 영속 성공을 되돌리지 않음.
      await onPersisted?.()
      onToast(spec ? `저장됨: ${col} — ${specSummary(spec)}` : `삭제됨: ${col}`)
    } catch (e) {
      onToast(`${spec ? '저장' : '삭제'} 실패 (${col}): ${e.message}`)
    } finally {
      setBusy(false)
      setModal(null)
    }
  }

  return (
    <div style={{ marginTop: 8 }}>
      <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>
        측정값의 허용 범위를 입력하세요. '이번만'은 이번 분석에만, '저장'하면 다음에도 같은 값이 제안됩니다.
      </div>
      {(columns || []).map((c) => {
        const col = c.name
        const kind = c.column_kind
        const d = drafts[col] || specToDraft(kind, null)
        const applied = cmap?.[col]
        const mv = mergedByCol[col]
        const constrainable = isConstrainable(c)
        // 재승인 게이트 — 세션 미적용 + prefill 존재 시에만 제안 박스 (값 미주입). 비숫자는 제안도 미표시.
        const suggestion = constrainable && !applied && mv?.source === 'prefill' ? mv.prefill : null
        const opaque = !editableType(kind, applied)
        const inp = { width: 80, fontSize: 12, padding: '2px 4px' }
        return (
          <div key={col} style={{ borderTop: '1px solid #f3f4f6', padding: '6px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <ColumnName name={col} kind={kind} groupDesc={c.group_desc} />
              {!constrainable ? (
                <span className="muted" style={{ fontSize: 12 }}>
                  <span className="ins-badge" style={{ marginRight: 6 }}>{c.dtype || 'null'}</span>
                  범위 제약 대상 아님
                </span>
              ) : opaque ? (
                <span style={{ fontSize: 12 }}>
                  현재 값: <code>{specSummary(applied)}</code>
                  <span className="muted" style={{ fontSize: 11 }}> (여기서는 수정할 수 없습니다)</span>
                </span>
              ) : kind === 'group' ? (
                <>
                  <select value={d.metric} onChange={(e) => setDraft(col, { metric: e.target.value })} style={inp}>
                    {AGG_METRICS.map((x) => <option key={x} value={x}>{x}</option>)}
                  </select>
                  <select value={d.op} onChange={(e) => setDraft(col, { op: e.target.value })} style={{ ...inp, width: 56 }}>
                    {AGG_OPS.map((x) => <option key={x} value={x}>{x}</option>)}
                  </select>
                  <input placeholder="value" value={d.value} style={inp}
                         onChange={(e) => setDraft(col, { value: e.target.value })} />
                  <input placeholder="unit(옵션)" value={d.unit} style={inp}
                         onChange={(e) => setDraft(col, { unit: e.target.value })} />
                </>
              ) : (
                <>
                  <input placeholder="min" value={d.min} style={inp}
                         onChange={(e) => setDraft(col, { min: e.target.value })} />
                  <span className="muted">~</span>
                  <input placeholder="max" value={d.max} style={inp}
                         onChange={(e) => setDraft(col, { max: e.target.value })} />
                  <input placeholder="unit(옵션)" value={d.unit} style={inp}
                         onChange={(e) => setDraft(col, { unit: e.target.value })} />
                  {c.stat_min != null && c.stat_max != null && (
                    <span className="muted" style={{ fontSize: 11 }}>
                      관측 범위 {fmtNum(c.stat_min)} ~ {fmtNum(c.stat_max)}
                    </span>
                  )}
                </>
              )}
              {constrainable && (
                <button className="btn" style={{ fontSize: 11, padding: '2px 10px' }}
                        disabled={busy} onClick={() => onSaveClick(col, kind)}>
                  적용
                </button>
              )}
              {applied && (
                <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 8,
                               background: '#dcfce7', border: '1px solid #22c55e', color: '#166534' }}>
                  적용됨: {specSummary(applied)}
                </span>
              )}
            </div>
            {suggestion && (
              <div style={{ marginTop: 4, padding: '6px 8px', borderRadius: 6, fontSize: 12,
                            background: '#eff6ff', border: '1px dashed #3b82f6', color: '#1e3a8a' }}>
                추천 값: <strong>{specSummary(suggestion.constraint_spec)}</strong>
                <button className="btn" style={{ fontSize: 11, padding: '1px 8px', marginLeft: 8 }}
                        onClick={() => applySession(col, suggestion.constraint_spec)}>
                  적용
                </button>
              </div>
            )}
          </div>
        )
      })}

      {modal && modal.step === 'branch' && (
        <Modal
          title={`허용 범위 적용 — ${modal.col}`}
          actions={
            <>
              <button className="btn" disabled={busy} onClick={() => setModal(null)}>취소</button>
              <button className="btn" disabled={busy} onClick={() => {
                applySession(modal.col, modal.spec)
                onToast(modal.spec
                  ? `이번만 적용: ${modal.col} — ${specSummary(modal.spec)}`
                  : `제거됨: ${modal.col}`)
                setModal(null)
              }}>
                이번만
              </button>
              <button className="btn btn-primary" disabled={busy} onClick={() => {
                if (modal.spec == null) setModal({ ...modal, step: 'confirm-delete' })
                else persist(modal.col, modal.spec)
              }}>
                저장
              </button>
            </>
          }
        >
          <div>값: <code>{specSummary(modal.spec)}</code></div>
          <div className="muted" style={{ marginTop: 6 }}>
            '이번만'은 이번 분석에만 적용됩니다. '저장'하면 다음에도 같은 값이 제안됩니다.
          </div>
        </Modal>
      )}
      {modal && modal.step === 'confirm-delete' && (
        <Modal
          title={`저장된 값 삭제 — ${modal.col}`}
          actions={
            <>
              <button className="btn" disabled={busy} onClick={() => setModal(null)}>취소</button>
              <button className="btn btn-primary" disabled={busy}
                      onClick={() => persist(modal.col, null)}>
                삭제
              </button>
            </>
          }
        >
          이 항목에 저장된 허용 범위를 <strong>삭제</strong>합니다. 계속할까요?
        </Modal>
      )}
    </div>
  )
}
