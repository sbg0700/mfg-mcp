# LLM 리소스 모니터링·프로파일링 — README (진입 가이드) (v0_1)

> **이 문서의 역할**: 처음 보는 사람(팀원·새 AI 세션)을 **올바른 문서로 라우팅**하는 단일 진입점.
> 내용 자체는 각 문서가 소유하고, 여기선 **지도·읽는 순서·복붙 프롬프트**만 둔다(중복·drift 방지).
> phase 무관 상위 문서 — phase-1/2 갈래를 안내한다.

---

## 1. 한 줄 소개
한계 하드웨어(RTX 3070 **8GB VRAM**)에서 로컬 LLM(gemma4)의 **자원·성능을 실측·프로파일링**하는 작업 브랜치
(`feature/llm-profiling`). **정직 명명: "리소스 모니터링/프로파일링"이지 "스트림 파이프라인"이 아니다.**

## 2. 산출물 지도 (`monitoring/docs/`)
| 문서 | 역할 | 언제 보나 |
|---|---|---|
| **0_resource_README_v0_1** (본 문서) | 진입 가이드·라우팅 | 맨 처음 |
| **2_TEAMMATE_claude_memory** | 작업 규칙(git·커밋·충돌·측정순도) 단일 소스 | 작업 전 필수 |
| **0_resource_blueprint_phase1_v0_1** | 왜·무엇 (설계·서사·역할·가설) | 맥락 파악 |
| **0_resource_protocol_phase1_v0_1** | 고정값 계약 (사전등록·측정 파라미터·판정) | 측정 직전 |
| **1_HO_all_phase1_v0_1** (실행 시 `1_HO1~4_phase1_`로 분리) | 실행 핸드오프 (선결·투두·검증 게이트) | 실행 단계 |
| **BG_TROUBLESHOOT_llm_resource_optimization** | 상세 방법론·모델 메타·분기 타당성 원본 | 깊이 들어갈 때 |

> **충돌 우선순위**: blueprint(설계) > protocol(고정값) > handoff(실행). TROUBLESHOOT의 갱신 전 서술은
> blueprint/protocol에 양보(특히 시계=CLOCK_MONOTONIC, 훅=passive 전용).

## 3. 읽는 순서
**2_TEAMMATE(작업 규칙) → blueprint_phase1(왜·무엇) → protocol_phase1(고정값) → handoff(실행).**
역할별 진입: 팀원=TEAMMATE+blueprint / 측정 실행자=protocol+handoff / 새 AI 세션=아래 §5 프롬프트.

**phase 갈래**: 현재 문서는 전부 **phase-1(앞단 MCP·Agent 파이프라인 LLM)**. **phase-2(EDA·모델링·코드생성)는
phase-1 완료 후 STEP 3에서 main 구현 코드를 보고 별도 문서(`*_phase2_*`)로** 다룬다.

## 4. 핵심 규칙 요지 (상세는 blueprint Part 12 / protocol §9)
- **정직 명명** — 리소스 프로파일링이지 스트림 처리 아님.
- **N%는 controlled 동일모델 전후만** — 모델 비교는 개선이 아님. 측정 전 N% 약속 금지.
- **userspace only** — HTTP API + nvidia-smi/pynvml/psutil. CLI·journal·docker는 admin/팀원 영역(측정엔 영향 없음).
- **본진 PostgreSQL 안 씀** — 측정 로그는 parquet+DuckDB로 격리.
- **26b = 목표 모델(주인공)** — 8GB 가용성 판정 + 파라미터·하네스 실용권 시험. negative result도 정당한 산출.
- **baseline = HO3 재현성(CV) 확인된 controlled 수치만** — 알파 개발 중 값은 참고치.

## 5. AI 컨텍스트 로딩 프롬프트 (새 수행자 챗 — 복붙)
```
이 브랜치(feature/llm-profiling)의 phase-1 리소스 프로파일링 작업을 이어간다.
먼저 monitoring/docs/의 다음을 순서대로 읽어라:
1) 2_TEAMMATE_claude_memory.md  (작업·git 규칙 — 절대 준수)
2) 0_resource_blueprint_phase1_v0_1.md  (설계·서사 — 단일 진실원본)
3) 0_resource_protocol_phase1_v0_1.md  (측정 고정값 — 사전등록 계약)
4) 1_HO_all_phase1_v0_1.md  (실행 핸드오프)
충돌 시 우선순위: blueprint > protocol > handoff.
핵심 불변: 정직 명명 / N%는 controlled 동일모델 전후만 / userspace only /
본진 PG 안 씀 / 26b는 목표 모델 / baseline은 재현성 확인 수치만 / 측정값은 [실측], 미검증은 [추론].
phase-2(EDA·모델링)는 범위 밖 — STEP 3 후 별도.
```

## 6. 현재 상태 (2026-06-02)
**phase-1 설계 완료**(blueprint·protocol·handoff 정합) / **측정 코드 미작성** / **측정 미시작** /
**protocol §12 서명 전**. 다음 = HO1 착수(데이터셋 실재화·프롬프트 캡처·환경확정).

---

**갱신**: 파일명·상태 변경 시 본 문서 §2·§6 갱신. 라우팅만 담당 — 규칙·값의 출처는 각 문서.
