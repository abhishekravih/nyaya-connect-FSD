"""
Health & Readiness Diagnostics Tests
File: backend/tests/test_health.py
"""

from fastapi.testclient import TestClient
from database import check_db_health, get_engine
from main import app

client = TestClient(app)

def test_database_health_check():
    get_engine()
    healthy, msg = check_db_health()
    assert healthy is True
    assert "reachable" in msg.lower()

def test_liveness_endpoint():
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_root_index_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "endpoints" in data
