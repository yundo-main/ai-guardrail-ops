"""Turn a RunRecord into a SecurityEvent (step04 capability)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone

from core.types import RunRecord, SecurityEvent


def to_event(record: RunRecord, model_name: str | None = None, policy_version: str = "policy-1") -> SecurityEvent:
    """Events carry decision/rule/risk/spans, never the raw prompt (privacy by default)."""
    rule_ids = ",".join(m.rule_id for m in record.matches)
    detail = rule_ids or (",".join(record.masked_fields) or record.category)
    return SecurityEvent(
        event_id=f"evt-{record.trace_id}",
        trace_id=record.trace_id,
        decision=record.decision,
        risk=record.risk,
        category=record.category,
        detail=detail,
        timestamp=datetime.now(timezone.utc).isoformat(),
        model_name=model_name,
        policy_version=policy_version,
        spans_json=json.dumps([asdict(s) for s in record.spans]),
    )
