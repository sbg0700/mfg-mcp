# Datalake Redesign — README (진입점)

> mfg-mcp 데이터 계층 재설계. 이 문서는 **새 챗 부트스트랩의 첫 진입점**이다.

## 한 줄 정의
검증된 엔진(Inspector→Planner→Executor→Validator, EDA, ML 학습, harness)은 **변경 0**으로 보존하고,
**데이터 진입·셀렉·자료구조·Page 2/3 데이터 연결만** DB catalog 패러다임으로 재작성한다.

## 좌표
- 브랜치: `feature/datalake-redesign`
- worktree: `~/FINAL/0_BGS/datalake-redesign` (base `d56fd51` = **현 origin/main** — R0 확인: `dccea63`(pre-step3) + step3-eda-ml 머지 = `d56fd51`. not-behind, 리베이스 불요)
- `manufacturing-mcp` = **메인 repo 폴더**. 현재 `feature/llm-profiling`(우리 브랜치, **일시 보류**) 체크아웃. 데이터 플로우 재설계는 main에서 분기한 `datalake-redesign`에서 진행 — 작업·실측은 이 worktree에서 (profiling과 커밋이 달라 base가 다르므로)

## 역할
- **Master = Claude (claude.ai)** — 설계·검토·검증(코드 포함)·게이트 판정·핸드오프 작성·명세 patch 저작
- **Executor = Claude Code** — worktree에서 구현·자체 테스트·결과 보고 (게이트 판정 권한 없음)

## 현재 상태
- **설계 완료** (모든 결정 잠김 — BLUEPRINT 참조)
- **프로토콜 수립 완료** (PROTOCOL 참조)
- **R0 완료 = GATE PASS** (baseline 태그·이음매·KAMP·환경 확인 — R0_HANDOFF 참조)
- **오픈 3건 전부 해소**: git author=myeongsun97(현 config) / FFT=컬럼-그룹 descriptor / step2=252·step3=322줄
- **DL-2 완료 → DL-2.5(hardening) 완료(태그 DL-2.5) → 다음 단계: DL-3**

## 새 챗 재개 — 읽기 순서
1. **README** (이 문서 — 현재 단계·좌표·역할)
2. **BLUEPRINT** (설계 SSOT — 모든 결정·근거)
3. **PROTOCOL** (역할·단계 사이클·게이트·롤백 원칙)
4. **최신 단계 HANDOFF** (직전 단계 결과 + 다음 진입조건)
→ 그 다음, 다음 단계 프롬프트를 Master가 발행

## 단계 (워크플로우)
`R0 준비` → `R1 명세 patch` → `DL-1 DB연결+catalog` → `DL-2 적재+KAMP` → `DL-3 Page2/3+제약` → `DL-4 session/aggregator+EDA` → `DL-5 e2e 검증` → `R-final 통합·롤백 드릴·인계`
