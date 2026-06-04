# LLM 리소스 프로파일링 — 핸드오프 4분할 · phase-1 (MCP) (v0_1)

> **범위**: phase-1(앞단 MCP·Agent 파이프라인 LLM, 프롬프트 P1·P2·P3) 측정의 **실행 핸드오프**. phase-2(EDA·
> 모델링·코드생성)는 phase-1 완료 후 STEP 3에서 별도 핸드오프(`1_HO*_phase2_*`).
>
> **상위 문서**: 설계=`0_resource_blueprint_phase1_v0_1.md`(해당 Part 참조) / 고정값=`0_resource_protocol_phase1_v0_1.md`(해당 § 참조)
> / 작업 규칙=`BG_TEAMMATE_claude_memory.md` / 방법론 원본=`BG_TROUBLESHOOT_llm_resource_optimization.md`.
> 충돌 시 **blueprint(설계) > protocol(고정값) > 본 문서(실행)** 순. 본 문서는 그 둘을 실행으로 옮길 뿐, 값을 새로 만들지 않는다.
>
> **Snapshot**: 2026-06-02 v0_1 (측정 코드 미작성 / 측정 미시작 / protocol §12 서명 전).
>
> **표기**: `[LOCKED]`=protocol 고정값 / `[OPEN]`=실행 중 확정 / `[GATE]`=검증 통과 못 하면 다음 단계 진입 금지.
> 호스트명=`LINUX-server`. 강조는 굵게/인용만.
>
> **이 문서를 묶은 이유**: HO1~4가 선결·인계로 촘촘히 엮여 한 흐름이라 한 문서로 둔다. 실행 단계에서
> 파일로 쪼갤 때 `1_HO1_phase1_v0_1.md` … `1_HO4_phase1_v0_1.md`로 분리.

---

## §A. 전체 흐름 + 의존성 + 검증 하네스 원칙

### A-1. 의존성 그래프 (순서 = 정석: 진단 → 도구 → 측정 → 산출)
```
HO1 진단 ──(num_ctx 적재값 / num_gpu 최적값 / e2b go-no-go / cooldown / 확정 프롬프트·데이터셋)──┐
   │                                                                                          │
   ▼                                                                                          ▼
HO2 계측 도구 ──(검증 통과한 sampler·poller·battery·join·DuckDB)──▶ HO3 측정 캠페인 ──(CV검증 baseline·전후 데이터)──▶ HO4 산출
```
- **HO1은 무거운 도구 없이 curl 기반 1회성 프로브로 진단**한다(size_vram=`/api/ps`, tok/s=in-band, OOM=에러).
  프로덕션 샘플러·조인은 HO2에서 만든다 → 닭-달걀 없음.
- **HO2 passive 훅은 controlled를 안 막는다**(controlled=프로파일러 직접 호출, blueprint Part 4-3). 따라서 HO3의
  N% 측정은 sampler·poller·battery·join만 있으면 진행 가능. passive 훅(byeonggab89 협조)은 늦어도 됨.

### A-2. 검증 하네스 원칙 (★ 본 핸드오프의 척추)
> 측정 도구·데이터는 **자기검증을 통과하기 전엔 신뢰하지 않는다.** 본진 하네스 4요소를 측정에 이식한다:

| 하네스 요소 | 측정에서의 의미 | 어디서 |
|---|---|---|
| **스키마 검증** | 출력 `calls` 테이블이 protocol §8 LOCKED 컬럼과 정확히 일치 | HO2 [GATE] |
| **자기검증(self-test)** | 각 도구를 알려진 입력으로 검증(샘플러 캡처·시계 조인·in-band 파싱) | HO2 [GATE] |
| **가드레일(판정 규칙)** | CV>15%·관찰자효과·26b 강등·N% 귀속 (protocol §9) | HO3·HO4 [GATE] |
| **Lineage** | 모든 측정 row가 `git_commit`·프롬프트 sha256·조건·단독창 여부로 추적 | 전 HO |

> **게이트 규칙**: 각 HO 끝의 `[GATE]`를 통과해야 다음 HO 진입. 통과 못 한 데이터로 다음 단계 진행 금지.

### A-3. OPEN 항목 → HO 배정 (protocol §11)
| OPEN | 항목 | HO |
|---|---|---|
| 1·2 | 프롬프트 P1/P2/P3 텍스트·sha256 + 핀 커밋(STEP 1B 완료) | HO1 (byeonggab89) |
| 9·10 | num_ctx 적재 기본값 / 데이터셋 실재화 | **HO1 — 측정 전 선결** |
| 3 | e2b pull (공유 데몬 — admin/byeonggab89 조율, pull 경로 HO1 확인) + 적재확인은 단독창 | HO1 |
| 6 | 26b 박스 quiesce 강도 | HO1 전 (팀원 협의) |
| 4·5 | num_gpu 스윕 단계값 / cooldown 초 | HO1 (진단 중 확정) |
| 8 | Q3/Q2 pull 여부 (→ §5-3 활성화) | HO1 진단 후 |
| 7 | 추천 정확도 정답셋 | HO3 전 |

---

## §B. HO1 — 진단 (Diagnosis)

> 목적: **측정 전 선결값 확정 + 진단으로 캠페인 파라미터 결정.** 무거운 도구 없이 curl 프로브로.

### B-1. 선결조건 (entry)
- protocol·blueprint phase-1 확정·커밋됨.
- userspace 권한 확인(`curl localhost:11434`·`nvidia-smi` 동작 — 기검증).
- 26b quiesce 강도 협의(OPEN6, 팀원).

### B-2. 입력
protocol §1(모델)·§2(프롬프트·데이터셋)·§3(제어값)·§9-4(T=60s) / blueprint Part 6-1(num_gpu)·6-5(e2b 스모크).

### B-3. TODO (순서)
1. **데이터셋 실재화 (OPEN10)** — `generate.py` 고정 seed 재생성 **또는** `monitoring/fixtures/` 커밋. 실제 파일명 확정 + sha256 기록(protocol §2-2). *재현 안 되면 이후 전부 무의미 → 1번.*
2. **프롬프트 캡처 (OPEN1·2)** — byeonggab89가 핀 커밋(STEP 1B 완료)에서 P1/P2/P3 payload 캡처 → `monitoring/prompts/{P1,P2,P3}.json` + sha256. AggregatedContext 동일 스냅샷 포함.
3. **환경 확정** — `pynvml`/`psutil` userspace import 검증 / `nproc`·swap·KV 동작 확인 / **num_ctx 적재 기본값 확인 (OPEN9)**: `/api/ps` + (가능 시 byeonggab89 적재로그). *4096 가정 금지 — 실제값 확정.*
4. **e2b pull (OPEN3)** — **공유 Ollama 데몬(`localhost:11434`) 모델스토어에 쓰는 작업이라 admin/byeonggab89 조율**로 pull. pull 경로는 HO1에서 확인: CLI는 불가(바이너리 없음 [실측]), **HTTP `POST /api/pull`은 데몬이 대신 수행하므로 read 권한자도 트리거 가능할 수 있음 `[추론: HO1 확인]`** — 다만 공유 자원 쓰기라 어느 경로든 조율. pull 후 `/api/tags`에 `gemma4:e2b` 뜨는지 확인 → 단독창에서 `/api/ps`로 GPU 100% 적재 확인. *모델은 공유 데몬이 서빙하므로 내 홈 별도 적재 불필요 — pull 1회로 공유.*
5. **[서명 게이트] protocol §12** — OPEN 1·2·9·10·6 채워지면 protocol 완성 → myeongsun97 + byeonggab89 서명. **서명 후 진단 측정 시작**(§0-3).
6. **num_gpu 스윕 ①진단 (OPEN4)** — e4b × P1, `num_gpu` 현재→상향 단계. 각 단계 `(size_vram via /api/ps, decode tok/s via in-band, OOM)` 기록 → **(A) 회수 가능 vs (B) 구조적 CPU 핀 판정** + 최적 num_gpu 1값 선정(blueprint Part 6-1).
7. **e2b 품질 스모크 (go/no-go)** — e2b × P1·P2·P3 × 1~2회, JSON 파싱·추천 합리성만. **미통과 시 "8GB→e2b 권장" 서사 보류**(blueprint Part 6-5).
8. **cooldown 발열 측정 (OPEN5)** — 연속 호출 시 GPU 온도·SM clock 관찰 → 셀 간 cooldown 초 확정.
9. **Q3/Q2 결정 (OPEN8)** — 진단 결과 보고 26b 양자화 진입 시험(§5-3) 활성화 여부 결정.

### B-4. [GATE] 검증 (통과해야 HO2/HO3로)
- 데이터셋 sha256 **재현 확인**(같은 seed/파일 → 같은 해시).
- 프롬프트 3종 sha256 고정·기록됨.
- num_ctx 적재 기본값 **수치로 확정**(가정 아님).
- in-band tok/s 공식 sanity: `eval_count/(eval_duration/1e9)` 합리적 범위.
- `pynvml` import·per-proc VRAM 읽기 성공(HO2 샘플러 가능성 확인).
- 서명 완료.

### B-5. 산출 → 인계
- **HO2로**: 측정 조건(확정 num_ctx, num_gpu 최적값 or (A)/(B) 판정, cooldown), 확정 프롬프트·데이터셋 경로·sha256.
- **HO3로**: e2b go-no-go 결과, 26b 양자화 진입 시험(§5-3) 활성 여부, num_gpu ②본측정용 최적값.

---

## §C. HO2 — 계측 도구 (Instrumentation)

> 목적: HO3 캠페인이 쓸 **검증된 측정 하네스** 구축. 전부 `monitoring/`, userspace(HTTP+pynvml/psutil)만.

### C-1. 선결조건
HO1 [GATE] 통과(조건값·sha256 확정). pynvml/psutil 가용 확인됨.

### C-2. 입력
protocol §6(측정 소스)·§8(출력 스키마)·§3(제어값) / blueprint Part 4(측정 설계)·4-4(CLOCK_MONOTONIC).

### C-3. TODO (순서)
1. **`llm_resource_sampler.py`** — pynvml **in-process** 250ms, `taskset` 유휴코어 핀(26b offload와 경합 금지), 시각=`time.clock_gettime_ns(CLOCK_MONOTONIC)`. 기록: gpu_util·vram_used·gpu_temp·sm_clock·per-proc VRAM·cpu%·rss·swap → `monitoring/logs/llm_resource.jsonl`. (subprocess `nvidia-smi` 매틱 spawn 금지.)
2. **`ps_poller.py`** — `/api/ps` 폴링 → `size_vram`·`size_total`(+ts) → `llm_ps.jsonl`.
3. **`bench_battery.py`** — controlled 호출기: **프로파일러가 `/api/generate` 직접 호출**(고정 프롬프트, 제어값 §3, `keep_alive` 명시 set, `num_gpu`/`num_ctx` 셀별 주입). in-band 파싱(total/load/prefill/eval count·duration), `origin_ts`=CLOCK_MONOTONIC → `llm_inband.jsonl`. **`cell`·model·prompt·num_ctx·keep_alive·num_gpu·cache_state 태깅**(§8 스키마).
4. **(passive) `backend/llm.py` PROFILE 훅** — `LLM_PROFILE` env-gate(기본 off → 본진 무영향), `call_id`+`origin_ts`(CLOCK_MONOTONIC), 자체 jsonl(본진 `agent_logs` 불간섭). **byeonggab89 사인오프 선결**. passive 전용이라 controlled 안 막음 → 늦어도 됨.
5. **`analyze_logs.py` (조인·집계)** — 3 jsonl 시각 조인 → `monitoring/results/runs.duckdb`(`calls`·`runs_meta`) + `samples.parquet`. `residual_ms = total − (load+prefill+decode)` 계산.

### C-4. [GATE] 검증 하네스 (★ 전부 통과해야 HO3)
- **자기검증 — 샘플러**: 알려진 부하(의도적 VRAM 점유) 시 샘플러가 변화를 잡나 / 250ms 간격 실제 유지(드리프트 점검).
- **자기검증 — 시계 조인**: controlled는 단일 프로세스라 자명. **passive는 백엔드(컨테이너) ts와 호스트 샘플러 ts의 CLOCK_MONOTONIC origin 일치 검증**(byeonggab89 — time namespace 미사용 확인, blueprint Part 4-4).
- **자기검증 — in-band 파싱**: `total ≈ load+prefill+decode+residual`, **residual > total의 5%면 플래그**(§4-1). tok/s 공식 재확인.
- **스키마 검증**: `calls` 테이블 컬럼이 protocol §8 LOCKED 목록과 **정확히 일치**(누락·추가 0).
- **관찰자효과 sanity (가벼운 도구검증)**: 샘플러 on vs off로 한 셀(e4b×P1) latency 차이가 잡히는지만 확인 — "측정 메커니즘이 동작하나" 점검. **풀 A/B 배터리·§9-2 판정은 HO3(D-3 5·D-4)**. 여기선 도구가 차이를 포착하는지만.
- **Lineage**: 모든 row에 `git_commit`·프롬프트 sha256·조건 자동 기록되나.
- **gitignore**: `logs/`·`results/`·`*.jsonl`·`*.parquet`·`*.db`·`*.duckdb`·`*.sqlite`.

### C-5. 산출 → 인계
검증 통과한 도구 4종 + 조인 파이프라인 → HO3. (passive 훅은 byeonggab89 사인오프 시 활성, 미완이어도 controlled 진행.)

---

## §D. HO3 — 측정 캠페인 (Campaign)

> 목적: protocol §5 매트릭스 실행 → **재현성 검증된** controlled baseline + 최적화 전후 + 품질 데이터.

### D-1. 선결조건
HO2 [GATE] 통과(도구 검증). HO1 산출(조건값·go-no-go). **정답셋 정의(OPEN7)**. 단독창 조율(§7).

### D-2. 입력
protocol §5(매트릭스)·§3(제어값)·§9(판정)·§4-4(품질 KPI) / blueprint Part 5(서사·역할)·6(가설).

### D-3. TODO (순서)
1. **정답셋 정의 (OPEN7)** — byeonggab89+myeongsun97. 추천 정확도용 **고정 입력→허용 정답 집합** 3~5케이스(blueprint Part 6-5).
2. **단독창 확보** — e4b/e2b: byeonggab89 LLM 정지 / **26b: 박스 quiesce**(비-LLM 부하도 정지, §7).
3. **[순도 검증]** 측정 전 `/api/ps` 타 모델 미적재 + `nvidia-smi` 타 프로세스 VRAM 0 확인.
4. **baseline 배터리 (§5-1)** — e2b·e4b × P1·P2·P3 × N=7(cold1+warm6), num_ctx=적재 기본값, keep_alive=warm. **26b: P1 × N=3**(목표 모델 시험, §9-4 강등 감시).
5. **관찰자효과 A/B 풀 배터리 (§5-5)** — e4b × P1·P2·P3 × N=7 × {sampler on/off}, 같은 단독창 back-to-back → §9-2 판정(HO2 sanity와 별개, 여기가 본 측정·판정).
6. **최적화 배터리 (§5-2)** — keep_alive{0,10m} / num_gpu ②본측정(HO1 최적값, P1·P2·P3) / num_ctx{적재값,2048}(기본 ≤2048이면 skip) / **all-levers**(헤드라인 N% 조합 셀).
7. **26b 양자화 진입 시험 (§5-3)** — Q3/Q2 pull 시. 적재율·size_vram·단일호출 시간 재측정 → 8GB 실용권 판정.
8. **품질 KPI** — JSON 유효율 / 추천 정확도(정답셋) / facts 인용율. *temp=0이라 품질은 셀당 1회 + 불일치 여부 기록(§4-4).*

### D-4. [GATE] 검증 하네스 (가드레일)
- **재현성 CV 게이트 (★ baseline 자격)**: 각 셀 **CV ≤ 15%**. >15% → 재측정 1회 → 여전히 >15% → high-variance 플래그 + p50/min/max 보고, **무한 재측정 금지**(§9-1). **CV 게이트 통과한 controlled 수치만 baseline 인정** — 이게 부록 B 참고치와의 결정적 차이.
- **26b 강등 트리거 (§9-4)**: 단일 호출 **> T=60s** 또는 써멀 스로틀 → 즉시 중단, negative-result 확정(N=3, 타임아웃·분배 문서화). 풀 배터리 강행 금지.
- **관찰자효과 판정 (§9-2)**: on/off median 차이 **> 5%** → in-band 1순위, out-of-band 맥락용.
- **KV 캐시 검증 (§9-3)**: 동일 프롬프트 2연속 → `prompt_eval_count` 변화 기록.
- **Lineage**: 모든 측정 row에 git_commit·프롬프트 sha256·단독창 여부 태깅.

### D-5. 산출 → 인계
재현성 확인 baseline + 최적화 전후 + 품질 KPI + 26b 판정 데이터(DuckDB/parquet) → HO4.

---

## §E. HO4 — 최적화·산출 (Analysis & Output)

> 목적: 데이터 → 결론·표·서사 + 본체 동기화. **정직성·재현성 게이트로 N% 방어.**

### E-1. 선결조건
HO3 [GATE] 통과(CV 검증 데이터).

### E-2. 입력
HO3 데이터 / blueprint Part 5(서사·N% 규칙)·6(가설)·7(산출)·10-3(동기화).

### E-3. TODO (순서)
1. **진단 우선 가설 검증** — H1(num_ctx demote 실측 확인) / num_gpu (A)/(B) 확정 / keep_alive 효과(=load_duration 제거분) / **26b 스래싱·양자화 판정**(8GB 실용권 진입 여부 = 핵심 결론).
2. **per-lever ΔN% 표(분해)** + **all-levers ΔN%(헤드라인)** — §9-5. *헤드라인은 per-lever 합이 아니라 조합 셀 실측.*
3. **트레이드오프 표** — 3모델 × latency/VRAM 적재율/tok/s/JSON유효율/추천정확도(Part 7-1).
4. **전후 비교표** — 동일 모델 baseline vs 최적화.
5. **서사 문서** — 26b(목표) → 8GB 가용성 판정 → 파라미터·하네스 결과 → 현실 대안(e4b·e2b 품질 게이트) → 26b 가려면 필요 하드웨어(24GB+).
6. **권장 매트릭스** — 목표 vs 현실(Part 5-4).
7. **본체 동기화 패치** — blueprint Part 10-3 우선순위표(8행): blueprint Part 1-1·우려노트·9-6 / README §5-3 / spec mockup / variable_index / CHANGELOG / structure_check.

### E-4. [GATE] 검증 하네스 (정직성)
- **N% 귀속 검증 (★)**: 분모=controlled 동일조건(per-lever) / all-levers 구분 정확 / 측정 전 약속 안 한 값 (§9-5).
- **정직성 검증**: negative result(26b 불가·e2b 품질 미달 등)도 그대로 보고 / **통제 config ≠ 운영값** 구분 명시(Part 5-3) / baseline=재현성 확인 수치(참고치 아님).
- **재현성 명시**: 모든 수치가 N·CV·조건과 함께.
- **Lineage 완결**: 결과 → 원시데이터 → git_commit 추적 가능.

### E-5. 산출 → 완료
트레이드오프·전후 표 + 서사 + 권장 매트릭스 + 본체 동기화 패치 = **phase-1 완료**.

---

## §F. 마스터 시퀀스 + 머지 + phase-2 훅

### F-1. 임계 경로 (한눈)
```
[HO1] 데이터셋 실재화 → 프롬프트 캡처 → num_ctx 적재값 → e2b pull → ▣서명 → num_gpu 스윕 → e2b 스모크 → cooldown
   └▶[GATE: sha256 재현·num_ctx 확정·서명]
[HO2] sampler → poller → battery → (passive 훅) → 조인/DuckDB
   └▶[GATE: 자기검증·스키마·관찰자효과 sanity·Lineage] ← 통과 못 하면 HO3 금지
[HO3] 정답셋 → 단독창 → baseline → 관찰자A/B → 최적화배터리 → (26b 양자화) → 품질
   └▶[GATE: CV≤15% baseline 자격·26b 강등·관찰자 판정]
[HO4] 가설검증 → per-lever/all-levers N% → 트레이드오프·전후표 → 서사 → 본체 동기화
   └▶[GATE: N% 귀속·정직성·재현성·Lineage]
```

### F-2. 머지 (blueprint Part 8)
- phase-1 controlled는 **STEP 1B 완료 커밋에 핀**(LLM 호출부 고정). 옵션 카드(STEP 2)는 호출부 안 바꿔 여유 있음.
- 병합 = **STEP 2 진입 전 1 PR**(도구 + 결과 + 본체 동기화). 도구(+passive 훅 gate off)는 본진 무영향.

### F-3. phase-2 훅 (deferred)
phase-1 완료 후 STEP 3에서 main 구현 코드 확인 → EDA·요약·**코드생성**(decode 길어 num_predict 상한 자주 도달 → 출력특성 다름) LLM을 동일 방법론(controlled→real-world)으로 **별도 protocol·핸드오프**(`*_phase2_*`)에서. 본 문서엔 자리만.

---

**작성**: 2026-06-02 v0_1 (Claude Opus 4.8 / 설계자=실무자 myeongsun97).
**갱신**: HO 진행 중 OPEN 채움·[GATE] 결과는 본 문서 해당 HO에 기록 + 필요 시 protocol `v0_2` 범프.
**다음**: HO1 B-3 1번(데이터셋 실재화)부터 착수. 단, OPEN 1·2·6(byeonggab89·팀원)은 HO1 전 협의 선행.
