"""Real NVIDIA NeMo Guardrails inference adapter."""

from __future__ import annotations

from pathlib import Path
import os
from typing import Any


class NemoGuardrailsClient:
    """Load a NeMo configuration once and call its real ``LLMRails`` object."""

    def __init__(self, config_path: str | Path | None = None):
        try:
            from nemoguardrails import LLMRails, RailsConfig
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError(
                "NeMo Guardrails is missing. Install "
                "02_llama_guard_nemo_guardrails/requirements-llm.txt with Python 3.12."
            ) from exc

        selected = config_path or os.getenv("NEMO_CONFIG_PATH")
        if selected is None:
            selected = Path(__file__).resolve().parents[1] / "nemo_config"
        self.config_path = Path(selected).resolve()
        self.config = RailsConfig.from_path(str(self.config_path))
        # Reuse this object across requests; initialization compiles the rails.
        self.rails = LLMRails(self.config)

    def generate(self, user_text: str) -> dict[str, Any]:
        """Run input/dialogue/output rails and return NeMo's response object."""
        result = self.rails.generate(messages=[{"role": "user", "content": user_text}])
        if isinstance(result, dict):
            return result
        return {"content": str(result)}
