# STEP 2b 구현 명세서 — 프론트 옵션 카드 UI (ApprovalCard 확장)

> **이 문서는 Claude Code(리눅스 본진 작업)를 위한 구현 인계서다.**
> 설계는 claude.ai 세션에서 확정. STEP 2a(백엔드 옵션·미리보기) 완료·push 직후.
> **작성**: 2026-06-02. STEP 2의 두 번째(마지막) 단계.
> **브랜치**: `feature/step2-option-cards` (이 브랜치에서만 작업).

---

## 0. ★작업 시작 전 (필독)★

### 브랜치 확인 (가장 먼저)
```bash
git branch     # * feature/step2-option-cards 여야 함
```
커밋·push 모두 이 브랜치로. main 직접 push 금지. git checkout 되돌리기·reset 금지.

### 컨텍스트 로딩
1. `CLAUDE.md` — 설계 헌법.
2. `docs/specs/STEP_2a_option_cards_backend.md` — 백엔드 옵션·미리보기 (이번의 입력).
3. STEP 2b 진단 보고 (아래 1장 요약).
4. 1B-3b 산출물 (ApprovalCard, StandardizePage — 확장 대상).

### 절대 원칙
- 백엔드(STEP 2a)는 **그대로.** 프론트만 확장. 백엔드 변경 금지.
- 옵션 없는 step(다른 L2)은 **기존 yes/no 그대로** (회귀 0).
- **기능 위주 + 기존 톤 유지.** 화려한 애니메이션·전면 리디자인 금지 (UI 폴리싱은 별도 단계). 
- 외부 의존성 추가 금지(Tailwind 등). CSS는 styles.css에 기존 톤으로.

---

## 1. 배경 — STEP 2b 진단 결과 요약 (근거)

진단으로 확인된 현재 상태:

| 영역 | 현재 | STEP 2b 확장 |
|---|---|---|
| `ApprovalCard.jsx` | step_key/operation/target/rationale만 렌더. yes/no 승인 버튼 | `available_options`·`preview` 있으면 옵션 카드 + 미리보기 렌더 |
| `onApprove` 시그니처 | `(step_key, stage_order, module_index)` 3-arg | `selected_option` 4번째 인자 추가 |
| `StandardizePage.jsx` | approve POST body = `{step_key, stage_order, module_index}` | `selected_option` 동봉 + selectedOptions 로컬 state |
| `api.js` | `post(path, body)` 범용 | **손 안 댐** (body에 키 추가만) |
| 백엔드 도달 | `pending_steps[i]`에 available_options(4)/preview **이미 도달** (curl 확인) | 프론트가 읽기만 하면 됨 |

**확정 설계 (claude.ai):**
- **UX = 카드형(B)**: 각 옵션을 카드로. label + 설명 + 미리보기 숫자(행수 변화/가중치) + 주의사항.
- **선택 정책 = 강제 선택(가) + 권장 배지**: 옵션 있는 step은 **선택해야 승인 가능**. class_weight에 "권장" 배지.
- **전체 승인**: 옵션 미선택 step 있으면 비활성화.
- **회귀**: available_options 비었으면 기존 yes/no 그대로.

---

## 2. 데이터 구조 (백엔드가 주는 것 — 읽기만)

`pending.pending_steps[i]` 각 항목 (STEP 2a 검증으로 도달 확인):
```js
{
  step_key: "balance_classes:PASS_YN",
  operation: "balance_classes",
  target_column: "PASS_YN",
  permission_level: "L2",
  rationale: "...",
  semantic_group: null,
  available_options: [        // ← 옵션 있는 step만 채워짐 (4종)
    {id:"class_weight", label:"클래스 가중치 (class_weight)", description:"...", effect:"rows_unchanged", weight:"light", caution:"..."},
    {id:"smote",        label:"SMOTE 오버샘플링", ..., effect:"minority_up", weight:"heavy", caution:"..."},
    {id:"random_under", label:"랜덤 언더샘플링", ..., effect:"majority_down", weight:"heavy", caution:"..."},
    {id:"skip",         label:"보정 안 함 (skip)", ..., effect:"none", weight:"none", caution:"..."},
  ],
  preview: {                  // ← 옵션 있는 step만
    applicable: true,
    current: {counts:{PASS:2915, FAIL:85}, total:3000, majority:2915, minority:85, minority_ratio:0.0283},
    previews: {
      class_weight: {rows_after:3000, rows_delta:0, weights:{PASS:0.5146, FAIL:17.6471}, detail:"..."},
      smote:        {rows_after:5830, rows_delta:2830, detail:"..."},
      random_under: {rows_after:170,  rows_delta:-2830, detail:"..."},
      skip:         {rows_after:3000, rows_delta:0, detail:"..."},
    }
  }
}
```
> 옵션 없는 step은 `available_options: []`, `preview: {}` (또는 부재). 그 경우 기존 yes/no 렌더.

---

## 3. ApprovalCard.jsx 확장

### 3-1. props 확장
```jsx
export default function ApprovalCard({
  pending, approvedKeys, busy,
  selectedOptions,        // ← 신규: {step_key: option_id} (StandardizePage state)
  onSelectOption,         // ← 신규: (step_key, option_id) => void
  onApprove, onApproveAll, onResume,
}) {
```

### 3-2. step 렌더 분기 — 옵션 있으면 카드형
```jsx
{steps.map((s) => {
  const isApproved = approved.has(s.step_key)
  const hasOptions = Array.isArray(s.available_options) && s.available_options.length > 0
  const selected = selectedOptions?.[s.step_key] || null

  return (
    <li key={s.step_key} className={`approval-step ${isApproved ? 'approved' : ''}`}>
      {/* 헤더 라인 — 기존 유지 */}
      <div className="approval-step-line">
        <span className="perm-badge" style={{...}}>{s.permission_level}</span>
        <strong>{s.operation}</strong>
        {s.target_column && <span className="muted"> · {s.target_column}</span>}
        <span style={{flex:1}} />
        {isApproved ? (
          <span className="approval-mark">✓ 승인됨</span>
        ) : !hasOptions ? (
          /* 옵션 없는 step — 기존 yes/no 그대로 (회귀 0) */
          <button className="btn" disabled={busy}
                  onClick={() => onApprove(s.step_key, pending.stage_order, pending.module_index, null)}>
            승인
          </button>
        ) : null /* 옵션 있는 step은 아래 카드 영역에 승인 버튼 */}
      </div>

      {s.rationale && <div className="approval-rationale muted">{s.rationale}</div>}

      {/* 옵션 카드 영역 — available_options 있고 미승인일 때만 */}
      {hasOptions && !isApproved && (
        <OptionCardGroup
          step={s}
          selected={selected}
          busy={busy}
          onSelect={(optId) => onSelectOption(s.step_key, optId)}
          onApprove={() => onApprove(s.step_key, pending.stage_order, pending.module_index, selected)}
        />
      )}
    </li>
  )
})}
```

### 3-3. OptionCardGroup 컴포넌트 (신규, 같은 파일 또는 분리)
```jsx
const RECOMMENDED = "class_weight"   // 권장 옵션 (가장 안전)

function OptionCardGroup({ step, selected, busy, onSelect, onApprove }) {
  const preview = step.preview || {}
  const cur = preview.current
  const previews = preview.previews || {}

  if (preview.applicable === false) {
    return <div className="opt-warn muted">{preview.reason || "옵션 적용 불가"}</div>
  }

  return (
    <div className="opt-group">
      {/* 현재 분포 요약 */}
      {cur && (
        <div className="opt-current muted">
          현재: {Object.entries(cur.counts).map(([k,v]) => `${k} ${v}`).join(' / ')}
          {' '}(소수 클래스 {(cur.minority_ratio*100).toFixed(2)}%)
        </div>
      )}

      {/* 옵션 카드 그리드 */}
      <div className="opt-cards">
        {step.available_options.map((opt) => {
          const pv = previews[opt.id] || {}
          const isSel = selected === opt.id
          return (
            <button key={opt.id}
                    className={`opt-card ${isSel ? 'selected' : ''}`}
                    disabled={busy}
                    onClick={() => onSelect(opt.id)}>
              <div className="opt-card-head">
                <span className="opt-label">{opt.label}</span>
                {opt.id === RECOMMENDED && <span className="opt-badge">권장</span>}
              </div>
              {/* 미리보기 숫자 — 유저가 명확히 알도록 */}
              <div className="opt-preview">
                {pv.rows_delta === 0
                  ? `행수 유지 (${pv.rows_after}행)`
                  : `${pv.rows_after}행 (${pv.rows_delta > 0 ? '+' : ''}${pv.rows_delta})`}
              </div>
              {opt.id === "class_weight" && pv.weights && (
                <div className="opt-sub muted">
                  가중치 최대 ~{Math.max(...Object.values(pv.weights))}배
                </div>
              )}
              <div className="opt-desc muted">{opt.description}</div>
              {opt.caution && <div className="opt-caution muted">⚠ {opt.caution}</div>}
            </button>
          )
        })}
      </div>

      {/* 승인 버튼 — 선택해야 활성화 (강제 선택) */}
      <div className="opt-actions">
        <button className="btn" disabled={busy || !selected} onClick={onApprove}>
          {selected ? `'${selected}' 선택 적용` : "옵션을 선택하세요"}
        </button>
      </div>
    </div>
  )
}
```
> 강제 선택: `disabled={!selected}` — 옵션 안 고르면 승인 불가. 권장 배지는 class_weight에.

### 3-4. 전체 승인 버튼 — 옵션 미선택 있으면 비활성화
```jsx
// onApproveAll 영역
const hasUnselectedOptionStep = steps.some(
  (s) => !approved.has(s.step_key)
      && Array.isArray(s.available_options) && s.available_options.length > 0
      && !selectedOptions?.[s.step_key]
)
// 전체 승인 버튼: disabled={busy || hasUnselectedOptionStep}
// 안내: hasUnselectedOptionStep이면 "옵션 선택이 필요한 단계가 있습니다"
```

---

## 4. StandardizePage.jsx 확장

### 4-1. selectedOptions 로컬 state + onSelectOption
```jsx
const [selectedOptions, setSelectedOptions] = useState({})   // {step_key: option_id}

function onSelectOption(step_key, option_id) {
  setSelectedOptions((prev) => ({ ...prev, [step_key]: option_id }))
}
```

### 4-2. onApprove에 selected_option 동봉
```jsx
async function onApprove(step_key, stage_order, module_index, selected_option = null) {
  setBusy(true)
  try {
    await post(`/pipeline/${sid}/approve`,
               { step_key, stage_order, module_index, selected_option })  // ← 동봉
    await refresh()
  } catch (e) {
    setToast(`승인 실패: ${e.message}`)
  } finally {
    setBusy(false)
  }
}
```

### 4-3. onApproveAll — 옵션 step은 선택값 동봉
```jsx
async function onApproveAll(remainingSteps, stage_order, module_index) {
  setBusy(true)
  try {
    for (const s of remainingSteps) {
      const sel = selectedOptions[s.step_key] || null
      await post(`/pipeline/${sid}/approve`,
                 { step_key: s.step_key, stage_order, module_index, selected_option: sel })
    }
    await refresh()
  } catch (e) { setToast(`일괄 승인 실패: ${e.message}`) }
  finally { setBusy(false) }
}
```

### 4-4. ApprovalCard에 새 props 전달
```jsx
<ApprovalCard
  pending={pending}
  approvedKeys={view.approved_step_keys}
  busy={busy}
  selectedOptions={selectedOptions}      // ← 신규
  onSelectOption={onSelectOption}        // ← 신규
  onApprove={onApprove}
  onApproveAll={onApproveAll}
  onResume={onResume}
/>
```

---

## 5. styles.css — 옵션 카드 스타일 (기존 톤 유지)

```css
/* Option cards (STEP 2b) — 기존 approval 톤 유지 */
.opt-group { margin-top: 10px; margin-left: 32px; }
.opt-current { font-size: 12px; margin-bottom: 8px; }
.opt-cards {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
}
.opt-card {
  background: var(--panel-2); border: 1px solid var(--border);
  border-radius: 6px; padding: 10px; text-align: left; cursor: pointer;
  color: var(--text); transition: border-color 0.15s;
}
.opt-card:hover { border-color: var(--c-process); }
.opt-card.selected { border-color: var(--c-process); border-width: 2px; }
.opt-card-head { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.opt-label { font-weight: 600; font-size: 13px; }
.opt-badge {
  background: var(--c-quality); color: white; font-size: 10px;
  padding: 1px 5px; border-radius: 4px; font-weight: 700;
}
.opt-preview { font-size: 13px; font-weight: 600; color: var(--c-process); margin-bottom: 4px; }
.opt-sub { font-size: 11px; margin-bottom: 4px; }
.opt-desc { font-size: 11px; margin-bottom: 4px; }
.opt-caution { font-size: 11px; color: var(--c-maintenance); }
.opt-actions { margin-top: 10px; }
.opt-warn { margin-top: 8px; font-size: 12px; }
```
> 기존 토큰(--panel-2, --c-process 파랑, --c-quality 초록, --border) 재사용. L2 주황 보더 카드 톤과 정합.
> 폴리싱(애니메이션·고급 레이아웃)은 별도 단계 — 지금은 기능·정합 위주.

---

## 6. 절대 하지 말 것
- ❌ 백엔드(STEP 2a) 변경 (프론트만)
- ❌ 옵션 없는 step의 yes/no 동작 변경 (회귀 0 — available_options 비면 기존 그대로)
- ❌ 강제 선택 우회 (옵션 step은 선택 없이 승인 불가)
- ❌ 외부 UI 라이브러리(Tailwind 등) 추가
- ❌ 전면 리디자인·화려한 애니메이션 (UI 폴리싱은 별도 단계)
- ❌ 다른 페이지(1,2,3,5,6) 변경 (Page 4만)
- ❌ 문서 별표(★)

---

## 7. 검증 (완료 기준)

### 옵션 카드 렌더
- [ ] press_forming(event-log, PASS_YN 2.83%) → Page 4 실행 → balance_classes step에
      **옵션 카드 4개**(class_weight/smote/random_under/skip) 표시
- [ ] 각 카드에 미리보기 숫자: class_weight(3000 유지 + 가중치 17.6배), smote(5830 +2830),
      random_under(170 -2830), skip(3000 유지)
- [ ] class_weight에 "권장" 배지
- [ ] 현재 분포 요약 (PASS 2915 / FAIL 85, 2.83%) 표시
- [ ] 각 카드에 description + caution(주의사항)

### 강제 선택 + 승인
- [ ] 옵션 안 고르면 승인 버튼 비활성화 ("옵션을 선택하세요")
- [ ] 옵션 선택 시 카드 강조(파랑 보더) + 승인 버튼 활성화("'smote' 선택 적용")
- [ ] 승인 → POST approve에 selected_option 동봉 → resume → applied_strategy 반영
- [ ] 전체 승인: 옵션 미선택 step 있으면 비활성화

### 회귀
- [ ] cnc_machine_injection(옵션 없는 L2들) → 기존 yes/no 승인 그대로 동작
- [ ] available_options 빈 step은 옵션 영역 안 그림
- [ ] 다른 페이지(1,2,3,5,6) 영향 0

### 통합
- [ ] Page 1~6 전체 흐름 정상 (옵션 카드 포함)
- [ ] npm run build 성공
- [ ] 브라우저 직접 확인 (옵션 카드 클릭 → 선택 → 승인 → resume)

### 문서
- [ ] decisions.md D-110~ (옵션 카드 UI 카드형+강제선택+권장배지)
- [ ] 0_variable_index_v5.md (ApprovalCard props, selectedOptions, OptionCardGroup)
- [ ] 별표(★) 0건

---

## 8. 커밋 + 인계

### 작업 흐름
1. 0장 (브랜치 확인 + 컨텍스트)
2. ApprovalCard(옵션 카드) → StandardizePage(state+동봉) → styles.css
3. **전체 완성 후** 7장 검증 (브라우저 Page 4 옵션 카드 + 회귀)
4. **검증 후** 논리 단위 커밋 (feature/step2-option-cards, checkout/reset 금지):
   ```
   feat(STEP2b): extend ApprovalCard with option cards + preview rendering
   feat(STEP2b): add selectedOptions state + selected_option in approve (StandardizePage)
   feat(STEP2b): add option card styles (existing tone)
   docs(STEP2b): record D-110~ option-card UI + variable_index
   ```
5. **push는 claude.ai 검증 후** (feature/step2-option-cards로).

### 완료 후 claude.ai에 보고
- 7장 체크리스트 결과
- ApprovalCard/OptionCardGroup 코드
- **브라우저 스크린샷**: 옵션 카드 4개 (미리보기 숫자 + 권장 배지 + 현재 분포)
- 강제 선택 동작 (미선택 시 버튼 비활성 → 선택 시 활성)
- 승인 → resume → applied_strategy 반영
- 회귀 0 (옵션 없는 step yes/no 유지)
- `git branch` + `git log --oneline -6` + `git log --format='%an <%ae>' -1` (sbg0700 확인)

---

## 부록 — 헌법 정합 (왜 이 설계)
- **"LLM 제안, 사람 결정"의 시각화**: 카드형 + 강제 선택 = 사용자가 의식적으로 보정 방식을 결정.
  디폴트 자동이면 무심코 넘어가 단일 승인과 차이 없음 → 강제 선택으로 결정의 의미 보존.
- **추적성 연결**: 사용자가 명시적으로 고른 옵션이 selected_option으로 백엔드 lineage에 기록(STEP 2a) →
  "사용자가 SMOTE를 의식적으로 선택" 감사 가능 (SI 컴플라이언스).
- **권장 배지**: 강제 선택의 부담을 가이드로 완화 — 초보 사용자도 안전한 class_weight로 유도하되, 선택은 본인이.
- **회귀 안전**: available_options 없으면 기존 yes/no — 다른 L2·모달리티 영향 0.
- **프로토타입-애자일**: 기능·정합 위주, 기존 톤 재사용. 전체 UI 폴리싱은 STEP 2·3 후 별도 단계.
