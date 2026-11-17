"""FastAPI service for the step 05 security dashboard backend."""

from __future__ import annotations

import os
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from event_model import SecurityEvent
from monitoring import critical_alert, dashboard_metrics
from policy import Decision, RiskLevel
import store

# 05/src/ 안에 번들된 로컬 guardrail_service를 사용한다.
# 외부 integration/ 폴더를 참조하지 않으므로 이 디렉터리만 복사해도 독립 실행이 가능하다.
from guardrail_service import GuardrailService, GuardrailServiceError


logger = logging.getLogger("guardrail.api")


class EventRequest(BaseModel):
    """Versioned JSON contract accepted by POST /events."""

    # API 요청을 명시적인 계약으로 받으면 잘못된 enum·길이·상태를 저장 전에 거부할 수 있다.
    schema_version: str = Field(default="1.0", min_length=1, max_length=16)
    event_id: str = Field(min_length=1, max_length=128)
    trace_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    decision: Decision
    risk: RiskLevel
    category: str = Field(min_length=1, max_length=128)
    detail: str = Field(default="", max_length=4000)
    timestamp: Optional[str] = None
    source_stage: str = Field(default="step04", min_length=1, max_length=64)
    policy_version: str = Field(default="policy-1", min_length=1, max_length=64)
    model_name: Optional[str] = Field(default=None, max_length=128)
    status: str = Field(default="open", pattern="^(open|acknowledged|closed)$")


class ChatRequest(BaseModel):
    """User message sent through the real Step 02 → Step 03 guardrail service."""

    message: str = Field(min_length=1, max_length=8000)
    conversation_id: Optional[str] = Field(default=None, max_length=128)


def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Protect non-health endpoints with a simple educational API key."""
    # 기본 키는 로컬 교육용일 뿐이며 공유 환경에서는 반드시 환경 변수로 교체한다.
    expected = os.getenv("GUARDRAIL_API_KEY", "dev-only-key")
    if x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")


app = FastAPI(
    title="AI Guardrail Security API",
    version="0.2.0",
    description="교육용 보안 이벤트·대시보드·Critical 알림 API",
)

store.initialize()
_guardrail_service: GuardrailService | None = None


@app.get("/health")
def health() -> dict[str, str]:
    """Expose a minimal unauthenticated liveness response."""
    return {"status": "ok", "storage": "sqlite"}


@app.post("/guardrail/chat", dependencies=[Depends(verify_api_key)])
def guardrail_chat(payload: ChatRequest) -> dict[str, object]:
    """Call the real guardrail chain and persist its normalized security event."""
    global _guardrail_service
    if _guardrail_service is None:
        try:
            _guardrail_service = GuardrailService()
        except Exception as exc:
            logger.exception("guardrail providers could not initialize")
            raise HTTPException(status_code=503, detail=f"guardrail providers unavailable: {exc}") from exc
    try:
        result = _guardrail_service.chat(payload.message)
    except GuardrailServiceError as exc:
        logger.exception("guardrail provider call failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    event = SecurityEvent(
        event_id=result["trace_id"],
        decision=Decision(result["decision"]),
        risk=RiskLevel(result["risk"]),
        category=str(result["category"]),
        detail=str(result["response"]),
        timestamp=str(result["timestamp"]),
        trace_id=str(result["trace_id"]),
        source_stage=str(result["source_stage"]),
        policy_version=str(result["policy_version"]),
        model_name="llama-guard-3 + nemo-guardrails",
    )
    store.save(event)
    result["event_id"] = event.event_id
    result["conversation_id"] = payload.conversation_id
    return result


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> str:
    """Serve the lightweight browser dashboard used in the lab."""
    path = Path(__file__).with_name("dashboard.html")
    return path.read_text(encoding="utf-8")


@app.post("/events", status_code=201, dependencies=[Depends(verify_api_key)])
def create_event(payload: EventRequest) -> dict[str, object]:
    """Validate, normalize, persist, and return one security event."""
    timestamp = payload.timestamp or datetime.now(timezone.utc).isoformat()
    event = SecurityEvent(
        event_id=payload.event_id,
        decision=payload.decision,
        risk=payload.risk,
        category=payload.category,
        detail=payload.detail,
        timestamp=timestamp,
        schema_version=payload.schema_version,
        trace_id=payload.trace_id or payload.event_id,
        source_stage=payload.source_stage,
        policy_version=payload.policy_version,
        model_name=payload.model_name,
        status=payload.status,
    )
    store.save(event)
    logger.info("security event stored", extra={"event_id": event.event_id, "risk": event.risk.value, "trace_id": event.trace_id})
    return asdict(event)


@app.get("/events", dependencies=[Depends(verify_api_key)])
def list_events() -> list[dict[str, object]]:
    """Return persisted events for the operator view."""
    return [asdict(event) for event in store.list_events()]


@app.get("/metrics", dependencies=[Depends(verify_api_key)])
def metrics() -> dict[str, object]:
    """Return aggregate data rather than exposing event detail to charts."""
    return dashboard_metrics(store.list_events())


@app.get("/alerts/critical", dependencies=[Depends(verify_api_key)])
def critical_alerts() -> list[dict[str, object]]:
    """Filter the persisted event stream down to urgent alert payloads."""
    return [alert for event in store.list_events() if (alert := critical_alert(event))]


@app.delete("/events", dependencies=[Depends(verify_api_key)])
def clear_events() -> dict[str, int]:
    deleted = store.clear_events()
    logger.warning("security event store cleared", extra={"deleted": deleted})
    return {"deleted": deleted}


@app.post("/events/{event_id}/acknowledge", dependencies=[Depends(verify_api_key)])
def acknowledge_event(event_id: str) -> dict[str, object]:
    """Record that an operator has accepted responsibility for an event."""
    event = store.acknowledge(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    logger.info("security event acknowledged", extra={"event_id": event_id, "trace_id": event.trace_id})
    return asdict(event)
