"""tests/test_e2e_dl5c3.py — DL-5c-3 image 프로덕션 위치 seam 게이트 (D-207).

체인: main.execute_endpoint(프로덕션 핸들러) → _resolve_seam_path(image→catalog data_path 디렉터리,
  *.csv glob 미경유) → inspect(data_path) → image MCP tools(data_path=실 lake 디렉터리) → plan
  → execute(data_path) → _execute_image(folder=실 lake). image 2종(flat / nested) full end-to-end.

MCP HTTP 실기동=live smoke(명선) → 게이트는 inspector._mcp_get 을 in-process image MCP tools 로
우회(HTTP 계층만 우회, MCP 데이터 로직=실행, 실 lake 디렉터리 읽기 검증). llm=결정론 stub.
image엔 행(n_rows) 개념 부재 → 정합지표 = n_images(장수): inspect n_images == 디렉터리 실측 장수
== execute 처리 장수. 정확값 금지(D-202): 존재·형상·정합·재현(2회)만. EDA 제외(D-123).
throwaway PG(D-182, 라이브 쓰기 0). carry(D-207)=별도 단위테스트(실 _mcp_get None-drop).
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import sys

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

_MODALITY = "inspection-image"
# (id, 구조설명, ground-truth 장수) — 소형 2종(빠른 게이트). flat·무라벨 + nested(하위폴더)·txt페어 커버.
_REPS = [
    ("L2_auto_console_detect", "flat·무라벨", 20),
    ("L2_press_aluminum", "nested(학습용/샘플)·txt페어", 50),
    # pattern C: bmp 100 + 라벨 csv 1 — n_images==100(csv 비처리) = 라벨파일 혼입 차단 실증(anti-silent)
    ("L2_welding_electrode", "flat·단일 csv 라벨(pattern C)", 100),
]
_IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")   # image tools._scan 와 동일 집합


# ── image MCP tools 격리 로드 (모듈명 'tools' 충돌 회피) ─────────────────────────
_mcp_mod = None


def _img_tools():
    global _mcp_mod
    if _mcp_mod is None:
        d = _REPO / "mcp-servers" / _MODALITY
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))
        spec = importlib.util.spec_from_file_location(
            "_mcptools_inspection_image", str(d / "tools.py"))
        _mcp_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mcp_mod)
    return _mcp_mod


async def _inproc_mcp(modality: str, path: str, **params):
    """inspector._mcp_get 대체 — HTTP 대신 in-process image MCP tools 직접 호출(실 데이터 로직).
    detect_encoding 은 server.ep_detect_encoding 과 동일하게 (디렉터리→첫 이미지) 해석."""
    t = _img_tools()
    did = params["dataset_id"]
    dp = params.get("data_path")
    if path == "/list_columns":
        return t.list_columns(did, dp)
    if path == "/get_schema":
        return t.get_schema(did, dp)
    if path == "/sample":
        return t.sample(did, params.get("n", 5), dp)
    if path == "/detect_encoding":
        folder = t._resolve(did, dp)
        items = t._scan(folder)
        if not items:
            raise FileNotFoundError("no images")
        return t.detect_encoding(os.path.join(folder, items[0]["file"]))
    raise ValueError(f"unknown MCP path: {path}")


async def _stub_generate(*_a, **_k) -> str:
    return json.dumps({"_llm_failed": True, "error": "5c-3 deterministic stub"})


def _seed_entry(did: str, name: str) -> dict:
    return {"datalake_id": did, "source": "kamp", "name": name,
            "modality": _MODALITY, "data_path": f"data/lake/{did}/"}


def _ground_truth(did: str) -> int:
    """data/lake/<id>/ 실측 이미지 장수 (_scan ext 집합과 동일, recursive)."""
    base = _REPO / "data" / "lake" / did
    return sum(1 for p in base.rglob("*")
               if p.is_file() and p.suffix.lower() in _IMG_EXT)


def _exec_image_count(execu: dict) -> int:
    """execute 처리 장수 — _execute_image output_path "{did} (이미지 N장, 원본 보존)" 파싱.
    (5a 동결로 _execute_image 에 새 정수 필드 추가 불가 → 기존 계약값에서 추출)."""
    op = execu.get("output_path", "") or ""
    m = re.search(r"이미지 (\d+)장", op)
    assert m, f"output_path 장수 파싱 실패: {op!r}"
    return int(m.group(1))


async def _run_one(cat, monkeypatch, did: str, name: str):
    """프로덕션 execute_endpoint 실태우기(inspect=실 image MCP tools·data_path 디렉터리)."""
    await cat.upsert_entry(_seed_entry(did, name))
    monkeypatch.setattr(inspector, "_mcp_get", _inproc_mcp)    # HTTP → in-process MCP tools
    monkeypatch.setattr(llm, "generate", _stub_generate)

    data_path = await main._resolve_seam_path(did, _MODALITY)  # image → 디렉터리(csv glob 미경유)
    profile = await inspector.inspect(did, modality=_MODALITY, data_path=data_path)
    plan = await planner.plan(profile, constraints=None)
    approved = [s["step_key"] for s in plan["steps"]
                if s["permission_level"] in ("L2", "L3")]

    lineage._STORE.clear()
    req = main.ExecuteReq(dataset_id=did, modality=_MODALITY, approved_keys=approved)
    result = await main.execute_endpoint(req)
    return result, plan, profile, data_path


# ─────────────────────────────────────────────────────────────────────────────
async def test_image_seam_2_datasets(cat, monkeypatch):
    """image 2종 — inspect(실 MCP·data_path 디렉터리)→plan→execute(_execute_image) full 완주.
    정합: inspect n_images == 디렉터리 실측 장수 == execute 처리 장수(같은 실 lake 관통)."""
    for did, _struct, gt in _REPS:
        result, _plan, profile, dp = await _run_one(cat, monkeypatch, did, did)

        # (0) seam 이 실 lake '디렉터리'를 반환(절대·존재·data/lake 경유 — csv 파일 아님)
        norm = dp.replace("\\", "/")
        assert os.path.isabs(dp) and os.path.isdir(dp) and "data/lake/" in norm, \
            f"{did}: seam dir 이상 {dp}"
        assert not dp.endswith(".csv"), f"{did}: seam 이 csv 파일 반환(디렉터리여야) {dp}"

        # (1) inspect 가 실 lake 읽음 — n_images>0
        n_img = profile.get("n_rows")
        assert n_img and n_img > 0, f"{did}: profile n_images 없음(실 lake 미로드)"

        # (2) inspect n_images == 디렉터리 실측 장수(ground truth)
        gtruth = _ground_truth(did)
        assert n_img == gt == gtruth, f"{did}: inspect {n_img} != 실측 {gtruth}(기대 {gt})"

        # (3) execution 도달·오류 0·완주
        execu = result["execution"]
        assert execu is not None and "error" not in execu, f"{did}: execution 오류 {execu}"
        assert execu["all_done"] is True, \
            f"{did}: all_done False pending={execu.get('pending_approvals')}"

        # (4) 정합 — execute 처리 장수 == inspect n_images (동일 실 lake 디렉터리)
        ec = _exec_image_count(execu)
        assert ec == n_img, f"{did}: execute {ec} != inspect {n_img}"

        # (5) lineage 일관성 (체인 == done 단계 수)
        chain = lineage.get_chain(did)
        done = [s for s in execu["results"] if s["status"] == "done"]
        assert len(chain) == len(done), f"{did}: lineage {len(chain)} != done {len(done)}"


async def test_image_seam_off_inspect_fails(cat, monkeypatch):
    """비공허 대조 — data_path=None 이면 image MCP 가 부재 synthetic IMAGE_DATA_ROOT 폴백 → 실패.
    (seam 이 load-bearing: 제거하면 실 lake 미도달)."""
    monkeypatch.setattr(inspector, "_mcp_get", _inproc_mcp)
    monkeypatch.setattr(llm, "generate", _stub_generate)
    for did, _struct, _gt in _REPS:
        await cat.upsert_entry(_seed_entry(did, did))
        with pytest.raises(Exception):       # synthetic ROOT 부재 → FileNotFoundError
            await inspector.inspect(did, modality=_MODALITY, data_path=None)


async def test_image_seam_reproducible(cat, monkeypatch):
    """auto_console_detect 2회 — plan steps + execution 결정론 필드 + n_images 동일(비결정 0)."""
    did, _struct, _gt = _REPS[0]

    def _sig(result, plan, profile):
        e = result["execution"]
        return (
            tuple((s["operation"], s["permission_level"]) for s in plan["steps"]),
            tuple((s["operation"], s["status"]) for s in e["results"]),
            e["all_done"], profile["n_rows"], _exec_image_count(e),
        )

    r1, p1, pr1, _ = await _run_one(cat, monkeypatch, did, did)
    r2, p2, pr2, _ = await _run_one(cat, monkeypatch, did, did)
    assert _sig(r1, p1, pr1) == _sig(r2, p2, pr2), (
        f"비결정 누출:\n{_sig(r1, p1, pr1)}\n!=\n{_sig(r2, p2, pr2)}"
    )


async def test_mcp_get_drops_none_params(monkeypatch):
    """carry(D-207) — 실 _mcp_get 이 None 파라미터를 미전송(httpx 'data_path='(빈문자열) 회피).
    data_path 있으면 전송, None 이면 키 자체 제거. (e2e 는 _mcp_get 우회 → 여기서 실 함수 직검)."""
    captured: dict = {}

    class _FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None):
            captured["params"] = dict(params or {})
            return _FakeResp()

    monkeypatch.setattr(inspector.httpx, "AsyncClient", _FakeClient)

    await inspector._mcp_get("timeseries", "/list_columns", dataset_id="x", data_path=None)
    assert "data_path" not in captured["params"], \
        f"None data_path 가 전송됨(carry 위반): {captured['params']}"

    await inspector._mcp_get("timeseries", "/list_columns", dataset_id="x", data_path="/real/dir")
    assert captured["params"].get("data_path") == "/real/dir", \
        f"실 data_path 전송 누락: {captured['params']}"
