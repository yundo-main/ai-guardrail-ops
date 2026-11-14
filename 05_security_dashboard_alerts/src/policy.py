from enum import Enum


class Decision(str, Enum):
    """The action counted by dashboard metrics."""
    # 관제 집계에서 허용·차단·검토를 구분하는 상태값이다.
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"


class RiskLevel(str, Enum):
    """The urgency that determines whether an alert is emitted."""
    # Critical 이벤트는 별도 알림 대상으로 사용한다.
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"
