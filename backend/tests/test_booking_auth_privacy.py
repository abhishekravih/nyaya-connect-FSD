"""
Integration Tests for Booking Authorization, Scoped Privacy, and Milestone Progression
Verifies:
1. Booking creation returns a valid JWT access token and initializes Stage 1 to IN_PROGRESS.
2. Unauthenticated GET /api/v1/bookings returns HTTP 401 Unauthorized (zero public data leakage).
3. Authenticated client sees ONLY their own bookings.
4. Client B cannot view or tamper with Client A's booking or milestones (HTTP 403 Forbidden).
5. Milestone progression follows strict sequential ordering.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from auth.jwt_handler import create_access_token

client = TestClient(app)

def test_unauthenticated_bookings_request_fails_401():
    """Verify that calling GET /api/v1/bookings without Bearer token rejects with HTTP 401."""
    res = client.get("/api/v1/bookings")
    assert res.status_code == 401
    assert "not authenticated" in res.json()["detail"].lower() or "credentials" in res.json()["detail"].lower()

def test_booking_creation_returns_token_and_sets_stage_1_in_progress():
    """Verify booking creation returns access_token and initializes stage 1 to IN_PROGRESS."""
    create_res = client.post("/api/v1/bookings", json={
        "lawyer_id": 1,
        "case_category": "Civil",
        "issue_summary": "Tenant security deposit recovery",
        "client_name": "Alice Sharma",
        "client_phone": "+91-9988112233"
    })
    assert create_res.status_code == 201
    data = create_res.json()
    assert "access_token" in data
    assert data["booking_id"] > 0
    assert data["payment_status"] == "Pending"

    # Verify milestones: Stage 1 IN_PROGRESS, others PENDING
    milestones = data["milestones"]
    assert len(milestones) == 4
    assert milestones[0]["stage_number"] == 1
    assert milestones[0]["status"] == "IN_PROGRESS"
    assert milestones[1]["status"] == "PENDING"
    assert milestones[2]["status"] == "PENDING"
    assert milestones[3]["status"] == "PENDING"

    alice_token = data["access_token"]

    # Verify Alice can list her booking
    alice_res = client.get("/api/v1/bookings", headers={"Authorization": f"Bearer {alice_token}"})
    assert alice_res.status_code == 200
    alice_bookings = alice_res.json()
    assert len(alice_bookings) >= 1
    assert alice_bookings[0]["booking_id"] == data["booking_id"]

def test_privacy_user_b_cannot_access_or_modify_user_a_booking():
    """Verify that User B cannot view or modify milestones of a booking owned by User A (HTTP 403)."""
    # 1. Create booking for Client A
    res_a = client.post("/api/v1/bookings", json={
        "lawyer_id": 1,
        "case_category": "Consumer",
        "issue_summary": "Defective electronics dispute",
        "client_name": "Client A",
        "client_phone": "+91-9111111111"
    })
    assert res_a.status_code == 201
    booking_a_id = res_a.json()["booking_id"]
    token_a = res_a.json()["access_token"]

    # 2. Create booking for Client B
    res_b = client.post("/api/v1/bookings", json={
        "lawyer_id": 2,
        "case_category": "Criminal",
        "issue_summary": "Bail matter",
        "client_name": "Client B",
        "client_phone": "+91-9222222222"
    })
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]

    # 3. Client B attempts to fetch Client A's booking by ID -> HTTP 403 Forbidden
    hack_res = client.get(f"/api/v1/bookings/{booking_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert hack_res.status_code == 403
    assert "forbidden" in hack_res.json()["detail"].lower()

    # 4. Client B attempts to update Client A's milestone -> HTTP 403 Forbidden
    tamper_res = client.patch(
        f"/api/v1/bookings/{booking_a_id}/milestones/1",
        json={"status": "COMPLETED"},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert tamper_res.status_code == 403
    assert "forbidden" in tamper_res.json()["detail"].lower()

def test_sequential_milestone_progression():
    """Verify milestones must advance in sequential order: Stage 2 cannot complete before Stage 1."""
    # 1. Create booking
    res = client.post("/api/v1/bookings", json={
        "lawyer_id": 1,
        "case_category": "Civil",
        "issue_summary": "Contractual dispute",
        "client_name": "Sequential Test User",
        "client_phone": "+91-9333333333"
    })
    assert res.status_code == 201
    booking_id = res.json()["booking_id"]
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Attempt to mark Stage 2 COMPLETED while Stage 1 is not completed -> HTTP 400 Bad Request
    invalid_res = client.patch(
        f"/api/v1/bookings/{booking_id}/milestones/2",
        json={"status": "COMPLETED"},
        headers=headers
    )
    assert invalid_res.status_code == 400
    assert "sequential progression" in invalid_res.json()["detail"].lower()

    # 3. Mark Stage 1 COMPLETED -> Success and automatically advances Stage 2 to IN_PROGRESS
    valid_res = client.patch(
        f"/api/v1/bookings/{booking_id}/milestones/1",
        json={"status": "COMPLETED"},
        headers=headers
    )
    assert valid_res.status_code == 200
    assert valid_res.json()["status"] == "COMPLETED"

    # 4. Now Stage 2 can be marked COMPLETED
    stage_2_res = client.patch(
        f"/api/v1/bookings/{booking_id}/milestones/2",
        json={"status": "COMPLETED"},
        headers=headers
    )
    assert stage_2_res.status_code == 200
    assert stage_2_res.json()["status"] == "COMPLETED"
