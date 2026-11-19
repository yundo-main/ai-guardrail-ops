"""DeepSeek API backend — OpenAI-compatible chat completions."""

from __future__ import annotations

import json
import os
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from providers.model import MODEL_ERROR_RESPONSE, Model, chat_messages


def deepseek_model(api_key: str | None = None, model: str | None = None,
                   base_url: str | None = None, timeout: int = 60) -> Model:
    """Return a callable that calls DeepSeek's chat completions endpoint."""
    key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
    model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    base = (base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")).rstrip("/")

    def call(prompt: str, history=None) -> str:
        if not key:
            return MODEL_ERROR_RESPONSE
        body = json.dumps({
            "model": model,
            "messages": chat_messages(history, prompt),
            "stream": False,
        }).encode()
        req = Request(f"{base}/chat/completions", data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }, method="POST")
        try:
            with urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"] or MODEL_ERROR_RESPONSE
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, IndexError):
            return MODEL_ERROR_RESPONSE

    call.model_name = f"deepseek:{model}"  # type: ignore[attr-defined]
    return call
