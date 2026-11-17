import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

root = Path(__file__).parents[2]
db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
db_file.close()
os.environ["GUARDRAIL_DB_PATH"] = db_file.name
os.environ["GUARDRAIL_API_KEY"] = "test-key"
sys.path.insert(0, str(root / "05_security_dashboard_alerts" / "src"))

from api import app  # noqa: E402
import store  # noqa: E402


class SecurityApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        store.clear_events()

    def test_health_and_event_flow(self):
        self.assertEqual(self.client.get("/health").json()["status"], "ok")
        self.assertEqual(self.client.get("/metrics").status_code, 401)
        self.assertEqual(self.client.post("/guardrail/chat", json={"message": "hello"}).status_code, 401)
        response = self.client.post(
            "/events",
            json={
                "event_id": "api-1",
                "decision": "block",
                "risk": "Critical",
                "category": "prompt injection",
                "detail": "masked",
            },
            headers={"X-API-Key": "test-key"},
        )
        self.assertEqual(response.status_code, 201)
        headers = {"X-API-Key": "test-key"}
        self.assertEqual(self.client.get("/metrics", headers=headers).json()["blocked_events"], 1)
        self.assertEqual(len(self.client.get("/alerts/critical", headers=headers).json()), 1)
        acknowledged = self.client.post("/events/api-1/acknowledge", headers=headers)
        self.assertEqual(acknowledged.status_code, 200)
        self.assertEqual(acknowledged.json()["status"], "acknowledged")
        self.assertEqual(self.client.get("/metrics", headers=headers).json()["open_events"], 0)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)


if __name__ == "__main__":
    unittest.main()
