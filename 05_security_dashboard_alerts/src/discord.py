"""Optional Discord webhook notifier for Critical security alerts.

이 모듈은 5단계 API의 알림 채널 중 하나로, 임계값 이상의 보안 이벤트를
Discord 채널 웹훅으로 전송한다. 외부 의존성 없이 stdlib(urllib)만 사용한다.

설정 방법:
    아래 ``WEBHOOK_URL`` 상수에 Discord 웹훅 URL을 붙여넣는다.
    비어 있으면 발송은 건너뛰는 no-op이므로 API는 그대로 동작한다.

안전 특성:
    - 발송은 ``notify_async()``가 데몬 스레드에서 수행 → 웹훅 지연·장애가
      API 응답 시간을 블록하지 않는다.
    - 네트워크 오류·웹훅 오류는 로그만 남기고 삼킨다 → 알림 실패가
      이벤트 등록 요청을 실패시키지 않는다.

주의:
    - 웹훅 URL은 "이 URL을 아는 누구나 해당 채널에 메시지를 보낼 수 있는"
      비밀값이다. 실습용으로 코드에 직접 넣는 방식을 택했으므로 실제 URL을
      커밋하기 전에 저장소 공개 여부를 확인한다.
"""

from __future__ import annotations

import json
import logging
import threading
import urllib.request
from typing import Any

# 로그 이름을 "guardrail.discord"로 고정해 api.py의 로깅 설정과 구분한다.
logger = logging.getLogger("guardrail.discord")

# Discord 웹훅 URL — 발급: 채널 설정 → 연동 → 웹후크 → 새 웹후크 → URL 복사.
# 비어 있으면 notify()가 즉시 False를 반환하는 no-op이 된다.
# git 추적 파일이므로 실제 운영 URL 커밋에 주의한다.
WEBHOOK_URL = ""

# 웹훅 응답 대기 상한(초). 초과 시 timeout 예외가 나고 notify()가 False를 반환한다.
_TIMEOUT = 10

# Discord embed 색상 — Critical(빨강 계열).
_EMBED_COLOR = 15158332


def _embed(alert: dict[str, Any]) -> dict[str, Any]:
    """알림 payload를 Discord embed 메시지 형식으로 변환한다.

    ``alert``는 monitoring.risk_alert()/critical_alert()가 만든 dict로,
    ``event`` 키에 SecurityEvent 직렬화 결과가 들어 있다. 필드 값이 없으면
    "—"로 표시하고, 상세는 Discord 필드 길이 제한(1024자)에 맞춰 자른다.
    """
    event = alert.get("event") or {}
    fields = [
        {"name": "이벤트 ID", "value": str(event.get("event_id", "—")), "inline": True},
        {"name": "추적 ID", "value": str(event.get("trace_id", "—")), "inline": True},
        {"name": "카테고리", "value": str(event.get("category", "—")), "inline": True},
        {"name": "상세", "value": str(event.get("detail", "—"))[:1024]},
    ]
    return {
        "username": "AI Guardrail 알림",
        "embeds": [
            {
                "title": str(alert.get("title", "AI 보안 Critical 이벤트")),
                "description": "Critical 위험 등급 보안 이벤트가 기록되었습니다.",
                "color": _EMBED_COLOR,
                "fields": fields,
                # footer로 발생 단계(step05)와 이벤트 시각을 함께 표시한다.
                "footer": {"text": f"step05 · {event.get('timestamp', '')}"},
            }
        ],
    }


def notify(alert: dict[str, Any]) -> bool:
    """``alert``를 설정된 Discord 웹훅으로 POST한다. 성공 시 True를 반환한다.

    - ``WEBHOOK_URL``이 비어 있으면 네트워크 호출 없이 False(no-op).
    - JSON 본문은 ``ensure_ascii=False``로 직렬화해 한글이 깨지지 않게 한다.
    - 모든 예외를 잡아 False로 변환한다 — 알림 실패가 API 요청을
      실패시키지 않도록 하는 것이 이 함수의 핵심 계약이다.
    """
    url = WEBHOOK_URL.strip()
    if not url:
        return False
    request = urllib.request.Request(
        url,
        data=json.dumps(_embed(alert), ensure_ascii=False).encode("utf-8"),
        # urllib 기본 UA(Python-urllib/x.x)는 Cloudflare에 차단되므로 명시한다.
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ai-guardrails-ops/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            # Discord 웹훅은 200/204 계열을 반환한다 — 2xx면 성공으로 본다.
            return 200 <= response.status < 300
    except Exception as exc:  # 네트워크·웹훅 오류가 API 요청을 실패시키지 않도록 삼킨다.
        logger.warning("discord webhook delivery failed: %s", exc)
        return False


def notify_async(alert: dict[str, Any]) -> None:
    """``alert``를 데몬 스레드에서 전송한다.

    api.py가 Critical 이벤트 등록 경로에서 호출한다. daemon=True라
    서버 종료 시 스레드가 강제 종료돼도 안전하고, 반환값을 기다리지
    않으므로 웹훅 응답 시간만큼 API 응답이 지연되지 않는다.
    """
    threading.Thread(target=notify, args=(alert,), daemon=True).start()
