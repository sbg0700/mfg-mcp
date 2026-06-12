"""
backend/datalake_api.py — DL-3a: catalog 계층의 API 노출 (/api/datalake/*).

- additive only (D-181/D-184): 구 핸들러·구 경로 무접촉. main.py 변경 = import + include_router 2줄.
- 표면 = spec-1 §1-3 / spec-3 §9-1 (7~10 + 9b/9c/9d, D-187).
- register = Mode B(서버 경로 메타 등록) 한정 (D-186). Mode A(multipart)는 명시적 400 + 이월 안내.
- POST constraints = catalog.insert_constraint 경유 — 동일 트랜잭션 constraints_history append
  (D-179 불변식). 검증(3c, D-190): entry 부재 404 / type ∉ D-185 화이트리스트 422 /
  canonical 필드(range·single_value·aggregate 엄격, ratio·list·text 미확정 422) /
  column_name 실존 422 / aggregate ↔ column_kind=group 정합 422.
  빈 값(None|{}) = delete_constraint 경로(D-191) — 동일 트랜잭션 history append(action=delete).
- 헤더 파싱 = tools/datalake_ingest.py 단일 구현 import 재사용(read_header/_uniquify_headers/
  infer_scalar_dtypes/measure_size) — 중복 구현 0. ingest 동작 변경 0.
- LAKE_ROOT = <repo>/data/lake 모듈 상수 — 프로덕션 env 분기 금지(D-159 정신).
  테스트는 monkeypatch 로 tmp 경로 대체(실 data/lake 오염 0).
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

# 레포 루트를 sys.path 에 (tools/ import 용 — main.py 와 동일 관행)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import catalog
from tools.datalake_ingest import (
    TABULAR_EXTS, _uniquify_headers, infer_scalar_dtypes, measure_size, read_header,
)

router = APIRouter(prefix="/api/datalake")

LAKE_ROOT = ROOT / "data" / "lake"        # D-159 — env 분기 금지. 테스트 = monkeypatch.

# D-185: spec §4-4 폼 5종 ∪ aggregate(column_kind=group 전용)
CONSTRAINT_TYPES = {"range", "single_value", "ratio", "list", "text", "aggregate"}
# D-190: canonical 확정 3종 / 미확정 3종(즉흥 정의 금지 — POST 명시 422)
CANONICAL_TYPES = {"range", "single_value", "aggregate"}
DEFERRED_TYPES = {"ratio", "list", "text"}
_AGG_METRICS = {"rms", "peak", "mean", "std"}
_AGG_OPS = {"<=", ">="}
# type별 허용 필드 (D-190 byte 대조 — 허용 외 필드 = 422, anti-silent)
_CANONICAL_FIELDS = {
    "range": {"type", "min", "max", "unit"},
    "single_value": {"type", "value", "unit"},
    "aggregate": {"type", "metric", "op", "value", "unit"},
}


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def canonical_error(spec: dict) -> str | None:
    """D-190 canonical 필드 검증 — 위반 사유 문자열, 통과 시 None.
    전제: spec['type'] ∈ CONSTRAINT_TYPES (D-185 화이트리스트 선행)."""
    t = spec.get("type")
    if t in DEFERRED_TYPES:
        return (f"type '{t}' = canonical 필드 미확정 type — 폼 구현 시 확정 예정 (D-190)")
    extra = set(spec) - _CANONICAL_FIELDS[t]
    if extra:
        return f"{t}: 허용 외 필드 {sorted(extra)} (D-190 canonical: {sorted(_CANONICAL_FIELDS[t])})"
    if not (spec.get("unit") is None or isinstance(spec.get("unit"), str)):
        return f"{t}: unit 은 str|null (D-190)"
    if t == "range":
        for k in ("min", "max"):
            if not (spec.get(k) is None or _is_num(spec.get(k))):
                return f"range: {k} 은 num|null (D-190)"
        if spec.get("min") is None and spec.get("max") is None:
            return "range: min/max 중 1개 이상 non-null (D-180/D-190)"
    elif t == "single_value":
        if not _is_num(spec.get("value")):
            return "single_value: value 는 num 필수 (D-190)"
    elif t == "aggregate":
        if spec.get("metric") not in _AGG_METRICS:
            return f"aggregate: metric ∉ {sorted(_AGG_METRICS)} (D-190)"
        if spec.get("op") not in _AGG_OPS:
            return f"aggregate: op ∉ {sorted(_AGG_OPS)} (D-190)"
        if not _is_num(spec.get("value")):
            return "aggregate: value 는 num 필수 (D-190)"
    return None
# CLAUDE.md §3 — 모달리티 4종 고정
MODALITIES = {"timeseries", "inspection-image", "event-log", "order"}
# variable_index §2 — Function 축 4종. function_hint(유저 힌트) → 권위 컬럼 function 해석 대상.
FUNCTION_AXES = {"process", "quality", "maintenance", "reference"}


def _ser(d: dict[str, Any]) -> dict[str, Any]:
    """registered_at/approved_at(TIMESTAMPTZ) → ISO 문자열 직렬화."""
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in d.items()}


async def _entry_or_404(datalake_id: str) -> dict[str, Any]:
    entry = await catalog.get_entry(datalake_id)
    if entry is None:
        raise HTTPException(404, f"datalake entry not found: {datalake_id}")
    return entry


# ── 7. /list — 3축 AND 필터 (D-166, 모두 optional) ──────────────────────
@router.get("/list")
async def dl_list(vid: str | None = None, function: str | None = None,
                  site: str | None = None) -> dict:
    entries = await catalog.list_entries(vid=vid, function=function, site=site)
    return {"entries": [_ser(e) for e in entries]}


# ── 8. /register — Mode B 한정 (D-186) ──────────────────────────────────
class RegisterReq(BaseModel):
    name: str
    server_path: str
    modality: str
    function_hint: str | None = None
    site: str | None = None
    vid: str | None = None
    company: str | None = None


def _slug(name: str) -> str:
    """datalake_id = slug(name), 문자집합 [a-z0-9_] (D-186). 자동 충돌-변형 금지."""
    s = re.sub(r"[^a-z0-9_]+", "_", name.strip().lower())
    return re.sub(r"_+", "_", s).strip("_")


@router.post("/register")
async def dl_register(request: Request) -> dict:
    # Mode A(파일 업로드) = 이월 — silent 422 대신 명시적 400 (D-186)
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("multipart/form-data"):
        raise HTTPException(
            400, "Mode A(파일 업로드) 미지원 — Mode B(server_path JSON)만 지원, Mode A 이월 (D-186)")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "JSON body 필요 — Mode B(server_path) 한정 (D-186)")
    try:
        req = RegisterReq(**(body or {}))
    except ValidationError as e:
        raise HTTPException(422, str(e))

    if req.modality not in MODALITIES:
        raise HTTPException(422, f"modality '{req.modality}' ∉ {sorted(MODALITIES)} (4종 고정)")
    # function_hint 해석: Function 축 화이트리스트 검증 후 권위 컬럼 function 에 저장
    # (rename 아님 — 입력 표면은 힌트, 저장은 권위. D-186/R1 이월)
    function: str | None = None
    if req.function_hint is not None:
        if req.function_hint not in FUNCTION_AXES:
            raise HTTPException(
                422, f"function_hint '{req.function_hint}' ∉ {sorted(FUNCTION_AXES)}")
        function = req.function_hint

    src = Path(req.server_path).expanduser()
    if not src.exists():
        raise HTTPException(400, f"server_path 없음: {src}")

    datalake_id = _slug(req.name)
    if not datalake_id:
        raise HTTPException(422, f"name '{req.name}' 에서 datalake_id([a-z0-9_]) 생성 불가")
    if await catalog.get_entry(datalake_id) is not None:
        raise HTTPException(
            409, f"datalake_id 충돌: '{datalake_id}' 이미 존재 — 자동 변형 금지(D-186), name 변경 필요")
    # orphan-dir 가드 (3a 룰링 ④ 후속): DELETE 가 DB-only 라 data/lake/<id>/ 잔존 가능 —
    # DB 부재여도 디렉터리 실존이면 silent 복사(이종 데이터 혼입) 차단, orphan 명시 409.
    dst_dir = LAKE_ROOT / datalake_id
    if dst_dir.exists():
        raise HTTPException(
            409, f"data/lake/{datalake_id}/ 디렉터리 잔존(orphan) — DB entry 부재여도 "
                 f"silent 복사 금지. 디렉터리 정리(또는 name 변경) 후 재시도")

    # 복사 → data/lake/<id>/ (등록 데이터도 동일 귀결, D-159/§1-6). 바이트 보존 복사 —
    # 인코딩 정규화(cp949→utf-8)는 manifest 권위 ingest 전용이라 여기선 비적용.
    dst_dir.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst_dir, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst_dir / src.name)

    entry = {   # 완전 레코드 upsert (D-172)
        "datalake_id": datalake_id,
        "source": "user_registered",
        "name": req.name,
        "modality": req.modality,
        "function": function,
        "site": req.site,
        "vid": req.vid,
        "size_bytes": measure_size(src),
        "encoding": None,               # 미실측 — 인코딩 감지는 이월
        "format": (src.suffix.lower().lstrip(".") or None) if src.is_file() else None,
        "data_path": f"data/lake/{datalake_id}/",
        "reusable_flag": False,
        "company": req.company,
    }
    await catalog.upsert_entry(entry)

    # 표형식 단일 파일 → 헤더 실측 (ingest 단일 구현 재사용). 그 외 = columns 0 + 응답 명시.
    columns: list[dict[str, Any]] = []
    columns_note: str | None = None
    if src.is_file() and src.suffix.lower() in TABULAR_EXTS:
        try:
            names, _renamed = _uniquify_headers(read_header(src, "utf-8-sig"))
            dtypes = infer_scalar_dtypes(src, "utf-8-sig", names)
            columns = [{"name": n, "dtype": dtypes.get(n, "unknown"),
                        "column_kind": "scalar", "group_desc": None} for n in names]
        except Exception as e:
            columns_note = f"헤더 실측 실패({type(e).__name__}) — columns 0건, 사람 교정 필요"
    else:
        columns_note = "비표형식(또는 폴더) — columns 미실측(0건)"
    await catalog.replace_columns(datalake_id, columns)

    out: dict[str, Any] = {"entry": _ser(await catalog.get_entry(datalake_id)),
                           "n_columns": len(columns)}
    if columns_note:
        out["columns_note"] = columns_note
    return out


# ── 9. /{id}/metadata ────────────────────────────────────────────────────
@router.get("/{datalake_id}/metadata")
async def dl_metadata(datalake_id: str) -> dict:
    return _ser(await _entry_or_404(datalake_id))


# ── 9b. /{id}/columns — Page 3 폼 소스 (D-90/D-161, __dupN 그대로 노출) ──
@router.get("/{datalake_id}/columns")
async def dl_columns(datalake_id: str) -> dict:
    await _entry_or_404(datalake_id)
    return {"datalake_id": datalake_id, "columns": await catalog.get_columns(datalake_id)}


# ── 9c. /{id}/constraints GET — prefill 소스 (D-167: 제안일 뿐 잠금 아님) ─
@router.get("/{datalake_id}/constraints")
async def dl_constraints(datalake_id: str) -> dict:
    await _entry_or_404(datalake_id)
    cons = await catalog.get_constraints(datalake_id)
    return {"datalake_id": datalake_id, "constraints": [_ser(c) for c in cons]}


# ── 9d. /{id}/constraints POST — "영속 업데이트" 쓰기 경로 (D-179/D-185/D-190/D-191) ──
class ConstraintReq(BaseModel):
    column_name: str
    constraint_spec: dict | None = None   # None 또는 {} = "빈칸 영속" → delete 경로 (D-191)
    approved_by: str = "user"


@router.post("/{datalake_id}/constraints")
async def dl_post_constraint(datalake_id: str, req: ConstraintReq) -> dict:
    await _entry_or_404(datalake_id)                                  # ① entry 부재 404

    # 빈 값(전 필드 null/clear) = delete_constraint 경로 (D-191) — silent no-op 금지: 부재 404
    if not req.constraint_spec:
        deleted = await catalog.delete_constraint(
            datalake_id, req.column_name, approved_by=req.approved_by)
        if not deleted:
            raise HTTPException(
                404, f"삭제할 제약 없음: ({datalake_id}, {req.column_name}) — "
                     "빈칸 영속 업데이트는 기존 제약 삭제 경로 (D-191)")
        return {"datalake_id": datalake_id, "column_name": req.column_name,
                "approved_by": req.approved_by, "deleted": True}

    ctype = req.constraint_spec.get("type")
    if ctype not in CONSTRAINT_TYPES:                                 # ② D-185 화이트리스트
        raise HTTPException(
            422, f"constraint_spec.type '{ctype}' ∉ {sorted(CONSTRAINT_TYPES)} (D-185)")
    err = canonical_error(req.constraint_spec)                        # ③ D-190 canonical
    if err:
        raise HTTPException(422, err)
    cols = {c["name"]: c for c in await catalog.get_columns(datalake_id)}
    if req.column_name not in cols:                                   # ④ 실컬럼 검증
        raise HTTPException(
            422, f"column_name '{req.column_name}' ∉ datalake.columns({datalake_id})")
    # ⑤ aggregate ↔ column_kind=group 정합 (D-185/D-190 — aggregate 는 group 전용)
    if ctype == "aggregate" and cols[req.column_name].get("column_kind") != "group":
        raise HTTPException(
            422, f"aggregate 는 column_kind=group 전용 — '{req.column_name}' 은 "
                 f"{cols[req.column_name].get('column_kind')} (D-185/D-190)")
    # insert_constraint = upsert + 동일 트랜잭션 history append (D-179 불변식 충족 경로)
    await catalog.insert_constraint(datalake_id, req.column_name,
                                    req.constraint_spec, approved_by=req.approved_by)
    return {"datalake_id": datalake_id, "column_name": req.column_name,
            "constraint_spec": req.constraint_spec,
            "approved_by": req.approved_by, "saved": True}


# ── 10. DELETE /{id} ─────────────────────────────────────────────────────
@router.delete("/{datalake_id}")
async def dl_delete(datalake_id: str) -> dict:
    await _entry_or_404(datalake_id)
    await catalog.delete_entry(datalake_id)   # 자식 명시 삭제 + history 'delete' (D-179)
    return {"deleted": True}
