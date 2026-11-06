"""
Unit & Integration Tests for SQL-Backed Lawyer Marketplace & Bookings
File: backend/tests/test_lawyers.py
"""

import pytest
import asyncio
from decimal import Decimal
from fastapi.testclient import TestClient
from database import (
    get_lawyers_by_category_db,
    create_booking_in_db,
    get_all_bookings_from_db,
    get_engine,
    check_db_health,
    SessionLocal
)
import models
from main import app

client = TestClient(app)

def test_database_engine_and_health():
    """Verify get_engine() works without arguments and health check executes truthfully."""
    eng = get_engine()
    assert eng is not None
    healthy, msg = check_db_health()
    assert healthy is True
    assert "reachable" in msg.lower()

@pytest.mark.asyncio
async def test_database_lawyer_retrieval_async():
    """Verify async lawyer retrieval returns truthful records without fabricated fields."""
    lawyers = await get_lawyers_by_category_db("Consumer")
    assert len(lawyers) > 0

    # Ensure sorted by affordability
    fees = [l["full_case_estimate"] for l in lawyers]
    assert fees == sorted(fees)

    # Validate truthful fields from models.Lawyer
    for l in lawyers:
        assert l["rating"] >= 4.0
        assert l["consultation_fee"] > 0
        assert l["full_case_estimate"] > 0
        assert len(l["milestones"]) == 4
        # Verify no ungrounded claims are present
        assert "verified" not in l
        assert "reviews_count" not in l

def test_booking_persistence_helper():
    """Verify create_booking_in_db creates booking and 4 atomic milestones in SQL."""
    db = SessionLocal()
    try:
        lawyer = db.query(models.Lawyer).filter(models.Lawyer.category == models.CaseCategory.Consumer).first()
        assert lawyer is not None, "Seeded lawyer must exist"
        lawyer_id = lawyer.lawyer_id
        consultation_fee = float(lawyer.consultation_fee)
    finally:
        db.close()

    # Persist booking through helper
    booking = create_booking_in_db(
        lawyer_id=lawyer_id,
        client_name="Test Citizen",
        client_phone="+91-9988776655",
        case_category="Consumer",
        notes="Defective appliance compensation claim"
    )

    assert "booking_id" in booking
    assert booking["booking_id"] > 0
    assert booking["lawyer_id"] == lawyer_id
    assert booking["total_fee"] == consultation_fee
    assert len(booking["milestone_schedule"]) == 4

    # Verify retrieval
    all_bookings = get_all_bookings_from_db()
    matching = [b for b in all_bookings if b["booking_id"] == booking["booking_id"]]
    assert len(matching) == 1
    assert matching[0]["client_name"] == "Test Citizen"

def test_booking_invalid_lawyer_fails():
    """Verify booking with nonexistent lawyer raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        create_booking_in_db(
            lawyer_id=999999,
            client_name="Unknown",
            client_phone="+91-1111111111",
            case_category="Consumer"
        )
    assert "not found" in str(exc_info.value).lower()

def test_direct_booking_api_endpoint():
    """Verify POST /api/v1/lawyers/book endpoint creates booking, returns ID, and masks phone."""
    db = SessionLocal()
    try:
        lawyer = db.query(models.Lawyer).first()
        assert lawyer is not None
        target_lawyer_id = lawyer.lawyer_id
    finally:
        db.close()

    res = client.post("/api/v1/lawyers/book", json={
        "lawyer_id": target_lawyer_id,
        "client_name": "Priya Sharma",
        "client_phone": "+91-9876543210",
        "case_category": "Consumer",
        "notes": "E-commerce refund dispute"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["booking_id"] > 0
    assert len(data["milestone_schedule"]) == 4

    # Check that GET /api/v1/lawyers/bookings returns masked phone number for privacy
    b_res = client.get("/api/v1/lawyers/bookings")
    assert b_res.status_code == 200
    bookings = b_res.json()
    matching = [b for b in bookings if b["booking_id"] == data["booking_id"]]
    assert len(matching) == 1
    assert "XXXXX" in matching[0]["client_phone"]
    assert "9876543210" not in matching[0]["client_phone"]
