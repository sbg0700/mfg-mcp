#!/usr/bin/env python3
"""
tools/datalake_ingest.py — DL-2 KAMP 적재 도구 (외부 CLI, manifest-driven).

설계 SSOT: catalogs/datalake_manifest.yaml (메타 권위) + DL_BLUEPRINT.md §3, decisions D-159~D-177.

★ D-173 리팩터: 파일시스템 추론(파일명 유도 datalake_id·폴더 파싱 vid) 폐기.
   이 도구는 manifest 를 "읽기만" 한다(파생 0):
     datalake_id · vid · modality · function · site · company · format · encoding = manifest 권위
     scalar 컬럼 이름·dtype = 파일 헤더 실측(사실 읽기)
     group descriptor(waveform/image_set) = manifest 권위 + 파일 검산
     node · capture = provenance 만 — DB 미적재(entries 14컬럼에 없음, D-175). 명시 제외(silent drop 금지).

[--dry-run] (기본):
    manifest 읽기 → ~/FINAL/1_data 정합 검산(경로 존재·인코딩 디코드·group 검산·size 실측)
    → 적재계획(D-172 완전 레코드) 출력. **복사 0 · DB write 0 · 네트워크/LLM 0.**

[--execute] (DL-2 실적재 greenlight 뒤에만):
    레코드별 src→data/lake/<id>/ 복사(인코딩·형태별 분기) + catalog.upsert_entry(완전레코드)
    + catalog.replace_columns(columns full-replace). constraints 미접촉(D-167).
    ★ 하드 게이트 (EXECUTE_ENABLED=False) — 2-STOP:
      본체·replace_columns 구현 완료. 운영 선행(① DB 백업 ③ 라이브 ALTER format/company)
      + ④ Master greenlight 후 EXECUTE_ENABLED=True 커밋(Phase 2)으로만 활성.
    → 그 전까지 --execute 호출해도 즉시 abort.

불변식:
    D-161/D-176 광폭/숫자헤더 = column_kind=group descriptor (per-column 금지).
                L3 vibration = raw 시간영역 waveform (fft 아님, axis=time_offset_s/fs_hz/window).
    D-167 constraints 절대 미접촉 (이 도구는 constraints 를 쓰지/지우지 않는다).
    D-172 upsert = full-record-replace (호출자가 항상 완전 레코드 전달).
    D-173 manifest 권위 = 파생 0 / node·capture 명시 제외(anti-silent-drop).
"""
from __future__ import annotations

import argparse
import csv
import json
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
MANIFEST = REPO_ROOT / "catalogs" / "datalake_manifest.yaml"  # 메타 권위 (SSOT, D-173)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff"}
TABULAR_EXTS = {".csv", ".xlsx", ".xls", ".xltx", ".xlsm"}
LABEL_EXTS = {".txt", ".json", ".xml", ".csv"}              # 이미지셋 동반 라벨/주석

# ★ 실적재 하드 게이트. 백업 게이트 + replace_columns 추가 후 Master greenlight 로만 True.
EXECUTE_ENABLED = False


# ── manifest 로딩 (권위 메타) ─────────────────────────────────────────────
def load_manifest() -> tuple[list[dict], list[dict]]:
    """returns (datasets, excluded). manifest 가 SSOT — 여기서 파생/추론 0."""
    if not MANIFEST.exists():
        sys.exit(f"ABORT: manifest 없음: {MANIFEST}")
    doc = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    datasets = doc.get("datasets", [])
    excluded = doc.get("excluded", [])
    if not datasets:
        sys.exit("ABORT: manifest.datasets 비어있음")
    return datasets, excluded


# ── 인코딩 디코드 검증 (cp949/utf-8 — 실측 검산) ──────────────────────────
def verify_decode(path: Path, encoding: str) -> str | None:
    """선언 encoding 으로 파일 일부를 디코드 시도. 실패면 사유 문자열, 성공이면 None.
    binary(xlsx/이미지) 는 텍스트 디코드 비대상 → None."""
    if encoding in ("binary",):
        return None
    codec = "utf-8-sig" if encoding == "utf-8-sig" else encoding
    try:
        with open(path, "rb") as fh:
            sample = fh.read(1 << 20)        # 1MB 표본
        sample.decode(codec)
        return None
    except (LookupError, UnicodeDecodeError) as e:
        return f"{encoding} 디코드 실패: {type(e).__name__}"


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
        codec = "utf-8-sig" if encoding == "utf-8-sig" else (encoding or "utf-8")
        with open(path, newline="", encoding=codec, errors="replace") as fh:
            row = next(csv.reader(fh), [])
        return [c if c.strip() else f"__unnamed_{i}" for i, c in enumerate(row)]
    # xlsx/xltx/xls — openpyxl read-only 로 활성 시트 첫 행 (바이너리 컨테이너, 텍스트 인코딩 N/A)
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    first = next(ws.iter_rows(max_row=1, values_only=True), ())
    wb.close()
    return [str(c) if c is not None else f"__unnamed_{i}" for i, c in enumerate(first)]


def _uniquify_headers(names: list[str]) -> tuple[list[str], list[str]]:
    """비어있지 않은 중복 헤더를 결정론적 접미(__dup2,__dup3,…)로 유니크화. 드롭 0.
    returns (유니크 이름들, ['원본→신규', …]). 빈 헤더는 read_header가 이미 __unnamed_i 로 처리.
    datalake.columns PK=(datalake_id,name) 위반(replace_columns 크래시) 방지 + anti-silent
    (중복을 조용히 버리지 않고 보존·재명명 후 경고)."""
    used: set[str] = set()
    counts: dict[str, int] = {}
    out: list[str] = []
    renamed: list[str] = []
    for n in names:
        if n not in used:
            used.add(n)
            counts[n] = 1
            out.append(n)
            continue
        counts[n] += 1
        new = f"{n}__dup{counts[n]}"
        while new in used:                       # 생성 이름이 기존과 충돌 시 카운터 증가
            counts[n] += 1
            new = f"{n}__dup{counts[n]}"
        used.add(new)
        out.append(new)
        renamed.append(f"{n}→{new}")
    return out, renamed


def infer_scalar_dtypes(path: Path, encoding: str, scalar_cols: list[str]) -> dict[str, str]:
    """scalar 컬럼만 소표본(100행)으로 dtype 시드 추정. group 컬럼은 읽지 않음.
    dry-run 시드일 뿐. 실패해도 'unknown' 으로 진행."""
    if not scalar_cols:
        return {}
    import pandas as pd
    real = [c for c in scalar_cols if not c.startswith("__unnamed_")]
    try:
        ext = path.suffix.lower()
        if ext == ".csv":
            codec = "utf-8-sig" if encoding == "utf-8-sig" else (encoding or "utf-8")
            df = pd.read_csv(path, nrows=100, encoding=codec,
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


# ── 파일/폴더 실측 (size·group 검산) ──────────────────────────────────────
def measure_size(path: Path) -> int:
    if path.is_dir():
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    return path.stat().st_size


def verify_image_set(path: Path, declared: dict, warnings_out: list[str]) -> dict:
    """이미지 폴더 실측 → manifest group_desc 검산. manifest 권위 유지, 불일치는 플래그."""
    files = [p for p in path.rglob("*") if p.is_file()]
    img = [p for p in files if p.suffix.lower() in IMAGE_EXTS]
    labels = [p for p in files if p.suffix.lower() in LABEL_EXTS]
    fmts = dict(Counter(p.suffix.lower().lstrip(".") for p in img))
    measured = {"kind": "image_set", "n_images": len(img),
                "formats": fmts, "label_files": len(labels)}
    dn = declared.get("n_images")
    if dn is not None and dn != len(img):
        warnings_out.append(f"image_set n_images 불일치: manifest={dn} vs 실측={len(img)}")
    df = declared.get("formats")
    if df is not None and df != fmts:
        warnings_out.append(f"image_set formats 불일치: manifest={df} vs 실측={fmts}")
    # manifest 권위 우선, 실측값을 _measured 로 동봉(검산 흔적)
    out = dict(declared)
    out["_measured"] = measured
    return out


def verify_waveform(path: Path, encoding: str, declared: dict,
                    warnings_out: list[str]) -> tuple[list[str], dict]:
    """waveform csv 헤더 실측 → (scalar 컬럼명, group_desc 검산). manifest 권위 유지(D-176)."""
    header = read_header(path, encoding)
    numeric = [c for c in header if _is_float(c)]
    scalar = [c for c in header if not _is_float(c)]
    n_decl = declared.get("n_cols")
    if n_decl is not None and n_decl != len(numeric):
        warnings_out.append(f"waveform n_cols 불일치: manifest={n_decl} vs 실측={len(numeric)}")
    if numeric:
        vals = sorted(float(c) for c in numeric)
        win = declared.get("window")
        if win and (abs(vals[0] - win[0]) > 1e-6 or abs(vals[-1] - win[1]) > 1e-6):
            warnings_out.append(
                f"waveform window 불일치: manifest={win} vs 실측=[{vals[0]}, {vals[-1]}]")
    ts = declared.get("timestamp_col")
    if ts and ts not in scalar:
        warnings_out.append(f"waveform timestamp_col '{ts}' 헤더 1열에 없음(실측 scalar={scalar})")
    out = dict(declared)
    out["_measured"] = {"n_numeric": len(numeric), "scalar_cols": scalar}
    return scalar, out


# ── manifest dataset → 적재 레코드 (entries 14컬럼 + columns) ──────────────
def build_record(ds: dict, data_root: Path) -> dict:
    """manifest 1행 → 완전 레코드(D-172) + per-column + 진단. 경로/인코딩/group 검산."""
    warnings_out: list[str] = []
    src = (data_root / ds["path"]).expanduser()

    # ── entries 14컬럼 명시 화이트리스트 (anti-silent-drop, D-173) ──
    # node·capture 는 provenance → DB 미적재(entries 컬럼 없음, D-175). 아래 14키만 의도적 선택.
    rec: dict[str, Any] = {
        "datalake_id": ds["datalake_id"],
        "source":      ds["source"],
        "name":        ds["name"],
        "modality":    ds["modality"],
        "function":    ds["function"],
        "site":        ds["site"],
        "vid":         ds["vid"],
        "size_bytes":  0,                                   # 아래 실측
        "encoding":    ds["encoding"],
        "format":      ds["format"],
        "data_path":   f"data/lake/{ds['datalake_id']}/",   # id 종속 (D-159)
        "reusable_flag": bool(ds.get("reusable_flag", False)),
        "company":     ds["company"],
        # ↑ 여기까지가 datalake.entries 적재 대상. node/capture 의도적 제외(provenance).
        "columns":     [],
        # ── 진단(dry-run 전용, DB 미적재) ──
        "_source_path": str(src),
        "_node":        ds.get("node"),                     # provenance (DB 미적재)
        "_capture":     ds.get("capture"),                  # provenance (DB 미적재)
        "_normalize_to": ds.get("normalize_to"),
        "_warnings":    warnings_out,
    }

    # 1) 경로 존재 검산
    if not src.exists():
        warnings_out.append(f"경로 없음: {src}")
        return rec
    rec["size_bytes"] = measure_size(src)

    # 2) 인코딩 디코드 검산 (csv 류; 폴더는 대표 파일로)
    if src.is_file() and src.suffix.lower() == ".csv":
        dec = verify_decode(src, ds["encoding"])
        if dec:
            warnings_out.append(dec)

    # 3) per-column — manifest group 권위 + 파일 검산 / scalar 는 헤더 실측
    manifest_cols = ds.get("columns")
    group_decl = None
    if manifest_cols:
        for c in manifest_cols:
            if c.get("column_kind") == "group":
                group_decl = c
                break

    if ds["modality"] == "inspection-image":
        gd = group_decl["group_desc"] if group_decl else {"kind": "image_set"}
        gd = verify_image_set(src, gd, warnings_out)
        rec["columns"] = [{"name": (group_decl or {}).get("name", "image_set"),
                           "dtype": None, "column_kind": "group", "group_desc": gd}]
    elif group_decl and group_decl["group_desc"].get("kind") == "waveform":
        # waveform: scalar(timestamp) 헤더 실측 + group manifest 권위 검산 (D-176)
        target = src
        if src.is_dir():
            cands = sorted(p for p in src.rglob("*") if p.suffix.lower() == ".csv")
            target = cands[0] if cands else src
        scalar, gd = verify_waveform(target, ds["encoding"], group_decl["group_desc"], warnings_out)
        dtypes = infer_scalar_dtypes(target, ds["encoding"], scalar)
        cols = [{"name": c, "dtype": dtypes.get(c, "unknown"),
                 "column_kind": "scalar", "group_desc": None} for c in scalar]
        cols.append({"name": group_decl.get("name", "waveform"), "dtype": "float",
                     "column_kind": "group", "group_desc": gd})
        rec["columns"] = cols
    else:
        # scalar tabular — 헤더 이름·dtype 실측 (사실 읽기). 다중파일 폴더는 대표 1개.
        target = src
        if src.is_dir():
            cands = sorted(p for p in src.rglob("*") if p.suffix.lower() in TABULAR_EXTS)
            if not cands:
                warnings_out.append("폴더에 tabular 파일 없음 — 분류 불가")
                return rec
            target = cands[0]
            _check_multifile_homogeneity(rec, cands, ds["encoding"])
        try:
            header = read_header(target, ds["encoding"])
        except Exception as e:
            warnings_out.append(f"헤더 판독 실패: {type(e).__name__}: {str(e)[:80]}")
            return rec
        if not header or all(c.startswith("__unnamed_") for c in header):
            warnings_out.append("헤더가 row0 에 없음(Unnamed/None) — 사람 교정 필요")
        dtypes = infer_scalar_dtypes(target, ds["encoding"], header)
        rec["columns"] = [{"name": c, "dtype": dtypes.get(c, "unknown"),
                           "column_kind": "scalar", "group_desc": None} for c in header]

    # 중복 컬럼명 가드 (전 브랜치 공통) — datalake.columns PK=(datalake_id,name) 위반 차단
    # (replace_columns 2번째 INSERT 크래시 방지). 비어있지 않은 중복을 결정론적 접미(__dupN)로
    # 유니크화(드롭 0, anti-silent). 빈 헤더는 read_header가 이미 __unnamed_i 로 처리.
    _uniq, _dups = _uniquify_headers([c["name"] for c in rec["columns"]])
    if _dups:
        for _c, _nm in zip(rec["columns"], _uniq):
            _c["name"] = _nm
        _shown = ", ".join(_dups[:5]) + (" …" if len(_dups) > 5 else "")
        warnings_out.append(f"중복 컬럼 {len(_dups)}건 비명명({_shown}) — 사람 교정 검토")
    return rec


def _check_multifile_homogeneity(rec: dict, files: list[Path], encoding: str) -> None:
    """다중파일 tabular: 동일 헤더 스키마인지 확인. 이종이면 플래그(대표만 반영)."""
    rec["_multifile"] = {"n_files": len(files), "representative": files[0].name}
    if len(files) > 24:
        return
    sigs = set()
    for p in files:
        try:
            sigs.add(tuple(read_header(p, encoding)))
        except Exception:
            sigs.add(("__read_fail__", p.name))
    if len(sigs) > 1:
        rec["_warnings"].append(
            f"이종 스키마 다중파일({len(sigs)}종/{len(files)}파일) — 대표만 반영, 사람 교정 필요")


# ── 출력 ─────────────────────────────────────────────────────────────────
def _sz(n: float) -> str:
    for u in ("B", "K", "M"):
        if n < 1024:
            return f"{n:.0f}{u}" if u == "B" else f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}G"


def print_plan(records: list[dict], excluded: list[dict]) -> None:
    print("=" * 78)
    print("DL-2 DRY-RUN 적재계획 (manifest-driven) — 복사 0 · DB write 0 · ALTER 0 · LLM 0")
    print("=" * 78)
    by_vid: dict[str, list[dict]] = {}
    for r in records:
        by_vid.setdefault(r["vid"], []).append(r)

    for vid, recs in by_vid.items():
        print(f"\n── vid (라인) = {vid}  [{len(recs)} datasets] " + "─" * 18)
        for r in recs:
            scal = sum(1 for c in r["columns"] if c["column_kind"] == "scalar")
            grp = [c for c in r["columns"] if c["column_kind"] == "group"]
            grp_str = ""
            if grp:
                g = grp[0]["group_desc"]
                if g.get("kind") == "waveform":
                    grp_str = (f" + GROUP[waveform: {g.get('n_cols')} cols, "
                               f"axis={g.get('axis')}, fs={g.get('fs_hz')}Hz, win={g.get('window')}]")
                elif g.get("kind") == "image_set":
                    grp_str = f" + GROUP[image_set: {g.get('n_images')} imgs {g.get('formats')}]"
                else:
                    grp_str = f" + GROUP[{g.get('kind')}]"
            norm = f" →norm={r['_normalize_to']}" if r.get("_normalize_to") else ""
            print(f"  • {r['datalake_id']}  ({r['name']})")
            print(f"      modality={r['modality']} function={r['function']} "
                  f"site={r['site']} company={r['company']} reusable={r['reusable_flag']}")
            print(f"      format={r['format']} enc={r['encoding']}{norm} size={_sz(r['size_bytes'])} "
                  f"cols: {scal} scalar{grp_str}")
            print(f"      data_path={r['data_path']}  node={r['_node']} capture={r['_capture']} (DB 미적재)")
            if r.get("_multifile"):
                mf = r["_multifile"]
                print(f"      multifile: {mf['n_files']} files (rep={mf['representative']})")
            for w in r["_warnings"]:
                print(f"      ⚠ {w}")

    # ── 집계 / 검산 ──
    print("\n" + "=" * 78)
    print("집계 · 정합 검산")
    print("=" * 78)
    modc = Counter(r["modality"] for r in records)
    print(f"총 데이터셋(= 계획 INSERT 수): {len(records)}  (manifest datasets={len(records)})")
    print(f"제외(DB 미등록, #15 D-177): {[e['datalake_id'] for e in excluded]}  → 34→{len(records)}")
    print(f"modality 분포: {dict(modc)}")
    print(f"  → order={modc.get('order',0)}건(D-177 1건 실재) · "
          f"event-log={modc.get('event-log',0)}건(ICT 검사레코드, 형태실측) · "
          f"inspection-image={modc.get('inspection-image',0)} · timeseries={modc.get('timeseries',0)}")
    encs = Counter(r["encoding"] for r in records)
    print(f"인코딩 분포: {dict(encs)}")
    cp = [(r["datalake_id"], r["_normalize_to"]) for r in records if r["encoding"] == "cp949"]
    print(f"cp949(정규화 대상, D-177): {cp}")
    wav = [(r["datalake_id"], next(c["group_desc"] for c in r["columns"]
            if c["column_kind"] == "group" and c["group_desc"].get("kind") == "waveform"))
           for r in records if any(c["column_kind"] == "group"
           and c["group_desc"].get("kind") == "waveform" for c in r["columns"])]
    print(f"waveform group(D-176, fft 아님): "
          f"{[(cid, g.get('fs_hz'), g.get('window')) for cid, g in wav]}")
    # 검산 결과
    no_path = [r["datalake_id"] for r in records if any("경로 없음" in w for w in r["_warnings"])]
    dec_fail = [r["datalake_id"] for r in records if any("디코드 실패" in w for w in r["_warnings"])]
    print(f"\n[검산] 경로 없음: {no_path or '없음(전건 존재)'}")
    print(f"[검산] 인코딩 디코드 실패: {dec_fail or '없음(전건 OK)'}")
    warned = [(r["datalake_id"], r["_warnings"]) for r in records if r["_warnings"]]
    print(f"[검산] 경고/이상치 데이터셋: {len(warned)}")
    for cid, ws in warned:
        for w in ws:
            print(f"  - {cid}: {w}")
    print("\n복사 0 · DB INSERT 0 · ALTER 실행 0 — dry-run 종료.")


# ── 실적재 (게이트 차단) ─────────────────────────────────────────────────
def to_db_entry(rec: dict) -> dict:
    """진단/provenance 제거 → datalake.entries upsert 인자(완전 레코드, D-172).
    node·capture 명시 비포함(DB 미적재, D-175). columns 는 별도 replace_columns 로."""
    return {k: rec[k] for k in (
        "datalake_id", "source", "name", "modality", "function", "site", "vid",
        "size_bytes", "encoding", "format", "data_path", "reusable_flag", "company")}


def execute_load(records: list[dict], data_root: Path) -> None:
    """실적재 경로 — catalog 재사용. greenlight(EXECUTE_ENABLED=True) 후에만 본체 도달.
    레코드별 순서(D-172/D-167): ① src→data/lake/<id>/ 복사(인코딩·형태별 분기)
      → ② catalog.upsert_entry(to_db_entry(rec)) [완전레코드, FK 부모 선존]
      → ③ catalog.replace_columns(id, rec['columns']) [DELETE→re-INSERT 멱등].
    constraints 절대 미접촉(D-167). 부분 적재 금지(소스 전수 존재 사전점검, anti-silent)."""
    if not EXECUTE_ENABLED:
        sys.exit(
            "ABORT: 실적재 비활성(EXECUTE_ENABLED=False) — 2-STOP 하드게이트.\n"
            "  본체·replace_columns 구현 완료. 운영 선행(① DB 백업 ③ 라이브 ALTER format/company)\n"
            "  + ④ Master greenlight 후 EXECUTE_ENABLED=True 커밋(Phase 2)으로만 활성. 현재 실적재 0."
        )
    # --- greenlight + EXECUTE_ENABLED=True 후 활성 ---
    import asyncio
    import shutil
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    import catalog
    import db

    lake_root = REPO_ROOT / "data" / "lake"

    # 사전점검: 소스 경로 전수 존재 (부분 적재 차단, anti-silent-drop)
    missing = [r["datalake_id"] for r in records
               if not Path(r["_source_path"]).exists()]
    if missing:
        sys.exit(f"ABORT: 소스 경로 없음 {missing} — 적재 중단(부분 적재 금지).")

    def _copy_one(rec: dict) -> str:
        """src → data/lake/<id>/. 반환=복사모드(로그용). 멱등(덮어쓰기/트리병합)."""
        src = Path(rec["_source_path"])
        dst_dir = lake_root / rec["datalake_id"]
        dst_dir.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            # 폴더형(image_set 7 · 다중 csv L3_extrusion_pdm) — 트리 통째(멱등)
            shutil.copytree(src, dst_dir, dirs_exist_ok=True)
            return "dir"
        if rec["encoding"] == "cp949":
            # cp949 3건 — 바이트복사 금지: cp949 read → utf-8 write(canonical, D-177).
            # 원본은 source(cp949) 보존 → 재실행 = source 재독으로 멱등.
            (dst_dir / src.name).write_text(
                src.read_text(encoding="cp949"), encoding="utf-8")
            return "cp949→utf-8"
        # utf-8 / utf-8-sig / binary(xlsx·xltx·이미지) — 바이트복사(BOM·바이너리 보존)
        shutil.copy2(src, dst_dir / src.name)
        return f"bytes:{rec['encoding']}"

    async def _run() -> None:
        try:
            total = len(records)
            for i, rec in enumerate(records, 1):
                cid = rec["datalake_id"]
                mode = _copy_one(rec)                               # ① 복사
                await catalog.upsert_entry(to_db_entry(rec))        # ② entries (D-172, FK 부모)
                await catalog.replace_columns(cid, rec["columns"])  # ③ columns full-replace (D-167)
                print(f"  ✓ [{i:>2}/{total}] {cid}: copy={mode} "
                      f"→ upsert_entry → replace_columns({len(rec['columns'])} cols)")
            print(f"\n실적재 완료: {total} datasets → data/lake/ + datalake.entries/columns "
                  f"(constraints 미접촉, D-167). 멱등 재적재 안전.")
        finally:
            await db.close_pool()

    asyncio.run(_run())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DL-2 KAMP datalake ingest (manifest-driven, dry-run default)")
    ap.add_argument("--root", default=str(DEFAULT_DATA_ROOT), help="KAMP 데이터 루트(manifest path 기준)")
    ap.add_argument("--dry-run", action="store_true", help="manifest 읽기+검산+계획 출력 (기본)")
    ap.add_argument("--execute", action="store_true", help="실적재 (현재 게이트 차단)")
    ap.add_argument("--json", action="store_true", help="계획을 JSON 으로 stdout 출력")
    args = ap.parse_args(argv)

    data_root = Path(args.root).expanduser()
    if not data_root.exists():
        sys.exit(f"ABORT: 데이터 루트 없음: {data_root}")

    datasets, excluded = load_manifest()
    records = [build_record(ds, data_root) for ds in datasets]

    if args.execute:
        execute_load(records, data_root)
        return 0

    # 기본 = dry-run (복사 0 · DB write 0 · ALTER 0)
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2, default=str))
    else:
        print_plan(records, excluded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
