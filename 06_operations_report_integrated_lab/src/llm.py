"""Optional local Ollama adapter used by the day 6 integration lab."""

from __future__ import annotations

import json
import os
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


def generate_response(prompt: str, model: str | None = None, base_url: str | None = None, timeout: int = 60) -> str | None:
    """Ask local Ollama and return only text that can enter the Guardrail layer.

    ``None`` is intentional: the caller can choose a deterministic fixture when
    LLM use is disabled or the local server is unavailable.
    """
    # USE_LLM=1 is an explicit opt-in so the default lab remains deterministic and offline.
    if os.getenv("USE_LLM", "0") != "1":
        # 명시적 opt-in 없이는 네트워크 호출을 하지 않아 기본 실습을 재현 가능하게 한다.
        return None

    # 모델과 주소를 환경 변수로 분리해 같은 코드를 여러 로컬 모델에 재사용한다.
    model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
    # stream=false로 받아 가드레일이 완성된 한 응답을 검사하도록 한다.
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    request = Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        # 외부 SaaS가 아니라 사용자가 지정한 로컬 Ollama 주소로만 요청한다.
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        # Ollama 응답 전체가 아니라 message.content만 다음 Guardrail에 전달한다.
        message = data.get("message", {})
        return message.get("content") or None
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        # 모델 서버가 꺼져 있어도 통합 실습 전체가 실패하지 않도록 호출 실패를 명시한다.
        return None
