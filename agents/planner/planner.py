"""
agents/planner/planner.py — 2단 Planner (실동작).

역할: DataProfile(Inspector 출력) + 사용자 제약 → PreprocessingPlan.
권한: 계획만 (실행 권한 없음 — CLAUDE.md §5).

설계 (3가지 결정):
  1) 출력은 '계획'이지 '실행'이 아니다. 데이터를 건드리지 않는다.
  2) 각 단계에 권한 등급(L1/L2/L3)을 박는다 — harness/guardrails.py가 결정.
  3) LLM은 '제안', 규칙은 '검증/보정'. Inspector flags 기반으로 후보를 먼저 추리고
     LLM은 순서·우선순위·이유만 정하게 한다 → 작은 모델도 안정적.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

# 레포 루트를 path에 (harness, schemas import)
ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(ROOT), str(ROOT / "agents" / "planner"), str(ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness.guardrails import OPERATION_PERMISSION, Permission  # noqa: E402
from schemas import PlanStep, PreprocessingPlan                  # noqa: E402


def _permission_for(operation: str) -> str:
    """작업 유형 → 권한 등급. 가드레일 매핑을 단일 소스로 사용."""
    return OPERATION_PERMISSION.get(operation, Permission.L3).value


def _candidate_operations(profile: dict) -> list[dict]:
    """[규칙 단계] Inspector가 잡은 flags를 보고 '후보 작업'을 결정론적으로 추린다.
    LLM에게 빈 캔버스를 주지 않기 위함 (Harness: 도구 스키마 검증 정신)."""
    candidates: list[dict] = []
    flags = profile.get("deterministic_flags", [])
    columns = profile.get("columns", [])

    # 인코딩 비정상 → 인코딩 정규화 (L1)
    if any("non-utf8" in f or "encoding" in f for f in flags):
        candidates.append({"operation": "detect_encoding", "target_column": None,
                           "rationale": "비-UTF8 인코딩 감지됨. UTF-8로 정규화 필요."})

    # 헤더 없음 → 헤더 재파싱 (L1)
    if any("headerless" in f for f in flags):
        candidates.append({"operation": "reparse_header", "target_column": None,
                           "rationale": "헤더가 데이터 행으로 감지됨. 헤더 재구성 필요."})

    # dtype 혼재 컬럼 → 마스킹 정리 (L2)
    for c in columns:
        if c.get("mixed_dtype_suspected"):
            candidates.append({"operation": "clean_masking", "target_column": c["name"],
                               "rationale": f"'{c['name']}'에 마스킹 문자/혼재 dtype. NaN 변환 후 수치화 필요."})

    # 결측 있는 컬럼 → 결측 처리 (L2)
    for c in columns:
        if c.get("null_count", 0) > 0 and not c.get("mixed_dtype_suspected"):
            candidates.append({"operation": "fill_missing", "target_column": c["name"],
                               "rationale": f"'{c['name']}'에 결측치 존재."})

    # 항상 기초 통계 (L1)
    candidates.append({"operation": "compute_stats", "target_column": None,
                       "rationale": "전처리 전후 비교를 위한 기초 통계."})
    return candidates


async def plan(data_profile: dict, constraints: dict | None = None) -> dict:
    """DataProfile → PreprocessingPlan."""
    constraints = constraints or {}
    dataset_id = data_profile.get("dataset_id", "unknown")

    # 1) 규칙으로 후보 작업 추리기
    candidates = _candidate_operations(data_profile)

    # 2) LLM에게 '순서 정하기 + 이유 다듬기'만 요청 (자유도 제한)
    from llm import generate  # backend/llm.py
    system = (
        "You are a manufacturing data preprocessing planner. "
        "You are given a list of CANDIDATE operations already filtered by rules. "
        "Do NOT invent new operations. Only (1) order them sensibly "
        "(encoding/header fixes first, then cleaning, then stats last), "
        "(2) refine the Korean rationale. "
        "Respond ONLY in JSON: {\"ordered\":[{\"operation\":..,\"rationale\":..}], \"summary\":\"..\"}"
    )
    prompt = (
        f"dataset_id: {dataset_id}\n"
        f"flags: {data_profile.get('deterministic_flags', [])}\n"
        f"candidate_operations: {json.dumps(candidates, ensure_ascii=False)}\n"
    )
    raw = await generate(prompt, system=system, fmt_json=True)
    llm_order: list[str] = []      # LLM이 제안한 operation 실행 순서
    llm_rationale: dict = {}        # operation -> 다듬어진 이유
    summary = ""
    try:
        llm_out = json.loads(raw)
        for item in llm_out.get("ordered", []):
            op = item.get("operation")
            if op:
                llm_order.append(op)
                if item.get("rationale"):
                    llm_rationale[op] = item["rationale"]
        summary = llm_out.get("summary", "")
    except (json.JSONDecodeError, TypeError):
        summary = "규칙 기반 계획 (LLM 보정 실패)"

    # 3) 후보(candidates)가 '진실의 원천'. LLM은 순서·이유만 기여한다.
    #    → LLM이 작업을 빠뜨리거나 지어내도, 실제 단계는 항상 후보에서 나온다.
    #    권한 등급은 규칙(가드레일)으로만 결정 (LLM이 권한을 못 바꾸게).
    def _rank(cand: dict) -> int:
        op = cand["operation"]
        return llm_order.index(op) if op in llm_order else len(llm_order) + 1

    ordered_candidates = sorted(candidates, key=_rank)

    steps: list[PlanStep] = []
    for i, cand in enumerate(ordered_candidates, start=1):
        op = cand["operation"]
        if op not in OPERATION_PERMISSION:
            continue  # 안전장치 (후보는 이미 유효하지만 이중 검증)
        steps.append(PlanStep(
            order=i, operation=op, target_column=cand.get("target_column"),
            permission_level=_permission_for(op),
            rationale=llm_rationale.get(op, cand.get("rationale", "")),
        ))

    requires_approval = any(s.permission_level in ("L2", "L3") for s in steps)
    plan_obj = PreprocessingPlan(
        dataset_id=dataset_id, steps=steps,
        summary=summary or f"{len(steps)}개 단계 전처리 계획",
        requires_approval=requires_approval,
    )
    return plan_obj.model_dump()
