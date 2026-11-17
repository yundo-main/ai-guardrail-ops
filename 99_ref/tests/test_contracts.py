import json
import unittest
from pathlib import Path

root = Path(__file__).parents[2]


class ContractTests(unittest.TestCase):
    def test_result_contract_files_have_trace_fields(self):
        step03 = json.loads((root / "03_policy_blocking_output_filtering" / "results" / "step03-guardrail-result.json").read_text(encoding="utf-8"))
        step04 = json.loads((root / "04_risk_rating_system" / "results" / "step04-security-event.json").read_text(encoding="utf-8"))
        self.assertEqual(step03["schema_version"], "1.0")
        self.assertEqual(step03["trace_id"], step04["trace_id"])
        self.assertEqual(step04["next"], "05_security_dashboard_alerts")

    def test_policy_json_has_expected_rules(self):
        entries = json.loads((root / "03_policy_blocking_output_filtering" / "policy-rules.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(entries), 4)
        self.assertEqual(entries[0]["decision"], "block")
        self.assertIn("High", {entry["risk"] for entry in entries})

    def test_step02_adapter_handoffs_are_explicit(self):
        import importlib.util

        path = root / "02_llama_guard_nemo_guardrails/src/contracts/adapters.py"
        spec = importlib.util.spec_from_file_location("step02-adapters_contract", path)
        module = importlib.util.module_from_spec(spec)
        import sys

        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        records = module.compare_adapters()
        self.assertEqual(records[0]["handoff_to"], "애플리케이션 정책 엔진")
        self.assertEqual(records[1]["handoff_to"], "LLM 호출 또는 출력 Guardrail")
        self.assertIn("not_responsible_for", records[0])


if __name__ == "__main__":
    unittest.main()
