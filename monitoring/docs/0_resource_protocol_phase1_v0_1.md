# LLM 리소스 모니터링·프로파일링 — 측정 protocol · phase-1 (MCP) (v0_1)

> **범위 (★)**: 본 protocol은 **phase-1 — 앞단 MCP·Agent 파이프라인 LLM 측정**(프롬프트 P1·P2·P3)의
> 고정값 계약이다. **phase-2(EDA·모델링·코드생성 LLM)는 phase-1 완료 후 STEP 3에서 main 구현 코드를
> 확인해 별도 protocol로 다룬다**(여기선 다루지 않음).
>
> **문서 목적**: 측정의 **모든 고정값을 측정 시작 전에 못박는 계약(사전등록, pre-registration)**.
> 이 문서가 정한 값으로만 측정하고, 값이 바뀌면 그 값으로 잰 데이터는 무효가 된다. 목적은 **사후
> cherry-pick 차단 = "N% 개선"의 정직성 담보**.
>
> **상위 문서**: 설계 근거·이유는 `0_resource_blueprint_phase1_v0_1.md`(이하 blueprint). 충돌 시 **blueprint(설계)
> 우선**, 본 문서는 그 아래 고정값 계약. 작업 규칙은 `2_TEAMMATE_claude_memory.md`. 상세 방법론 원본은
> `BG_TROUBLESHOOT_llm_resource_optimization.md`.
>
> **Snapshot**: 2026-06-02 v0_1 (측정 코드 미작성 / 측정 미시작 / 서명 전).
>
> **표기 규칙**: 강조는 굵게(**)/인용(>)만(별표 금지). 한국어 우선·식별자 영문. 호스트명 = `LINUX-server`.
> **`[LOCKED]`** = 변경 시 재측정 + 버전 범프 / **`[OPEN]`** = 측정 전 채울 값 / **`[측정 후 v0_2]`** = 측정 결과로 확정.

---

## §0. 이 문서의 지위 + 무효화 규칙

### 0-1. 사전등록의 의미
- protocol은 **측정 전에** 모든 파라미터·판정 규칙을 고정한다. 측정 후 "유리한 조건만 골라 N%"가 불가능해진다.
- 이것이 본 브랜치 차별점("정직한 N%")의 **방법론적 뿌리**다. 측정 전 약속한 분모로만 개선을 주장한다.

### 0-2. 무효화 규칙 `[LOCKED]`
> **`[LOCKED]` 표시된 값이 바뀌면, 그 값으로 잰 모든 측정은 무효다.** 변경 시 → (1) 본 문서 버전 범프
> (`v0_1→v0_2`) + 헤더에 변경 사유 (2) 영향받은 셀 **재측정**. 측정 도중 값을 바꿔 끼우는 행위 금지.

### 0-3. 서명 전 진입 금지
§12 서명(myeongsun97 + byeonggab89) **완료 후** 측정 시작. 서명 = "이 고정값에 합의했고, 이후 결과는
이 계약 기준"의 확인.

---

## §1. 측정 대상 + 양자화 (block 1) `[LOCKED]`
> **워크로드 = phase-1(앞단 MCP·Agent 파이프라인 LLM, 프롬프트 P1·P2·P3 §2).** EDA·모델링·코드생성은 phase-2(별도 protocol).

| 모델 | 양자화 | 역할 | 설치 |
|---|---|---|---|
| `gemma4:e2b` | Q4_K_M | 8GB **하한**(GPU 100% 적재 유일) + 보조 N% — **품질 게이트(HO1 스모크) 통과 시 대안 자격** | **미설치 → pull 필요** `[OPEN: 시점]` |
| `gemma4:e4b` | Q4_K_M | 8GB **균형 현실선** + 동일모델 최적화 N% 주력 | 설치됨 |
| `gemma4:26b` | Q4_K_M | **목표 모델(주인공)** — 8GB 가용성 판정 + 파라미터·하네스 실용권 시험 | 설치됨 — **§9-4 강등 규칙 적용** |

- **양자화 = Q4_K_M 고정.** Q3/Q2 추가 pull은 **선택**(진단 후, 시간 남으면) → `[OPEN]`.
- **제외**: 31B Dense·super\*/uncensored (blueprint Part 1-5). 측정 1회 적재도 금지.

---

## §2. 프롬프트 + 입력 고정 (block 2)

### 2-1. 실프롬프트 3종 (phase-1 MCP 워크로드) `[LOCKED 구성 / OPEN 텍스트]`
| ID | 출처 | 성격 |
|---|---|---|
| `P1_analyze` | Page 5 분석목적 추천 LLM 호출 | JSON 출력, 단일 호출 |
| `P2_model` | Page 6 모델 추천 LLM 호출 | JSON 출력, 단일 호출 |
| `P3_planner` | Planner 계획(순서·이유) LLM 호출 | JSON 출력, 단일 호출 |

> 위 3종 = **phase-1 MCP·파이프라인 호출**(전부 짧은 JSON). **phase-2 프롬프트군(EDA 추천·요약·자연어 코드생성
> 등)은 출력 특성이 달라**(코드는 decode 길어 num_predict 상한 자주 도달) **STEP 3 후 별도 protocol에서 캡처·고정**.

> **controlled 단위 = "단일 LLM 호출"**이다. Page 4 전체 파이프라인(LLM ~8회)이 아니라 위 3종 각각.
> (파이프라인 누적 시간은 passive·알파 관측용.)

### 2-2. 입력 고정 (재현성의 핵심) `[LOCKED 원칙 / OPEN 구현]`
> **문제 (코드 확인)** `[실측]`: 예시로 들었던 `press_forming.csv`는 **실재하지 않고**, 합성 CSV는
> `generate.py` 생성물이라 **gitignore됨**(repo에 없음). → 그대로면 새 수행자가 다른 입력으로 재현 불가
> = 브랜치의 무기(재현성) 붕괴.
- **데이터셋 고정 방식 `[OPEN: HO1 — 둘 중 택1]`**:
  - (i) **결정론 재생성**: `data/synthetic/.../generate.py`를 **고정 seed**로 돌려 동일 CSV 보장 + 그 호출
    커맨드·seed·산출 sha256을 protocol에 기록. (gitignore 유지, 재현은 명령으로)
  - (ii) **측정 입력만 커밋**: 측정에 쓴 CSV를 `monitoring/fixtures/`에 **명시 커밋**(gitignore 예외). 소량이면 권장.
- **실재 파일명 확정** `[OPEN: HO1]` — generate.py 산출 실제 경로·파일명으로 교체(press_forming은 예시일 뿐).
- **AggregatedContext 고정** — 위 입력에서 나온 컨텍스트를 단일 스냅샷으로 `monitoring/prompts/`에 함께 저장.
- 실데이터는 passive 검증 시 재확인(③ 더미 기준).

### 2-3. 캡처 절차 `[LOCKED 절차 / OPEN 산출]`
프롬프트 **텍스트는 LLM 호출부 코드에서 생성**되므로, byeonggab89가 **고정 커밋에서 실제 문자열을 캡처**한다:
1. **핀 커밋** = STEP 1B 완료 상태 `[OPEN: 커밋 해시 — byeonggab89 확정]`. 이 커밋에서 LLM 호출부가 고정.
2. P1/P2/P3 각각 실제 전송 payload(prompt + system)를 캡처 → `monitoring/prompts/{P1,P2,P3}.json`.
3. 각 파일 **sha256 기록**(본 문서 §11에 적어 고정). 측정 중 프롬프트 변경 시 무효.

---

## §3. 제어 변수 (block 3) `[LOCKED]`

> **전제 (코드 확인)** `[실측: backend/llm.py grep]`: 본진 백엔드는 `num_ctx`·`temperature`·`num_predict`·
> `keep_alive`를 **하나도 set 하지 않는다 → 전부 Ollama 런타임 기본값.** 따라서 아래 고정값은 **controlled(B)에서
> 프로파일러가 명시 set 하는 측정-통제 config**다. 이것이 **실제 운영값과 다름**에 유의(운영 분포는 passive(A)가
> 담당 — §10 baseline 문구 참조). 재현성·비교 공정성을 위해 통제값을 고정하되, 그 통제값이 운영 default가
> 아님을 정직하게 분리한다.

| 변수 | 값 | 비고 |
|---|---|---|
| `temperature` | **0** | greedy = 결정론적 출력 (§4-4 품질 측정과 연결) |
| `seed` | **42** | temp=0이라 영향 적으나 고정(재현성 보험) |
| `num_predict` | **512** | 출력 길이 상한 통일 → tok/s 비교 공정. **출력이 512 도달(truncate) 시 기록**(품질 신호 겸용, §4-4) |
| `top_p` / `top_k` | Ollama 기본 | temp=0이라 무영향, 고정 |
| `num_ctx` | **`[OPEN: HO1 확인]`** baseline=실제 적재값 / 실험=2048 | **backend가 num_ctx 미설정 → Ollama 기본값이 실제 baseline.** HO1에서 적재 n_ctx 확인 후 확정. 기본이 2048이면 baseline=2048 → "4096→2048 축소"(H1)는 무의미(H1 demote 이중 확정) |
| `keep_alive` | **cold=0 / warm=10m (둘 다 측정)** | **backend 미설정 → controlled에서 프로파일러가 명시 set.** keep_alive 레버 분리용 (§4-3) |
| `N` (셀당 반복) | **7** | latency 분산용. p50+min/max (p95 금지) |
| 워밍업 | **셀당 1회 콜드 분리** | 첫 호출(모델 적재 직후)은 별도 기록, 본 N=7에서 제외 |
| cooldown | **셀 간 ≥ 5s** `[OPEN: HO1 발열 측정 후 확정]` | 연속 측정 throttle 방지 |

**cold / warm 정의** `[LOCKED]`:
- **cold** = `keep_alive=0` → 호출마다 모델 재적재(load_duration 발생) + 프롬프트 캐시 미스. **정직한 최악치.**
- **warm** = `keep_alive=10m` → 워밍업 후 모델 상주(load_duration≈0) + 반복 시 프롬프트 캐시 가능. **운영 낙관치.**

---

## §4. KPI 정의 + 공식 (block 4) `[LOCKED]`

### 4-1. 시간 분해 (in-band, ns→ms 변환)
> **`total_duration ≈ load_duration + prompt_eval_duration(prefill) + eval_duration(decode)`** — 세 성분을
> 분리 기록한다(이 분해가 **레버별 귀속의 핵심**). 단 **항등식이 아니라 근사**다 — Ollama `total`엔
> 토큰화·큐잉·직렬화 등 잔차가 있을 수 있으므로 **`residual = total − (load + prefill + decode)`도 기록**하고,
> residual이 유의하게 크면(예: total의 >5%) 플래그한다.
> - keep_alive 레버 → `load_duration` (cold에서 발생, warm≈0)
> - 프롬프트 캐시 → `prompt_eval_duration` (반복 시 감소)
> - num_gpu / num_ctx / 모델 → `eval_duration`(decode) + size_vram
> - 모델 비교(e2b vs e4b) → decode + size_vram + 품질

### 4-2. 처리량
- **decode tok/s** = `eval_count / (eval_duration / 1e9)`
- **prefill tok/s** = `prompt_eval_count / (prompt_eval_duration / 1e9)`

### 4-3. 자원 KPI (out-of-band 샘플러 + /api/ps)
| KPI | 소스 | 단위 |
|---|---|---|
| `size_vram` (내 모델 GPU 점유) | `/api/ps` | MiB (KPI 기준) |
| peak process VRAM (추론 중 최대) | pynvml `nvmlDeviceGetComputeRunningProcesses` | MiB (헤드룸 판정용) |
| GPU util (호출 윈도우 mean/peak) | pynvml | % |
| GPU 온도 max / SM clock min | pynvml | °C / MHz (throttle 감시) |
| ollama CPU% / RSS | psutil | % / MiB (offload 부하) |
| swap_used | psutil | MiB (8GB swap 경계 감시) |

### 4-4. 품질 KPI (3종)
| KPI | 측정 | 정답셋 |
|---|---|---|
| JSON 유효율 | N회 중 valid JSON 비율 | 불필요(결정론) |
| 추천 정확도 | 고정 입력 → 허용 정답 집합에 드는 비율 | **필요** `[OPEN: HO3 정의]` |
| rationale facts 인용율 | rationale가 인용한 컬럼·통계가 입력 컨텍스트에 실재하는가 | 체커(불필요 손라벨) |

> **temp=0 결정론 주의** `[LOCKED 해석]`: temp=0이라 (모델, 프롬프트) 동일 시 출력이 **사실상 결정론적**.
> → **품질 KPI는 셀당 1회로 충분**(N=7은 latency 분산용, 품질 분산용 아님). 단 CPU offload 부동소수
> 비결정성으로 드물게 출력이 흔들릴 수 있으므로, **N회 중 출력 불일치 발생 여부도 기록**.

### 4-5. 집계 `[LOCKED]`
셀당 **p50(중앙값) + min + max + CV(변동계수=std/mean)**. **N=7이라 p95 금지**(불안정). CV는 §9-1 판정 입력.

---

## §5. 측정 매트릭스 (실행 단위)

> controlled 단위 = 단일 LLM 호출. 아래 배터리는 **고정 코드 커밋(§2-3 핀)에서** 실행.

### 5-1. baseline 배터리 (무튜닝, 현 설정)
> **num_ctx = `[OPEN: HO1]` 실제 적재 기본값**(backend 미설정 — §3 전제). 4096 가정 금지, HO1 확인 후 확정.
> **keep_alive 고정 원칙 `[LOCKED]`**: baseline·num_gpu·num_ctx 셀은 모두 **`keep_alive=warm(10m)` 고정**으로
> 잰다(load_duration 노이즈 제거 → decode/size_vram 레버 효과만 분리). `warm`은 Ollama 기본(5m)이 아닌
> **선택한 통제값**이다(§10). keep_alive **자체의 N%**는 §5-2에서 cold vs warm으로 별도 측정한다.

| 모델 | 프롬프트 | num_ctx | keep_alive | N | 비고 |
|---|---|---|---|---|---|
| e2b, e4b | P1·P2·P3 | 적재 기본값 `[OPEN]` | warm(10m) | 7 (+워밍업1 cold) | 헤드라인 baseline |
| 26b | P1만 | 적재 기본값 `[OPEN]` | warm | **3** | 목표 모델 시험 → 스래싱 시 §9-4 강등(negative-result). 양자화 진입 시험은 §5-3 |

### 5-2. 최적화 배터리 (e4b 주, e2b 보조)
> **헤드라인 N% 정의 `[LOCKED]`**: **1순위 = per-lever 보고**(레버별 baseline 대비 ΔN% — 귀속이 깨끗하고
> 어떤 레버가 얼마인지 분해됨). **단일 헤드라인 숫자가 필요하면** = baseline → **모든 유효 레버 동시 적용
> 조합 셀**(아래 `all-levers`)의 ΔN%. per-lever 합과 조합이 다를 수 있으므로(상호작용) **조합은 합산이 아니라
> 별도 측정**한다. 보고서엔 per-lever 표 + all-levers 단일 숫자를 **함께** 싣는다(분해 + 헤드라인 둘 다).
>
> **num_gpu 스윕 = 2패스 `[LOCKED]`**: ① HO1 진단 패스(P1, 빠르게 단계별 size_vram·tok/s·OOM만 — 회수
> 가능 num_gpu 구간 탐색) → ② 본측정 패스(진단이 고른 **최적 num_gpu 1값**으로 P1·P2·P3 × N=7, baseline과
> 동일 포맷). 아래 표의 스윕 행은 ①, all-levers·보고 N%는 ②의 고정값을 쓴다.

| 실험 | 레버 | 셀 | N | 진단 의존 |
|---|---|---|---|---|
| keep_alive | `keep_alive` {0, 10m} | e4b × P1·P2·P3 | 7 | 독립, 1순위 |
| num_gpu 스윕 (①진단) | `num_gpu` {현재→상향 단계} | e4b × P1 | 5 | **첫 진단**(Part 6-1). 각 단계서 (size_vram, decode tok/s, OOM 여부) 기록. 단계값 `[OPEN: HO1]` |
| num_gpu 본측정 (②) | `num_gpu` = ①이 고른 최적 1값 | e4b × P1·P2·P3 | 7 | ① 결과 종속. (A)회수 불가로 판정 시 skip |
| num_ctx | `num_ctx` {적재 기본값 `[OPEN]`, 2048} | e4b × P1·P2·P3 | 7 | 보조(H1 demote — Part 6-2). **기본이 이미 ≤2048이면 이 실험 무의미 → skip**(H1 demote 이중 확정) |
| **all-levers (헤드라인)** | warm + 최적 num_gpu(+유효 시 num_ctx) 동시 | e4b × P1·P2·P3 | 7 | 단일 헤드라인 N%. 유효 레버만 합침 |

### 5-3. 26b 양자화 진입 시험 (목표 모델 — 8GB 실용권) `[OPEN: Q3/Q2 pull 시]`
> blueprint §5-0·6-3의 핵심 질문: **양자화(Q3/Q2)로 26b를 8GB 실용권에 넣을 수 있나** — MoE 스래싱을
> 못 잡는 파라미터 레버와 달리 **적재율 자체를 줄이는 유일한 구조적 레버**. §9-4 강등(스래싱 시 N=3 중단)과
> **별개로**, 양자화 변형은 시도 가치가 있다(시간 허용 시).

| 실험 | 레버 | 셀 | N | 비고 |
|---|---|---|---|---|
| 26b 양자화 진입 | 양자화 {Q4 → Q3/Q2 pull} | 26b × P1 | 3 | `[OPEN: Q3/Q2 pull]`. **적재율·size_vram·CPU/GPU 분배·단일호출 시간 재측정 → 8GB 실용권 진입 판정.** 여전히 T=60s 초과면 "양자화로도 불가" 확정(§9-4 강등) |

> 판정: Q3/Q2에서 단일 호출이 T 이내로 떨어지고 품질이 버티면 → "8GB+양자화로 26b 가능"(강한 긍정).
> 안 되면 → "양자화로도 8GB 불가, 24GB+ 필요"(정직한 부정). 둘 다 §5-0 핵심 질문의 valuable한 답.

### 5-4. e2b 품질 스모크 (HO1 go/no-go)
e2b pull 직후 P1·P2·P3 × N=2, **품질만**(JSON 유효·추천 합리성). 미통과 시 "8GB→e2b 권장" 서사 보류.

### 5-5. 관찰자효과 A/B 캘리브레이션 `[LOCKED]`
e4b × P1·P2·P3 × N=7을 **샘플러 on vs off**로 측정. **반드시 같은 단독창 안 back-to-back**(다른 시간 = 노이즈 교란). 판정 = §9-2.

### 5-6. 실행량·소요 추정 `[추론]`
총 ~200회 내외(baseline + keep_alive·num_gpu(①진단+②본측정)·num_ctx·all-levers 조합, 대부분 e2b ~3s /
e4b ~8s 단일 호출 → 컴퓨트 ~20–30분) + 26b ~3×120s(~6분) + cooldown.
**단독창 1–2 세션이면 충분.** 26b를 풀 배터리로 돌리면 수 시간 → §9-4로 차단.
**26b 양자화 진입 시험(§5-3)은 Q3/Q2 pull 시 선택** — pull 시간 + 3회 재측정 추가(별도 단독창 권장).

---

## §6. 측정 소스·도구 (block 6) `[LOCKED]`

| 항목 | 고정값 |
|---|---|
| in-band (1순위, 노이즈 0) | `/api/generate` 메타: total/load/prompt_eval/eval (count·duration) |
| out-of-band (자원) | **pynvml in-process**, 250ms 간격, **`taskset` 유휴코어 핀**. subprocess `nvidia-smi` 매틱 spawn **금지** |
| VRAM 귀속 | `/api/ps` `size_vram`(KPI) vs nvidia-smi 전체(경합 맥락) |
| **controlled 호출 경로** | **프로파일러가 `/api/generate`를 직접 호출** — 호스트 단일 프로세스 시계, **훅·도커 무관** |
| **passive 호출 경로** | `backend/llm.py` PROFILE 훅(`LLM_PROFILE` env-gate, 기본 off), byeonggab89 협조 |
| 프로세스 간 시계 | **`time.clock_gettime_ns(time.CLOCK_MONOTONIC)` 통일.** `perf_counter` 금지(프로세스 간 비교 시 조용히 어긋남 — C3) |
| 권한 | **userspace only**(blueprint Part 1-4): `ollama` CLI·`docker exec`·`journalctl` 불가 → HTTP API + nvidia-smi/pynvml/psutil. e2b pull은 admin/byeonggab89 협조 |

---

## §7. 단독창 + 측정 순도 (block 7) `[LOCKED]`

- 모델 적재·controlled 측정은 **조율된 단독창**에서(상황별 협의).
- **단독창 강도(모델별 분리)**:
  - e4b / e2b (GPU 위주) → byeonggab89 **LLM 작업 정지**.
  - 26b (CPU offload) → **박스 quiesce**(byeonggab89의 비-LLM 부하도 정지) `[OPEN: 팀원 협의]`.
- **측정 전 점검 프로토콜**: `/api/ps`로 타 모델 미적재 확인 + `nvidia-smi`로 타 프로세스 VRAM 0 확인.
- **KV 캐시 검증**: 동일 프롬프트 2연속 호출 → `prompt_eval_count` 변화 기록(캐시 활성 특성화, §9-3).

---

## §8. 출력 스키마 (block 8) `[LOCKED]`

### 8-1. raw 로그 (jsonl, `monitoring/logs/`)
| 파일 | 내용 |
|---|---|
| `llm_inband.jsonl` | call_id, origin_ts_ns(CLOCK_MONOTONIC), model, total/load/prompt_eval/eval duration·count |
| `llm_resource.jsonl` | ts_ns(CLOCK_MONOTONIC), gpu_util, vram_used_total, gpu_temp, sm_clock, per-proc VRAM, cpu%, rss, swap |
| `llm_ps.jsonl` | ts_ns, model, size_vram, size_total |

### 8-2. 집계 (격리, 본진 PG 안 씀)
> **시계열 샘플 = parquet** (다량) / **호출별 요약·런 메타 = DuckDB** (소량, SQL·jupyter). SQLite 대안.
> DuckDB가 parquet을 직접 쿼리. `monitoring/results/runs.duckdb` + `monitoring/results/samples.parquet`.

`calls` 테이블(호출별 요약) 컬럼 `[LOCKED]`:
```
run_id, ts, model, prompt_id, cell(baseline|keep_alive|num_gpu|num_ctx|all_levers|smoke),
num_ctx, keep_alive, num_gpu, cache_state(cold|warm),
total_ms, load_ms, prefill_ms, decode_ms, residual_ms, decode_toks, prefill_toks,
size_vram_mib, peak_proc_vram_mib, gpu_util_mean, gpu_util_peak,
cpu_pct, rss_mib, swap_mib, gpu_temp_max, sm_clock_min,
num_predict_hit(bool), json_valid(bool), recommend_correct(nullable), facts_cited(bool),
sampler_on(bool), git_commit, notes
```
`runs_meta` 테이블: run_id, 세션 시각, 단독창 여부, 관찰자 A/B 짝, git_commit, 측정자.

### 8-3. gitignore `[LOCKED]`
`logs/`·`results/`·`*.jsonl`·`*.parquet`·`*.db`·`*.duckdb`·`*.sqlite`.

---

## §9. 판정·합격 규칙 (block 9) `[LOCKED — 사전 결정]`

### 9-1. 분산 (CV)
- 셀 CV > 15% → **단독창 재측정 1회.**
- 재측정도 > 15% → **high-variance 플래그** 달고 p50+min/max로 분포 명시하여 그대로 보고. **무한 재측정 금지**(공유 박스라 한없이 못 돌림).

### 9-2. 관찰자효과
- 샘플러 on vs off의 in-band median latency 차이 **> 5%**(또는 CV 밴드 초과) → **in-band를 1순위 KPI**, out-of-band는 자원 맥락용으로 강등.
- 차이 ≤ 5% → 둘 다 1급으로 사용.

### 9-3. KV 캐시
- 동일 프롬프트 2연속 시 `prompt_eval_count`가 0/감소 → 캐시 활성. 안 줄면 캐시 off(버그 아님). cold/warm 해석에 반영.

### 9-4. 26b 조건부 강등 — **임계시간 T 확정** `[LOCKED]`
> **T = 60s.** 근거: e4b 단일 호출은 `/analyze` 5.0s·`/model` 9.8s로 < 10s. 26b `/analyze`는 120s.
> **건강한 gemma4 단일 호출이 60s를 넘는 경우는 8GB CPU-bound 스래싱뿐** → T=60s가 e4b/e2b 오탐 없이 26b만 잡는다.
>
> **규칙**: 26b의 단일 controlled 호출이 **T=60s 초과** 또는 **써멀 스로틀(SM clock 다운) 감지** 시 → 즉시
> 중단, **negative-result로 확정**. 26b는 **P1 단일 프롬프트 N=3까지만** 측정(타임아웃·CPU/GPU 분배·스래싱
> 문서화), **전체 배터리·최적화 실험 미적용**.

### 9-5. N% 귀속 `[LOCKED]`
- 분모 = **controlled 최적화 전 동일 조건**(동일 모델·HW·프롬프트·num_ctx — **per-lever 기준**; all-levers는 다수 레버 동시 변경분을 동일 baseline에 대해 잼).
- ❌ 모델 비교("e4b가 26b보다") = N% 아님. ✅ 동일 모델 최적화 전후만.
- **per-lever ΔN%(분해) + all-levers ΔN%(헤드라인)를 함께 보고**(§5-2). 헤드라인은 per-lever 합이 아니라 조합 셀 실측.
- **측정 전 N% 약속 금지.** baseline 확정(§10) 후에만 비율 산출.

---

## §10. baseline (block 5)

- **정의** = blueprint Part 5-1: "각 모델이 측정 환경 구축 후, protocol 통제 조건에서 무튜닝(레버 미적용)으로 도는 controlled 수치".
- **"무튜닝"의 정확한 의미 `[LOCKED 해석]`**: baseline은 **측정-통제 config(재현용 temp=0·num_predict=512 등 §3
  통제값)에서 최적화 레버 미적용** 상태다. **literal 운영 default가 아니다** — 운영은 backend가 옵션을 안 set해
  Ollama 기본(temp~0.8 등)으로 돈다(§3 전제). 즉 N%는 "통제 config 내 레버 전후"를 잰다.
  **운영 그대로의 분포는 passive(A)가 별도 측정**해 함께 보고한다(둘을 섞지 않음 = 회의론 방어·정직성 핵심).
- **역할** = Part 5-2: **26b = 목표 모델(주인공, 8GB 가용성 판정+하네스 시험) / e4b = 균형 현실선·최적화 N% 주력 / e2b = 8GB 하한(품질 게이트)**.
- **근거 1줄**: "8GB VRAM 초과로 Ollama가 자동 CPU offload — 현 하드웨어 실제 조건."
- **확정 절차 `[LOCKED]`**: baseline은 **HO3에서 (1) 실행파일·코드 정리 완료 후 (2) protocol 조건 controlled 측정
  (3) CV로 재현성 확인된 수치만 인정.** 아래 알파 값은 **baseline이 아니라 개발 중 참고치**(자릿수·방향 sanity +
  진단 가설 근거). blueprint 부록 B 주의와 동일.
- **개발 중 참고치 (baseline 아님)** `[byeonggab89, 알파]`:

| 작업 | e4b | 26b |
|---|---|---|
| /analyze (LLM 1회) | 5.0s | 120s (타임아웃) |
| /model recommend | 9.8s | — |
| Page 4 파이프라인 (LLM ~8회) | 46.6s | 274.2s |
| 적재 (`/api/ps`/ps) | ~9.87GB (GPU 3.20 / CPU 6.67, 32%GPU) | ~20GB (63%CPU/37%GPU) |

- **확정값** = `[측정 후 v0_2]` (controlled 5-1 배터리 결과).

---

## §11. OPEN 항목 (측정 전 채울 것)

| # | 항목 | 주체 | 시점 |
|---|---|---|---|
| 1 | 프롬프트 텍스트 P1/P2/P3 + 각 sha256 | byeonggab89 | §2-3, HO1 전 |
| 2 | 핀 커밋 해시 (STEP 1B 완료) | byeonggab89 | §2-3 |
| 3 | e2b pull (공유 데몬 모델스토어 쓰기 → admin/byeonggab89 조율. CLI 불가[실측]/HTTP `/api/pull`은 가능성 `[추론: HO1 확인]`. pull 1회로 공유) | admin/byeonggab89 조율 | HO1 |
| 4 | num_gpu 스윕 단계값 | myeongsun97 | HO1 (적재 보고 후) |
| 5 | cooldown 초 | myeongsun97 | HO1 (발열 측정 후) |
| 6 | 26b 박스 quiesce 강도 | 팀원 협의 | HO1 전 |
| 7 | 추천 정확도 정답셋 | byeonggab89 + myeongsun97 | HO3 전 |
| 8 | Q3/Q2 추가 pull 여부 (→ 26b 양자화 진입 시험 §5-3 활성화) | myeongsun97 | 진단 후 |
| **9 ★** | **실제 적재 num_ctx 기본값** (backend 미설정 → §3·§5 baseline 전제) | byeonggab89(/api/ps·적재로그) | **HO1 — 측정 전 선결** |
| **10 ★** | **고정 입력 데이터셋 실재화** (재생성 seed+sha256 또는 fixtures 커밋, §2-2) | myeongsun97 | **HO1 — 측정 전 선결** |

> OPEN이 채워지면 본 문서 해당 칸 갱신 + `v0_2` 범프. LOCKED 값은 §0-2 무효화 규칙 적용.

---

## §12. 서명

> 아래 서명 = "본 protocol의 `[LOCKED]` 고정값에 합의했고, 이후 측정·N% 주장은 이 계약 기준임"의 확인.
> 서명 후 측정 시작. 서명 전 측정 금지.

| 역할 | 이름 | 책임 | 서명/날짜 |
|---|---|---|---|
| 설계자=실무자 | myeongsun97 | 프로파일러 제작·측정·분석·문서 | ________ |
| 본체 코드 | byeonggab89 | 프롬프트·핀 커밋 캡처 / PROFILE 훅 / 단독창·quiesce 협의 / 정답셋 공동정의 | ________ |

**핀 커밋(측정 기준)**: `[OPEN]` ____ / **서명 시 protocol 버전**: v0_1

---

**작성**: 2026-06-02 v0_1 (Claude Opus 4.8 / 설계자=실무자 myeongsun97).
**갱신 정책**: `[LOCKED]` 변경 → 무효화·재측정·버전 범프(§0-2). `[OPEN]` 채움 → 해당 칸 갱신 + 범프.
**다음 단계**: §11 OPEN 채우기(특히 1·2·6) → §12 서명 → 핸드오프 4분할 상세화 → 단독창 조율 → 1_HO1 진단.
