"""
mcp-servers/event-log/tools.py
==============================
event-log 모달리티 MCP 서버 — 7종 도구 구현.

★timeseries/image와 ★동일한 7개 도구 계약★. 로직만 event-log용.
  list_columns / get_schema / sample / detect_encoding /
  check_constraints / apply_preprocessing / lineage

event-log 특유 처리:
  - 멀티시트 Excel 통합 (시트마다 다른 구조)
  - 클래스 불균형 감지 (PASS_YN 등 라벨 컬럼)
  - LOT 첫 행 NaN 메타 감지

데이터 단위:
  dataset_id = CSV 파일 또는 Excel 파일(멀티시트)
  "컬럼" = 통합된 컬럼 / "행" = LOT 이벤트

실데이터 교체: EVENTLOG_DATA_ROOT 만 실제 KAMP 경로로.
"""
from __future__ import annotations
import os
import glob
from typing import Any

import pandas as pd

EVENTLOG_DATA_ROOT = os.environ.get(
    "EVENTLOG_DATA_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic", "event-log"),
)
# 라벨로 추정되는 컬럼명 (불균형 검사 대상)
LABEL_HINTS = {"PASS_YN", "JUDGE", "JUDGEMENT", "RESULT", "OK_NG", "DEFECT_TYPE", "LABEL"}


def _resolve(dataset_id: str) -> str:
    name = dataset_id
    if not (name.endswith(".csv") or name.endswith(".xlsx")):
        # 확장자 없으면 둘 다 시도
        for ext in (".csv", ".xlsx"):
            p = os.path.join(EVENTLOG_DATA_ROOT, name + ext)
            if os.path.exists(p):
                return p
    p = os.path.join(EVENTLOG_DATA_ROOT, name)
    if not os.path.exists(p):
        raise FileNotFoundError(f"event-log dataset not found: {dataset_id}")
    return p


def _load(path: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """CSV/Excel 로드. Excel 멀티시트면 통합하고 메타 반환."""
    meta: dict[str, Any] = {"source_format": "csv", "sheets": None, "merged": False}
    if path.endswith(".xlsx"):
        meta["source_format"] = "xlsx"
        sheets = pd.read_excel(path, sheet_name=None)  # 모든 시트
        meta["sheets"] = {name: list(df.columns) for name, df in sheets.items()}
        if len(sheets) > 1:
            # ★멀티시트 통합: 공통 키(LOT_NO)로 outer merge
            meta["merged"] = True
            dfs = list(sheets.values())
            key = "LOT_NO" if all("LOT_NO" in d.columns for d in dfs) else None
            if key:
                merged = dfs[0]
                for d in dfs[1:]:
                    merged = merged.merge(d, on=key, how="outer", suffixes=("", "_dup"))
                return merged, meta
            return pd.concat(dfs, ignore_index=True), meta
        return list(sheets.values())[0], meta
    # CSV (인코딩 흡수)
    for enc in ("utf-8-sig", "cp949", "latin1"):
        try:
            return pd.read_csv(path, encoding=enc), meta
        except (UnicodeDecodeError, LookupError):
            continue
    return pd.read_csv(path, encoding="utf-8", errors="replace"), meta


def detect_encoding(file_path: str) -> dict[str, Any]:
    """CSV 인코딩 / Excel 포맷 감지."""
    if file_path.endswith(".xlsx"):
        return {"file_path": file_path, "encoding": "xlsx (multi-sheet)", "confidence": "high"}
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with open(file_path, encoding=enc) as f:
                f.read(2048)
            return {"file_path": file_path, "encoding": enc, "confidence": "high"}
        except (UnicodeDecodeError, LookupError):
            continue
    return {"file_path": file_path, "encoding": "unknown", "confidence": "low"}


def list_columns(dataset_id: str) -> dict[str, Any]:
    """통합 후 컬럼 분석 + 불균형/NaN 감지 (timeseries 계약과 동일 구조)."""
    path = _resolve(dataset_id)
    df, meta = _load(path)
    columns = []
    for name in df.columns:
        s = df[name]
        info: dict[str, Any] = {
            "name": str(name), "dtype": str(s.dtype),
            "null_count": int(s.isna().sum()), "n_unique": int(s.nunique(dropna=True)),
        }
        # ★클래스 불균형 감지 (라벨 컬럼)
        if str(name).upper() in LABEL_HINTS or s.nunique(dropna=True) == 2:
            vc = s.value_counts(normalize=True)
            if len(vc) == 2 and vc.min() < 0.1:  # 소수 클래스 10% 미만 = 불균형
                info["imbalance_suspected"] = True
                info["minority_ratio"] = round(float(vc.min()), 4)
                info["distribution"] = {str(k): int(v) for k, v in s.value_counts().items()}
        columns.append(info)

    read_notes: dict[str, Any] = {"modality": "event-log",
                                   "source_format": meta["source_format"]}
    if meta["merged"]:
        read_notes["multi_sheet_merged"] = True
        read_notes["sheets"] = meta["sheets"]
    return {"dataset_id": dataset_id, "n_rows": len(df), "n_cols": len(df.columns),
            "columns": columns, "read_notes": read_notes}


def get_schema(dataset_id: str) -> dict[str, Any]:
    meta = list_columns(dataset_id)
    props = {c["name"]: {"type": "number" if "float" in c["dtype"] or "int" in c["dtype"] else "string"}
             for c in meta["columns"]}
    return {"dataset_id": dataset_id, "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object", "properties": props}


def sample(dataset_id: str, n: int = 5) -> dict[str, Any]:
    path = _resolve(dataset_id)
    df, _ = _load(path)
    rows = df.head(n).where(pd.notna(df.head(n)), None).to_dict(orient="records")
    return {"dataset_id": dataset_id, "n": n, "rows": rows,
            "columns": [str(c) for c in df.columns],
            "read_notes": {"modality": "event-log"}}


def check_constraints(dataset_id: str, constraints: dict[str, Any]) -> dict[str, Any]:
    path = _resolve(dataset_id)
    df, _ = _load(path)
    violations = []
    min_minority = constraints.get("min_minority_ratio")
    label_col = constraints.get("label_column")
    if min_minority and label_col and label_col in df.columns:
        vc = df[label_col].value_counts(normalize=True)
        if len(vc) and vc.min() < min_minority:
            violations.append({"type": "class_imbalance", "column": label_col,
                               "minority_ratio": round(float(vc.min()), 4), "min": min_minority})
    return {"dataset_id": dataset_id, "passed": len(violations) == 0, "violations": violations}


def apply_preprocessing(dataset_id: str, operations: list[dict[str, Any]],
                        permission_level: str = "L1") -> dict[str, Any]:
    if permission_level not in ("L1", "L2", "L3"):
        return {"error": f"invalid permission_level: {permission_level}"}
    if permission_level in ("L2", "L3"):
        return {"dataset_id": dataset_id, "status": "awaiting_approval",
                "permission_level": permission_level, "operations": operations}
    return {"dataset_id": dataset_id, "status": "done", "permission_level": "L1",
            "applied": [{"op": op.get("type"), "status": "applied (L1 stub)"} for op in operations]}


def lineage(dataset_id: str) -> dict[str, Any]:
    try:
        from harness.lineage import get_chain  # type: ignore
        return {"dataset_id": dataset_id, "chain": get_chain(dataset_id)}
    except Exception:
        return {"dataset_id": dataset_id, "chain": [], "note": "lineage store not wired (Sprint 2)"}


TOOLS = {
    "detect_encoding": detect_encoding,
    "list_columns": list_columns,
    "get_schema": get_schema,
    "sample": sample,
    "check_constraints": check_constraints,
    "apply_preprocessing": apply_preprocessing,
    "lineage": lineage,
}
