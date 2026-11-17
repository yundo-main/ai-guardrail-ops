"""Offline tests for the real-adapter boundaries; no model is downloaded."""

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "02_llama_guard_nemo_guardrails" / "src"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestRealGuardAdapters(unittest.TestCase):
    def test_llama_guard_parser_is_fail_closed(self):
        module = load_module("llama_guard_test", SRC / "classifier" / "llama_guard.py")
        self.assertTrue(module.parse_guard_output("safe", "test").safe)
        unsafe = module.parse_guard_output("unsafe\nS4", "test")
        self.assertFalse(unsafe.safe)
        self.assertEqual(unsafe.category, "S4")
        unknown = module.parse_guard_output("unexpected", "test")
        self.assertFalse(unknown.safe)

    def test_nemo_config_contains_real_ollama_engine(self):
        config = (ROOT / "02_llama_guard_nemo_guardrails" / "nemo_config" / "config.yml").read_text()
        self.assertIn("engine: ollama", config)
        self.assertIn("self check input", config)
        self.assertIn("self check output", config)


if __name__ == "__main__":
    unittest.main()
