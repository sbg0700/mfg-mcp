"""
tests/test_engine_invariance_dl5a.py — 엔진 로직-0 불변 가드 (DL-5a, D-201; DL-5b 정제, D-201 재정의).

명제: 엔진 5종 = agents/{inspector,planner,executor,validator,ml} 이
R0 baseline(tag dl-baseline-20260605) 대비 '로직 변경 0' 임을 자동 박제한다.
→ "엔진 변경 0"이라는 핵심 영업명제를 DL 전체(R0~)에 걸친 상시 회귀 게이트로 고정.

★ DL-5b 정제(D-201 재정의): 파일 동결 → compute 동결 + 데이터 seam additive 허용.
  {inspector,planner,validator,ml} = byte-동결(R0 대비 diff 0).
  executor.py = compute 동결이되 문서화된 데이터 seam additive(data_path 인자+None 분기)만
  허용(D-203 배선). seam 외 변경(특히 compute)은 RED — test_executor_seam_additive_only 가 강제.

설계 (★ 경계 가드 D-199 와 반대 방향):
- 본 단정은 baseline→worktree 의 '한쪽-끝' diff 다(닫힌범위 아님). 즉 committed 드리프트뿐
  아니라 working tree 의 '미커밋' 엔진 변경까지 포착한다. 불변 가드는 '미래·미커밋' 엔진
  변경을 *잡아야* 정상이므로 한쪽-끝이 정답이다 (mutation check 가 이 방향성을 실증).
- 비공허 2중: (a) test_engine_guard_not_vacuous = R0 대비 변경이 *확인된* DL-레이어 파일
  diff != 빈 목록(probe 생존), (b) STEP5 mutation check = 엔진 파일 임시 변경 시 본 단정 RED.
- 데이터 의존성 0: 순수 git subprocess. PG 하니스/fixture 불요 → DB 없이도 항상 실행.
- baseline 미해결(tag 부재) 시 가드 자체가 RuntimeError 로 fail-loud(조용한 green 금지).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

# ── 경로 상수 ────────────────────────────────────────────────────────────────
_REPO = Path(__file__).resolve().parent.parent  # = worktree 루트
_R0_TAG = "dl-baseline-20260605"

# 엔진 5종(watched — 경로 실재 감시 대상). 데이터 seam(datalake.get)·aggregator·EDA 는
# 이 목록 밖 = PROTOCOL §3 additive 허용(BLUEPRINT §1.5: dataset_id→path 만 additive).
_ENGINE_PATHS = [
    "agents/inspector",
    "agents/planner",
    "agents/executor",
    "agents/validator",
    "agents/ml",
]

# ── D-201 재정의(DL-5b/5c-2): compute/프로파일 동결 + 데이터 seam additive 허용 ──
# {planner,validator,ml}+inspector/schemas.py = byte-동결(R0 대비 diff 0).
# executor.py(D-203)·inspector.py(D-206) = compute/프로파일 로직 동결이되 '문서화된 데이터 seam
#   additive'(data_path 인자 전파)만 허용. seam 밖 변경은 RED — 아래 _*_SEAM_* 화이트리스트가 경계.
_FROZEN_PATHS = [
    "agents/inspector/schemas.py",
    "agents/planner",
    "agents/validator",
    "agents/ml",
]
_EXECUTOR_PATH = "agents/executor/executor.py"
_INSPECTOR_PATH = "agents/inspector/inspector.py"

# 대조(control) 경로 — R0 대비 변경이 *실증된* DL-레이어 파일(probe 비공허 증명용).
# CC 가 STEP1~2 에서 `git diff --name-only <R0> -- backend/catalog.py` == 1 로 non-empty 확인.
_CONTROL_PATH = "backend/catalog.py"


# ── git 헬퍼 (fail-loud) ─────────────────────────────────────────────────────
def _git(*args: str) -> str:
    """worktree 루트에서 git 실행. 0 아닌 종료코드는 RuntimeError 로 fail-loud."""
    proc = subprocess.run(
        ["git", *args], cwd=_REPO, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} 실패(rc={proc.returncode}): {proc.stderr.strip()}"
        )
    return proc.stdout


def _resolve_r0() -> str:
    """R0 tag → commit deref. 미해결(tag 부재) 시 _git 가 RuntimeError = 가드 fail-loud."""
    return _git("rev-parse", f"{_R0_TAG}^{{commit}}").strip()


def _changed_vs_r0(*pathspecs: str) -> list[str]:
    """R0(deref) → worktree 한쪽-끝 diff 의 변경 파일명 목록(공백줄 제거)."""
    r0 = _resolve_r0()
    out = _git("diff", "--name-only", r0, "--", *pathspecs)
    return [ln for ln in out.splitlines() if ln.strip()]


# ── 본 단정: 엔진 로직-0 (byte-동결 4종 — executor 제외, D-201 재정의) ────────
def test_engine_logic_zero_vs_r0() -> None:
    """{planner,validator,ml}+inspector/schemas.py 가 R0 대비 변경 0(committed+미커밋 모두).
    executor.py(D-203)·inspector.py(D-206) 는 데이터 seam additive 가 허용되어 본 단정에서
    제외되고, test_executor_seam_additive_only·test_inspector_seam_additive_only 가 각 경계를 강제."""
    changed = _changed_vs_r0(*_FROZEN_PATHS)
    assert changed == [], (
        f"엔진 로직-0 불변 위반 — R0({_R0_TAG}) 대비 변경된 동결 엔진 파일:\n"
        + "\n".join(f"  - {f}" for f in changed)
    )


# ── 대조 단정: probe 비공허 ──────────────────────────────────────────────────
def test_engine_guard_not_vacuous() -> None:
    """대조 경로(R0 대비 변경 확인됨)가 diff != 빈 목록임을 단정 → probe 가 공허하지 않음."""
    changed = _changed_vs_r0(_CONTROL_PATH)
    assert changed, (
        f"가드 공허 — 대조 경로 {_CONTROL_PATH} 가 R0({_R0_TAG}) 대비 변경 0 "
        "(probe 신뢰 불가: 본 단정의 빈-목록이 '진짜 불변' 인지 'diff 무력화' 인지 구분 불가)"
    )


# ── 경로 감시 보증: vacuous-via-bad-path 차단 (D-201 보강) ────────────────────
def test_engine_paths_are_watched() -> None:
    """엔진 5종이 각각 추적 파일 ≥1개로 실재함을 단정 → 경로 오타·미래 리네임이
    본 단정(test_engine_logic_zero_vs_r0)을 vacuous-green('미감시'를 '불변'으로 오판)
    으로 만드는 잔여 벡터를 fail-loud 차단."""
    for p in _ENGINE_PATHS:
        tracked = [ln for ln in _git("ls-files", "--", p).splitlines() if ln.strip()]
        assert tracked, (
            f"엔진 경로 {p} 추적 파일 0 — 오타/리네임 의심. "
            f"본 단정의 빈-목록이 '불변'이 아닌 '미감시'일 수 있음(vacuous 차단)."
        )


# ── executor 데이터 seam: additive-only 강제 (D-201 재정의 / D-203) ───────────
# R0 대비 executor.py diff 의 +/- 내용 라인이 *오직* 아래 문서화 seam 라인뿐이어야 한다.
# compute(변환·backup·lineage) 라인이 단 1줄이라도 변하면 화이트리스트 밖 = RED.
# 화이트리스트는 DL-5b STEP2 실제 `git diff --unified=0 <R0> -- executor.py` 로 저작(즉흥 금지).
_EXECUTOR_SEAM_ADDED = {
    # DL-5b: execute() 시그니처 data_path 인자 + timeseries/order seam (기존)
    "                  selected_options: dict[str, str] | None = None,",
    "                  data_path: str | None = None) -> dict:",
    "    path = data_path if data_path is not None else _resolve(dataset_id, modality)",
    # DL-5c-1 (D-204): event-log seam additive — execute 분기·_execute_eventlog·_load_eventlog
    "        return await _execute_eventlog(plan, approved_keys, dataset_id, selected_options, data_path)",
    "                            selected_options: dict[str, str] | None = None,",
    "                            data_path: str | None = None) -> dict:",
    "        df, path, n_sheets = _load_eventlog(dataset_id, data_path)",
    "def _load_eventlog(dataset_id: str, data_path: str | None = None):",
    "    path = data_path if data_path is not None else os.path.join(EVENTLOG_DATA_ROOT, name)",
    "    if data_path is None and not os.path.exists(path):",
}
_EXECUTOR_SEAM_REMOVED = {
    # DL-5b (기존)
    "                  selected_options: dict[str, str] | None = None) -> dict:",
    "    path = _resolve(dataset_id, modality)",
    # DL-5c-1 (D-204): event-log seam 이전 라인
    "        return await _execute_eventlog(plan, approved_keys, dataset_id, selected_options)",
    "                            selected_options: dict[str, str] | None = None) -> dict:",
    "        df, path, n_sheets = _load_eventlog(dataset_id)",
    "def _load_eventlog(dataset_id: str):",
    "    path = os.path.join(EVENTLOG_DATA_ROOT, name)",
    "    if not os.path.exists(path):",
}


def _diff_pm_lines_vs_r0(pathspec: str) -> tuple[list[str], list[str]]:
    """R0 대비 pathspec 의 unified=0 diff 에서 +/- 내용 라인(파일헤더·@@ 제외)을 (added, removed)로."""
    r0 = _resolve_r0()
    out = _git("diff", "--unified=0", r0, "--", pathspec)
    added: list[str] = []
    removed: list[str] = []
    for ln in out.splitlines():
        if ln.startswith("+++") or ln.startswith("---"):
            continue
        if ln.startswith("+"):
            added.append(ln[1:])
        elif ln.startswith("-"):
            removed.append(ln[1:])
    return added, removed


def test_executor_seam_additive_only() -> None:
    """executor.py 의 R0 대비 변경이 *정확히* 문서화된 데이터 seam additive 뿐임을 단정.
    (1) 동결: seam 화이트리스트 밖 +/- 라인(특히 compute·backup·lineage)이 하나라도 있으면 RED.
    (2) presence(A1, DL-5b-e2e): seam 라인이 *존재함*도 단정 — D-203 배선이 사라지면 RED(자기완결).
    → (1)∧(2) = R0 대비 diff 가 seam 화이트리스트와 정확히 일치(초과·결손 모두 RED)."""
    added, removed = _diff_pm_lines_vs_r0(_EXECUTOR_PATH)
    sa, sr = set(added), set(removed)
    # (1) 동결: 허용 밖 변경 0
    extra_added = sorted(sa - _EXECUTOR_SEAM_ADDED)
    extra_removed = sorted(sr - _EXECUTOR_SEAM_REMOVED)
    assert not extra_added and not extra_removed, (
        "executor seam 경계 위반 — 허용 seam additive 밖 변경 감지(compute 동결 위반 의심):\n"
        + "".join(f"  + {ln}\n" for ln in extra_added)
        + "".join(f"  - {ln}\n" for ln in extra_removed)
    )
    # (2) presence(A1): seam 이 실재 — D-203 배선 회귀(seam 제거) 시 RED
    missing_added = sorted(_EXECUTOR_SEAM_ADDED - sa)
    missing_removed = sorted(_EXECUTOR_SEAM_REMOVED - sr)
    assert not missing_added and not missing_removed, (
        "executor seam 부재 — 문서화된 data_path seam 소실(D-203 배선 회귀 의심):\n"
        + "".join(f"  (missing +) {ln}\n" for ln in missing_added)
        + "".join(f"  (missing -) {ln}\n" for ln in missing_removed)
    )


# ── inspector 데이터 seam: additive-only 강제 (D-206 / DL-5c-2) ────────────────
# R0 대비 inspector.py diff 의 +/- 내용 라인이 *오직* 아래 문서화 seam(data_path 인자 전파)뿐.
# 프로파일·flags·LLM 로직이 단 1줄이라도 변하면 화이트리스트 밖 = RED.
# 화이트리스트는 DL-5c-2 실제 `git diff --unified=0 <R0> -- inspector.py` 로 저작(즉흥 금지).
_INSPECTOR_SEAM_ADDED = {
    '                  modality: str = "timeseries", data_path: str | None = None) -> dict:',
    '    columns = await _mcp_get(modality, "/list_columns", dataset_id=dataset_id, data_path=data_path)',
    '    schema = await _mcp_get(modality, "/get_schema", dataset_id=dataset_id, data_path=data_path)',
    '    sample = await _mcp_get(modality, "/sample", dataset_id=dataset_id, n=5, data_path=data_path)',
    '    encoding = await _mcp_get(modality, "/detect_encoding", dataset_id=dataset_id, data_path=data_path)',
}
_INSPECTOR_SEAM_REMOVED = {
    '                  modality: str = "timeseries") -> dict:',
    '    columns = await _mcp_get(modality, "/list_columns", dataset_id=dataset_id)',
    '    schema = await _mcp_get(modality, "/get_schema", dataset_id=dataset_id)',
    '    sample = await _mcp_get(modality, "/sample", dataset_id=dataset_id, n=5)',
    '    encoding = await _mcp_get(modality, "/detect_encoding", dataset_id=dataset_id)',
}


def test_inspector_seam_additive_only() -> None:
    """inspector.py 의 R0 대비 변경이 *정확히* 문서화된 data_path seam 전파뿐임을 단정(D-206).
    (1) 동결: seam 밖 +/- 라인(특히 프로파일·flags·LLM 로직)이 하나라도 있으면 RED.
    (2) presence: seam 라인이 *실재*함도 단정 — D-206 배선이 사라지면 RED(자기완결).
    → (1)∧(2) = R0 대비 diff 가 seam 화이트리스트와 정확히 일치(초과·결손 모두 RED)."""
    added, removed = _diff_pm_lines_vs_r0(_INSPECTOR_PATH)
    sa, sr = set(added), set(removed)
    # (1) 동결: 허용 밖 변경 0
    extra_added = sorted(sa - _INSPECTOR_SEAM_ADDED)
    extra_removed = sorted(sr - _INSPECTOR_SEAM_REMOVED)
    assert not extra_added and not extra_removed, (
        "inspector seam 경계 위반 — 허용 seam 밖 변경 감지(프로파일 동결 위반 의심):\n"
        + "".join(f"  + {ln}\n" for ln in extra_added)
        + "".join(f"  - {ln}\n" for ln in extra_removed)
    )
    # (2) presence: seam 이 실재 — D-206 배선 회귀(seam 제거) 시 RED
    missing_added = sorted(_INSPECTOR_SEAM_ADDED - sa)
    missing_removed = sorted(_INSPECTOR_SEAM_REMOVED - sr)
    assert not missing_added and not missing_removed, (
        "inspector seam 부재 — 문서화된 data_path seam 소실(D-206 배선 회귀 의심):\n"
        + "".join(f"  (missing +) {ln}\n" for ln in missing_added)
        + "".join(f"  (missing -) {ln}\n" for ln in missing_removed)
    )
