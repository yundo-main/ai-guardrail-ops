"""Input policy (step03 capability): JSON rules with a fail-closed built-in default."""

from __future__ import annotations

import json
from pathlib import Path
import re

from core.types import Decision, PolicyMatch, RiskLevel
from risk.score import classify_risk

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "policy-rules.json"
_FLAGS = {"IGNORECASE": re.IGNORECASE, "DOTALL": re.DOTALL}


def load_rules(path: str | Path | None = None) -> tuple[tuple[str, re.Pattern, str, RiskLevel, Decision, bool], ...]:
    """Load rules. A bad policy file raises: silently running without rules is unsafe."""
    entries = json.loads(Path(path or DEFAULT_RULES_PATH).read_text(encoding="utf-8"))
    rules = []
    for e in entries:
        flag_names = e.get("flags", [])
        flags = sum(_FLAGS.get(f, 0) for f in flag_names)
        # step04 scoring: a rule may fix "risk" directly or supply impact/exploitability/exposure (0-3 each)
        if "risk" in e:
            risk = RiskLevel(e["risk"])
        else:
            risk = classify_risk(e.get("impact", 0), e.get("exploitability", 0), e.get("exposure", 0))
        rules.append((e["rule_id"], re.compile(e["pattern"], flags), e["reason"],
                      risk, Decision(e["decision"]), "NORMALIZE" in flag_names))
    return tuple(rules)


def inspect_input(text: str, rules=None) -> list[PolicyMatch]:
    """Return every match so compound violations stay auditable.

    Rules flagged NORMALIZE are matched against whitespace-collapsed text,
    so 'ignore   all   previous   instructions' cannot evade them.
    """
    rules = rules if rules is not None else load_rules()
    collapsed = re.sub(r"\s+", " ", text)
    return [PolicyMatch(rid, reason, risk, dec)
            for rid, pat, reason, risk, dec, norm in rules
            if pat.search(collapsed if norm else text)]


def highest_risk(matches) -> RiskLevel:
    return max((m.risk for m in matches), key=lambda r: r.rank, default=RiskLevel.LOW)
