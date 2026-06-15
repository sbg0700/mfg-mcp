"""tests/test_e2e_dl5c1.py — DL-5c-1 프로덕션 execute seam 게이트 (D-204).

체인: main.execute_endpoint(/api/execute 프로덕션 핸들러) 실태우기
  → 내부 _resolve_seam_path(catalog data_path) → executor.execute(data_path=실 lake)
  → csv 3 모달리티(timeseries/order/event-log) 실 KAMP 적재·완주.

stub: inspect=실 파일 실측 profile(flags=[] — encoding/header/mixed/imbalance 챌린지는
  5c-2/D-205 범위 밖, fill_missing·compute_stats만), llm=결정론 폴백(planner 후보순서).
게이트 본질(D-204) = "프로덕션이 실 PG lake를 id 기준으로 읽고 전 과정 완주". 정확값 금지
(D-202): 존재·형상·정합·재현(2회)만. throwaway PG(D-182), 라이브 쓰기 0.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd

_REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (_REPO, _REPO / "backend", _REPO / "agents" / "inspector",
           _REPO / "agents" / "planner", _REPO / "agents" / "executor",
           _REPO / "agents" / "validator"):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import main                                    # noqa: E402  (backend — 프로덕션 핸들러)
import inspector                               # noqa: E402
import planner                                 # noqa: E402
import executor                                # noqa: E402
import llm                                     # noqa: E402
from harness import lineage                    # noqa: E402
from resolver import resolve_dataset_path      # noqa: E402

# csv 3 모달리티 대표 (실 data/lake) — 클린(mct, null 0)·결측(order/ict, fill_missing)
_REPS = [
    ("L1_mct_tool_manage", "timeseries", "MCT 공구 관리"),
    ("order_planning", "order", "주문 계획"),
    ("L4_ict_inspection", "event-log", "ICT 검사"),
]


def _seed_entry(did: str, modality: str, name: str) -> dict:
    return {"datalake_id": did, "source": "kamp", "name": name,
            "modality": modality, "data_path": f"data/lake/{did}/"}


def _load_real(did: str, modality: str, path: str):
    """실 파일 로드 (profile 실측용). event-log는 executor 로더 재사용(seam 동형)."""
    if modality == "event-log":
        df, _p, _n = executor._load_eventlog(did, path)
        return df
    for enc in ("utf-8-sig", "cp949", "latin1"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except (UnicodeDecodeError, LookupError):
            continue
    return pd.read_csv(path)


def _profile_from_real(did: str, modality: str, path: str) -> dict:
    """Inspector 출력 형태 profile — 실 파일 실측(columns name/dtype/null_count, 날조 0).
    flags=[]: 5c-1 범위는 데이터 seam — fill_missing(결측)·compute_stats만 트리거."""
    df = _load_real(did, modality, path)
    cols = [{"name": str(c), "dtype": str(df[c].dtype), "null_count": int(df[c].isna().sum())}
            for c in df.columns]
    return {"dataset_id": did, "modality": modality, "n_rows": int(df.shape[0]),
            "n_cols": int(df.shape[1]), "columns": cols, "semantic_groups": {},
            "sample_rows": [], "deterministic_flags": [], "llm_interpretation": {}}


async def _stub_generate(*_a, **_k) -> str:
    """LLM 결정론화 — _llm_failed 마커 → planner graceful 폴백(candidate 결정론 순서)."""
    return json.dumps({"_llm_failed": True, "error": "5c-1 deterministic stub"})


async def _run_one(cat, monkeypatch, did: str, modality: str, name: str):
    """프로덕션 execute_endpoint 실태우기 → (result, plan)."""
    await cat.upsert_entry(_seed_entry(did, modality, name))
    path = await resolve_dataset_path(did)                 # ★프로덕션 seam과 동일 해석점
    profile = _profile_from_real(did, modality, path)

    async def _stub_inspect(dataset_id, model=None, modality="timeseries"):  # noqa: ARG001
        return profile
    monkeypatch.setattr(inspector, "inspect", _stub_inspect)
    monkeypatch.setattr(llm, "generate", _stub_generate)

    # plan 선산출 → L2 step_key 승인 목록(프로덕션 승인 시뮬). 핸들러 내부 plan과 동일(결정론).
    plan = await planner.plan(profile, constraints=None)
    approved = [s["step_key"] for s in plan["steps"]
                if s["permission_level"] in ("L2", "L3")]

    lineage._STORE.clear()
    req = main.ExecuteReq(dataset_id=did, modality=modality, approved_keys=approved)
    result = await main.execute_endpoint(req)              # ★프로덕션 핸들러 실태우기
    return result, plan


# ─────────────────────────────────────────────────────────────────────────────
async def test_seam_completion_3_modalities(cat, monkeypatch):
    """csv 3 모달리티 — 프로덕션 핸들러가 실 lake 읽고 완주 (존재·형상·정합만)."""
    for did, modality, name in _REPS:
        result, plan = await _run_one(cat, monkeypatch, did, modality, name)

        # (1) execution 도달 (pre_validation blocking 아님) + 오류 0
        execu = result["execution"]
        assert execu is not None, f"{did}: execution None ({result.get('note')})"
        assert "error" not in execu, f"{did}: execute error {execu.get('error')}"
        # (2) 무승인 완주 (L2는 사전 승인) — 실 lake not-found 면 error 로 빠졌을 것
        assert execu["all_done"] is True, f"{did}: all_done False, pending={execu['pending_approvals']}"
        assert execu["pending_approvals"] == []
        # (3) 산출물 존재 + 실 데이터 적재(빈 backup=synthetic not-found 의심)
        bdf = pd.read_parquet(execu["backup_path"])
        pdf = pd.read_parquet(execu["output_path"])
        assert bdf.shape[0] > 0, f"{did}: 빈 backup — 실 lake 미로드 의심"
        # (4) silent drop 0 — 행 보존(fill_missing/compute_stats=행 불변)
        assert bdf.shape[0] == pdf.shape[0], f"{did}: silent drop {bdf.shape} -> {pdf.shape}"
        # (5) lineage 정합 — done step 마다 1건 기록
        chain = lineage.get_chain(did)
        done = [s for s in execu["results"] if s["status"] == "done"]
        assert len(chain) >= 1, f"{did}: lineage 비어있음"
        assert len(chain) == len(done), f"{did}: lineage {len(chain)} != done {len(done)}"
        # (6) plan 구성 — 클린셋=compute_stats만, 결측셋=fill_missing 포함(seam이 실 결측 처리)
        ops = {s["operation"] for s in plan["steps"]}
        assert "compute_stats" in ops, f"{did}: compute_stats 누락 {ops}"
        if did != "L1_mct_tool_manage":
            assert "fill_missing" in ops, f"{did}: 결측셋인데 fill_missing 없음 {ops}"


async def test_seam_reproducible(cat, monkeypatch):
    """event-log(fill_missing 케이스) 2회 — plan steps + execution 결정론 필드 동일."""
    did, modality, name = _REPS[2]

    def _sig(result, plan):
        e = result["execution"]
        return (
            tuple((s["operation"], s["permission_level"], s.get("target_column"))
                  for s in plan["steps"]),
            tuple((s["operation"], s["status"]) for s in e["results"]),
            e["all_done"],
            pd.read_parquet(e["backup_path"]).shape,
            pd.read_parquet(e["output_path"]).shape,
        )

    r1, p1 = await _run_one(cat, monkeypatch, did, modality, name)
    r2, p2 = await _run_one(cat, monkeypatch, did, modality, name)
    assert _sig(r1, p1) == _sig(r2, p2), (
        f"비결정 누출:\n{_sig(r1, p1)}\n!=\n{_sig(r2, p2)}"
    )
