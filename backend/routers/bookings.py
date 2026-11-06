from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field

from database import get_db, create_booking_in_db
import models
import schemas
from auth.jwt_handler import get_current_user, decode_access_token

router = APIRouter(prefix="/api/v1/bookings", tags=["Smart Milestone Bookings"])

class UnifiedBookingCreate(BaseModel):
    lawyer_id: int = Field(..., description="ID of lawyer to book")
    case_category: Optional[str] = Field("Consumer", description="Civil, Consumer, or Criminal")
    case_summary: Optional[str] = Field(None, description="Detailed case notes")
    issue_summary: Optional[str] = Field(None, description="Frontend alias for case notes")
    total_fee: Optional[Decimal] = Field(None, description="Optional fee override")
    client_name: Optional[str] = Field("Citizen Client", description="Client name")
    client_phone: Optional[str] = Field("+91-9876543210", description="Client phone number")
    user_id: Optional[int] = Field(None, description="Optional authenticated user ID")

class MilestoneUpdatePayload(BaseModel):
    status: str = Field(..., description="Target status ('COMPLETED', 'IN_PROGRESS', 'PENDING')")

def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """Extracts authenticated user if Bearer token is provided, else returns None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if email:
            return db.query(models.User).filter(models.User.email == email).first()
    except Exception:
        pass
    return None

@router.post("", status_code=status.HTTP_201_CREATED, summary="Create booking with atomic 4-stage milestones")
@router.post("/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_booking_endpoint(
    payload: UnifiedBookingCreate,
    optional_user: Optional[models.User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Consolidated single booking creation path:
    - Atomically creates booking and 4 linked CaseMilestones (15%, 25%, 30%, 30%).
    - Sets Milestone 1 to IN_PROGRESS, others PENDING.
    - Sets payment_status to honest 'Pending'.
    - Returns JWT access token for scoped dashboard access.
    """
    summary = payload.issue_summary or payload.case_summary or f"Consultation for {payload.case_category} case"
    user_id = optional_user.user_id if optional_user else payload.user_id
    client_name = optional_user.full_name if optional_user else (payload.client_name or "Citizen Client")
    client_phone = optional_user.phone if optional_user else (payload.client_phone or "+91-9876543210")

    try:
        result = create_booking_in_db(
            lawyer_id=payload.lawyer_id,
            client_name=client_name,
            client_phone=client_phone,
            case_category=payload.case_category or "Consumer",
            notes=summary,
            total_fee_override=payload.total_fee,
            user_id=user_id
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Booking creation failed: {str(e)}")

@router.get("", summary="List bookings scoped to authenticated user")
@router.get("/", include_in_schema=False)
def list_user_bookings(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns bookings belonging exclusively to the authenticated user.
    Prevents public exposure of client data.
    """
    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.user_id
    ).order_by(models.Booking.booking_id.desc()).all()

    results = []
    for b in bookings:
        results.append({
            "booking_id": b.booking_id,
            "user_id": b.user_id,
            "lawyer_id": b.lawyer_id,
            "lawyer_name": b.lawyer.full_name if b.lawyer else "Assigned Advocate",
            "category": b.case_category.value if hasattr(b.case_category, "value") else str(b.case_category),
            "issue_summary": b.case_summary,
            "total_fee": float(b.total_agreed_fee),
            "status": "pending",
            "payment_status": "Pending",
            "created_at": str(b.created_at) if b.created_at else datetime.now(timezone.utc).isoformat(),
            "lawyer": {
                "lawyer_id": b.lawyer.lawyer_id if b.lawyer else b.lawyer_id,
                "full_name": b.lawyer.full_name if b.lawyer else "Assigned Advocate",
                "category": b.lawyer.category.value if b.lawyer and hasattr(b.lawyer.category, "value") else str(b.case_category),
                "city": b.lawyer.city if b.lawyer else "Bengaluru",
                "phone": b.lawyer.phone if b.lawyer else "",
                "email": b.lawyer.email if b.lawyer else "",
                "total_case_estimate": float(b.total_agreed_fee)
            },
            "milestones": [
                {
                    "stage_number": m.stage_number,
                    "name": m.stage_name,
                    "percentage": float(m.percentage),
                    "amount": float(m.amount),
                    "status": "Completed" if m.status == models.MilestoneStatus.COMPLETED else (
                        "In Progress" if m.status == models.MilestoneStatus.IN_PROGRESS else "Locked"
                    )
                } for m in b.milestones
            ]
        })
    return results

@router.get("/{booking_id}", summary="Get single booking with privacy check")
def get_booking_by_id(
    booking_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches a single booking, strictly ensuring the user is the owner."""
    booking = db.query(models.Booking).filter(models.Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking {booking_id} not found.")

    if booking.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view this booking."
        )

    return {
        "booking_id": booking.booking_id,
        "user_id": booking.user_id,
        "lawyer_id": booking.lawyer_id,
        "lawyer_name": booking.lawyer.full_name if booking.lawyer else "Assigned Advocate",
        "category": booking.case_category.value,
        "issue_summary": booking.case_summary,
        "total_fee": float(booking.total_agreed_fee),
        "status": "pending",
        "milestones": [
            {
                "stage_number": m.stage_number,
                "name": m.stage_name,
                "percentage": float(m.percentage),
                "amount": float(m.amount),
                "status": "Completed" if m.status == models.MilestoneStatus.COMPLETED else (
                    "In Progress" if m.status == models.MilestoneStatus.IN_PROGRESS else "Locked"
                )
            } for m in booking.milestones
        ]
    }

@router.patch("/{booking_id}/milestones/{stage_no}", summary="Update milestone status with ownership & sequential check")
def update_milestone_endpoint(
    booking_id: int,
    stage_no: int,
    payload: MilestoneUpdatePayload,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates milestone status.
    - Checks ownership: only booking owner can update.
    - Handles 0-based and 1-based index safely.
    - Normalizes status ('Completed' -> COMPLETED).
    - Enforces sequential progression.
    """
    actual_stage = stage_no if stage_no in [1, 2, 3, 4] else (stage_no + 1 if stage_no in [0, 1, 2, 3] else stage_no)
    if actual_stage not in [1, 2, 3, 4]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid milestone stage. Must be 1 to 4.")

    booking = db.query(models.Booking).filter(models.Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking {booking_id} not found.")

    if booking.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to modify this booking's milestones."
        )

    # Normalize status string to MilestoneStatus Enum
    raw_status = payload.status.upper().replace(" ", "_")
    if raw_status in ["COMPLETED", "COMPLETE", "DONE"]:
        target_status = models.MilestoneStatus.COMPLETED
    elif raw_status in ["IN_PROGRESS", "PROGRESS", "ACTIVE"]:
        target_status = models.MilestoneStatus.IN_PROGRESS
    elif raw_status in ["PENDING", "LOCKED"]:
        target_status = models.MilestoneStatus.PENDING
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid milestone status '{payload.status}'.")

    milestone = db.query(models.CaseMilestone).filter(
        models.CaseMilestone.booking_id == booking_id,
        models.CaseMilestone.stage_number == actual_stage
    ).first()

    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Stage {actual_stage} not found.")

    # Enforce sequential progression
    if target_status in [models.MilestoneStatus.IN_PROGRESS, models.MilestoneStatus.COMPLETED]:
        if actual_stage > 1:
            earlier = db.query(models.CaseMilestone).filter(
                models.CaseMilestone.booking_id == booking_id,
                models.CaseMilestone.stage_number < actual_stage
            ).all()
            for e in earlier:
                if e.status != models.MilestoneStatus.COMPLETED:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Sequential progression: Stage {actual_stage} requires Stage {e.stage_number} to be COMPLETED first."
                    )

    now_utc = datetime.now(timezone.utc)
    milestone.status = target_status
    milestone.updated_at = now_utc
    if target_status == models.MilestoneStatus.COMPLETED:
        milestone.completed_at = now_utc

        # Automatically advance next milestone to IN_PROGRESS if next stage exists
        if actual_stage < 4:
            next_ms = db.query(models.CaseMilestone).filter(
                models.CaseMilestone.booking_id == booking_id,
                models.CaseMilestone.stage_number == actual_stage + 1
            ).first()
            if next_ms and next_ms.status == models.MilestoneStatus.PENDING:
                next_ms.status = models.MilestoneStatus.IN_PROGRESS
                next_ms.updated_at = now_utc

    db.commit()
    db.refresh(milestone)

    return {
        "booking_id": booking_id,
        "stage_number": actual_stage,
        "stage_name": milestone.stage_name,
        "status": milestone.status.value,
        "completed_at": str(milestone.completed_at) if milestone.completed_at else None
    }
