"""
NyayaConnect - Comprehensive Legal RAG Pipeline & API Test Suite
Validates schema adherence, category constraints, zero hallucination, word boundary classification, and caching.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
try:
    from main import app
except ImportError:
    from rag_server import app
from vector_store import hybrid_retrieve, extract_exact_legal_references
from rag_chain import RAGLegalResponse, classify_legal_domain

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/rag/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["vector_store"]["collection"] == "indian_legal_corpus"
    # Reviewer Requirement 8: Removed brittle total_chunks == 1030 assertion
    assert data["vector_store"]["total_chunks"] >= 1000
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
    assert legal_resp.consult_lawyer_immediately is True
    assert "disclaimer" in data and len(data["disclaimer"]) > 10
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


def test_ask_consumer_protection_query():
    """Reviewer Requirement 5: Consumer queries go through retrieval and LLM."""
    payload = {
        "query": "A customer bought an expensive television with a 2-year warranty that broke down in 1 month, and the seller refused repair or refund.",
        "top_k": 3
    }
    response = client.post("/api/v1/rag/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    legal_resp = RAGLegalResponse(**data)
    assert legal_resp.recommended_case_category == "Consumer"
    assert len(legal_resp.answer) > 30


def test_word_boundary_classifier_no_false_positives():
    """Reviewer Requirement 6: Ensure 'fir' does not falsely match 'first' or 'confirm'."""
    q_first = "This is my first time seeking guidance on property mutation in municipal records"
    cat1, _, _ = classify_legal_domain(q_first)
    assert cat1 != "Criminal", f"Query containing 'first' must not be classified as Criminal (got {cat1})"

    q_confirm = "Can you confirm if religious education is permitted in state institutions?"
    cat2, _, _ = classify_legal_domain(q_confirm)
    assert cat2 != "Criminal", f"Query containing 'confirm' must not be classified as Criminal (got {cat2})"

    q_fir = "The local police officer refused to register an FIR for violent theft"
    cat3, _, _ = classify_legal_domain(q_fir)
    assert cat3 == "Criminal", f"Query containing 'FIR' must be classified as Criminal (got {cat3})"


def test_query_caching_behavior():
    payload = {
        "query": "What does the Preamble of the Constitution of India declare?",
        "top_k": 2
    }
    # First request: computes and caches
    res1 = client.post("/api/v1/rag/ask", json=payload)
    assert res1.status_code == 200

    # Second request: served instantly from cache
    res2 = client.post("/api/v1/rag/ask", json=payload)
    assert res2.status_code == 200
    assert res1.json()["answer"] == res2.json()["answer"]


def test_hybrid_retrieval_exact_article_extraction():
    q1 = "Explain Article 21 to me"
    refs1 = extract_exact_legal_references(q1)
    assert "Article 21" in refs1

    q2 = "What are the remedies under Article 32?"
    refs2 = extract_exact_legal_references(q2)
    assert "Article 32" in refs2

    q3 = "What does the Preamble say?"
    refs3 = extract_exact_legal_references(q3)
    assert "Preamble" in refs3

    results = hybrid_retrieve("Article 21 right to life", top_k=2)
    assert len(results) > 0
    top_match = results[0]
    assert top_match["metadata"]["article_number"] == "Article 21"
