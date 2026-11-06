"""
Isolated Pytest Fixture for Backend Test Suite
Configures dedicated temporary SQLite test database.
Fails setup immediately if schema creation or seeding fails.
"""

import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is in PYTHONPATH
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

TEST_DB_FILE = os.path.join(backend_dir, "test_ci_isolated.db")
TEST_DB_URL = f"sqlite:///{TEST_DB_FILE}"

# Enforce pure test database URL
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["IS_EXTERNAL_DB"] = "0"
os.environ["DB_HOST"] = ""

import database
import models
from main import app
from seed_data import seed_database

test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Monkeypatch database engine and session
database.engine = test_engine
database.SessionLocal = TestingSessionLocal

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[database.get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_isolated_test_database():
    """
    Initializes clean temporary test database with full relational schema and 30 lawyers.
    Strictly fails if schema generation or seeding encounters any error.
    """
    # Clean previous run if existing
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

    # 1. Create all relational tables
    models.Base.metadata.create_all(bind=test_engine)

    # 2. Seed test database and fail immediately on error
    seed_database()

    yield

    # Teardown
    test_engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass
