"""Model backends (step06 capability): Ollama or DeepSeek via LLM_PROVIDER."""

from __future__ import annotations

import json
import os
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

Model = Callable[..., str]

HISTORY_LIMIT = 20

MODEL_ERROR_RESPONSE = "모델 호출에 실패했습니다. LLM 서버 연결 상태를 확인하세요."


def sanitize_history(history) -> list[dict]:
    """Keep only well-formed user/assistant turns, capped at HISTORY_LIMIT."""
    out = []
    for m in (history or [])[-HISTORY_LIMIT:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") \
                and isinstance(m.get("content"), str) and m["content"].strip():
            out.append({"role": m["role"], "content": m["content"]})
    return out


def chat_messages(history, prompt: str) -> list[dict]:
    """Build an OpenAI-style messages array from prior turns plus the new prompt."""
    return sanitize_history(history) + [{"role": "user", "content": prompt}]


def ollama_model(model: str | None = None, base_url: str | None = None, timeout: int = 60) -> Model:
    """Return a callable that asks a local Ollama; returns MODEL_ERROR_RESPONSE on failure."""
    model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    base = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")

    def call(prompt: str, history=None) -> str:
        body = json.dumps({"model": model, "messages": chat_messages(history, prompt),
                           "stream": False}).encode()
        req = Request(f"{base}/api/chat", data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode()).get("message", {}).get("content") or MODEL_ERROR_RESPONSE
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            return MODEL_ERROR_RESPONSE

    call.model_name = model  # type: ignore[attr-defined]
    return call


def default_model() -> Model:
    """Pick the model backend.

    LLM_PROVIDER selects:
      ollama   (default) — local Ollama via OLLAMA_BASE_URL/OLLAMA_MODEL
      deepseek           — DeepSeek API via DEEPSEEK_API_KEY/DEEPSEEK_MODEL
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "deepseek":
        from providers.deepseek import deepseek_model
        return deepseek_model()
    return ollama_model()
