"""Step 04: deterministic risk rating helper for security events."""

from __future__ import annotations

import json
from pathlib import Path

from monitoring import event_payload, make_event
from policy import Decision
from policy import RiskLevel


def classify_risk(impact: int, exploitability: int, exposure: int) -> RiskLevel:
    """Classify a 0-3 score using impact, exploitability, and exposure."""
    # 세 축을 합산하되 입력값이 범위를 벗어나도 0~9로 제한한다.
    # 입력 정규화는 잘못된 점수 하나가 관제 우선순위를 비정상적으로 바꾸는 것을 막는다.
    # 세 점수는 각각 0~3을 기대하지만, 교육용 함수는 비정상 입력도 보수적으로 정규화한다.
    score = max(0, min(9, impact + exploitability + exposure))
    # 임계값은 교육용 기준이며 실제 서비스에서는 조직 정책으로 조정한다.
    # 등급을 코드로 고정해 사람이 임의로 판단하는 편차를 줄이는 것이 이 함수의 목적이다.
    if score >= 8:
        return RiskLevel.CRITICAL
    if score >= 6:
        return RiskLevel.HIGH
    if score >= 3:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def event_from_guardrail_file(path: str | Path):
    """Convert a step 03 JSON result into a step 04 security event."""
    # 파일 경계에서만 연결하므로 3단계 코드를 import하지 않아도 독립 실행이 가능하다.
    # 즉, 각 단계 소스의 중복을 허용하면서도 결과 파일로 학습 흐름을 이어 간다.
    source_path = Path(path)
    # 파일을 경계로 읽기 때문에 4단계는 3단계 Python 모듈을 import하지 않는다.
    data = json.loads(source_path.read_text(encoding="utf-8"))
    return make_event(
        event_id=data.get("event_id", "step03-result"),
        decision=Decision(data["decision"]),
        risk=RiskLevel(data["risk"]),
        category=data.get("category", "guardrail"),
        detail=data.get("detail", data.get("category", "")),
        trace_id=data.get("trace_id", data.get("event_id", "step03-result")),
    )


def write_event_result(event, path: str | Path) -> None:
    # 5단계 API가 그대로 받을 수 있는 JSON 형태로 저장한다.
    # API의 EventRequest와 필드 이름을 맞추는 것이 이 함수의 계약이다.
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(event_payload(event), ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    # 3단계 결과가 있으면 실제 파일을 읽어 4단계 이벤트로 변환한다.
    # 파일이 없을 때도 점수 기반 예제를 출력해 4단계 함수 자체를 독립 실행할 수 있게 한다.
    repo_root = Path(__file__).resolve().parents[2]
    stage_dir = Path(__file__).resolve().parents[1]
    source_path = repo_root / "03_policy_blocking_output_filtering" / "results" / "step03-guardrail-result.json"
    target_path = stage_dir / "results" / "step04-security-event.json"
    if source_path.exists():
        event = event_from_guardrail_file(source_path)
        write_event_result(event, target_path)
        # report.py는 __main__ 실행 시에만 필요하므로 지연 import로 테스트 격리 로드를 유지한다.
        from report import write_report

        write_report(event_payload(event), target_path.with_suffix(".html"))
        print(json.dumps(event_payload(event), ensure_ascii=False, indent=2))
    else:
        print(classify_risk(3, 3, 3).value)
