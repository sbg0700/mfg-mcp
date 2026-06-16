"""
tests/test_ssot_cross.py — 이중 SSOT(lines.yaml ↔ datalake_manifest.yaml) 교차 정합 박제
(DL-3b ⓐ, D-188). yaml 파싱만 — DB·throwaway 컨테이너 불요.

배경: Page 1→3 바인딩 키(line_id→vid)와 Page 2 참조(hint_dataset→datalake_id)가
서로 다른 권위 파일에 살아 order_cp949형 silent 괴리가 가능 — 상시 테스트로 차단(D-182).
"""
from __future__ import annotations

from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parent.parent
_LINES = _REPO / "catalogs" / "lines.yaml"
_MANIFEST = _REPO / "catalogs" / "datalake_manifest.yaml"

# D-177 #15 — 데모 적재 보류(excluded) 2건. lines.yaml hint가 이들을 가리키는 것은
# 알려진 상태(보류이지 dangling 아님). 집합을 박제해 silent 증가를 차단.
KNOWN_EXCLUDED_HINTS = {"L1_mct_tool_improve", "L3_mct_condition_inspect"}


def _load():
    lines = yaml.safe_load(_LINES.read_text(encoding="utf-8"))
    manifest = yaml.safe_load(_MANIFEST.read_text(encoding="utf-8"))
    return lines, manifest


def _walk_collect(obj, key, out):
    if isinstance(obj, dict):
        if key in obj:
            out.add(obj[key])
        for v in obj.values():
            _walk_collect(v, key, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_collect(v, key, out)


def test_hint_dataset_subset_of_manifest_ids():
    """lines.yaml hint_dataset 전수 ⊆ manifest id 집합(datasets ∪ excluded) — dangling 0."""
    lines, manifest = _load()
    hints: set[str] = set()
    _walk_collect(lines, "hint_dataset", hints)
    assert hints, "hint_dataset 0건 — 파싱 실패 의심"
    loaded = {d["datalake_id"] for d in manifest["datasets"]}
    excluded = {d["datalake_id"] for d in manifest.get("excluded", [])}
    dangling = hints - loaded - excluded
    assert dangling == set(), f"manifest 에 없는 hint_dataset(dangling): {sorted(dangling)}"
    # 보류(excluded) 참조는 알려진 2건 고정 — 늘어나면 의도 확인 필요(anti-silent)
    assert hints & excluded == KNOWN_EXCLUDED_HINTS


def test_line_id_equals_manifest_vid_set():
    """line_id 집합 = manifest vid DISTINCT 집합 (D-188 — 부분집합 넘어 동일 집합 실측).
    신 Page 3는 session line_id 를 vid 필터로 직사용한다."""
    lines, manifest = _load()
    line_ids: set[str] = set()
    _walk_collect(lines, "line_id", line_ids)
    vids = {d["vid"] for d in manifest["datasets"]}
    vids |= {d["vid"] for d in manifest.get("excluded", []) if "vid" in d}
    assert line_ids == vids == {
        "module_1_metal_processing", "module_2_forming_joining",
        "module_3_polymer_electronic",
    }
    # vid 분포 박제 (Phase 0 (i) 실측): manifest 전 행 34 = 13+9+12 (excluded 2건 모두
    # module_1) → 적재 32 = 11+9+12.
    from collections import Counter
    dist_all = Counter(d["vid"] for d in manifest["datasets"])
    dist_all.update(d["vid"] for d in manifest.get("excluded", []) if "vid" in d)
    assert dist_all == {"module_1_metal_processing": 13,
                        "module_2_forming_joining": 9,
                        "module_3_polymer_electronic": 12}
    dist_loaded = Counter(d["vid"] for d in manifest["datasets"])
    assert dist_loaded == {"module_1_metal_processing": 11,
                           "module_2_forming_joining": 9,
                           "module_3_polymer_electronic": 12}
