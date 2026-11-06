"""
Comprehensive Tests for Liveness & Readiness Probes
Verifies that readiness truthfully fails with HTTP 503 when MySQL or RAG is unavailable.
"""

from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app
import database

client = TestClient(app)

def test_liveness_probe_returns_200():
    """Verify /health/live returns HTTP 200 when backend process is running."""
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_readiness_probe_fails_503_when_db_down():
    """Verify /health/ready returns HTTP 503 when primary SQL database fails connection check."""
    with patch("main.check_db_health", return_value=(False, "Connection to MySQL port 3306 timed out")):
        res = client.get("/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["ready"] is False
        assert data["database"]["status"] == "unreachable"
        assert "timed out" in data["database"]["detail"]

def test_readiness_probe_fails_503_when_rag_service_down():
    """Verify /health/ready returns HTTP 503 when upstream ChromaDB RAG microservice is unreachable."""
    with patch("main.check_db_health", return_value=(True, "database reachable")):
        with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused on port 8001")):
            res = client.get("/health/ready")
            assert res.status_code == 503
            data = res.json()
            assert data["ready"] is False
            assert data["rag_service"]["status"] == "unreachable"
