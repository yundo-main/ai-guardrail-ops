"""Output redaction (day 3 capability). Patterns live in config/output-patterns.json."""

from __future__ import annotations

import json
from pathlib import Path
import re

from core.types import RiskLevel

PATTERNS_PATH = Path(__file__).resolve().parents[2] / "config" / "output-patterns.json"
_FLAGS = {"IGNORECASE": re.IGNORECASE, "DOTALL": re.DOTALL}


def load_patterns(path: str | Path | None = None) -> tuple[tuple[str, re.Pattern], ...]:
    """Load masking patterns. A bad file raises: redaction must not silently vanish."""
    entries = json.loads(Path(path or PATTERNS_PATH).read_text(encoding="utf-8"))
    return tuple(
        (e["field"], re.compile(e["pattern"], sum(_FLAGS.get(f, 0) for f in e.get("flags", []))))
        for e in entries
    )


OUTPUT_PATTERNS = load_patterns()


def redact(text: str, patterns=None) -> tuple[str, tuple[str, ...], RiskLevel]:
    """Mask sensitive fields; returns (masked_text, fields, risk)."""
    fields: list[str] = []
    for field, pattern in (patterns if patterns is not None else OUTPUT_PATTERNS):
        text, count = pattern.subn(f"[{field.upper()}_REDACTED]", text)
        if count:
            fields.append(field)
    if not fields:
        return text, (), RiskLevel.LOW
    risk = RiskLevel.CRITICAL if {"api_key", "secret_keyword"} & set(fields) else RiskLevel.HIGH
    return text, tuple(fields), risk
