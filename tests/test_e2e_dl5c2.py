"""tests/test_e2e_dl5c2.py — DL-5c-2 inspect/MCP 프로덕션 seam 게이트 (D-206).

체인: main.execute_endpoint(프로덕션 핸들러) 실태우기 → 내부 _resolve_seam_path(catalog data_path)
  → inspect(data_path) → MCP tools(data_path=실 lake) → plan → execute(data_path) → validate.
  csv 3 모달리티(timeseries/order/event-log) full end-to-end (5c-1은 inspect=stub였음).

MCP HTTP 실기동=live smoke(명선) → 게이트는 inspector._mcp_get 을 in-process MCP tools 호출로
우회(HTTP 계층만 우회, MCP 데이터 로직=실행, 실 lake data_path 읽기 검증). llm=결정론 stub.
정확값 금지(D-202): 존재·형상·정합·재현(2회)만. image=5c-3(범위 밖). throwaway PG(D-182).
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pandas as pd
import pytest

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
import llm                                     # noqa: E402
from harness import lineage                    # noqa: E402
from resolver import resolve_dataset_path      # noqa: E402

_REPS = [
    ("L1_mct_tool_manage", "timeseries", "MCT 공구 관리"),
    ("order_planning", "order", "주문 계획"),
    ("L4_ict_inspection", "event-log", "ICT 검사"),
]

# ── MCP tools 격리 로드 (4서버 모듈명 'tools' 충돌 회피 — spec 고유명) ──────────
_MCP_CACHE: dict = {}


def _load_mcp_tools(modality: str):
    if modality in _MCP_CACHE:
        return _MCP_CACHE[modality]
    d = _REPO / "mcp-servers" / modality
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))            # tools 내부 상대 import(semantic 등) 위해
    spec = importlib.util.spec_from_file_location(
        f"_mcptools_{modality.replace('-', '_')}", str(d / "tools.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MCP_CACHE[modality] = mod
    return mod


async def _inproc_mcp(modality: str, path: str, **params):
    """inspector._mcp_get 대체 — HTTP 대신 in-process MCP tools 직접 호출(실 데이터 로직)."""
    t = _load_mcp_tools(modality)
    did = params["dataset_id"]
    dp = params.get("data_path")
    if path == "/list_columns":
        return t.list_columns(did, dp)
    if path == "/get_schema":
        return t.get_schema(did, dp)
    if path == "/sample":
        return t.sample(did, params.get("n", 5), dp)
    if path == "/detect_encoding":
        return t.detect_encoding(t._resolve(did, dp))
    raise ValueError(f"unknown MCP path: {path}")


async def _stub_generate(*_a, **_k) -> str:
    return json.dumps({"_llm_failed": True, "error": "5c-2 deterministic stub"})


def _seed_entry(did: str, modality: str, name: str) -> dict:
    return {"datalake_id": did, "source": "kamp", "name": name,
            "modality": modality, "data_path": f"data/lake/{did}/"}


async def _run_one(cat, monkeypatch, did: str, modality: str, name: str):
    """프로덕션 execute_endpoint 실태우기(inspect=실 MCP tools·data_path) → (result, plan, profile)."""
    await cat.upsert_entry(_seed_entry(did, modality, name))
    monkeypatch.setattr(inspector, "_mcp_get", _inproc_mcp)   # HTTP → in-process MCP tools
    monkeypatch.setattr(llm, "generate", _stub_generate)

    # approved 추출용 선산출(핸들러 내부와 동일 결정론). inspect=실 lake(data_path) 경유.
    data_path = await resolve_dataset_path(did)
    profile = await inspector.inspect(did, modality=modality, data_path=data_path)
    plan = await planner.plan(profile, constraints=None)
    approved = [s["step_key"] for s in plan["steps"]
                if s["permission_level"] in ("L2", "L3")]

    lineage._STORE.clear()
    req = main.ExecuteReq(dataset_id=did, modality=modality, approved_keys=approved)
    result = await main.execute_endpoint(req)
    return result, plan, profile


# ─────────────────────────────────────────────────────────────────────────────
async def test_inspect_seam_3_modalities(cat, monkeypatch):
    """csv 3 모달리티 — inspect(실 MCP·data_path)→plan→execute→validate full 완주."""
    for did, modality, name in _REPS:
        result, plan, profile = await _run_one(cat, monkeypatch, did, modality, name)

        # (1) inspect 가 실 lake 읽음 — profile.n_rows>0 (synthetic not-found 면 inspect 가 raise→500)
        assert profile.get("n_rows") and profile["n_rows"] > 0, f"{did}: profile n_rows 없음(실 lake 미로드)"
        assert profile.get("columns"), f"{did}: profile columns 없음"
        # (2) execution 도달 + 오류 0
        execu = result["execution"]
        assert execu is not None, f"{did}: execution None ({result.get('note')})"
        assert "error" not in execu, f"{did}: execute error {execu.get('error')}"
        # (3) 완주 (L2 사전 승인)
        assert execu["all_done"] is True, f"{did}: all_done False, pending={execu['pending_approvals']}"
        # (4) 산출물 + 실 데이터 적재 + silent drop 0
        bdf = pd.read_parquet(execu["backup_path"])
        pdf = pd.read_parquet(execu["output_path"])
        assert bdf.shape[0] > 0, f"{did}: 빈 backup — 실 lake 미로드 의심"
        assert bdf.shape[0] == pdf.shape[0], f"{did}: silent drop {bdf.shape} -> {pdf.shape}"
        # (5) inspect 프로파일 행수 == execute 적재 행수 (같은 실 lake 관통 정합)
        assert profile["n_rows"] == bdf.shape[0], (
            f"{did}: inspect n_rows {profile['n_rows']} != execute backup {bdf.shape[0]} (소스 불일치)")
        # (6) lineage == done
        chain = lineage.get_chain(did)
        done = [s for s in execu["results"] if s["status"] == "done"]
        assert len(chain) == len(done) and len(chain) >= 1, f"{did}: lineage {len(chain)} != done {len(done)}"


async def test_seam_off_inspect_fails(cat, monkeypatch):
    """비공허 대조 — data_path 없이 inspect 시 MCP tools 가 부재 synthetic ROOT → 실패."""
    monkeypatch.setattr(inspector, "_mcp_get", _inproc_mcp)
    monkeypatch.setattr(llm, "generate", _stub_generate)
    for did, modality, name in _REPS:
        await cat.upsert_entry(_seed_entry(did, modality, name))
        with pytest.raises(Exception):       # synthetic ROOT 부재 → FileNotFoundError
            await inspector.inspect(did, modality=modality, data_path=None)


async def test_inspect_seam_reproducible(cat, monkeypatch):
    """event-log 2회 — plan steps + execution 결정론 필드 + profile n_rows 동일."""
    did, modality, name = _REPS[2]

    def _sig(result, plan, profile):
        e = result["execution"]
        return (
            tuple((s["operation"], s["permission_level"], s.get("target_column")) for s in plan["steps"]),
            tuple((s["operation"], s["status"]) for s in e["results"]),
            e["all_done"], profile["n_rows"],
            pd.read_parquet(e["output_path"]).shape,
        )

    r1, p1, pr1 = await _run_one(cat, monkeypatch, did, modality, name)
    r2, p2, pr2 = await _run_one(cat, monkeypatch, did, modality, name)
    assert _sig(r1, p1, pr1) == _sig(r2, p2, pr2), (
        f"비결정 누출:\n{_sig(r1, p1, pr1)}\n!=\n{_sig(r2, p2, pr2)}"
    )
