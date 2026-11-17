"""Llama Guard inference adapters.

Two interchangeable backends normalize Llama Guard's ``safe``/``unsafe``
contract into ``LlamaGuardResult``:

- ``OllamaLlamaGuardClient`` (default): calls a local Ollama server, so the
  real integration needs no large Hugging Face download.
- ``LlamaGuardClient``: loads the model with Transformers (optional, heavy).

The imports for both backends are lazy: the day-by-day exercises and unit
tests can run without downloading a model or installing the LLM packages.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from typing import Any
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class LlamaGuardResult:
    """Normalized result passed to the application's policy layer."""

    safe: bool
    category: str | None
    raw: str
    model: str
    provider: str = "meta-llama/transformers"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_guard_output(
    raw: str,
    model: str,
    provider: str = "meta-llama/transformers",
) -> LlamaGuardResult:
    """Parse the model's first-line ``safe``/``unsafe`` contract.

    Llama Guard emits ``safe`` or ``unsafe`` followed by a category for an
    unsafe result.  Unknown output is treated as unsafe so a malformed model
    response cannot accidentally bypass the application's policy.
    """
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    status = lines[0].lower() if lines else "unknown"
    safe = status == "safe"
    category = None if safe else (lines[1] if len(lines) > 1 else "unknown")
    return LlamaGuardResult(
        safe=safe,
        category=category,
        raw=raw.strip(),
        model=model,
        provider=provider,
    )


class LlamaGuardClient:
    """Load and call Llama Guard 3 through the Transformers API."""

    def __init__(self, model_id: str | None = None, max_new_tokens: int = 128):
        self.model_id = model_id or os.getenv("LLAMA_GUARD_MODEL", "meta-llama/Llama-Guard-3-8B")
        self.max_new_tokens = max_new_tokens
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError(
                "Llama Guard dependencies are missing. Install "
                "02_llama_guard_nemo_guardrails/requirements-llm.txt with Python 3.12."
            ) from exc

        self._torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype="auto",
            device_map="auto",
        )

    def classify(self, user_text: str, assistant_text: str | None = None) -> LlamaGuardResult:
        """Classify a user request, optionally together with an assistant reply."""
        chat = [{"role": "user", "content": user_text}]
        if assistant_text:
            chat.append({"role": "assistant", "content": assistant_text})
        inputs = self.tokenizer.apply_chat_template(
            chat,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        device = getattr(self.model, "device", None)
        if device is not None:
            inputs = inputs.to(device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        prompt_length = inputs["input_ids"].shape[-1]
        raw = self.tokenizer.decode(outputs[0][prompt_length:], skip_special_tokens=True)
        return parse_guard_output(raw, self.model_id)


class OllamaLlamaGuardClient:
    """Call Llama Guard through a local Ollama ``/api/chat`` endpoint.

    This is the default backend for the real integration: it needs only a
    running Ollama server and a pulled guard model, not the Transformers
    stack.  Set ``OLLAMA_BASE_URL``/``OLLAMA_GUARD_MODEL`` to override the
    defaults.
    """

    PROVIDER = "ollama/llama-guard"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int = 120,
    ):
        self.model = model or os.getenv("OLLAMA_GUARD_MODEL", "llama-guard3:1b")
        self.base_url = (
            base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self.timeout = timeout

    def classify(self, user_text: str, assistant_text: str | None = None) -> LlamaGuardResult:
        """Classify a user request, optionally together with an assistant reply."""
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
        except OSError as exc:
            raise RuntimeError(
                f"Ollama server is unreachable at {self.base_url}. "
                "Start Ollama and pull the guard model first."
            ) from exc
        raw = payload.get("message", {}).get("content", "")
        return parse_guard_output(raw, self.model, provider=self.PROVIDER)


def get_llama_guard_client(backend: str | None = None):
    """Instantiate the configured Llama Guard backend.

    ``backend`` may be ``"ollama"`` (default) or ``"transformers"``; when it is
    ``None`` the ``LLAMA_GUARD_BACKEND`` environment variable is consulted,
    falling back to ``ollama``.
    """
    selected = (backend or os.getenv("LLAMA_GUARD_BACKEND", "ollama")).lower()
    if selected == "ollama":
        return OllamaLlamaGuardClient()
    if selected == "transformers":
        return LlamaGuardClient()
    raise ValueError(
        f"Unknown Llama Guard backend {selected!r}; use 'ollama' or 'transformers'."
    )
