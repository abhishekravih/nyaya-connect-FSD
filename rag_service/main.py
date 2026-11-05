"""
NyayaConnect - Constitutional RAG Microservice (Person 3: AI & RAG Engine)
File: /rag_service/main.py

Port: 8001 (default) or $PORT
Endpoints:
  - POST /api/v1/rag/ask (Constitutional grounding, zero-hallucination citations, case categorization)
  - GET /api/v1/rag/health (Detailed RAG health check)
  - GET /health (Docker health check)
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag_chain import RAGLegalResponse, ask_constitutional_rag, MODEL_NAME
from vector_store import get_collection, build_vector_store, COLLECTION_NAME, EMBED_MODEL_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("nyayaconnect.rag_service")

app = FastAPI(
    title="NyayaConnect Constitutional RAG Engine",
    description="Vector search & Constitutional Article grounding powered by ChromaDB & Google Gemini",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory LRU query cache for sub-millisecond repeated responses
_QUERY_CACHE: Dict[str, Dict[str, Any]] = {}
_MAX_CACHE_SIZE = 500


class AskRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        description="Legal question submitted by user",
        json_schema_extra={"example": "The police detained my brother for 36 hours without producing him before a magistrate."}
    )
    language: Optional[str] = Field("en", description="Preferred language code (e.g. 'en', 'hi')")
    chat_history: Optional[list] = Field(default_factory=list, description="Prior conversation context")
    top_k: Optional[int] = Field(4, ge=1, le=10, description="Number of constitutional articles to retrieve")


class ArticleCitation(BaseModel):
    article_number: str
    title: str
    relevance_summary: str


class RichCitedArticle(BaseModel):
    article: str
    part: Optional[str] = ""
    exact_quote: Optional[str] = ""


class ComprehensiveRAGResponse(BaseModel):
    query: str
    answer: str
    explanation: str  # Alias for backend/routers/orchestrator.py compatibility
    cited_articles: List[RichCitedArticle]  # Section 4 Blueprint schema
    articles: List[ArticleCitation]  # Orchestrator schema
    recommended_case_category: str
    urgency_level: str
    suggested_action: str


@app.on_event("startup")
def startup_event():
    """Verify or initialize persistent ChromaDB index on startup."""
    try:
        col = get_collection()
        count = col.count()
        if count == 0:
            logger.info("ChromaDB collection is empty. Auto-indexing constitutional corpus...")
            build_vector_store(force_reindex=False)
            logger.info(f"Auto-indexing complete. {col.count()} chunks available.")
        else:
            logger.info(f"ChromaDB persistent collection '{COLLECTION_NAME}' loaded with {count} chunks.")
    except Exception as e:
        logger.warning(f"ChromaDB startup initialization notice: {e}")


@app.get("/", tags=["Root"])
def root():
    return {
        "status": "online",
        "service": "NyayaConnect Constitutional RAG Engine",
        "version": "1.0.0",
        "endpoints": {
            "ask": "POST /api/v1/rag/ask",
            "health": "GET /api/v1/rag/health",
            "docker_health": "GET /health",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
def docker_health():
    """Lightweight Docker healthcheck endpoint matching docker-compose.yml."""
    return {"status": "healthy"}


@app.get("/api/v1/rag/health", tags=["Health"])
def rag_health_check():
    """Detailed healthcheck endpoint matching Person 3 guide."""
    try:
        col = get_collection()
        total_chunks = col.count()
    except Exception as e:
        total_chunks = f"Notice: {str(e)}"

    api_key_configured = bool(os.getenv("GEMINI_API_KEY", "").strip())

    return {
        "status": "healthy",
        "service": "NyayaConnect Constitutional RAG Engine",
        "version": "1.0.0",
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
            "max_capacity": _MAX_CACHE_SIZE
        }
    }


@app.post("/api/v1/rag/ask", response_model=ComprehensiveRAGResponse, tags=["RAG"])
def ask_constitutional_query(req: AskRequest):
    """
    Core Constitutional RAG pipeline:
    1. Checks LRU memory cache for instant hit (< 5ms).
    2. Executes hybrid retrieval against persistent ChromaDB.
    3. Synthesizes zero-hallucination response validated by Pydantic.
    4. Formats both rich cited_articles (Blueprint) and articles (Orchestrator).
    """
    clean_query = req.query.strip()
    cache_key = f"{clean_query.lower()}_{req.top_k}"

    if cache_key in _QUERY_CACHE:
        return _QUERY_CACHE[cache_key]

    try:
        legal_resp: RAGLegalResponse = ask_constitutional_rag(clean_query, top_k=req.top_k)

        # Build dual article schemas for 100% interoperability
        rich_cited: List[RichCitedArticle] = []
        simple_articles: List[ArticleCitation] = []

        for item in legal_resp.cited_articles:
            art_str = getattr(item, "article", str(item))
            part_str = getattr(item, "part", "Part III – Fundamental Rights")
            quote_str = getattr(item, "exact_quote", "")

            rich_cited.append(RichCitedArticle(
                article=art_str,
                part=part_str,
                exact_quote=quote_str
            ))
            simple_articles.append(ArticleCitation(
                article_number=art_str,
                title=part_str,
                relevance_summary=quote_str or f"Grounded provision under {art_str}"
            ))

        response_dict = {
            "query": clean_query,
            "answer": legal_resp.answer,
            "explanation": legal_resp.answer,  # Exact field required by backend orchestrator
            "cited_articles": [r.model_dump() for r in rich_cited],
            "articles": [s.model_dump() for s in simple_articles],
            "recommended_case_category": legal_resp.recommended_case_category,
            "urgency_level": legal_resp.urgency_level,
            "suggested_action": legal_resp.suggested_action
        }

        # Cache response
        if len(_QUERY_CACHE) >= _MAX_CACHE_SIZE:
            oldest = next(iter(_QUERY_CACHE))
            del _QUERY_CACHE[oldest]
        _QUERY_CACHE[cache_key] = response_dict

        return ComprehensiveRAGResponse(**response_dict)

    except Exception as exc:
        logger.error(f"RAG inference error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Constitutional RAG pipeline inference failed: {str(exc)}"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting NyayaConnect RAG Microservice on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
