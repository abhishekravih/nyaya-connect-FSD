"""
Health & Readiness Diagnostics Tests
File: backend/tests/test_health.py
"""

from backend.database import check_db_health, get_engine

def test_database_health_check():
    get_engine()
    healthy, msg = check_db_health()
    assert healthy is True
    assert "reachable" in msg.lower()
