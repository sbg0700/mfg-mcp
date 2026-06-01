"""
backend/llm.py
==============
Ollama 클라이언트 래퍼. **모델 교체는 오직 여기(환경변수)에서만** 일어난다.
(CLAUDE.md §1: 모델명 하드코딩 금지)

스캐폴딩: OLLAMA_MODEL=gemma4:e4b   (빠름, 배관 검증용)
에이전트 검증: OLLAMA_MODEL=gemma4:26b (똑똑함, 8GB VRAM 환경에선 CPU 오프로딩으로 매우 느림 — D-100)
❌ 31B 금지 (VRAM 8GB)

STEP 1B-3d B3 (D-101):
- generate(): HTTP 에러는 {"_llm_failed": true, "error": ..} 마커로 명확히 표면화.
              위장 _llm_error 키 폐기 — 호출부가 _llm_failed 체크 가능하게.
- _try_parse_llm(raw): 견고한 JSON 파싱. 코드펜스/앞뒤 텍스트 제거 후 시도.
- generate_json(): generate + 파싱 + 재시도 묶음. 호출부는 dict로 받음.
"""

from __future__ import annotations
import os
import json
import re
import httpx

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))


async def generate(prompt: str, system: str | None = None,
                   fmt_json: bool = False, model: str | None = None) -> str:
    """Ollama /api/generate 호출. fmt_json=True면 JSON 출력 강제.
    model 지정 시 그 모델로 (UI 선택용). 미지정이면 환경변수 기본값.
    HTTP 에러 시 {"_llm_failed": true, "error": ..} 마커 JSON 문자열을 반환 (D-101).
    호출부는 _try_parse_llm 또는 generate_json을 사용해 마커를 체크.
    """
    payload: dict = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system
    if fmt_json:
        payload["format"] = "json"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
            r.raise_for_status()
            return r.json().get("response", "")
        except httpx.HTTPError as e:
            # 위장 금지 — 명확한 마커. 호출부가 _llm_failed를 반드시 체크.
            return json.dumps({
                "_llm_failed": True,
                "error": str(e),
                "hint": "ollama 컨테이너/모델(pull)/타임아웃 확인",
                "model_attempted": payload["model"],
            })


def _coerce_json(raw: str):
    """LLM 출력에서 JSON을 견고하게 추출. 코드펜스 제거 + 첫 {...} 부분 추출 후 파싱.
    실패 시 None 반환."""
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("```"):
        # ```json ... ``` 또는 ``` ... ``` 펜스 제거
        s = s.strip("`").strip()
        if s.lower().startswith("json"):
            s = s[4:].lstrip(":").strip()
    # 첫 { ~ 마지막 } 추출 (멀티라인 허용)
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        s = m.group(0)
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _try_parse_llm(raw: str) -> dict:
    """generate() 결과 문자열을 dict로 변환. _llm_failed 마커 보존.

    반환:
      - 정상 JSON → 파싱된 dict
      - _llm_failed 마커 JSON → 그대로 (호출부가 보고 처리)
      - 깨진 JSON → {"_llm_failed": True, "error": "json parse failed", "raw_preview": ..}
    """
    if not raw:
        return {"_llm_failed": True, "error": "empty response"}
    # 우선 직접 시도
    try:
        out = json.loads(raw)
        if isinstance(out, dict):
            return out
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    # 보정 시도
    coerced = _coerce_json(raw)
    if isinstance(coerced, dict):
        return coerced
    # 둘 다 실패
    preview = (raw[:200] + "…") if len(raw) > 200 else raw
    return {"_llm_failed": True, "error": "json parse failed", "raw_preview": preview}


async def generate_json(prompt: str, system: str | None = None,
                        model: str | None = None, retries: int = 2) -> dict:
    """generate + 견고한 파싱 + 재시도. 호출부 권장 진입점 (D-101).

    소형 모델(e4b)의 깨진 JSON / HTTP 에러를 모두 흡수. 최대 (retries+1)회 시도.
    최종 실패 시 {"_llm_failed": True, "error": ..} 반환.
    """
    last_err = "unknown"
    for attempt in range(retries + 1):
        raw = await generate(prompt, system=system, fmt_json=True, model=model)
        parsed = _try_parse_llm(raw)
        if not parsed.get("_llm_failed"):
            return parsed
        last_err = str(parsed.get("error", "")) or last_err
    return {"_llm_failed": True, "error": last_err, "attempts": retries + 1}


async def health() -> dict:
    """Ollama 서버 + 모델 가용성 확인."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            return {"ollama": "up", "model_target": OLLAMA_MODEL,
                    "model_available": OLLAMA_MODEL in models,
                    "installed_models": models}
        except httpx.HTTPError as e:
            return {"ollama": "down", "error": str(e)}
