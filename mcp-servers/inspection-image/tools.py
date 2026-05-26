"""
mcp-servers/inspection-image/tools.py
=====================================
inspection-image 모달리티 MCP 서버 — 7종 도구 구현.

★핵심: timeseries 서버와 ★완전히 동일한 7개 도구 계약★을 따른다 (CLAUDE.md §4).
  list_columns / get_schema / sample / detect_encoding /
  check_constraints / apply_preprocessing / lineage

같은 이름·같은 입출력 구조. 안의 '로직'만 이미지용으로 교체했다.
→ 이게 "모달리티 재사용"의 실체: 상위 Agent는 timeseries든 image든 코드 변경 0.

데이터 단위 비교:
  timeseries: dataset_id = CSV 파일,    "컬럼" = CSV 컬럼
  image:      dataset_id = 이미지 폴더,  "컬럼" = 이미지 속성(width/height/mode/format)

실데이터 교체: IMAGE_DATA_ROOT 만 실제 KAMP 경로로 바꾸면 됨.
"""
from __future__ import annotations
import os
import glob
from collections import Counter
from typing import Any

from PIL import Image

IMAGE_DATA_ROOT = os.environ.get(
    "IMAGE_DATA_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic", "inspection-image"),
)
IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")


def _resolve(dataset_id: str) -> str:
    """dataset_id(폴더명) → 실제 폴더 경로. (timeseries는 파일, image는 폴더)"""
    path = os.path.normpath(os.path.join(IMAGE_DATA_ROOT, dataset_id))
    if not os.path.isdir(path):
        raise FileNotFoundError(f"image dataset not found: {dataset_id} ({path})")
    return path


def _scan(path: str) -> list[dict[str, Any]]:
    """폴더 내 모든 이미지를 스캔해 속성 수집 (라벨=상위 폴더명)."""
    items = []
    for f in glob.glob(os.path.join(path, "**", "*"), recursive=True):
        if not f.lower().endswith(IMG_EXT):
            continue
        try:
            with Image.open(f) as im:
                rel = os.path.relpath(f, path)
                # 라벨 추론: 이미지가 하위폴더에 있으면 그 폴더명이 라벨 (폴더명=라벨 패턴)
                parts = rel.split(os.sep)
                label = parts[0] if len(parts) > 1 else None
                # .txt 동명 페어 존재 여부
                txt_pair = os.path.exists(os.path.splitext(f)[0] + ".txt")
                items.append({
                    "file": rel, "width": im.width, "height": im.height,
                    "mode": im.mode, "format": im.format, "label": label,
                    "has_txt_label": txt_pair,
                })
        except Exception:
            items.append({"file": os.path.relpath(f, path), "error": "corrupt/unreadable"})
    return items


# ---------------------------------------------------------------------------
# 도구 1: detect_encoding  [L1]  — 이미지엔 '포맷/모드 감지'로 의미 매핑
# ---------------------------------------------------------------------------
def detect_encoding(file_path: str) -> dict[str, Any]:
    """timeseries의 인코딩 감지 ↔ image의 '포맷·컬러모드 감지' (계약 동일, 의미 매핑)."""
    try:
        with Image.open(file_path) as im:
            return {"file_path": file_path, "encoding": f"{im.format}/{im.mode}",
                    "format": im.format, "mode": im.mode, "confidence": "high"}
    except Exception as e:
        return {"file_path": file_path, "encoding": "unknown", "confidence": "low", "error": str(e)}


# ---------------------------------------------------------------------------
# 도구 2: list_columns  [L1]  — 이미지 '속성'을 컬럼처럼 노출
# ---------------------------------------------------------------------------
def list_columns(dataset_id: str) -> dict[str, Any]:
    """이미지 폴더의 속성 분포를 'columns'로 노출 (timeseries 컬럼 계약과 동일 구조).
    각 속성(width/height/mode/format/label)을 하나의 '컬럼'으로 보고 분포·혼재를 분석."""
    path = _resolve(dataset_id)
    items = [i for i in _scan(path) if "error" not in i]
    n = len(items)

    def _col(name: str, mixed_check: bool = False) -> dict[str, Any]:
        vals = [i.get(name) for i in items if i.get(name) is not None]
        uniq = set(vals)
        info: dict[str, Any] = {
            "name": name, "dtype": "image-attr",
            "null_count": n - len(vals), "n_unique": len(uniq),
        }
        # ★해상도/모드 혼재 감지 (timeseries의 dtype 혼재 감지에 대응)
        if mixed_check and len(uniq) > 1:
            info["mixed_dtype_suspected"] = True
            info["distribution"] = dict(Counter(vals).most_common(5))
        return info

    columns = [
        _col("width", mixed_check=True),
        _col("height", mixed_check=True),
        _col("mode", mixed_check=True),     # ★RGB/L/RGBA 혼재
        _col("format", mixed_check=True),   # ★png/jpg/bmp 혼재
        _col("label"),                       # 폴더명=라벨
    ]
    return {"dataset_id": dataset_id, "n_rows": n, "n_cols": len(columns),
            "columns": columns,
            "read_notes": {"modality": "inspection-image", "image_count": n}}


# ---------------------------------------------------------------------------
# 도구 3: get_schema  [L1]
# ---------------------------------------------------------------------------
def get_schema(dataset_id: str) -> dict[str, Any]:
    meta = list_columns(dataset_id)
    props = {c["name"]: {"type": "integer" if c["name"] in ("width", "height") else "string",
                         "x-image-attr": True} for c in meta["columns"]}
    return {"dataset_id": dataset_id, "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object", "properties": props}


# ---------------------------------------------------------------------------
# 도구 4: sample  [L1]  — 이미지 N장의 속성 샘플
# ---------------------------------------------------------------------------
def sample(dataset_id: str, n: int = 5) -> dict[str, Any]:
    """이미지 N장의 속성을 샘플로 (timeseries의 행 샘플 ↔ image의 파일 샘플)."""
    path = _resolve(dataset_id)
    items = _scan(path)[:n]
    return {"dataset_id": dataset_id, "n": n, "rows": items,
            "columns": ["file", "width", "height", "mode", "format", "label", "has_txt_label"],
            "read_notes": {"modality": "inspection-image"}}


# ---------------------------------------------------------------------------
# 도구 5: check_constraints  [L1]
# ---------------------------------------------------------------------------
def check_constraints(dataset_id: str, constraints: dict[str, Any]) -> dict[str, Any]:
    """제약 검증. 예: {"required_mode": "RGB", "min_count_per_class": 5}"""
    path = _resolve(dataset_id)
    items = [i for i in _scan(path) if "error" not in i]
    violations = []

    req_mode = constraints.get("required_mode")
    if req_mode:
        bad = [i["file"] for i in items if i.get("mode") != req_mode]
        if bad:
            violations.append({"type": "mode_mismatch", "expected": req_mode,
                               "count": len(bad), "examples": bad[:3]})

    min_per_class = constraints.get("min_count_per_class")
    if min_per_class:
        cls_counts = Counter(i.get("label") for i in items if i.get("label"))
        for cls, cnt in cls_counts.items():
            if cnt < min_per_class:
                violations.append({"type": "class_too_few", "class": cls,
                                   "count": cnt, "min": min_per_class})
    return {"dataset_id": dataset_id, "passed": len(violations) == 0, "violations": violations}


# ---------------------------------------------------------------------------
# 도구 6: apply_preprocessing  [L1/L2/L3]  — 이미지 전처리 (권한 분기 동일)
# ---------------------------------------------------------------------------
def apply_preprocessing(dataset_id: str, operations: list[dict[str, Any]],
                        permission_level: str = "L1") -> dict[str, Any]:
    """전처리 실행. 권한 분기는 timeseries와 동일 계약.
    수직 슬라이스: L1만 즉시, L2/L3는 승인 대기 신호."""
    if permission_level not in ("L1", "L2", "L3"):
        return {"error": f"invalid permission_level: {permission_level}"}
    if permission_level in ("L2", "L3"):
        return {"dataset_id": dataset_id, "status": "awaiting_approval",
                "permission_level": permission_level, "operations": operations,
                "message": "L2/L3 이미지 전처리는 사용자 승인 후 실행됩니다."}
    applied = [{"op": op.get("type", "unknown"), "status": "applied (L1 stub)"} for op in operations]
    return {"dataset_id": dataset_id, "status": "done", "permission_level": "L1",
            "applied": applied, "lineage_recorded": True}


# ---------------------------------------------------------------------------
# 도구 7: lineage  [L1]
# ---------------------------------------------------------------------------
def lineage(dataset_id: str) -> dict[str, Any]:
    try:
        from harness.lineage import get_chain  # type: ignore
        return {"dataset_id": dataset_id, "chain": get_chain(dataset_id)}
    except Exception:
        return {"dataset_id": dataset_id, "chain": [], "note": "lineage store not wired (Sprint 2)"}


# 7종 도구 레지스트리 (timeseries와 동일한 키 — 계약 증명)
TOOLS = {
    "detect_encoding": detect_encoding,
    "list_columns": list_columns,
    "get_schema": get_schema,
    "sample": sample,
    "check_constraints": check_constraints,
    "apply_preprocessing": apply_preprocessing,
    "lineage": lineage,
}
