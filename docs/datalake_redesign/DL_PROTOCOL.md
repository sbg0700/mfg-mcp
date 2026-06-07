# Datalake Redesign — PROTOCOL (운영 체계)

> Master/Executor 협업으로 단계별 실행하며, 각 단계 끝에 핸드오프를 남겨 **새 챗에서도 이어지게** 한다.
> 목표: 견고함 + **롤백 가능성 최소화**.

---

## 0. 역할
- **Master = Claude (claude.ai)** — 설계, 검토, 코드 검증, 게이트 판정, 단계 핸드오프 작성, 명세 patch 저작.
- **Executor = Claude Code** — worktree에서 구현, 자체 테스트, **결과 보고**. 설계·게이트 판정 권한 없음(보고 후 Master 승인 대기).
- `feature/llm-profiling`은 **우리 자신의 브랜치(리소스 프로파일링), 현재 일시 보류**. `manufacturing-mcp`(메인)에서 분기한 `datalake-redesign`이 현재 작업 브랜치. 이 프로토콜은 datalake-redesign 전용.

## 1. ★ Worktree 고정 (중대)
- 모든 작업 = **`~/FINAL/0_BGS/datalake-redesign`** (feature/datalake-redesign).
- `manufacturing-mcp` worktree(llm-profiling)에서 작업·실측 **금지** — 다른 브랜치라 파일 상태가 다름.
- 매 CC 작업 첫 줄: `cd ~/FINAL/0_BGS/datalake-redesign && git branch --show-current` → `feature/datalake-redesign` 확인.
- 주의: 이전에 llm-profiling worktree에서 나온 실측/라인참조는 우리 브랜치 기준 재확인 대상(R0에서 처리).

## 2. 단계 사이클 (매 단계 반복)
1. **Master가 단계 프롬프트 발행** — 목표·범위·게이트 기준·보고 항목 명시.
2. **Executor 실행** — worktree에서 ultrathink, **granular 커밋**(push는 지시 시만), 게이트 자체 테스트.
3. **Executor 보고** — 수행 내역(파일/라인) + 게이트 증거(테스트 출력) + **검증 핵심부 코드 인용** + 이탈/이슈.
4. **Master 검증** — 보고 + 코드 인용 검토(특히 검증 핵심부) + 교차검증 → 판정: **GATE PASS** 또는 **FIX**.
5. FIX → Master 교정 프롬프트 → (2)로. PASS → (6).
6. **Master가 단계 핸드오프 작성**(§6 템플릿).
7. 컨텍스트 무거우면 **새 챗** — §5 부트스트랩으로 재개.

> 사용자(병갑)는 매 단계 전환 시 결과·진행을 보고받고 확인 후 넘어간다. 검증이 필요한 코드는 Master가 함께 확인한다.

## 3. 게이트·롤백 원칙 (롤백 최소화)
- **additive 범위 구분 (★ 전체로 오독 금지):**
  - 핵심 compute 엔진(Inspector·Planner·Executor·Validator·ML 학습) = **기존 로직 불변**(데이터 소스 seam만 additive) → 구 경로 생존.
  - aggregator·EDA = **additive만**(vid 전파·slim stage_chain) — 파일 diff는 생기되 로직 0.
  - **Page 2/3 = 계획된 교체(재설계 본체)** — '구 경로 생존' 대상 아님. 전환기 feature-gate로 병존, DL-5 green 후 구 경로 제거.
- **멱등·비파괴 마이그레이션** — `CREATE … IF NOT EXISTS`, **DROP 금지**.
- **DB 백업 = DL-2 진입 게이트**(준비도 아님 — 데이터 손실 강제 차단). 공유 postgres면 DL-1 마이그레이션 전에도.
- **phase별 GATE green 필수** + **red면 직전 태그/커밋으로 즉시 되감기** 후 재시도. 미통과 시 다음 단계 진입 금지.
- **granular 커밋** — 되감기 지점 촘촘히.
- **feature-gate(Page 2/3)** — 신규 경로를 구 경로와 공존, DL-5 green 전까지 구 경로 안 뜯음.
- **baseline 태그(R0)** + **R-final 롤백 드릴**(사고 전 1회 되감아 복구 절차 검증).

## 4. 검증 핵심부 (Master 코드리뷰 필수 항목)
- **R1** — 문서 교차검증(blueprint↔spec↔variable_index↔decisions 모순 0). 순수 문서, 코드 0.
- **DL-1** — **진입 게이트: ① `.env` DB 접속 추가(5432 열림 확인, 자격=사용자 시크릿) ② 변경 전 build+smoke green ③ 공유 PG(byeonggab89)면 첫 쓰기 전 백업**; 마이그레이션 멱등(2회=동일), `datalake.get` round-trip, additive(기존 스키마 불변).
- **DL-2** — **진입 게이트: DB 백업 완료**; 건수 일치(스캔=INSERT), 인코딩 깨짐 0, `datalake.get` 샘플 읽힘, 멱등 재적재.
- **DL-3** — 제약 머지 3케이스(세션/카탈로그prefill/빈칸), **재승인 게이트(prefill 자동적용 0)**, 기존 흐름 회귀 0.
- **DL-4** — vid 끝까지 전파, EDA payload에 slim 들어감, 결정론 `compute_chart_data` 불변(D-59).
- **DL-5** — 핵심 compute 엔진(Inspector·Planner·Executor·Validator·학습) **기존 로직 불변**(aggregator·EDA·데이터 seam은 additive diff 허용, 로직 0 확인), e2e 실데이터 완주, 기존 8 챌린지 회귀 통과.

## 5. 새 챗 부트스트랩 (읽기 순서)
1. **README** (현재 단계·좌표·역할)
2. **BLUEPRINT** (설계 SSOT)
3. **PROTOCOL** (이 문서)
4. **최신 단계 HANDOFF** (직전 결과·다음 진입조건)
→ 그 다음, Master가 다음 단계 프롬프트 발행.

## 6. 단계 핸드오프 템플릿
```
[HANDOFF] 단계: (R0 / R1 / DL-n)
- 완료 커밋: <해시>
- 게이트 증거: <통과 항목 + 테스트 출력 요약>
- 현재 상태: <지금 존재하는 것>
- 변경 파일: <목록>
- 이탈/오픈: <예외·미결>
- 다음 단계: <목표 + 진입조건>
- 재개 지시: worktree=~/FINAL/0_BGS/datalake-redesign, branch=feature/datalake-redesign, 읽기순서=README→BLUEPRINT→PROTOCOL→이 HANDOFF
```

## 7. 단계 목록 + 추정 (CC 트리 기반 [추론], gate 포함)
| 단계 | 내용 | [추론] wall-clock |
|---|---|---|
| R0 | 롤백 기준점 + 규모/환경 실측 (worktree에서) | 0.5–1h |
| R1 | 명세 patch (Master 저작 → CC 적용, 문서) | ~0.5일 |
| DL-1 | DB 연결 + catalog 접근 계층 | 0.5–1일 |
| DL-2 | 적재 도구 + KAMP 5.1G 적재 | 1–1.5일 |
| DL-3 | Page 2/3 + 제약 (최대 덩어리) | 1.5–2.5일 |
| DL-4 | session/aggregator 스레딩 + EDA | ~0.5일 |
| DL-5 | 엔진 결합 e2e 검증 (회귀 게이트) | 0.5–1일 |
| R-final | 통합·롤백 드릴·인계 | ~0.5일 |

**추정을 흔드는 3대 변수:** ① DL-1 DB접근·포트 조율 ② DL-2 KAMP 실데이터 quirk(인코딩·이종) ③ DL-3 Page2/3 재작성 범위. → R0 실측으로 좁힘.

## 8. 분업
- **실행 환경 = myeongsun97 계정/홈** (worktree·KAMP·CC 실행). **설계·검토·게이트 = 병갑(Master)**.
- 병갑이 R0~DL-5(데이터 연결·전체 플로우·기본 UI·오류점검) 완성 → 팀원이 완성 코드베이스로 front 디자인. worktree 분리라 충돌 0.
- byeonggab89 = 실행 중 docker 스택(infra) 호스트. profiling = 일시 보류.
- **[확인 필요] 커밋 author·datalake 실행 주체** — worktree가 myeongsun97 홈이라 실행 계정이 myeongsun97인지, git author를 sbg0700/myeongsun97 중 무엇으로 둘지 R0에서 확정.
