"""
agents/aggregator/context_aggregator.py — STEP 1B-2b Context Aggregator.

★생명선 (D-59)★
  - 이 모듈은 LLM을 **절대** 부르지 않는다. 추론 엔진 import 0, 모델 호출 0.
  - 모든 추출은 규칙·임계 비교·템플릿 매핑. 같은 입력 → 같은 출력 (100% 재현).
  - blueprint Part 4-4: "Context Aggregation — LLM 역할 없음, 결정론 역할 추출·구조화, 환각 위험 0".

역할: 1B-2a 세션의 `module_results`(Inspector/Planner/Executor/Validator 4단 기록)를
spec-1 Part 1-2 (바) `AggregatedContext` 스키마로 재구성한다. Page 5/6 LLM 프롬프트의
컨텍스트 소스가 된다 (LLM 입력으로 쓰이지만, LLM 호출은 본 모듈에서 일어나지 않음).

출력 5영역 (spec-1 line 283~372):
  A) pipeline_structure / pipeline_constraints — 앞단 입력 보존
  B) key_findings                              — 결정론 추출
  C) function_axis_summary                     — process/quality/maintenance/reference 분류
  D) stage_chain                               — stage별 main_findings + downstream_implication (템플릿)
  E) agent_records                             — 4단 판단 기록 원본 보존 (요약 X — Page 5/6 LLM이 직접 씀)
  F) user_intent                               — Page 5 미구현 → 항상 None
"""
from __future__ import annotations
from typing import Any


# ─────────────────────────────────────────────────────────────────────────
# downstream_implication 템플릿 (LLM 아님 — finding type → 한 줄 함의)
# ─────────────────────────────────────────────────────────────────────────
_IMPLICATION_TEMPLATES: dict[str, str] = {
    "class_imbalance":        "분류 모델 시 class_weight 또는 SMOTE 권장 (학습 데이터 편향 가능성).",
    "missing_values":         "결측 보정 적용됨. 분석 시 imputation 영향 검토 필요.",
    "dtype_mixed":            "혼재 dtype 정리(마스킹/수치화) 적용됨. 수치형 가정 재확인 권장.",
    "transformation_applied": "전처리 변환 기록 있음 (백업·lineage 존재 — rollback 가능).",
    "constraint_violation":   "사용자 제약 위반 잔여. 모델링 전 추가 정제 또는 제약 완화 검토.",
    "validation_concern":     "검증 경고 있음 — 결과 해석 시 주의.",
    "sequence_normalized":    "시퀀스/프로파일 그룹 정규화 적용 (추세/형상 보존). EDA 시 그룹 단위로 관찰 권장.",
}
_NO_FINDING_IMPLICATION = "특이사항 없음."


# ─────────────────────────────────────────────────────────────────────────
# Severity 정렬 (high > medium > low > info)
# ─────────────────────────────────────────────────────────────────────────
_SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1, "info": 0}


def _sev_rank(s: str | None) -> int:
    return _SEVERITY_RANK.get((s or "low").lower(), 0)


def _parse_module_key(key: str) -> tuple[int, int]:
    """'stage_order.module_index' → (int, int). 잘못된 형식이면 (-1, -1)."""
    try:
        a, b = str(key).split(".", 1)
        return int(a), int(b)
    except (ValueError, AttributeError):
        return -1, -1


def _find_module(pipeline_full: dict, stage_order: int, module_index: int) -> dict | None:
    """pipeline_full에서 (stage_order, module_index)의 모듈 찾기."""
    for stage in pipeline_full.get("stages", []):
        if stage.get("stage_order") == stage_order:
            for m in stage.get("modules", []):
                if m.get("index") == module_index:
                    return m
    return None


# ─────────────────────────────────────────────────────────────────────────
# 영역 E — agent_records 원본 보존
# ─────────────────────────────────────────────────────────────────────────
def _build_agent_record(stage_order: int, module: dict, mr: dict) -> dict:
    """module_results[module_key] → agent_records[i]. 손실 0(spec-1 §1-9-7) 목표.
    profile / plan / execution / validation의 핵심 필드를 거의 그대로 옮긴다."""
    profile = mr.get("profile") or {}
    plan = mr.get("plan") or {}
    execution = mr.get("execution") or {}
    validation = mr.get("validation") or {}

    # Inspector — deterministic_flags는 profile에, modality_guess/concerns/next_steps는 llm_interpretation에.
    interp = profile.get("llm_interpretation") or {}
    inspector_block = {
        "deterministic_flags": list(profile.get("deterministic_flags", [])),
        "modality_guess": interp.get("modality_guess") or profile.get("modality") or "?",
        "concerns": list(interp.get("concerns", [])),
        "recommended_next_steps": list(interp.get("recommended_next_steps", [])),
    }

    # Planner — candidate_operations는 plan 본문에 별도 보관이 없으므로 ordered와 동일 풀(=후보).
    # ordered_with_rationale는 plan.steps 그대로(필수 필드만).
    ordered = [
        {
            "operation": s.get("operation"),
            "rationale": s.get("rationale", ""),
            "permission_level": s.get("permission_level"),
            "step_key": s.get("step_key"),
            "target_column": s.get("target_column"),
            "semantic_group": s.get("semantic_group"),
        }
        for s in plan.get("steps", [])
    ]
    planner_block = {
        "candidate_operations": [
            {"operation": s.get("operation"), "target_column": s.get("target_column"),
             "semantic_group": s.get("semantic_group")}
            for s in plan.get("steps", [])
        ],
        "ordered_with_rationale": ordered,
        "llm_summary": plan.get("summary", ""),
    }

    # Executor — applied_steps는 execution.results 그대로(필수 필드만).
    applied = [
        {
            "step_key": r.get("step_key"),
            "operation": r.get("operation"),
            "target_column": r.get("target_column"),
            "semantic_group": r.get("semantic_group"),
            "permission_level": r.get("permission_level"),
            "before_stats": r.get("before_stats", {}),
            "after_stats": r.get("after_stats", {}),
            "lineage_id": r.get("lineage_id"),
            "status": r.get("status"),
            "detail": r.get("detail", ""),
        }
        for r in execution.get("results", [])
    ]
    executor_block = {
        "applied_steps": applied,
        "rolled_back": [],   # rollback 미구현 — 빈 list (스키마 자리)
        "output_path": execution.get("output_path"),
        "all_done": execution.get("all_done"),
    }

    # Validator — issues는 메시지 문자열 list (spec-1 line 360).
    validator_block = {
        "passed": bool(validation.get("passed")),
        "issues": [str(i.get("message", "")) for i in validation.get("issues", [])],
        "next_action": validation.get("next_action", ""),
        "checks": dict(validation.get("checks", {})),  # 5종 검증 결과 그대로
        "n_high": int(validation.get("n_high", 0)),
        "n_medium": int(validation.get("n_medium", 0)),
        "n_low": int(validation.get("n_low", 0)),
    }

    return {
        "stage_order": stage_order,
        "module_index": module.get("index"),
        "module_function": module.get("function"),
        "dataset_role": module.get("dataset_role") or module.get("datalake_id") or "?",
        "modality": mr.get("modality"),
        "dataset_id": mr.get("dataset_id"),
        "inspector": inspector_block,
        "planner": planner_block,
        "executor": executor_block,
        "validator": validator_block,
    }


# ─────────────────────────────────────────────────────────────────────────
# 영역 B — key_findings 결정론 추출
# ─────────────────────────────────────────────────────────────────────────
def _extract_key_findings(record: dict) -> list[dict]:
    """한 모듈의 record에서 finding을 규칙으로 추출. LLM 0, 임계 비교만."""
    so = record["stage_order"]
    fn = record.get("module_function")
    findings: list[dict] = []

    # 1) Inspector flags → dtype_mixed / class_imbalance 신호
    for flag in record["inspector"]["deterministic_flags"]:
        flag_s = str(flag)
        # dtype 혼재 (한국어/영어 둘 다 감지)
        if "mixed dtype" in flag_s or "혼재" in flag_s:
            findings.append({
                "type": "dtype_mixed", "stage_order": so, "module_function": fn,
                "column": None, "severity": "medium",
                "detail": flag_s,
            })
        # 클래스 불균형 (Inspector 신호 — 보정 적용 전이라도 사실 자체를 기록)
        if "class imbalance" in flag_s or "불균형" in flag_s:
            # minority_ratio% < 5% 면 high, 그 외 medium
            severity = "medium"
            # 메시지에서 % 추출 시도 (없으면 medium 유지)
            import re
            m = re.search(r"(\d+\.\d+)%", flag_s)
            if m:
                try:
                    pct = float(m.group(1))
                    severity = "high" if pct < 5.0 else "medium"
                except ValueError:
                    pass
            findings.append({
                "type": "class_imbalance", "stage_order": so, "module_function": fn,
                "column": None, "severity": severity,
                "detail": flag_s,
            })

    # 2) Executor applied_steps → transformation_applied / missing_values / sequence_normalized
    for step in record["executor"]["applied_steps"]:
        if step.get("status") != "done":
            continue
        op = step.get("operation")
        col = step.get("target_column")
        bs = step.get("before_stats") or {}
        as_ = step.get("after_stats") or {}

        if op == "fill_missing":
            nulls_before = bs.get("nulls")
            severity = "low"
            if isinstance(nulls_before, int) and nulls_before > 0:
                # 결측 비율로 severity 결정 (n_rows를 모르므로 절대값으로 근사)
                if nulls_before > 1000:
                    severity = "high"
                elif nulls_before > 100:
                    severity = "medium"
            findings.append({
                "type": "missing_values", "stage_order": so, "module_function": fn,
                "column": col, "severity": severity,
                "nulls_before": nulls_before, "nulls_after": as_.get("nulls"),
                "detail": f"'{col}' 결측 {nulls_before}→{as_.get('nulls')}",
            })
        elif op == "balance_classes":
            findings.append({
                "type": "class_imbalance", "stage_order": so, "module_function": fn,
                "column": col, "severity": "high",
                "applied": True,
                "detail": f"'{col}' 클래스 불균형 보정 적용 (suggested_strategy in after_stats)",
            })
        elif op == "normalize_group":
            sg = step.get("semantic_group")
            findings.append({
                "type": "sequence_normalized", "stage_order": so, "module_function": fn,
                "column": None, "severity": "low",
                "semantic_group": sg,
                "detail": f"'{sg}' 그룹 정규화 적용 (n_members={as_.get('normalized', 0)})",
            })
        elif op in ("clean_masking", "remove_outlier", "drop_column",
                    "relabel", "create_feature", "merge_external"):
            # 일반 변환 — 정보성 (Page 5/6 LLM이 컨텍스트로 알아두면 좋음)
            findings.append({
                "type": "transformation_applied", "stage_order": so, "module_function": fn,
                "column": col, "severity": "low",
                "operation": op,
                "detail": step.get("detail", "") or f"{op} 적용",
            })

    # 3) Validator issues → validation_concern / constraint_violation
    for issue in record["validator"].get("issues", []):
        # issues는 이미 문자열 list로 변환됐음. kind는 잃었으므로 message에서 추론.
        msg = str(issue)
        if "범위" in msg and ("위반" in msg or "violation" in msg.lower()):
            findings.append({
                "type": "constraint_violation", "stage_order": so, "module_function": fn,
                "column": None, "severity": "medium",
                "detail": msg,
            })
        else:
            findings.append({
                "type": "validation_concern", "stage_order": so, "module_function": fn,
                "column": None, "severity": "low",
                "detail": msg,
            })

    return findings


# ─────────────────────────────────────────────────────────────────────────
# 영역 D — stage_chain
# ─────────────────────────────────────────────────────────────────────────
def _downstream_template(findings: list[dict]) -> str:
    """stage의 finding 모음 → 한 줄 함의 (LLM 아님 — 매핑 테이블 + 결합)."""
    if not findings:
        return _NO_FINDING_IMPLICATION
    # 중복 type 제거하면서 등장 순서 유지
    seen: set[str] = set()
    parts: list[str] = []
    # 심각도 높은 순으로 정렬 후 템플릿 결합
    for f in sorted(findings, key=lambda x: -_sev_rank(x.get("severity"))):
        t = f.get("type")
        if t in seen or t not in _IMPLICATION_TEMPLATES:
            continue
        seen.add(t)
        parts.append(_IMPLICATION_TEMPLATES[t])
    return " ".join(parts) if parts else _NO_FINDING_IMPLICATION


def _build_stage_chain(pipeline_full: dict, key_findings: list[dict]) -> list[dict]:
    chain: list[dict] = []
    for stage in pipeline_full.get("stages", []):
        so = stage.get("stage_order")
        stage_findings = [f for f in key_findings if f.get("stage_order") == so]
        main_findings = [
            f"{f.get('type')}({f.get('severity')})" + (
                f": {f.get('column')}" if f.get("column") else ""
            )
            for f in stage_findings
        ]
        chain.append({
            "stage_order": so,
            "node_id": stage.get("node_id"),
            "main_findings": main_findings,
            "downstream_implication": _downstream_template(stage_findings),
        })
    return chain


# ─────────────────────────────────────────────────────────────────────────
# 영역 C — function_axis_summary
# ─────────────────────────────────────────────────────────────────────────
def _build_function_axis(key_findings: list[dict]) -> dict[str, list[dict]]:
    axis: dict[str, list[dict]] = {
        "process": [], "quality": [], "maintenance": [], "reference": []
    }
    for f in key_findings:
        fn = f.get("module_function")
        if fn in axis:
            axis[fn].append(f)
    return axis


# ─────────────────────────────────────────────────────────────────────────
# 영역 A — pipeline_structure / pipeline_constraints
# ─────────────────────────────────────────────────────────────────────────
def _build_constraints(pipeline_full: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for stage in pipeline_full.get("stages", []):
        so = stage.get("stage_order")
        for m in stage.get("modules", []):
            c = m.get("constraints") or {}
            if c:
                out[f"{so}.{m.get('index')}"] = dict(c)
    return out


# ─────────────────────────────────────────────────────────────────────────
# 공개 API — aggregate(session)
# ─────────────────────────────────────────────────────────────────────────
def aggregate(session: dict) -> dict[str, Any]:
    """PipelineSession → AggregatedContext (결정론, LLM 0).

    같은 session(dict) 입력에 대해 같은 출력을 보장한다. 호출 순서·반복에 무관.
    """
    if not isinstance(session, dict):
        raise TypeError("aggregate(): session must be a dict")

    sid = session.get("session_id") or "?"
    pipeline_full = session.get("pipeline_full") or {}
    module_results = session.get("module_results") or {}

    # 1) agent_records — 모듈 키를 안정적으로 정렬 (stage_order, module_index)
    sorted_keys = sorted(module_results.keys(), key=_parse_module_key)
    agent_records: list[dict] = []
    for k in sorted_keys:
        so, mi = _parse_module_key(k)
        mod = _find_module(pipeline_full, so, mi) or {"index": mi}
        rec = _build_agent_record(so, mod, module_results[k])
        agent_records.append(rec)

    # 2) key_findings — 각 record에서 규칙 추출, 등장 순서 유지
    key_findings: list[dict] = []
    for rec in agent_records:
        key_findings.extend(_extract_key_findings(rec))

    # 3) function_axis_summary — finding을 function별로 분류
    function_axis_summary = _build_function_axis(key_findings)

    # 4) stage_chain — stage별 요약 + downstream 함의 (템플릿)
    stage_chain = _build_stage_chain(pipeline_full, key_findings)

    # 5) pipeline_structure / pipeline_constraints — 앞단 입력 보존
    pipeline_structure = pipeline_full   # 1-1+1-2 구조 그대로
    pipeline_constraints = _build_constraints(pipeline_full)

    return {
        "session_id": sid,
        "pipeline_structure": pipeline_structure,
        "pipeline_constraints": pipeline_constraints,
        "key_findings": key_findings,
        "function_axis_summary": function_axis_summary,
        "stage_chain": stage_chain,
        "agent_records": agent_records,
        "user_intent": None,   # Page 5(분석목적 UI) 미구현 — 자리만
        "generated_by": "context_aggregator(deterministic)",
    }
