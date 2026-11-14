"""Security events and risk classification for day 4."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from policy import Decision, RiskLevel


@dataclass(frozen=True)
class SecurityEvent:
    """Immutable evidence record passed from risk classification to monitoring."""
    # 관제 시스템이 검색·집계할 구조화된 보안 이벤트다.
    # 이벤트 형식을 고정하면 대시보드·알림·리포트가 같은 증거를 공유할 수 있다.
    event_id: str
    decision: Decision
    risk: RiskLevel
    category: str
    detail: str
    timestamp: str
    schema_version: str = "1.0"
    trace_id: str = ""
    source_stage: str = "step04"
    policy_version: str = "policy-1"
    model_name: str | None = None
    status: str = "open"
    acknowledged_at: str | None = None


def make_event(event_id: str, decision: Decision, risk: RiskLevel, category: str, detail: str, trace_id: str = "") -> SecurityEvent:
    """Create an event with a UTC timestamp and a stable trace identifier."""
    # 모든 이벤트에 UTC 시각을 붙여 시스템 간 시간대를 통일한다.
    # 나중에 DB나 이벤트 스트림으로 보내더라도 이 생성 함수를 공통 진입점으로 사용할 수 있다.
    return SecurityEvent(event_id, decision, risk, category, detail, datetime.now(timezone.utc).isoformat(), trace_id=trace_id or event_id)


def event_payload(event: SecurityEvent, next_stage: str = "05_security_dashboard_alerts") -> dict[str, object]:
    """Serialize one event for the next day's API exercise."""
    # enum을 문자열로 바꾸고 다음 단계를 기록해 폴더 간 파일 전달을 명확히 한다.
    payload = asdict(event)
    # JSON 경계에서는 Python enum 대신 계약에 정의된 문자열을 사용한다.
    payload["decision"] = event.decision.value
    payload["risk"] = event.risk.value
    payload["next"] = next_stage
    return payload
