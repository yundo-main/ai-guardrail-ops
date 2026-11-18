"""Dashboard metrics and critical alerts for step 05."""

from __future__ import annotations

import os

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone

from event_model import SecurityEvent
from policy import Decision, RiskLevel


def make_event(event_id: str, decision: Decision, risk: RiskLevel, category: str, detail: str, trace_id: str = "") -> SecurityEvent:
    """Create a normalized event for tests, API adapters, or integration code."""
    # 테스트와 통합 실행에서 동일한 이벤트 생성 규칙을 재사용한다.
    return SecurityEvent(event_id, decision, risk, category, detail, datetime.now(timezone.utc).isoformat(), trace_id=trace_id or event_id)


def dashboard_metrics(events: list[SecurityEvent]) -> dict[str, object]:
    """Aggregate events into screen-safe counts and distributions."""
    # 대시보드 카드와 그래프에 필요한 최소 집계값을 만든다.
    # 원문 이벤트를 화면에 직접 노출하지 않고 운영 판단에 필요한 집계만 반환한다.
    total = len(events)
    # 0으로 나누지 않으면서 빈 대시보드도 유효한 JSON으로 반환한다.
    return {
        "total_events": total,
        "blocked_events": sum(e.decision is Decision.BLOCK for e in events),
        "review_events": sum(e.decision is Decision.REVIEW for e in events),
        "block_rate": round(sum(e.decision is Decision.BLOCK for e in events) / total, 4) if total else 0.0,
        "review_rate": round(sum(e.decision is Decision.REVIEW for e in events) / total, 4) if total else 0.0,
        "by_category": dict(Counter(e.category for e in events)),
        "by_risk": dict(Counter(e.risk.value for e in events)),
        "open_events": sum(e.status == "open" for e in events),
        "acknowledged_events": sum(e.status == "acknowledged" for e in events),
    }


_ALERT_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


def alert_min_risk() -> RiskLevel:
    """Return the lowest risk level that triggers outbound alert delivery."""
    # GUARDRAIL_ALERT_MIN_RISK로 발송 임계값을 조정한다 — 기본은 Critical만.
    # 잘못된 값은 가장 보수적인 Critical로 되돌려 알림 폭주를 막는다.
    raw = os.environ.get("GUARDRAIL_ALERT_MIN_RISK", "Critical").strip()
    for level in RiskLevel:
        if raw.lower() == level.value.lower():
            return level
    return RiskLevel.CRITICAL


def risk_alert(event: SecurityEvent) -> dict[str, object] | None:
    """Return an alert payload when the event meets the configured threshold."""
    # 임계값 미만이면 payload를 만들지 않아 알림 피로를 줄인다.
    # 실제 Discord 외 채널 전송은 이 payload를 받는 어댑터의 책임으로 분리한다.
    if _ALERT_ORDER[event.risk] < _ALERT_ORDER[alert_min_risk()]:
        return None
    return {
        "severity": event.risk.value.lower(),
        "title": f"AI 보안 {event.risk.value} 이벤트",
        "event": asdict(event),
    }


def critical_alert(event: SecurityEvent) -> dict[str, object] | None:
    """Return an alert payload only for Critical events."""
    # Critical이 아니면 알림을 만들지 않아 알림 피로를 줄인다.
    # 실제 Slack·이메일 전송은 이 payload를 받는 별도 어댑터의 책임으로 분리한다.
    if event.risk is not RiskLevel.CRITICAL:
        return None
    return {"severity": "critical", "title": "AI 보안 Critical 이벤트", "event": asdict(event)}
