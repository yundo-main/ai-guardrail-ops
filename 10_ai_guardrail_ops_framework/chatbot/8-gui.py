"""8-gui.py

7단계 CLI 챗봇을 브라우저 GUI 로 감싸는 단계.

6-api.py 가 "기능을 HTTP 로 노출"하는 단계였다면,
8-gui.py 는 "그 위에 사람이 쓰는 화면을 얹는" 단계다.

의도적으로 신규 패키지를 쓰지 않는다. 이미 있는 fastapi/uvicorn 만으로
정적 HTML 한 장을 서빙한다. Streamlit/Gradio 는 자체 런타임을 들고 오기
때문에 5·7단계에서 만든 자산을 우회하게 되고, 공급망 표면도 늘어난다.

신뢰 경계
  브라우저(신뢰 안 함) ── HTTP ──> 이 서버(신뢰) ── HTTPS ──> Gemini
  - GEMINI_API_KEY 는 서버 프로세스에만 존재한다. 클라이언트로 내려보내지 않는다.
  - 문서 코퍼스와 LLM 응답은 '신뢰 경계 밖 데이터'로 취급해 DOM 에 삽입한다.
"""

from __future__ import annotations

import importlib.util
import os
import secrets
import sys
import threading
import time
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent

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


def load_module(module_name: str, file_name: str):
    """번호가 붙은 예제 파일을 경로로 직접 로드한다. 6-api.py 와 동일한 방식."""
    module_path = BASE_DIR / file_name
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러올 수 없습니다: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# 7단계를 통째로 재사용한다. ChatSession(멀티턴 이력), answer(모드별 분기),
# MODES 를 다시 구현하지 않는다. 7단계가 고쳐지면 GUI 도 같이 고쳐진다.
CHATBOT = load_module("chatbot_gui", "7-chatbot.py")
DOCUMENTS = CHATBOT.DOCUMENTS

# ── 세션 저장소 ────────────────────────────────────────────────
# 교육용 단일 프로세스 인메모리 저장소. 재시작 시 소실되고, 워커가 여러 개면
# 세션이 갈린다. 세션 ID 는 클라이언트가 정하게 두지 않는다(예측/충돌 방지).
SESSIONS: dict[str, "CHATBOT.ChatSession"] = {}
MAX_SESSIONS = 50

# answer() 와 하위 모듈은 판단 과정을 stdout 으로 출력한다. 그 출력을 가로채
# 화면의 '실행 추적' 패널에 보여준다. redirect_stdout 은 프로세스 전역이므로
# 동시 요청이 서로의 출력을 섞는다. 락으로 직렬화한다.
# 대가: 동시 요청이 순차 처리된다. 로컬 학습 도구이므로 수용한다.
ANSWER_LOCK = threading.Lock()

# 루프백 서버는 브라우저의 다른 탭에서 접근 가능하다. DNS 리바인딩으로
# 공격자 도메인이 127.0.0.1 을 가리키게 만드는 경로를 Host 헤더로 차단한다.
ALLOWED_HOSTS = {"127.0.0.1:8001", "localhost:8001", "127.0.0.1", "localhost"}

# 어느 프로세스가 응답 중인지 /health 로 판별하기 위한 표식.
# 환경변수는 execve() 시점에 한 번 복사되고 이후 갱신되지 않는다.
# 즉 "export 했는데 서버가 모른다"는 대부분 export 이전에 뜬 프로세스가
# 아직 포트를 잡고 있는 경우다. pid/기동시각을 노출해 이를 즉시 구분한다.
STARTED_AT = time.strftime("%Y-%m-%d %H:%M:%S")

app = FastAPI(
    title="RAG Agent Demo GUI",
    description="7단계 CLI 챗봇의 브라우저 인터페이스",
    version="0.1.0",
)


@app.middleware("http")
async def guard(request: Request, call_next):
    """Host 헤더 검증 + 응답 보안 헤더 부착."""
    host = request.headers.get("host", "")
    if host not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "허용되지 않은 Host 헤더"}, status_code=421)

    response = await call_next(request)
    # 외부 리소스를 일절 쓰지 않으므로 self 로 묶는다.
    # CDN 을 안 쓰는 이유이기도 하다: 오프라인 동작 + 공급망 표면 제거.
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; "
        "script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; "
        "form-action 'none'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


class ChatRequest(BaseModel):
    # max_length 는 6-api.py 에 없던 통제다. 무제한 입력은 그대로
    # 무제한 토큰 소비(=비용)로 이어진다.
    session_id: str = Field("", max_length=64)
    message: str = Field(..., min_length=1, max_length=2000)


class SettingsRequest(BaseModel):
    session_id: str = Field(..., max_length=64)
    mode: str | None = None
    top_k: int | None = Field(None, ge=1, le=10)


def get_session(session_id: str) -> tuple[str, "CHATBOT.ChatSession"]:
    """세션 ID 로 세션을 찾고, 없으면 새로 발급한다."""
    if session_id and session_id in SESSIONS:
        return session_id, SESSIONS[session_id]
    if len(SESSIONS) >= MAX_SESSIONS:
        SESSIONS.pop(next(iter(SESSIONS)))
    new_id = secrets.token_urlsafe(24)
    SESSIONS[new_id] = CHATBOT.ChatSession()
    return new_id, SESSIONS[new_id]


@app.get("/health")
def health() -> dict[str, str]:
    # api_key 는 '보유 여부'만 반환한다. 값을 실으면 인증 없는 이 엔드포인트가
    # 그대로 키 유출 경로가 된다. 길이도 넣지 않는다(키 형식 추정 단서가 된다).
    return {
        "status": "ok",
        "sessions": str(len(SESSIONS)),
        "api_key": "설정됨" if os.getenv("GEMINI_API_KEY", "").strip() else "없음",
        "pid": str(os.getpid()),
        "started": STARTED_AT,
    }


@app.get("/api/modes")
def get_modes() -> dict[str, object]:
    docs = DOCUMENTS.load_documents()
    return {"modes": list(CHATBOT.MODES), "doc_count": len(docs)}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, object]:
    session_id, session = get_session(request.session_id)
    session.add("user", request.message)

    buffer = StringIO()
    with ANSWER_LOCK:
        try:
            # 판단 과정 출력을 가로채 trace 로 돌려준다.
            with redirect_stdout(buffer):
                text = CHATBOT.answer(session, request.message)
        except SystemExit as exc:
            # 하위 모듈은 API 키가 없으면 sys.exit(1) 로 끝난다.
            # 6-api.py 의 translate_error() 와 같은 이유로 흡수한다.
            raise HTTPException(
                status_code=503,
                detail="Gemini 설정을 확인하세요 (GEMINI_API_KEY).",
            ) from exc
        except Exception as exc:
            # 예외 메시지를 그대로 내보내지 않는다. 내부 경로/모델명 노출 방지.
            print(f"[8-gui] 처리 실패: {exc!r}", file=sys.stderr, flush=True)
            raise HTTPException(status_code=500, detail="답변 생성에 실패했습니다.") from exc

    session.add("bot", text)
    return {
        "session_id": session_id,
        "answer": text,
        "trace": buffer.getvalue(),
        "mode": session.mode,
        "top_k": session.top_k,
        "turns": len(session.turns),
    }


@app.post("/api/settings")
def settings(request: SettingsRequest) -> dict[str, object]:
    session_id, session = get_session(request.session_id)
    if request.mode is not None:
        if request.mode not in CHATBOT.MODES:
            raise HTTPException(status_code=400, detail="알 수 없는 모드입니다.")
        session.mode = request.mode
    if request.top_k is not None:
        session.top_k = request.top_k
    return {"session_id": session_id, "mode": session.mode, "top_k": session.top_k}


@app.post("/api/reset")
def reset(request: SettingsRequest) -> dict[str, object]:
    session_id, session = get_session(request.session_id)
    session.reset()
    return {"session_id": session_id, "turns": 0}


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(PAGE)


# ── 화면 ───────────────────────────────────────────────────────
# 단일 파일 유지를 위해 HTML 을 문자열로 둔다.
#
# XSS 방어의 핵심: 답변 문자열을 innerHTML 이 아니라 textContent 로 넣는다.
# 코퍼스 문서와 LLM 응답은 신뢰 경계 밖 데이터이며, 코퍼스가 외부 입력으로
# 확장되면 문서에 심어진 <script> 가 저장형 XSS 로 성립한다.
# textContent 는 마크업을 해석하지 않으므로 이 경로를 원천 차단한다.
PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAG Agent 챗봇</title>
<style>
  :root { --bg:#12141a; --panel:#1b1e26; --line:#2c313d; --fg:#e6e8ee; --dim:#8b93a7; --accent:#6ea8fe; }
  * { box-sizing:border-box; }
  body { margin:0; height:100vh; display:flex; flex-direction:column;
         background:var(--bg); color:var(--fg);
         font:14px/1.6 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif; }
  header { padding:12px 16px; border-bottom:1px solid var(--line); display:flex;
           gap:12px; align-items:center; flex-wrap:wrap; background:var(--panel); }
  header b { font-weight:600; }
  label { color:var(--dim); font-size:13px; }
  select, input[type=number] { background:var(--bg); color:var(--fg);
           border:1px solid var(--line); border-radius:6px; padding:4px 8px; font:inherit; }
  button { background:var(--accent); color:#0b0d12; border:0; border-radius:6px;
           padding:7px 14px; font:inherit; font-weight:600; cursor:pointer; }
  button.ghost { background:transparent; color:var(--dim); border:1px solid var(--line); font-weight:400; }
  button:disabled { opacity:.45; cursor:not-allowed; }
  #log { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:12px; }
  .msg { max-width:74ch; padding:10px 14px; border-radius:10px; white-space:pre-wrap; word-break:break-word; }
  .user { align-self:flex-end; background:#2a3550; }
  .bot  { align-self:flex-start; background:var(--panel); border:1px solid var(--line); }
  .err  { align-self:flex-start; background:#3a2226; border:1px solid #6b3038; color:#ffb4bd; }
  .trace { align-self:flex-start; max-width:74ch; font-size:12px; color:var(--dim);
           background:#161920; border:1px dashed var(--line); border-radius:8px;
           padding:8px 12px; white-space:pre-wrap; font-family:ui-monospace,Menlo,monospace; }
  footer { border-top:1px solid var(--line); padding:12px 16px; display:flex; gap:10px;
           align-items:flex-end; background:var(--panel); }
  textarea { flex:1; resize:none; height:64px; background:var(--bg); color:var(--fg);
             border:1px solid var(--line); border-radius:8px; padding:10px; font:inherit; }
  .hint { color:var(--dim); font-size:12px; }
</style>
</head>
<body>
<header>
  <b>RAG Agent 챗봇</b>
  <label>모드
    <select id="mode">
      <option value="agent">agent — 도구 자동 선택</option>
      <option value="rag">rag — 항상 문서 검색</option>
      <option value="direct">direct — 검색 없이 답변</option>
    </select>
  </label>
  <label>top_k <input id="topk" type="number" min="1" max="10" value="2" style="width:60px"></label>
  <label><input id="showtrace" type="checkbox" checked> 실행 추적</label>
  <button class="ghost" id="reset">대화 초기화</button>
  <span class="hint" id="status"></span>
</header>

<div id="log"></div>

<footer>
  <textarea id="input" placeholder="질문을 입력하세요.  Enter 전송 / Shift+Enter 줄바꿈"></textarea>
  <button id="send">전송</button>
</footer>

<script>
let sessionId = sessionStorage.getItem("sid") || "";

const log = document.getElementById("log");
const input = document.getElementById("input");
const send = document.getElementById("send");
const status = document.getElementById("status");

function bubble(cls, text) {
  const el = document.createElement("div");
  el.className = cls;
  // innerHTML 을 쓰지 않는다. 문서/LLM 출력은 신뢰 경계 밖 데이터다.
  el.textContent = text;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await res.json().catch(() => ({ detail: "응답을 해석할 수 없습니다." }));
  if (!res.ok) throw new Error(data.detail || ("HTTP " + res.status));
  return data;
}

function remember(data) {
  if (data.session_id) { sessionId = data.session_id; sessionStorage.setItem("sid", sessionId); }
}

async function submit() {
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  send.disabled = true;
  status.textContent = "생성 중…";
  bubble("msg user", text);

  const pending = bubble("msg bot", "…");
  try {
    const data = await post("/api/chat", { session_id: sessionId, message: text });
    remember(data);
    pending.textContent = data.answer;
    if (document.getElementById("showtrace").checked && data.trace.trim()) {
      bubble("trace", data.trace.trim());
    }
    status.textContent = "턴 " + data.turns + " / " + data.mode;
  } catch (e) {
    pending.remove();
    bubble("msg err", e.message);
    status.textContent = "";
  } finally {
    send.disabled = false;
    input.focus();
  }
}

send.addEventListener("click", submit);

// IME 조합 중 Enter 는 한글 확정용이다. isComposing 을 보지 않으면
// 조합 중인 마지막 글자가 잘린 채 전송된다.
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    submit();
  }
});

async function pushSettings() {
  const data = await post("/api/settings", {
    session_id: sessionId,
    mode: document.getElementById("mode").value,
    top_k: Number(document.getElementById("topk").value)
  });
  remember(data);
  status.textContent = data.mode + " / top_k " + data.top_k;
}
document.getElementById("mode").addEventListener("change", pushSettings);
document.getElementById("topk").addEventListener("change", pushSettings);

document.getElementById("reset").addEventListener("click", async () => {
  const data = await post("/api/reset", { session_id: sessionId });
  remember(data);
  log.replaceChildren();
  status.textContent = "이력 초기화됨";
});

// 기동 직후 서버 상태를 화면에 띄운다. 키가 없는 프로세스에 붙어 있으면
// 질문을 보내기 전에 바로 드러난다.
Promise.all([
  fetch("/api/modes").then(r => r.json()),
  fetch("/health").then(r => r.json())
]).then(([m, h]) => {
  status.textContent = "문서 " + m.doc_count + "건 / 키 " + h.api_key
                     + " / pid " + h.pid + " (" + h.started + ")";
  if (h.api_key !== "설정됨") {
    bubble("msg err",
`이 서버 프로세스에 GEMINI_API_KEY 가 없습니다 (pid ${h.pid}, 기동 ${h.started}).
환경변수는 프로세스 시작 시점에 고정되므로 지금 export 해도 반영되지 않습니다.
서버를 종료하고, 키를 export 한 터미널에서 다시 실행하세요.

  lsof -ti:8001 | xargs kill
  export GEMINI_API_KEY='...'
  python 8-gui.py`);
  }
});
input.focus();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn

    # 6-api.py 와 같은 이유로 루프백 고정. 이 화면에는 인증도 레이트 리밋도 없다.
    # 0.0.0.0 바인딩은 API 키를 소비하는 무제한 호출 경로를 그대로 노출한다.
    # 포트는 6-api.py(8000)와 동시 실행할 수 있도록 8001 을 쓴다.
    print("http://127.0.0.1:8001 열기", flush=True)
    # 리로드가 필요하면 uvicorn CLI 를 쓴다. 파일명이 숫자로 시작해도 동작한다.
    #   uvicorn 8-gui:app --host 127.0.0.1 --port 8001 --reload
    # 포트를 바꾸면 ALLOWED_HOSTS 에 그 포트를 추가해야 한다(아니면 421).
    uvicorn.run(app, host="127.0.0.1", port=8001)
