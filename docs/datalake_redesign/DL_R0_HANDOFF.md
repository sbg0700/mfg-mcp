[HANDOFF] 단계: R0 (준비·롤백 기준점 + 규모/환경 실측)
판정: **GATE PASS** (Master 검증 완료, 2026-06-05) — DL-1 진입 가능. 단 진입 선결 2건 + R1 입력 3건.

## 완료 (게이트 증거)
- baseline 태그 `dl-baseline-20260605` (worktree, 커밋 0). 롤백 원점 확보.
- **base 확정: `d56fd51` = 현 origin/main** (`dccea63`(pre-step3) + step3-eda-ml 머지 = d56fd51). datalake-redesign not-behind → 리베이스 불요. (CC 이전 세션의 dccea63은 step3 머지 전 stale 값이었음.)
- deps 존재: `backend/requirements.txt`, `frontend/package.json` (Vite/React, src/step1~6).

## R0 확인 이음매 (d56fd51 기준 — 이전 llm-profiling 측정값을 대체)
| 이음매 | 위치 | DL 연결 |
|---|---|---|
| ① modality 라우터 | `executor.py:44` `_resolve(id, modality)` (호출 `:207`) | DL-1 `datalake.get→data_path` 연결점 |
| ② EDA payload | `eda_engine.py:173-174` (ctx에서 `key_findings[:10]` + `user_intent`만) | DL-4 slim stage_chain 주입 |
| ③ EDA 호출부 | `main.py` aggregated_context (610·773…), 총 1483줄 | — |
| ④ stage_chain | `context_aggregator.py` `_build_stage_chain:287` · `_build_agent_record:72` | DL-4 vid 전파 |
| ⑤ constraint | `main.py:195-224` (옵션, **빈값=기존동작**) | DL-3 제약 경로 |
→ R1·BLUEPRINT는 이 확정 refs 사용. (이전 진단의 `:168-175` 등은 폐기.)

## KAMP (5.1G) 확인
- 3 module: **metal / forming_joining / polymer** (= module_1/2/3).
- 대부분 일반 CSV+헤더(ASCII — **cp949 우려 해소**).
- ★ **L3 vibration = FFT 광폭**(컬럼=주파수값, 숫자헤더) → 적재도구·catalog 특수 처리 필요(아래 R1 입력 [설계]).

## DL-1 진입 선결조건 (게이트)
1. **`.env` DB 접속 추가** — host=127.0.0.1, port=5432(열림 확인), user/pass/db = **사용자 시크릿(터미널 확인)**. 
   - ★ 이 PG는 **byeonggab89 공유 스택** → 첫 쓰기(마이그레이션) 전 **DB 백업 + 조율**.
2. **변경 전 build+smoke green 1회** (R0서 deps만 확인 — 실행 검증은 DL-1 진입 시).

## 오픈 항목 — 전부 해소 (2026-06-07)
- ✅ **git commit author = `myeongsun97`** — 현 config가 이미 `myeongsun125 <myeongsun97@gmail.com>` → **변경 불요**.
- ✅ **FFT 광폭/숫자헤더 catalog 표현 = 컬럼-그룹 descriptor** (`column_kind = scalar | group`), 제약은 집계/대역형(per-column 부적합). BLUEPRINT §1.2 반영, **사용자 확인 완료**.
- ✅ **step2/step3 UI 규모 측정 완료** — step2(Page2)=252줄, step3(Page3 제약)=322줄 → **DL-3(Page2/3)=~574줄**. backend 핸들러: `/datasets/all`:94 · `execute_pipeline`:442 · `status`:625 · `approve`:644.

## 다음 단계
**R1 (명세 patch)** — Master 저작 → CC 적용. **오픈 3건 전부 해소 → R1 착수 가능**. (DL-1 선결조건 = .env DB·공유PG 백업·build/smoke green은 R1 이후.)
재개 지시: worktree `~/FINAL/0_BGS/datalake-redesign`, branch `feature/datalake-redesign`, 읽기순서 README→BLUEPRINT→PROTOCOL→이 HANDOFF.
