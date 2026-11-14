"""Input blocking and output redaction for day 3."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re

from policy import Decision, PolicyMatch, RiskLevel, highest_risk, inspect_input


@dataclass(frozen=True)
class GuardrailResult:
    """Carry a safe, serializable decision across input and output layers."""
    # 입력·출력 레이어가 공통으로 반환하는 판정 결과 객체다.
    decision: Decision
    text: str
    risk: RiskLevel
    matches: tuple[PolicyMatch, ...] = ()
    masked_fields: tuple[str, ...] = ()


 # 외부 전송 없이 로컬 정규식으로 민감정보를 먼저 마스킹한다.
OUTPUT_PATTERNS = (
    # 패턴은 탐지 필드명과 함께 관리해야 어떤 값이 가려졌는지 리포트할 수 있다.
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("api_key", re.compile(r"\b(?:sk|api)[-_][A-Za-z0-9_-]{12,}\b", re.I)),
    ("phone", re.compile(r"(?<!\d)(?:\+?\d{1,3}[ -]?)?\d{2,4}[ -]\d{3,4}[ -]\d{4}(?!\d)")),
    ("secret_keyword", re.compile(r"\b(?:password|secret|private key)\s*[:=]\s*\S+", re.I)),
)


def check_input(prompt: str) -> GuardrailResult:
    """Inspect a prompt before model execution and fail closed on a match."""
    # 모델을 호출하기 전에 위험 요청을 차단해 불필요한 처리를 막는다.
    # 모델에 전달되기 전 차단하면 위험한 요청이 도구·데이터·비용에 접근하는 것을 줄일 수 있다.
    matches = tuple(inspect_input(prompt))
    if matches:
        return GuardrailResult(Decision.BLOCK, "요청이 보안 정책에 의해 차단되었습니다.", highest_risk(list(matches)), matches)
    return GuardrailResult(Decision.ALLOW, prompt, RiskLevel.LOW)


def redact_output(response: str) -> GuardrailResult:
    """Mask known sensitive fields before the response crosses the user boundary."""
    # 모델 응답의 각 민감정보 패턴을 순서대로 치환한다.
    # 출력 검열은 모델이 안전하다고 가정하지 않고 최종 사용자에게 노출될 경계를 보호한다.
    masked = response
    fields: list[str] = []
    for field, pattern in OUTPUT_PATTERNS:
        masked, count = pattern.subn(f"[{field.upper()}_REDACTED]", masked)
        if count:
            fields.append(field)
    if not fields:
        return GuardrailResult(Decision.ALLOW, response, RiskLevel.LOW)
    # API 키·비밀값 노출은 즉시 대응이 필요하므로 Critical로 올린다.
    risk = RiskLevel.CRITICAL if "api_key" in fields or "secret_keyword" in fields else RiskLevel.HIGH
    return GuardrailResult(Decision.REVIEW, masked, risk, masked_fields=tuple(fields))


def safe_response(prompt: str, model_response: str) -> tuple[GuardrailResult, GuardrailResult]:
    """Apply input blocking first, then output redaction only for allowed prompts."""
    # 입력이 차단되면 모델 출력은 신뢰하지 않고 안전한 차단 결과를 반환한다.
    # 이 래퍼를 하나의 진입점으로 사용하면 실제 모델과 더미 모델에서 같은 방어 순서를 보장할 수 있다.
    input_result = check_input(prompt)
    if input_result.decision is Decision.BLOCK:
        return input_result, GuardrailResult(Decision.BLOCK, input_result.text, input_result.risk)
    return input_result, redact_output(model_response)


def result_payload(result: GuardrailResult, next_stage: str = "04_risk_rating_system") -> dict[str, object]:
    """Serialize a result for the next day's JSON-based exercise."""
    # 폴더별 코드는 독립적으로 유지하고, 단계 간에는 안정적인 JSON을 전달한다.
    # enum·dataclass는 그대로 JSON에 넣을 수 없으므로 경계에서 문자열·dict로 정규화한다.
    payload = asdict(result)
    payload["decision"] = result.decision.value
    payload["risk"] = result.risk.value
    payload["matches"] = [asdict(match) for match in result.matches]
    for match in payload["matches"]:
        match["decision"] = match["decision"].value
        match["risk"] = match["risk"].value
    payload["schema_version"] = "1.0"
    payload["event_id"] = "step03-guardrail-result"
    payload["trace_id"] = "step03-guardrail-result"
    payload["source_stage"] = "step03"
    payload["next"] = next_stage
    return payload


def write_result(result: GuardrailResult, path: str | Path) -> None:
    """Write a redacted result artifact for the next day's exercise."""
    # 결과 파일에는 모델 원문 대신 정책 판정과 마스킹된 값만 남긴다.
    # 이 파일이 4단계의 입력이 되므로 경로와 필드 변경은 문서와 함께 관리한다.
    output_path = Path(path)
    # 부모 폴더를 먼저 만들면 새 실습 환경에서도 결과 저장이 실패하지 않는다.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result_payload(result), ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    # 파일을 직접 실행했을 때도 학습자가 입력 차단과 출력 마스킹을 한 번에 확인하도록 한다.
    # 실제 모델 호출은 포함하지 않고, 안전한 더미 응답만 사용해 재현 가능한 결과를 만든다.
    project_root = Path(__file__).resolve().parents[2]
    result_path = project_root / "99_ref" / "results" / "step03-guardrail-result.json"
    input_result, output_result = safe_response(
        "What is the support contact?",
        "Contact learner@example.invalid; api_key=sk_demo_1234567890.",
    )
    result = output_result if input_result.decision is Decision.ALLOW else input_result
    write_result(result, result_path)
    print(json.dumps(result_payload(result), ensure_ascii=False, indent=2))
