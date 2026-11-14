"""Optional safety classifier (day 2 capability): Llama Guard 3 via Transformers.

Lazy import: the framework runs without torch/transformers. Unknown or malformed
output is treated as unsafe (fail closed).
"""

from __future__ import annotations

import os


def parse_guard_output(raw: str) -> dict:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    safe = bool(lines) and lines[0].lower() == "safe"
    return {"safe": safe, "category": None if safe else (lines[1] if len(lines) > 1 else "unknown"), "raw": raw.strip()}


class LlamaGuardClassifier:
    def __init__(self, model_id: str | None = None, max_new_tokens: int = 128):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("Install transformers/torch (Python 3.12) to use the Llama Guard classifier.") from exc
        self.model_id = model_id or os.getenv("LLAMA_GUARD_MODEL", "meta-llama/Llama-Guard-3-8B")
        self.max_new_tokens = max_new_tokens
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_id, torch_dtype="auto", device_map="auto")

    def __call__(self, user_text: str, assistant_text: str | None = None) -> dict:
        chat = [{"role": "user", "content": user_text}]
        if assistant_text:
            chat.append({"role": "assistant", "content": assistant_text})
        inputs = self.tokenizer.apply_chat_template(chat, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt")
        inputs = inputs.to(self.model.device)
        out = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens, pad_token_id=self.tokenizer.eos_token_id)
        raw = self.tokenizer.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        result = parse_guard_output(raw)
        result["model"] = self.model_id
        return result
