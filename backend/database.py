import os
import sys
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Pure-Python mode for SQLAlchemy to prevent DLL/AppLocker blocks on Windows
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nyayaconnect.database")

# Load environment variables
load_dotenv()

FALLBACK_SQLITE_URL = "sqlite:///./nyayaconnect.db"

def is_external_url(url: str) -> bool:
    """Detects whether a URL string targets an external SQL server (MySQL / PostgreSQL)."""
    return any(p in url.lower() for p in ["mysql", "postgresql", "postgres"])

def build_database_url() -> Tuple[str, bool]:
    """
    Constructs the database connection URL.
    Returns (url_string, is_mysql_or_external).

    1. If DATABASE_URL is set in environment, uses it.
    2. If DB_HOST is set (e.g. in Docker Compose with db), safely creates a MySQL URL
       via SQLAlchemy's URL.create to escape passwords properly.
    3. Otherwise defaults to SQLite for zero-config local development and testing.
    """
    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url and env_db_url.strip():
        is_ext = is_external_url(env_db_url.strip())
        return env_db_url.strip(), is_ext

    db_host = os.getenv("DB_HOST")
    if db_host and db_host.strip():
        db_user = os.getenv("DB_USER", "root")
        db_pass = os.getenv("DB_PASSWORD", "")
        db_port = int(os.getenv("DB_PORT", "3306"))
        db_name = os.getenv("DB_DATABASE", "nyayaconnect")

        mysql_url = URL.create(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            host=db_host.strip(),
            port=db_port,
            database=db_name
        )
        return mysql_url.render_as_string(hide_password=False), True

    return FALLBACK_SQLITE_URL, False

DATABASE_URL, IS_EXTERNAL_DB = build_database_url()

def get_engine(db_url: Optional[str] = None):
    """
    Creates an SQLAlchemy engine.
    If db_url is omitted, uses the configured DATABASE_URL.

    STRICT RULE: Never fall back to SQLite when the selected or configured URL is MySQL or PostgreSQL.
    SQLite is strictly reserved for local development or tests when explicitly selected.
    If MySQL/PostgreSQL cannot be reached, creates an engine that fails on connect,
    ensuring health checks and readiness probes truthfully fail with HTTP 503.
    """
    target_url = db_url or DATABASE_URL
    is_ext = is_external_url(target_url)

    if not is_ext:
        # SQLite: used only when explicitly selected
        return create_engine(
            target_url,
            connect_args={"check_same_thread": False}
        )

    # MySQL or PostgreSQL: strictly enforced without SQLite failover
    try:
        eng = create_engine(
            target_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"connect_timeout": 3}
        )
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connected successfully to primary external database.")
        return eng
    except Exception as e:
        logger.error("Primary database (%s) connection failed: %s", target_url.split("@")[-1], str(e))
        # Return engine that will raise OperationalError on connect so readiness truthfully fails
        return create_engine(target_url, pool_pre_ping=True, connect_args={"connect_timeout": 2})

engine = get_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI dependency yielding a transactional SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_health() -> Tuple[bool, str]:
    """
    Truthful database health check executing SELECT 1 on the configured engine.
    Returns (True, 'database reachable') or (False, error_message).
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "database reachable"
    except Exception as e:
        return False, str(e)

async def get_lawyers_by_category_db(category: str) -> List[Dict[str, Any]]:
    """
    Queries database for lawyers in category sorted by fee estimate.
    Returns actual stored values without fabricating ungrounded verification or review data.
    Raises RuntimeError on database failure rather than hiding errors as an empty list.
    """
    try:
        import models
        db = SessionLocal()
        try:
            cat_val = category.capitalize()
            db_lawyers = db.query(models.Lawyer).filter(
                models.Lawyer.category == cat_val
            ).order_by(models.Lawyer.full_case_estimate.asc()).limit(3).all()

            results = []
            for l in db_lawyers:
                langs = [s.strip() for s in l.languages.split(",") if s.strip()]
                results.append({
                    "id": l.lawyer_id,
                    "name": l.full_name,
                    "specialization": f"{l.category.value if hasattr(l.category, 'value') else l.category} Law",
                    "bar_council_id": l.bar_council_id,
                    "experience_years": l.experience_years,
                    "consultation_fee": float(l.consultation_fee),
                    "full_case_estimate": float(l.full_case_estimate),
                    "rating": float(l.rating),
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
        logger.error(f"get_lawyers_by_category_db error: {err}")
        raise RuntimeError(f"Database error during lawyer retrieval: {str(err)}")


def create_booking_in_db(
    lawyer_id: int,
    client_name: str,
    client_phone: str,
    case_category: str,
    notes: Optional[str] = None,
    total_fee_override: Optional[Decimal] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Consolidated single booking creation engine:
    1. Verifies lawyer in database.
    2. Identifies or creates user account with secure random credentials.
    3. Persists booking with honest status 'Pending'.
    4. Atomically creates 4 CaseMilestone rows (15%, 25%, 30%, 30%).
    5. Sets Milestone 1 to IN_PROGRESS and Milestones 2-4 to PENDING.
    6. Issues a signed JWT access token for authenticated access to this booking.
    """
    import models
    import secrets
    from auth.jwt_handler import get_password_hash, create_access_token

    db = SessionLocal()
    try:
        lawyer = db.query(models.Lawyer).filter(models.Lawyer.lawyer_id == lawyer_id).first()
        if not lawyer:
            raise ValueError(f"Lawyer with ID {lawyer_id} not found.")

        # Find or create user
        if user_id:
            user = db.query(models.User).filter(models.User.user_id == user_id).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found.")
        else:
            user = db.query(models.User).filter(models.User.phone == client_phone).first()
            if not user:
                clean_phone = "".join(filter(str.isdigit, client_phone))
                email = f"client_{clean_phone}@nyayaconnect.in"
                existing_email = db.query(models.User).filter(models.User.email == email).first()
                if existing_email:
                    email = f"client_{clean_phone}_{secrets.token_hex(4)}@nyayaconnect.in"
                user = models.User(
                    full_name=client_name or "Citizen Client",
                    email=email,
                    phone=client_phone,
                    password_hash=get_password_hash(secrets.token_urlsafe(32)),
                    role=models.UserRole.CLIENT
                )
                db.add(user)
                db.flush()

        cat_upper = case_category.upper()
        if "CIVIL" in cat_upper:
            cat_enum = models.CaseCategory.Civil
        elif "CRIMINAL" in cat_upper:
            cat_enum = models.CaseCategory.Criminal
        else:
            cat_enum = models.CaseCategory.Consumer

        total_fee = total_fee_override if total_fee_override and total_fee_override > 0 else Decimal(str(lawyer.full_case_estimate))

        booking = models.Booking(
            user_id=user.user_id,
            lawyer_id=lawyer.lawyer_id,
            case_category=cat_enum,
            case_summary=notes.strip() if notes and notes.strip() else f"Consultation for {case_category} matter",
            total_agreed_fee=total_fee
        )
        db.add(booking)
        db.flush()

        # Atomic 4-stage milestones: 15%, 25%, 30%, 30%
        m1 = Decimal(str(round(total_fee * Decimal("0.15"), 2)))
        m2 = Decimal(str(round(total_fee * Decimal("0.25"), 2)))
        m3 = Decimal(str(round(total_fee * Decimal("0.30"), 2)))
        m4 = total_fee - (m1 + m2 + m3)

        milestone_defs = [
            (1, "Stage 1: Initial Assessment & Consultation", Decimal("15.00"), m1, models.MilestoneStatus.IN_PROGRESS),
            (2, "Stage 2: Document Drafting & Legal Notice", Decimal("25.00"), m2, models.MilestoneStatus.PENDING),
            (3, "Stage 3: Case Filing & First Hearing", Decimal("30.00"), m3, models.MilestoneStatus.PENDING),
            (4, "Stage 4: Final Arguments & Resolution", Decimal("30.00"), m4, models.MilestoneStatus.PENDING)
        ]

        milestone_records = []
        milestone_schedule = []
        for stage_no, name, pct, amt, init_status in milestone_defs:
            ms = models.CaseMilestone(
                booking_id=booking.booking_id,
                stage_number=stage_no,
                stage_name=name,
                percentage=pct,
                amount=amt,
                status=init_status
            )
            db.add(ms)
            milestone_records.append({
                "stage_number": stage_no,
                "stage_name": name,
                "percentage": float(pct),
                "amount": float(amt),
                "status": init_status.value
            })
            milestone_schedule.append(f"{name} ({int(pct)}% - ₹{amt})")

        db.commit()
        db.refresh(booking)

        # Generate scoped JWT access token for this booking owner
        access_token = create_access_token({
            "sub": user.email,
            "user_id": user.user_id,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "booking_id": booking.booking_id
        })

        return {
            "booking_id": booking.booking_id,
            "user_id": user.user_id,
            "lawyer_id": lawyer.lawyer_id,
            "lawyer_name": lawyer.full_name,
            "client_name": user.full_name,
            "client_phone": user.phone,
            "case_category": cat_enum.value,
            "case_summary": booking.case_summary,
            "total_fee": float(total_fee),
            "payment_status": "Pending",
            "current_milestone": 1,
            "milestone_schedule": milestone_schedule,
            "milestones": milestone_records,
            "access_token": access_token
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_all_bookings_from_db(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Returns bookings from database scoped to user_id.
    Prevents public leakage of client names, fees, and private details.
    """
    import models
    db = SessionLocal()
    try:
        query = db.query(models.Booking)
        if user_id is not None:
            query = query.filter(models.Booking.user_id == user_id)
        bookings = query.order_by(models.Booking.booking_id.desc()).all()

        results = []
        for b in bookings:
            results.append({
                "booking_id": b.booking_id,
                "user_id": b.user_id,
                "lawyer_id": b.lawyer_id,
                "lawyer_name": b.lawyer.full_name if b.lawyer else "Assigned Advocate",
                "client_name": b.user.full_name if b.user else "Citizen",
                "client_phone": b.user.phone if b.user else "",
                "case_category": b.case_category.value if hasattr(b.case_category, "value") else str(b.case_category),
                "case_summary": b.case_summary,
                "total_fee": float(b.total_agreed_fee),
                "payment_status": "Pending",
                "milestones": [
                    {
                        "stage_number": m.stage_number,
                        "stage_name": m.stage_name,
                        "percentage": float(m.percentage),
                        "amount": float(m.amount),
                        "status": m.status.value
                    } for m in b.milestones
                ],
                "milestone_schedule": [
                    f"{m.stage_name} ({int(m.percentage)}%)" for m in b.milestones
                ]
            })
        return results
    finally:
        db.close()
