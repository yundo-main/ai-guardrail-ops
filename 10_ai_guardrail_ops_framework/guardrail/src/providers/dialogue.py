"""Optional dialogue/topic rails (step02 capability: NeMo Guardrails role).

Two backends behind one callable interface `rail(user_text, assistant_text) -> dict`:

- `KeywordTopicRail`: deterministic stand-in. You declare topics as
  {name: [keywords]}; a prompt matching no topic is off-rail.
- `NemoGuardrailsRail`: lazy wrapper around nemoguardrails.LLMRails. Only used
  when explicitly requested; raises at construction if the package is missing.

Failure policy mirrors the classifier: provider errors are reported as unsafe
(fail closed) by the pipeline, never silently allowed.
"""

from __future__ import annotations

import os

TOPIC_ENV = "GUARDRAIL_TOPICS"  # JSON: {"general": ["summary", "report", ...], ...}

DEFAULT_TOPICS = {
    "general": ["summary", "summarize", "report", "policy", "status", "help", "explain", "what", "how"],
}


class KeywordTopicRail:
    """Deterministic topic check: prompt must hit at least one declared topic."""

    model_name = "keyword-topic-rail"

    def __init__(self, topics: dict[str, list[str]] | None = None):
        import json
        if topics is None:
            raw = os.getenv(TOPIC_ENV)
            topics = json.loads(raw) if raw else DEFAULT_TOPICS
        self.topics = {k: [w.lower() for w in v] for k, v in topics.items()}

    def __call__(self, user_text: str, assistant_text: str | None = None) -> dict:
        text = user_text.lower()
        hits = [name for name, words in self.topics.items() if any(w in text for w in words)]
        return {"on_topic": bool(hits), "topics": hits, "model": self.model_name}


class NemoGuardrailsRail:
    """NeMo Guardrails rails via LLMRails (requires nemoguardrails + config)."""

    def __init__(self, config_path: str | None = None):
        try:
            from nemoguardrails import LLMRails, RailsConfig
        except ImportError as exc:
            raise RuntimeError("Install nemoguardrails to use the NeMo dialogue rail.") from exc
        config = RailsConfig.from_path(config_path or os.getenv("NEMO_CONFIG", "nemo_config"))
        self.rails = LLMRails(config)
        self.model_name = "nemo-guardrails"

    def __call__(self, user_text: str, assistant_text: str | None = None) -> dict:
        res = self.rails.generate(messages=[{"role": "user", "content": user_text}])
        text = "".join(str(m.get("content", "")) for m in res.get("messages", []) if m.get("role") == "assistant")
        # canonical-form rails return a refusal/empty response when off-rail
        return {"on_topic": bool(text.strip()), "response": text, "model": self.model_name}


def build_rail(name: str | None):
    """Factory: None/'off' -> None, 'keywords' -> KeywordTopicRail, 'nemo' -> NemoGuardrailsRail."""
    if not name or name == "off":
        return None
    if name == "keywords":
        return KeywordTopicRail()
    if name == "nemo":
        return NemoGuardrailsRail()
    raise ValueError(f"unknown rail: {name}")
