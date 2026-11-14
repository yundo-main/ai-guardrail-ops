from __future__ import annotations

from dataclasses import dataclass

from policy import Decision, RiskLevel


@dataclass(frozen=True)
class SecurityEvent:
    """Versioned event contract shared by API, SQLite, metrics, and alerts."""
    # 대시보드와 알림이 공유하는 이벤트 스키마다.
    # API 요청·집계 함수·외부 알림 사이의 데이터 계약 역할을 한다.
    event_id: str
    decision: Decision
    risk: RiskLevel
    category: str
    detail: str
    timestamp: str
    # 결과 파일과 API가 서로 다른 단계에서 같은 사건을 추적하기 위한 계약 필드다.
    schema_version: str = "1.0"
    trace_id: str = ""
    source_stage: str = "step05"
    policy_version: str = "policy-1"
    model_name: str | None = None
    status: str = "open"
    acknowledged_at: str | None = None
