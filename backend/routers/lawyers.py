from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal
from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/v1/lawyers", tags=["Lawyer Directory"])

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

@router.get("/{lawyer_id}", response_model=schemas.LawyerDetailResponse)
def get_lawyer_profile(lawyer_id: int, db: Session = Depends(get_db)):
    """
    Returns full lawyer profile with category benchmark fee comparison.
    Calculates dynamic average full_case_estimate for the lawyer's category
    and generates an automated comparison badge.
    """
    lawyer = db.query(models.Lawyer).filter(models.Lawyer.lawyer_id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lawyer with ID {lawyer_id} not found"
        )

    # Calculate average full_case_estimate for this lawyer's category
    avg_fee = db.query(func.avg(models.Lawyer.full_case_estimate)).filter(
        models.Lawyer.category == lawyer.category
    ).scalar()

    if avg_fee is not None:
        category_avg = Decimal(str(round(avg_fee, 2)))
    else:
        category_avg = lawyer.full_case_estimate

    # Compute difference percentage
    if category_avg > 0:
        diff_pct = ((lawyer.full_case_estimate - category_avg) / category_avg) * Decimal("100")
        diff_val = round(abs(diff_pct), 1)

        if diff_pct < Decimal("-0.5"):
            # Normalize display (e.g. 12% or 12.5%)
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
    """
    Integration endpoint for Person 3's RAG service.
    Accepts detected legal category and urgency/budget parameters, returning the top 3
    matching verified lawyers sorted by rating and fee affordability.
    """
    query = db.query(models.Lawyer).filter(
        models.Lawyer.category == payload.recommended_case_category
    )

    if payload.max_budget is not None:
        query = query.filter(models.Lawyer.full_case_estimate <= payload.max_budget)

    # Sort by highest rating first, then lowest full_case_estimate for affordability
    return query.order_by(
        models.Lawyer.rating.desc(),
        models.Lawyer.full_case_estimate.asc()
    ).limit(3).all()
