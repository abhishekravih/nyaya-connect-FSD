"""
NyayaConnect - Composite Orchestrator Router (Person 4: System Integration)
File: /backend/routers/orchestrator.py

Composite Endpoint:
  POST /api/v1/orchestrate/legal-assist

Flow:
  1. Accepts citizen legal inquiry in any supported Indian regional language.
  2. If non-English, translates query to English via Stage 3 translation adapter.
  3. Queries Person 3's ChromaDB RAG Engine (POST /api/v1/rag/ask) to obtain:
     - Constitutional Articles
     - recommended_case_category ('Civil', 'Consumer', or 'Criminal')
     - Plain-language legal explanation
  4. Translates explanation back to native language if needed, preserving citations.
  5. Queries Person 2's SQL database for top 3 verified lawyers in that exact category,
     sorted by transparent fee affordability. Truthful schema without fabricated data.
  6. Returns a single unified JSON payload to Person 1's UI in <3 seconds.
"""

import os
import re
import time
import logging
from typing import List, Optional, Dict, Any
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from backend.database import get_lawyers_by_category_db
from backend.routers.voice_bridge import (
    stage_3_translate_to_english,
    stage_4_translate_to_vernacular,
    validate_language_code,
    SUPPORTED_LANGUAGES
)

logger = logging.getLogger("nyayaconnect.orchestrator")

router = APIRouter(prefix="/api/v1/orchestrate", tags=["Unified Orchestrator"])

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag_service:8001/api/v1")
RAG_LOCAL_URL = os.getenv("RAG_LOCAL_URL", "http://127.0.0.1:8001/api/v1")

class LegalAssistRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Legal question submitted by user")
    source_language: Optional[str] = Field("en-IN", description="Language of inquiry (e.g. kn-IN, hi-IN, en-IN)")
    user_location: Optional[str] = Field("Bengaluru, Karnataka", description="User city/state")

class ConstitutionalArticle(BaseModel):
    article_number: str
    title: str
    relevance_summary: str

class LawyerRecommendation(BaseModel):
    id: int
    name: str
    specialization: str
    bar_council_id: str
    experience_years: int
    consultation_fee: float
    full_case_estimate: float
    rating: float
    languages_spoken: List[str]
    location: str
    milestones: List[str]

class LegalAssistResponse(BaseModel):
    status: str
    query: str
    source_language: str
    translated_english_query: str
    category: str
    explanation: str
    constitutional_articles: List[ConstitutionalArticle]
    recommended_lawyers: List[LawyerRecommendation]
    response_time_ms: float

def resolve_case_category(rag_category: Optional[str]) -> str:
    """
    Validates upstream RAG legal classification.
    Rejects missing or invalid categories with HTTP 502 rather than broad keyword guessing.
    """
    if rag_category and isinstance(rag_category, str) and rag_category.strip():
        cat = rag_category.strip().capitalize()
        if cat in ["Civil", "Consumer", "Criminal"]:
            return cat

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Upstream RAG service returned invalid or missing legal category: '{rag_category}'. Expected Civil, Consumer, or Criminal."
    )

async def query_rag_service(query_text: str) -> Dict[str, Any]:
    """Calls Person 3's RAG service POST /api/v1/rag/ask with fallback error reporting."""
    target_urls = [
        f"{RAG_SERVICE_URL}/rag/ask",
        f"{RAG_LOCAL_URL}/rag/ask",
        "http://localhost:8001/api/v1/rag/ask"
    ]
    last_error = None
    for url in target_urls:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(url, json={"query": query_text})
                if res.status_code == 200:
                    return res.json()
                last_error = f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            last_error = str(e)
            continue

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"RAG engine unavailable at {RAG_SERVICE_URL}. Error: {last_error}"
    )

@router.post("/legal-assist", response_model=LegalAssistResponse, summary="Composite Ask -> Classify -> Recommend Flow")
async def orchestrate_legal_assist(request: LegalAssistRequest):
    """
    Unified composite endpoint called by frontend.
    1. Validates and translates regional language queries before RAG lookup.
    2. Retrieves Constitutional advice & category classification.
    3. Translates explanation back to native language preserving legal citations.
    4. Connects classified category to verified affordable lawyers in <3s.
    """
    start_time = time.time()

    # Determine and validate language
    raw_lang = request.source_language or "en-IN"
    lang_code = "en-IN"
    if raw_lang in SUPPORTED_LANGUAGES:
        lang_code = raw_lang
    else:
        # Check by name prefix
        lower_lang = raw_lang.lower()
        for code, name in SUPPORTED_LANGUAGES.items():
            if name.lower() in lower_lang or code.split("-")[0] in lower_lang:
                lang_code = code
                break

    # 1. Translate regional queries before querying RAG engine
    english_query = request.query
    if not lang_code.startswith("en"):
        english_query = await stage_3_translate_to_english(request.query, lang_code)

    # 2. Query RAG microservice with English query
    rag_data = await query_rag_service(english_query)
    raw_category = rag_data.get("recommended_case_category")
    category = resolve_case_category(raw_category)
    articles = [ConstitutionalArticle(**a) for a in rag_data.get("articles", [])]
    raw_explanation = rag_data.get("explanation") or rag_data.get("answer") or ""

    # 3. Translate explanation back to native language if non-English
    final_explanation = raw_explanation
    if not lang_code.startswith("en"):
        final_explanation, _ = await stage_4_translate_to_vernacular(raw_explanation, lang_code)

    # 4. Query SQL database for top 3 verified lawyers in this category
    try:
        lawyers = await get_lawyers_by_category_db(category)
        lawyer_models = [LawyerRecommendation(**l) for l in lawyers]
    except Exception as e:
        logger.error(f"Database error during lawyer orchestration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database failed to retrieve verified lawyers: {str(e)}"
        )

    elapsed = round((time.time() - start_time) * 1000, 2)

    return LegalAssistResponse(
        status="success",
        query=request.query,
        source_language=lang_code,
        translated_english_query=english_query,
        category=category,
        explanation=final_explanation,
        constitutional_articles=articles,
        recommended_lawyers=lawyer_models,
        response_time_ms=elapsed
    )
