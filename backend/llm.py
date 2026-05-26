"""
backend/llm.py
==============
Ollama 클라이언트 래퍼. **모델 교체는 오직 여기(환경변수)에서만** 일어난다.
(CLAUDE.md §1: 모델명 하드코딩 금지)

스캐폴딩: OLLAMA_MODEL=gemma4:e4b   (빠름, 배관 검증용)
에이전트 검증: OLLAMA_MODEL=gemma4:26b (똑똑함, 툴체인 검증용)
❌ 31B 금지 (VRAM 8GB)
"""

from __future__ import annotations
import os
import json
import httpx

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))


async def generate(prompt: str, system: str | None = None,
                   fmt_json: bool = False, model: str | None = None) -> str:
    """Ollama /api/generate 호출. fmt_json=True면 JSON 출력 강제.
    model 지정 시 그 모델로 (UI 선택용). 미지정이면 환경변수 기본값."""
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
            # LLM이 안 떠 있어도 파이프라인은 죽지 않게 (데모 안전장치)
            return json.dumps({"_llm_error": str(e),
                               "_hint": "ollama 컨테이너와 모델(pull) 확인"})


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
