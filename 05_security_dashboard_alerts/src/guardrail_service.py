"""Application service that composes Day 2 adapters with Day 3 policy.

This module is the real-service boundary: it does not hide the vendor calls,
but it makes their order, failure behavior, and normalized response explicit.

05단계 src/ 폴더 안에 번들된 버전이다.
외부 단계 폴더를 참조하지 않고 같은 src/ 디렉터리의 로컬 복사본을 사용한다.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any
from uuid import uuid4


# 같은 src/ 폴더 — step03-policy.py, step03-guardrail.py, llama_guard.py, nemo_guardrails_client.py가 있다.
SRC = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    """Load a daily exercise module without making its folder a package."""
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load integration module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class GuardrailServiceError(RuntimeError):
    """Raised when a real provider cannot safely produce a decision."""


def _content(result: Any) -> str:
    """Extract text from the common NeMo response shapes."""
    if isinstance(result, dict):
        value = result.get("content")
        if value is not None:
            return str(value)
        messages = result.get("messages")
        if isinstance(messages, list) and messages:
            return str(messages[-1].get("content", ""))
    return str(result)


class GuardrailService:
    """Run input policy, NeMo dialogue rails, Llama classification, output policy."""

    def __init__(self):
        # Day 5 also has a module named ``policy.py``.  Day 3's guardrail.py
        # uses an absolute import, so temporarily bind the intended policy
        # module while loading it and then restore the API's module binding.
        # 05/src/ 안의 step03-policy.py·step03-guardrail.py를 사용한다.
        # policy 모듈명이 05/src/policy.py와 충돌하므로 로드 시 임시로 대체하고 복원한다.
        policy_name = "policy"
        previous_policy = sys.modules.get(policy_name)
        day3_policy = _load(
            "day3_policy_definition",
            SRC / "step03-policy.py",
        )
        sys.modules[policy_name] = day3_policy
        try:
            day3 = _load("day3_policy_for_service", SRC / "step03-guardrail.py")
        finally:
            if previous_policy is None:
                sys.modules.pop(policy_name, None)
            else:
                sys.modules[policy_name] = previous_policy
        llama = _load("day2_llama_for_service", SRC / "llama_guard.py")
        nemo = _load("day2_nemo_for_service", SRC / "nemo_guardrails_client.py")
        self.day3 = day3
        self.llama = llama.LlamaGuardClient()
        self.nemo = nemo.NemoGuardrailsClient()

    def chat(self, prompt: str) -> dict[str, Any]:
        trace_id = f"trace-{uuid4().hex}"
        started = time.perf_counter()
        input_result = self.day3.check_input(prompt)
        if input_result.decision is self.day3.Decision.BLOCK:
            return self._result(
                trace_id, started, "block", input_result.risk.value,
                "policy", input_result.text, input_result.matches,
                llama=None, nemo=None,
            )

        try:
            nemo_raw = self.nemo.generate(prompt)
            response = _content(nemo_raw)
            llama_result = self.llama.classify(prompt, response)
        except Exception as provider_error:
            raise GuardrailServiceError(f"real guardrail provider failed: {provider_error}") from provider_error

        if not llama_result.safe:
            return self._result(
                trace_id, started, "block", "Critical", llama_result.category or "unsafe",
                "안전성 분류 결과가 unsafe입니다.", (), llama=llama_result.as_dict(), nemo=nemo_raw,
            )

        output_result = self.day3.redact_output(response)
        return self._result(
            trace_id, started, output_result.decision.value, output_result.risk.value,
            "output_redaction" if output_result.masked_fields else "safe",
            output_result.text, output_result.matches, llama=llama_result.as_dict(), nemo=nemo_raw,
            masked_fields=list(output_result.masked_fields),
        )

    @staticmethod
    def _result(trace_id, started, decision, risk, category, response, matches, *, llama, nemo, masked_fields=None):
        return {
            "trace_id": trace_id,
            "decision": decision,
            "risk": risk,
            "category": category,
            "response": response,
            "matches": [
                {
                    **asdict(item),
                    "risk": item.risk.value,
                    "decision": item.decision.value,
                }
                for item in matches
            ],
            "llama_guard": llama,
            "nemo_guardrails": nemo,
            "masked_fields": masked_fields or [],
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_stage": "integration-guardrail-service",
            "policy_version": "policy-1",
        }
