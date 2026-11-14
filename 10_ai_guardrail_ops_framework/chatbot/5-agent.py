# 5-agent.py
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Callable

BASE_DIR = Path(__file__).resolve().parent

# 로컬 문서 검색의 최고 유사도가 이 값보다 낮으면, 문서로 답변을 만들어 보지 않고
# 곧장 웹 검색으로 넘긴다.
#
# 이 값은 정확도가 아니라 비용을 조절한다.
# 정확도 판정은 2단계(답변 내용 확인)가 맡는다. 1단계는 명백히 무관한 질문에서
# 생성 호출 1회를 아끼려고 있는 것이고, 없애도 최종 결과는 같다.
#
# 그래서 오류 방향이 비대칭이다.
#   기준이 낮으면  → 답변을 만들어 보고 2단계가 걸러낸다. 생성 1회 낭비로 끝난다.
#   기준이 높으면  → 답변을 만들어 보지 않으므로 2단계가 개입할 수 없다.
#                    문서로 답할 수 있었던 질문이 조용히 웹으로 샌다. 복구 불가다.
#
# 따라서 낮은 쪽으로 잡는다. "답할 수 있는 질문을 절대 거르지 않을 만큼 낮게,
# 명백한 쓰레기는 걸러낼 만큼만 높게" 가 기준이다.
#
# 0.65 는 그 원칙에 따른 잠정값이다. 현재 코퍼스(12건)와 gemini-embedding-001 실측값에서
#   문서가 답할 수 있는 질문   0.722 ~ 0.805
#   문서와 무관한 질문         0.611 ~ 0.658
# 무관 구간의 최고값 바로 위에 둔 것이다. 표본이 작아 정밀한 값은 아니며, 정밀할 필요도 없다.
#
# 실행 로그에 실제 점수가 찍히므로 그 값을 보고 조정한다.
#   RAG_MIN_SCORE=0.5 python 5-agent.py
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


RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.65"))


def load_module(module_name: str, file_name: str):
    """번호가 붙은 예제 파일을 경로로 직접 로드한다."""
    module_path = BASE_DIR / file_name
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러올 수 없습니다: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# 이 예제 폴더는 단계별 파일명 앞에 번호가 붙어 있어서
# 일반적인 import 문으로는 바로 불러오기 어렵다.
# 그래서 경로를 직접 지정해 1~3단계 모듈을 읽어온다.
DOCUMENTS = load_module("documents_demo", "1-documents.py")
sys.modules.setdefault("documents", DOCUMENTS)
EMBEDDINGS = load_module("embeddings_demo", "2-embeddings.py")
sys.modules.setdefault("embeddings", EMBEDDINGS)
LLM = load_module("llm_demo", "3-llm.py")
sys.modules.setdefault("llm", LLM)
RAG = load_module("rag_demo", "4-1-rag.py")
WEB = load_module("websearch_demo", "4-2-websearch.py")


def tool_list_documents() -> str:
    """에이전트가 문서 목록을 확인할 때 쓰는 도구."""
    docs = DOCUMENTS.load_documents()
    lines = ["[도구] 문서 목록 조회"]
    for doc in docs:
        lines.append(f"- {doc.doc_id}: {doc.text}")
    return "\n".join(lines)


def tool_document_summary() -> str:
    """에이전트가 현재 보유한 문서 구성을 짧게 요약할 때 쓰는 도구."""
    docs = DOCUMENTS.load_documents()
    lines = ["[도구] 문서 구성 요약"]
    lines.append(f"- 문서 수: {len(docs)}")
    lines.append(f"- 문서 id: {', '.join(doc.doc_id for doc in docs)}")
    return "\n".join(lines)


# 4-1-rag.py 의 프롬프트는 "Context 에 없는 내용은 추측하지 말고
# '문서에 없습니다' 라고 하세요" 라고 지시한다. 그 지시를 그대로 따른 응답만 실패로 본다.
#
# 표지를 넓게 잡으면 오탐이 난다. 실제로 "알 수 없습니다" 를 표지에 넣었더니
# 아래 답변이 실패로 처리되어 웹 검색으로 넘어갔다.
#   "현재 시각에 대한 정보가 문서에 없으므로 지금 열려 있는지 알 수 없습니다.
#    문서에는 고객 지원 시간이 평일 09:00-18:00 이며 주말·공휴일은 휴무라고 명시되어 있습니다."
# 이 답변은 질문에 답하지 못한 부분을 밝히면서 문서가 가진 정보를 정확히 전달한다.
# 버릴 이유가 없다.
INSUFFICIENT_MARKERS = ("문서에 없습니다", "문서에 없음")

# 표지가 있어도 답변이 길면 유용한 정보가 함께 담긴 것으로 본다.
# 순수한 거절("문서에 없습니다.")은 짧다.
INSUFFICIENT_MAX_CHARS = 60


def is_insufficient(answer: str) -> bool:
    """문서로 답하지 못했다는 응답인지 판별한다.

    문자열 매칭이라 견고하지 않다. 모델이 다르게 표현하면 놓친다.
    정공법은 생성 단계에서 구조화된 판정값을 받는 것이다.
    """
    text = answer.strip()
    if not text:
        return True
    if not any(marker in text for marker in INSUFFICIENT_MARKERS):
        return False
    return len(text) <= INSUFFICIENT_MAX_CHARS


def tool_rag(question: str) -> str:
    """문서에서 먼저 답을 찾고, 안 되면 웹 검색으로 넘긴다.

    웹 검색은 최후 수단이다. 두 단계로 판정한다.

      1단계 (검색 점수) — 유사도가 기준 미만이면 생성하지 않고 바로 웹으로.
                          관련 문서가 아예 없는 질문에서 생성 호출을 아낀다.
      2단계 (답변 내용) — 생성까지 갔는데 "문서에 없습니다" 로 끝나면 웹으로.
                          유사도는 높지만 정작 답이 문서에 없는 경우를 잡는다.

    2단계가 필요한 이유는 유사도로 갈리지 않는 질문이 있기 때문이다.
    "지금 고객센터 열려 있어?" 는 policy 문서로 0.7572, "오늘 서울 날씨 어때?" 는
    weather 문서로 0.7222 가 나온다. 앞은 문서가 답할 수 있고 뒤는 답할 수 없는데
    점수만으로는 구분되지 않는다. 실제로 답을 만들어 봐야 안다.
    """
    hits = RAG.retrieve(question, top_k=2)
    score = RAG.top_score(hits)

    if score < RAG_MIN_SCORE:
        print(
            f"  [1단계] 검색 최고 점수 {score:.4f} < 기준 {RAG_MIN_SCORE:.2f}"
            " → 관련 문서 없음, 웹 검색으로 전환",
            flush=True,
        )
        return tool_web_search(question)

    print(
        f"  [1단계] 검색 최고 점수 {score:.4f} >= 기준 {RAG_MIN_SCORE:.2f}"
        " → 문서로 답변 시도",
        flush=True,
    )
    answer = RAG.answer_with_contexts(question, hits)

    if is_insufficient(answer):
        print(
            "  [2단계] 문서로 답하지 못함 → 웹 검색으로 전환",
            flush=True,
        )
        return tool_web_search(question)

    print("  [2단계] 문서로 답변 완료", flush=True)
    return answer


def tool_direct_answer(question: str) -> str:
    """문서 검색 없이 일반 답변만 생성한다."""
    return LLM.generate_direct_answer(question)


def tool_web_search(question: str) -> str:
    """외부 웹에서 최신 정보를 찾아 답변한다.

    tool_rag 와 달리 신뢰 경계 밖 텍스트를 프롬프트에 넣는다.
    정규화·구획화는 4-2-websearch.py 안에서 수행된다.
    """
    return WEB.run_websearch(question)


def choose_action(question: str) -> tuple[str, Callable[..., str]]:
    """질문을 보고 어떤 도구를 쓸지 고른다.

    이 예제는 진짜 복잡한 계획 대신, 학습용 규칙 기반 분기만 사용한다.
    실제 에이전트는 보통 LLM 이 직접 다음 행동을 고르기도 한다.
    """
    if any(keyword in question for keyword in ["몇 개", "구성", "종류", "요약"]):
        return ("문서 구성을 먼저 요약하는 것이 맞음", tool_document_summary)

    # 문서 자체를 보여달라는 요청이면 검색보다 목록 조회가 먼저다.
    if any(keyword in question for keyword in ["문서", "목록", "documents"]):
        return ("문서 목록을 먼저 보여주는 것이 맞음", tool_list_documents)

    # 나머지는 전부 RAG 로 보낸다. 웹 검색은 여기서 실패했을 때만 쓴다.
    #
    # 미리 가르지 않는 이유:
    #   - 코퍼스 키워드 목록으로 가르던 방식은 문서를 추가할 때마다 목록을
    #     함께 고쳐야 했고, 실제로 "교환은?" 이 목록에 없어 RAG 를 건너뛰었다.
    #   - 시점 표지(오늘·지금·최근)로 가르던 방식은 정책 문서가 답할 수 있는
    #     "지금 고객센터 열려 있어?" 까지 웹으로 보냈다.
    #
    # 판단은 tool_rag 안에서 실제 검색·생성 결과를 보고 한다.
    return ("문서에서 먼저 찾고, 답이 안 나오면 웹으로 넘김", tool_rag)


def run_agent_with_trace(question: str) -> dict[str, str]:
    """질문을 받아 도구 선택 과정과 최종 결과를 함께 반환한다."""
    print("=" * 60, flush=True)
    print("Agent 데모", flush=True)
    print("=" * 60, flush=True)
    print(f"[입력] {question}", flush=True)

    reason, action = choose_action(question)
    print("[계획] 질문을 보고 다음 행동을 결정합니다.", flush=True)
    print(f"  - 판단: {reason}", flush=True)
    print(f"  - 선택 도구: {action.__name__}", flush=True)

    print("[행동] 도구를 실행합니다.", flush=True)
    # 도구마다 받는 인자가 다르다.
    # RAG/웹검색/일반답변 도구는 질문 문자열이 필요하고,
    # 문서 목록·구성 요약 도구는 추가 인자 없이 바로 실행된다.
    #
    # 질문을 받는 도구를 여기에 빠뜨리면 TypeError 로 죽는다.
    # 도구를 추가할 때 이 목록도 함께 갱신해야 한다.
    if action in (tool_rag, tool_web_search, tool_direct_answer):
        result = action(question)
    else:
        result = action()

    # 에이전트는 보통 도구 실행 결과를 관찰한 뒤 다음 행동을 정한다.
    # 이 예제는 한 번만 실행하고 끝나는 아주 작은 형태다.
    print("[관찰] 도구 실행 결과를 받았습니다.", flush=True)
    return {
        "question": question,
        "reason": reason,
        "tool_name": action.__name__,
        "result": result,
    }


def run_agent(question: str) -> str:
    """질문을 받아 도구를 고르고, 최종 결과 문자열만 반환한다."""
    trace = run_agent_with_trace(question)
    return trace["result"]


def main() -> None:
    """학습용 예제 질문을 순서대로 실행한다."""
    # 질문별로 어떤 도구가 선택되는지 비교해보기 위해
    # 성격이 다른 예제 질문을 섞어 두었다.
    questions = [
        "문서 목록 보여줘",
        "문서 구성 요약해줘",
        "주말에 고객 지원 받을 수 있어?",
        "서울 여름 날씨는 어때?",
        "오늘 서울 날씨 어때?",
        "파이썬은 어떤 언어야?",
    ]

    for index, question in enumerate(questions, start=1):
        print()
        print(f"======== Agent 질문 {index} ========", flush=True)
        try:
            answer = run_agent(question)
        except Exception as exc:
            print(f"[오류] {exc}", file=sys.stderr, flush=True)
            sys.exit(1)
        print("--- 최종 결과 ---", flush=True)
        print(answer, flush=True)


if __name__ == "__main__":
    main()
