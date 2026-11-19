"""Guardrail pipeline with per-stage spans (step01 architecture + observability).

input policy -> model -> [classifier] -> output redaction -> (caller records event)
"""

from __future__ import annotations

import inspect
import time
from typing import Callable
from uuid import uuid4

from core.types import Decision, RiskLevel, RunRecord, Span
from guard.output import redact
from guard.policy import highest_risk, inspect_input, load_rules
from providers.model import default_model

STAGES = ("input_guardrail", "dialogue_rail", "model", "classifier", "output_guardrail")


class Pipeline:
    def __init__(self, model: Callable[[str], str] | None = None, classifier: Callable | None = None,
                 rail: Callable | None = None, rules=None):
        self.model = model or default_model()
        self.classifier = classifier
        self.rail = rail
        self.rules = rules if rules is not None else load_rules()
        try:
            self._model_takes_history = "history" in inspect.signature(self.model).parameters
        except (TypeError, ValueError):
            self._model_takes_history = False

    @property
    def model_name(self) -> str:
        return getattr(self.model, "model_name", "deterministic-fixture")

    def run(self, prompt: str, history=None) -> RunRecord:
        spans: list[Span] = []

        def span(stage, outcome, t):
            spans.append(Span(stage, outcome, round((time.perf_counter() - t) * 1000, 3)))

        trace_id = f"trace-{uuid4().hex[:12]}"

        t = time.perf_counter()
        matches = tuple(inspect_input(prompt, self.rules)) if prompt.strip() else ()
        empty = not prompt.strip()
        span("input_guardrail", "block" if any(m.decision is Decision.BLOCK for m in matches) or empty else "review" if matches else "allow", t)
        if empty:
            return RunRecord(trace_id, prompt, "입력이 비어 있어 모델을 호출하지 않았습니다.", Decision.BLOCK, RiskLevel.LOW, "empty_input", spans=spans)
        blocking = tuple(m for m in matches if m.decision is Decision.BLOCK)
        if blocking:
            return RunRecord(trace_id, prompt, "요청이 보안 정책에 의해 차단되었습니다.", Decision.BLOCK,
                             highest_risk(blocking), blocking[0].reason, blocking, spans=spans)
        # review-only matches: the request proceeds but the outcome can never be a clean allow
        input_review = matches[0] if matches else None

        # dialogue rail gates the prompt before the model is called (saves LLM cost on off-topic input)
        rail_verdict = None
        if self.rail is not None:
            t = time.perf_counter()
            try:
                rail_verdict = self.rail(prompt, None)
            except Exception as exc:  # provider failure must not bypass the guardrail
                rail_verdict = {"on_topic": False, "category": "provider_error", "raw": str(exc)}
            span("dialogue_rail", "on_topic" if rail_verdict.get("on_topic") else "off_topic", t)
            if not rail_verdict.get("on_topic"):
                return RunRecord(trace_id, prompt, "요청이 허용된 대화 주제 범위를 벗어났습니다.", Decision.REVIEW,
                                 RiskLevel.MEDIUM, rail_verdict.get("category") or "topic_violation",
                                 matches, spans=spans, rail=rail_verdict)

        t = time.perf_counter()
        if history and self._model_takes_history:
            response = self.model(prompt, history=history)
        elif history:
            ctx = "\n".join(f"{'사용자' if m.get('role') == 'user' else '봇'}: {m.get('content', '')}"
                           for m in history[-10:] if isinstance(m, dict))
            response = self.model(f"[이전 대화]\n{ctx}\n\n[현재 질문]\n{prompt}")
        else:
            response = self.model(prompt)
        span("model", "ok", t)

        verdict = None
        if self.classifier is not None:
            t = time.perf_counter()
            try:
                verdict = self.classifier(prompt, response)
            except Exception as exc:  # provider failure must not bypass the guardrail
                verdict = {"safe": False, "category": "provider_error", "raw": str(exc)}
            span("classifier", "safe" if verdict["safe"] else "unsafe", t)
            if not verdict["safe"]:
                return RunRecord(trace_id, prompt, "안전성 분류 결과가 unsafe입니다.", Decision.BLOCK, RiskLevel.CRITICAL,
                                 verdict.get("category") or "unsafe", matches, spans=spans, classifier=verdict)

        t = time.perf_counter()
        masked, fields, risk = redact(response)
        span("output_guardrail", "review" if fields else "allow", t)
        if fields:
            return RunRecord(trace_id, prompt, masked, Decision.REVIEW, risk, fields[0], matches, masked_fields=fields, spans=spans, classifier=verdict, rail=rail_verdict)
        if not response.strip():
            return RunRecord(trace_id, prompt, response, Decision.REVIEW, RiskLevel.LOW, "empty_response", matches, spans=spans, classifier=verdict, rail=rail_verdict)
        if input_review is not None:
            return RunRecord(trace_id, prompt, response, Decision.REVIEW, input_review.risk, input_review.reason,
                             matches, spans=spans, classifier=verdict, rail=rail_verdict)
        return RunRecord(trace_id, prompt, response, Decision.ALLOW, RiskLevel.LOW, "normal", matches, spans=spans, classifier=verdict, rail=rail_verdict)
