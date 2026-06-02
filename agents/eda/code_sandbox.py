"""agents/eda/code_sandbox.py — STEP 3a-2 자연어 코드 생성 안전 설계.

★3중 안전★
  ① _validate_eda_code  : AST 화이트리스트 (생성 시) — 허용 노드/이름만 통과
  ② 실행 직전 재검증     : approve 시점에 한 번 더 _validate_eda_code (호출부 책임)
  ③ _sandbox_exec       : builtins 차단 네임스페이스 + df 사본 + 타임아웃

원칙:
  - LLM 생성 코드는 "제안". 절대 검증 없이 실행 금지.
  - 허용 모듈: pandas (pd), numpy (np). df, result 외 최상위 이름 사용 불가.
  - import / 파일 / 네트워크 / exec/eval / dunder(__) 일체 금지.
  - df는 .copy()로 사본 전달 (원본 보호). result만 회수.

옵션 카드(D-107 BALANCE_OPTION_IDS) 발상과 같음:
  허용 집합을 코드로 고정 → LLM 출력이 그 집합 안만 통과.
"""
from __future__ import annotations
import ast
import signal
from typing import Any

# ─────────────────────────────────────────────────────────────────────────
# 허용 AST 노드 (읽기 전용 분석에 필요한 최소 집합)
# ─────────────────────────────────────────────────────────────────────────
ALLOWED_NODES: frozenset = frozenset({
    # 모듈/문장 구조
    ast.Module, ast.Expr, ast.Assign, ast.AugAssign,
    # 이름/리터럴
    ast.Name, ast.Load, ast.Store, ast.Constant,
    # 표현식
    ast.Call, ast.Attribute, ast.Subscript, ast.Slice, ast.Starred,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
    # 컬렉션
    ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp, ast.comprehension,
    # keyword arg + Index(파이썬 3.8 호환)
    ast.keyword,
    # 연산자 — 산술/비교/논리
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.MatMult, ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd,
    ast.UAdd, ast.USub, ast.Not, ast.Invert,
    ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
})

# 금지 이름 (사용 자체가 시도되면 거부)
FORBIDDEN_NAMES: frozenset = frozenset({
    "import", "__import__", "exec", "eval", "compile", "open",
    "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr", "hasattr",
    "os", "sys", "subprocess", "socket", "pathlib", "shutil",
    "__builtins__", "__class__", "__bases__", "__subclasses__", "__mro__",
    "input", "breakpoint",
})

# 허용된 최상위 이름 (sandbox 네임스페이스에 주입되는 것)
ALLOWED_ROOT_NAMES: frozenset = frozenset({"df", "result", "pd", "np", "True", "False", "None"})


# ─────────────────────────────────────────────────────────────────────────
# 1) AST 화이트리스트 검증
# ─────────────────────────────────────────────────────────────────────────
def validate_eda_code(code: str) -> tuple[bool, str]:
    """AST 화이트리스트 — 허용 노드/이름만. import/파일/네트워크/exec/dunder 차단.

    반환: (ok, reason). ok=True면 reason="ok"; False면 거부 사유.
    """
    if not isinstance(code, str) or not code.strip():
        return False, "empty code"

    # 길이 가드 — 10KB 초과는 안전 영역 밖
    if len(code) > 10_000:
        return False, f"code too long: {len(code)} bytes (max 10000)"

    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        return False, f"SyntaxError: {e.msg} (line {e.lineno})"

    # 트리 워크 — 노드 종류 / 이름 / dunder
    for node in ast.walk(tree):
        nt = type(node)
        if nt not in ALLOWED_NODES:
            return False, f"disallowed AST node: {nt.__name__}"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False, "import forbidden"
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return False, f"forbidden name: {node.id}"
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):   # _private, __dunder 모두 차단
                return False, f"private/dunder attribute access: {node.attr}"
            if node.attr in FORBIDDEN_NAMES:
                return False, f"forbidden attribute: {node.attr}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_NAMES:
                return False, f"forbidden call: {node.func.id}"

    # 최상위 이름 가드 (불러쓰는 글로벌)
    used_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    bad = used_names - ALLOWED_ROOT_NAMES - {n.id for n in ast.walk(tree)
                                             if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    # comprehension 안의 임시 이름(예: x in [for x in ...])은 store됐다 load되므로 자동 제외됨
    if bad:
        return False, f"undefined names: {sorted(bad)}"

    return True, "ok"


# ─────────────────────────────────────────────────────────────────────────
# 2) 샌드박스 실행 (builtins 차단 + df 사본 + 타임아웃)
# ─────────────────────────────────────────────────────────────────────────
class SandboxTimeout(Exception):
    pass


def _timeout_handler(_signum, _frame):
    raise SandboxTimeout("execution exceeded time limit")


# 결과 직렬화에 사용할 안전 변환기 (pandas 객체 → dict / list)
def _coerce_result(result: Any) -> Any:
    """exec 결과 result 변수를 JSON 직렬화 가능한 형태로 변환.
    pandas Series/DataFrame은 dict/records로, numpy 배열은 list로, scalar는 그대로."""
    try:
        import pandas as pd
        import numpy as np
    except Exception:
        return repr(result)
    if result is None:
        return None
    if isinstance(result, (int, float, str, bool)):
        return result
    if isinstance(result, dict):
        return {str(k): _coerce_result(v) for k, v in result.items()}
    if isinstance(result, (list, tuple)):
        return [_coerce_result(x) for x in result]
    if isinstance(result, pd.Series):
        return {str(k): _coerce_result(v) for k, v in result.to_dict().items()}
    if isinstance(result, pd.DataFrame):
        # 행이 너무 많으면 상위 200행만
        df = result.head(200)
        return {"columns": [str(c) for c in df.columns],
                "rows": [[_coerce_result(v) for v in row] for row in df.itertuples(index=False, name=None)],
                "n_rows_total": int(len(result)),
                "truncated": int(len(result)) > 200}
    if isinstance(result, np.ndarray):
        return [_coerce_result(v) for v in result.tolist()]
    if isinstance(result, (np.integer,)):
        return int(result)
    if isinstance(result, (np.floating,)):
        return float(result)
    # 기타 — repr (정보 손실 인지)
    return repr(result)


def sandbox_exec(code: str, df, timeout_seconds: int = 5) -> dict:
    """제한된 네임스페이스에서 LLM 생성 코드 실행. df는 사본 전달.

    반환: {"ok": bool, "result": <coerced>, "error": str | None, "result_type": str}.
    """
    # 실행 직전 재검증 (이중 안전)
    ok, reason = validate_eda_code(code)
    if not ok:
        return {"ok": False, "result": None, "error": f"revalidation failed: {reason}",
                "result_type": None}

    import pandas as pd
    import numpy as np

    safe_globals: dict[str, Any] = {"__builtins__": {}}
    # df는 사본 — 원본 변경 차단
    safe_locals: dict[str, Any] = {
        "df": df.copy() if hasattr(df, "copy") else df,
        "pd": pd, "np": np,
        "result": None,
    }

    # 타임아웃 가드 — 무한 루프/지나치게 무거운 연산 차단 (UNIX signal 기반)
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(int(timeout_seconds))
    try:
        compiled = compile(code, "<eda_freeform>", "exec")
        exec(compiled, safe_globals, safe_locals)
    except SandboxTimeout as e:
        return {"ok": False, "result": None, "error": f"timeout: {e}",
                "result_type": None}
    except Exception as e:
        return {"ok": False, "result": None, "error": f"runtime error: {type(e).__name__}: {e}",
                "result_type": None}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    raw_result = safe_locals.get("result")
    return {
        "ok": True,
        "result": _coerce_result(raw_result),
        "error": None,
        "result_type": type(raw_result).__name__,
    }


# ─────────────────────────────────────────────────────────────────────────
# 3) LLM 코드 생성 (제안만 — 실행은 승인 후)
# ─────────────────────────────────────────────────────────────────────────
async def llm_generate_eda_code(user_query: str, profile: dict,
                                model: str | None) -> dict:
    """사용자 한국어 → pandas/numpy 분석 코드 (제안). 실행 X.

    반환: {"code": "...", "raw": "...", "model": ...} 또는 {"_llm_failed": True, ...}.
    """
    from llm import generate

    system = (
        "제조 데이터 분석 코드 생성기. 사용자 한국어 요청을 pandas/numpy 코드로 변환. "
        "엄격 규칙: (1) df는 이미 로드되어 있음 (읽기 전용), "
        "(2) 결과는 result 변수에 dict로 저장, "
        "(3) 허용 모듈: pandas (pd), numpy (np). 별명 외 사용 금지. "
        "(4) 금지: import, 파일 I/O(open/read), 네트워크, exec/eval, "
        "os/sys/subprocess, df 수정, dunder(__) 접근. "
        "(5) 출력은 코드만 (설명·마크다운·코드펜스 금지). "
        "예: result = df.groupby('PASS_YN')['PRESS_FORCE'].mean().to_dict()"
    )
    import json as _json
    prompt = (
        f"데이터 프로파일:\n{_json.dumps(profile, ensure_ascii=False, default=str)}\n\n"
        f"사용자 요청 (한국어): {user_query}"
    )
    raw = await generate(prompt, system=system, fmt_json=False, model=model)

    # LLM 실패 마커 보존 (D-101)
    if isinstance(raw, str) and raw.startswith('{') and '"_llm_failed"' in raw:
        try:
            import json as _j
            err = _j.loads(raw)
            if err.get("_llm_failed"):
                return err
        except Exception:
            pass

    # 코드펜스 제거 (LLM이 ```python ... ``` 둘러쌀 때)
    code = (raw or "").strip()
    if code.startswith("```"):
        lines = code.split("\n")
        # 첫 줄/마지막 줄의 ``` 제거
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        code = "\n".join(lines).strip()
        # 'python' 헤더 잔재 제거
        if code.lower().startswith("python\n"):
            code = code[7:]

    return {"code": code, "raw": raw, "model": model}
