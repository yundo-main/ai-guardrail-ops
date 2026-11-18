"""SQLite persistence for the step 05 security-event API."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path

from event_model import SecurityEvent
from policy import Decision, RiskLevel


# 05단계 폴더 루트(src/의 부모) — 다른 단계 폴더를 참조하지 않는다.
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "results" / "security_events.db"


def database_path() -> Path:
    """Return the configured database path and create its parent directory."""
    # 환경 변수로 테스트용 임시 DB와 운영용 DB를 분리할 수 있다.
    path = Path(os.environ.get("GUARDRAIL_DB_PATH", str(DEFAULT_DB_PATH)))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect() -> sqlite3.Connection:
    """Open a short-lived SQLite connection with row dictionaries enabled."""
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    return connection


def initialize() -> None:
    """Create the event table before the API serves requests."""
    # CREATE IF NOT EXISTS로 API 프로세스 재시작 때도 기존 데이터를 보존한다.
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS security_events (
                event_id TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                risk TEXT NOT NULL,
                category TEXT NOT NULL,
                detail TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source_stage TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                model_name TEXT,
                status TEXT NOT NULL,
                acknowledged_at TEXT
            )
            """
        )


def save(event: SecurityEvent) -> SecurityEvent:
    """Insert or replace one normalized event using its stable event ID."""
    # dataclass를 SQL named parameter로 변환하고 enum만 저장 가능한 문자열로 정규화한다.
    values = asdict(event)
    values["decision"] = event.decision.value
    values["risk"] = event.risk.value
    with connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO security_events
            (event_id, schema_version, trace_id, decision, risk, category, detail,
             timestamp, source_stage, policy_version, model_name, status, acknowledged_at)
            VALUES (:event_id, :schema_version, :trace_id, :decision, :risk, :category,
                    :detail, :timestamp, :source_stage, :policy_version, :model_name,
                    :status, :acknowledged_at)
            """,
            values,
        )
    return event


def _from_row(row: sqlite3.Row) -> SecurityEvent:
    return SecurityEvent(
        event_id=row["event_id"],
        decision=Decision(row["decision"]),
        risk=RiskLevel(row["risk"]),
        category=row["category"],
        detail=row["detail"],
        timestamp=row["timestamp"],
        schema_version=row["schema_version"],
        trace_id=row["trace_id"],
        source_stage=row["source_stage"],
        policy_version=row["policy_version"],
        model_name=row["model_name"],
        status=row["status"],
        acknowledged_at=row["acknowledged_at"],
    )


def list_events() -> list[SecurityEvent]:
    """Return events in newest-first order for API and dashboard consumers."""
    # 연결을 매번 닫아 교육용 단일 프로세스에서도 파일 잠금을 오래 유지하지 않는다.
    with connect() as connection:
        rows = connection.execute("SELECT * FROM security_events ORDER BY timestamp DESC").fetchall()
    return [_from_row(row) for row in rows]


def clear_events() -> int:
    """Delete all lab events and return the number removed."""
    with connect() as connection:
        count = connection.execute("SELECT COUNT(*) FROM security_events").fetchone()[0]
        connection.execute("DELETE FROM security_events")
    return int(count)


def acknowledge(event_id: str) -> SecurityEvent | None:
    """Mark one event as acknowledged and return the updated event."""
    # acknowledgement는 원본 이벤트를 삭제하지 않고 상태와 시각만 갱신한다.
    with connect() as connection:
        connection.execute(
            "UPDATE security_events SET status = ?, acknowledged_at = ? WHERE event_id = ?",
            ("acknowledged", datetime.now(timezone.utc).isoformat(), event_id),
        )
    return next((event for event in list_events() if event.event_id == event_id), None)
