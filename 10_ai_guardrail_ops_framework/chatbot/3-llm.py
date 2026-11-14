"""3-llm.py

Gemini LLM 호출만 담당하는 단계.
4-1-rag.py 는 RAG 답변 생성에 이 파일을 쓰고,
5-agent.py 는 일반 답변 생성에 이 파일을 쓴다.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

# GEMINI_API_KEY 만 사용 (없으면 종료). 교육용으로 다른 프로바이더는 넣지 않음.
# .env 를 환경 변수로 올린다. 셸에 이미 있는 값이 우선하므로
# `RAG_MIN_SCORE=0.5 python <파일>` 같은 일회성 지정도 그대로 통한다.
#
# 0-env.py 도 숫자로 시작해 일반 import 가 안 된다. 다른 단계와 같은 방식으로 읽는다.
_env_spec = importlib.util.spec_from_file_location(
    "env", Path(__file__).with_name("0-env.py")
)
_env = importlib.util.module_from_spec(_env_spec)
_env_spec.loader.exec_module(_env)
_env.load_env()


API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# 답변 생성 모델
# gemini-2.0-flash 는 서비스 종료되어 404 를 반환한다(2026-09 확인).
# preview 가 아닌 GA 모델을 기본값으로 둔다.
# 더 최신 모델을 쓰려면 GEMINI_MODEL 환경 변수로 덮어쓴다(예: gemini-3.6-flash).
CHAT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# RAG 답변 생성 시 넣는 시스템 지시문
SYSTEM_INSTRUCTION = (
    "당신은 RAG 어시스턴트입니다. "
    "제공된 Context 범위 안에서만 한국어로 간결히 답합니다."
)


def require_gemini():
    """google.generativeai 로드 + API 키 설정.

    **합성 경로의 공용 진입점이다.** 4-1-rag.py 와 4-2-websearch.py 가 이 함수를
    호출해 genai 를 얻고, 그것을 2-embeddings.py 의 embed_text() 등에 넘긴다.

    2-embeddings.py 에도 같은 이름의 함수가 있으나 그쪽은 단독 실행 전용이다.
    """
    if not API_KEY:
        print(
            "GEMINI_API_KEY 가 필요합니다.\n"
            "  export GEMINI_API_KEY='your-key'",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        import google.generativeai as genai
    except ImportError:
        print(
            "패키지 필요: pip install google-generativeai",
            file=sys.stderr,
        )
        sys.exit(1)
    genai.configure(api_key=API_KEY)
    return genai


def generate_answer(genai, user_prompt: str) -> str:
    """Prompt → Gemini → 답변 문자열."""
    print(f"[6] LLM 호출 model={CHAT_MODEL}", flush=True)
    model = genai.GenerativeModel(
        model_name=CHAT_MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
    )
    # Context 를 근거로 답하는 작업이라 창의성이 필요 없다.
    # 0.2 로 두면 같은 질문에 표현이 조금씩 달라지고, 5-agent.py 의 2단계 판정이
    # 그 표현을 보고 판단하므로 결과가 갈릴 수 있다. 변동 폭을 줄이려고 0 으로 둔다.
    # (0 이어도 완전한 결정성은 보장되지 않는다. 폭이 줄어들 뿐이다.)
    response = model.generate_content(
        user_prompt,
        generation_config={"temperature": 0.0},
    )
    text = getattr(response, "text", None)
    if not text:
        return f"[Gemini] 빈 응답: {response!r}"
    return text.strip()


def generate_direct_answer(question: str) -> str:
    """문서 검색 없이 질문만으로 일반 답변을 생성한다."""
    genai = require_gemini()
    model = genai.GenerativeModel(
        model_name=CHAT_MODEL,
        system_instruction=(
            "당신은 간단한 학습용 에이전트입니다. "
            "도구 결과가 없을 때는 한국어로 짧고 분명하게 답하세요."
        ),
    )
    # 이쪽은 Context 없이 답하는 일반 질문이라 0.2 를 유지한다.
    # 판정 대상이 아니므로 표현이 달라져도 문제되지 않는다.
    response = model.generate_content(
        question,
        generation_config={"temperature": 0.2},
    )
    text = getattr(response, "text", None)
    if not text:
        return f"[Gemini] 빈 응답: {response!r}"
    return text.strip()

if __name__ == "__main__":
    # 단독 테스트 실행
    test_question = "파이썬에 대해 설명해 주세요."
    print(f"질문: {test_question}")
    answer = generate_direct_answer(test_question)
    print(f"답변:\n{answer}")