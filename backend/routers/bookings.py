from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from decimal import Decimal
from database import get_db
import models
import schemas
from auth.jwt_handler import get_current_user

router = APIRouter(prefix="/api/v1/bookings", tags=["Smart Milestone Bookings"])

MILESTONE_DEFINITIONS = [
    (1, "Stage 1: Initial Consultation", Decimal("0.15"), Decimal("15.00")),
    (2, "Stage 2: Notice/Drafting", Decimal("0.25"), Decimal("25.00")),
    (3, "Stage 3: Filing & First Hearing", Decimal("0.30"), Decimal("30.00")),
    (4, "Stage 4: Final Arguments", Decimal("0.30"), Decimal("30.00")),
]

@router.post("", response_model=schemas.BookingResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=schemas.BookingResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_booking(
    booking_in: schemas.BookingCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates an atomic, race-condition-free case booking and automatically generates
    4 linked milestone rows with exact DECIMAL(10,2) fee splits (15%, 25%, 30%, 30%).
    Protected route: requires valid JWT bearer token (HTTP 401 if unauthenticated).
    """
    # 1. Target user defaults to authenticated user or validates user_id
    target_user_id = booking_in.user_id or current_user.user_id
    user = db.query(models.User).filter(models.User.user_id == target_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {target_user_id} not found"
        )

    # 2. Verify Lawyer existence
    lawyer = db.query(models.Lawyer).filter(models.Lawyer.lawyer_id == booking_in.lawyer_id).first()
    if not lawyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lawyer with ID {booking_in.lawyer_id} not found"
        )

    # 3. Exact DECIMAL(10,2) fee calculation
    total_fee = Decimal(str(lawyer.full_case_estimate))

    m1_amount = Decimal(str(round(total_fee * Decimal("0.15"), 2)))
    m2_amount = Decimal(str(round(total_fee * Decimal("0.25"), 2)))
    m3_amount = Decimal(str(round(total_fee * Decimal("0.30"), 2)))
    m4_amount = total_fee - (m1_amount + m2_amount + m3_amount)

    stage_amounts = [m1_amount, m2_amount, m3_amount, m4_amount]

    # 4. Atomic Transaction
    try:
        new_booking = models.Booking(
            user_id=target_user_id,
            lawyer_id=booking_in.lawyer_id,
            case_category=booking_in.case_category,
            case_summary=booking_in.case_summary,
            total_agreed_fee=total_fee
        )
        db.add(new_booking)
        db.flush()  # Allocates new_booking.booking_id

        # Generate 4 linked milestones
        for idx, (stage_num, name, factor, pct) in enumerate(MILESTONE_DEFINITIONS):
            milestone = models.CaseMilestone(
                booking_id=new_booking.booking_id,
                stage_number=stage_num,
                stage_name=name,
                percentage=pct,
                amount=stage_amounts[idx],
                status=models.MilestoneStatus.PENDING
            )
            db.add(milestone)

        db.commit()
        db.refresh(new_booking)
        return new_booking

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Atomic booking creation failed: {str(e)}"
        )

@router.get("", response_model=List[schemas.BookingResponse])
@router.get("/", response_model=List[schemas.BookingResponse], include_in_schema=False)
def list_bookings(
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List bookings with associated 4-stage milestones.
    Protected route: requires valid JWT bearer token.
    """
    return db.query(models.Booking).order_by(models.Booking.booking_id.desc()).offset(skip).limit(limit).all()

@router.get("/user/{user_id}", response_model=List[schemas.BookingResponse])
def get_user_bookings(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all bookings placed by a specific user with ordered 4-stage milestones
    for Person 1's /dashboard client UI.
    Protected route: requires valid JWT bearer token.
    """
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user_id
    ).order_by(models.Booking.booking_id.desc()).all()
    return bookings

@router.get("/{booking_id}", response_model=schemas.BookingResponse)
def get_booking(
    booking_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch a single booking with its 4-stage milestones.
    Protected route: requires valid JWT bearer token.
    """
    booking = db.query(models.Booking).filter(models.Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    return booking

@router.patch("/{booking_id}/milestones/{stage_no}", response_model=schemas.MilestoneResponse)
def update_milestone_stage(
    booking_id: int,
    stage_no: int,
    status_update: schemas.MilestoneStatusUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates milestone status ('PENDING' -> 'IN_PROGRESS' -> 'COMPLETED').
    Enforces sequential stage progression: later stages cannot be marked
    'IN_PROGRESS' or 'COMPLETED' while an earlier stage is still pending.
    Audits updated_at and completed_at timestamps.
    Protected route: requires valid JWT bearer token.
    """
    if stage_no not in [1, 2, 3, 4]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stage_no. Must be 1, 2, 3, or 4."
        )

    # 1. Fetch target milestone
    milestone = db.query(models.CaseMilestone).filter(
        models.CaseMilestone.booking_id == booking_id,
        models.CaseMilestone.stage_number == stage_no
    ).first()

    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Milestone stage {stage_no} for booking {booking_id} not found"
        )

    # 2. Enforce sequential progression if advancing to IN_PROGRESS or COMPLETED
    if status_update.status in (models.MilestoneStatus.IN_PROGRESS, models.MilestoneStatus.COMPLETED):
        if stage_no > 1:
            earlier_stages = db.query(models.CaseMilestone).filter(
                models.CaseMilestone.booking_id == booking_id,
                models.CaseMilestone.stage_number < stage_no
            ).order_by(models.CaseMilestone.stage_number.asc()).all()

            for earlier in earlier_stages:
                if earlier.status != models.MilestoneStatus.COMPLETED:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Sequential progression violation: Stage {stage_no} cannot be marked "
                            f"'{status_update.status.value}' because Stage {earlier.stage_number} "
                            f"({earlier.stage_name}) is still '{earlier.status.value}'."
                        )
                    )

    # 3. Apply state transition and timestamp audits
    now_utc = datetime.now(timezone.utc)
    milestone.status = status_update.status
    milestone.updated_at = now_utc

    if status_update.status == models.MilestoneStatus.COMPLETED:
        milestone.completed_at = now_utc
    elif status_update.status == models.MilestoneStatus.PENDING:
        milestone.completed_at = None

    db.commit()
    db.refresh(milestone)
    return milestone
