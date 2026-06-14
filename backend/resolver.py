"""
backend/resolver.py — catalog.get 데이터 seam: datalake_id → 실파일 경로 (DL-5b, D-203).

엔진(executor)이 datalake_id를 파일명으로 직접 해석하던 것을, catalog(PG)의 data_path를
단일 권위로 삼아 실파일을 locate 한다. BLUEPRINT §1.5 "데이터→엔진 경계의 단일 해석점".

흐름: catalog.get(id)(PG) → {data_path(=data/lake/{id}/ 디렉터리), modality}
      → timeseries/order(csv): 디렉터리 내 *.csv glob → 단일 실파일 경로.

fail-loud (silent fallback 금지, D-192):
  - entry 없음 / data_path 비어있음 / 디렉터리 부재 / CSV 0개 → FileNotFoundError
  - CSV 복수(모호) → ValueError (임의 선택 금지 — 5b=단일파일 클린셋 전제)

배치: agents 밖(backend/) — 엔진(forbidden-zone)을 건드리지 않는 seam 배선부.
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


async def resolve_dataset_path(datalake_id: str) -> str:
    """datalake_id → catalog data_path 디렉터리 → 단일 실 CSV 경로(존재 보장).

    catalog(PG)의 data_path가 데이터 위치의 단일 권위. 디렉터리 내 *.csv 를 glob 해
    정확히 1개일 때만 그 경로를 반환한다. 어떤 모호함도 raise(조용한 추측 금지).
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

    matches = sorted(glob.glob(os.path.join(directory, "*.csv")))
    if not matches:
        raise FileNotFoundError(
            f"CSV 부재: {directory} (id={datalake_id}, modality={entry.get('modality')})"
        )
    if len(matches) > 1:
        names = [os.path.basename(m) for m in matches]
        raise ValueError(
            f"복수 CSV 모호({len(matches)}): {directory} → {names} "
            f"(5b=단일파일 클린셋 전제 — 임의 선택 금지)"
        )
    return matches[0]
