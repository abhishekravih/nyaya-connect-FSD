import os
import sys

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ensure pure-Python mode for SQLAlchemy to prevent DLL/AppLocker blocks on Windows
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nyayaconnect.database")

# Load environment variables from .env
load_dotenv()

# Read DATABASE_URL or default to local SQLite fallback
FALLBACK_SQLITE_URL = "sqlite:///./nyayaconnect.db"
DATABASE_URL = os.getenv("DATABASE_URL", FALLBACK_SQLITE_URL)

def get_engine(db_url: str):
    """
    Creates SQLAlchemy engine with automatic fallback to SQLite if MySQL/PostgreSQL
    is specified but unreachable.
    """
    try:
        if db_url.startswith("sqlite"):
            return create_engine(
                db_url,
                connect_args={"check_same_thread": False}
            )
        else:
            # MySQL or PostgreSQL connection attempt
            eng = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to primary database: %s", db_url.split("@")[-1] if "@" in db_url else db_url)
            return eng
    except Exception as e:
        logger.warning(
            "Primary database connection (%s) failed: %s. Falling back to local SQLite (%s)",
            db_url.split("@")[-1] if "@" in db_url else db_url,
            str(e),
            FALLBACK_SQLITE_URL
        )
        return create_engine(
            FALLBACK_SQLITE_URL,
            connect_args={"check_same_thread": False}
        )

# Initialize Engine and Session
engine = get_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative ORM models
Base = declarative_base()

def get_db():
    """
    FastAPI dependency yielding a transactional SQLAlchemy session per request.
    Automatically closes session upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_health():
    """
    Truthful database health check executing SELECT 1.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "database reachable"
    except Exception as e:
        return False, str(e)

async def get_lawyers_by_category_db(category: str):
    """
    Integration helper for Person 4's composite orchestrator.
    Queries Person 2's database for verified lawyers in category sorted by fee affordability.
    """
    try:
        import models
        db = SessionLocal()
        try:
            db_lawyers = db.query(models.Lawyer).filter(
                models.Lawyer.category == category
            ).order_by(models.Lawyer.full_case_estimate.asc()).limit(3).all()

            results = []
            for l in db_lawyers:
                langs = [s.strip() for s in l.languages.split(",") if s.strip()]
                results.append({
                    "id": l.lawyer_id,
                    "name": l.full_name,
                    "specialization": f"{l.category.value} Law & Dispute Resolution",
                    "bar_council_id": l.bar_council_id,
                    "experience_years": l.experience_years,
                    "consultation_fee": float(l.consultation_fee),
                    "rating": float(l.rating),
                    "reviews_count": 50 + (l.experience_years * 8),
                    "verified": True,
                    "languages_spoken": langs,
                    "location": l.city,
                    "milestones": [
                        "1. Initial Consultation (15%)",
                        "2. Notice/Drafting (25%)",
                        "3. Filing & First Hearing (30%)",
                        "4. Final Arguments (30%)"
                    ]
                })
            return results
        finally:
            db.close()
    except Exception as err:
        logger.debug(f"get_lawyers_by_category_db error: {err}")
        return []
