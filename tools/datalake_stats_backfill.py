#!/usr/bin/env python3
"""
tools/datalake_stats_backfill.py — (b) 관측 min/max 통계 백필.

목적: datalake.columns 의 숫자 scalar(integer/float) 컬럼에 대해 실데이터 파일에서
      관측 min/max 를 계산해 stat_min/stat_max 에 기록한다.
      → 제약 폼이 "관측 범위 X~Y" 안내(데이터 사실)를 표시. 규격 제안 아님(D-43 무위반).

설계:
  - 재사용: 헤더 파싱 = tools/datalake_ingest.read_header + _uniquify_headers(카탈로그 컬럼명과 동일 산물,
    __dup/__unnamed/멀티라인 헤더 일관). 값 = pandas. (재발명 0)
  - 레이크 파일은 적재 시 utf-8 정규화됨(entry.encoding 은 소스 인코딩) → utf-8-sig 로 읽음.
  - 이름→파일위치 매핑: U=_uniquify_headers(read_header) 가 파일 물리순서이며 카탈로그 name 과 일치.
    pandas 는 header=0 로 읽고 컬럼명을 U 로 덮어써 카탈로그 name 으로 직접 접근(__dup pandas .N 불일치 회피).
  - 멱등: UPDATE(재실행 동일값). fail-loud: CSV 0/복수헤더불일치/컬럼수불일치/name 부재 시 raise(silent skip 금지).
  - 다중 CSV(동일 스키마 shard) = 위치 concat.

사용:
  PGHOST=.. PGPORT=.. PGUSER=.. PGPASSWORD=.. PGDATABASE=.. \
    python tools/datalake_stats_backfill.py [--vid module_3_polymer_electronic] [--dry-run]
  (이번 범위: 라인3. 전체 백필은 --vid 생략으로 후속.)
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import os
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import catalog  # noqa: E402
from datalake_ingest import read_header, _uniquify_headers  # noqa: E402

NUMERIC_DTYPES = {"integer", "float"}
LAKE_CODEC = "utf-8-sig"   # 레이크 파일은 utf-8 정규화(적재 산물). BOM 있으면 제거.


def _resolve_csvs(data_path: str) -> list[Path]:
    """data_path 디렉터리의 *.csv (1개 이상). 0개면 fail-loud."""
    directory = data_path if os.path.isabs(data_path) else str(REPO / data_path)
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"data_path 디렉터리 부재: {directory}")
    matches = sorted(glob.glob(os.path.join(directory, "*.csv")))
    if not matches:
        raise FileNotFoundError(f"CSV 0개: {directory}")
    return [Path(m) for m in matches]


def _load_named(paths: list[Path]) -> pd.DataFrame:
    """CSV(들)을 읽어 컬럼명을 U(카탈로그 정렬)로 덮어쓴 DataFrame 반환(shard concat).
    fail-loud: pandas 컬럼수 != 헤더수 / shard 헤더 불일치."""
    frames, headers = [], []
    for p in paths:
        u, _ = _uniquify_headers(read_header(p, LAKE_CODEC))
        df = pd.read_csv(p, header=0, encoding=LAKE_CODEC, encoding_errors="replace",
                         on_bad_lines="skip", low_memory=False)
        if df.shape[1] != len(u):
            raise ValueError(f"{p.name}: pandas 컬럼수 {df.shape[1]} != 헤더수 {len(u)} (위치정렬 깨짐)")
        df.columns = u
        frames.append(df)
        headers.append(tuple(u))
    if len(set(headers)) != 1:
        raise ValueError(f"shard 헤더 불일치: {[p.name for p in paths]}")
    return pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]


async def backfill(vid: str | None, dry: bool) -> None:
    pool = await catalog.get_pool()
    where = "WHERE vid = $1" if vid else ""
    args = [vid] if vid else []
    entries = await pool.fetch(
        f"SELECT datalake_id, data_path FROM datalake.entries {where} ORDER BY datalake_id", *args)

    total_filled = 0
    all_nan: list[str] = []
    print(f"== 백필 시작 (vid={vid or 'ALL'}, dry={dry}) — {len(entries)} 데이터셋 ==")
    for e in entries:
        did, dp = e["datalake_id"], e["data_path"]
        cols = await pool.fetch(
            "SELECT name, dtype, column_kind FROM datalake.columns WHERE datalake_id = $1", did)
        names = [c["name"] for c in cols
                 if c["column_kind"] == "scalar" and c["dtype"] in NUMERIC_DTYPES]
        if not names:
            print(f"  [{did}] 숫자 scalar 0 — skip")
            continue

        df = _load_named(_resolve_csvs(dp))
        miss = [n for n in names if n not in df.columns]
        if miss:                                    # fail-loud (silent skip 금지)
            raise KeyError(f"{did}: 카탈로그 컬럼이 파일에 없음(매핑 실패): {miss}")

        filled = 0
        for n in names:
            vals = pd.to_numeric(df[n], errors="coerce")
            mn, mx = vals.min(), vals.max()
            if pd.isna(mn) or pd.isna(mx):          # 전부 비숫자 → 통계 없음(명시 기록, silent 아님)
                all_nan.append(f"{did}.{n}")
                continue
            if not dry:
                await pool.execute(
                    "UPDATE datalake.columns SET stat_min = $1, stat_max = $2 "
                    "WHERE datalake_id = $3 AND name = $4",
                    float(mn), float(mx), did, n)
            filled += 1
        total_filled += filled
        print(f"  [{did}] 숫자 scalar {len(names)} → 채움 {filled}"
              + (f" / 통계없음 {len(names) - filled}" if filled < len(names) else ""))

    print(f"\n== 완료: 채운 컬럼 {total_filled}"
          + (f" / 통계없음(전부비숫자) {len(all_nan)}: {all_nan}" if all_nan else "") + " ==")
    if dry:
        print("   (--dry-run: DB write 0)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vid", default=None, help="대상 vid (생략=전체). 이번 범위=module_3_polymer_electronic")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    asyncio.run(backfill(a.vid, a.dry_run))


if __name__ == "__main__":
    main()
