"""Score-based risk rating (step04 capability): impact + exploitability + exposure -> RiskLevel."""

from __future__ import annotations

from core.types import RiskLevel


def classify_risk(impact: int, exploitability: int, exposure: int) -> RiskLevel:
    """Classify a 0-9 score (each axis 0-3, clamped) into a RiskLevel.

    Same thresholds as step04: >=8 Critical, >=6 High, >=3 Medium, else Low.
    """
    score = max(0, min(9, int(impact) + int(exploitability) + int(exposure)))
    if score >= 8:
        return RiskLevel.CRITICAL
    if score >= 6:
        return RiskLevel.HIGH
    if score >= 3:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
