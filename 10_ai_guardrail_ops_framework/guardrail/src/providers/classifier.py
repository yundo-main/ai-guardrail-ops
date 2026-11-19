"""Optional safety classifier: Llama Guard via a local Ollama server.

Calls ``/api/chat`` on Ollama with a pulled guard model (default
``llama-guard3:1b``). Only stdlib ``urllib`` is used, so the framework still
runs without torch/transformers — it just needs a running Ollama server.
Unknown or malformed output is treated as unsafe (fail closed).
"""

from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


def parse_guard_output(raw: str) -> dict:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    safe = bool(lines) and lines[0].lower() == "safe"
    return {"safe": safe, "category": None if safe else (lines[1] if len(lines) > 1 else "unknown"), "raw": raw.strip()}


class LlamaGuardClassifier:
    """Call Llama Guard through a local Ollama ``/api/chat`` endpoint.

    Set ``OLLAMA_BASE_URL``/``OLLAMA_GUARD_MODEL`` to override the defaults.
    """

    PROVIDER = "ollama/llama-guard"

    def __init__(self, model: str | None = None, base_url: str | None = None, timeout: int = 120):
        self.model = model or os.getenv("OLLAMA_GUARD_MODEL", "llama-guard3:1b")
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.timeout = timeout

    def __call__(self, user_text: str, assistant_text: str | None = None) -> dict:
        chat = [{"role": "user", "content": user_text}]
        if assistant_text:
            chat.append({"role": "assistant", "content": assistant_text})
        body = json.dumps(
            {
                "model": self.model,
                "messages": chat,
                "stream": False,
                "options": {"num_predict": 128},
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError) as exc:
            raise RuntimeError(
                f"Ollama server is unreachable at {self.base_url}. "
                "Start Ollama and pull the guard model first."
            ) from exc
        raw = payload.get("message", {}).get("content", "")
        result = parse_guard_output(raw)
        result["model"] = self.model
        result["provider"] = self.PROVIDER
        return result
