# 4-1-rag.py
# =============================================================================
# RAG (Retrieval-Augmented Generation) 설명용 샘플
#
# 데이터 흐름 (한 줄):
#   Document → Embed → Vector DB → search → Prompt → LLM → 답변
#
# 각 단계:
#   1) Document   : 참고할 텍스트(지식)를 준비한다
#   2) Embed      : 텍스트를 숫자 벡터로 바꾼다 (의미 유사도 비교용)
#   3) Vector DB  : 벡터를 저장한다 (여기선 메모리 리스트로 단순화)
#   4) search     : 질문 벡터와 가장 비슷한 문서를 찾는다
#   5) Prompt     : 찾은 문서(Context) + 질문을 프롬프트로 합친다
#   6) LLM        : 3-llm.py 가 Gemini 를 호출해 답변을 생성한다
#
# 예제 모듈:
#   1-documents.py (Document, load_documents)
#   2-embeddings.py (embed_text, embed_query)
#   3-llm.py      (require_gemini, generate_answer)
#
# 실행:
#   python 4-1-rag.py
# =============================================================================

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

try:
    from documents import Document, load_documents
except ModuleNotFoundError:
    module_path = Path(__file__).with_name("1-documents.py")
    spec = importlib.util.spec_from_file_location("documents", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러올 수 없습니다: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["documents"] = module
    spec.loader.exec_module(module)
    Document = module.Document
    load_documents = module.load_documents

try:
    from embeddings import embed_query, embed_text
except ModuleNotFoundError:
    module_path = Path(__file__).with_name("2-embeddings.py")
    spec = importlib.util.spec_from_file_location("embeddings", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러올 수 없습니다: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["embeddings"] = module
    spec.loader.exec_module(module)
    embed_query = module.embed_query
    embed_text = module.embed_text

try:
    from llm import generate_answer, require_gemini
except ModuleNotFoundError:
    module_path = Path(__file__).with_name("3-llm.py")
    spec = importlib.util.spec_from_file_location("llm", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러올 수 없습니다: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["llm"] = module
    spec.loader.exec_module(module)
    generate_answer = module.generate_answer
    require_gemini = module.require_gemini


@dataclass
class VectorRecord:
    """벡터 DB 한 행: 문서 + 그 문서의 임베딩."""

    document: Document
    embedding: List[float]


class InMemoryVectorDB:
    """실제 Chroma/Pinecone 대신 리스트로 저장."""

    def __init__(self) -> None:
        self._rows: List[VectorRecord] = []

    def add(self, document: Document, embedding: Sequence[float]) -> None:
        self._rows.append(
            VectorRecord(document=document, embedding=list(embedding))
        )

    def all(self) -> List[VectorRecord]:
        return list(self._rows)


def build_index(genai, documents: List[Document]) -> InMemoryVectorDB:
    """문서를 임베딩해 메모리 벡터 DB 에 적재한다."""
    db = InMemoryVectorDB()
    print("[1–3] Document → Embed → Vector DB", flush=True)
    for doc in documents:
        print(f"  - embedding document {doc.doc_id!r}", flush=True)
        vec = embed_text(genai, doc.text)
        db.add(doc, vec)
        print(f"  + indexed {doc.doc_id!r} (dim={len(vec)})", flush=True)
    return db


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """코사인 유사도: 1에 가까울수록 방향이 비슷."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def search(
    genai,
    db: InMemoryVectorDB,
    query: str,
    top_k: int = 2,
) -> List[Tuple[Document, float]]:
    """질문 임베딩 후 DB 에서 유사도 상위 top_k 문서 반환."""
    print(f"[4] search query={query!r} top_k={top_k}", flush=True)
    q_vec = embed_query(genai, query)
    scored: List[Tuple[Document, float]] = []
    for row in db.all():
        score = cosine_similarity(q_vec, row.embedding)
        scored.append((row.document, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    hits = scored[:top_k]
    for doc, score in hits:
        print(f"  hit {doc.doc_id!r} score={score:.4f}", flush=True)
    return hits

# roe
def build_prompt(question: str, contexts: List[Document]) -> str:
    """검색된 문서를 Context 로 붙인 사용자 프롬프트 작성."""
    if not contexts:
        context_block = "(관련 문서 없음)"
    else:
        parts = [f"[{c.doc_id}] {c.text}" for c in contexts]
        context_block = "\n".join(parts)

    prompt = f"""다음 Context 만 근거로 질문에 답하세요.
Context 에 없는 내용은 추측하지 말고 '문서에 없습니다'라고 하세요.

--- Context ---
{context_block}
---

Question: {question}
"""
    print("[5] Prompt 조립 (Context + Question)", flush=True)
    return prompt


def retrieve(question: str, top_k: int = 2) -> List[Tuple[Document, float]]:
    """Document → Embed → Vector DB → search 까지만 수행한다.

    답변을 만들기 전에 검색 점수를 확인해야 하는 호출부가 있어 생성과 분리했다.
    5-agent.py 는 이 점수를 보고 로컬 문서로 답할지 웹 검색으로 넘길지 결정한다.
    """
    documents = load_documents()
    print("[1] Document 로드", flush=True)
    for doc in documents:
        print(f"  - document {doc.doc_id!r}: {doc.text}", flush=True)

    genai = require_gemini()
    db = build_index(genai, documents)
    return search(genai, db, question, top_k=top_k)


def top_score(hits: Sequence[Tuple[Document, float]]) -> float:
    """검색 결과 중 최고 유사도. 결과가 없으면 0.0 을 돌려준다."""
    return hits[0][1] if hits else 0.0


def answer_with_contexts(
    question: str,
    hits: Sequence[Tuple[Document, float]],
) -> str:
    """검색 결과를 Context 로 붙여 답변을 생성한다.

    require_gemini() 를 다시 부르지만 이는 임포트와 키 설정뿐이라 API 호출이 아니다.
    """
    contexts = [doc for doc, _score in hits]
    prompt = build_prompt(question, contexts)
    genai = require_gemini()
    return generate_answer(genai, prompt)


def run_rag(question: str, top_k: int = 2) -> str:
    """Document → Embed → Vector DB → search → Prompt → LLM → 답변

    검색 점수와 무관하게 항상 로컬 문서로 답한다.
    점수에 따라 웹 검색으로 넘기려면 5-agent.py 의 tool_rag() 를 쓴다.
    """
    hits = retrieve(question, top_k=top_k)
    return answer_with_contexts(question, hits)


def main() -> None:
    print("=" * 60)
    print("RAG 데모 (Gemini)")
    print("Document → Embed → Vector DB → search → Prompt → LLM")
    print("=" * 60)

    # 12건 코퍼스(1-documents.json)에 맞춘 예제다.
    # 마지막 질문은 코퍼스에 없는 주제라 '문서에 없습니다' 가 나온다.
    # RAG 가 모르는 것을 지어내지 않는다는 점을 보여주기 위한 것이다.
    questions = [
        "주말에 고객 지원 받을 수 있어?",   # policy 문서로 답한다
        "환불하면 배송비는 누가 내?",       # refund 문서로 답한다
        "비행기 표 환불 규정 알려줘",       # 코퍼스에 없다
    ]

    for i, q in enumerate(questions, 1):
        print()
        print(f"======== 질문 {i}: {q} ========")
        try:
            answer = run_rag(q, top_k=2)
        except Exception as exc:
            print(f"[오류] {exc}", file=sys.stderr)
            sys.exit(1)
        print("--- 답변 ---")
        print(answer)
        print()


if __name__ == "__main__":
    main()
