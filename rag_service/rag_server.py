"""
NyayaConnect - Multi-Source Legal RAG Microservice (FastAPI)
Exposes POST /api/v1/rag/ask and GET /api/v1/rag/health with true OrderedDict LRU caching,
restricted CORS, and full contract compatibility for Person 1, Person 2, and Orchestrator.
"""

import os
import time
import json
from collections import OrderedDict
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag_chain import RAGLegalResponse, ask_constitutional_rag, MODEL_NAME
from vector_store import get_collection, COLLECTION_NAME, EMBED_MODEL_NAME

app = FastAPI(
    title="NyayaConnect Legal RAG API",
    description="Multi-Source Legal Intelligence Microservice for NyayaConnect (Constitution, CPA, BNSS, BNS, RTI, Precedents).",
    version="1.1.0"
)

# Reviewer Requirement 7: Restrict CORS to authorized frontend & orchestration origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# True LRU query cache (Reviewer Requirement 7)
_QUERY_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_MAX_CACHE_SIZE = 500


class AskRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        description="The citizen or paralegal legal query",
        json_schema_extra={"example": "Can the police arrest a citizen without informing them of the grounds of arrest?"}
    )
    language: Optional[str] = Field(default="en", description="Preferred language code (e.g. 'en', 'hi')")
    chat_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Prior chat history for multi-turn conversational context")
    top_k: Optional[int] = Field(
        default=4,
        ge=1,
        le=10,
        description="Number of legal provisions to retrieve"
    )


@app.get("/", tags=["Root"])
def root():
    return {
        "status": "online",
        "service": "NyayaConnect Legal RAG API",
        "endpoints": {
            "ask": "POST /api/v1/rag/ask",
            "health": "GET /api/v1/rag/health",
            "docs": "/docs"
        }
    }


@app.get("/api/v1/rag/health", tags=["Health"])
def health_check():
    """Returns vector database status, chunk counts, and model readiness."""
    try:
        col = get_collection()
        total_chunks = col.count()
    except Exception as e:
        total_chunks = f"Error: {str(e)}"

    api_key_configured = bool(os.getenv("GEMINI_API_KEY", "").strip())

    return {
        "status": "healthy",
        "service": "NyayaConnect Legal RAG API",
        "version": "1.1.0",
        "vector_store": {
            "collection": COLLECTION_NAME,
            "total_chunks": total_chunks,
            "embedding_model": EMBED_MODEL_NAME,
            "status": "connected"
        },
        "llm_engine": {
            "model": MODEL_NAME,
            "api_key_present": api_key_configured,
            "mode": "gemini-live" if api_key_configured else "grounded-offline-fallback"
        },
        "cache": {
            "cached_entries": len(_QUERY_CACHE),
            "max_capacity": _MAX_CACHE_SIZE,
            "type": "OrderedDict_LRU"
        }
    }


@app.post("/api/v1/rag/ask", tags=["RAG"])
def ask_legal_question(request: AskRequest):
    """
    Multi-Source Legal RAG pipeline:
    1. Checks LRU memory cache (query + language + history + top_k).
    2. Executes hybrid retrieval (BM25 + Dense RRF) against legal index.
    3. Synthesizes zero-hallucination response verified by code guardrail.
    4. Guarantees cross-compatibility with Person 1 (cited_articles) and Person 4 Orchestrator (explanation, articles).
    """
    clean_query = request.query.strip()
    
    # Reviewer Requirement 7: Include language and chat history in LRU cache key
    hist_hash = hash(json.dumps(request.chat_history, sort_keys=True)) if request.chat_history else 0
    cache_key = f"{request.language}_{clean_query.lower()}_{request.top_k}_{hist_hash}"

    # Cache hit check with LRU promotion
    if cache_key in _QUERY_CACHE:
        _QUERY_CACHE.move_to_end(cache_key)
        return _QUERY_CACHE[cache_key]

    try:
        start_time = time.time()
        response: RAGLegalResponse = ask_constitutional_rag(clean_query, top_k=request.top_k)
        elapsed = round(time.time() - start_time, 3)

        # Build full teammate cross-compatibility response payload
        orchestrator_articles = []
        for c in response.cited_articles:
            art_num = getattr(c, "article", str(c))
            quote = getattr(c, "exact_quote", "")
            orchestrator_articles.append({
                "article_number": art_num,
                "title": getattr(c, "part", "Legal Provision"),
                "relevance_summary": quote if quote else f"Key provision under {art_num}"
            })

        payload = {
            "query": response.query,
            "answer": response.answer,
            "explanation": response.answer,
            "cited_articles": [c.model_dump() for c in response.cited_articles],
            "articles": orchestrator_articles,
            "recommended_case_category": response.recommended_case_category,
            "urgency_level": response.urgency_level,
            "suggested_action": response.suggested_action,
            "consult_lawyer_immediately": response.consult_lawyer_immediately,
            "disclaimer": response.disclaimer,
            "execution_time_seconds": elapsed
        }

        # Evict least recently used if at capacity
        if len(_QUERY_CACHE) >= _MAX_CACHE_SIZE:
            _QUERY_CACHE.popitem(last=False)

        _QUERY_CACHE[cache_key] = payload
        return payload

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Legal RAG inference failed: {str(exc)}"
        )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting NyayaConnect Legal RAG Server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
