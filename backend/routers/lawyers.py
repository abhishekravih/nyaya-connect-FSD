from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field
import secrets
from database import get_db, create_booking_in_db
import models
import schemas
from auth.jwt_handler import get_password_hash, get_current_user

def mask_phone_number(raw_phone: Optional[str]) -> str:
    """Masks phone number to protect citizen privacy on public dashboards."""
    if not raw_phone or len(raw_phone.strip()) < 4:
        return "+91-XXXXX-XXXX"
    digits = "".join(filter(str.isdigit, raw_phone))
    last4 = digits[-4:] if len(digits) >= 4 else "0000"
    return f"+91-XXXXX-{last4}"

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
def book_lawyer_direct(payload: DirectBookingRequest):
    """
    Direct consultation booking for citizen frontend:
    Uses the consolidated create_booking_in_db engine to prevent drift.
    """
    try:
        booking = create_booking_in_db(
            lawyer_id=payload.lawyer_id,
            client_name=payload.client_name,
            client_phone=payload.client_phone,
            case_category=payload.case_category,
            notes=payload.notes
        )
        return DirectBookingResponse(
            booking_id=booking["booking_id"],
            lawyer_id=booking["lawyer_id"],
            lawyer_name=booking["lawyer_name"],
            total_fee=booking["total_fee"],
            payment_status=booking["payment_status"],
            current_milestone=1,
            milestone_schedule=booking["milestone_schedule"],
            message="Consultation and 4 smart milestones booked and persisted in SQL database."
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Booking failed: {str(e)}")

@router.get("/bookings", response_model=List[DirectBookingRecord], summary="List persisted bookings scoped to client")
def list_persisted_bookings(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns genuine persisted bookings scoped to the authenticated user."""
    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.user_id
    ).order_by(models.Booking.booking_id.desc()).all()
    results = []
    for b in bookings:
        results.append(DirectBookingRecord(
            booking_id=b.booking_id,
            lawyer_id=b.lawyer_id,
            lawyer_name=b.lawyer.full_name if b.lawyer else "Assigned Advocate",
            client_name=b.user.full_name if b.user else "Citizen",
            client_phone=mask_phone_number(b.user.phone if b.user else None),
            case_category=b.case_category.value if hasattr(b.case_category, "value") else str(b.case_category),
            total_fee=float(b.total_agreed_fee),
            payment_status="Pending",
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
