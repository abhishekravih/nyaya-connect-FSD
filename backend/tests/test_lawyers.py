"""
Unit & Integration Tests for SQL-Backed Lawyer Marketplace & Bookings
File: backend/tests/test_lawyers.py
"""

import pytest
from backend.database import (
    get_lawyers_by_category_db,
    create_booking_in_db,
    get_all_bookings_from_db,
    get_engine
)

def test_database_initialization_and_lawyer_retrieval():
    get_engine()
    lawyers = get_lawyers_by_category_db("Consumer")
    assert len(lawyers) > 0

    # Ensure sorted by consultation fee ascending
    fees = [l["consultation_fee"] for l in lawyers]
    assert fees == sorted(fees)

    # Ensure verified flag is true
    for l in lawyers:
        assert l["verified"] is True

def test_booking_persistence_in_sql():
    # 1. Retrieve a verified lawyer
    consumer_lawyers = get_lawyers_by_category_db("Consumer")
    target_lawyer = consumer_lawyers[0]

    # 2. Persist booking
    booking = create_booking_in_db(
        lawyer_id=target_lawyer["id"],
        client_name="Test Citizen",
        client_phone="+91-9988776655",
        case_category="Consumer",
        notes="Defective refrigerator not replaced by manufacturer."
    )

    # Check returned fields
    assert "booking_id" in booking
    assert booking["booking_id"] > 0
    assert booking["lawyer_name"] == target_lawyer["name"]
    # Fee must match official lawyer fee from database
    assert booking["total_fee"] == target_lawyer["consultation_fee"]
    assert len(booking["milestone_schedule"]) == 4

    # 3. Retrieve all bookings and confirm this booking exists
    all_bookings = get_all_bookings_from_db()
    matching = [b for b in all_bookings if b["booking_id"] == booking["booking_id"]]
    assert len(matching) == 1
    assert matching[0]["client_name"] == "Test Citizen"

def test_booking_invalid_lawyer_fails():
    with pytest.raises(ValueError) as exc_info:
        create_booking_in_db(
            lawyer_id=99999,
            client_name="Unknown",
            client_phone="+91-1111111111",
            case_category="Consumer"
        )
    assert "not found" in str(exc_info.value).lower()
