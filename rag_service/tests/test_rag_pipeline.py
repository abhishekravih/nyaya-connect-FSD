"""
NyayaConnect - Comprehensive RAG Pipeline & API Test Suite
Validates schema adherence, category constraints, zero hallucination, and caching.
"""

import pytest
from fastapi.testclient import TestClient
try:
    from main import app
except ImportError:
    from rag_server import app
from vector_store import hybrid_retrieve, extract_exact_article_query
from rag_chain import RAGLegalResponse

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/rag/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["vector_store"]["collection"] == "constitution_rag"
    assert data["vector_store"]["total_chunks"] == 1030
    assert data["vector_store"]["status"] == "connected"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "endpoints" in data


def test_ask_article_22_detention():
    payload = {
        "query": "A citizen was kept in police custody for 36 hours without being produced before a magistrate. What does the Constitution say?",
        "top_k": 3
    }
    response = client.post("/api/v1/rag/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Validate Pydantic schema
    legal_resp = RAGLegalResponse(**data)
    assert legal_resp.recommended_case_category in ["Civil", "Consumer", "Criminal"]
    assert legal_resp.urgency_level in ["Low", "Medium", "High"]
    assert len(legal_resp.answer) > 20
    assert legal_resp.recommended_case_category == "Criminal"
    assert legal_resp.urgency_level == "High"
    assert any("Article 22" in getattr(art, "article", str(art)) for art in legal_resp.cited_articles)


def test_ask_article_14_equality():
    payload = {
        "query": "Can the government deny equality before law or equal protection of laws to a non-citizen?",
        "top_k": 3
    }
    response = client.post("/api/v1/rag/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    legal_resp = RAGLegalResponse(**data)
    assert legal_resp.recommended_case_category == "Civil"
    assert any("Article 14" in getattr(art, "article", str(art)) for art in legal_resp.cited_articles)


def test_query_caching_behavior():
    payload = {
        "query": "What is the Preamble of the Constitution of India?",
        "top_k": 2
    }
    # First request: computes and caches
    res1 = client.post("/api/v1/rag/ask", json=payload)
    assert res1.status_code == 200

    # Second request: served instantly from cache
    res2 = client.post("/api/v1/rag/ask", json=payload)
    assert res2.status_code == 200
    assert res1.json() == res2.json()


def test_hybrid_retrieval_exact_article_extraction():
    q1 = "Explain Article 21 to me"
    assert extract_exact_article_query(q1) == "Article 21"

    q2 = "What are the remedies under Article 32?"
    assert extract_exact_article_query(q2) == "Article 32"

    q3 = "What does the Preamble say?"
    assert extract_exact_article_query(q3) == "Preamble"

    results = hybrid_retrieve("Article 21 right to life", top_k=2)
    assert len(results) > 0
    top_match = results[0]
    assert top_match["metadata"]["article_number"] == "Article 21"
