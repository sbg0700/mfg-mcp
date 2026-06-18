"""
backend/resolver.py — catalog.get 데이터 seam: datalake_id → 실파일 경로 (DL-5b, D-203).

엔진(executor)이 datalake_id를 파일명으로 직접 해석하던 것을, catalog(PG)의 data_path를
단일 권위로 삼아 실파일을 locate 한다. BLUEPRINT §1.5 "데이터→엔진 경계의 단일 해석점".

흐름: catalog.get(id)(PG) → {data_path(=data/lake/{id}/ 디렉터리), modality}
      → timeseries/order(csv): 디렉터리 내 *.csv glob
          · 1개 → 그 경로
          · 복수(동일 스키마) → 전부 concat 한 병합 캐시(_merged_shards.csv) 경로 (anti-silent: 전부 사용)
          · 복수(스키마 상이) → ValueError (오병합 금지)

fail-loud (silent fallback 금지, D-192):
  - entry 없음 / data_path 비어있음 / 디렉터리 부재 / CSV 0개 → FileNotFoundError
  - 멀티샤드 스키마 불일치 → ValueError (임의 선택/오병합 금지)

배치: agents 밖(backend/) — 엔진(forbidden-zone)을 건드리지 않는 seam 배선부.
멀티샤드 concat 도 이 seam 에서 수행(엔진/MCP 는 단일 경로만 받음 — 계약 불변, 회귀 0).
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent  # repo 루트 (backend/의 부모)
if str(_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(_ROOT / "backend"))

import catalog  # noqa: E402

# 멀티샤드 병합 캐시 — 레이크(팀 소유·읽기전용)가 아닌 '쓰기 가능 파생' 디렉터리. gitignore.
_MERGE_CACHE_DIR = _ROOT / "data" / "_shard_merge"


def _read_csv_any_enc(path: str):
    """인코딩 흡수 로드 (executor 와 동일 후보 순서: utf-8-sig → cp949 → latin1)."""
    import pandas as pd
    for cand in ("utf-8-sig", "cp949", "latin1"):
        try:
            return pd.read_csv(path, encoding=cand, low_memory=False)
        except (UnicodeDecodeError, LookupError):
            continue
    return pd.read_csv(path, encoding="latin1", low_memory=False)


def _merge_shards(shards: list[str], datalake_id: str) -> str:
    """동일 스키마 샤드 전부 concat → 병합 캐시 경로. 스키마 상이면 fail-loud.
    캐시: 병합본이 모든 샤드보다 최신이면 재사용(재-concat 회피). 레이크 무접촉(쓰기는 캐시 디렉터리)."""
    import pandas as pd
    _MERGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    merged = str(_MERGE_CACHE_DIR / f"{datalake_id}.csv")
    if os.path.exists(merged) and all(
            os.path.getmtime(merged) >= os.path.getmtime(s) for s in shards):
        return merged

    frames, headers = [], []
    for s in shards:
        df = _read_csv_any_enc(s)
        frames.append(df)
        headers.append(tuple(df.columns))
    if len(set(headers)) != 1:                       # 실제 스키마 상이 → 오병합 금지
        raise ValueError(
            f"멀티샤드 스키마 불일치({len(shards)}): {datalake_id} → 헤더 상이, concat 불가 "
            f"(파일별 컬럼셋 확인 필요)")
    full = pd.concat(frames, ignore_index=True)      # 행 적층(전부 사용, 누락 0)
    full.to_csv(merged, index=False, encoding="utf-8")
    return merged


async def resolve_dataset_path(datalake_id: str) -> str:
    """datalake_id → catalog data_path 디렉터리 → 실 CSV 경로(존재 보장).

    catalog(PG)의 data_path가 데이터 위치의 단일 권위. 디렉터리 내 *.csv 를 glob:
    1개면 그 경로, 동일 스키마 복수면 concat 병합 경로(전부 사용), 스키마 상이면 raise.
    """
    entry = await catalog.get(datalake_id)
    if entry is None:
        raise FileNotFoundError(f"datalake entry 없음: {datalake_id}")
    data_path = entry.get("data_path")
    if not data_path:
        raise FileNotFoundError(f"data_path 비어있음(entry 손상): {datalake_id}")

    directory = data_path if os.path.isabs(data_path) else os.path.join(_ROOT, data_path)
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"data_path 디렉터리 부재: {directory} (id={datalake_id})")

    matches = sorted(glob.glob(os.path.join(directory, "*.csv")))   # 병합 캐시는 레이크 밖 → 제외 불필요
    if not matches:
        raise FileNotFoundError(
            f"CSV 부재: {directory} (id={datalake_id}, modality={entry.get('modality')})"
        )
    if len(matches) == 1:
        return matches[0]                            # 단일 파일 — 현행(회귀 0)
    return _merge_shards(matches, datalake_id)        # 동일스키마 멀티샤드 concat
