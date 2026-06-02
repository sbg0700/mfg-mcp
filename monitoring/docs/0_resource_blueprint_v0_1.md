# LLM 리소스 모니터링·프로파일링 브랜치 — 마스터 블루프린트 (v0_1)

> **문서 목적**: 이 브랜치(`feature/llm-profiling`)가 **무슨 프로젝트이고, 무엇을 어떤 순서로
> 하는지**를 이 한 문서로 파악하게 하는 마스터 청사진. 새 수행자(새 AI 세션·팀원)의 진입점이자
> **단일 진실원본(single source of truth)**. 다른 리소스 문서와 충돌 시 본 문서가 우선한다.
>
> **이력**: 직전 `0_resource_MASTER_CONTEXT_v0_1` + `0_resource_blueprint_v0_1` 초안을 **단일 마스터로
> 통합**(MASTER_CONTEXT 승격 + blueprint 서사 흡수). 두 문서는 retire.
>
> **Snapshot**: 2026-06-02 v0_1 (알파 진입 전 / 측정 코드 미작성 / 측정 미시작).
>
> **표기 규칙**
> - 강조는 굵게(**)/인용(>)만. 별표(★) 마크업 금지(본체 README §5-1 규칙 승계).
> - 한국어 우선, 코드·식별자는 영문 그대로.
> - **`[실측]`** = 코드·명령·메타데이터로 검증된 사실 / **`[추론]`** = 미검증 추정 / **`[측정 후 v0_2]`** = 측정 캠페인 후 채울 자리.
> - **보안 마스킹**: 호스트명은 `LINUX-server`로 표기. 자격증명·외부 노출 포트 마스킹. 내부 loopback 포트만 표기.
>
> **위치 약칭**: `repo/` = `manufacturing-mcp/` 본진 루트. `본체` = manufacturing-mcp 제품.
> `공유 서버` = 측정이 도는 단일 GPU 호스트(`LINUX-server`). 본 브랜치 작업 영역 = `repo/monitoring/`.
>
> **명명·버전 정책**: `0_` = 글로벌 설계층(README·blueprint·protocol, 먼저 전부 읽음) /
> `1_` = 핸드오프 실행층(`1_HO*`). 버전 `v0_1` = 알파 전. 측정 결과 반영 시 `v0_2`로 갱신.
> 파일명·본문 버전 표기는 **언더스코어(`v0_1`)로 통일**.

---

## Part 0. Executive Summary

### 한 줄 정체성
한계 하드웨어(RTX 3070 **8GB VRAM**)에서 로컬 LLM(gemma4 계열)의 **자원·성능을 실측·모니터링·
프로파일링**하여, (1) 본체의 **모델 사이징 결정을 데이터로 정당화**하고 (2) **동일 조건 최적화
전후의 "N% 개선"을 정직하게 입증**하는, 본체에서 분기한 독립 작업 브랜치.

### 한 마디 (북극성)
> 측정 도구는 **일반 하드웨어 모니터링**(머신 전체)이고, 이 브랜치의 **측정 캠페인**은 그 위에
> **LLM 호출 귀속 렌즈**를 얹은 것이다. 일반 베이스는 그대로 두고, 렌즈만 LLM에 맞춘다.

### 정직한 명명 (오해 차단)
> 이것은 **"리소스 모니터링/프로파일링"**이다. **"실시간 스트림 파이프라인"이 아니다.**
> Kafka/Flink식 연상 금지. 본질은 추론 중 자원을 폴링·기록하고 사후 분석하는 것이다.
> 같은 공유 서버의 다른 프로젝트 P2(`binance-stream-bench`)와 이름이 섞이면 안 된다 — 무관하다.

### 현재 좌표 (2026-06-02 기준)
- 본체: 설계 v5 완성 + 1층(4 Agent + 4 MCP) 동작 + **STEP 1B 완료**(git STEP1B-3d), **알파 미진입** → **STEP 2(옵션 카드, `feature/step2-option-cards`) 진입 예정**. (v5 README의 "STEP 1B 미진입"은 stale — 본체 동기화 시 갱신 대상.)
- 본 브랜치: `feature/llm-profiling` 체크아웃·푸시됨. **문서 설계 단계**(측정 코드 미작성, 측정 미시작).
- 측정 환경 `[실측]`: `/api/ps`·`/api/generate`·`nvidia-smi` userspace 접근 동작 확인. 모델 메타 확인.
- 미설치: `gemma4:e2b`(8GB GPU 100% 적재 유일 후보) → 단독창에서 pull 필요(주체=admin/byeonggab89 협조).

### 차별점 (정직 버전)
- **공식·재현 가능·방어 가능한 데이터**만 쓴다(비공식 fine-tune 배제 → Part 1-4).
- **모델 비교가 아니라 동일조건 최적화 전후**로 N%를 주장한다(→ Part 5).
- **negative result도 산출**로 인정한다(26b는 8GB로 안 됨을 데이터로 확정 → Part 6-3).
- 본체의 **미해결 결정(모델 사이징)을 실측으로 닫고**, 부산물로 **운영용 일반 모니터링 도구**를 남긴다.

### 이 문서만 읽으면 보이는 워크플로우 (한눈)
```
[진단]   환경확정(e2b pull·pynvml·swap·KV·nproc) → 단독창 진단(num_gpu 스윕·keep_alive·e2b 품질 스모크)
   │         → 양자화 범위·baseline 수치 확정                          (핸드오프 1_HO1)
[계측]   사이드카 샘플러(pynvml+psutil) + /api/ps 폴러 + (passive용) llm.py PROFILE 훅 + 시각조인 + 출력스키마
   │                                                                  (핸드오프 1_HO2)
[측정]   passive(A) 실트래픽 baseline + controlled(B) 고정배터리 + 품질 KPI
   │                                                                  (핸드오프 1_HO3)
[최적화·산출]  진단우선 가설검증 → 트레이드오프표·전후표 → 서사 → 본체 동기화 (parquet + DuckDB + jupyter)
                                                                      (핸드오프 1_HO4)
```

---

## Part 1. 본체와의 관계 + 절대 제약 + 제외 모델

### 1-1. 본체 한 줄 + 이 브랜치의 자리
**본체** = SI 기업용 **MCP·Agent·로컬 LLM(gemma4) 기반 제조 데이터 전처리 자동화**. LLM이
판단·해석·매핑·요약(제안), 결정론 코드가 실행·검증(가드레일). 외부 API 0 / 데이터 외부 유출 0 /
코드=호스트·도커=실행.

> 본 브랜치는 새 scope가 아니다. 본체 설계가 **이미 미뤄둔 숙제**를 실행한다(아래 1-2).

### 1-2. 세 연결고리 (붕 뜬 게 아니라 빈 슬롯에 꽂힘)
1. **blueprint Part 1-1 우려 노트 → Part 9-6 알파 실측 검증** `[실측: 원문 확인]`:
   본체 blueprint는 "8GB 적재 가능 태그는 e2b 한 가지, 옵션 (a)~(d), 1~3 tok/s 등은 예측값이며
   알파 진입 시 `ollama pull` 후 실측 검증(Part 9-6)"이라 **명시적으로 미뤄뒀다**. 본 브랜치가
   그 실측 검증과 옵션 (a)~(d) 해소를 **실행**한다.
2. **품질 lane vs 자원 lane 분리** `[실측: spec-1 Part 1-9-3 확인]`:
   본체 Part 1-9-3의 "LLM 모니터링 7 지표"는 **품질·환각 lane**(모달리티 외 응답 비율·일치율·
   채택률 등)이다. 본 브랜치는 그걸 채우는 게 아니라 **자원·성능이라는 새 lane**을 추가한다.
   두 lane은 겹치지 않고 상호보완한다.
3. **토폴로지 정합**: 본체 헌법 "코드=호스트, 도커=실행만" = 측정 순도(측정대상 Ollama=호스트
   service)와 동일. 측정 설계가 헌법과 충돌하지 않는다.

### 1-3. 헌법 정합
| 헌법 규칙 | 본 브랜치 정합 |
|---|---|
| 외부 API 0 | 로컬 `nvidia-smi`/`psutil`/Ollama loopback(`localhost:11434`)만. 외부 호출 없음 |
| 데이터 외부 유출 0 | 리소스 수치는 데이터가 아닌 메트릭. 외부 송신 없음 |
| 코드=호스트/도커=실행 | 측정 코드·측정 대상 모두 호스트. Ollama는 host system service |
| LLM=제안/결정론=실행(D-13/D-15) | 본 브랜치는 결정에 LLM 안 씀. 호출의 자원만 관측 |

### 1-4. 절대 제약 — 측정 주체 권한 = userspace only (★중요)
`[실측: 2026-06-02 명령 검증]` 측정 주체(myeongsun97)는 공유 서버에서 **userspace 권한만** 가진다.

| 항목 | 가용 여부 `[실측]` | 영향 |
|---|---|---|
| `curl localhost:11434` (Ollama HTTP API) | **가능** | in-band 메타·`/api/ps`·controlled 직접 호출의 기반 |
| `nvidia-smi` (per-process VRAM 포함) | **가능** | 자원 샘플링·헤드룸 계산 |
| `pynvml` / `psutil` (userspace) | **가능 추정** `[추론]` | in-process 샘플러 (HO1에서 import 검증) |
| `ollama` CLI | **불가**(admin 소유, snap) | CLI 의존 금지 → 전부 HTTP API로 |
| `journalctl -u ollama` (서버 로그) | **불가**(adm/systemd-journal 그룹 아님) | 버퍼 분해(가중치/KV/compute) 직접 확인 불가 → `/api/ps size_vram` + nvidia-smi로 대체 |
| `docker ps/exec/inspect` | **불가**(도커는 admin/byeonggab89 소유) | 컨테이너 내부 점검 불가 → 백엔드 훅 검증은 byeonggab89 협조 |

> **설계 귀결**: 프로파일러는 **HTTP API + nvidia-smi/pynvml/psutil로만** 동작해야 한다. CLI·서버
> 로그·도커 내부에 의존하는 측정 경로는 설계에서 배제한다. 이 제약은 오히려 측정을 단순·견고하게
> 만든다(아래 Part 4-3 controlled 직접 호출 참조).

### 1-5. 제외 모델 (설계자 검토 확정)
- **31B Dense** → 헌법 절대규칙 #1 위반. 측정 목적이라도 1회 적재 금지. 외부 발표값 인용·26b 외삽으로만 비교.
- **super\*/uncensored 비공식 fine-tune** → ①안전가드 제거(SI 컴플라이언스 즉사) ②비공식 공급망
  리스크 ③채택 불가 모델은 측정 의미 0. 외부 자료 인용만 조건부 허용.

### 1-6. 역할 + 공유 서버 협의
- **본 브랜치(리소스)**: 설계자=실무자 모두 **myeongsun97**. 프로파일러 제작·실험·분석·문서 전부 주체.
- **본체 코드**: **byeonggab89**(구현·알파테스트·실측 데이터 출처). `backend/llm.py` PROFILE 훅(passive
  전용)은 사전공유 완료 `[사용자 확인: 사전공유됨 — HO1에서 byeonggab89 수신·적용 재확인]`. 측정 시간창은 **상황별 협의**.
- **공유 서버 제약** `[실측]`: 단일 RTX 3070 + Ollama system service를 byeonggab89와 **공유**.
  → 모델 적재·controlled 측정은 **조율된 단독 시간창**에서(상황별 협의).
- **서버 관리자 협의 반영** `[실측: 협의 문서]`: 신규 호스트 포트는 **`127.0.0.1` bind + 인증**. 고부하
  실험은 사전 공지 대상이나 **본 브랜치는 "내부 리소스 측정"이라 그 게이트는 비해당** — byeonggab89와의
  데이터 순도용 단독창 조율만 유효(허가 게이트 아님). 참고: Prometheus/Grafana 도입 허가는 **P2용**이었고,
  본 브랜치는 Part 7에서 미사용 결정.

---

## Part 2. 측정 대상 — gemma4 3 모델 + 양자화 축

### 2-1. 왜 gemma인가 (전제)
gemma는 **동급 크기 최고 성능 + 단일 GPU 최적화**다. 멀티 GPU/클라우드가 필요한 모델군과 달리,
**제조 현장(단일 GPU 온프레미스, 데이터 외부 반출 금지)**에 정확히 들어맞는다. 본 브랜치는 그
강점을 **8GB라는 극한에서 최대로 끌어내기**다. 타 모델군(qwen/phi 등) 비교는 범위 밖.

### 2-2. 3 모델 정체 (실측 GGUF 메타데이터)
| 항목 | gemma4:e2b | gemma4:e4b | gemma4:26b |
|---|---|---|---|
| 파라미터/양자화 `[실측]` | ~7.2GB급(미설치) | 8.0B / Q4_K_M | 25.8B / Q4_K_M |
| 디스크(로드) `[실측]` | ~7.2GB | ~9.6GB(로드 ~9.87GB) | ~18GB(로드 ~20GB) |
| 8GB 적재 | **유일 100% GPU 가능** | 초과 → 일부 CPU offload | 초과 → 대부분 CPU |
| 구조 `[실측]` | (e계열, 미설치) | block 42, **PLE=256**, vision16+audio12 | block 30, **MoE expert 128/활성 8**, PLE 0, vision27 |
| KV 절감 `[실측]` | — | shared_kv 18 + GQA(kv_head 2) | shared_kv 0 |
| ctx `[실측]` | — | 131072 | 262144 |
| 설치 | **미설치(pull 필요)** | 설치됨(현 개발 기본) | 설치됨 |
| 역할 | 8GB 기준점 | 8GB 균형 | 운영(24GB+ 전제) |

### 2-3. 양자화 축 (확정)
**Q4(현재) + e2b 기본.** Q3/Q2 추가 pull은 **선택**(시간 남으면, "더 작게 해서 26b도 8GB에?"
시험용). 핵심 가설은 양자화 없이도 검증되므로 디스크·시간 낭비 방지. 실제 pull 여부는 진단 후 결정.

### 2-4. 제외 정리
공식 gemma4 변형(e2b/e4b/26b)만 측정. **31B Dense·super\* 제외**(사유 Part 1-5).

---

## Part 3. 실측 데이터

### 3-1. 하드웨어 `[실측]`
RTX 3070 **8GB VRAM** / RAM 32GB(가용 ~27.6GB) / Swap 8GB / CPU **16코어**(nproc=16, 8코어
16스레드). Ollama는 host system service 상시 기동, 기본 모델 `gemma4:e4b`. 측정 API는
`localhost:11434`(loopback, 외부 아님).

### 3-2. 메모리 적재 — e4b `[실측: 2026-06-02 /api/ps + nvidia-smi, warm]`
| 소스 | GPU | CPU | total | GPU% | 비고 |
|---|---|---|---|---|---|
| `/api/ps` `size_vram` | **3.20GiB** | 6.67GiB | **9.87GiB** | **32%** | ollama 모델 회계(가중치+KV) = KPI 기준 |
| `nvidia-smi` (프로세스) | **3.40GiB**(3480MiB) | — | — | — | size_vram + CUDA 컨텍스트·compute 버퍼(~0.2GiB) |

> **측정 조건 주의**: 위 수치는 "hi" 1회 추론 후 warm 상태. **KV 증가·warmup·num_ctx에 따라 흔들린다.**
> protocol에서 측정 조건(num_ctx, warmup 후)을 고정해 재현성을 확보한다. (이전 문서의 2.8/6.6/9.4·9.9는
> 다른 시점 스냅샷 — 본 표를 정본으로 채택.)
> **헤드룸 계산은 nvidia-smi 실점유(3.40GiB) 기준**: 8GB 중 ~4.5GiB가 GPU에 비어 있음 → 그 실체가
> 회수 가능 헤드룸인지 구조적 CPU 핀인지는 Part 6-1 num_gpu 스윕으로 판정.

### 3-3. 메모리 적재 — 26b `[실측]`
로드 ~20GB, **63% CPU / 37% GPU**. 대부분 CPU 상주.

### 3-4. 알파 성능 `[실측: byeonggab89]` (예비 baseline)
| 작업 | e4b | 26b |
|---|---|---|
| /analyze (LLM 1회, JSON) | 5.0s | 120s (타임아웃) |
| /model recommend (LLM 1회) | 9.8s | — |
| Page 4 파이프라인 (LLM ~8회) | 46.6s | 274.2s |

### 3-5. 측정 소스 동작확인 + 포트 `[실측]`
- 동작 확인: `/api/ps`(size_vram) · `/api/generate`(메타) · `nvidia-smi`(per-process). `pynvml`/`psutil`은 HO1에서 import 검증.
- 포트: 6380/8001(P2)·3000/9090(Grafana/Prometheus 기본)·9100 — **전부 미개방**(리스닝 0). P2 미가동.

---

## Part 4. 측정 설계 — 2층 구조 + 방법론

### 4-1. 두 층 (동시에 측정)
- **① 일반 하드웨어 모니터링(샘플러)**: `pynvml`+`psutil`로 GPU util·VRAM·CPU·RAM·swap·온도를
  시계열 샘플링. **머신 전체, 모달리티 무관.** → 운영 단계 재활용(STEP 3 부산물).
- **② LLM 호출 귀속 렌즈**: Ollama in-band 메타 + `call_id` 조인. ①의 샘플 중 어느 구간이 어느
  LLM 호출이었나를 태깅. → "어느 모델이 얼마"를 떼고, 공유 박스 노이즈(타 프로세스)를 걷어냄.
- **둘은 동시에 측정된다.** 샘플러가 전체 HW를 상시 재는 위에 LLM 호출 시점이 귀속·시간조인된다.
- **확장성**: 비-LLM 단계(전처리·DB)는 `[추론]` 현재 병목 아님 → 후순위. 넓힐 땐 `call_id` 대신
  **phase 마커(단계 태그)**만 추가하면 같은 샘플러로 커버(구조 불변).

### 4-2. 측정 소스 (2종)
- **in-band (Ollama `/api/generate` 메타) = 1순위 KPI, 노이즈 0** `[실측: 동작 확인]`:
  `total_duration`/`load_duration`/`prompt_eval_*`/`eval_*`. **prefill(prompt_eval) vs
  decode(eval) 분리.** decode tok/s = `eval_count/(eval_duration/1e9)`.
- **out-of-band (자원 샘플러) = 자원 KPI**: `pynvml` **in-process**(subprocess `nvidia-smi` 매틱
  spawn 금지), 200~250ms 간격, **`taskset` 유휴코어 핀**(26b CPU offload와 경합 금지).
  GPU util·VRAM·온도/클럭(throttle 감시)·per-process VRAM·RSS·swap.
- **VRAM 귀속 분리**: `/api/ps`의 `size_vram`(내 모델) vs `nvidia-smi` 전체(경합 맥락). KPI는 `size_vram`,
  헤드룸은 nvidia-smi 실점유.

### 4-3. 통합 = 사이드카 + controlled 직접 호출 (권한 제약 반영, ★)
- **controlled(B) = 프로파일러가 API 직접 호출.** 고정 프롬프트를 프로파일러가 `localhost:11434`에
  직접 curl로 쏜다. 호출 시작·끝 시각을 **호스트 시계 하나**로 잰다 → **컨테이너↔호스트 시계 문제 자체가
  없음. 백엔드 훅·도커와 무관.** N%의 출처인 controlled가 본진 코드에 의존하지 않는다.
- **passive(A) = 백엔드 훅 필요.** 실트래픽이 byeonggab89의 백엔드를 통과하므로, `backend/llm.py`
  `generate()`에 `call_id`+`origin_ts` **최소 훅(2줄+헬퍼)** + **`LLM_PROFILE` env-gate(기본 off →
  본진 완전 무영향)**. in-band 로그는 본진 `agent_logs` 안 건드리고 **자체 jsonl**로 떨굼.
- **훅의 위치**: passive 전용·보조. 사전공유 완료. **핵심 산출물(N%) 차단 게이트가 아니라 passive
  모드 진입 전 가벼운 협의 항목.**

### 4-4. 프로세스 간 시각 조인 — CLOCK_MONOTONIC (passive에 한함)
- **controlled**: 단일 프로세스(프로파일러)라 시계 조인 불필요.
- **passive**: 훅(백엔드)·샘플러(호스트) 모두 **`time.clock_gettime_ns(time.CLOCK_MONOTONIC)`**로 통일.
  > `perf_counter`는 "기준점 미정의"라 프로세스 간 비교 금지(조용히 어긋나 per-call 자원 프로파일이
  > 틀어짐 — C3 교정 사항).
  > 백엔드가 도커 컨테이너면 컨테이너의 time namespace 사용 여부 확인 필요(기본 미사용이면 안전).
  > 측정 주체는 docker 접근 불가 → **byeonggab89가 검증**하거나, passive를 coarse 귀속으로 운영.

### 4-5. 두 측정 모드 (둘 다 필수)
- **(A) passive 관측**: 알파 실트래픽 그대로 → **진짜 baseline·운영 분포**.
- **(B) controlled 배터리**: 고정 프롬프트(실프롬프트 3종 × 각 모델 × N회) → **"N% 개선" 귀속의 유일
  근거**(실트래픽은 매번 달라 비교 불가). 입력 데이터셋 = **더미/합성 고정**(③ 더미 기준; 실데이터는
  passive 검증 시 재확인).

### 4-6. 캐시(KV/prompt) 측정 — cold·warm 둘 다 (★)
keep_alive 레버의 N%는 곧 **(cold 비용) − (warm 비용)**이다. 따라서 캐시를 켠 warm과 끈 cold를
**둘 다** 측정한다.
- **cold**: 매 호출 prefill 재계산 → 정직한 최악치·비교 공정.
- **warm**: keep_alive 상주 + 반복 컨텍스트 → 실운영 낙관치.
- **장**: keep_alive 이득을 직접 정량화. **단**: 이 축으로 측정 횟수 2배.
- KV 캐시 동작 검증: 동일 프롬프트 반복 시 `prompt_eval_count` 0/감소로 캐시 활성 여부 특성화
  (안 줄면 버그가 아니라 캐시 off로 해석).

### 4-7. 재현성·관찰자효과
temp=0 / seed·num_predict 고정 / 워밍업 1회 콜드 분리 / **N=7 중앙값±CV**(>15%면 throttle·경합
의심) / 관찰자효과 **샘플러 on·off A/B 캘리브레이션 — 반드시 같은 단독창 안에서 back-to-back**(다른
시간이면 공유 박스 노이즈가 교란). 영향 유의 시 in-band 1순위.

---

## Part 5. baseline + "N% 개선" 프레이밍 (정직성의 심장)

### 5-1. baseline 정의 (사용자 합의)
> **baseline = "현 설계 메인(26b) + e4b가 오늘 8GB 박스에서 무튜닝으로 도는 controlled 수치".**
> 예비값 = Part 3-4 알파 실측. 측정 후 controlled 수치로 확정.
> 1줄 근거: *8GB VRAM 초과로 Ollama가 자동 CPU offload — 이게 현 하드웨어의 실제 운영 조건.*

### 5-2. baseline 역할 분리 (★ — N% 귀속 명확화)
| 모델 | baseline 역할 | N% 대상? |
|---|---|---|
| **e4b** (현 개발 기본) | **헤드라인 N%의 주인공** — 헤드룸·keep_alive 레버 여지 가장 큼 | **예 (동일모델 전후)** |
| e2b | keep_alive만 적용(이미 100% GPU) — 보조 N% | 보조 |
| 26b | **negative-result 앵커** — "왜 8GB에 안 맞나"의 데이터 | 아니오(8GB에서 최적화 안 함) |

### 5-3. N% 귀속 규칙 (절대)
- ❌ "e4b가 26b보다 빠르다" = **모델 비교지 우리 개선이 아님.**
- ✅ "**동일 모델·동일 하드웨어**에서 파라미터/파이프라인 핸들링 최적화 → baseline 대비 latency
  N%↓ / VRAM 효율 N%↑" = 정당한 개선.
- **N% 분모는 controlled(B)의 최적화 전 동일 조건만.** 측정 전 N% 약속 금지.

### 5-4. 산출되는 영업·포트폴리오 자산
- 권장 사양 매트릭스: **8GB → e2b(GPU 상주)~e4b(균형) / 24GB+ → 26b(MoE, 운영)**.
- "어떤 하드웨어에 어떤 모델·설정"을 **실측으로 답하는 배포 가이드**.

---

## Part 6. 최적화 가설 — 진단 우선 (레버보다 진단 먼저)

### 6-1. 진단 핵심 (H1 대체) — 첫 실험 = num_gpu 스윕 (★)
`[실측 메타 근거]` e4b는 8GB 중 ~3.4GiB만 GPU 사용(nvidia-smi). 나머지 ~4.5GiB가 **(A) 회수 가능
헤드룸(num_gpu 레버)** 인지 **(B) PLE 구조적 CPU 핀(e4b 바닥)** 인지 **측정으로 판정**.
- **num_gpu 스윕**: 같은 추론을 `options.num_gpu`를 단계적으로 올려가며(현재→…→OOM 직전) 매번
  (GPU 점유, decode tok/s) 기록.
  - 더 올려서 GPU에 들어가고 tok/s↑ → **(A) 회수 가능** → num_gpu가 유효 레버.
  - OOM 나거나 6.67GiB(PLE·멀티모달 타워)가 안 줄음 → **(B) 구조적 CPU 핀** → num_gpu 무효.
- `[추론]` PLE 특성상 (B) 비중 클 가능성. 추론 중 peak VRAM 측정은 이 스윕의 **해석용 입력**.

### 6-2. H1(num_ctx↓→GPU 100%) — demote, 단 측정은 함 [OPEN]
- e4b CPU 6.67GiB는 KV가 아니라 **PLE(256) + 안 쓰는 vision/audio 타워**(설계상 CPU 고정). KV는
  이미 작음(shared_kv 18 + GQA). → num_ctx 줄여도 그 6.67GiB 안 움직임. e4b 100% GPU는 e2b만 가능.
- **그래도 protocol에선 num_ctx 4096 vs 2048 둘 다 측정**(경험적 확인). 본문엔 "효과 작을 것 + 이유"
  기술(측정 결과 해석용). **[OPEN: 측정 결과 보고 본문 확정 — v0_2]**

### 6-3. 26b = MoE expert 스래싱 (H3, negative result) `[실측 메타 + 알파]`
26b는 MoE(128 experts, 토큰당 8 활성). 8GB에선 expert 가중치 대부분이 CPU/RAM에 있고 **토큰마다
필요한 8개가 바뀌어 CPU↔연산 랜덤 페치 폭발 → 120초 타임아웃**. num_gpu로 못 고침(hot expert 예측
불가). → **"24GB+ 전제" 확정**. "26b가 본질적으로 느린 게 아니라 8GB에 안 맞아서"를 데이터로 분리.
> **26b 측정 예산 (조건부 제외, ③ 반영)**: 26b 포함. **단 단일 호출이 임계시간 T 초과 또는 써멀
> 스로틀 발생 시 → negative-result 확인용(단일 프롬프트 N=3 + 타임아웃 문서화)으로 자동 강등.**
> 풀 배터리 강행 금지(공유 박스 수 시간 스래싱 방지).

### 6-4. keep_alive = 가장 현실적 same-model 레버
Page 4 파이프라인은 LLM ~8회 호출 `[실측: e4b 46.6s / 26b 274.2s]`. 중간 재로딩이 끼면
`load_duration`이 매번 붙음. keep_alive로 상주시키면 제거 → **깨끗한 N%가 나올 1순위 same-model 레버.**
(측정은 Part 4-6 cold/warm 양쪽으로.)

### 6-5. e2b 품질 트레이드오프 (H4) — HO1에 품질 스모크 선행 (★)
e2b는 GPU 100% 적재라 빠름 — 당연. **품질을 함께 측정해야 의미 있다**: JSON 유효율 / 추천 정확도
(정답 있는 케이스) / rationale facts 인용율. 결과 = "e2b latency N%↓이나 JSON 유효율 e4b 95% vs
e2b 78%" 식 **트레이드오프 표**.
> **e2b 품질 스모크 (go/no-go, HO1)**: e2b pull 직후 실프롬프트 3종을 1~2회만 돌려 (a) JSON 파싱
> 성공 (b) 추천 합리성만 빠르게 본다. **통과 못 하면 "8GB→e2b 권장" 서사를 접고 keep_alive 레버로
> 무게중심 이동.** 며칠짜리 캠페인 확정 전 분기점.

### 6-6. 최적화 레버 요약
| 레버 | 기대 | 진단 의존 |
|---|---|---|
| num_gpu(offload 레이어) | e4b 헤드룸 회수 시 큰 이득 | **6-1 스윕 판정에 종속** |
| keep_alive | 재로딩 load_duration 제거 | 독립, 1순위 (cold/warm 양측) |
| num_ctx | (e4b엔 효과 작음 — 6-2) | 보조, 측정은 함 |
| 양자화(Q3/Q2 pull) | 크기↓→적재율↑ | 선택 [OPEN] |

---

## Part 7. 산출물 + 저장 (Grafana 제외)

### 7-1. 결과물 4종
1. **트레이드오프 표**: 3모델 × (latency / VRAM 적재율 / tok/s / JSON유효율 / 추천정확도).
2. **최적화 전후 비교표**: 동일 모델 baseline vs 튜닝 → latency N%↓ / VRAM효율 N%↑.
3. **서사 문서**: 문제 → 측정 → 최적화 → 결정(권장 매트릭스). (정직 명명 유지.)
4. **부산물**: 운영 단계 일반 리소스 모니터링 도구(STEP 3 재활용).

### 7-2. 저장 = parquet + DuckDB (Grafana 불필요)
- 우리 데이터는 소량(N=7 × 3프롬프트 × 3모델, 실시간 아님). **본진 PostgreSQL과 별개로 격리 저장.**
- **권장: 시계열 샘플=parquet(다량), 호출별 요약·런 메타=DuckDB(소량).** DuckDB는 임베디드(서버리스
  단일파일)로 **parquet를 SQL로 직접 쿼리** + pandas/jupyter 통합이 매끄러움. **SQLite는 대안**(SQL은
  되나 parquet 직접 쿼리·분석함수는 DuckDB가 우위).
- Grafana는 **P2의 실시간 대용량(WS 스트림)**용 도구였음 — 우리 경계형 캠페인엔 오버킬. **v0_1 제외.**
- **본진 PG는 어느 단계든 안 씀**(사이드카 원칙 — 측정 로그를 본진과 안 섞음).
- 측정 데이터는 gitignore: `logs/`·`results/`·`*.jsonl`·`*.parquet` + **`*.db`·`*.duckdb`·`*.sqlite`** 추가.

---

## Part 8. 병합 타이밍 + 층별 baseline 정책

**병합되는 것 2종**: (A) 측정 도구 + (passive용) PROFILE 훅(`monitoring/` + `llm.py` 2줄, 게이트
off라 본진 무영향) / (B) 측정 결과 = 모델 사이징 결정(본체 문서 동기화).

**층별 baseline 정책 (중요)**:
- **일반 HW 층**: 본진 LLM 코드 변경에 안 묶임 → **최신 기준 재-baseline 자유.**
- **LLM 귀속 층**: N% 유효하려면 **코드 상태 고정** 후 측정. STEP 2가 섞이면 baseline 흐려짐 —
  **이것이 byeonggab89가 "병합 회의적"이었던 이유(LLM 호출부 한정)**, 타당.

**권장 병합 시점**:
1. 측정은 **고정 코드 상태**(LLM 호출부 변경 머지 전). controlled는 **고정 더미 데이터셋**(재현성).
2. 도구 검증 + 측정 캠페인 완료 + 모델 결정 → **STEP 2 진입 전(STEP 1B 완료 상태) 1개 PR로 병합**
   (도구+결과+문서동기화). 단 병합 타깃의 **본질은 phase 라벨이 아니라 "LLM 호출부 고정 커밋에서
   controlled 측정"**이다. STEP 2 옵션 카드는 LLM 호출 횟수·프롬프트를 안 바꾸므로(결정론 옵션) 호출부
   baseline 영향이 작아 타이밍에 여유가 있다 → controlled는 **현 STEP 1B 완료 커밋에 핀**해두면 됨.
3. 멘탈모델 정합: *더미로 골격·오류 안정화 → controlled로 baseline 확정 → (알파 중 실데이터 passive
   검증) → 병합.* 실데이터는 운영분포 검증(passive)용이라 **핵심 N% 병합 전 필수는 아님.**

---

## Part 9. 위험 요소 + 미해결 (정직 버전)

### 9-1. 위험 / 완화
| 위험 | 내용 | 완화 |
|---|---|---|
| 공유 박스 경합 | 타 프로세스가 CPU/GPU 점유 → CV 증가, baseline 오염 | 단독창 조율 / N=7 중앙값±CV>15% 재측정 / 26b는 박스 quiesce(팀원 협의) |
| 권한 제약 | CLI·journal·docker 불가 → 측정 경로 제한 | HTTP API+nvidia-smi/pynvml/psutil only (Part 1-4) |
| 관찰자효과 | 샘플러가 측정대상 자원을 갉음 | 같은 단독창 on/off A/B 캘리브레이션, 유의 시 in-band 1순위 |
| 시계 조인 어긋남 | passive에서 컨테이너 시계 불일치 → 조용한 오류 | controlled는 단일 프로세스(무관) / passive는 byeonggab89 time namespace 검증 |
| e2b 품질 미달 | 작은 모델이라 JSON·추천 품질 저하 가능 | HO1 품질 스모크 go/no-go (Part 6-5) |
| 26b 측정 폭주 | 풀 배터리 시 수 시간 스래싱 | 조건부 강등(임계시간 T / 스로틀) — Part 6-3 |
| 수치 드리프트 | VRAM이 KV·warmup·num_ctx에 흔들림 | protocol에 측정 조건 고정 (Part 3-2) |

### 9-2. OPEN (결정 대기)
- [ ] **num_gpu 스윕 판정**: (A) 헤드룸 회수 vs (B) 구조적 CPU 핀 — 측정 후 (HO1).
- [ ] **baseline 수치**: controlled 측정 후 확정(정의는 Part 5-1로 고정). **[측정 후 v0_2]**
- [ ] **H1 num_ctx 효과**: 측정은 함, 본문 해석 확정 보류 (Part 6-2).
- [ ] **양자화 범위**: Q4 고정 vs Q3/Q2 추가 pull (진단 후).
- [ ] **e2b pull 시점**: 단독창 조율.
- [ ] **품질 KPI 정답셋**: 추천 정확도용 정답 케이스 정의 — **수행하며 결정(HO3 선결)**.
- [ ] **26b 박스 quiesce 강도**: 팀원 협의 후 확정.
- [ ] **DuckDB vs SQLite 최종**: protocol에서 확정(기본 DuckDB 권장).
- [ ] **passive 시계 검증**: 백엔드 컨테이너 time namespace — byeonggab89 확인.

### 9-3. 설계자 검토 4조건 — 수용 상태
① 31B 제외 ✅ / ② super\* 제외 ✅ / ③ 측정 프로토콜 v0_1 사전 합의 → **protocol 문서로**(부록 C 요약) /
④ baseline 정당성 사용자 합의 → **Part 5-1로 확정**. 4조건 충족 시 알파와 병렬 진행 OK.

---

## Part 10. 로드맵 + 핸드오프 4분할 + 본체 동기화

### 10-1. 작업 순서
진단 → 계측 도구 → passive(A) → controlled(B) → 최적화 실험(진단 우선 재배열) →
트레이드오프·전후 표 + 서사 → 본체 동기화.

### 10-2. 핸드오프 4분할
| 핸드오프 | 범위 | 산출 |
|---|---|---|
| **1_HO1 진단** | 환경확정(e2b pull·pynvml/psutil 검증·swap·KV·nproc) + 단독창 진단(num_gpu 스윕·keep_alive·**e2b 품질 스모크**) | 양자화 범위·baseline 수치·스윕 판정 |
| **1_HO2 계측 도구** | 사이드카 샘플러 + /api/ps 폴러 + (passive) llm.py PROFILE 훅 + 시각조인 + 출력스키마(parquet/DuckDB) | 측정 도구(실행파일) |
| **1_HO3 측정 캠페인** | passive(A) + controlled(B, cold/warm) + 품질 KPI(+정답셋 정의) | 원시 측정 데이터 |
| **1_HO4 최적화·산출** | 진단우선 가설검증 + 트레이드오프/전후 표 + 서사 + 본체 동기화 패치 | 결과물 + 본체 합류 |

> 핸드오프 분할 입도(4개)는 본 블루프린트 확정 후 상세 합의.

### 10-3. 본체 동기화 대상 (브랜치 결과 반영 시, 우선순위)
| 우선 | 문서 | 갱신 |
|---|---|---|
| 1 | blueprint Part 1-1 표 행 #1 | 메인/스캐폴딩 모델 태그 확정 |
| 1 | blueprint Part 1-1 우려 노트 | 옵션 (a)~(d) 결정 명시 |
| 1 | blueprint Part 9-6 | 인프라 실측 체크 |
| 2 | README §5-3 절대규칙 행 1 | blueprint 행 #1 동기 |
| 2 | spec-1/2/3 mockup `[모델: e4b ▼]` | 6 페이지 전체 |
| 3 | variable_index | 모델 관련 행(없으면 신규) |
| 3 | CHANGELOG | 알파 첫 기록 = 모델 결정 |
| 4 | 0_structure_check_v5 | 모델 태그 정합 체크 |

---

## Part 11. 문서 체계 + 작업 규칙

### 11-1. 문서군 (단일 home = `repo/monitoring/docs/`)
> **모든 브랜치 문서는 `monitoring/docs/`에 단일 home.** `docs/specs/`에 있던 TEAMMATE·TROUBLESHOOT
> (이 브랜치가 추가한 파일 — main엔 없음)는 `monitoring/docs/`로 이전하고 `docs/specs/` 사본은
> 제거한다(중복·drift 차단). 본진 v5 설계 문서(`docs/0_*_v5.md`·`decisions.md`)는 그대로 둔다.
```
monitoring/
├─ docs/
│  ├─ 0_resource_blueprint_v0_1.md       ← 본 문서(단일 진실원본, 진입점)
│  ├─ 0_resource_README_v0_1.md          (진입 가이드, 예정)
│  ├─ 0_resource_protocol_v0_1.md        (고정값 계약, 부록 C 기반, 예정)
│  ├─ 2_TEAMMATE_claude_memory.md        (작업 규칙 단일 소스 — §4 관찰성/포트 포함 최신본)
│  ├─ 1_BG_TROUBLESHOOT_llm_resource_optimization.md  (상세 방법론 원본)
│  └─ 1_HO1~4_*.md                       (실행 핸드오프, 본 문서 확정 후)
└─ (코드 예정) llm_resource_sampler.py / ps_poller.py / bench_battery.py / analyze_logs.py
```
> 직전 `0_resource_MASTER_CONTEXT_v0_1`·`0_resource_blueprint_v0_1`(초안)은 본 문서로 **통합·retire**.
> **TROUBLESHOOT §3-4 sync 필요**: "훅=passive 전용 / controlled=API 직접 호출"로 갱신(현재 in-band 중심 서술).
> (명명 prefix(0_/1_/2_) 정리는 추후 — 지금은 단일 home·내용 최신성 우선.)

### 11-2. 수행자 진입 순서
TEAMMATE(어떻게 행동) → 본 blueprint(왜/무엇) → protocol(고정값) → handoff(실행 단계).

### 11-3. git 규칙 (TEAMMATE 단일 소스 — 요약+포인터)
git/커밋/충돌/측정순도 규칙은 **`monitoring/docs/2_TEAMMATE_claude_memory.md`에만** 둔다(복제 drift 방지).
- 작업 브랜치 `feature/llm-profiling`만. **main 직접 push 금지. `git init`·`reset`·`rebase` 금지.**
- 커밋 = Conventional Commits(영어). 논리 단위 완성 + 사용자 컨펌 시 답변 마지막에 커밋 명령.
- **새 파일 우선**(`monitoring/`). **불가피한 기존 수정 = `backend/llm.py` PROFILE 훅뿐**(게이트+사전공유).
- **절대 안 건드림**: `agents/`·`frontend/`·`catalogs/`·`harness/`·`mcp-servers/`·`db/`·`docs/0_*_v5.md`·`docs/decisions.md`·본진 `docs/specs/*` 명세(inspector/planner/STEP_1B 등).
- **단 예외(home 통합)**: `docs/specs/`에 이 브랜치가 추가했던 **TEAMMATE·TROUBLESHOOT 2개 파일만** `monitoring/docs/`로 이전 후 `git rm`(main엔 없는 브랜치 산출물 — 본진 v5 명세는 불가침).

### 11-4. 설계 단계 변경 추적
본체 CHANGELOG는 "알파 이후"라 우리 설계 수정 미포함 → **각 문서 헤더에 `이력` 블록 + 버전 범프
(`v0_1→v0_2`)**로 추적(v5 방식). 별도 changelog 파일 안 만듦.

---

## Part 12. AI 컨텍스트 사용 가이드

### 12-1. 새 세션 1차 컨텍스트
1. `monitoring/docs/2_TEAMMATE_claude_memory.md` (작업 규칙)
2. 본 문서 `0_resource_blueprint_v0_1.md`
3. `0_resource_protocol_v0_1.md` (작성 후)
- 본체 맥락 필요 시: `0_CONSOLIDATED_PROJECT_DESIGN.md` (본체 합본)

### 12-2. AI가 착각하기 쉬운 부분 (이 브랜치 한정)
- **"리소스 모니터링" ≠ "스트림 파이프라인"** — Kafka/Flink 연상 금지. P2(`binance-stream-bench`)와 무관.
- **N%는 동일모델 전후만** — "e4b가 26b보다 빠르다"는 모델 비교지 우리 개선이 아님.
- **31B·super\* 측정 금지** — 외부 인용/외삽만.
- **본진 PostgreSQL 안 씀** — 측정 로그는 parquet/DuckDB로 격리.
- **측정 주체 권한 = userspace only** — ollama CLI·journalctl·docker 의존 코드 제안 금지.
- **controlled는 API 직접 호출(훅 무관) / passive만 훅 필요** — 둘을 섞지 말 것.
- **모델 적재·controlled는 단독창에서** — 공유 박스 경합 = 측정 오염.
- **VRAM 수치는 측정 조건(num_ctx·warmup)에 흔들림** — 조건 명시 없이 단정 금지.

### 12-3. AI가 주관 판단하면 안 되는 영역
- 측정 전 N% 약속 금지(분모는 controlled 최적화 전 동일 조건).
- `backend/llm.py` 외 기존 파일 수정 제안 금지(특히 `frontend/`·`agents/`는 byeonggab89 절대영역).
- baseline 정의 변경 금지(Part 5-1 고정).
- 가능: 측정 데이터 해석, 가설 검증 서술, 트레이드오프 표 작성, 권장 매트릭스 도출.

---

## 부록 A. GGUF 메타데이터 실측표 (헤더, 적재 아님)
| 키 | e4b `[실측]` | 26b `[실측]` |
|---|---|---|
| parameter_size / quant | 8.0B / Q4_K_M | 25.8B / Q4_K_M |
| block_count | 42 | 30 |
| per_layer_input_embedding (PLE) | **256 (있음)** | **0 (없음)** |
| expert_count / used | — | **128 / 8 (MoE)** |
| attention head / kv | 8 / 2 (GQA) | 16 / (kv 0) |
| shared_kv_layers | 18 | 0 |
| 멀티모달 타워 | vision 16 + audio 12 | vision 27 |
| context_length | 131072 | 262144 |

## 부록 B. 알파 실측 데이터 (baseline 후보 / byeonggab89)
| 작업 | e4b `[실측]` | 26b `[실측]` |
|---|---|---|
| /analyze (LLM 1회, JSON) | 5.0s | 120s (타임아웃) |
| /model recommend (LLM 1회) | 9.8s | — |
| Page 4 파이프라인 (LLM ~8회) | 46.6s | 274.2s |
| ollama ps 적재 | ~9.87GB (GPU 3.20 / CPU 6.67, 32%GPU) | ~20GB (63%CPU/37%GPU) |
| 하드웨어 | RTX 3070 8GB / RAM 32GB(가용~27.6GB) / Swap 8GB / CPU 16코어 | |

## 부록 C. 측정 protocol v0_1 — 9블록 고정값 (요약 + 포인터)
> 상세·서명은 별도 `0_resource_protocol_v0_1.md`. 아래는 본 블루프린트가 고정한 값 요약.

| 블록 | 확정값 |
|---|---|
| 1 양자화 | **Q4 + e2b 기본**, Q3/Q2 선택(시간 남으면) |
| 2 프롬프트 | 실 3종(analyze/model/planner) + **입력 데이터셋 고정(더미)** + 동일 AggregatedContext. byeonggab89가 실프롬프트 캡처해 고정 |
| 3 제어값 | temp=0, seed=42, num_predict=512, num_ctx **4096 / 2048 둘 다**, N=7, 워밍업1 콜드분리, **cache cold/warm 둘 다**, 중앙값±CV(>15% 경고) |
| 4 KPI 단위 | 시간 ms/s(ollama ns 변환), tok/s=eval_count/(eval_dur_ns/1e9), VRAM MiB, **N=7이라 p50+min/max**(p95 불안정). 품질 3종(JSON유효율/추천정확도/facts인용율) |
| 5 baseline | 측정 후 채움 + 예비=알파 실측(부록 B) + 역할 분리(Part 5-2) + 근거 1줄(Part 5-1) |
| 6 측정소스·도구 | **LOCKED** — /api/generate 메타, pynvml in-process 250ms taskset핀, /api/ps size_vram, controlled=API 직접호출, passive=CLOCK_MONOTONIC 조인+LLM_PROFILE gate |
| 7 단독창 | 모델 적재·controlled는 단독창(상황별 협의). 26b는 박스 quiesce(팀원 협의) |
| 8 출력 | **parquet(시계열) + DuckDB(요약·메타) 격리, 본진 PG 안 씀**. SQLite 대안 |
| 9 합격/판정 | **LOCKED** — CV>15% 재측정, 관찰자효과 유의→in-band 1순위, KV캐시 검증(prompt_eval_count), 26b 임계시간 초과→negative-result 강등 |

## 부록 D. 용어집
- **in-band / out-of-band**: Ollama 응답 메타(노이즈 0) / 외부 자원 샘플러.
- **prefill / decode**: prompt_eval(입력 처리) / eval(토큰 생성). tok/s는 decode 기준.
- **num_gpu 스윕**: GPU에 올릴 레이어 수를 단계적으로 바꿔 헤드룸 회수 가능성 판정(Part 6-1).
- **cold / warm**: 캐시 미스(매번 prefill) / keep_alive 상주(prefill 재사용). keep_alive N%=cold−warm.
- **PLE**: per_layer_input_embedding. e4b가 CPU에 상주시키는 큰 비중(num_ctx 무관).
- **MoE 스래싱**: 26b가 토큰마다 다른 expert 8개를 CPU↔GPU 랜덤 페치 → 폭주(Part 6-3).
- **passive(A) / controlled(B)**: 실트래픽 관측 / 고정 배터리. N%는 controlled에서만.
- **negative result**: "26b는 8GB로 안 됨"처럼 안 되는 걸 데이터로 확정하는 것 — 정당한 산출.
- **P2**: 같은 서버의 무관한 프로젝트(`binance-stream-bench`). 혼동 금지.

---

**작성**: 2026-06-02 v0_1 (Claude Opus 4.8 / 설계자=실무자 myeongsun97).
**갱신 정책**: 측정 결과 반영 시 헤더 `이력` + `v0_2` 범프. 본 문서가 단일 진실원본 — 충돌 시 본 문서 우선.
**다음 단계**: (1) protocol v0_1 작성(부록 C + seed·정답셋 확정 → byeonggab89·사용자 서명) (2) 핸드오프 4분할 상세화 (3) 단독창 조율 → 1_HO1 진단.
