# 팀원 작업 규칙 (Claude Code 메모리) — 트러블슈팅 / LLM 리소스 최적화

> **이 파일은 팀원(myeongsun) 전담 트러블슈팅 작업의 Claude Code 메모리다.**
> Claude Code는 작업 시작 시 이 파일을 읽고 아래 규칙을 항상 따른다.
> 메인 설계 헌법은 별도 `CLAUDE.md`(프로젝트 루트)에 있으며, 이 파일은 **협업·git 규칙**에 집중한다.

---

## 0. 작업 정체성
- **담당**: LLM 리소스 모니터링·프로파일링 + Ollama 자원 할당 최적화 (한계 하드웨어 RTX 3070 8GB).
- **상세 설계도**: `docs/specs/TROUBLESHOOT_llm_resource_optimization.md` (이 문서가 작업 명세).
- **작업 브랜치**: `feature/llm-profiling` (이 브랜치에서만 작업).

---

## 1. ★브랜치 규칙 (절대 준수)★
1. **작업 시작 전 항상 `git branch`로 현재 브랜치 확인.** `* feature/llm-profiling`이어야 함.
2. **커밋·push 모두 `feature/llm-profiling`로만.** `main`에 **직접 push 금지.**
3. 만약 다른 브랜치(main 등)에 있으면 → `git checkout feature/llm-profiling`로 이동 후 작업.
4. `git checkout`으로 작업 내용 되돌리기·`git reset`·`git rebase` **금지** (히스토리 훼손 위험). 필요 시 사람에게 보고.
5. **`git init` 절대 실행 금지.** (상위 폴더에 잘못된 git 레포가 생기는 사고 방지)
6. VS Code/작업 폴더는 항상 clone 루트(`manufacturing-mcp`)여야 함. 상위 폴더에서 git 명령 실행 금지.

---

## 2. ★커밋 메시지 표준 (Conventional Commits, 영어)★
형식: `type(scope): summary` — **영어로**, 명령형, 한 줄 요약.

**type 7종:**
| type | 용도 | 예시 |
|---|---|---|
| `feat` | 새 기능 추가 | `feat(profiler): add pynvml resource sampler` |
| `fix` | 버그 수정 | `fix(profiler): correct VRAM attribution for offload` |
| `docs` | 문서만 변경 | `docs(profiler): record e2b vs e4b benchmark results` |
| `test` | 테스트 추가/수정 | `test(profiler): add controlled prompt battery` |
| `refactor` | 동작 변경 없는 구조 개선 | `refactor(profiler): extract sampler loop into module` |
| `chore` | 빌드/설정/잡무 | `chore: add pynvml to requirements` |
| `style` | 포맷팅(동작 무관) | `style(profiler): format sampler with black` |

- scope: 작업 영역 (`profiler`, `sampler`, `bench`, `llm` 등).
- 본진 작업 흐름과 동일 — 전체 완성 → 검증 → **마지막에 논리 단위로 커밋**. 중간 커밋 남발 금지.
- push는 검증 완료 + 사람(설계자) 확인 후. (단, 팀원 브랜치라 본진보다 자유로움 — 단 main 병합 전 정리)

---

## 3. ★충돌 회피 — 새 파일 우선 원칙★
머지(나중에 main 병합) 시 충돌을 최소화하기 위한 핵심 규칙. 충돌은 "둘이 같은 파일 같은 줄을 고칠 때" 발생하므로:

### 3-1. 기본 — 새 Py 파일로
- 프로파일러·샘플러·분석·벤치마크는 **새 파일**로 만든다. 기존 파일 수정 최소화.
- 권장 위치: `monitoring/` 또는 `tools/profiling/` 디렉터리 신설 (본진 코드와 물리적 분리).
  - 예: `monitoring/llm_resource_sampler.py`, `monitoring/ps_poller.py`, `monitoring/bench_battery.py`,
       `monitoring/analyze_logs.py`
- 로그 출력도 별도 디렉터리: `logs/profiling/` (gitignore 대상 — 측정 데이터는 커밋 안 함).

### 3-2. 불가피한 기존 파일 수정 — 격리·최소·사전 공유
설계도상 `backend/llm.py`의 `generate()`에 PROFILE 훅(call_id, origin_ts_ns)이 필요하다. 이건 기존 파일 수정이므로:
- **최소 침습**: `generate()` 본문엔 2줄 내외만. 무거운 로직은 **별도 함수**(`_profile_log()`)로 빼서 llm.py 하단 또는 별도 모듈에.
- **PROFILE 가드 필수**: `LLM_PROFILE` 환경변수가 `"1"`일 때만 동작. 기본(`"0"`)이면 **본 기능 완전 무영향**.
  ```python
  PROFILE = os.environ.get("LLM_PROFILE", "0") == "1"
  # generate() 안: if PROFILE: ... (가드 없이는 어떤 측정 코드도 실행 안 됨)
  ```
- **수정한 기존 파일은 반드시 설계자(병갑)에게 사전 공유.** 어떤 파일 몇 줄을 왜 고쳤는지 보고 → 머지 전 충돌 조율.
- 같은 파일을 설계자도 STEP 2에서 건드릴 수 있음(`llm.py`, `main.py`). 겹치는 파일은 특히 조심.

### 3-3. 절대 건드리지 말 것 (본진 핵심 — 설계자 영역)
- `agents/` (inspector/planner/executor/validator) — 본진 로직. 측정 훅도 여기 넣지 말 것.
- `frontend/` — STEP 2b(설계자)가 작업. UI 리소스 표시가 필요하면 설계자와 별도 협의.
- `catalogs/`, `harness/` — 설계 헌법 영역.
- `docs/decisions.md` — 설계자가 관리. 팀원 결정은 트러블슈팅 문서 안에 기록.
→ 측정은 "본진을 관측"하되 "본진을 바꾸지 않는다" (사이드카 원칙, 설계도 §3-1 방식 ii).

---

## 4. 측정 순도 (설계 헌법 정합)
- 코드=호스트/도커 헌법 유지. 프로파일러가 26b CPU offload 코어와 경합 금지 → `taskset` 핀.
- 측정 도구는 본진과 분리된 프로세스(사이드카). 본진 로그엔 call_id/origin_ts_ns 최소 키만.
- 명명 정직: "리소스 모니터링/프로파일링" — "스트림 파이프라인" 등 과장 금지.
- "N% 개선" 주장은 **동일 조건 최적화 전후(controlled, baseline 대비)**로만. 모델 비교는 개선 아님.

---

## 5. 작업 전 체크리스트 (매 세션 시작 시)
```bash
git branch                    # * feature/llm-profiling 확인
git status                    # 워킹트리 상태 확인
git config user.name          # 팀원 본인 이름 (커밋 작성자)
git config user.email         # 팀원 GitHub 이메일 (잔디·Contributor 연결)
git log --oneline -3          # 현재 위치 확인
```
- `user.email`이 GitHub 계정 이메일이어야 커밋이 팀원 기여로 잡힘 (잔디·Contributor).
- Claude Code가 작성자를 임의로 바꾸지 않도록, 커밋 후 `git log --format='%an <%ae>' -1`로 확인 권장.

---

## 6. 완료·보고
- 트러블슈팅 결과(트레이드오프 표, 최적화 전후, 서사 문서)는 `docs/specs/` 또는 `monitoring/`에 정리.
- 본진 수정분(llm.py 훅 등)은 설계자에게 별도 보고 → 머지 전 검토.
- main 병합은 나중에 GitHub PR로 (설계자와 함께). 팀원 단독 main push 금지.

---

## 부록 — 이 규칙이 왜 필요한가 (배경)
- 같은 리눅스 서버, 다른 계정(myeongsun97)·다른 폴더(`~/FINAL/0_BGS/manufacturing-mcp`)·다른 브랜치에서 작업.
- 설계자(병갑)는 `feature/step2-option-cards`에서 STEP 2 진행 중. 두 작업은 독립적.
- 새 파일 우선 + 기존 수정 격리 → 나중 머지 시 충돌 최소화.
- 과거 사고: 상위 폴더 `git init`으로 2860개 untracked 발생 → `git init` 금지·폴더 루트 확인 규칙 추가.
