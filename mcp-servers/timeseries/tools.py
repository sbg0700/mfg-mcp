"""
mcp-servers/timeseries/tools.py
===============================
timeseries 모달리티 MCP 서버의 핵심 도구 7종 구현.

설계 헌법 §4의 표준 인터페이스(7종)를 그대로 구현한다.
이 7개 시그니처는 모든 모달리티 서버(image/event-log/order)가 공유할 '계약'이므로
이름·인자·반환 구조를 바꾸지 마라. (CLAUDE.md §4)

수직 슬라이스 단계라 데이터는 로컬 CSV(data/synthetic/timeseries/)를 직접 읽는다.
실데이터 교체 시: DATA_ROOT 만 진짜 KAMP 경로로 바꾸면 된다.
"""

from __future__ import annotations
import io
import os
from typing import Any

import pandas as pd

# 데이터 루트 (환경변수로 교체 가능 → 실데이터 전환 지점)
DATA_ROOT = os.environ.get(
    "TIMESERIES_DATA_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic", "timeseries"),
)


def _resolve(dataset_id: str, data_path: str | None = None) -> str:
    """dataset_id(파일명, 확장자 생략 가능) → 실제 파일 경로.
    data_path(catalog 실 lake, D-206) 주어지면 그 경로를 권위로 사용(구 ROOT 탐색 생략)."""
    if data_path is not None:
        return data_path
    name = dataset_id if dataset_id.endswith(".csv") else f"{dataset_id}.csv"
    path = os.path.normpath(os.path.join(DATA_ROOT, name))
    if not os.path.exists(path):
        raise FileNotFoundError(f"dataset not found: {dataset_id} ({path})")
    return path


# ---------------------------------------------------------------------------
# 도구 1: detect_encoding  [L1]
# ---------------------------------------------------------------------------
def detect_encoding(file_path: str) -> dict[str, Any]:
    """[챌린지 1] 인코딩 자동 감지. utf-8(-sig) → cp949 순으로 시도.
    chardet 없이도 동작하는 경량 휴리스틱."""
    candidates = ["utf-8-sig", "utf-8", "cp949", "euc-kr", "latin1"]
    with open(file_path, "rb") as f:
        raw = f.read(65536)
    for enc in candidates:
        try:
            raw.decode(enc)
            return {"file_path": file_path, "encoding": enc, "confidence": "high"}
        except (UnicodeDecodeError, LookupError):
            continue
    return {"file_path": file_path, "encoding": "unknown", "confidence": "low"}


def _smart_read(path: str, nrows: int | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """인코딩·헤더 이상을 흡수하면서 안전하게 읽는 내부 헬퍼.
    반환: (DataFrame, 감지 메모)"""
    notes: dict[str, Any] = {}
    enc = detect_encoding(path)["encoding"]
    notes["encoding"] = enc

    # [챌린지 2] 헤더가 데이터인지 감지: 첫 줄이 전부 숫자로 파싱되면 헤더 없음으로 판단
    with open(path, "r", encoding=enc, errors="replace") as f:
        first_line = f.readline().strip()
    tokens = first_line.split(",")
    numeric_tokens = sum(1 for t in tokens if _is_number(t))
    headerless = len(tokens) > 1 and numeric_tokens == len(tokens)
    notes["headerless"] = headerless

    df = pd.read_csv(
        path,
        encoding=enc,
        nrows=nrows,
        header=None if headerless else "infer",
        low_memory=False,
    )
    if headerless:
        df.columns = [f"col_{i}" for i in range(df.shape[1])]
    return df, notes


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# 도구 2: list_columns  [L1]
# ---------------------------------------------------------------------------
def list_columns(dataset_id: str, data_path: str | None = None) -> dict[str, Any]:
    """컬럼명·dtype·기초 통계 + dtype 혼재 의심 플래그 + ★의미 그룹(semantic_group)★."""
    import semantic  # 같은 디렉터리 (우려 1: 공정 의미 분류)
    path = _resolve(dataset_id, data_path)
    df, notes = _smart_read(path)
    col_names = [str(c) for c in df.columns]
    sem = semantic.classify_columns(col_names)  # {name: {semantic_group, strategy, is_grouped...}}

    cols = []
    for c in df.columns:
        series = df[c]
        cname = str(c)
        s_info = sem.get(cname, {})
        info: dict[str, Any] = {
            "name": cname,
            "dtype": str(series.dtype),
            "null_count": int(series.isna().sum()),
            "n_unique": int(series.nunique(dropna=True)),
            # ★의미 그룹 (규칙 기반 분류)
            "semantic_group": s_info.get("semantic_group", "unknown"),
            "strategy": s_info.get("strategy", "single_zscore"),
            "is_grouped": s_info.get("is_grouped", False),
        }
        # [챌린지 3] dtype 혼재 의심
        is_textual = (series.dtype == object
                      or str(series.dtype) in ("str", "string")
                      or pd.api.types.is_string_dtype(series))
        if is_textual:
            sample = series.dropna().astype(str).head(200)
            num_ratio = sample.map(_is_number).mean() if len(sample) else 0
            if 0 < num_ratio < 1:
                info["mixed_dtype_suspected"] = True
                info["numeric_ratio"] = round(float(num_ratio), 3)
        cols.append(info)

    group_summary = semantic.summarize_groups(col_names)
    return {"dataset_id": dataset_id, "n_rows": int(df.shape[0]),
            "n_cols": int(df.shape[1]), "columns": cols, "read_notes": notes,
            "semantic_groups": group_summary}


# ---------------------------------------------------------------------------
# 도구 3: get_schema  [L1]
# ---------------------------------------------------------------------------
def get_schema(dataset_id: str, data_path: str | None = None) -> dict[str, Any]:
    """JSON Schema 형태의 스키마 추출."""
    meta = list_columns(dataset_id, data_path)
    props = {}
    for c in meta["columns"]:
        dt = c["dtype"]
        json_type = ("integer" if "int" in dt else
                     "number" if "float" in dt else "string")
        props[c["name"]] = {"type": json_type, "x-dtype": dt}
    return {"dataset_id": dataset_id, "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object", "properties": props}


# ---------------------------------------------------------------------------
# 도구 4: sample  [L1]
# ---------------------------------------------------------------------------
def sample(dataset_id: str, n: int = 5, data_path: str | None = None) -> dict[str, Any]:
    """[Harness §7-2] 큰 데이터를 LLM에 직접 넣지 않기 위해 요약·샘플만 반환."""
    path = _resolve(dataset_id, data_path)
    df, notes = _smart_read(path, nrows=max(n * 4, 50))
    head = df.head(n)
    # NaN을 JSON 직렬화 가능하게
    rows = head.where(pd.notna(head), None).to_dict(orient="records")
    return {"dataset_id": dataset_id, "n": n, "rows": rows,
            "columns": [str(c) for c in df.columns], "read_notes": notes}


# ---------------------------------------------------------------------------
# 도구 5: check_constraints  [L1]
# ---------------------------------------------------------------------------
def check_constraints(dataset_id: str, constraints: dict[str, Any]) -> dict[str, Any]:
    """사용자 제약 검증. 지금은 간단한 규칙만 (하드코딩 수준, 헌법 스코프대로).
    constraints 예: {"required_columns": [...], "max_null_ratio": 0.1}"""
    meta = list_columns(dataset_id)
    violations = []
    colnames = {c["name"] for c in meta["columns"]}

    for req in constraints.get("required_columns", []):
        if req not in colnames:
            violations.append({"type": "missing_column", "column": req})

    max_null = constraints.get("max_null_ratio")
    if max_null is not None:
        for c in meta["columns"]:
            ratio = c["null_count"] / max(meta["n_rows"], 1)
            if ratio > max_null:
                violations.append({"type": "null_ratio_exceeded", "column": c["name"],
                                   "ratio": round(ratio, 3), "limit": max_null})
    return {"dataset_id": dataset_id, "passed": len(violations) == 0,
            "violations": violations}


# ---------------------------------------------------------------------------
# 도구 6: apply_preprocessing  [L1/L2/L3 — 권한 분기]
# ---------------------------------------------------------------------------
def apply_preprocessing(dataset_id: str, operations: list[dict[str, Any]],
                        permission_level: str = "L1") -> dict[str, Any]:
    """전처리 실행. 권한 등급(L1/L2/L3)에 따라 분기.
    ⚠️ 수직 슬라이스 단계: 실제 변환은 최소만, Lineage 기록 패턴을 보여주는 데 집중.
    실 구현(결측 대체·이상치 제거 등)은 Sprint 2의 Executor 에이전트로 이동 예정."""
    if permission_level not in ("L1", "L2", "L3"):
        return {"error": f"invalid permission_level: {permission_level}"}

    # L2/L3는 사용자 승인이 선행돼야 함 → 여기서는 '승인 대기' 신호만 반환
    if permission_level in ("L2", "L3"):
        return {"dataset_id": dataset_id, "status": "awaiting_approval",
                "permission_level": permission_level, "operations": operations,
                "message": "L2/L3 작업은 사용자 승인 후 실행됩니다. (1-click 승인 UI 연동 예정)"}

    # L1: 안전한 작업만 즉시 실행 (예: 인코딩 정규화 메모)
    applied = [{"op": op.get("type", "unknown"), "status": "applied (L1 stub)"}
               for op in operations]
    return {"dataset_id": dataset_id, "status": "done",
            "permission_level": "L1", "applied": applied,
            "lineage_recorded": True}  # 실제 기록은 harness/lineage.py가 담당


# ---------------------------------------------------------------------------
# 도구 7: lineage  [L1]
# ---------------------------------------------------------------------------
def lineage(dataset_id: str) -> dict[str, Any]:
    """변환 체인 조회. 수직 슬라이스에서는 harness/lineage.py의 인메모리 저장소를 조회.
    Sprint 2에서 PostgreSQL schema:lineage로 이전."""
    try:
        from harness.lineage import get_chain  # type: ignore
        return {"dataset_id": dataset_id, "chain": get_chain(dataset_id)}
    except Exception:
        return {"dataset_id": dataset_id, "chain": [],
                "note": "lineage store not wired yet (Sprint 2)"}


# 도구 레지스트리 (서버가 노출할 7종)
TOOLS = {
    "detect_encoding": detect_encoding,
    "list_columns": list_columns,
    "get_schema": get_schema,
    "sample": sample,
    "check_constraints": check_constraints,
    "apply_preprocessing": apply_preprocessing,
    "lineage": lineage,
}
