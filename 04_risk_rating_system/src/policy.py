"""Shared decision and risk enums for day 4."""

from enum import Enum


class Decision(str, Enum):
    """The action that monitoring should associate with a security event."""
    # 이벤트가 허용·차단·검토 중 어느 상태인지 표현한다.
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"


class RiskLevel(str, Enum):
    """The four operational urgency levels used by the learning pipeline."""
    # 관제 대응의 우선순위를 나타내는 네 단계다.
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"
