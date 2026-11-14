# 7-chatbot.py
# =============================================================================
# 마지막 단계: 지금까지 만든 기능을 하나의 대화형 챗봇으로 묶는다.
#
# 1~6단계와 이 단계의 결정적 차이는 "대화 이력(history)" 이다.
#   1~5단계 : 질문 1개 → 답변 1개 (매번 독립)
#   7단계    : 이전 대화를 기억하고, 후속 질문을 이어서 처리
#
# 실행:
#   python 7-chatbot.py
# =============================================================================

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent


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


# 5-agent.py 는 임포트 시점에 이미 1·2·3·4-1 를 모두 로드한다.
# 그래서 여기서는 5-agent.py 하나만 읽고, 나머지는 그 안에서 꺼내 쓴다.
# (각 파일을 다시 로드하면 같은 모듈이 두 번 실행되어 상태가 갈라진다.)
AGENT = load_module("agent_chat", "5-agent.py")
DOCUMENTS = AGENT.DOCUMENTS
LLM = AGENT.LLM
RAG = AGENT.RAG

# 대화 이력을 무한정 쌓으면 프롬프트가 계속 길어지고 토큰 비용도 함께 늘어난다.
# 학습용이므로 최근 N턴만 남기는 가장 단순한 방식을 쓴다.
MAX_HISTORY_TURNS = 8

# 답변 경로. /mode 명령으로 바꾼다.
#   agent  : 5-agent.py 가 질문을 보고 도구를 고른다 (기본값)
#   rag    : 항상 4-1-rag.py 의 문서 검색을 거친다
#   direct : 문서 검색 없이 3-llm.py 로 바로 답한다
MODES = ("agent", "rag", "direct")

# 짧거나 지시대명사로 시작하는 질문은 앞 대화에 기대고 있을 가능성이 높다.
# 실제 서비스는 LLM 으로 질의를 재작성(query rewriting)하지만,
# 이 예제는 판단 과정을 눈으로 보기 위해 규칙 기반으로 둔다.
# 앞 대화를 가리키는 표현만 넣는다.
#
# 일반 의문사(왜·언제·얼마·어떻게)를 넣으면 안 된다. 새로 던진 독립 질문에도
# 들어가기 때문이다. 예) "비트코인 지금 얼마야?" 가 '얼마' 에 걸려 후속 질문으로
# 오인되면 직전 질문이 검색 질의 앞에 붙어 엉뚱한 결과가 나온다.
#
# 한 글자 표지(더·또)도 넣지 않는다. 부분 문자열로 매칭하므로
# "더위", "또한" 같은 단어에 걸린다.
FOLLOWUP_MARKERS = (
    "그럼", "그러면", "그건", "그거", "그것", "그 중",
    "거기", "방금", "아까", "앞서", "위에서", "말한",
)


@dataclass
class Turn:
    """대화 한 줄. role 은 'user' 또는 'bot'."""

    role: str
    text: str


@dataclass
class ChatSession:
    """한 번의 대화 세션 상태.

    turns  : 주고받은 대화 이력
    mode   : 현재 답변 경로 (agent / rag / direct)
    top_k  : RAG 검색 시 가져올 문서 수
    """

    turns: List[Turn] = field(default_factory=list)
    mode: str = "agent"
    top_k: int = 2

    def add(self, role: str, text: str) -> None:
        self.turns.append(Turn(role=role, text=text))
        # 오래된 턴부터 잘라내 프롬프트 길이를 일정하게 유지한다.
        if len(self.turns) > MAX_HISTORY_TURNS:
            self.turns = self.turns[-MAX_HISTORY_TURNS:]

    def last_user_question(self) -> str | None:
        for turn in reversed(self.turns[:-1] if self.turns else []):
            if turn.role == "user":
                return turn.text
        return None

    def render_history(self) -> str:
        """이력을 프롬프트에 넣을 수 있는 문자열로 만든다."""
        lines = []
        for turn in self.turns:
            speaker = "사용자" if turn.role == "user" else "어시스턴트"
            lines.append(f"{speaker}: {turn.text}")
        return "\n".join(lines)

    def reset(self) -> None:
        self.turns.clear()


def is_followup(session: ChatSession, question: str) -> bool:
    """이 질문이 앞 대화에 이어지는 후속 질문인지 추정한다."""
    if not session.turns:
        return False
    stripped = question.strip()
    # 한국어 질문은 원래 짧다("서울 여름 날씨 어때?" = 12자).
    # 길이 기준을 느슨하게 잡으면 멀쩡한 새 질문까지 후속 질문으로 오인한다.
    # 그래서 길이는 아주 짧을 때만 근거로 쓰고, 판단의 주축은 지시대명사 표지로 둔다.
    if len(stripped) <= 6:
        return True
    return any(marker in stripped for marker in FOLLOWUP_MARKERS)


def build_search_query(session: ChatSession, question: str) -> str:
    """검색(임베딩)용 질의를 만든다.

    후속 질문은 그 자체로는 검색어가 되지 못한다("그럼 주말은?").
    직전 사용자 질문을 앞에 붙여 검색어의 의미를 복원한다.

    주의: 이력 전체를 붙이면 임베딩이 흐려져 오히려 검색 품질이 떨어진다.
    그래서 검색용은 짧게(직전 질문 1개), 생성용은 길게(이력 블록) 나눠 쓴다.
    """
    if not is_followup(session, question):
        return question
    previous = session.last_user_question()
    if not previous:
        return question
    return f"{previous} {question}"


def build_contextual_prompt(session: ChatSession, question: str) -> str:
    """생성(LLM)용 프롬프트를 만든다. 이전 대화를 함께 넣는다."""
    if not session.turns:
        return question
    return (
        "--- 이전 대화 ---\n"
        f"{session.render_history()}\n"
        "---\n"
        "위 대화 맥락을 참고해 다음 질문에 한국어로 간결히 답하세요.\n"
        f"Question: {question}"
    )


def answer(session: ChatSession, question: str) -> str:
    """현재 모드에 맞는 경로로 답변을 만든다."""
    followup = is_followup(session, question)
    if followup:
        print("  [이력] 후속 질문으로 판단 → 이전 대화를 함께 사용", flush=True)

    if session.mode == "direct":
        # 문서 검색 없이 3-llm.py 로 바로 보낸다.
        return LLM.generate_direct_answer(build_contextual_prompt(session, question))

    if session.mode == "rag":
        # 항상 4-1-rag.py 의 검색을 거친다.
        return RAG.run_rag(build_search_query(session, question), top_k=session.top_k)

    # agent 모드: 5-agent.py 의 도구 선택 로직을 그대로 쓴다.
    #
    # 단, run_agent_with_trace() 를 통째로 부르지 않고 choose_action() 과
    # 도구 실행을 분리한다. 그 함수는 "도구 선택"과 "도구 실행"에 같은 문자열을
    # 쓰는데, 후속 질문 때문에 이전 질문을 앞에 붙이면 그 문자열이 라우팅까지
    # 흔들어 버리기 때문이다.
    #   예) "문서 구성 요약해줘" + "서울 여름 날씨 어때?"
    #       → '요약' 키워드에 걸려 RAG 대신 문서 요약 도구가 선택됨
    #
    # 따라서 라우팅은 사용자가 실제로 친 질문으로만 하고,
    # 대화 맥락은 선택된 도구에 넘기는 질의에만 반영한다.
    reason, action = AGENT.choose_action(question)
    print("  [계획] 질문을 보고 다음 행동을 결정합니다.", flush=True)
    print(f"    - 판단: {reason}", flush=True)
    print(f"    - 선택 도구: {action.__name__}", flush=True)

    if action is AGENT.tool_rag:
        # tool_rag 안에서 점수·답변을 보고 필요하면 웹 검색으로 넘어간다.
        # 그때 넘어가는 질의도 여기서 만든 것이다. build_search_query() 는
        # 로컬 임베딩 검색에 맞춰 이력을 최소한만 붙이는 설계라
        # 웹 질의로는 최적이 아니다. 분리가 필요하면 5-agent.py 의
        # tool_rag() 폴백 지점에서 한다.
        return AGENT.tool_rag(build_search_query(session, question))

    # 나머지는 문서 목록·구성 요약 도구로, 질문 문자열을 받지 않는다.
    #
    # choose_action() 은 tool_web_search 나 tool_direct_answer 를 반환하지 않는다.
    # 웹 검색은 tool_rag 의 폴백으로만, 일반 답변은 /mode direct 로만 쓰인다.
    return action()


HELP_TEXT = """사용 가능한 명령
  /help           이 도움말
  /mode <이름>    답변 경로 변경 (agent | rag | direct)
  /topk <숫자>    RAG 검색 문서 수 변경 (1~10)
  /docs           현재 보유 문서 목록
  /history        지금까지의 대화 이력
  /reset          대화 이력 초기화
  /quit           종료 (Ctrl-D 도 동일)"""


def handle_command(session: ChatSession, line: str) -> bool:
    """슬래시 명령을 처리한다. 종료해야 하면 False 를 반환한다."""
    parts = line.split()
    command = parts[0].lower()
    argument = parts[1] if len(parts) > 1 else ""

    if command in ("/quit", "/exit"):
        return False

    if command == "/help":
        print(HELP_TEXT, flush=True)

    elif command == "/mode":
        if argument in MODES:
            session.mode = argument
            print(f"  [모드] {argument} 로 전환", flush=True)
        else:
            print(f"  [오류] 모드는 {' | '.join(MODES)} 중 하나입니다.", flush=True)

    elif command == "/topk":
        if argument.isdigit() and 1 <= int(argument) <= 10:
            session.top_k = int(argument)
            print(f"  [설정] top_k = {session.top_k}", flush=True)
        else:
            print("  [오류] top_k 는 1~10 사이의 숫자입니다.", flush=True)

    elif command == "/docs":
        for doc in DOCUMENTS.load_documents():
            print(f"  - {doc.doc_id}: {doc.text}", flush=True)

    elif command == "/history":
        if not session.turns:
            print("  (이력 없음)", flush=True)
        else:
            print(session.render_history(), flush=True)

    elif command == "/reset":
        session.reset()
        print("  [이력] 초기화됨", flush=True)

    else:
        print(f"  [오류] 알 수 없는 명령: {command} (/help 참고)", flush=True)

    return True


def main() -> None:
    session = ChatSession()

    print("=" * 60, flush=True)
    print("RAG 챗봇 (Gemini) — 1~6단계를 대화형으로 묶은 마지막 단계", flush=True)
    print("=" * 60, flush=True)
    print(f"모드: {session.mode} / top_k: {session.top_k}", flush=True)
    print("/help 로 명령 목록을 볼 수 있습니다.", flush=True)

    while True:
        try:
            line = input("\n나> ").strip()
        except (EOFError, KeyboardInterrupt):
            # Ctrl-D / Ctrl-C 로 빠져나올 때 트레이스백을 보이지 않게 한다.
            print("\n종료합니다.", flush=True)
            break

        if not line:
            continue

        if line.startswith("/"):
            if not handle_command(session, line):
                print("종료합니다.", flush=True)
                break
            continue

        try:
            result = answer(session, line)
        except SystemExit:
            # 하위 모듈은 API 키가 없으면 sys.exit(1) 로 끝난다.
            # 챗봇은 프로세스를 죽이지 않고 안내만 하고 계속 받는다.
            print("  [오류] Gemini 설정을 확인하세요 (GEMINI_API_KEY).", flush=True)
            continue
        except Exception as exc:
            print(f"  [오류] {exc}", flush=True)
            continue

        # 이력에는 사용자의 원래 질문과 최종 답변만 남긴다.
        # (검색용으로 가공한 질의는 남기지 않는다 — 다음 턴에서 중복 증폭됨)
        session.add("user", line)
        session.add("bot", result)

        print("\n봇>", flush=True)
        print(result, flush=True)


if __name__ == "__main__":
    main()
