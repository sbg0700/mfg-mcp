"""
tests/test_engine_invariance_dl5a.py — 엔진 로직-0 불변 가드 (DL-5a, D-201).

명제: 엔진 5종 = agents/{inspector,planner,executor,validator,ml} 이
R0 baseline(tag dl-baseline-20260605) 대비 '로직 변경 0' 임을 자동 박제한다.
→ "엔진 변경 0"이라는 핵심 영업명제를 DL 전체(R0~)에 걸친 상시 회귀 게이트로 고정.

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

# 엔진 5종(불변이어야 하는 forbidden-zone). 데이터 seam(datalake.get)·aggregator·EDA 는
# 이 목록 밖 = PROTOCOL §3 additive 허용(BLUEPRINT §1.5: dataset_id→path 만 additive).
_ENGINE_PATHS = [
    "agents/inspector",
    "agents/planner",
    "agents/executor",
    "agents/validator",
    "agents/ml",
]

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


# ── 본 단정: 엔진 로직-0 ─────────────────────────────────────────────────────
def test_engine_logic_zero_vs_r0() -> None:
    """엔진 5종이 R0 대비 변경 0(committed+미커밋 모두). 위반 시 변경 파일을 명시."""
    changed = _changed_vs_r0(*_ENGINE_PATHS)
    assert changed == [], (
        f"엔진 로직-0 불변 위반 — R0({_R0_TAG}) 대비 변경된 엔진 파일:\n"
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
