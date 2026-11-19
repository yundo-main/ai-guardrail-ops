"""Guardrail ops HTTP server (stdlib only): JSON API + single-page GUI."""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import sys
import threading
import time

_OPS_SRC = Path(__file__).resolve().parents[1]
_ROOT = _OPS_SRC.parent.parent
sys.path.insert(0, str(_ROOT / "guardrail" / "src"))
sys.path.insert(0, str(_OPS_SRC))

from core.pipeline import Pipeline  # noqa: E402
from observe.metrics import metrics  # noqa: E402
from observe.report import period_report  # noqa: E402
from observe.runtime import load_runtime, save_runtime  # noqa: E402
from observe.store import EventStore  # noqa: E402
from risk.classify import to_event  # noqa: E402
from serve.page import CHAT_PAGE, LANDING_PAGE, PAGE  # noqa: E402

MAX_BODY = 1_000_000          # 1 MB request body cap
CHECK_RATE_LIMIT = 30         # POST /v1/check per client per window
RATE_WINDOW = 60.0            # seconds
ALERT_TAIL = 50
REPO_ROOT = _ROOT.parent  # ai-guardrails-ops/ — step folders live here
RUN_TIMEOUT = 30
# /run-step whitelist: fixed commands only, no user-supplied shell input
STEP_COMMANDS = {
    "01": "python 01_guardrail_concept_architecture/src/architecture.py",
    "02": "python 02_llama_guard_nemo_guardrails/src/main.py",
    "03": "python 03_policy_blocking_output_filtering/src/guardrail.py",
    "04": "PYTHONPATH=04_risk_rating_system/src python 04_risk_rating_system/src/risk.py",
    "05": "python -m pip install -q -r 05_security_dashboard_alerts/requirements.txt && uvicorn api:app --app-dir 05_security_dashboard_alerts/src --port 8001",
    "06": "python 06_operations_report_integrated_lab/src/app.py",
}

OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "AI Guardrail Ops", "version": "1.1"},
    "paths": {
        "/": {"get": {"summary": "GUI (single-page app)"}},
        "/health": {"get": {"summary": "liveness probe"}},
        "/v1/check": {"post": {"summary": "run prompt through the guardrail pipeline",
                               "requestBody": {"content": {"application/json": {"schema": {
                                   "type": "object", "properties": {"prompt": {"type": "string"},
                                       "history": {"type": "array", "description": "prior turns [{role: user|assistant, content}]"}}, "required": ["prompt"]}}}}}},
        "/metrics": {"get": {"summary": "aggregate metrics"}},
        "/events": {"get": {"summary": "stored security events (newest first)"}},
        "/alerts": {"get": {"summary": "recent critical alerts (jsonl tail)"}},
        "/audit": {"get": {"summary": "grade/status change audit trail", "parameters": [
            {"name": "event_id", "in": "query", "schema": {"type": "string"}}]}},
        "/llm": {"get": {"summary": "LLM/Ollama connection status + installed models"}},
        "/settings": {"post": {"summary": "update LLM settings (use_llm, model, base_url); pipeline rebuilt", "requestBody": {"content": {
            "application/json": {"schema": {"type": "object", "properties": {
                "use_llm": {"type": "boolean"}, "provider": {"type": "string", "enum": ["ollama", "deepseek", "dummy"]},
                "model": {"type": "string"}, "base_url": {"type": "string"},
                "api_key": {"type": "string"}, "deepseek_model": {"type": "string"},
                "deepseek_base_url": {"type": "string"}}}}}}}},
        "/policy": {"get": {"summary": "active input policy rules + output masking patterns + raw config"},
                    "post": {"summary": "replace policy-rules.json (validated before save)", "requestBody": {"content": {
                        "application/json": {"schema": {"type": "object", "properties": {
                            "config": {"description": "rule array (object or JSON string)"}}}}}}}},
        "/report": {"get": {"summary": "weekly|monthly ops report", "parameters": [
            {"name": "period", "in": "query", "schema": {"enum": ["weekly", "monthly"], "default": "weekly"}}]}},
        "/ack": {"post": {"summary": "acknowledge an event (actor/reason recorded in audit trail)", "requestBody": {"content": {"application/json": {
            "schema": {"type": "object", "properties": {"event_id": {"type": "string"},
                        "actor": {"type": "string"}, "reason": {"type": "string"}}, "required": ["event_id"]}}}}}},
        "/run-step": {"post": {"summary": "run a whitelisted step practice command (01-06)", "requestBody": {"content": {
            "application/json": {"schema": {"type": "object", "properties": {"step": {"type": "string", "enum": ["01","02","03","04","05","06"]}}, "required": ["step"]}}}}}},
        "/clear": {"post": {"summary": "delete all events (requires {\"confirm\": true})"}},
    },
}


def run_server(host: str = "127.0.0.1", port: int = 8000, db: str | None = None,
               classifier: bool = False, rail: str | None = None) -> int:
    load_runtime()
    clf = None
    if classifier:
        from providers.classifier import LlamaGuardClassifier
        clf = LlamaGuardClassifier()
    from providers.dialogue import build_rail
    rail_obj = build_rail(rail)
    pipeline = Pipeline(classifier=clf, rail=rail_obj)

    def rebuild_pipeline():
        nonlocal pipeline
        pipeline = Pipeline(classifier=clf, rail=rail_obj)
    store = EventStore(db)
    lock = threading.Lock()  # sqlite3 connection is shared across request threads
    hits: dict[str, deque] = defaultdict(deque)

    def rate_limited(ip: str) -> bool:
        q = hits[ip]
        now = time.monotonic()
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= CHECK_RATE_LIMIT:
            return True
        q.append(now)
        return False

    class Handler(BaseHTTPRequestHandler):
        server_version = "GuardrailOps/1.1"

        def _json(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def _html(self, html):
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None
            if n > MAX_BODY:
                self._json(413, {"error": "request body too large"})
                return False
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return None

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/health":
                return self._json(200, {"status": "ok"})
            if path in ("/ops", "/ui", "/index.html", "/guardrail"):
                return self._html(PAGE)
            if path in ("/chat", "/chatbot"):
                return self._html(CHAT_PAGE)
            if path == "/":
                return self._html(LANDING_PAGE)
            if path.startswith("/diagrams/"):
                name = path.rsplit("/", 1)[-1]
                if name not in ("flow-01-service-pipeline.svg", "flow-02-pipeline.svg", "flow-03-service.svg"):
                    return self._json(404, {"error": "not found"})
                f = _ROOT / "docs" / "diagrams" / name
                if not f.exists():
                    return self._json(404, {"error": "not found"})
                body = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return self.wfile.write(body)
            if path == "/editor-test":
                return self._json(404, {"error": "not found"})
            if path == "/openapi.json":
                return self._json(200, OPENAPI)
            if path == "/metrics":
                with lock:
                    return self._json(200, metrics(store.list()))
            if path == "/events":
                with lock:
                    return self._json(200, [e.as_dict() for e in store.list()])
            if path == "/alerts":
                f = store.path.parent / "alerts.jsonl"
                if str(store.path) == ":memory:" or not f.exists():
                    return self._json(200, [])
                lines = f.read_text(encoding="utf-8").splitlines()[-ALERT_TAIL:]
                return self._json(200, [json.loads(l) for l in lines if l.strip()])
            if path == "/audit":
                event_id = parse_qs(urlsplit(self.path).query).get("event_id", [None])[0]
                with lock:
                    return self._json(200, store.audit_trail(event_id))
            if path == "/llm":
                import os
                from urllib.request import urlopen
                provider = os.getenv("LLM_PROVIDER", "ollama")
                base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
                info = {"use_llm": os.getenv("USE_LLM", "1") != "0",
                        "provider": provider,
                        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
                        "base_url": base,
                        "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                        "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                        "deepseek_key_set": bool(os.getenv("DEEPSEEK_API_KEY")),
                        "classifier": bool(clf), "rail": rail}
                try:
                    with urlopen(f"{base}/api/tags", timeout=3) as r:
                        tags = json.loads(r.read().decode())
                    info["ollama"] = {"reachable": True,
                                      "installed_models": [m["name"] for m in tags.get("models", [])]}
                except Exception:
                    info["ollama"] = {"reachable": False, "installed_models": []}
                info["reachable"] = (info["ollama"]["reachable"] if provider == "ollama"
                                     else info["deepseek_key_set"] if provider == "deepseek"
                                     else True)
                return self._json(200, info)
            if path == "/policy":
                import guard.output as gout
                from guard.policy import DEFAULT_RULES_PATH
                rules = [{"rule_id": rid, "pattern": pat.pattern, "reason": reason,
                          "risk": risk.value, "decision": dec.value, "normalize": norm}
                         for rid, pat, reason, risk, dec, norm in pipeline.rules]
                return self._json(200, {
                    "config": json.loads(DEFAULT_RULES_PATH.read_text(encoding="utf-8")),
                    "config_path": str(DEFAULT_RULES_PATH),
                    "masking_config": json.loads(gout.PATTERNS_PATH.read_text(encoding="utf-8")),
                    "masking_path": str(gout.PATTERNS_PATH),
                    "input_rules": rules,
                    "output_masking": [{"field": name, "pattern": pat.pattern} for name, pat in gout.OUTPUT_PATTERNS],
                })
            if path == "/report":
                period = parse_qs(urlsplit(self.path).query).get("period", ["weekly"])[0]
                with lock:
                    try:
                        return self._json(200, period_report(store.list(), period))
                    except ValueError as exc:
                        return self._json(400, {"error": str(exc)})
            self._json(404, {"error": "not found"})

        def do_POST(self):
            path = urlsplit(self.path).path
            if path == "/v1/check" or path == "/check":
                if rate_limited(self.client_address[0]):
                    return self._json(429, {"error": "rate limit exceeded"})
            body = self._body()
            if body is False:
                return
            if body is None:
                return self._json(400, {"error": "invalid json"})
            if path in ("/check", "/v1/check"):
                history = body.get("history")
                if history is not None and not isinstance(history, list):
                    return self._json(400, {"error": "history must be a list"})
                if isinstance(history, list) and len(history) > 20:
                    history = history[-20:]
                with lock:
                    record = pipeline.run(str(body.get("prompt", "")), history=history)
                    event = store.save(to_event(record, pipeline.model_name))
                out = record.as_dict()
                out["event_id"] = event.event_id
                return self._json(200, out)
            if path == "/ack":
                with lock:
                    event = store.acknowledge(str(body.get("event_id", "")),
                                              actor=body.get("actor"), reason=body.get("reason"))
                return self._json(200 if event else 404, event.as_dict() if event else {"error": "not found"})
            if path == "/settings":
                import os
                updates = {}
                if "use_llm" in body:
                    updates["USE_LLM"] = "0" if body["use_llm"] in (False, "0", 0) else "1"
                if body.get("provider") in ("ollama", "deepseek", "dummy"):
                    updates["LLM_PROVIDER"] = body["provider"]
                if body.get("model"):
                    updates["OLLAMA_MODEL"] = str(body["model"])
                if body.get("base_url"):
                    updates["OLLAMA_BASE_URL"] = str(body["base_url"]).rstrip("/")
                if body.get("api_key"):
                    updates["DEEPSEEK_API_KEY"] = str(body["api_key"])
                if body.get("deepseek_model"):
                    updates["DEEPSEEK_MODEL"] = str(body["deepseek_model"])
                if body.get("deepseek_base_url"):
                    updates["DEEPSEEK_BASE_URL"] = str(body["deepseek_base_url"]).rstrip("/")
                for k, v in updates.items():
                    os.environ[k] = v
                if updates:
                    save_runtime(updates)
                with lock:
                    rebuild_pipeline()
                return self._json(200, {"saved": True, "use_llm": os.getenv("USE_LLM", "1") != "0",
                                        "provider": os.getenv("LLM_PROVIDER", "ollama"),
                                        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
                                        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")})
            if path == "/policy":
                saved = []
                # --- masking patterns ---
                if "masking" in body:
                    import guard.output as gout
                    from guard.output import load_patterns
                    raw = body["masking"]
                    text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
                    try:
                        entries = json.loads(text)
                        assert isinstance(entries, list)
                    except (ValueError, AssertionError) as exc:
                        return self._json(400, {"error": f"invalid masking json: {exc}"})
                    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
                        tmp.write(text)
                        tmp_path = tmp.name
                    try:
                        load_patterns(tmp_path)
                    except Exception as exc:
                        return self._json(400, {"error": f"masking validation failed: {exc}"})
                    finally:
                        Path(tmp_path).unlink(missing_ok=True)
                    gout.PATTERNS_PATH.write_text(text, encoding="utf-8")
                    with lock:
                        gout.OUTPUT_PATTERNS = load_patterns()
                    saved.append("masking")
                # --- input rules ---
                raw = body.get("config", body.get("rules"))
                if raw is not None:
                    from guard.policy import DEFAULT_RULES_PATH, load_rules
                    text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
                    try:
                        entries = json.loads(text)
                        assert isinstance(entries, list) and entries
                    except (ValueError, AssertionError) as exc:
                        return self._json(400, {"error": f"invalid policy json: {exc}"})
                    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
                        tmp.write(text if isinstance(text, str) else json.dumps(entries, ensure_ascii=False))
                        tmp_path = tmp.name
                    try:
                        load_rules(tmp_path)  # raises on bad rule -> nothing is written
                    except Exception as exc:
                        return self._json(400, {"error": f"policy validation failed: {exc}"})
                    finally:
                        Path(tmp_path).unlink(missing_ok=True)
                    DEFAULT_RULES_PATH.write_text(
                        text if isinstance(text, str) else json.dumps(entries, ensure_ascii=False, indent=2),
                        encoding="utf-8")
                    with lock:
                        pipeline.rules = load_rules()
                    saved.append(f"rules({len(pipeline.rules)})")
                if not saved:
                    return self._json(400, {"error": "nothing to save (config/rules/masking required)"})
                return self._json(200, {"saved": True, "updated": saved})
            if path == "/run-step":
                step = str(body.get("step", ""))
                cmd = STEP_COMMANDS.get(step)
                if not cmd:
                    return self._json(400, {"error": f"unknown step: {step}"})
                try:
                    r = subprocess.run(cmd, shell=True, cwd=REPO_ROOT,
                                       capture_output=True, text=True, timeout=RUN_TIMEOUT)
                    out = (r.stdout + r.stderr).strip()
                    return self._json(200, {"step": step, "code": r.returncode,
                                            "output": out[:8000] or "(출력 없음)"})
                except subprocess.TimeoutExpired as exc:
                    out = ((exc.stdout or b"") + (exc.stderr or b""))
                    if isinstance(out, bytes):
                        out = out.decode("utf-8", "replace")
                    return self._json(200, {"step": step, "code": -1, "timeout": True,
                                            "output": (out.strip() or "(시간 초과)")[:8000] + "\n… (30초 초과 — 서버형 명령은 부분 출력만 표시)"})
            if path == "/clear":
                if body.get("confirm") is not True:
                    return self._json(400, {"error": "requires {\"confirm\": true}"})
                with lock:
                    return self._json(200, {"removed": store.clear()})
            self._json(404, {"error": "not found"})

        def log_message(self, fmt, *a):
            sys.stderr.write(f"{self.address_string()} - {fmt % a}\n")

    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"guardrail framework on http://{host}:{port} (db={store.path})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        store.close()
    return 0
