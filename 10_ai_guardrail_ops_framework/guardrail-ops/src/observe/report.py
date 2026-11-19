"""Weekly/monthly operations report (step06 capability)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from observe.metrics import metrics

PERIOD_DAYS = {"weekly": 7, "monthly": 30}


def period_report(events, period: str = "weekly", now: datetime | None = None) -> dict:
    if period not in PERIOD_DAYS:
        raise ValueError("period must be weekly or monthly")
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=PERIOD_DAYS[period])
    recent = [e for e in events
              if datetime.fromisoformat(e.timestamp) >= cutoff]
    m = metrics(list(recent))
    actions = ["반복 카테고리의 정책 오탐·미탐을 재평가"]
    if m["by_risk"].get("Critical"):
        actions.insert(0, "Critical 이벤트의 담당자와 대응 기한을 확인")
    if m["open_events"]:
        actions.append(f"미확인 이벤트 {m['open_events']}건 확인(acknowledge)")
    return {"period": period, "period_days": PERIOD_DAYS[period],
            "generated_at": now.isoformat(), "events_in_period": len(recent),
            "metrics": m, "next_actions": actions}
