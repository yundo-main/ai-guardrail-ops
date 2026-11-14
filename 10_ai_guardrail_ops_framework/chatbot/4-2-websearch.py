# 4-2-websearch.py
# =============================================================================
# 외부 웹 검색 단계 — 세 번째 지식 소스
#
# 지식 소스 계열:
#   3-llm.py         모델 파라미터 내부 지식 (학습 시점에 고정)
#   4-1-rag.py       로컬 문서 (1-documents.json, 직접 관리하는 고정 코퍼스)
#   4-2-websearch.py 외부 웹        <- 이 파일
#
# 데이터 흐름:
#   질문 → [모델이 검색과 답변 생성을 한 번에 수행] → 답변 + 근거 출처
#
# 4-1 과의 차이는 갱신 주기다. 1-documents.json 은 고정되어 있어 오늘 날씨나
# 현재 시세처럼 시점에 따라 달라지는 질문에 답할 수 없다. 이 단계가 그 빈자리를 메운다.
#
# Gemini 내장 검색(그라운딩)을 쓴다. GEMINI_API_KEY 하나로 동작하며
# 별도 검색 서비스 키가 필요 없다.
#
# 실행:
#   python 4-2-websearch.py
# =============================================================================

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List

try:
    from llm import CHAT_MODEL
except ModuleNotFoundError:
    module_path = Path(__file__).with_name("3-llm.py")
    spec = importlib.util.spec_from_file_location("llm", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러올 수 없습니다: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["llm"] = module
    spec.loader.exec_module(module)
    CHAT_MODEL = module.CHAT_MODEL

# .env 를 환경 변수로 올린다. 셸에 이미 있는 값이 우선한다.
#
# 0-env.py 도 숫자로 시작해 일반 import 가 안 된다. 다른 단계와 같은 방식으로 읽는다.
_env_spec = importlib.util.spec_from_file_location(
    "env", Path(__file__).with_name("0-env.py")
)
_env = importlib.util.module_from_spec(_env_spec)
_env_spec.loader.exec_module(_env)
_env.load_env()


MAX_RESULTS = 3          # 답변에 함께 보여줄 근거 출처 수
TITLE_MAX_CHARS = 120    # 출처 제목 길이 상한
ALLOWED_SCHEMES = ("http", "https")
HTTP_TIMEOUT = 10

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

# 제어문자(C0/C1)와 ANSI 이스케이프. 외부에서 온 제목에 섞여 있으면
# 터미널 출력과 로그가 깨진다.
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


@dataclass
class SearchResult:
    """근거 출처 1건."""

    title: str
    url: str


def clean(text: str, limit: int) -> str:
    """제어문자 제거 → 공백 정리 → 길이 상한."""
    text = ANSI_RE.sub("", str(text))
    text = "".join(
        c for c in text
        if c in "\n\t" or unicodedata.category(c) != "Cc"
    )
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "…(생략)"
    return text


def safe_url(url: str) -> str | None:
    """스킴을 확인한다. http/https 외에는 출처로 표시하지 않는다."""
    import urllib.parse

    cleaned = clean(url, 300)
    try:
        parsed = urllib.parse.urlparse(cleaned)
    except ValueError:
        return None
    if parsed.scheme.lower() not in ALLOWED_SCHEMES or not parsed.netloc:
        return None
    return cleaned


# ── Gemini 그라운딩 ───────────────────────────────────────────
#
# 4-1 과 구조가 다르다.
#   4-1  : 검색 결과를 받아 → 프롬프트 조립 → LLM 호출     (단계가 나뉨)
#   4-2  : 모델이 내부에서 검색과 답변 생성을 한 번에 수행   (한 호출)
#
# 그래서 중간 산출물(검색 결과 목록)이 없다. 대신 응답의 그라운딩 메타데이터에서
# 모델이 실제로 실행한 검색어와 근거 출처를 꺼내 [W1]~[W4] 로 보여준다.
#
# SDK 대신 REST 를 직접 호출하는 이유:
#   google-generativeai 0.8.6 은 google_search 도구를 요청에 싣지 못한다.
#   dict 로 넘기면 FunctionDeclaration 으로 오인해 거부하고, 프로토를 직접
#   넘기면 요청은 통과하지만 도구가 빠진 채 전송되어 검색이 수행되지 않는다.
#   (구형 도구 이름 google_search_retrieval 은 서버가 400 으로 거부한다.)
#   REST 로 보내면 정상 동작하며, urllib 만 쓰므로 새 의존성도 없다.


def _post_grounded(question: str) -> dict:
    """generateContent 를 google_search 도구와 함께 호출한다."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print(
            "GEMINI_API_KEY 가 필요합니다.\n"
            "  .env 에 넣거나 export GEMINI_API_KEY='your-key'",
            file=sys.stderr,
        )
        sys.exit(1)

    body = json.dumps(
        {
            "contents": [{"parts": [{"text": question}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.2},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{GEMINI_ENDPOINT}/{CHAT_MODEL}:generateContent",
        data=body,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 응답 본문에 키가 반사될 수 있으므로 상태코드만 남긴다.
        hint = " (키를 확인하세요)" if exc.code in (400, 401, 403) else ""
        raise RuntimeError(f"Gemini API 오류 (HTTP {exc.code}){hint}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini API 연결 실패: {exc.reason}") from None


def grounding_sources(payload: dict, max_results: int) -> List[SearchResult]:
    """응답에서 근거 출처를 꺼낸다.

    출처 URL 은 대부분 vertexaisearch.cloud.google.com 리다이렉트 형태로 온다.
    """
    candidates = payload.get("candidates") or [{}]
    chunks = candidates[0].get("groundingMetadata", {}).get("groundingChunks", [])
    sources: List[SearchResult] = []
    for chunk in chunks:
        web = chunk.get("web", {})
        url = safe_url(web.get("uri", ""))
        if url is None:
            continue
        sources.append(
            SearchResult(title=clean(web.get("title", ""), TITLE_MAX_CHARS), url=url)
        )
        if len(sources) >= max_results:
            break
    return sources


def run_websearch(question: str, max_results: int = MAX_RESULTS) -> str:
    """질문 → Gemini 내장 검색 → 답변."""
    print(f"[W1] 그라운딩 요청 model={CHAT_MODEL}", flush=True)
    payload = _post_grounded(question)

    candidates = payload.get("candidates") or [{}]
    meta = candidates[0].get("groundingMetadata", {})

    queries = meta.get("webSearchQueries", [])
    print(f"[W2] 모델이 실행한 검색어 {len(queries)}건", flush=True)
    for q in queries:
        print(f"  - {q!r}", flush=True)

    sources = grounding_sources(payload, max_results)
    print(f"[W3] 근거 출처 {len(sources)}건", flush=True)
    for r in sources:
        print(f"  + {r.url}  {r.title}", flush=True)
    if not sources:
        print(
            "  주의: 근거 출처가 비어 있다. 모델이 검색하지 않고 내부 지식으로 답했을 수 있다.",
            flush=True,
        )

    print("[W4] 답변 수신 (검색과 생성이 한 번의 호출에서 이뤄짐)", flush=True)
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    return text or f"[Gemini] 빈 응답: {payload!r}"


def main() -> None:
    print("=" * 60, flush=True)
    print("4-2 웹 검색 데모", flush=True)
    print("질문 → [모델 내부 검색 + 답변 생성] → 답변 + 근거 출처", flush=True)
    print("=" * 60, flush=True)

    question = "오늘 서울 날씨 어때?"
    print(f"[입력] {question}\n", flush=True)

    try:
        print(run_websearch(question), flush=True)
    except RuntimeError as exc:
        print(f"[오류] {exc}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
