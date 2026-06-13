"""tests/test_vid_source_dl411.py — 4.1.1 게이트 (D-197/D-188).

DL-4 가 배선한 vid 전파 파이프의 '입구(소스)'를 켰는지 검증한다.
DL-4(test_vid_eda_dl4) 는 pipeline_full.vid 를 테스트에서 '수동 주입'했지만,
여기서는 실제 backend session-build(main.sessions_create / session_put_structure)가
vid=line_id 를 스스로 적재하는지 = 실값 소스를 구동해서 끝까지(record/stage_chain) 도달함을 본다.

- T-A: 실값 e2e — session-build → pipeline_full.vid → aggregate → record/stage_chain == "L1"(비-None).
- T-B: None graceful — line_id 부재 세션은 vid 미적재(silent 기본값 0) + aggregate vid None·crash 0 (DL-4 T1b 보존).
- T-C: D-59 — compute_chart_data 정의 불변(eda_engine.py == baseline blob, DEF_CHANGED=0).
- T-D: 경계 — 코드 변경은 backend/main.py(+tests 신규)뿐, 금지영역 0접촉.

순수 검증 — throwaway PG 불요. session_store 는 in-memory, main import 는 hermetic(db lazy pool).
conftest 가 PG* env 를 throwaway 로 강제하므로 라이브 오접촉 차단. asyncio_mode=auto → async 직접 실행.
"""
from __future__ import annotations

import importlib
import inspect
import pathlib
import subprocess
import sys

# baseline = 4.1.1 작업 직전 HEAD (Master 좌표 정정: DL-4 tag d8500d7 후 .gitignore 핸드오프 2커밋).
_BASELINE = "3343f3a1139d7a3d547f2d74589054bee455e915"

_REPO = pathlib.Path(__file__).resolve().parents[1]
# conftest 가 backend/ 를 넣지만 명시. agents/aggregator 는 context_aggregator 용.
for _p in (_REPO / "backend", _REPO / "agents" / "aggregator"):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

import main               # noqa: E402  — backend session-build 핸들러(import 시 agents 경로도 셋업)
import session_store      # noqa: E402  — in-memory 세션(핸들러와 동일 인스턴스 공유)
import context_aggregator  # noqa: E402  — DL-4 vid 전파 소비부


def _git(*args: str) -> str:
    """git stdout 반환(check=True). pipe 종료코드 비의존 — stdout 값으로 판정(D-192)."""
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


# ─────────────────────────────────────────────────────────────────────────
# T-A — 실값 e2e: session-build 가 vid=line_id 를 적재 → 끝까지 비-None 도달
# ─────────────────────────────────────────────────────────────────────────
async def test_a_vid_source_real_value_e2e():
    # (1) create skeleton (Page 1, line_id 단독) — 소스 1지점: skeleton 에 vid 적재
    res = await main.sessions_create(main.CreateSessionReq(line_id="L1"))
    sid = res["session_id"]
    pf_create = session_store.get_session(sid)["pipeline_full"]
    assert pf_create["vid"] == "L1", f"create skeleton vid 미적재: {pf_create}"

    # (2) structure (Page 2) — stages 채움, 소스 2지점: structure 에도 vid 적재
    await main.session_put_structure(
        sid, main.StructureReq(line_id="L1", stages=_stages()))
    sess = session_store.get_session(sid)
    assert sess["pipeline_full"]["vid"] == "L1", f"structure vid 미적재: {sess['pipeline_full']}"
    assert sess["pipeline_full"]["line_id"] == "L1"   # 기존 키 불변(additive)

    # (3) module_results 부여 → DL-4 전파 파이프(aggregate) → record/stage_chain 까지 실값 도달
    sess["module_results"] = _module_results()
    ctx = context_aggregator.aggregate(sess)
    assert ctx["agent_records"] and ctx["stage_chain"], "record/stage_chain 비어 있음"
    assert all(r["vid"] == "L1" for r in ctx["agent_records"]), \
        f"record vid 비-L1: {[r['vid'] for r in ctx['agent_records']]}"
    assert all(n["vid"] == "L1" for n in ctx["stage_chain"]), \
        f"stage_chain vid 비-L1: {[n['vid'] for n in ctx['stage_chain']]}"

    # self-consistency: 단일 vid 실값(비-None)
    rec_vids = {r["vid"] for r in ctx["agent_records"]}
    node_vids = {n["vid"] for n in ctx["stage_chain"]}
    assert rec_vids == node_vids == {"L1"}, (rec_vids, node_vids)
    assert None not in rec_vids and None not in node_vids   # 소스 ON = 더 이상 None 아님


# ─────────────────────────────────────────────────────────────────────────
# T-B — None graceful: line_id 부재 → vid 미적재 + aggregate None·crash 0 (DL-4 T1b 보존)
# ─────────────────────────────────────────────────────────────────────────
async def test_b_vid_none_graceful_preserved():
    # line_id 부재(수신경로: pipeline_full 만) — 빌드포인트 vid 적재 우회 = silent 기본값 주입 0
    res = await main.sessions_create(main.CreateSessionReq(
        pipeline_full={"stages": _stages()}))
    sid = res["session_id"]
    sess = session_store.get_session(sid)
    assert "vid" not in sess["pipeline_full"], \
        f"line_id 부재인데 vid 주입됨(silent default 금지 위반): {sess['pipeline_full']}"

    # aggregate 는 vid 없으면 None 으로 '실어 나르기' — 키 존재·값 None·crash 0
    sess["module_results"] = _module_results()
    ctx = context_aggregator.aggregate(sess)
    assert all("vid" in r and r["vid"] is None for r in ctx["agent_records"])
    assert all("vid" in n and n["vid"] is None for n in ctx["stage_chain"])


# ─────────────────────────────────────────────────────────────────────────
# T-C — D-59: compute_chart_data 정의 불변(eda_engine.py == baseline blob)
# ─────────────────────────────────────────────────────────────────────────
def test_c_compute_chart_data_unchanged_d59():
    """DEF_CHANGED=0 — eda_engine.py(=compute_chart_data 정의 포함) 현재 == baseline blob.
    commit 상태 무관(작업트리 파일 vs baseline 커밋 blob 비교)."""
    baseline = _git("show", f"{_BASELINE}:agents/eda/eda_engine.py")
    current = (_REPO / "agents" / "eda" / "eda_engine.py").read_text(encoding="utf-8")
    assert current == baseline, "D-59 위반: eda_engine.py(compute_chart_data 정의 포함) 변경 감지"
    assert "def compute_chart_data" in baseline       # 정의 실재
    eda = importlib.import_module("eda_engine")
    assert inspect.isfunction(eda.compute_chart_data)  # 호출 가능 보존


# ─────────────────────────────────────────────────────────────────────────
# T-D — 경계: 코드 변경 = backend/main.py 한 파일(+tests 신규)뿐, 금지영역 0접촉
# ─────────────────────────────────────────────────────────────────────────
def test_d_boundary_only_mainpy():
    """작업트리 기준 baseline 대비 변경 코드파일 검사(commit 전/후 무관)."""
    out = _git("diff", _BASELINE, "--name-only", "--",
               "*.py", "*.ts", "*.tsx", "*.jsx")
    changed = [ln for ln in out.splitlines() if ln.strip()]
    allowed = {"backend/main.py", "tests/test_vid_source_dl411.py"}
    extra = set(changed) - allowed
    assert not extra, f"경계 위반: 허용밖 코드 변경 {extra}"
    assert "backend/main.py" in changed, f"main.py 변경 미검출: {changed}"
    forbidden = ("agents/aggregator", "agents/eda", "backend/db.py",
                 "backend/datalake_api.py", "mcp-servers/", "frontend/", "harness/")
    for f in changed:
        assert not any(f.startswith(p) for p in forbidden), f"금지영역 접촉: {f}"
