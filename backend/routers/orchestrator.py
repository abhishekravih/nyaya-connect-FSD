"""
NyayaConnect - Composite Orchestrator Router (Person 4: System Integration)
File: /backend/routers/orchestrator.py

Composite Endpoint:
  POST /api/v1/orchestrate/legal-assist

Flow:
  1. Accepts citizen legal inquiry.
  2. Queries Person 3's ChromaDB RAG Engine (POST /api/v1/rag/ask) to obtain:
     - Constitutional Articles
     - recommended_case_category ('Civil', 'Consumer', or 'Criminal')
     - Plain-language legal explanation
  3. Queries Person 2's SQL database for top 3 verified lawyers in that exact category,
     sorted by transparent fee affordability.
  4. Returns a single unified JSON payload to Person 1's UI in <3 seconds.
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from backend.database import get_lawyers_by_category_db

logger = logging.getLogger("nyayaconnect.orchestrator")

router = APIRouter(prefix="/api/v1/orchestrate", tags=["Unified Orchestrator"])

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag_service:8001/api/v1")
RAG_LOCAL_URL = os.getenv("RAG_LOCAL_URL", "http://127.0.0.1:8001/api/v1")

class LegalAssistRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Legal question submitted by user")
    source_language: Optional[str] = Field("en-IN", description="Language of inquiry")
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
    rating: float
    reviews_count: int
    verified: bool
    languages_spoken: List[str]
    location: str
    milestones: List[str]

class LegalAssistResponse(BaseModel):
    status: str
    query: str
    category: str
    explanation: str
    constitutional_articles: List[ConstitutionalArticle]
    recommended_lawyers: List[LawyerRecommendation]
    response_time_ms: float

async def query_rag_service(query_text: str) -> Dict[str, Any]:
    """Calls Person 3's RAG service POST /api/v1/rag/ask with fallback error reporting."""
    target_urls = [
        f"{RAG_SERVICE_URL}/rag/ask",
        f"{RAG_LOCAL_URL}/rag/ask"
    ]
    last_error = None
    for url in target_urls:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
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
    Returns Constitutional advice from RAG and top 3 affordable verified lawyers in <3s.
    """
    start_time = time.time()

    # 1. Query RAG microservice for category & constitutional grounding
    rag_data = await query_rag_service(request.query)
    category = rag_data.get("recommended_case_category", "Consumer")
    articles = [ConstitutionalArticle(**a) for a in rag_data.get("articles", [])]
    explanation = rag_data.get("explanation") or rag_data.get("answer") or ""

    # 2. Query SQL database for top 3 verified lawyers in this category
    lawyers = await get_lawyers_by_category_db(category)
    lawyer_models = [LawyerRecommendation(**l) for l in lawyers]

    elapsed = round((time.time() - start_time) * 1000, 2)

    return LegalAssistResponse(
        status="success",
        query=request.query,
        category=category,
        explanation=explanation,
        constitutional_articles=articles,
        recommended_lawyers=lawyer_models,
        response_time_ms=elapsed
    )
