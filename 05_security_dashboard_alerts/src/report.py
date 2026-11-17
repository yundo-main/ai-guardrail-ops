"""Step 05: dashboard and alert payload helpers."""

from datetime import datetime, timezone

from monitoring import dashboard_metrics


def dashboard_payload(events):
    """Build the minimal payload consumed by a dashboard or alert worker."""
    # 지표와 Critical 필터를 하나의 외부 연동용 payload로 묶는다.
    # 웹 대시보드나 알림 워커가 Python 내부 객체를 알 필요 없도록 JSON 경계를 만든다.
    # 실제 운영에서는 이 payload를 인증된 API 응답이나 메시지 큐로 전달한다.
    metrics = dashboard_metrics(list(events))
    return {"dashboard": metrics, "alert_filter": {"risk": "Critical"}}


def period_report(events, period: str = "weekly"):
    """Create a report envelope that can be used for weekly or monthly review."""
    # 기간을 데이터와 함께 남겨 같은 지표를 주간·월간으로 비교할 수 있게 한다.
    # 허용 기간을 제한해야 서로 다른 리포트의 지표 정의가 흔들리지 않는다.
    if period not in {"weekly", "monthly"}:
        raise ValueError("period must be weekly or monthly")
    return {
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": dashboard_metrics(list(events)),
        "next_actions": [
            "Critical 이벤트의 담당자와 대응 기한을 확인",
            "반복 카테고리의 정책 오탐·미탐을 재평가",
        ],
    }
