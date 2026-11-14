"""Rules and risk classification for day 3."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import re


class Decision(str, Enum):
    """The application action after a policy match is interpreted."""
    # 정책 엔진이 반환할 세 가지 운영 상태다.
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"


class RiskLevel(str, Enum):
    """The highest operational urgency attached to a policy result."""
    # 가장 높은 위험 등급을 기준으로 대응 강도를 결정한다.
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(frozen=True)
class PolicyMatch:
    """Evidence that one named rule matched the input."""
    # 규칙이 매칭됐을 때 감사 로그에 남길 최소 정보다.
    rule_id: str
    reason: str
    risk: RiskLevel
    decision: Decision


@dataclass(frozen=True)
class Rule:
    """Executable policy configuration plus the reason and response contract."""
    # 정규식과 판정 결과를 하나의 정책 규칙으로 묶는다.
    rule_id: str
    pattern: re.Pattern[str]
    reason: str
    risk: RiskLevel
    decision: Decision


def load_rules(path: str | Path | None = None) -> tuple[Rule, ...]:
    """Load versioned policy rules from JSON while keeping a safe code default."""
    # 설정 파일이 없거나 잘못되면 학습 흐름이 멈추지 않도록 기본 규칙을 사용한다.
    # 운영에서는 잘못된 정책을 조용히 무시하지 말고 배포 단계에서 검증해야 한다.
    default_path = Path(__file__).resolve().parents[1] / "policy-rules.json"
    policy_path = Path(path or os.getenv("GUARDRAIL_POLICY_PATH", str(default_path)))
    try:
        entries = json.loads(policy_path.read_text(encoding="utf-8"))
        rules = []
        flag_map = {"IGNORECASE": re.IGNORECASE, "DOTALL": re.DOTALL}
        for entry in entries:
            # JSON에는 정규식 플래그를 문자열로 저장하므로 런타임 플래그로 변환한다.
            flags = sum((flag_map.get(flag, 0) for flag in entry.get("flags", [])), 0)
            rules.append(Rule(entry["rule_id"], re.compile(entry["pattern"], flags), entry["reason"], RiskLevel(entry["risk"]), Decision(entry["decision"])))
        return tuple(rules)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, re.error):
        # 학습 중 설정 파일이 없어도 안전한 기본 정책으로 계속 실행한다.
        # 운영 배포에서는 이 fallback 대신 시작 단계에서 설정 오류를 차단하는 편이 바람직하다.
        return (
            Rule("INJ-001", re.compile(r"ignore\s+(?:all\s+)?previous instructions", re.I), "prompt injection", RiskLevel.HIGH, Decision.BLOCK),
            Rule("EXF-001", re.compile(r"(?:reveal|print|show|dump).{0,40}(?:system prompt|secret|credential|api key)", re.I | re.S), "secret exfiltration request", RiskLevel.CRITICAL, Decision.BLOCK),
            Rule("TOOL-001", re.compile(r"(?:delete|drop|rm\s+-rf|disable).{0,30}(?:database|production|audit|logging)", re.I | re.S), "dangerous tool or infrastructure action", RiskLevel.CRITICAL, Decision.BLOCK),
            Rule("ABUSE-001", re.compile(r"(?:credential stuffing|ransomware|malware|steal passwords)", re.I), "harmful cyber request", RiskLevel.HIGH, Decision.BLOCK),
        )


INPUT_RULES = load_rules()


def inspect_input(text: str) -> list[PolicyMatch]:
    """Return every matching rule so compound violations remain auditable."""
    # 모든 규칙을 검사해 여러 위반을 동시에 기록한다.
    # 첫 번째 매치에서 멈추지 않는 이유는 복합 위반의 근거를 모두 감사 로그에 남기기 위해서다.
    return [PolicyMatch(r.rule_id, r.reason, r.risk, r.decision) for r in INPUT_RULES if r.pattern.search(text)]


def highest_risk(matches: list[PolicyMatch]) -> RiskLevel:
    """Select the most urgent risk so a lower match cannot hide a Critical one."""
    # 여러 위반이 있으면 가장 높은 등급 하나를 최종 등급으로 사용한다.
    # 보수적인 기본값을 사용해야 한 요청의 낮은 위험 매치가 Critical 매치를 덮지 않는다.
    order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
    return max(matches, key=lambda item: order[item.risk]).risk if matches else RiskLevel.LOW
