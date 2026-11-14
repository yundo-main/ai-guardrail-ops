"""Day 2: compare safety classification and conversational policy adapters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailAdapter:
    """Describe one guardrail's boundary in the end-to-end request flow.

    The fields deliberately show both responsibility and handoff.  A learner
    should be able to answer not only “what is this tool?” but also “what data
    enters it, what comes out, and which layer makes the final decision?”.
    """
    # 기술별 목적과 적용 시점을 같은 필드로 비교하기 위한 구조다.
    # 이 비교 계층이 있어야 제품명을 외우는 데서 끝나지 않고 적용 책임을 설계할 수 있다.
    name: str
    purpose: str
    input_stage: str
    output: str
    receives: str
    produces: str
    handoff_to: str
    not_responsible_for: str


 # 두 기술을 같은 입력 단계에 놓지 않고 역할별로 구분한다.
ADAPTERS = (
    GuardrailAdapter(
        "Llama Guard",
        "위험 요청·응답의 안전성 범주 분류",
        "모델 호출 전·후",
        "안전성 범주·위험 신호",
        "프롬프트 또는 모델 응답",
        "분류 결과·위험 카테고리",
        "애플리케이션 정책 엔진",
        "최종 허용·차단·검토 결정",
    ),
    GuardrailAdapter(
        "NeMo Guardrails",
        "대화 주제·절차·응답 경로 제어",
        "대화 중",
        "정책에 맞는 대화 전환",
        "사용자 발화·대화 상태·허용 흐름",
        "허용 응답·주제 복귀·사람 검토 전환",
        "LLM 호출 또는 출력 Guardrail",
        "안전성 범주 분류 자체",
    ),
)


def compare_adapters() -> list[dict[str, str]]:
    """Return a JSON-friendly comparison without importing vendor SDKs.

    ``handoff_to`` is the key learning field: it makes the composition between
    a classifier, a conversation policy, and the application decision explicit.
    """
    # 표·슬라이드·리포트에서 쓰기 쉬운 dict 형태로 변환한다.
    # 실제 SDK 호출 대신 메타데이터를 먼저 검증해 정책 위치와 기대 결과를 합의한다.
    return [
        {
            "name": item.name,
            "purpose": item.purpose,
            "input_stage": item.input_stage,
            "output": item.output,
            "receives": item.receives,
            "produces": item.produces,
            "handoff_to": item.handoff_to,
            "not_responsible_for": item.not_responsible_for,
        }
        for item in ADAPTERS
    ]


if __name__ == "__main__":
    # 실제 모델 호출이 아니라 “어떤 책임을 어느 위치에 둘 것인가”를 먼저 검증한다.
    # 이 경계를 먼저 합의하면 이후 SDK를 교체해도 애플리케이션 정책이 흔들리지 않는다.
    for item in compare_adapters():
        print(
            f"{item['name']}: {item['purpose']} / "
            f"입력={item['receives']} / 출력={item['produces']} / "
            f"다음={item['handoff_to']}"
        )
