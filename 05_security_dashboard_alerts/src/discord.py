"""Optional Discord webhook notifier for Critical security alerts.

Set ``DISCORD_WEBHOOK_URL`` to a Discord channel webhook to enable delivery.
When the variable is unset the notifier is a no-op, so the API keeps working
offline. Delivery failures are logged but never break request handling.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.request
from typing import Any

logger = logging.getLogger("guardrail.discord")

_TIMEOUT = 10


def _webhook_url() -> str:
    return os.getenv("DISCORD_WEBHOOK_URL", "").strip()


def _embed(alert: dict[str, Any]) -> dict[str, Any]:
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
                "color": 15158332,
                "fields": fields,
                "footer": {"text": f"step05 · {event.get('timestamp', '')}"},
            }
        ],
    }


def notify(alert: dict[str, Any]) -> bool:
    """POST ``alert`` to the configured Discord webhook. Returns True on success."""
    url = _webhook_url()
    if not url:
        return False
    request = urllib.request.Request(
        url,
        data=json.dumps(_embed(alert), ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            return 200 <= response.status < 300
    except Exception as exc:  # 네트워크·웹훅 오류가 API 요청을 실패시키지 않도록 삼킨다.
        logger.warning("discord webhook delivery failed: %s", exc)
        return False


def notify_async(alert: dict[str, Any]) -> None:
    """Deliver ``alert`` on a daemon thread so webhook latency never blocks the API."""
    threading.Thread(target=notify, args=(alert,), daemon=True).start()
