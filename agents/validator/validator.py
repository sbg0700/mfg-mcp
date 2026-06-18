"""
agents/validator/validator.py — Validator (사전+사후 양방향, STEP 1B-2c 강화).

역할: Executor 흐름의 양쪽에서 결정론 검증한다.
헌법 "LLM은 제안, 규칙이 결정"의 후반부 — LLM/규칙이 만든 결과를 결정론(산수·비교·규칙)으로만 검증.

★사전 검증 (Executor 전, STEP 1B-2c 신규)★
  - `validate_plan(plan, profile)` — 순서 규칙 + 작업 충돌 + L3 안전 (결정론, blocking 가능)

★사후 검증 6종 (Executor 후)★
  1. 컴플라이언스  — 모든 done 단계에 lineage가 있는가
  2. 변환 결과    — 변환이 의도대로 됐는가 (fill_missing 후 결측이 줄었나?)
  3. 계획 무결성  — 같은 작업이 중복 제안됐나
  4. 회귀         — 전처리가 데이터를 망치진 않았나 (행 급감)
  5. constraint  — 사용자 입력 constraints (D-43, D-67: ★원본 backup_path 기준★)
  6. output_health — 출력이 명백히 고장났는지 (Inf/std==0/그룹정규화 사후조건)
                    ★"고장 감지"만, "정상성 판단"·"분포 해석"은 안 함 (Page 5 EDA로 분리, D-68)★

검증 실패 시 → next_action으로 라우팅 (재시도/사람개입/검토권고).
입력: ExecutionResult + (선택) PreprocessingPlan, DataProfile, constraints.

★생명선★: 이 모듈은 LLM을 부르지 않는다 (추론 엔진 import 0).
"""
from __future__ import annotations
from typing import Any


def _check_compliance(results: list[dict]) -> list[dict]:
    """검증1 — done 단계에 lineage 누락 = 컴플라이언스 위반."""
    issues = []
    for r in results:
        if r.get("status") == "done" and not r.get("lineage_id"):
            issues.append({
                "kind": "compliance", "severity": "high", "order": r.get("order"),
                "message": f"단계 {r.get('order')}({r.get('operation')}): lineage 기록 누락 — 추적 불가",
            })
    return issues


def _check_transform_result(results: list[dict]) -> list[dict]:
    """검증2 — 변환이 의도대로 됐는가 (before/after 통계 비교)."""
    issues = []
    for r in results:
        if r.get("status") != "done":
            continue
        op = r.get("operation")
        before, after = r.get("before_stats", {}), r.get("after_stats", {})

        if op == "clean_masking":
            if not after:
                issues.append({"kind": "transform", "severity": "medium", "order": r.get("order"),
                               "message": f"단계 {r.get('order')}(clean_masking): 변환 결과 통계 없음 — 정제 여부 불명"})
        if op == "fill_missing":
            nb = before.get("nulls"); na = after.get("nulls")
            if nb is not None and na is not None and na >= nb:
                issues.append({"kind": "transform", "severity": "high", "order": r.get("order"),
                               "message": f"단계 {r.get('order')}(fill_missing): 결측이 줄지 않음 ({nb}→{na}) — 채우기 실패 의심"})
        if op == "normalize_group":
            n = after.get("normalized", 0)
            if n == 0:
                issues.append({"kind": "transform", "severity": "medium", "order": r.get("order"),
                               "message": f"단계 {r.get('order')}(normalize_group): 정규화된 컬럼 0개 — 그룹 처리 실패"})
    return issues


def _check_plan_integrity(results: list[dict], plan: dict | None) -> list[dict]:
    """검증3 — 계획 무결성: 중복 작업 감지 (width/height 중복 같은 것)."""
    issues = []
    steps = (plan or {}).get("steps", results)

    seen: dict[tuple, int] = {}
    for s in steps:
        key = (s.get("operation"), s.get("target_column"))
        if s.get("target_column") is None and s.get("semantic_group"):
            key = (s.get("operation"), "group:" + str(s.get("semantic_group")))
        seen[key] = seen.get(key, 0) + 1

    for (op, target), cnt in seen.items():
        if cnt > 1 and op is not None:
            tgt = target or "(전역)"
            issues.append({"kind": "integrity", "severity": "medium",
                           "message": f"중복 작업 감지: {op} · {tgt} 가 {cnt}회 — 계획에 중복 (정리 권장)"})

    grouped_cols: set = set()
    for s in steps:
        if s.get("operation") == "normalize_group":
            grouped_cols.update(s.get("group_members", []))
    for s in steps:
        if s.get("operation") in ("clean_masking", "fill_missing") and s.get("target_column") in grouped_cols:
            issues.append({"kind": "integrity", "severity": "low",
                           "message": f"'{s.get('target_column')}'가 그룹 정규화와 개별 작업에 동시 포함 — 순서 확인 권장"})
    return issues


def _check_regression(results: list[dict], profile: dict | None) -> list[dict]:
    """검증4 — 회귀: 전처리가 데이터를 망치진 않았나 (행 급감 등)."""
    issues = []
    final_rows = None
    for r in results:
        if r.get("operation") == "compute_stats":
            after = r.get("after_stats", {})
            final_rows = after.get("n_rows")
    orig_rows = (profile or {}).get("n_rows")

    if orig_rows and final_rows:
        loss = (orig_rows - final_rows) / orig_rows
        if loss > 0.5:
            issues.append({"kind": "regression", "severity": "high",
                           "message": f"행 급감: {orig_rows}→{final_rows} ({loss*100:.0f}% 손실) — 데이터 손실 과다"})
    return issues


def _bounds(spec: Any) -> tuple[float | None, float | None]:
    """constraint 값을 (min, max) 튜플로 정규화. 지원 형식: [min,max] 리스트 또는 {"min":..,"max":..} 딕트.
    None은 '제약 없음'으로 간주. 숫자가 아니면 None으로 변환."""
    def _num(v: Any) -> float | None:
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None
    if isinstance(spec, dict):
        return _num(spec.get("min")), _num(spec.get("max"))
    if isinstance(spec, (list, tuple)) and len(spec) >= 2:
        return _num(spec[0]), _num(spec[1])
    return None, None


def _check_constraint_violation(execution: dict, constraints: dict | None) -> list[dict]:
    """검증5 — 사용자가 Page 3에서 입력한 constraints를 데이터가 지키는가.
    ★카탈로그 디폴트(typical_ranges)가 아니라 사용자 입력 constraints 기준★ (D-43).
    ★STEP 1B-2c: 정제 전 원본(backup_path) 기준으로 검증 — 정규화 후 무의미한 위반 회피 (D-67)★
    위반 판정은 결정론(산수). LLM 안 씀. 1층 단일 모드(constraints 빈)는 skip."""
    issues: list[dict] = []
    if not constraints:
        return issues

    # remove_outlier 가 실제 적용(done)된 컬럼 — 메시지를 '검토 권장'이 아닌 '승인 제거됨'으로 정합.
    removed_cols = {
        str(r.get("target_column")) for r in (execution.get("results") or [])
        if r.get("operation") == "remove_outlier" and r.get("status") == "done"
    }

    import os
    # ★D-67: 사용자 제약은 원본 측정값 기준이므로 정제 전 backup parquet에서 검증.
    #   backup이 없으면(레거시 세션) processed로 폴백 (회귀 안전, low severity 경고는 안 함).
    src_path = execution.get("backup_path") or ""
    src_kind = "원본(backup)"
    if not isinstance(src_path, str) or not src_path.endswith(".parquet") or not os.path.exists(src_path):
        src_path = execution.get("output_path") or ""
        src_kind = "정제(processed) — 폴백"
        if not isinstance(src_path, str) or not src_path.endswith(".parquet") or not os.path.exists(src_path):
            return issues   # 이미지 등 비-parquet, 또는 파일 없음 — 검증 대상 아님

    try:
        import pandas as pd
        df = pd.read_parquet(src_path)
    except Exception as e:
        issues.append({"kind": "constraint", "severity": "low",
                       "message": f"constraint 검증 스킵 ({src_kind} 로드 실패: {e})"})
        return issues

    col_names = {str(c).lower(): str(c) for c in df.columns}
    for key, spec in constraints.items():
        lo, hi = _bounds(spec)
        if lo is None and hi is None:
            continue
        actual = col_names.get(str(key).lower())
        if not actual:
            issues.append({"kind": "constraint", "severity": "low",
                           "message": f"constraint '{key}': 일치 컬럼 없음 (검증 스킵)"})
            continue
        series = pd.to_numeric(df[actual], errors="coerce")
        n_total = int(series.notna().sum())
        if n_total == 0:
            continue
        viol_mask = pd.Series(False, index=series.index)
        if lo is not None:
            viol_mask |= series < lo
        if hi is not None:
            viol_mask |= series > hi
        n_viol = int(viol_mask.fillna(False).sum())
        if n_viol > 0:
            bound_str = f"[{lo if lo is not None else '-∞'}, {hi if hi is not None else '∞'}]"
            if actual in removed_cols:                    # 승인 제거 적용 — 보존 아님
                issues.append({
                    "kind": "constraint", "severity": "low",
                    "column": actual, "n_violations": n_viol, "n_total": n_total,
                    "bounds": [lo, hi], "source": src_kind, "removed": True,
                    "message": f"'{actual}' 범위 {bound_str} 밖 {n_viol}/{n_total}행 — 승인 제거됨(감사 기록)",
                })
            else:
                issues.append({
                    "kind": "constraint", "severity": "medium",
                    "column": actual, "n_violations": n_viol, "n_total": n_total,
                    "bounds": [lo, hi], "source": src_kind,
                    "message": f"'{actual}' 범위 {bound_str} 위반 {n_viol}/{n_total}행 — 사용자 검토 권장",
                })
    return issues


# ─────────────────────────────────────────────────────────────────────────
# Work 3 — 출력 고장 감지 (사후, 결정론). "정상성 판단" 아님 (Page 5 EDA로 분리).
# ─────────────────────────────────────────────────────────────────────────
def _check_output_health(execution: dict) -> list[dict]:
    """검증6 — 출력이 명백히 고장났는지 결정론으로 감지.

    원칙 (D-68): "100% 단언 가능한 고장"만 잡는다.
      - 표준편차 0(변환 후 다 같은 값) → 변환 실패 (고장 ✅)
      - Inf 발생 → 0으로 나눔 등 (고장 ✅)
      - 그룹 정규화 사후조건 이탈(블록 평균≈0/std≈1 아님) → 정규화 실패 (고장 ✅)
    ★개별 컬럼 평균이 0이 아니어도 정상★ — 그룹 공통 정규화는 컬럼 추세를 보존하므로
    개별 컬럼 평균이 0일 필요 없음 (1ST INJECTION VELOCITY=-1.412 등이 정상 상태).
    "분포가 정상인가/모델링에 적합한가"는 Page 5 EDA LLM의 일 — 여기선 안 한다."""
    import os
    issues: list[dict] = []
    output_path = execution.get("output_path") or ""
    if not isinstance(output_path, str) or not output_path.endswith(".parquet"):
        return issues   # 이미지 등 비-parquet 대상 아님
    if not os.path.exists(output_path):
        return issues

    try:
        import numpy as np
        import pandas as pd
        df = pd.read_parquet(output_path)
    except Exception as e:
        issues.append({"kind": "output_health", "severity": "low",
                       "message": f"output_health 검증 스킵 (processed 로드 실패: {e})"})
        return issues

    # 어떤 컬럼이 '변환에 닿았나' 수집 — std==0 false positive 회피(원래 상수 컬럼 제외)
    touched_cols: set[str] = set()
    for r in execution.get("results", []):
        if r.get("status") != "done":
            continue
        if r.get("target_column"):
            touched_cols.add(str(r["target_column"]))
        for m in r.get("group_members", []) or []:
            touched_cols.add(str(m))

    num = df.select_dtypes("number")
    for col in num.columns:
        s = num[col]
        arr = s.to_numpy(dtype=float)
        # (a) Inf 발생 — 변환 오류(0으로 나눔 등) 100% 단언
        if bool(np.isinf(arr).any()):
            issues.append({
                "kind": "output_health", "severity": "high", "column": str(col),
                "message": f"'{col}'에 Inf 발생 — 변환 오류(0으로 나눔 등) 의심",
            })
        # (b) 표준편차 0 — 변환이 적용된 컬럼에 한해 (원래 상수 컬럼 제외)
        if str(col) in touched_cols and int(s.notna().sum()) > 1 and float(s.std(ddof=0)) == 0.0:
            issues.append({
                "kind": "output_health", "severity": "high", "column": str(col),
                "message": f"'{col}' 변환 후 표준편차 0 — 전부 같은 값(변환 실패) 의심",
            })

    # (c) normalize_group 사후조건 — ★그룹 단위로만★ 평균≈0, std≈1 확인
    #     개별 컬럼 평균≈0 강제 안 함 (그룹 공통 정규화는 컬럼 평균 0 아님 — 추세 보존)
    for r in execution.get("results", []):
        if r.get("operation") != "normalize_group" or r.get("status") != "done":
            continue
        members = [m for m in (r.get("group_members") or []) if m in num.columns]
        if not members:
            continue
        block = num[members].to_numpy(dtype=float).ravel()
        block = block[~np.isnan(block)]
        if block.size <= 1:
            continue
        gmean = float(np.mean(block))
        gstd = float(np.std(block, ddof=0))
        if abs(gmean) > 0.1 or abs(gstd - 1.0) > 0.1:
            issues.append({
                "kind": "output_health", "severity": "medium",
                "semantic_group": r.get("semantic_group"),
                "group_mean": round(gmean, 4), "group_std": round(gstd, 4),
                "message": (f"그룹 '{r.get('semantic_group')}' 정규화 사후조건 이탈 "
                            f"(그룹 평균 {gmean:.3f}, 표준편차 {gstd:.3f} — z-score면 0/1 근처여야)"),
            })
    return issues


# ─────────────────────────────────────────────────────────────────────────
# Work 2 — 사전 검증 validate_plan (Executor 전, 결정론, sync)
# ─────────────────────────────────────────────────────────────────────────
# 작업 유형별 단계 순위: 작을수록 먼저 와야 함. 9는 "언제 와도 됨"(예외).
_ORDER_RANK: dict[str, int] = {
    "detect_encoding": 0, "reparse_header": 0,
    "clean_masking": 1,
    "fill_missing": 2, "remove_outlier": 2,
    "normalize_group": 3, "balance_classes": 3, "create_feature": 3,
    "drop_column": 5, "relabel": 5, "merge_external": 5,
    "compute_stats": 9,   # 예외 — 어디 와도 됨
}


def validate_plan(plan: dict, profile: dict | None = None) -> dict:
    """[사전 검증] Executor 실행 전, 계획의 타당성을 결정론으로 검증.

    LLM 0. 순서 규칙 + 작업 충돌 + L3 안전 선행 정보성.
    blocking 기준: high(작업 충돌)만 → 실행 차단 권고. 순서 의심(medium)·L3(low)은 경고만.

    반환:
      { "plan_ok": bool, "plan_issues": [{kind,severity,message,...}], "blocking": bool }
    """
    steps = (plan or {}).get("steps", []) or []
    issues: list[dict] = []

    # (a) 순서 규칙 — 인코딩/헤더 < 정제 < 정규화 < 결측보정 등 < (compute_stats 예외)
    last_rank = -1
    for s in steps:
        op = s.get("operation")
        r = _ORDER_RANK.get(op, 4)   # 미정의는 중간 rank
        if op != "compute_stats" and r < last_rank:
            issues.append({
                "kind": "plan_order", "severity": "medium",
                "operation": op, "rank": r, "prev_max_rank": last_rank,
                "message": (f"순서 의심: {op}(rank {r})가 앞 작업(rank {last_rank})보다 뒤 — "
                            f"인코딩/정제 선행 권장"),
            })
        if op != "compute_stats":
            last_rank = max(last_rank, r)

    # (b) 작업 충돌 — drop_column 대상 컬럼을 다른 작업도 건드리면 모순 (high → blocking)
    dropped: set[str] = set()
    for s in steps:
        if s.get("operation") == "drop_column" and s.get("target_column"):
            dropped.add(str(s["target_column"]))
    for s in steps:
        tgt = s.get("target_column")
        if tgt and str(tgt) in dropped and s.get("operation") != "drop_column":
            issues.append({
                "kind": "plan_conflict", "severity": "high",
                "operation": s.get("operation"), "target_column": tgt,
                "message": (f"충돌: '{tgt}'를 drop_column 하는데 다른 작업({s.get('operation')})도 "
                            f"그 컬럼 대상 — 어느 쪽이 먼저든 모순"),
            })

    # (c) L3 안전 — 정보성 (현재 executor가 항상 백업 뜨므로 통과하지만 plan 차원에서 기록)
    for s in steps:
        if s.get("permission_level") == "L3":
            issues.append({
                "kind": "plan_l3_notice", "severity": "low",
                "operation": s.get("operation"), "target_column": s.get("target_column"),
                "message": f"L3 작업({s.get('operation')}) 포함 — 백업·명시 승인 필요",
            })

    n_high = sum(1 for i in issues if i.get("severity") == "high")
    return {
        "plan_ok": n_high == 0,
        "plan_issues": issues,
        "blocking": n_high > 0,
        "n_high": n_high,
        "n_medium": sum(1 for i in issues if i.get("severity") == "medium"),
        "n_low": sum(1 for i in issues if i.get("severity") == "low"),
    }


async def validate(execution: dict, plan: dict | None = None,
                   profile: dict | None = None,
                   constraints: dict | None = None) -> dict:
    """ExecutionResult 검증 → ValidationReport. 6종 검증 수행 (사후, STEP 1B-2c 확장).
    plan/profile을 주면 무결성·회귀 검증이 강화됨.
    constraints를 주면 5번째 검증(constraint 위반) 동작. 안 주면 skip (회귀 없음)."""
    results = execution.get("results", [])

    done = [r for r in results if r.get("status") == "done"]
    failed = [r for r in results if r.get("status") == "failed"]
    pending = [r for r in results if r.get("status") == "awaiting_approval"]

    issues: list[dict] = []
    issues += _check_compliance(results)                        # 1. 컴플라이언스
    issues += _check_transform_result(results)                  # 2. 변환 결과
    issues += _check_plan_integrity(results, plan)              # 3. 계획 무결성
    issues += _check_regression(results, profile)               # 4. 회귀
    issues += _check_constraint_violation(execution, constraints)  # 5. constraint (★원본 backup_path 기준 — D-67)
    issues += _check_output_health(execution)                   # 6. ★output_health (고장 감지만, 분포 해석 X — D-68)

    high = [i for i in issues if i.get("severity") == "high"]
    medium = [i for i in issues if i.get("severity") == "medium"]
    low = [i for i in issues if i.get("severity") == "low"]

    if failed or high:
        next_action = "retry_or_human"
    elif pending:
        next_action = "await_approval"
    elif medium:
        next_action = "review_recommended"
    else:
        next_action = "ready_for_ml"

    checks = {
        "compliance": not any(i["kind"] == "compliance" for i in issues),
        "transform": not any(i["kind"] == "transform" for i in issues),
        "integrity": not any(i["kind"] == "integrity" for i in issues),
        "regression": not any(i["kind"] == "regression" for i in issues),
        "constraint": not any(i["kind"] == "constraint" for i in issues),
        "output_health": not any(i["kind"] == "output_health" for i in issues),
    }

    return {
        "dataset_id": execution.get("dataset_id"),
        "passed": len(high) == 0 and len(failed) == 0,
        "n_done": len(done), "n_failed": len(failed), "n_pending": len(pending),
        "checks": checks,
        "issues": issues,
        "n_high": len(high), "n_medium": len(medium), "n_low": len(low),
        "next_action": next_action,
    }
