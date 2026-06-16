"""tests/test_seam_reach_dl5b.py — catalog.get 데이터 seam reach 실증 (DL-5b, D-203).

(1) resolve_dataset_path: catalog(throwaway PG)의 data_path → 실 data/lake CSV locate (fail-loud).
(2) reach: resolve → executor.execute(data_path=...) 가 실 KAMP(1628행×29컬럼)를 적재함을
    backup parquet 형상으로 단정 — synthetic file-not-found 아님(catalog→engine seam 관통 증명).

실 KAMP = data/lake/L1_mct_tool_manage/ (gitignore·디스크 존재). throwaway PG(D-182)에 entry seed.
"""
from __future__ import annotations

import os
import pathlib
import sys

import pandas as pd

# conftest 는 backend/·tools/ 만 sys.path 에 넣는다. agents/executor flat 경로 추가.
_REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (_REPO / "agents" / "executor",):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import executor                              # noqa: E402  (agents/executor — ROOT/harness self-bootstrap)
from resolver import resolve_dataset_path    # noqa: E402  (backend — conftest path)

_REPRESENTATIVE = "L1_mct_tool_manage"
_EXPECT_ROWS = 1628   # 실 KAMP 데이터행 (헤더 제외; seam-1 보고 wc -l = 1629)
_EXPECT_COLS = 29     # gdatetime … A_c_a


def _seed_entry() -> dict:
    """대표셋 entry — data_path 는 실 data/lake 디렉터리(기본 규칙 그대로)."""
    return {
        "datalake_id": _REPRESENTATIVE,
        "source": "kamp",
        "name": "MCT 공구 관리",
        "modality": "timeseries",
        "data_path": f"data/lake/{_REPRESENTATIVE}/",
    }


async def test_resolve_dataset_path_locates_real_kamp(cat):
    """catalog data_path → 실 CSV 단일 경로 반환·존재 (fail-loud resolver 정상 경로)."""
    await cat.upsert_entry(_seed_entry())
    path = await resolve_dataset_path(_REPRESENTATIVE)
    assert os.path.isfile(path), f"resolve 결과 파일 부재: {path}"
    assert path.endswith(".csv"), f"CSV 아님: {path}"
    assert _REPRESENTATIVE in os.path.basename(path)  # 긴 KAMP 파일명에 datalake_id 포함


async def test_seam_reach_executes_real_kamp(cat):
    """resolve → execute(data_path=...) 가 실 KAMP(1628×29) 적재 — synthetic not-found 아님."""
    await cat.upsert_entry(_seed_entry())
    path = await resolve_dataset_path(_REPRESENTATIVE)

    # 최소 valid plan(빈 steps) — seam(load→backup)만 격리 검증, compute 무관.
    plan = {"dataset_id": _REPRESENTATIVE, "steps": []}
    res = await executor.execute(plan, data_path=path, modality="timeseries")

    assert "error" not in res, f"execute 오류(seam 미관통?): {res.get('error')}"
    backup = res.get("backup_path")
    assert backup, "backup_path 부재"
    df = pd.read_parquet(backup)
    assert df.shape == (_EXPECT_ROWS, _EXPECT_COLS), (
        f"실 KAMP 형상 불일치: {df.shape} != ({_EXPECT_ROWS}, {_EXPECT_COLS}) "
        f"— synthetic not-found / 오로드 의심"
    )
