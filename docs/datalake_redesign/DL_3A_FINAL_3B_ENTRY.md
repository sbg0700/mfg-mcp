# DL-3a FINAL + 3b ENTRY — Master 통합 핸드오프 (새 Master 챗 부트스트랩)

> 작성: 2026-06-11, 직전 Master 챗(DL-2.5~3a 수행) 인계본. 이 문서가 현 시점 권위.
> 읽기순서: DL_README → DL_BLUEPRINT → DL_PROTOCOL → **이 문서** (§4의 3b 프롬프트 전문 포함).
> 프로젝트 지식: spec-1·decisions.md 최신 반영 상태 — 단 부트스트랩 첫 액션으로 신선도 재검증(§5).

---

## §1. 현재 좌표

- worktree `~/FINAL/0_BGS/datalake-redesign` · branch `feature/datalake-redesign` · 원격 `github.com/sbg0700/mfg-mcp`
- 단계: **DL-3b 진행 중** (3b 프롬프트 발행 완료 — CC(Fable) 실행 중 또는 보고 대기. 새 Master의 첫 임무 = 3b 보고 게이트 판정)
- 태그 체인: dl-baseline-20260605 → DL-2-A → DL-2-B → DL-2.5 → **DL-3-A** (3a PASS 후 push+태그 지시됨 — Phase 0에서 반영 확인)
- decisions max = **D-187** (3b 커밋 ⓒ 완료 시 D-188)
- Executor 모델 = **Fable** (DL-3부터). 프롬프트 스타일 = 목표·불변식·게이트 잠금 + 구현 세부 위임. 거버넌스(게이트/[STOP]/증거보고/granular 커밋/라이브 쓰기 체크포인트)는 불변.

## §2. DL-3a — CLOSED (GATE PASS, 2026-06-11)

- 커밋: ⓐ `a80e6c8`(docs: D-186·D-187 + spec 표 동기 + Mode A 이월 표기 + variable_index D-159 잔재 정정) ⓑ `3772bfb`(feat: backend/datalake_api.py + main.py 2줄) ⓒ `ea1b6c3`(test: API 9건 + httpx 핀)
- 산출: `/api/datalake/*` 7종(list·metadata·columns·constraints GET/POST·register Mode B·DELETE), pytest 22 green(13+9), main.py diff = import/include 2줄뿐, 라이브 무접촉, data/lake 32 불변.
- 신규 결정: **D-186**(register = Mode B 한정·slug id·충돌 409·function_hint→function 해석, Mode A 이월=데모 후 재결정) · **D-187**(API 표면 확장 3종 — columns·constraints GET/POST, spec §1-3/spec-3 §9-1 표 동기)
- 판정 시 룰링 4건: ① §4-11 Mode A 체크박스는 1개(Master 전제 오류) → §4-7 "100MB 초과(Mode A)" 행 포함 전수 이월 표기로 의도 충족 ② variable_index 잔재 실위치 = §1+§13(§8 아님) 정정 승인 ③ 위임 선택 승인(function_hint 4종 검증·GET 404 일관·바이트 보존 복사+encoding NULL 명시) ④ **DELETE = DB-only 승인 + orphan 리스크 발견**: data/lake/<id>/ 잔존 시 동일 id 재등록이 silent 복사 가능 → **3b 커밋 ⓞ로 가드 추가 지시됨**.

## §3. 직전 맥락 (새 Master가 grep하고 놀라지 않도록)

- **order_cp949 = 두 네임스페이스**: (a) KAMP 카탈로그 구 hint → `order_planning`으로 정정 완료(커밋 `4e47e3d`, push됨) (b) **합성 더미 실명** — `data/synthetic/generate.py`가 챌린지 1(CP949)용 더미를 의도적으로 `order_cp949.csv`로 생성. 더미 동렬 맥락의 참조(spec-3:495·571 / inspector.md:23 / blueprint:992·1004·1362) + manifest provenance 주석 2 = **의도 보존이 정답**. grep에 잡혀도 정정 금지.
- spec-1 §1-9-2 "KAMP 5 데이터셋" 리스트의 나머지 4개 명칭(press_imbalance 등)도 manifest id와 불일치 가능 → **3c 트래킹** (지금 건드리지 말 것).
- DL-2.5에서 constraints 감사 체계 완비: approved_by + constraints_history(append-only·FK 없음), **불변식 = constraints의 모든 현재·미래 쓰기 경로는 동일 트랜잭션 history append 의무(D-179)**. 백엔드 쓰기는 insert_constraint 경유만.
- 테스트 규율(D-182): throwaway PG 127.0.0.1:55432/dl_test 전용, conftest 하드가드(PG* 강제 override + assert 트립와이어), DOCKER_HOST는 코드 레벨 명시(`unix:///run/user/1002/docker.sock`). 라이브 접촉 = 게이트 시점만.
- 백업(D-183): 복원 드릴 1회 성공 완료. **3c 직전 fresh dump 필수**(constraints 첫 실쓰기 단계).

## §4. 3b 프롬프트 전문 (발행본 — 게이트 판정은 이 기준 그대로)

[DL-3b / Page 3 셀렉 (frontend) — Master 발행, Executor=CC(Fable)]
직전: DL-3a GATE PASS(tag DL-3-A, push 완료 전제). 목표: VITE_DL_UI_V2 게이트 뒤
신규 Page 3 셀렉(카드 UI, catalog 소스). 구 경로 무접촉(D-181/184).
불변식 충돌·전제 불일치 = [STOP]. push/tag는 Master GATE PASS 후.

Phase 0 — 진입 게이트 + 실측 3종 (READ-ONLY)
기본: branch·clean·origin 0/0(DL-3-A 반영)·decisions max=D-187·pytest 22 green.
실측 (보고 필수):
 (i) vid 값 체계 정합 — lines.yaml line_id 전수 ↔ manifest vid DISTINCT 대조.
     line_id ⊆ vid green → 신 Page 3는 session line_id를 vid 필터로 직사용 + D-188 기록.
     불일치 → [STOP] (매핑 룰링 필요 — 3b 본체 착수 금지).
 (ii) constraints 소비처 실측 (3c 설계 재료, 변경 0) — pipeline_full.modules[].constraints가
     execute_pipeline→Planner/엔진으로 흐르는 경로 grep + 기대 shape 코드 인용. 보고만.
 (iii) frontend VITE_* 사용 현황(기대 0) + 라우트 구조 확인.

잠긴 설계 (세부 위임)
A. 플래그: import.meta.env.VITE_DL_UI_V2 (미설정=off=구 경로 그대로). off 시 구 라우트 동작 변경 0.
B. 신 Page 3 v2: 별도 컴포넌트 디렉터리(네이밍 위임). 셀렉 = vid(=session line_id)×function×site
   → GET /api/datalake/list → 카드(이름/modality/크기) → datalake_id 바인딩 (D-166, §4-3).
   컬럼 표시 소스 = GET /api/datalake/{id}/columns. __dupN = 원본 헤더명+중복 배지, 드롭·은닉 금지(D-180).
C. 제약 폼 = 3c 범위 — 전환기엔 구 ConstraintForm import 재사용만(구 파일 무수정, 3c 교체 주석).
   register 모달 UI도 3c 이월(백엔드는 3a 완비).
D. api.js: datalake 클라이언트 함수 additive 추가(기존 함수 무수정).
E. 구 컴포넌트 파일(jsx 7종·api.js 기존부) 무수정 — git diff 증명.
F. register orphan-dir 가드(3a 후속): LAKE_ROOT/<id> 디렉터리 실존 시 DB 부재여도 409(orphan 명시). 테스트 1건.
G. SSOT 교차 테스트: tests/test_ssot_cross.py — lines.yaml hint_dataset ⊆ manifest id 집합 ·
   line_id ⊆ manifest vid 집합. yaml 파싱만(DB·throwaway 불요).

문서 (표준 2칸 표 형식)
D-188 | vid 값 체계 = lines.yaml line_id와 동일 체계(실측 확정 — Phase 0 (i) 수치 기입).
신 Page 3 필터는 session line_id를 vid로 직사용. 교차 정합은 test_ssot_cross.py 상시 박제(D-182). |
Page 1→3 바인딩 키가 문서상 미보증 — 이중 SSOT 교차 참조의 order_cp949형 사고 재발 차단.

커밋: ⓞ fix(orphan 가드+테스트) ⓐ test(SSOT 교차) ⓑ feat(frontend: 플래그+Page 3 v2 셀렉) ⓒ docs(D-188)
GATE: ① pytest 전체 green(22+신규, 전문) ② vite build green ③ git diff로 구 컴포넌트·구 핸들러 0접촉
④ 플래그 off 수동 체크(구 Page 3 렌더·셀렉·다음 이동 정상 — 체크리스트 보고) ⑤ 플래그 on 수동 e2e 1회
(카드 필터→셀렉→바인딩, 상태 인용) ⑥ 라이브 무접촉.
보고: 게이트 증거 + Phase 0 실측 3종 + 검증 핵심부 인용(플래그 분기점/카드 필터 쿼리/__dupN 배지/orphan 가드)
+ 커밋 4건 해시 + 이탈/[STOP].

## §5. 새 Master 부트스트랩 절차

1. 첨부 확인: DL_ 문서 3종(README/BLUEPRINT/PROTOCOL) + 이 문서 + **CC의 3b 보고** + **3bc 14파일**(frontend jsx 7종·main/App/api/modality·session_store·STEP_1B-3a/3b — 3b 코드리뷰 대조용).
2. 신선도 검증: 프로젝트 지식 decisions.md max 확인(이 문서 시점 D-187, 3b ⓒ 후 D-188 — 더 크면 이 문서가 stale이니 병갑에게 최신 핸드오프 요청). spec-1 §1-5에 approved_by·constraints_history 존재 확인.
3. 3b 보고를 §4 게이트 기준 그대로 판정 → PASS 시 push+tag DL-3-B 지시, worklog는 단계 묶음(DL-3 종료 시 일괄 또는 서브게이트별 — Master 재량) → 3c 프롬프트 저작.
4. 3c 저작 시 §6 carry-over 전 항목 소화 + Phase 0 (ii) 실측 기반 constraints shape 룰링 선행.

## §6. Carry-over 트래킹 (3c·DL-4/5 프롬프트와 핸드오프에 계속 승계)

- [3c 전·Master 룰링] constraints shape 신구 호환 — 3b Phase 0 (ii) 실측 기반.
  직전 Master 잠정 선호: catalog=D-180 shape, session=구 shape({col:[min,max]}) 다운컨버트 → 엔진 무변경.
- [3c] §1-9-2 명칭 리스트 전체 정합 / STEP_1B-3a·3b 문서 지위 룰링(폐기·대체·갱신) /
  3c 직전 fresh dump(D-183) / 정기 백업 주기 D-보강("GATE PASS 클로즈아웃 = push+프로젝트지식 갱신+fresh dump") /
  register 모달 UI / D-185 type별 필드 byte 대조(Part 1-2(가)·§4-4) / 전용 delete_constraint(D-179 불변식 준수)
- [DL-5 전·Master 룰링] D-168 validator 알람의 additive 경계("엔진 로직 불변" 해석)
- [데모 후·병갑] register Mode A 재결정
- [R-final] python 3.10 vs 3.11 / 프론트 e2e 도입 재평가(잠정: 수동 유지) / decisions↔CHANGELOG 분리 /
  DOCKER_HOST .bashrc 영구 수정(병갑) / DELETE orphan 파일 정리 정책

## §7. 역할·규율 리마인드

- 병갑 = 권한자·도메인 결정·env/시크릿/백업 실행. Master = 설계·룰링·게이트 판정·프롬프트/핸드오프 저작(환경·.env 비접촉, E2 경계). CC(Fable) = worktree 구현·자체검증·보고.
- push/tag = Master GATE PASS 후만. 세션 경계 = 원격 동기 유지(E5 교훈). 라이브 쓰기 = 명시 체크포인트만.
- decisions 기록 = 표준 2칸 표, 별표(*) 강조 금지, 번호 = 현재 max+1.
