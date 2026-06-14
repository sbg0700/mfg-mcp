"""tests/test_vid_full_dl412.py — 4.1.2 게이트 (D-198).

Page-3 /full 핸들러가 클라이언트 pipeline_full로 통째 교체할 때 vid 보존.
4.1.1이 켠 입구(create/structure)가 /full overwrite로 prod에서 vid None 회귀하던
갭(D-198)을 닫는다. v1(main.session_put_full) + v2(datalake_api.dl_session_put_full)
양 경로 검증.

- T-A : /full vid 미동반(pf.line_id 동반) → vid=line_id 보존(① pf.line_id) + e2e record/stage_chain 도달.
- T-A2: pf.line_id 부재 + 세션 line_id 존재 → vid 재유도(② 세션 line_id) anti-silent 우선순위.
- T-B : /full vid 실값이 derived(권위)와 불일치 → 422 거부(D-200 fail-loud).
- T-B2: present vid가 derived와 일치 → 존중 no-op(raise 0).
- T-C : vid·line_id 모두 부재(세션도) → vid None graceful, crash 0 (silent default 0).
- T-D : compute_chart_data 불변(eda==baseline blob, DEF_CHANGED=0, D-59).
- T-E : 경계 — 변경 = main.py/datalake_api.py(+신규테스트)뿐, 금지영역 0.

hermetic: session_store in-memory, main/datalake_api import db lazy pool → throwaway PG 불요.
conftest 가 PG* env throwaway 강제 → 라이브 무접촉. asyncio_mode=auto.
"""
from __future__ import annotations

import importlib
import inspect
import pathlib
import subprocess
import sys

import pytest
from fastapi import HTTPException

# baseline = 4.1.2 작업 직전 HEAD = tag DL-4.1.1
_BASELINE = "acc1f4cf8bce63dfa9466d098e5616a296e00c1c"

_REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (_REPO / "backend", _REPO / "agents" / "aggregator"):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

import main               # noqa: E402  v1 /full 핸들러 + session-build 핸들러
import datalake_api       # noqa: E402  v2 /full 핸들러
import session_store      # noqa: E402  in-memory(핸들러와 동일 인스턴스)
import context_aggregator  # noqa: E402  vid 전파 소비부


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(_REPO), *args],
                          capture_output=True, text=True, check=True).stdout


def _stages() -> list[dict]:
    return [
        {"stage_order": 1, "node_id": "n1",
         "modules": [{"index": 0, "function": "process", "dataset_role": "press",
                      "datalake_id": "L1_press"}]},
        {"stage_order": 2, "node_id": "n2",
         "modules": [{"index": 0, "function": "quality", "dataset_role": "insp",
                      "datalake_id": "L1_insp"}]},
    ]


def _module_results() -> dict:
    return {
        "1.0": {"modality": "timeseries", "dataset_id": "L1_press",
                "profile": {}, "plan": {}, "execution": {}, "validation": {}},
        "2.0": {"modality": "event-log", "dataset_id": "L1_insp",
                "profile": {}, "plan": {}, "execution": {}, "validation": {}},
    }


async def _call_full(variant: str, sid: str, pf: dict):
    """v1/v2 /full 핸들러 직접 구동(라우팅 우회)."""
    if variant == "v1":
        return await main.session_put_full(sid, main.FullReq(pipeline_full=pf))
    return await datalake_api.dl_session_put_full(sid, datalake_api.FullV2Req(pipeline_full=pf))


async def _built_session(line_id: str = "L1") -> str:
    """4.1.1 입구(create→structure)로 세션 빌드. sid 반환."""
    res = await main.sessions_create(main.CreateSessionReq(line_id=line_id))
    sid = res["session_id"]
    await main.session_put_structure(
        sid, main.StructureReq(line_id=line_id, stages=_stages()))
    return sid


# ─────────────────────────────────────────────────────────────────────────
# T-A — /full vid 미동반 보존(① pf.line_id) + e2e (D-198 핵심 갭 클로즈)
# ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("variant", ["v1", "v2"])
async def test_a_full_preserves_vid_via_pf_lineid(variant):
    sid = await _built_session("L1")
    # 클라가 vid 미동반(line_id=L1 포함) full 전송 — 4.1.1 전이면 여기서 vid 소실
    await _call_full(variant, sid, {"line_id": "L1", "stages": _stages()})
    sess = session_store.get_session(sid)
    assert sess["pipeline_full"]["vid"] == "L1", \
        f"[{variant}] /full 후 vid 미보존: {sess['pipeline_full'].get('vid')}"
    # e2e: aggregate → record/stage_chain 까지 실값(비-None) 도달
    sess["module_results"] = _module_results()
    ctx = context_aggregator.aggregate(sess)
    assert ctx["agent_records"] and ctx["stage_chain"]
    assert all(r["vid"] == "L1" for r in ctx["agent_records"]), f"[{variant}] record vid"
    assert all(n["vid"] == "L1" for n in ctx["stage_chain"]), f"[{variant}] stage_chain vid"


# ─────────────────────────────────────────────────────────────────────────
# T-A2 — pf.line_id 부재 → 세션 line_id 로 재유도(② 우선순위, anti-silent)
# ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("variant", ["v1", "v2"])
async def test_a2_full_redrives_vid_from_session_lineid(variant):
    sid = await _built_session("L1")                       # 세션 line_id="L1"
    await _call_full(variant, sid, {"stages": _stages()})  # pf vid·line_id 둘 다 부재
    sess = session_store.get_session(sid)
    assert sess["pipeline_full"]["vid"] == "L1", \
        f"[{variant}] ② 세션 line_id 재유도 실패: {sess['pipeline_full'].get('vid')}"


# ─────────────────────────────────────────────────────────────────────────
# T-B — D-200 fail-loud: /full vid 실값이 derived(권위)와 불일치 → 422 거부
# ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("variant", ["v1", "v2"])
async def test_b_full_rejects_vid_mismatch(variant):
    sid = await _built_session("L1")                       # 세션 line_id="L1" = 권위 derived
    with pytest.raises(HTTPException) as ei:
        await _call_full(variant, sid, {"vid": "Lkeep", "stages": _stages()})  # 불일치
    assert ei.value.status_code == 422, f"[{variant}] status={ei.value.status_code}"
    assert "vid mismatch" in str(ei.value.detail), f"[{variant}] detail={ei.value.detail}"


# ─────────────────────────────────────────────────────────────────────────
# T-B2 — present vid가 derived와 일치 → 존중 no-op (raise 0, 정상 round-trip)
# ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("variant", ["v1", "v2"])
async def test_b2_full_respects_matching_vid(variant):
    sid = await _built_session("L1")
    await _call_full(variant, sid, {"vid": "L1", "stages": _stages()})  # 일치 → 존중
    sess = session_store.get_session(sid)
    assert sess["pipeline_full"]["vid"] == "L1", \
        f"[{variant}] 일치 vid 존중 실패: {sess['pipeline_full'].get('vid')}"


# ─────────────────────────────────────────────────────────────────────────
# T-C — vid·line_id 모두 부재(세션도) → vid None graceful, crash 0
# ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("variant", ["v1", "v2"])
async def test_c_full_none_graceful(variant):
    # line_id 없는 세션(수신경로) → 세션 line_id 부재
    res = await main.sessions_create(main.CreateSessionReq(pipeline_full={"stages": _stages()}))
    sid = res["session_id"]
    await _call_full(variant, sid, {"stages": _stages()})  # pf vid·line_id 부재
    sess = session_store.get_session(sid)
    assert sess["pipeline_full"].get("vid") is None, \
        f"[{variant}] None graceful 위반(silent default?): {sess['pipeline_full'].get('vid')}"
    sess["module_results"] = _module_results()
    ctx = context_aggregator.aggregate(sess)               # crash 0
    assert all(r["vid"] is None for r in ctx["agent_records"])
    assert all(n["vid"] is None for n in ctx["stage_chain"])


# ─────────────────────────────────────────────────────────────────────────
# T-D — D-59: compute_chart_data 정의 불변(eda_engine.py == baseline blob)
# ─────────────────────────────────────────────────────────────────────────
def test_d_compute_chart_data_unchanged():
    baseline = _git("show", f"{_BASELINE}:agents/eda/eda_engine.py")
    current = (_REPO / "agents" / "eda" / "eda_engine.py").read_text(encoding="utf-8")
    assert current == baseline, "D-59 위반: eda_engine.py(compute_chart_data 포함) 변경 감지"
    assert "def compute_chart_data" in baseline
    eda = importlib.import_module("eda_engine")
    assert inspect.isfunction(eda.compute_chart_data)


# ─────────────────────────────────────────────────────────────────────────
# T-E — 경계: 변경 = backend/main.py + backend/datalake_api.py(+신규테스트)뿐
# ─────────────────────────────────────────────────────────────────────────
def test_e_boundary():
    out = _git("diff", _BASELINE, "--name-only", "--",
               "*.py", "*.ts", "*.tsx", "*.jsx")
    changed = [ln for ln in out.splitlines() if ln.strip()]
    allowed = {"backend/main.py", "backend/datalake_api.py", "tests/test_vid_full_dl412.py"}
    extra = set(changed) - allowed
    assert not extra, f"경계 위반: 허용밖 코드 변경 {extra}"
    assert "backend/main.py" in changed and "backend/datalake_api.py" in changed, \
        f"양 핸들러 변경 미검출: {changed}"
    forbidden = ("agents/aggregator", "agents/eda", "backend/db.py",
                 "backend/session_store.py", "mcp-servers/", "frontend/", "harness/")
    for f in changed:
        assert not any(f.startswith(p) for p in forbidden), f"금지영역 접촉: {f}"
