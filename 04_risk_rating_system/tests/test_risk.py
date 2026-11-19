"""4단계 위험도 분류·이벤트 변환 단위 테스트.

04_risk_rating_system/src/ 만 참조하며, importlib로 격리 로드한다.
03·05·06 단계에도 policy.py·monitoring.py가 있으므로 sys.modules를 임시 교체해 충돌을 막는다.
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).parents[2] / "04_risk_rating_system" / "src"


def _load(module_name: str, filename: str):
    """04단계 src/ 안의 파일을 고유한 이름으로 격리 로드한다."""
    path = _SRC / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# 로드 순서: policy → monitoring → risk (각 모듈의 from X import가 바인딩을 참조)
_bound = {}
def _bind(name, mod):
    _bound[name] = sys.modules.get(name)
    sys.modules[name] = mod

_policy = _load("step04-policy", "policy.py")
_bind("policy", _policy)
_monitoring = _load("step04-monitoring", "monitoring.py")
_bind("monitoring", _monitoring)
_risk = _load("step04-risk", "risk.py")

Decision = _policy.Decision
RiskLevel = _policy.RiskLevel
classify_risk = _risk.classify_risk
event_from_guardrail_file = _risk.event_from_guardrail_file
event_payload = _monitoring.event_payload
make_event = _monitoring.make_event
write_event_result = _risk.write_event_result

for name, prev in _bound.items():
    if prev is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = prev


class Step04RiskTests(unittest.TestCase):
    def test_classify_risk_thresholds(self):
        self.assertEqual(classify_risk(0, 0, 0), RiskLevel.LOW)
        self.assertEqual(classify_risk(1, 1, 1), RiskLevel.MEDIUM)   # 3점
        self.assertEqual(classify_risk(3, 3, 0), RiskLevel.HIGH)     # 6점
        self.assertEqual(classify_risk(3, 3, 2), RiskLevel.CRITICAL) # 8점
        self.assertEqual(classify_risk(3, 3, 3), RiskLevel.CRITICAL) # 9점

    def test_classify_risk_clamps_out_of_range(self):
        self.assertEqual(classify_risk(-5, 0, 0), RiskLevel.LOW)
        self.assertEqual(classify_risk(9, 9, 9), RiskLevel.CRITICAL)

    def test_event_from_guardrail_file(self):
        payload = {
            "event_id": "step03-guardrail-result",
            "trace_id": "step03-guardrail-result",
            "decision": "review",
            "risk": "Critical",
            "category": "prompt_injection",
            "detail": "정책 위반",
            "next": "04_risk_rating_system",
        }
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "step03.json"
            src.write_text(json.dumps(payload), encoding="utf-8")
            event = event_from_guardrail_file(src)
        self.assertEqual(event.event_id, "step03-guardrail-result")
        self.assertEqual(event.decision, Decision.REVIEW)
        self.assertEqual(event.risk, RiskLevel.CRITICAL)
        self.assertEqual(event.source_stage, "step04")
        self.assertEqual(event.status, "open")

    def test_event_payload_contract_fields(self):
        event = make_event("e1", Decision.BLOCK, RiskLevel.HIGH, "data_leakage", "email")
        out = event_payload(event)
        self.assertEqual(out["decision"], "block")
        self.assertEqual(out["risk"], "High")
        self.assertEqual(out["next"], "05_security_dashboard_alerts")
        self.assertEqual(out["schema_version"], "1.0")
        self.assertEqual(out["source_stage"], "step04")

    def test_write_event_result_roundtrip(self):
        event = make_event("e2", Decision.ALLOW, RiskLevel.LOW, "normal", "hello")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "out" / "event.json"
            write_event_result(event, target)
            self.assertTrue(target.parent.exists())
            data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(data["event_id"], "e2")
        self.assertEqual(data["decision"], "allow")


if __name__ == "__main__":
    unittest.main()
