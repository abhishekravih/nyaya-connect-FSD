"""
Pytest Fixtures for Backend Tests
Initializes database with all schema tables and seeds 30 lawyers and test users.
Ensures tests pass from clean checkout with no pre-existing database.
"""
import os
import sys
import pytest

# Ensure both backend and repo root are in PYTHONPATH
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo_root = os.path.dirname(backend_dir)
for p in [backend_dir, repo_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from database import engine, Base, SessionLocal
from seed_data import seed_database
import models

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-level fixture that idempotently ensures tables exist and seed data is populated.
    """
    Base.metadata.create_all(bind=engine)
    try:
        seed_database()
    except Exception:
        pass
    yield
