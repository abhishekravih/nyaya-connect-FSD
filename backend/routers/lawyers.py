"""
NyayaConnect Marketplace Backend Router (Person 2 & Person 4 Integration)
File: /backend/routers/lawyers.py
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/lawyers", tags=["Lawyer Marketplace"])

class LawyerItem(BaseModel):
    id: int
    name: str
    specialization: str
    bar_council_id: str
    experience_years: int
    consultation_fee: float
    rating: float
    reviews_count: int
    verified: bool
    languages_spoken: List[str]
    location: str
    milestones: List[str]

class BookingRequest(BaseModel):
    lawyer_id: int
    client_name: str
    client_phone: str
    case_category: str
    notes: Optional[str] = None

class BookingResponse(BaseModel):
    booking_id: int
    lawyer_id: int
    status: str
    message: str
    milestone_schedule: List[str]

# In-memory booking records for persistence verification
ACTIVE_BOOKINGS = []

@router.get("", response_model=List[LawyerItem])
async def list_lawyers(category: Optional[str] = Query(None, description="Filter by Civil, Consumer, Criminal")):
    from backend.routers.orchestrator import query_marketplace_lawyers, FALLBACK_LAWYERS_BY_CATEGORY
    if category:
        lawyers = await query_marketplace_lawyers(category.capitalize())
    else:
        all_l = []
        for cat_list in FALLBACK_LAWYERS_BY_CATEGORY.values():
            all_l.extend(cat_list)
        lawyers = all_l
    return [LawyerItem(**l) for l in lawyers]

@router.post("/book", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def book_lawyer(booking: BookingRequest):
    """Books a verified lawyer with upfront fee cards & 4 smart milestones."""
    booking_id = len(ACTIVE_BOOKINGS) + 1
    record = {
        "id": booking_id,
        "lawyer_id": booking.lawyer_id,
        "client_name": booking.client_name,
        "client_phone": booking.client_phone,
        "category": booking.case_category,
        "status": "Confirmed_Escrow_Hold",
        "current_milestone": 1
    }
    ACTIVE_BOOKINGS.append(record)
    
    milestones = [
        "Milestone 1: Preliminary Case Review & Evidence Audit",
        "Milestone 2: Statutory Legal Notice & Registry Service",
        "Milestone 3: Tribunal / District Commission Filing",
        "Milestone 4: Arguments, Settlement & Decree Recovery"
    ]

    return BookingResponse(
        booking_id=booking_id,
        lawyer_id=booking.lawyer_id,
        status="Confirmed",
        message="Consultation booked successfully with smart escrow milestones.",
        milestone_schedule=milestones
    )
