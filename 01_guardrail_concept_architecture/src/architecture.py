"""Day 1: describe and execute the smallest Guardrail pipeline.

The first lesson uses deterministic stand-ins. Later lessons can replace the
model and guardrail implementations while preserving this same sequence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class PipelineStage:
    """Describe one control point in the end-to-end AI request path."""
    # 한 단계의 이름과 책임을 데이터로 표현해 아키텍처를 재사용한다.
    # 문자열을 흩어 쓰지 않으면 슬라이드·문서·검사 코드가 같은 구조를 공유할 수 있다.
    name: str
    purpose: str
    control_point: str


 # 모델 호출 전·중·후와 관제 지점을 학습용 기본 흐름으로 정의한다.
DEFAULT_PIPELINE = (
    PipelineStage("input_guardrail", "입력 정책과 위험 요청 검사", "모델 호출 전"),
    PipelineStage("model", "허용된 요청 처리", "모델 호출"),
    PipelineStage("output_guardrail", "PII·비밀정보·유해 출력 검사", "모델 호출 후"),
    PipelineStage("monitoring", "이벤트 기록과 대응 연결", "항상"),
)


@dataclass(frozen=True)
class PipelineResult:
    """Serializable evidence produced by the Day 1 demonstration pipeline."""

    prompt: str
    model_response: str
    final_response: str
    decision: str
    stages: tuple[str, ...]


def run_pipeline(prompt: str, model: Callable[[str], str] | None = None) -> PipelineResult:
    """Run a deterministic input → model → output → monitoring exercise.

    The input and output controls are intentionally simple in Day 1. Their
    purpose is to make the insertion points executable before Day 2 replaces
    the model with Ollama/NeMo and adds the optional Llama Guard path.
    """
    stages = tuple(stage.name for stage in DEFAULT_PIPELINE)
    if not prompt.strip():
        return PipelineResult(prompt, "", "입력이 비어 있어 모델을 호출하지 않았습니다.", "block", stages)
    generate = model or (lambda text: f"더미 모델 응답: {text}")
    response = generate(prompt)
    if not response.strip():
        return PipelineResult(prompt, response, "모델 응답이 비어 있어 검토가 필요합니다.", "review", stages)
    return PipelineResult(prompt, response, response, "allow", stages)


def pipeline_summary(stages: tuple[PipelineStage, ...] = DEFAULT_PIPELINE) -> list[str]:
    """Convert structured stages into lines suitable for a lesson or checklist."""
    # 문서나 슬라이드에 바로 넣을 수 있는 한 줄 요약 목록을 만든다.
    # 실제 서비스에서는 이 결과를 아키텍처 검토 로그나 운영 체크리스트로도 사용할 수 있다.
    return [f"{stage.name}: {stage.control_point} — {stage.purpose}" for stage in stages]


if __name__ == "__main__":
    # 이 파일은 외부 서비스 없이 아키텍처의 최소 실행 결과만 확인하는 1단계 진입점이다.
    print("\n".join(pipeline_summary()))
    demo = run_pipeline("Guardrail의 기본 흐름을 설명해줘")
    print(f"\n실습 결과: decision={demo.decision} / response={demo.final_response}")
