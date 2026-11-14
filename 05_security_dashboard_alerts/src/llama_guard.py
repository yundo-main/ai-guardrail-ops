"""Real Llama Guard 3 inference adapter.

The imports are intentionally lazy: the day-by-day exercises and unit tests
can run without downloading an 8B model.  When this adapter is instantiated it
loads the model from Hugging Face and performs the actual Transformers call.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from typing import Any


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


def parse_guard_output(raw: str, model: str) -> LlamaGuardResult:
    """Parse the model's first-line ``safe``/``unsafe`` contract.

    Llama Guard emits ``safe`` or ``unsafe`` followed by a category for an
    unsafe result.  Unknown output is treated as unsafe so a malformed model
    response cannot accidentally bypass the application's policy.
    """
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    status = lines[0].lower() if lines else "unknown"
    safe = status == "safe"
    category = None if safe else (lines[1] if len(lines) > 1 else "unknown")
    return LlamaGuardResult(safe=safe, category=category, raw=raw.strip(), model=model)


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
