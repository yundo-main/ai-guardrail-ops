"""SQLite event store (step05 capability). Path via GUARDRAIL_OPS_DB or constructor."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3

from core.types import Decision, RiskLevel, SecurityEvent

DEFAULT_DB = Path(__file__).resolve().parents[2] / "results" / "events.db"
COLUMNS = ("event_id", "trace_id", "decision", "risk", "category", "detail", "timestamp", "schema_version",
           "source_stage", "policy_version", "model_name", "status", "acknowledged_at", "spans_json")


class EventStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv("GUARDRAIL_OPS_DB", str(DEFAULT_DB)))
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, decision TEXT NOT NULL,"
            " risk TEXT NOT NULL, category TEXT NOT NULL, detail TEXT NOT NULL, timestamp TEXT NOT NULL,"
            " schema_version TEXT NOT NULL, source_stage TEXT NOT NULL, policy_version TEXT NOT NULL,"
            " model_name TEXT, status TEXT NOT NULL, acknowledged_at TEXT, spans_json TEXT)"
        )
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(events)")}
        if "spans_json" not in cols:
            self._conn.execute("ALTER TABLE events ADD COLUMN spans_json TEXT")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL,"
            " field TEXT NOT NULL, old_value TEXT, new_value TEXT, actor TEXT, reason TEXT, timestamp TEXT NOT NULL)"
        )

    def save(self, event: SecurityEvent) -> SecurityEvent:
        data = event.as_dict()
        with self._conn:
            self._conn.execute(
                f"INSERT OR REPLACE INTO events ({','.join(COLUMNS)}) VALUES ({','.join(':' + c for c in COLUMNS)})", data)
        if event.risk is RiskLevel.CRITICAL and str(self.path) != ":memory:":
            with open(self.path.parent / "alerts.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(event.as_dict(), ensure_ascii=False) + "\n")
        return event

    def list(self) -> list[SecurityEvent]:
        rows = self._conn.execute("SELECT * FROM events ORDER BY timestamp DESC").fetchall()
        return [SecurityEvent(**{**dict(r), "decision": Decision(r["decision"]), "risk": RiskLevel(r["risk"]),
                                 "spans_json": r["spans_json"] or ""}) for r in rows]

    def _audit(self, event_id: str, field: str, old, new, actor: str | None, reason: str | None) -> None:
        """Step04 rule: grade/status changes never overwrite silently — actor, time, reason are recorded apart."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO audit (event_id, field, old_value, new_value, actor, reason, timestamp)"
                " VALUES (?,?,?,?,?,?,?)",
                (event_id, field, str(old), str(new), actor, reason,
                 datetime.now(timezone.utc).isoformat()))

    def acknowledge(self, event_id: str, actor: str | None = None, reason: str | None = None) -> SecurityEvent | None:
        event = next((e for e in self.list() if e.event_id == event_id), None)
        if event is None:
            return None
        with self._conn:
            self._conn.execute("UPDATE events SET status='acknowledged', acknowledged_at=? WHERE event_id=?",
                               (datetime.now(timezone.utc).isoformat(), event_id))
        self._audit(event_id, "status", event.status, "acknowledged", actor, reason)
        return next((e for e in self.list() if e.event_id == event_id), None)

    def audit_trail(self, event_id: str | None = None) -> list[dict]:
        sql = "SELECT * FROM audit" + (" WHERE event_id=?" if event_id else "") + " ORDER BY id"
        rows = self._conn.execute(sql, (event_id,) if event_id else ()).fetchall()
        return [dict(r) for r in rows]

    def clear(self) -> int:
        with self._conn:
            return self._conn.execute("DELETE FROM events").rowcount

    def close(self) -> None:
        self._conn.close()
