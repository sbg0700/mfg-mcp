"""tests/test_e2e_dl5b.py — 결정론 전처리 e2e 게이트 (DL-5b-e2e, D-202 개정).

체인: profile fixture(수기·실데이터 충실) → planner.plan(LLM stub→결정론) → resolve_dataset_path
      → executor.execute(data_path=실 KAMP) → validator.validate.
게이트 = 회귀 보호(데이터층 재설계가 엔진 실데이터 처리를 깨뜨렸나) = 결정론 경로.
ML/EDA·live smoke = 게이트 밖(capstone 이월). 정확값 단정 금지 — 존재·형상·정합·재현만(D-202).

★ profile fixture 는 실 CSV(data/lake/L1_mct_tool_manage/...csv) pandas 실측 기반(날조 금지):
  1628행×29컬럼, nulls=0·mixed/masking=0(전 컬럼 클린) → deterministic_flags=[] →
  candidate=compute_stats(L1)만 → 무승인 all_done 경로.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd

# conftest 는 backend/·tools/ 만 sys.path 에. 엔진 flat 모듈 + repo 루트 추가.
_REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (_REPO, _REPO / "agents" / "planner", _REPO / "agents" / "executor",
           _REPO / "agents" / "validator"):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import executor                              # noqa: E402
import planner                               # noqa: E402
import validator                             # noqa: E402
import llm                                   # noqa: E402  (backend — stub 대상)
from harness import lineage                  # noqa: E402
from resolver import resolve_dataset_path    # noqa: E402

_REP = "L1_mct_tool_manage"
_ROWS = 1628
_COLS = 29

# 실 CSV pandas 실측 (DL-5b-e2e STEP1, 날조 금지): dtype·null_count 모두 실측값.
# 전 컬럼 nulls=0, mixed/masking=0 → flags=[] (utf-8-sig 비플래그·결측0·혼재0·불균형0).
_REAL_COLUMNS = [
    ("gdatetime", "object"), ("fcycleTime", "int64"), ("fspindleRPM1", "int64"),
    ("fspindleTroq1", "int64"), ("ftoolNum", "int64"), ("gadc2", "float64"),
    ("gadc3", "float64"), ("gadc4", "float64"), ("gadc5", "float64"), ("gmv", "float64"),
    ("gma", "float64"), ("gmactP", "float64"), ("gmractP", "float64"), ("gmapv", "float64"),
    ("gmpf", "float64"), ("gmfeq", "float64"), ("gmtemp", "int64"), ("day", "object"),
    ("count", "int64"), ("T_change", "int64"), ("T_current", "int64"),
    ("Inspection_F", "int64"), ("TRT_P", "float64"), ("ATRT", "float64"),
    ("T_start", "int64"), ("c_v", "float64"), ("c_a", "float64"),
    ("A_c_v", "float64"), ("A_c_a", "float64"),
]


def _build_profile() -> dict:
    """inspect 출력 형태(plain dict)와 동일한 수기 profile — 실측 충실."""
    return {
        "dataset_id": _REP,
        "modality": "timeseries",
        "encoding": "utf-8-sig",
        "n_rows": _ROWS,
        "n_cols": _COLS,
        "columns": [{"name": n, "dtype": d, "null_count": 0} for n, d in _REAL_COLUMNS],
        "semantic_groups": {},
        "sample_rows": [],
        "deterministic_flags": [],   # 클린셋 — flag 트리거 0
        "llm_interpretation": {},    # LLM 미관여(게이트 결정론)
    }


def _seed_entry() -> dict:
    return {
        "datalake_id": _REP, "source": "kamp", "name": "MCT 공구 관리",
        "modality": "timeseries", "data_path": f"data/lake/{_REP}/",
    }


async def _stub_generate(*args, **kwargs) -> str:
    """LLM 결정론화 — _llm_failed 마커 반환 → planner graceful 폴백(candidate 결정론 순서)."""
    return json.dumps({"_llm_failed": True, "error": "e2e deterministic stub"})


async def _run_chain(profile: dict, path: str):
    """profile → plan → execute(실 KAMP) → validate. lineage 는 이 실행분만 반영(clear 선행)."""
    lineage._STORE.clear()
    plan = await planner.plan(profile, constraints=None)
    execu = await executor.execute(plan, data_path=path)
    valid = await validator.validate(execu, plan=plan, profile=profile)
    return plan, execu, valid


# ─────────────────────────────────────────────────────────────────────────────
async def test_e2e_completion_deterministic(cat, monkeypatch):
    """전처리 완주 — 예외0·산출물·형상·lineage 정합·validate 통과 (존재/형상/정합만)."""
    monkeypatch.setattr(llm, "generate", _stub_generate)
    await cat.upsert_entry(_seed_entry())
    profile = _build_profile()
    path = await resolve_dataset_path(_REP)

    plan, execu, valid = await _run_chain(profile, path)

    # (1) 예외 0(도달=무예외) + error 키 없음
    assert "error" not in execu, f"execute error: {execu.get('error')}"
    # (2) 클린셋 → plan = compute_stats(L1)만 → 무승인
    ops = [s["operation"] for s in plan["steps"]]
    assert ops == ["compute_stats"], f"예상 외 plan(클린셋 가정 위반): {ops}"
    assert plan["requires_approval"] is False
    # (3) 무승인 완주
    assert execu["all_done"] is True, execu
    assert execu["pending_approvals"] == []
    # (4) 산출물 존재 + 형상
    bdf = pd.read_parquet(execu["backup_path"])
    pdf = pd.read_parquet(execu["output_path"])
    assert bdf.shape == (_ROWS, _COLS), f"backup 형상: {bdf.shape}"     # 원본 보존
    assert pdf.shape[0] == _ROWS, f"processed 행: {pdf.shape}"          # compute_stats=행 보존
    # (5) anti-silent: backup 컬럼 = fixture(=실데이터) 정합 — 날조/오로드 차단
    assert list(bdf.columns) == [c["name"] for c in profile["columns"]]
    # (6) silent drop 0: backup 행 == processed 행
    assert bdf.shape[0] == pdf.shape[0]
    # (7) lineage non-empty + done step 수 정합 (모든 변경이 기록됨)
    chain = lineage.get_chain(_REP)
    done = [s for s in execu["results"] if s["status"] == "done"]
    assert len(chain) >= 1, "lineage 비어있음"
    assert len(chain) == len(done), f"lineage {len(chain)} != done {len(done)}"
    # (8) validate 완주 + 컴플라이언스 high 위반 0
    assert valid["passed"] is True, valid
    assert valid["checks"]["compliance"] is True
    assert valid["n_high"] == 0, valid["issues"]


async def test_e2e_reproducible(cat, monkeypatch):
    """체인 2회 — plan steps + execu 결정론 필드(status/형상) 동일 (비결정 누출 0)."""
    monkeypatch.setattr(llm, "generate", _stub_generate)
    await cat.upsert_entry(_seed_entry())
    profile = _build_profile()
    path = await resolve_dataset_path(_REP)

    def _sig(plan, execu):
        return (
            tuple((s["operation"], s["order"], s["permission_level"], s.get("target_column"))
                  for s in plan["steps"]),
            tuple((s["operation"], s["status"]) for s in execu["results"]),
            execu["all_done"],
            pd.read_parquet(execu["backup_path"]).shape,
            pd.read_parquet(execu["output_path"]).shape,
        )

    plan1, execu1, _ = await _run_chain(profile, path)
    plan2, execu2, _ = await _run_chain(profile, path)
    assert _sig(plan1, execu1) == _sig(plan2, execu2), (
        f"비결정 누출:\n{_sig(plan1, execu1)}\n!=\n{_sig(plan2, execu2)}"
    )
