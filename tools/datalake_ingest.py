#!/usr/bin/env python3
"""
tools/datalake_ingest.py — DL-2 KAMP 적재 도구 (외부 CLI).

설계 SSOT: docs/datalake_redesign/DL_BLUEPRINT.md §3, decisions D-159~D-172.

[--dry-run] (기본):
    ~/FINAL/1_data 결정론 스캔 → 메타 생성(LLM 0) → 컬럼 분류(scalar/group, D-161)
    → 적재계획(D-172 완전 레코드) 출력. **복사 0 · DB write 0 · 네트워크/LLM 0.**

[--execute] (DL-2 실적재 greenlight 뒤에만):
    data/lake/<id>/ 복사 + catalog upsert + columns full-replace.
    ★ 현재 하드 게이트 차단 (EXECUTE_ENABLED=False):
      - DB 백업 게이트(PROTOCOL §3) 미완
      - catalog.replace_columns(멱등 columns full-replace) 미구현 (Step 3 finding)
    → --execute 호출해도 즉시 abort. 2-STOP 강제.

결정론 메타 규칙 (사람 교정 가능 — Master 잠금 대상):
    modality : 파일포맷/폴더 — 이미지폴더→inspection-image, tabular(csv/xlsx)→timeseries.
               order/event-log 는 포맷 규칙상 0건(R0 정합). 의미상 order인 파일은 보고 후 사람 교정.
    function : L1~L4 접두사 시드 + lines.yaml 교차검증.
               L1→process · L2→quality · L3→maintenance · L4→reference.
    vid      : 라인 = module_N → lines.yaml line_id (D-162).
    site     : KAMP 경로서 미도출 → seed 'kamp' (단일 데모 site). 사람 교정 대상.
    datalake_id : L-slug 우선((L[1-4]_…)_kamp), 없으면 노드 slug. 충돌 시 _N 접미.
    reusable_flag : 기본 FALSE (reference/L4 는 reusable 후보 — 보고만).

불변식:
    D-161 FFT 광폭/숫자헤더 = column_kind=group descriptor (per-column 금지).
    D-167 constraints 절대 미접촉 (이 도구는 constraints 를 쓰지/지우지 않는다).
    D-172 upsert = full-record-replace (호출자가 항상 완전 레코드 전달).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import warnings
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

warnings.filterwarnings("ignore")  # openpyxl/pandas 의 디폴트 시트 경고 억제 (결정론 무관)

# ── 경로/상수 ────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent          # …/datalake-redesign
DEFAULT_DATA_ROOT = Path("~/FINAL/1_data").expanduser()
LINES_YAML = REPO_ROOT / "catalogs" / "lines.yaml"

SOURCE = "kamp"
SEED_SITE = "kamp"                                           # KAMP 경로서 site 미도출 → 단일 데모 site
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff"}
TABULAR_EXTS = {".csv", ".xlsx", ".xls", ".xltx", ".xlsm"}
LABEL_EXTS = {".txt", ".json", ".xml", ".csv"}              # 이미지셋 동반 라벨/주석
LPREFIX_FUNCTION = {"L1": "process", "L2": "quality", "L3": "maintenance", "L4": "reference"}
GROUP_MIN_NUMERIC = 16                                       # 숫자헤더 N개 이상이면 group descriptor (D-161)

# ★ 실적재 하드 게이트. 백업 게이트 + replace_columns 추가 후 Master greenlight 로만 True.
EXECUTE_ENABLED = False


# ── 인코딩 감지 (chardet 부재 → BOM 스니핑 + try-decode 폴백, 결정론) ──────
def detect_encoding(path: Path) -> str:
    """tabular 파일 인코딩 결정론 감지: BOM → utf-8-sig, 아니면 utf-8 시도 후 cp949 폴백."""
    with open(path, "rb") as fh:
        sample = fh.read(65536)
    if sample.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if sample.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    try:
        sample.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        sample.decode("cp949")
        return "cp949"                                       # 한글 KAMP (file(1) 은 iso-8859-1 로 오탐)
    except UnicodeDecodeError:
        return "latin-1"                                     # 최후 폴백 — 보고서서 플래그


def _is_float(s: str) -> bool:
    try:
        float(str(s).strip())
        return True
    except (ValueError, TypeError):
        return False


# ── tabular 헤더 읽기 (csv: csv 모듈 / xlsx: openpyxl read-only) ──────────
def read_header(path: Path, encoding: str) -> list[str]:
    ext = path.suffix.lower()
    if ext == ".csv":
        with open(path, newline="", encoding=encoding, errors="replace") as fh:
            row = next(csv.reader(fh), [])
        return [c if c.strip() else f"__unnamed_{i}" for i, c in enumerate(row)]
    # xlsx/xltx/xls — openpyxl read-only 로 활성 시트 첫 행
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    first = next(ws.iter_rows(max_row=1, values_only=True), ())
    wb.close()
    return [str(c) if c is not None else f"__unnamed_{i}" for i, c in enumerate(first)]


def infer_scalar_dtypes(path: Path, encoding: str, scalar_cols: list[str]) -> dict[str, str]:
    """scalar 컬럼만 소표본(100행)으로 dtype 시드 추정. group/FFT 컬럼은 읽지 않음.
    dry-run 시드일 뿐(실적재서 전체 재확인 가능). 실패해도 'unknown' 으로 진행."""
    if not scalar_cols:
        return {}
    import pandas as pd
    real = [c for c in scalar_cols if not c.startswith("__unnamed_")]
    try:
        ext = path.suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(path, nrows=100, encoding=encoding,
                             usecols=lambda c: c in real, on_bad_lines="skip")
        else:
            df = pd.read_excel(path, nrows=100)
            df = df[[c for c in df.columns if c in real]]
    except Exception:
        return {c: "unknown" for c in scalar_cols}
    out: dict[str, str] = {}
    for c in scalar_cols:
        if c in df.columns:
            k = df[c].dtype.kind
            out[c] = {"i": "integer", "u": "integer", "f": "float", "b": "boolean",
                      "M": "datetime", "O": "text"}.get(k, "text")
        else:
            out[c] = "unknown"
    return out


def classify_columns(header: list[str]) -> tuple[list[str], dict | None]:
    """헤더 → (scalar 컬럼명 리스트, group descriptor 또는 None) — D-161.
    숫자로 파싱되는 헤더가 GROUP_MIN_NUMERIC 이상이고 과반이면 그 묶음을 group descriptor 로,
    나머지(명명 컬럼)는 scalar 로 분리."""
    numeric = [c for c in header if _is_float(c)]
    if len(numeric) >= GROUP_MIN_NUMERIC and len(numeric) >= len(header) * 0.5:
        vals = sorted(float(c) for c in numeric)
        scalar = [c for c in header if not _is_float(c)]
        group = {
            "kind": "fft_spectrum",
            "header_kind": "numeric",
            "n_cols": len(numeric),
            "value_range": [vals[0], vals[-1]],
            "note": "숫자헤더 광폭(FFT/스펙트럼) — per-column 금지(D-161), 단일 group descriptor 등록",
        }
        return scalar, group
    return header, None


# ── lines.yaml (vid 라인맵 + function 교차검증) ──────────────────────────
def load_lines_index() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """returns (module_prefix→line_id, hint_dataset→function, node_id→function)."""
    line_map: dict[str, str] = {}
    hint_func: dict[str, str] = {}
    node_func: dict[str, set] = {}
    if not LINES_YAML.exists():
        return line_map, hint_func, {}
    data = yaml.safe_load(LINES_YAML.read_text(encoding="utf-8")) or []
    for line in data:
        lid = line.get("line_id", "")
        m = re.match(r"(module_\d+)", lid)
        if m:
            line_map[m.group(1)] = lid
        for stage in line.get("stages", []):
            nid = stage.get("node_id", "")
            for mod in stage.get("available_modules", []):
                if mod.get("hint_dataset"):
                    hint_func[mod["hint_dataset"]] = mod.get("function", "")
                if nid:
                    node_func.setdefault(nid, set()).add(mod.get("function", ""))
    # 노드의 모듈 function 이 단일할 때만 폴백 후보로 채택(모호하면 제외)
    node_func1 = {k: next(iter(v)) for k, v in node_func.items() if len(v) == 1}
    return line_map, hint_func, node_func1


# ── slug / id 유도 ───────────────────────────────────────────────────────
def derive_id_core(entry_name: str, node_slug: str) -> tuple[str, str]:
    """returns (datalake_id_core, id_rule). L-slug 우선, 없으면 노드 slug 폴백."""
    stem = re.sub(r"\.(csv|xlsx|xls|xltx|xlsm)$", "", entry_name, flags=re.I)
    m = re.match(r"(L[1-4]_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*?)_kamp", stem)
    if m:
        return m.group(1), "L-slug"
    ascii_stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_")
    if ascii_stem:
        return ascii_stem.lower(), "ascii-stem"
    return node_slug, "node-fallback(비ASCII stem)"   # 예: 고객사_모델별_주문량 → order_planning


def function_from_id(id_core: str, hint_func: dict[str, str]) -> tuple[str, str | None]:
    """L 접두사 시드 + lines.yaml 교차검증. returns (function, mismatch_or_None)."""
    pref = id_core[:2] if re.match(r"L[1-4]", id_core) else None
    seed = LPREFIX_FUNCTION.get(pref) if pref else None
    yml = hint_func.get(id_core)
    if seed and yml and seed != yml:
        return yml, f"L접두사={seed} vs lines.yaml={yml} (lines.yaml 채택)"
    return (yml or seed or "unknown"), None


# ── 스캐너 ───────────────────────────────────────────────────────────────
def scan_entry(entry: Path, module_dir: str, node_dir: str,
               line_map: dict, hint_func: dict, node_func: dict) -> dict:
    """노드 폴더의 직속 자식 1개 = 1 데이터셋. 완전 레코드(D-172) + 컬럼계획 + 진단."""
    node_slug = re.sub(r"^\d+_", "", node_dir)
    module_prefix = re.match(r"(module_\d+)", module_dir).group(1)
    vid = line_map.get(module_prefix, module_dir)            # D-162: 라인=line_id
    id_core, id_rule = derive_id_core(entry.name, node_slug)
    func, func_mismatch = function_from_id(id_core, hint_func)
    if func == "unknown" and node_slug in node_func:         # L 접두사·hint 미스 → 노드 function 폴백
        func = node_func[node_slug]
        func_mismatch = f"L/hint 미해당 → lines.yaml 노드({node_slug}) function={func} 폴백"

    rec: dict[str, Any] = {
        "datalake_id": id_core, "source": SOURCE, "name": id_core,
        "function": func, "site": SEED_SITE, "vid": vid,
        "data_path": f"data/lake/{id_core}/",
        "reusable_flag": False,
        "_source_path": str(entry), "_id_rule": id_rule,
        "_func_mismatch": func_mismatch, "_warnings": [],
        "columns": [],
    }

    if entry.is_dir():
        files = [p for p in entry.rglob("*") if p.is_file()]
        rec["size_bytes"] = sum(p.stat().st_size for p in files)
        img = [p for p in files if p.suffix.lower() in IMAGE_EXTS]
        tab = [p for p in files if p.suffix.lower() in TABULAR_EXTS]
        labels = [p for p in files if p.suffix.lower() in LABEL_EXTS]
        if img and len(img) >= len(tab):
            # 이미지 데이터셋: scalar 컬럼 없음 + image_set group descriptor 1개
            rec["modality"] = "inspection-image"
            rec["encoding"] = "binary"
            fmt = Counter(p.suffix.lower().lstrip(".") for p in img)
            rec["columns"] = [{
                "name": "image_set", "dtype": None, "column_kind": "group",
                "group_desc": {"kind": "image_set", "n_images": len(img),
                               "formats": dict(fmt), "label_files": len(labels),
                               "note": "이미지 데이터셋 — per-column 부적합, 셋 descriptor 등록"},
            }]
            if tab:
                rec["_warnings"].append(f"이미지셋에 tabular {len(tab)}개 동반(라벨/사이드카 추정)")
        else:
            # 다중파일 tabular 데이터셋 (대표 파일 헤더 사용)
            rec["modality"] = "timeseries"
            reps = sorted(tab, key=lambda p: p.name)
            rec["_multifile"] = {"n_files": len(tab), "representative": reps[0].name if reps else None}
            if reps:
                _fill_tabular_columns(rec, reps[0])
                _check_multifile_homogeneity(rec, reps)
            else:
                rec["encoding"] = "unknown"
                rec["_warnings"].append("디렉터리에 tabular/이미지 파일 없음 — 분류 불가")
    else:
        rec["size_bytes"] = entry.stat().st_size
        if entry.suffix.lower() in TABULAR_EXTS:
            rec["modality"] = "timeseries"
            _fill_tabular_columns(rec, entry)
        elif entry.suffix.lower() in IMAGE_EXTS:
            rec["modality"] = "inspection-image"
            rec["encoding"] = "binary"
        else:
            rec["modality"] = "unknown"
            rec["encoding"] = "unknown"
            rec["_warnings"].append(f"미지원 확장자: {entry.suffix}")
    return rec


def _check_multifile_homogeneity(rec: dict, files: list[Path]) -> None:
    """다중파일 tabular: 파일들이 동일 헤더 스키마인지 확인. 이종이면 플래그(대표만 반영됨)."""
    if len(files) > 24:                                      # 과도하면 비교 생략(성능)
        return
    sigs = set()
    for p in files:
        try:
            enc = detect_encoding(p) if p.suffix.lower() == ".csv" else "xlsx"
            sigs.add(tuple(read_header(p, enc)))
        except Exception:
            sigs.add(("__read_fail__", p.name))
    if len(sigs) > 1:
        rec["_warnings"].append(
            f"이종 스키마 다중파일({len(sigs)}종/{len(files)}파일) — 대표만 반영, "
            "데이터셋 분할/대표선정 사람 교정 필요")


def _fill_tabular_columns(rec: dict, path: Path) -> None:
    """tabular 파일 1개 → encoding + 컬럼(scalar/group) 채움. 실패는 warning 으로 회수."""
    # xlsx/xls/xltx 는 바이너리 office 컨테이너(내부 XML=UTF-8) → 텍스트 인코딩 N/A.
    # 텍스트 인코딩 감지는 CSV 에만 적용(아니면 ZIP 바이트가 latin-1 로 오탐됨).
    enc = detect_encoding(path) if path.suffix.lower() == ".csv" else "xlsx"
    rec["encoding"] = enc
    if enc in ("cp949", "latin-1", "utf-16"):
        rec["_warnings"].append(f"비-UTF8 인코딩={enc} (실적재 시 디코드 방침 필요)")
    try:
        header = read_header(path, enc)
    except Exception as e:
        rec["_warnings"].append(f"헤더 판독 실패: {type(e).__name__}: {str(e)[:80]}")
        return
    if not header or all(c.startswith("__unnamed_") for c in header):
        rec["_warnings"].append("헤더가 row0 에 없음(Unnamed/None) — 보고서류 추정, 사람 교정 필요")
    scalar, group = classify_columns(header)
    rec["_ncols_raw"] = len(header)
    dtypes = infer_scalar_dtypes(path, enc, scalar)
    cols = [{"name": c, "dtype": dtypes.get(c, "unknown"), "column_kind": "scalar",
             "group_desc": None} for c in scalar]
    if group:
        cols.append({"name": "spectrum", "dtype": "float", "column_kind": "group",
                     "group_desc": group})
    rec["columns"] = cols


def scan_root(root: Path, line_map: dict, hint_func: dict, node_func: dict) -> list[dict]:
    records: list[dict] = []
    for module_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for node_dir in sorted(p for p in module_dir.iterdir() if p.is_dir()):
            for entry in sorted(node_dir.iterdir()):
                records.append(scan_entry(entry, module_dir.name, node_dir.name,
                                          line_map, hint_func, node_func))
    return records


# ── 적재계획 검증/충돌 ───────────────────────────────────────────────────
def check_id_collisions(records: list[dict]) -> None:
    seen: dict[str, int] = {}
    for r in records:
        cid = r["datalake_id"]
        if cid in seen:
            seen[cid] += 1
            r["datalake_id"] = f"{cid}_{seen[cid]}"
            r["name"] = r["datalake_id"]
            r["data_path"] = f"data/lake/{r['datalake_id']}/"
            r["_warnings"].append(f"datalake_id 충돌 → {r['datalake_id']} 로 비충돌화")
        else:
            seen[cid] = 1


# ── 출력 ─────────────────────────────────────────────────────────────────
def _sz(n: float) -> str:
    for u in ("B", "K", "M"):
        if n < 1024:
            return f"{n:.0f}{u}" if u == "B" else f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}G"


def print_plan(records: list[dict]) -> None:
    print("=" * 78)
    print("DL-2 DRY-RUN 적재계획 — 복사 0 · DB write 0 · LLM 0")
    print("=" * 78)
    by_mod: dict[str, list[dict]] = {}
    for r in records:
        by_mod.setdefault(r["vid"], []).append(r)

    for vid, recs in by_mod.items():
        print(f"\n── vid (라인) = {vid}  [{len(recs)} datasets] " + "─" * 20)
        for r in recs:
            scal = sum(1 for c in r["columns"] if c["column_kind"] == "scalar")
            grp = [c for c in r["columns"] if c["column_kind"] == "group"]
            grp_str = ""
            if grp:
                g = grp[0]["group_desc"]
                if g["kind"] == "fft_spectrum":
                    grp_str = (f" + GROUP[fft_spectrum: {g['n_cols']} numeric-header, "
                               f"range={g['value_range']}]")
                else:
                    grp_str = f" + GROUP[{g['kind']}: {g.get('n_images', g.get('n_cols'))}]"
            print(f"  • {r['datalake_id']}")
            print(f"      modality={r['modality']} function={r['function']} "
                  f"site={r['site']} reusable={r['reusable_flag']}")
            print(f"      size={_sz(r['size_bytes'])} enc={r['encoding']} "
                  f"cols: {scal} scalar{grp_str}")
            print(f"      data_path={r['data_path']}  (id_rule={r['_id_rule']})")
            if r.get("_multifile"):
                mf = r["_multifile"]
                print(f"      multifile: {mf['n_files']} files (rep={mf['representative']})")
            if r["_func_mismatch"]:
                print(f"      ⚠ function: {r['_func_mismatch']}")
            for w in r["_warnings"]:
                print(f"      ⚠ {w}")

    # ── 집계 ──
    print("\n" + "=" * 78)
    print("집계")
    print("=" * 78)
    modc = Counter(r["modality"] for r in records)
    print(f"총 데이터셋(= 계획 INSERT 수): {len(records)}")
    print(f"modality 분포: {dict(modc)}")
    print(f"  → order={modc.get('order',0)}건 · event-log={modc.get('event-log',0)}건 "
          f"(R0 'order=0건' 정합)")
    encs = Counter(r["encoding"] for r in records if r["modality"] != "inspection-image")
    print(f"tabular 인코딩 분포: {dict(encs)}")
    nonutf = [r["datalake_id"] for r in records
              if r["encoding"] in ("cp949", "latin-1", "utf-16")]
    print(f"비-UTF8(디코드 방침 필요): {nonutf}")
    fft = [(r["datalake_id"], next(c["group_desc"]["n_cols"] for c in r["columns"]
            if c["column_kind"] == "group" and c["group_desc"]["kind"] == "fft_spectrum"))
           for r in records if any(c["column_kind"] == "group"
           and c["group_desc"]["kind"] == "fft_spectrum" for c in r["columns"])]
    print(f"FFT 광폭(group descriptor): {fft}")
    warned = [(r["datalake_id"], r["_warnings"]) for r in records if r["_warnings"]]
    print(f"경고/이상치 데이터셋: {len(warned)}")
    for cid, ws in warned:
        for w in ws:
            print(f"  - {cid}: {w}")


# ── 실적재 (게이트 차단) ─────────────────────────────────────────────────
def execute_load(records: list[dict], data_root: Path) -> None:
    """실적재 경로 — catalog 재사용. ★ 현재 하드 게이트로 차단(2-STOP)."""
    if not EXECUTE_ENABLED:
        sys.exit(
            "ABORT: 실적재 비활성(EXECUTE_ENABLED=False).\n"
            "  필요 선행: ① DB 백업 게이트(PROTOCOL §3) ② catalog.replace_columns "
            "(columns 멱등 full-replace) 추가 ③ Master greenlight.\n"
            "  현재 단계 = dry-run 까지만. 실적재 0."
        )
    # --- greenlight 후 활성화 (참고 구현; replace_columns 추가 전엔 도달 불가) ---
    import asyncio, shutil  # noqa: F401
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    import catalog  # noqa: F401  (재사용: upsert_entry=full-record-replace D-172 / replace_columns 필요)
    raise NotImplementedError(
        "실적재 본체는 greenlight 시 활성: per-record data/lake/<id>/ 복사 → "
        "catalog.upsert_entry(완전레코드, D-172) → catalog.replace_columns(id, cols) "
        "[columns DELETE→re-INSERT, 멱등] · constraints 미접촉(D-167)."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DL-2 KAMP datalake ingest (dry-run default)")
    ap.add_argument("--root", default=str(DEFAULT_DATA_ROOT), help="KAMP 데이터 루트")
    ap.add_argument("--dry-run", action="store_true", help="스캔+메타+계획 출력 (기본)")
    ap.add_argument("--execute", action="store_true", help="실적재 (현재 게이트 차단)")
    ap.add_argument("--json", action="store_true", help="계획을 JSON 으로 stdout 출력")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser()
    if not root.exists():
        sys.exit(f"ABORT: 데이터 루트 없음: {root}")

    line_map, hint_func, node_func = load_lines_index()
    records = scan_root(root, line_map, hint_func, node_func)
    check_id_collisions(records)

    if args.execute:
        execute_load(records, root)
        return 0

    # 기본 = dry-run (복사 0 · DB write 0)
    if args.json:
        clean = [{k: v for k, v in r.items()} for r in records]
        print(json.dumps(clean, ensure_ascii=False, indent=2, default=str))
    else:
        print_plan(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
