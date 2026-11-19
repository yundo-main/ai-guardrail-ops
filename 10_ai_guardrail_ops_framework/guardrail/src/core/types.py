"""Shared vocabulary of the framework (self-contained; no imports from steps 01-06)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

    @property
    def rank(self) -> int:
        return ("Low", "Medium", "High", "Critical").index(self.value)


@dataclass(frozen=True)
class PolicyMatch:
    rule_id: str
    reason: str
    risk: RiskLevel
    decision: Decision


@dataclass(frozen=True)
class Span:
    """Timing of one pipeline stage: the unit of observability."""

    stage: str
    outcome: str
    ms: float


@dataclass(frozen=True)
class SecurityEvent:
    event_id: str
    trace_id: str
    decision: Decision
    risk: RiskLevel
    category: str
    detail: str
    timestamp: str
    schema_version: str = "1.1"
    source_stage: str = "framework"
    policy_version: str = "policy-1"
    model_name: str | None = None
    status: str = "open"
    acknowledged_at: str | None = None
    spans_json: str = ""  # JSON array of Span dicts; observability persisted with the event

    def as_dict(self) -> dict:
        data = asdict(self)
        data["decision"] = self.decision.value
        data["risk"] = self.risk.value
        return data


@dataclass
class RunRecord:
    """Everything observable about one request through the pipeline."""

    trace_id: str
    prompt: str
    response: str
    decision: Decision
    risk: RiskLevel
    category: str
    matches: tuple[PolicyMatch, ...] = ()
    masked_fields: tuple[str, ...] = ()
    spans: list[Span] = field(default_factory=list)
    classifier: dict | None = None
    rail: dict | None = None

    @property
    def latency_ms(self) -> float:
        return round(sum(s.ms for s in self.spans), 2)

    def as_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "decision": self.decision.value,
            "risk": self.risk.value,
            "category": self.category,
            "response": self.response,
            "matches": [
                {"rule_id": m.rule_id, "reason": m.reason, "risk": m.risk.value, "decision": m.decision.value}
                for m in self.matches
            ],
            "masked_fields": list(self.masked_fields),
            "classifier": self.classifier,
            "rail": self.rail,
            "spans": [asdict(s) for s in self.spans],
            "latency_ms": self.latency_ms,
        }
