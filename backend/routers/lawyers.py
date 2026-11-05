from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field
from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/v1/lawyers", tags=["Lawyer Directory"])

class DirectBookingRequest(BaseModel):
    lawyer_id: int = Field(..., description="ID of verified lawyer")
    client_name: str = Field(..., min_length=2, description="Full name of client")
    client_phone: str = Field(..., min_length=10, description="Contact phone number")
    case_category: str = Field(..., description="Consumer, Civil, or Criminal")
    notes: Optional[str] = Field(None, description="Brief case notes")

class DirectBookingResponse(BaseModel):
    booking_id: int
    lawyer_id: int
    lawyer_name: str
    total_fee: float
    payment_status: str
    current_milestone: int
    milestone_schedule: List[str]
    message: str

class DirectBookingRecord(BaseModel):
    booking_id: int
    lawyer_id: int
    lawyer_name: str
    client_name: str
    client_phone: str
    case_category: str
    total_fee: float
    payment_status: str
    current_milestone: int
    created_at: str

@router.get("", response_model=List[schemas.LawyerResponse])
@router.get("/", response_model=List[schemas.LawyerResponse], include_in_schema=False)
def list_lawyers(
    category: Optional[models.CaseCategory] = None,
    max_budget: Optional[Decimal] = None,
    language: Optional[str] = None,
    city: Optional[str] = None,
    sort_by: Optional[str] = Query(None, pattern="^(fee_asc|fee_desc|experience_desc|rating_desc)$"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Search and filter verified lawyers across Civil, Consumer, and Criminal categories.
    Supports multi-criteria filtering by category, max_budget, language, city, and sorting.
    """
    query = db.query(models.Lawyer)

    if category:
        query = query.filter(models.Lawyer.category == category)
    if max_budget is not None:
        query = query.filter(models.Lawyer.full_case_estimate <= max_budget)
    if language:
        query = query.filter(models.Lawyer.languages.ilike(f"%{language.strip()}%"))
    if city:
        query = query.filter(models.Lawyer.city.ilike(f"%{city.strip()}%"))

    # Sorting
    if sort_by == "fee_asc":
        query = query.order_by(models.Lawyer.full_case_estimate.asc(), models.Lawyer.rating.desc())
    elif sort_by == "fee_desc":
        query = query.order_by(models.Lawyer.full_case_estimate.desc(), models.Lawyer.rating.desc())
    elif sort_by == "experience_desc":
        query = query.order_by(models.Lawyer.experience_years.desc(), models.Lawyer.rating.desc())
    else:
        # Default sort: Highest rating first, then fee affordability
        query = query.order_by(models.Lawyer.rating.desc(), models.Lawyer.full_case_estimate.asc())

    return query.offset(skip).limit(limit).all()

@router.post("/book", response_model=DirectBookingResponse, status_code=status.HTTP_201_CREATED, summary="Direct Client Consultation Booking with 4 Milestones")
def book_lawyer_direct(payload: DirectBookingRequest, db: Session = Depends(get_db)):
    """
    Direct consultation booking for citizen frontend:
      1. Verifies that lawyer exists in SQL.
      2. Uses the official lawyer fee from database.
      3. Persists booking in SQL database.
      4. Returns genuine inserted booking ID.
    """
    lawyer = db.query(models.Lawyer).filter(models.Lawyer.lawyer_id == payload.lawyer_id).first()
    if not lawyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lawyer with ID {payload.lawyer_id} not found"
        )

    # Find or create a client user record
    user = db.query(models.User).filter(models.User.phone == payload.client_phone).first()
    if not user:
        # Determine unique email
        clean_phone = "".join(filter(str.isdigit, payload.client_phone))
        email = f"client_{clean_phone}@nyayaconnect.in"
        user = models.User(
            full_name=payload.client_name,
            email=email,
            phone=payload.client_phone,
            password_hash="client_direct_auth",
            role=models.UserRole.CLIENT
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    total_fee = Decimal(str(lawyer.consultation_fee))
    # Map category string to Enum
    cat_enum = models.CaseCategory.CONSUMER
    cat_upper = payload.case_category.upper()
    if "CIVIL" in cat_upper:
        cat_enum = models.CaseCategory.CIVIL
    elif "CRIMINAL" in cat_upper:
        cat_enum = models.CaseCategory.CRIMINAL

    booking = models.Booking(
        user_id=user.user_id,
        lawyer_id=lawyer.lawyer_id,
        case_title=f"Vernacular Consultation ({payload.case_category})",
        case_category=cat_enum,
        total_agreed_fee=total_fee,
        status=models.BookingStatus.PENDING
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    milestones = [
        "Stage 1: Initial Consultation (15%)",
        "Stage 2: Notice/Drafting (25%)",
        "Stage 3: Filing & First Hearing (30%)",
        "Stage 4: Final Arguments (30%)"
    ]

    return DirectBookingResponse(
        booking_id=booking.booking_id,
        lawyer_id=lawyer.lawyer_id,
        lawyer_name=lawyer.full_name,
        total_fee=float(total_fee),
        payment_status="Confirmed_Escrow_Hold",
        current_milestone=1,
        milestone_schedule=milestones,
        message="Consultation booked successfully and persisted in SQL database."
    )

@router.get("/bookings", response_model=List[DirectBookingRecord], summary="List persisted bookings for client dashboard")
def list_persisted_bookings(db: Session = Depends(get_db)):
    """Returns genuine persisted bookings from SQL database for dashboard rendering."""
    bookings = db.query(models.Booking).order_by(models.Booking.booking_id.desc()).limit(20).all()
    results = []
    for b in bookings:
        results.append(DirectBookingRecord(
            booking_id=b.booking_id,
            lawyer_id=b.lawyer_id,
            lawyer_name=b.lawyer.full_name if b.lawyer else "Assigned Advocate",
            client_name=b.user.full_name if b.user else "Citizen",
            client_phone=b.user.phone if b.user else "",
            case_category=b.case_category.value if hasattr(b.case_category, "value") else str(b.case_category),
            total_fee=float(b.total_agreed_fee),
            payment_status=b.status.value if hasattr(b.status, "value") else str(b.status),
            current_milestone=1,
            created_at=str(b.created_at)
        ))
    return results

@router.get("/{lawyer_id}", response_model=schemas.LawyerDetailResponse)
def get_lawyer_profile(lawyer_id: int, db: Session = Depends(get_db)):
    lawyer = db.query(models.Lawyer).filter(models.Lawyer.lawyer_id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lawyer with ID {lawyer_id} not found"
        )

    avg_fee = db.query(func.avg(models.Lawyer.full_case_estimate)).filter(
        models.Lawyer.category == lawyer.category
    ).scalar()

    category_avg = Decimal(str(round(avg_fee, 2))) if avg_fee is not None else lawyer.full_case_estimate

    if category_avg > 0:
        diff_pct = ((lawyer.full_case_estimate - category_avg) / category_avg) * Decimal("100")
        diff_val = round(abs(diff_pct), 1)
        if diff_pct < Decimal("-0.5"):
            display_pct = int(diff_val) if diff_val == int(diff_val) else diff_val
            badge = f"{display_pct}% Below Category Average"
        elif diff_pct > Decimal("0.5"):
            display_pct = int(diff_val) if diff_val == int(diff_val) else diff_val
            badge = f"{display_pct}% Above Category Average"
        else:
            badge = "At Category Average"
    else:
        badge = "At Category Average"

    return schemas.LawyerDetailResponse(
        lawyer_id=lawyer.lawyer_id,
        full_name=lawyer.full_name,
        bar_council_id=lawyer.bar_council_id,
        category=lawyer.category,
        experience_years=lawyer.experience_years,
        languages=lawyer.languages,
        city=lawyer.city,
        phone=lawyer.phone,
        email=lawyer.email,
        consultation_fee=lawyer.consultation_fee,
        drafting_fee=lawyer.drafting_fee,
        hearing_fee=lawyer.hearing_fee,
        full_case_estimate=lawyer.full_case_estimate,
        rating=lawyer.rating,
        category_average_fee=category_avg,
        fee_comparison_badge=badge
    )

@router.post("/recommend", response_model=List[schemas.LawyerResponse])
def recommend_lawyers(payload: schemas.LawyerRecommendRequest, db: Session = Depends(get_db)):
    query = db.query(models.Lawyer).filter(
        models.Lawyer.category == payload.recommended_case_category
    )
    if payload.max_budget is not None:
        query = query.filter(models.Lawyer.full_case_estimate <= payload.max_budget)
    return query.order_by(
        models.Lawyer.rating.desc(),
        models.Lawyer.full_case_estimate.asc()
    ).limit(3).all()
