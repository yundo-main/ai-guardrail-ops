"""Runtime settings persistence via .env — survives server restarts.

POST /settings writes whitelisted vars to guardrail-ops/.env;
load_runtime() restores them into os.environ at startup.
Secrets (e.g. DEEPSEEK_API_KEY) belong here, not in runtime.json.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

KEYS = ("LLM_PROVIDER", "OLLAMA_MODEL", "OLLAMA_BASE_URL",
        "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "DEEPSEEK_BASE_URL")


def _parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def load_runtime(path: Path | None = None) -> dict:
    """Restore persisted .env settings into os.environ. Returns the loaded dict."""
    p = path or ENV_PATH
    data = {k: v for k, v in _parse_env(p).items() if k in KEYS}
    for key, val in data.items():
        os.environ[key] = val
    return data


def save_runtime(updates: dict, path: Path | None = None) -> None:
    """Merge whitelisted updates into .env, preserving other lines."""
    p = path or ENV_PATH
    updates = {k: str(v) for k, v in updates.items() if k in KEYS}
    if not updates:
        return
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    seen = set()
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.partition("=")[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
