"""tests/test_vid_eda_dl4.py — DL-4 게이트 (D-182).

(A) vid 결정론 전파: PipelineFull.vid → _build_agent_record / _build_stage_chain 산출물 (D-162).
(B) EDA slim_stage_chain: eda_engine LLM payload 1키 + system prompt [EN] 1줄 (BLUEPRINT §2.3).
(C) D-59 경계: compute_chart_data 결정론 불변 + aggregator LLM 0건 유지.

순수 검증 — throwaway PG 불요(aggregate/eda slim/compute_chart_data 모두 dict·df in-memory).
conftest 의 PG fixture 를 요청하지 않으므로 본 모듈은 컨테이너를 기동하지 않는다.
"""
from __future__ import annotations
import json
import pathlib
import re
import sys
import types

# conftest 는 backend/·tools/ 만 sys.path 에 넣는다. agents/ 의 flat 모듈 경로 추가.
_REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (_REPO / "agents" / "aggregator", _REPO / "agents" / "eda"):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

import context_aggregator  # noqa: E402
import eda_engine          # noqa: E402


# ─────────────────────────────────────────────────────────────────────────
# fixtures (in-memory session — DB 무관)
# ─────────────────────────────────────────────────────────────────────────
def _session(with_vid: bool) -> dict:
    pf: dict = {
        "line_id": "L1",
        "stages": [
            {"stage_order": 1, "node_id": "n1",
             "modules": [{"index": 0, "function": "process", "dataset_role": "press",
                          "datalake_id": "L1_press"}]},
            {"stage_order": 2, "node_id": "n2",
             "modules": [{"index": 0, "function": "quality", "dataset_role": "insp",
                          "datalake_id": "L1_insp"}]},
        ],
    }
    if with_vid:
        pf["vid"] = "L1"   # PipelineFull 최상위 SSOT (entries.vid 동일명). 테스트에서 'catalog vid' 주입.
    return {
        "session_id": "s1",
        "pipeline_full": pf,
        "module_results": {
            "1.0": {"modality": "timeseries", "dataset_id": "L1_press",
                    "profile": {}, "plan": {}, "execution": {}, "validation": {}},
            "2.0": {"modality": "event-log", "dataset_id": "L1_insp",
                    "profile": {}, "plan": {}, "execution": {}, "validation": {}},
        },
    }


# ─────────────────────────────────────────────────────────────────────────
# T1 — vid 끝까지 전파: 스키마 → agent_record → stage_chain (게이트 1)
# ─────────────────────────────────────────────────────────────────────────
def test_t1_vid_propagates_to_records_and_stage_chain():
    ctx = context_aggregator.aggregate(_session(with_vid=True))

    assert ctx["agent_records"], "agent_records 비어 있음"
    assert ctx["stage_chain"], "stage_chain 비어 있음"

    # 각 산출물 최상위에 vid 키 존재 + 값 == 주입한 'L1'
    assert all("vid" in r for r in ctx["agent_records"])
    assert all(r["vid"] == "L1" for r in ctx["agent_records"])
    assert all("vid" in n for n in ctx["stage_chain"])
    assert all(n["vid"] == "L1" for n in ctx["stage_chain"])

    # 값 일치(self-consistency): record vid 집합 == node vid 집합 == {단일 vid}
    rec_vids = {r["vid"] for r in ctx["agent_records"]}
    node_vids = {n["vid"] for n in ctx["stage_chain"]}
    assert rec_vids == node_vids == {"L1"}, (rec_vids, node_vids)

    # 경계: vid 는 흐름 ID 만 — function/site 와 무관(중복 전파 0). record 에 'site' 키 없음.
    for r in ctx["agent_records"]:
        assert "site" not in r
        assert r["vid"] != r.get("module_function")  # vid 를 function 으로 재구성하지 않음


def test_t1b_vid_none_when_absent_graceful():
    """런타임 오픈 항목 문서화: 백엔드가 pipeline_full.vid 를 아직 안 실음(line_id 만).
    그 경우 vid 는 None 으로 '실어 나르기'(crash 0·키는 존재) — additive·graceful."""
    ctx = context_aggregator.aggregate(_session(with_vid=False))
    assert all("vid" in r and r["vid"] is None for r in ctx["agent_records"])
    assert all("vid" in n and n["vid"] is None for n in ctx["stage_chain"])


# ─────────────────────────────────────────────────────────────────────────
# T2 — EDA slim_stage_chain (게이트 2)
# ─────────────────────────────────────────────────────────────────────────
def test_t2a_slim_stage_chain_helper_shape():
    sc = [
        {"stage_order": 1, "node_id": "n1", "main_findings": ["a", "b"],
         "downstream_implication": "impl1"},
        {"stage_order": 2, "node_id": "n2", "main_findings": [],
         "downstream_implication": "impl2"},
    ]
    slim = eda_engine._slim_stage_chain(sc)
    assert len(slim) == 2
    for e in slim:
        assert set(e.keys()) == {"stage_order", "node_id", "downstream_implication"}
        assert "main_findings" not in e          # key_findings 와 중복 → 생략
    assert slim[0]["stage_order"] == 1 and slim[0]["downstream_implication"] == "impl1"
    assert eda_engine._slim_stage_chain(None) == []   # graceful


async def test_t2b_llm_payload_includes_slim_and_prompt(monkeypatch):
    """실제 LLM payload(=user JSON) + system prompt 검증. hermetic fake llm 주입
    (실 ollama·네트워크 무접촉). asyncio_mode=auto 이므로 async 테스트 직접 실행."""
    cap: dict = {}
    fake = types.ModuleType("llm")

    async def fake_generate_json(prompt, system=None, model=None):
        cap["user"] = prompt
        cap["system"] = system
        return {"recommendations": []}

    fake.generate_json = fake_generate_json
    # eda_engine.llm_recommend_charts 가 호출 시점에 `from llm import generate_json` 하므로
    # 호출 전에 sys.modules['llm'] 을 fake 로 교체(monkeypatch 가 자동 복원).
    monkeypatch.setitem(sys.modules, "llm", fake)

    ctx = {
        "stage_chain": [
            {"stage_order": 1, "node_id": "n1", "main_findings": ["x", "y"],
             "downstream_implication": "impl-down"},
        ],
        "key_findings": [],
        "user_intent": None,
    }
    profile = {"available": True, "dataset_id": "d", "modality": "timeseries",
               "rows": 1, "n_cols": 1, "columns": []}

    await eda_engine.llm_recommend_charts(profile, ctx, "process", "timeseries", None)

    payload = json.loads(cap["user"])
    assert "slim_stage_chain" in payload                 # 게이트 2: 키 존재
    elems = payload["slim_stage_chain"]
    assert elems, "slim_stage_chain 비어 있음"
    for e in elems:
        assert {"stage_order", "node_id", "downstream_implication"} <= set(e)
        assert "main_findings" not in e                  # 게이트 2: main_findings 부재
    assert elems[0]["downstream_implication"] == "impl-down"

    # system prompt 에 [EN] 1줄 verbatim append 확인
    assert "slim_stage_chain encodes this dataset's position in its process flow" in cap["system"]
    assert "must not affect any chart or statistical computation" in cap["system"]


# ─────────────────────────────────────────────────────────────────────────
# T3 — compute_chart_data 결정론 불변 (게이트 3, D-59)
# ─────────────────────────────────────────────────────────────────────────
def test_t3_compute_chart_data_deterministic_histogram():
    import pandas as pd
    df = pd.DataFrame({"x": [float(i) for i in range(100)]})
    out1 = eda_engine.compute_chart_data(df.copy(), "histogram", {"target_column": "x"}, "timeseries")
    out2 = eda_engine.compute_chart_data(df.copy(), "histogram", {"target_column": "x"}, "timeseries")
    assert out1 == out2                                  # 같은 입력 → 같은 출력(재현성)
    assert out1["column"] == "x"
    assert out1["stats"]["n"] == 100
    assert out1["stats"]["min"] == 0.0 and out1["stats"]["max"] == 99.0
    assert sum(out1["counts"]) == 100                    # 전 행이 bin 에 귀속


def test_t3_compute_chart_data_deterministic_class_distribution():
    import pandas as pd
    df = pd.DataFrame({"label": ["a", "a", "b", "c", "c", "c"]})
    out = eda_engine.compute_chart_data(df.copy(), "class_distribution",
                                        {"target_column": "label"}, "event-log")
    assert out["column"] == "label"
    assert dict(zip(out["labels"], out["counts"])) == {"a": 2, "b": 1, "c": 3}


# ─────────────────────────────────────────────────────────────────────────
# T4 — aggregator LLM 0건 유지 (게이트 4, D-59)
# ─────────────────────────────────────────────────────────────────────────
def test_t4_aggregator_zero_llm():
    src = (_REPO / "agents" / "aggregator" / "context_aggregator.py").read_text(encoding="utf-8")
    hits = re.findall(r"from llm|import llm|generate\(", src)
    assert hits == [], f"D-59 위반: aggregator 에 LLM 호출 흔적 {hits}"
