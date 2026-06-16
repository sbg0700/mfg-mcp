"""scripts/measure.py — 측정 환경 PPT 데이터 생성.

축1(모델): gemma4:e4b vs gemma4:26b
축2(데이터 크기): timeseries csv 3종 (작은/중간/큰)
각 조합(2×3=6)으로 POST /api/execute(18001) → 전체 시간 + VRAM peak + n_rows/n_cols.

측정 항목:
- total_s        : 전체 시간 (time.perf_counter, inspect+plan+execute+validate 통합 1콜)
- vram_peak_mb   : 추론 중 nvidia-smi memory.used 폴링 peak
- vram_baseline  : 호출 직전 baseline
- n_rows/n_cols  : 실 lake 관통 확인 (응답 profile)
- status         : ok / timeout / error / oom (메시지)

실패·OOM도 기록 (26b CPU 오프로딩 느림 = PPT 데이터, D-100).
응답에 단계별 timing 필드 없음 → 전체 시간만 (확인됨).
"""
from __future__ import annotations
import csv
import json
import subprocess
import threading
import time
import urllib.request

BACKEND = "http://127.0.0.1:18001"
OLLAMA = "http://127.0.0.1:11434"

# 측정 대상 — 184 / 43k / 210k (안전 조합, 사용자 확정)
DATASETS = [
    {"id": "L1_injection_production", "modality": "timeseries", "label": "작은(184행)"},
    {"id": "L3_vacuum_pump",          "modality": "timeseries", "label": "중간(43k행)"},
    {"id": "L3_elevator_vibration",   "modality": "timeseries", "label": "큰(210k행)"},
]
MODELS = ["gemma4:e4b", "gemma4:26b"]

# 26b는 CPU 오프로딩으로 느림 (D-100) — 타임아웃 넉넉히
TIMEOUT_S = {"gemma4:e4b": 180, "gemma4:26b": 600}


def nvidia_used_mb() -> int | None:
    """현재 GPU memory.used (MB). 실패 시 None."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return None


class VramPoller(threading.Thread):
    """추론 중 백그라운드로 VRAM 폴링 → peak 기록."""
    def __init__(self, interval: float = 0.5):
        super().__init__(daemon=True)
        self.interval = interval
        self.peak = 0
        self._stop_evt = threading.Event()

    def run(self):
        while not self._stop_evt.is_set():
            u = nvidia_used_mb()
            if u is not None and u > self.peak:
                self.peak = u
            time.sleep(self.interval)

    def stop(self):
        self._stop_evt.set()


def ollama_warmup(model: str, keep_alive: str = "30m") -> float:
    """워밍업 — 모델을 메모리에 로드 (콜드 로딩 제거). keep_alive 길게 유지.
    짧은 프롬프트로 로드만. 반환: 워밍업(로딩) 소요 시간(s)."""
    t0 = time.perf_counter()
    try:
        body = json.dumps({
            "model": model, "prompt": "ok", "stream": False,
            "keep_alive": keep_alive,
        }).encode()
        req = urllib.request.Request(f"{OLLAMA}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=600).read()
    except Exception as e:
        print(f"  (워밍업 실패: {e})", flush=True)
    return time.perf_counter() - t0


def run_execute(dataset_id: str, modality: str, model: str, timeout: int) -> dict:
    """POST /api/execute. 반환: {ok, http_status, body or error}."""
    body = json.dumps({
        "dataset_id": dataset_id, "modality": modality, "model": model,
    }).encode()
    req = urllib.request.Request(f"{BACKEND}/api/execute", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"ok": True, "http_status": r.status, "body": json.loads(r.read())}
    except urllib.error.HTTPError as e:
        return {"ok": False, "http_status": e.code, "error": e.read().decode()[:300]}
    except Exception as e:
        return {"ok": False, "http_status": None, "error": f"{type(e).__name__}: {e}"}


def measure_one(dataset: dict, model: str) -> dict:
    """단일 조합 측정."""
    ds_id, modality, label = dataset["id"], dataset["modality"], dataset["label"]
    timeout = TIMEOUT_S[model]
    print(f"\n[측정] {model} × {ds_id} ({label}) ... timeout={timeout}s", flush=True)

    baseline = nvidia_used_mb() or 0
    poller = VramPoller(interval=0.5)
    poller.start()

    t0 = time.perf_counter()
    res = run_execute(ds_id, modality, model, timeout)
    total_s = time.perf_counter() - t0

    poller.stop()
    poller.join(timeout=2)
    vram_peak = poller.peak

    row = {
        "model": model, "dataset": ds_id, "label": label,
        "total_s": round(total_s, 2),
        "vram_baseline_mb": baseline,
        "vram_peak_mb": vram_peak,
        "vram_delta_mb": vram_peak - baseline,
        "n_rows": None, "n_cols": None,
        "validation_passed": None, "status": "",
    }

    if res["ok"]:
        b = res["body"]
        prof = b.get("profile") or {}
        val = b.get("validation") or {}
        row["n_rows"] = prof.get("n_rows")
        row["n_cols"] = prof.get("n_cols")
        row["validation_passed"] = val.get("passed")
        row["status"] = "ok"
    else:
        msg = (res.get("error") or "")[:120]
        if res["http_status"] is None and "timed out" in msg.lower():
            row["status"] = f"timeout(>{timeout}s)"
        else:
            row["status"] = f"error[{res['http_status']}]:{msg}"

    print(f"  → total={row['total_s']}s  vram_peak={vram_peak}MB "
          f"(Δ{row['vram_delta_mb']})  n_rows={row['n_rows']}  status={row['status']}",
          flush=True)
    return row


def main():
    print("=" * 70)
    print("측정 시작 (WARM) — 6 조합 (e4b/26b × 184/43k/210k)")
    print("=" * 70)
    rows = []
    for model in MODELS:
        # ★워밍업: 본 측정 전 모델 로드(콜드 로딩 제거) + keep_alive 30m 유지
        w_s = ollama_warmup(model, keep_alive="30m")
        print(f"\n[워밍업] {model} 로드 완료 — {round(w_s, 2)}s (이후 측정은 콜드 로딩 제거)",
              flush=True)
        for ds in DATASETS:
            # unload 안 함 — 모델 메모리 유지(warm 측정). keep_alive로 연속 유지.
            rows.append(measure_one(ds, model))

    # CSV 출력
    out_csv = "/tmp/measure_results_warm.csv"
    fields = ["model", "dataset", "label", "n_rows", "n_cols", "total_s",
              "vram_baseline_mb", "vram_peak_mb", "vram_delta_mb",
              "validation_passed", "status"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # 콘솔 요약
    print("\n" + "=" * 70)
    print("측정 완료 — 요약")
    print("=" * 70)
    hdr = f"{'model':<12} {'dataset':<24} {'rows':>8} {'total_s':>9} {'vram_peak':>10} {'status':<14}"
    print(hdr)
    print("-" * 70)
    for r in rows:
        print(f"{r['model']:<12} {r['dataset']:<24} {str(r['n_rows']):>8} "
              f"{str(r['total_s']):>9} {str(r['vram_peak_mb']):>10} {r['status']:<14}")
    print(f"\nCSV: {out_csv}")


if __name__ == "__main__":
    main()
