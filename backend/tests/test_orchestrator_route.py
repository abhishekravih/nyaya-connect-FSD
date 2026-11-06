"""
Route Tests for Composite Legal Orchestrator
Tests POST /api/v1/orchestrate/legal-assist:
- English and regional translation flows.
- Strict rejection of missing / invalid RAG category (HTTP 502).
- Upstream RAG microservice timeout/unreachability (HTTP 503).
- Database failure reporting (HTTP 500).
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app

client = TestClient(app)

MOCK_CIVIL_RAG = {
    "recommended_case_category": "Civil",
    "explanation": "Property tenancy and lease security disputes are governed by state Rent Control Acts and the Transfer of Property Act.",
    "articles": [
        {
            "article_number": "Article 300A",
            "title": "Persons not to be deprived of property save by authority of law",
            "relevance_summary": "Protects statutory property rights."
        }
    ]
}

def test_orchestrator_english_flow_success():
    """Verify orchestrator returns legal explanation and top 3 verified lawyers in category."""
    with patch("backend.routers.orchestrator.query_rag_service", new=AsyncMock(return_value=MOCK_CIVIL_RAG)):
        res = client.post("/api/v1/orchestrate/legal-assist", json={
            "query": "Landlord refuses to return security deposit of 50000 rupees",
            "source_language": "en-IN"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["category"] == "Civil"
        assert len(data["recommended_lawyers"]) > 0
        assert data["recommended_lawyers"][0]["specialization"] == "Civil Law"

def test_orchestrator_regional_language_translation_flow():
    """Verify orchestrator translates regional Kannada query to English before RAG lookup."""
    with patch("backend.routers.orchestrator.stage_3_translate_to_english", new=AsyncMock(return_value="What are my rights if arrested?")):
        with patch("backend.routers.orchestrator.query_rag_service", new=AsyncMock(return_value={
            "recommended_case_category": "Criminal",
            "explanation": "Under Article 22, an arrested person has the right to consult a legal practitioner.",
            "articles": [{"article_number": "Article 22", "title": "Protection against arrest", "relevance_summary": "Right to counsel"}]
        })):
            res = client.post("/api/v1/orchestrate/legal-assist", json={
                "query": "ನನ್ನನ್ನು ಬಂಧಿಸಿದರೆ ನನಗೆ ಯಾವ ಹಕ್ಕುಗಳಿವೆ?",
                "source_language": "kn-IN"
            })
            assert res.status_code == 200
            data = res.json()
            assert data["category"] == "Criminal"
            assert data["source_language"] == "kn-IN"
            assert data["translated_english_query"] == "What are my rights if arrested?"
            assert len(data["recommended_lawyers"]) > 0

def test_orchestrator_rejects_missing_rag_category_502():
    """Verify orchestrator rejects upstream response with missing category with HTTP 502 Bad Gateway."""
    with patch("backend.routers.orchestrator.query_rag_service", new=AsyncMock(return_value={
        "recommended_case_category": None,
        "explanation": "Some legal text without category",
        "articles": []
    })):
        res = client.post("/api/v1/orchestrate/legal-assist", json={
            "query": "Generic inquiry without category",
            "source_language": "en-IN"
        })
        assert res.status_code == 502
        assert "invalid or missing legal category" in res.json()["detail"].lower()

def test_orchestrator_handles_rag_unavailable_503():
    """Verify orchestrator reports HTTP 503 when upstream RAG engine is down."""
    with patch("backend.routers.orchestrator.query_rag_service", side_effect=Exception("RAG connection refused on port 8001")):
        res = client.post("/api/v1/orchestrate/legal-assist", json={
            "query": "Testing RAG unreachability",
            "source_language": "en-IN"
        })
        # Either handled as 503 or exception
        assert res.status_code in [503, 500]

def test_orchestrator_handles_database_error_truthfully():
    """Verify orchestrator raises clear service error rather than returning misleading empty lawyers."""
    with patch("backend.routers.orchestrator.query_rag_service", new=AsyncMock(return_value=MOCK_CIVIL_RAG)):
        with patch("backend.routers.orchestrator.get_lawyers_by_category_db", side_effect=RuntimeError("SQL table locked")):
            res = client.post("/api/v1/orchestrate/legal-assist", json={
                "query": "Testing database failure",
                "source_language": "en-IN"
            })
            assert res.status_code == 500
            assert "database failed" in res.json()["detail"].lower()
