# 트러블슈팅 설계도 — 한계 하드웨어(RTX 3070 8GB)에서 로컬 LLM 리소스 최적화 + 프로파일링

> **이 문서는 팀원 전담 트러블슈팅 태스크의 설계도다.**
> 작성: 설계자(claude.ai 세션) + 팀원 1차 기술검토 자료 크로스체크 결과.
> 목표: 측정 도구(프로파일러)를 만들고(C-1), 그걸로 Ollama 리소스 할당을 최적화해(C-2),
> 최적화 전/후를 같은 도구로 비교하여 "N% 개선"을 정직하게 입증한다(C-3).
> **명명 규칙(정직)**: "리소스 모니터링/프로파일링" — 스트림 파이프라인 아님.

---

## 0. 트러블슈팅 주제 — 우리가 직면한 문제와 부합하는가? (검토 답변)

**질문(설계자)**: "공장은 하드웨어가 제한적일 수 있음을 감안, 제한적 하드웨어(VRAM 8GB, RTX 3070)에서
리소스 모니터링·파이프라인 핸들링으로 Ollama의 GPU 점유를 최적화하거나 속도 측면에서 더 유연하게
할당하는 방법이 있는가?"

**판정: 부합하고 적합하다.** 근거:
1. **실제 직면한 문제다.** 알파테스트 중 드롭다운 26b 선택 시 `/analyze`가 **120초 타임아웃**, e4b는 5초.
   Page 4 파이프라인이 26b에서 274초 vs e4b 46.6초. 8GB VRAM 초과로 CPU 오프로딩이 실측됐다.
2. **공장 현실과 정합.** 제조 현장은 멀티 GPU 클러스터를 두지 않는다. 단일 GPU(또는 그 이하)
   온프레미스가 일반적. "제한적 하드웨어에서 로컬 LLM을 어떻게 돌리나"는 우리 제품의 핵심 영업 질문.
3. **gemma 선택 근거와 직결.** gemma는 "단일 GPU에서 도는 최고 효율 모델"이 게임체인저다(아래 §1).
   그 강점을 8GB라는 극한에서 어떻게 살리느냐가 이 트러블슈팅의 본질.

**단, 프레이밍 교정 (중요):**
팀원 자료의 "기존 정량값 대비 KPI N% 개선"은 **무엇 대비 개선인지**를 명확히 해야 정직하다.
- ❌ "e4b가 26b보다 N% 빠르다" = 이건 모델 비교지 우리가 만든 개선이 아니다.
- ✅ "동일 모델·동일 하드웨어에서, Ollama 파라미터/파이프라인 핸들링을 최적화하여
     baseline 대비 latency N%↓ / VRAM 효율 N%↑" = 이게 정당한 "N% 개선".
→ N% 주장의 분모(baseline)는 **"최적화 전 동일 조건"**이어야 한다. (§4 controlled 측정 B가 필수)

---

## 1. 왜 gemma인가 + 3개 모델의 정체 (측정 전 필수 이해)

### gemma 게임체인저 이유 (트러블슈팅의 전제)
- gemma는 **동급 크기 중 최고 성능**이며, **단일 GPU/TPU 애플리케이션에 최적화**됐다.
- DeepSeek-V4·Llama 4·Qwen3 235B 등 강력한 모델은 멀티 GPU/클라우드가 필요한 반면,
  gemma는 단일 GPU에서 강한 추론·멀티모달·긴 컨텍스트(128K)를 제공한다.
- → **제조 현장(단일 GPU 온프레미스, 데이터 외부 반출 금지)에 gemma가 정확히 들어맞는다.**
  이 트러블슈팅은 "그 강점을 8GB라는 극한 하드웨어에서 최대로 끌어내기"다.

### 측정 대상 3개 모델 (gemma4 계열 — 확장 안 함)
| 모델 | 크기 | 8GB 적재 | 특성 | 역할 |
|---|---|---|---|---|
| **gemma4:e2b** | ~7.2GB | **유일하게 GPU 100% 적재 가능** | 가장 작음. 품질 트레이드오프 | "8GB에서 제대로 도는" 기준점 (★pull 필요) |
| **gemma4:e4b** | ~9.6GB | 초과 (일부 CPU offload) | **8GB 등급 최고 종합 역량**(업계 권장) | 현 개발 기본 |
| **gemma4:26b** | ~18-20GB | 초과 (대부분 CPU) | **MoE**: 토큰당 ~4B만 활성. 24GB면 기본 선택 | 운영(24GB+ GPU 전제) |

**핵심 이해 2가지:**
1. **e2b만 8GB GPU에 완전히 들어간다.** e4b·26b는 초과 → CPU offload → 느림. e2b는 미설치 → `ollama pull gemma4:e2b` 필요.
2. **26b는 MoE 구조**다. 18-20GB지만 토큰당 ~4B만 활성화되어, 24GB GPU에선 31B 밀집 모델의 ~95% 품질을
   훨씬 빠르게 낸다. 단 8GB엔 안 들어가 우리 환경에선 CPU offload로 느림. → "26b가 본질적으로 느린 게
   아니라, 8GB에 안 맞아서 느린 것"임을 측정으로 분리해야 한다.

**모델 확장 불필요 (설계자 결정):** gemma의 단일 GPU 효율이 채택 이유이므로, 타 모델군(qwen/phi 등)
비교는 범위 밖. gemma4 3종(e2b/e4b/26b)의 **속도 ↔ 품질 트레이드오프**에 집중한다.

---

## 2. ★우리 실측 데이터 — 트러블슈팅 출발점★ (baseline 후보)

알파테스트 중 측정된 값. 팀원의 [추론]을 이 실측으로 교체·확정할 것.

### 2-1. 추론 시간 (8GB VRAM, RTX 3070, 현 설정 = 최적화 전)
| 작업 | e4b | 26b | 비율 |
|---|---|---|---|
| `/analyze` (LLM 1회, JSON 출력) | **5.0s** | **120s (타임아웃)** | x24+ |
| `/model recommend` (LLM 1회) | **9.8s** | — (미측정) | — |
| Page 4 파이프라인 (Inspector+Planner+judge+exec+validate+aggregate, LLM ~8회) | **46.6s** | **274.2s** | x5.9 |

### 2-2. 메모리 적재 (`ollama ps` 실측)
| 모델 | 로드 크기 | CPU/GPU 분배 |
|---|---|---|
| e4b | 10GB | **68% / 32%** (CPU/GPU) |
| 26b | 20GB | **63% / 37%** (CPU/GPU) |

### 2-3. 하드웨어 (실측 환경)
- GPU: RTX 3070 **8GB VRAM**
- RAM: 32GB (가용 ~27.6GB) / Swap 8GB / 16코어 (팀원 자료: CPU 16코어 — 단 RTX 3070은 보통 8코어 Ryzen과 페어. 실측 확정 필요)
- Ollama: service 상시 기동. `OLLAMA_MODEL` 기본 `gemma4:e4b`.

### 2-4. Ollama 로그에서 확인된 오프로딩 (e4b 사례)
```
offloaded 42/43 layers to GPU
model weights: CUDA0(GPU) 2.8GiB + CPU 6.6GiB   ← 9.4GB 중 GPU엔 2.8GB만
total memory: 9.9GiB
```
→ e4b조차 42/43 레이어만 GPU, 출력 레이어는 CPU. 가중치 6.6GB가 CPU(RAM). 이게 속도 저하 원인.

**팀원 자료 [추론] 교정**: 팀원이 "26b는 GPU~40%/CPU~60%[추론]"이라 했으나, 실측은 **63%/37% CPU/GPU**
(즉 GPU 37%). "26b 18GB"는 list 기준 17GB, 로드 시 20GB. 이 실측으로 출발할 것.

---

## 3. 측정 도구 설계 (C-1: 프로파일러)

### 3-1. 통합 방식 결정 — **(ii) 사이드카 샘플러 채택** (팀원 질문 1 답)
**사유:**
- 본진 코드(헌법: "코드=호스트/도커, 측정 순도 유지")에 **덜 침습적**. `agent_logs.decisions`에 필드를
  덧붙이면(방식 i) 본진 스키마가 측정 관심사로 오염된다. 측정은 본진과 분리돼야 한다.
- **call_id로 조인**: 본진 LLM 호출에 `call_id`(uuid)와 `origin_ts_ns`(int64, time.perf_counter_ns)를
  찍는 **최소 훅**만 추가(아래 3-4). 프로파일러는 별도 프로세스로 자원을 샘플링하고, call_id로 사후 조인.
- 결과: 본진은 `call_id`·`origin_ts_ns` 두 필드만 로그에 남기고, 무거운 측정은 사이드카가 전담.

### 3-2. 측정 소스 (팀원 질문 2 — 방법론, (가) 정밀 채택)
**in-band (Ollama 메타데이터) = 1순위 KPI (노이즈 0):**
`/api/generate` 응답의 `total_duration`, `load_duration`, `prompt_eval_count`,
`prompt_eval_duration`, `eval_count`, `eval_duration`을 그대로 기록.
- **prefill(prompt_eval) vs decode(eval) 분리**: `prompt_eval_duration`(프롬프트 처리) vs
  `eval_duration`(생성)을 별도 KPI로. decode tok/s = `eval_count / (eval_duration/1e9)`.
- **KV 캐시 확인**: 동일 프롬프트 반복 시 `prompt_eval_count`가 0/감소하는지 기록 (캐시 히트 검증).
- 이 in-band 값은 Ollama가 직접 보고하므로 관찰자효과 0. **N% 개선의 1순위 근거.**

**out-of-band (자원 샘플러) = 자원 KPI:**
- **pynvml in-process** (★subprocess `nvidia-smi` 매틱 spawn 금지 — 팀원 지적 정확). 200~250ms 간격.
- 샘플: GPU util%, VRAM used(전체) + **per-process VRAM**(`nvmlDeviceGetComputeRunningProcesses`),
  GPU 온도/클럭(throttle 감시), psutil로 프로세스 RSS·CPU%.
- **VRAM 귀속 분리** (팀원 지적 정확): `/api/ps`의 `size_vram`(내 모델 점유) vs nvidia-smi 전체(경합 맥락).
  둘 다 기록하되 KPI는 `size_vram` 기준.
- **샘플러 코어 핀** (팀원 지적 정확): 26b의 CPU offload 레이어와 경합 안 하게 `taskset`으로 샘플러를
  별도 코어에 핀. (관찰자효과 최소화)

**제어 변수 (재현성):**
- `temperature=0`, `seed` 고정, `num_predict` 고정 (출력 길이 통일 → tok/s 비교 공정).
- 발열/클럭 throttle 감시: 연속 측정 시 GPU 온도 상승으로 클럭 다운되면 결과 왜곡 → 측정 간 cooldown.

**본진 환경에서 막힐 수 있는 지점 (팀원 질문 2 답):**
- pynvml: 도커 컨테이너 내부면 `--gpus all` + nvidia runtime 필요. **백엔드 컨테이너에서 pynvml/nvidia-smi
  접근 가능한지 먼저 확인** (`docker exec mfg-backend python -c "import pynvml; pynvml.nvmlInit()"`).
  안 되면 → 프로파일러를 **호스트에서** 실행(Ollama가 host service이므로 자연스러움).
- per-process VRAM: 일부 드라이버/컨테이너 조합에서 process 목록이 안 보일 수 있음 → size_vram으로 폴백.

### 3-3. 두 측정 모드 (팀원 질문 3 답 — 둘 다 필수)
- **(A) passive 관측**: 알파 실트래픽을 그대로 관측. **진짜 baseline·운영 분포**. 사이드카가 백그라운드 상주.
- **(B) controlled 배터리**: 고정 프롬프트 세트(동일 프롬프트 N회)로 측정. **"N% 개선" 귀속의 유일한 근거.**
  - B 없이 N% 주장 불가 (실트래픽은 프롬프트가 매번 달라 비교 불가).
  - B 배터리 구성: 우리 실제 프롬프트 3종(analyze 추천 / model 추천 / planner 계획)을 고정 입력으로.
  - 각 모델(e2b/e4b/26b) × 각 프롬프트 × N회(예 7회) → 중앙값±CV.
  - **B를 알파 일정에 끼울 것** (passive와 별도 세션, 타 트래픽 없는 시간대).

### 3-4. 본진 최소 훅 (침습 최소화 — 방식 ii 전제)
`backend/llm.py`의 `generate()`에 **2줄**만 추가 (측정 활성화 시에만):
```python
import time, uuid, os
PROFILE = os.environ.get("LLM_PROFILE", "0") == "1"   # 기본 off — 본진 무영향

async def generate(prompt, system=None, fmt_json=False, model=None) -> str:
    call_id = uuid.uuid4().hex if PROFILE else None
    origin_ts_ns = time.perf_counter_ns() if PROFILE else None
    payload = {"model": model or OLLAMA_MODEL, "prompt": prompt, "stream": False}
    if system: payload["system"] = system
    if fmt_json: payload["format"] = "json"
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        try:
            r = await c.post(f"{OLLAMA_HOST}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            if PROFILE:
                _profile_log(call_id, origin_ts_ns, model or OLLAMA_MODEL, data)  # in-band 메타 기록
            return data.get("response", "")
        except httpx.HTTPError as e:
            return json.dumps({"_llm_failed": True, "error": str(e),
                               "hint": "...", "model_attempted": payload["model"]})
```
```python
def _profile_log(call_id, origin_ts_ns, model, data):
    """in-band 메타를 jsonl로. PROFILE=1일 때만. 본진 로직 무영향."""
    rec = {
        "call_id": call_id, "origin_ts_ns": origin_ts_ns, "model": model,
        "total_duration": data.get("total_duration"),
        "load_duration": data.get("load_duration"),
        "prompt_eval_count": data.get("prompt_eval_count"),
        "prompt_eval_duration": data.get("prompt_eval_duration"),
        "eval_count": data.get("eval_count"),
        "eval_duration": data.get("eval_duration"),
    }
    with open(os.environ.get("LLM_PROFILE_PATH", "logs/llm_inband.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")
```
> `LLM_PROFILE=0`(기본)이면 call_id 생성도 안 함 → 본진 완전 무영향. 측정 시에만 `LLM_PROFILE=1`.
> 사이드카 샘플러는 별도 프로세스(아래 3-5)로, 시간(origin_ts_ns)으로 in-band 레코드와 조인.

### 3-5. 사이드카 샘플러 (out-of-band, 별도 프로세스/호스트)
```python
#!/usr/bin/env python3
"""llm_resource_sampler.py — pynvml + psutil로 자원을 250ms 간격 샘플링.
본진과 분리된 프로세스. taskset으로 별도 코어 핀 권장: taskset -c 15 python3 llm_resource_sampler.py"""
from __future__ import annotations
import time, json, os
import pynvml, psutil

INTERVAL = 0.25
OUT = os.environ.get("SAMPLER_PATH", "logs/llm_resource.jsonl")

def find_ollama_pids():
    return [p.pid for p in psutil.process_iter(["name"]) if "ollama" in (p.info["name"] or "")]

def main():
    pynvml.nvmlInit()
    h = pynvml.nvmlDeviceGetHandleByIndex(0)
    with open(OUT, "a") as f:
        while True:
            ts = time.perf_counter_ns()
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            try:
                clk = pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_SM)
            except Exception:
                clk = None
            # per-process VRAM
            procs = {}
            try:
                for p in pynvml.nvmlDeviceGetComputeRunningProcesses(h):
                    procs[p.pid] = p.usedGpuMemory
            except Exception:
                pass
            ollama_pids = find_ollama_pids()
            cpu_pct = sum(psutil.Process(pid).cpu_percent() for pid in ollama_pids if psutil.pid_exists(pid))
            rss = sum(psutil.Process(pid).memory_info().rss for pid in ollama_pids if psutil.pid_exists(pid))
            rec = {"ts_ns": ts, "gpu_util": util.gpu, "vram_used_total": mem.used,
                   "vram_total": mem.total, "gpu_temp": temp, "gpu_sm_clock": clk,
                   "ollama_vram_proc": {str(k): v for k, v in procs.items()},
                   "ollama_cpu_pct": cpu_pct, "ollama_rss": rss,
                   "swap_used": psutil.swap_memory().used}   # Swap 8GB 경계 감시 (팀원 질문 5)
            f.write(json.dumps(rec) + "\n"); f.flush()
            time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
```
> `/api/ps`의 size_vram은 별도로 주기 조회(아래 3-6). 샘플러는 자원 시계열, in-band는 호출별 KPI.

### 3-6. /api/ps 폴러 (size_vram = 내 모델 귀속 VRAM)
```python
# 측정 중 주기적으로 GET http://localhost:11434/api/ps → models[].size_vram, size_total 기록
# nvidia-smi 전체(경합) vs size_vram(내 모델) 구분의 핵심 소스
```

---

## 4. 최적화 실험 (C-2: 무엇을 튜닝하나 — "N% 개선"의 실체)

측정만으론 "개선"이 아니다. **같은 모델·같은 하드웨어에서 Ollama 파라미터·파이프라인 핸들링을 조정**하여
baseline 대비 개선을 만든다. 후보 레버:

### 4-1. Ollama 파라미터 레버
| 레버 | 설명 | 기대 효과 | 측정 |
|---|---|---|---|
| `num_gpu` (offload 레이어 수) | GPU에 올릴 레이어 수 명시 | 너무 많으면 OOM·throttle, 적으면 CPU 과다 → **최적점 탐색** | latency, size_vram |
| `num_ctx` (컨텍스트 크기) | KV 캐시 크기. 기본 4096 | 우리 프롬프트는 짧음 → 줄이면 VRAM 절약 → 더 많은 레이어 GPU 적재 | size_vram, tok/s |
| `num_thread` | CPU 스레드 수 | offload된 CPU 연산 병렬도 | decode tok/s (26b) |
| `num_batch` | 배치 크기 | prefill 처리량 | prompt_eval tok/s |
| keep_alive | 모델 상주 시간 | load_duration 제거 (재로딩 방지) | load_duration |
| 양자화 변형 | 더 강한 양자화(Q4→Q3 등) pull | 크기↓ → GPU 적재율↑ | size_vram, 품질 |

### 4-2. 핵심 가설 (측정으로 검증)
- **H1**: e4b의 `num_ctx`를 4096→2048(우리 프롬프트 충분)로 줄이면 KV 캐시 VRAM이 줄어, offload 레이어가
  42/43 → 43/43이 되어 GPU 100% 적재 → latency N%↓. (가장 유력 — 우리 프롬프트가 짧으므로)
- **H2**: keep_alive를 늘리면 모델 재로딩(load_duration) 제거 → 연속 호출 시 누적 시간 단축.
- **H3**: 26b는 8GB로는 num_gpu 조정해도 한계 → "24GB+ 전제" 확정 (negative result도 가치).
- **H4**: e2b는 GPU 100% 적재 → e4b 대비 latency N%↓이나, 품질(JSON 안정성/추천 정확도) 트레이드오프 측정.

### 4-3. ★속도 ↔ 품질 트레이드오프 측정 (설계자 강조)★
e2b가 빠른 건 당연 — **품질을 함께 측정해야 의미 있다.** 품질 지표:
- **JSON 유효율**: 각 모델 N회 호출 중 valid JSON 비율 (e2b가 깨질 확률 ↑ 예상 — B3 재시도와 연결).
- **추천 정확도**: 고정 입력(예: constraint_violation 있는 컨텍스트)에 대해 "anomaly_detection을
  1순위로 추천하는가" 같은 **정답 있는 케이스**로 모델별 정답률.
- **rationale 충실도**: facts 인용 여부 (환각 방어 통과율).
→ 결과: "e2b는 latency 60%↓이나 JSON 유효율 e4b 95% vs e2b 78%" 같은 **트레이드오프 표**.
   이게 "8GB에서 어떤 모델을 왜 쓰는가"의 데이터 기반 답이 된다.

---

## 5. 산출 인터페이스 (C-3: 결과 포맷, 팀원 질문 6 답)

### 5-1. 출력 스키마
- **in-band**: `logs/llm_inband.jsonl` (call_id, origin_ts_ns, model, *_duration, *_count)
- **out-of-band**: `logs/llm_resource.jsonl` (ts_ns, gpu_util, vram, temp, clock, per-proc, cpu, rss, swap)
- **/api/ps**: `logs/llm_ps.jsonl` (ts_ns, model, size_vram, size_total)
- **조인**: origin_ts_ns(in-band) ↔ ts_ns(샘플러) 시간 윈도우 조인 → 호출별 자원 프로파일.
- 최종 집계: **parquet** (분석 편의) 또는 SQLite. 시계열 + 호출별 요약 2테이블.

### 5-2. 재현성·관찰자효과 (팀원 질문 6)
- **관찰자효과 A/B**: 샘플러 on/off로 동일 배터리 측정 → 샘플러가 latency에 주는 영향 정량화(캘리브레이션).
  영향이 유의미하면 in-band(노이즈 0)를 1순위로, out-of-band는 자원 맥락으로만.
- **재현성**: 각 셀(모델×프롬프트) **N=7회, 중앙값 ± CV(변동계수)** 보고. CV 높으면(>15%) throttle/경합 의심.

### 5-3. 결과물 (포트폴리오/영업)
1. **트레이드오프 표**: 모델 3종 × (latency / VRAM 적재율 / tok/s / JSON유효율 / 추천정확도).
2. **최적화 전후 비교표**: 동일 모델, baseline vs 튜닝(num_ctx 등) → "latency N%↓, VRAM효율 N%↑".
3. **"하드웨어 제약 대응" 문서** (서사): 문제→측정→최적화→결정. (아래 §7)
4. (선택) **대시보드**: Grafana 연계 가능하나, 알파 단계는 jsonl→parquet→정적 차트로 충분.
   본진 UI에 "현재 세션 모델 리소스 상태"(size_vram/util) 표시는 별 태스크(설계자 1B-3e 후보).

### 5-4. 측정 순도 (팀원 질문 4 답)
- 프로파일러는 호스트 또는 별도 컨테이너. **26b CPU offload 레이어와 코어 경합 금지** → `taskset -c <유휴코어>`.
- **타 트래픽 사전 점검 프로토콜**: 측정 전 `ollama ps`로 다른 모델 미적재 확인 + `nvidia-smi`로 타 프로세스
  VRAM 0 확인. controlled 배터리(B)는 단독 점유 시간대에.

---

## 6. 실측 확정 필요 항목 (팀원 질문 5 답 + 추가)

측정 전 [추론]을 [확정]으로 바꿀 것:
- [ ] **e2b pull 후 적재율**: `ollama pull gemma4:e2b` → `ollama ps`로 GPU 100% 적재 확인. (7.2GB < 8GB 가설 검증)
- [ ] **26b CPU측 가중치가 RAM(27GB 가용)에 swap 없이 수용되는가**: 로드 후 `swap_used` 0 유지 확인.
      Swap 8GB 경계 감시 (샘플러에 포함됨). swap 발생 시 latency 급증 — 별도 표기.
- [ ] **CPU 코어 수 확정**: 팀원 자료 "16코어" vs 일반적 페어. `nproc`로 확정 → taskset 핀 코어 결정.
- [ ] **백엔드 컨테이너 pynvml 접근 가능 여부**: 안 되면 호스트 실행. (3-2 참조)
- [ ] **KV 캐시 동작**: 동일 프롬프트 반복 시 prompt_eval_count 변화 확인.

---

## 7. 결과 서사 (포트폴리오/영업 — 정직하게)

```
문제: 제조 현장은 제한적 단일 GPU(RTX 3070 8GB 등) 온프레미스가 일반적.
      gemma4 e4b·26b가 8GB VRAM을 초과 → CPU offload → 26b는 분석 1회 120초(실측).
측정: in-band(Ollama 메타) + out-of-band(pynvml/psutil) 프로파일러 자체 제작.
      관찰자효과 캘리브레이션 + N회 중앙값±CV로 재현성 확보.
발견: e2b만 8GB GPU 100% 적재. e4b는 42/43 레이어(일부 CPU). 26b는 대부분 CPU.
      모델 3종 속도↔품질 트레이드오프 정량화.
최적화: 동일 모델·하드웨어에서 num_ctx 축소 등으로 GPU 적재율↑ → latency N%↓ (baseline 대비, controlled).
결정: 데이터 기반 권장 — 8GB: e2b(GPU full)~e4b(균형) / 24GB+: 26b(MoE, 운영).
      "어떤 하드웨어에 어떤 모델·설정"을 실측으로 답하는 배포 가이드 확보.
부수효과: 운영 단계 리소스 모니터링 도구를 부산물로 확보 (STEP 3 공장 통합 시 재활용).
```
**금지**: "스트림 파이프라인" 같은 과장 명명. "N% 개선"은 controlled 측정(B) baseline 대비로만 주장.

---

## 8. 작업 순서 (팀원)
1. **환경 확정** (§6): e2b pull, nproc, pynvml 접근, swap 감시 셋업.
2. **훅 + 도구** (§3): 본진 generate에 PROFILE 훅(2줄) + 사이드카 샘플러 + /api/ps 폴러.
3. **passive 측정** (A): 알파 실트래픽 백그라운드 관측 → 운영 분포 baseline.
4. **controlled 배터리** (B): 고정 프롬프트 3종 × 3모델 × N=7 → latency/자원/품질.
5. **최적화 실험** (§4): H1~H4 가설별 튜닝 → 같은 배터리로 전후 비교.
6. **트레이드오프·전후 표 + 서사 문서** (§5·7).
7. 설계자에 회신: 통합 방식(ii) 확정 + 본진 훅 PR(PROFILE 가드) + 측정 결과.

---

## 부록 — 팀원 1차 자료 크로스체크 결과
| 팀원 항목 | 우리 검토 |
|---|---|
| 통합 (i) vs (ii) | **(ii) 채택.** call_id + origin_ts_ns 최소 훅으로 join. 본진 비침습. |
| in-band 1순위 + out-of-band 자원 | **동의.** prefill/decode 분리, pynvml in-process, subprocess 금지 모두 정확. |
| 모드 A(passive)+B(controlled) | **동의. B 필수.** N% 주장의 유일 근거. 알파 일정에 단독 시간대로. |
| 측정 순도(taskset 핀) | **동의.** 26b offload 코어 경합 방지. 타 트래픽 사전 점검 프로토콜 §5-4. |
| 26b GPU40/CPU60 [추론] | **실측 교정**: 63%/37% CPU/GPU. 26b 17GB(list)/20GB(load). |
| e2b 미설치 | **pull 필요 확정.** 8GB 유일 적재 가능 모델 — 기준점으로 필수. |
| 출력 스키마/캘리브레이션 | **동의.** jsonl→parquet, A/B 캘리브레이션, N회 중앙값±CV. |
| "KPI N% 개선" | **프레이밍 교정**(§0): 모델 비교 아닌 "동일조건 최적화 전후"가 N%의 정당한 분모. |
