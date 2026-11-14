# 6-apy.py
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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


# 이 예제 폴더는 단계별 파일명 앞에 번호가 붙어 있다.
# 그래서 API 파일도 필요한 모듈을 경로로 직접 읽어온다.
DOCUMENTS = load_module("documents_api", "1-documents.py")
sys.modules.setdefault("documents", DOCUMENTS)
EMBEDDINGS = load_module("embeddings_api", "2-embeddings.py")
sys.modules.setdefault("embeddings", EMBEDDINGS)
RAG = load_module("rag_api", "4-1-rag.py")
AGENT = load_module("agent_api", "5-agent.py")

# FastAPI 앱: 지금까지 만든 문서/임베딩/RAG/Agent 기능을
# HTTP 요청으로 호출할 수 있게 감싸는 서비스 진입점이다.
app = FastAPI(
    title="RAG Agent Demo API",
    description="학습용 RAG + Agent 예제를 HTTP API로 감싼 서비스",
    version="0.1.0",
)


class QuestionRequest(BaseModel):
    # /agent 처럼 질문 문자열만 받는 엔드포인트에서 사용한다.
    question: str = Field(..., description="사용자 질문")


class RagRequest(QuestionRequest):
    # /rag 는 질문뿐 아니라 검색할 문서 개수(top_k)도 함께 받는다.
    top_k: int = Field(2, ge=1, le=10, description="검색할 상위 문서 수")


def translate_error(exc: BaseException) -> HTTPException:
    """스크립트 스타일 예외를 API용 HTTP 예외로 바꾼다."""
    if isinstance(exc, SystemExit):
        return HTTPException(status_code=500, detail="Gemini 설정 또는 실행 중 종료가 발생했습니다.")
    return HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
def health() -> dict[str, str]:
    # 서버가 살아 있는지만 빠르게 확인하는 용도
    return {"status": "ok"}


@app.get("/documents")
def get_documents() -> dict[str, object]:
    # 1-documents.py 단계에서 만든 문서 로더 결과를 그대로 보여준다.
    docs = DOCUMENTS.load_documents()
    return {
        "count": len(docs),
        "documents": [{"doc_id": doc.doc_id, "text": doc.text} for doc in docs],
    }


@app.get("/tools")
def get_tools() -> dict[str, object]:
    # 5-agent.py 가 내부에서 고를 수 있는 도구 목록을 API로 노출한다.
    return {
        "tools": [
            {"name": "tool_list_documents", "description": "문서 목록 조회"},
            {"name": "tool_document_summary", "description": "문서 구성 요약"},
            {"name": "tool_rag", "description": "RAG 검색 후 답변 생성 (점수 미달 시 웹 검색으로 폴백)"},
            {"name": "tool_direct_answer", "description": "문서 검색 없이 일반 답변 생성"},
            {"name": "tool_web_search", "description": "외부 웹 검색 후 답변 생성"},
        ]
    }


@app.post("/rag")
def rag_answer(request: RagRequest) -> dict[str, object]:
    # 3-rag.py 의 run_rag() 를 HTTP 엔드포인트로 감싼다.
    try:
        answer = RAG.run_rag(request.question, top_k=request.top_k)
    except BaseException as exc:
        raise translate_error(exc) from exc
    return {
        "mode": "rag",
        "question": request.question,
        "top_k": request.top_k,
        "answer": answer,
    }


@app.post("/agent")
def agent_answer(request: QuestionRequest) -> dict[str, object]:
    # 5-agent.py 의 run_agent_with_trace() 를 호출한다.
    # 단순 답변뿐 아니라 어떤 도구를 골랐는지도 함께 반환한다.
    try:
        trace = AGENT.run_agent_with_trace(request.question)
    except BaseException as exc:
        raise translate_error(exc) from exc
    return {"mode": "agent", **trace}


if __name__ == "__main__":
    import uvicorn

    # python 6-api.py 로 바로 실행할 수 있게 로컬 개발 서버를 띄운다.
    #
    # 여기서는 reload=True 를 쓸 수 없다. uvicorn 은 리로드를 위해 app 을
    # import 문자열로 받아야 하는데 이 호출은 app 객체를 직접 넘기기 때문이다.
    # 그 조합에서 uvicorn 은 경고만 남기고 서버를 띄우지 않고 종료한다.
    #
    # 리로드가 필요하면 uvicorn CLI 를 쓴다. 파일명이 숫자로 시작해도 동작한다.
    #   uvicorn 6-api:app --host 127.0.0.1 --port 8000 --reload
    #
    # host 는 필요 시 "0.0.0.0" 으로 바꿀 수 있으나, 이 API 에는 인증도
    # 레이트 리밋도 없다. 외부 바인딩은 API 키를 소비하는 무제한 호출 경로를
    # 그대로 노출하므로 기본값은 루프백으로 둔다.
    uvicorn.run(app, host="127.0.0.1", port=8000)
