"""Offline tests for the real-adapter boundaries; no model is downloaded."""

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "02_llama_guard_nemo_guardrails" / "src"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_llama_guard_parser_is_fail_closed():
    module = load_module("llama_guard_test", SRC / "classifier" / "llama_guard.py")
    assert module.parse_guard_output("safe", "test").safe is True
    unsafe = module.parse_guard_output("unsafe\nS4", "test")
    assert unsafe.safe is False
    assert unsafe.category == "S4"
    unknown = module.parse_guard_output("unexpected", "test")
    assert unknown.safe is False


def test_nemo_config_contains_real_ollama_engine():
    config = (ROOT / "02_llama_guard_nemo_guardrails" / "nemo_config" / "config.yml").read_text()
    assert "engine: ollama" in config
    assert "self check input" in config
    assert "self check output" in config
