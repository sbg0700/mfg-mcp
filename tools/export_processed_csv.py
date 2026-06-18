#!/usr/bin/env python3
"""tools/export_processed_csv.py — processed/backup parquet → CSV (전후 비교 generic export).

레이크 무접촉. 출력 = data/_export/{id}__before.csv (원본 backup) + {id}__after.csv (processed).
remove_outlier 등 행 제거가 무슨 행을 뺐는지 CSV 한 쌍으로 확인.

사용: PROCESSED_ROOT=.. python tools/export_processed_csv.py <datalake_id>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
PROCESSED = Path(os.environ.get("PROCESSED_ROOT", str(REPO / "data" / "processed")))
EXPORT = REPO / "data" / "_export"


def export(datalake_id: str) -> dict:
    EXPORT.mkdir(parents=True, exist_ok=True)
    out: dict[str, tuple[str, int]] = {}
    for kind, suffix in (("before", "__backup.parquet"), ("after", "__processed.parquet")):
        p = PROCESSED / f"{datalake_id}{suffix}"
        if not p.exists():
            print(f"  [{kind}] parquet 없음: {p} (파이프라인 실행 후 생성)")
            continue
        df = pd.read_parquet(p)
        csv = EXPORT / f"{datalake_id}__{kind}.csv"
        df.to_csv(csv, index=False, encoding="utf-8")
        out[kind] = (str(csv), len(df))
        print(f"  [{kind}] {csv} — {len(df)}행")
    if "before" in out and "after" in out:
        diff = out["before"][1] - out["after"][1]
        print(f"  Δ 행수: {out['before'][1]} → {out['after'][1]} (제거 {diff})")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: export_processed_csv.py <datalake_id>")
        sys.exit(1)
    export(sys.argv[1])
