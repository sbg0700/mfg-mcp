"""
agents/planner/data_necessity.py — STEP 1B-2a: 데이터 미업로드 모듈 알람.

blueprint Part 2-6 + 4-5: 모듈은 1-1에서 배치됐지만 1-2에서 datalake가 비어있는 경우,
"이 데이터가 이 공정에 필수인가"를 LLM이 판단해 알람을 띄운다.

★환각 방어 (D-13, D-46 연장)★:
  - LLM은 '알람 문구'만 만들고, 파이프라인 흐름을 절대 바꾸지 못한다.
  - 처리 진행/중단의 결정은 사용자가 status를 보고 한다 (Orchestrator는 알람 기록 후 계속 진행 — skip).
  - judge 실패해도 안전 (likely_essential=False 폴백, 알람만 남김).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

# llm은 backend/llm.py — 같은 sys.path 트릭
ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(ROOT), str(ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)


async def llm_judge_data_necessity(stage: dict, missing: list[dict], uploaded: list[dict],
                                   model: str | None = None) -> dict:
    """미업로드 모듈에 대해 '필수성 알람'을 LLM이 생성. 결정은 사용자 몫.

    입력
    ----
    stage   : pipeline_full.stages[i] — {stage_order, node_id, modules:[...]}
    missing : datalake_id가 None인 모듈 list
    uploaded: 함께 있는, 업로드된 모듈 list (LLM 참고용 컨텍스트)

    반환
    ----
    { "likely_essential": bool,           # 참고 신호 — 흐름 결정에 사용 ❌
      "alarm_ko": "<한국어 알람 1~2문장>",  # UI 표시용
      "missing": ["function/dataset_role", ...] }
    """
    from llm import generate  # backend/llm.py

    def _desc(m: dict) -> str:
        return f"{m.get('function', '?')}/{m.get('dataset_role') or m.get('datalake_id') or '?'}"

    missing_desc = [_desc(m) for m in missing]
    uploaded_desc = [_desc(m) for m in uploaded]

    system = (
        "You are a manufacturing pipeline assistant. Some module slots in a process "
        "stage have NO data uploaded. Judge whether the missing data is likely ESSENTIAL "
        "for this stage's analysis, given the other uploaded modules. "
        "You only RAISE AN ALARM with reasoning — you do NOT decide. The user decides. "
        "Respond ONLY in JSON: {\"likely_essential\": true/false, "
        "\"alarm_ko\": \"<한국어 알람 1-2문장>\"}"
    )
    prompt = (
        f"stage node: {stage.get('node_id', '?')}\n"
        f"missing modules: {missing_desc}\n"
        f"uploaded modules: {uploaded_desc}\n"
    )

    try:
        raw = await generate(prompt, system=system, fmt_json=True, model=model)
        out = json.loads(raw)
        return {
            "likely_essential": bool(out.get("likely_essential", False)),
            "alarm_ko": str(out.get("alarm_ko") or "데이터 미업로드 모듈이 있습니다."),
            "missing": missing_desc,
        }
    except (json.JSONDecodeError, TypeError, Exception):
        # judge 실패 폴백 — 알람은 띄우되 '필수' 단정 안 함 (안전 측 기본)
        return {
            "likely_essential": False,
            "alarm_ko": "데이터 미업로드 모듈이 있습니다. (LLM 판단 실패 — 사용자 확인 요망)",
            "missing": missing_desc,
        }
