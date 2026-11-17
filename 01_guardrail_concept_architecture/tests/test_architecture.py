import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "01_guardrail_concept_architecture/src/architecture.py"
spec = importlib.util.spec_from_file_location("step01-architecture", PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ArchitectureTests(unittest.TestCase):
    def test_day_one_pipeline_runs_with_deterministic_model(self):
        result = module.run_pipeline("hello")
        self.assertEqual(result.decision, "allow")
        self.assertIn("model", result.stages)
        self.assertIn("monitoring", result.stages)

    def test_empty_input_is_blocked_before_model(self):
        result = module.run_pipeline("  ")
        self.assertEqual(result.decision, "block")
        self.assertEqual(result.model_response, "")

    def test_empty_model_response_requires_review(self):
        result = module.run_pipeline("hello", model=lambda _: "")
        self.assertEqual(result.decision, "review")


if __name__ == "__main__":
    unittest.main()
