"""Aggregate metrics and critical alerts (day 5 capability)."""

from __future__ import annotations

from collections import Counter

from core.types import Decision, RiskLevel, SecurityEvent


def metrics(events: list[SecurityEvent]) -> dict:
    total = len(events)
    blocked = sum(e.decision is Decision.BLOCK for e in events)
    review = sum(e.decision is Decision.REVIEW for e in events)
    return {
        "schema_version": "1.0",
        "total_events": total,
        "blocked_events": blocked,
        "review_events": review,
        "block_rate": round(blocked / total, 4) if total else 0.0,
        "review_rate": round(review / total, 4) if total else 0.0,
        "open_events": sum(e.status == "open" for e in events),
        "acknowledged_events": sum(e.status == "acknowledged" for e in events),
        "by_category": dict(Counter(e.category for e in events)),
        "by_risk": dict(Counter(e.risk.value for e in events)),
    }


def critical_alert(event: SecurityEvent) -> dict | None:
    if event.risk is not RiskLevel.CRITICAL:
        return None
    return {"severity": "critical", "title": "AI 보안 Critical 이벤트", "event": event.as_dict()}


def stage_latency(records) -> dict[str, dict[str, float]]:
    """Per-stage latency (avg/max ms) over RunRecords: the observability view of the pipeline."""
    buckets: dict[str, list[float]] = {}
    for r in records:
        for s in r.spans:
            buckets.setdefault(s.stage, []).append(s.ms)
    return {k: {"count": len(v), "avg_ms": round(sum(v) / len(v), 3), "max_ms": max(v)} for k, v in buckets.items()}
