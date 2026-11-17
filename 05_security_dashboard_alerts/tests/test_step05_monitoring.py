"""5단계 모니터링·알림 단위 테스트.

05_security_dashboard_alerts/src/ 만 참조한다.
3단계 모듈을 sys.path에 추가하지 않으므로 이 파일만 복사해도 독립 실행이 가능하다.
"""

import sys
import unittest
from pathlib import Path

root = Path(__file__).parents[2]
sys.path.insert(0, str(root / "05_security_dashboard_alerts" / "src"))

from monitoring import critical_alert, dashboard_metrics, make_event  # noqa: E402
from policy import Decision, RiskLevel  # noqa: E402


class Step05MonitoringTests(unittest.TestCase):
    def test_metrics_blocked_count(self):
        event = make_event("e1", Decision.BLOCK, RiskLevel.CRITICAL, "secret exfiltration request", "blocked")
        self.assertEqual(dashboard_metrics([event])["blocked_events"], 1)

    def test_critical_alert_emitted(self):
        event = make_event("e2", Decision.BLOCK, RiskLevel.CRITICAL, "prompt injection", "blocked")
        self.assertEqual(critical_alert(event)["severity"], "critical")

    def test_non_critical_alert_is_none(self):
        event = make_event("e3", Decision.BLOCK, RiskLevel.HIGH, "policy match", "blocked")
        self.assertIsNone(critical_alert(event))

    def test_empty_event_list_metrics(self):
        metrics = dashboard_metrics([])
        self.assertEqual(metrics["total_events"], 0)
        self.assertEqual(metrics["block_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
