"""
Marketplace Test Suite (Person 2 - Backend & DB)
Tests multi-filter lawyer queries, category fee benchmarks,
RAG recommendation engine, 4-stage milestone fee calculations,
JWT authentication, protected route guards, and sub-30ms API latency.
"""

import time
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models

client = TestClient(app)

def test_placeholder_scaffold():
    """Verify test runner environment is properly recognized."""
    assert True

def test_milestone_percentages_sum_to_100():
    """Verify that milestone percentages exactly total 100%."""
    stages = [Decimal("15.00"), Decimal("25.00"), Decimal("30.00"), Decimal("30.00")]
    assert sum(stages) == Decimal("100.00")

def test_milestone_fee_split_precision():
    """Verify DECIMAL(10,2) rounding consistency without floating point drift."""
    total_fee = Decimal("50000.00")
    s1 = Decimal(str(round(total_fee * Decimal("0.15"), 2)))
    s2 = Decimal(str(round(total_fee * Decimal("0.25"), 2)))
    s3 = Decimal(str(round(total_fee * Decimal("0.30"), 2)))
    s4 = Decimal(str(round(total_fee * Decimal("0.30"), 2)))

    assert s1 == Decimal("7500.00")
    assert s2 == Decimal("12500.00")
    assert s3 == Decimal("15000.00")
    assert s4 == Decimal("15000.00")
    assert s1 + s2 + s3 + s4 == total_fee

def test_seeded_lawyer_counts_and_types():
    """Verify 30 seeded lawyers exist in database with 10 in each category."""
    db = SessionLocal()
    try:
        civil = db.query(models.Lawyer).filter(models.Lawyer.category == models.CaseCategory.Civil).count()
        consumer = db.query(models.Lawyer).filter(models.Lawyer.category == models.CaseCategory.Consumer).count()
        criminal = db.query(models.Lawyer).filter(models.Lawyer.category == models.CaseCategory.Criminal).count()
        total = db.query(models.Lawyer).count()

        assert civil == 10, f"Expected 10 Civil lawyers, found {civil}"
        assert consumer == 10, f"Expected 10 Consumer lawyers, found {consumer}"
        assert criminal == 10, f"Expected 10 Criminal lawyers, found {criminal}"
        assert total == 30, f"Expected 30 total lawyers, found {total}"

        first_lawyer = db.query(models.Lawyer).first()
        assert isinstance(first_lawyer.consultation_fee, Decimal)
        assert isinstance(first_lawyer.full_case_estimate, Decimal)
        assert first_lawyer.bar_council_id is not None
        assert "@" in first_lawyer.email
    finally:
        db.close()

# ================= STEP 3 API TESTS =================

def test_root_health_check():
    """Verify GET / returns healthy status on Port 8000."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["port"] == 8000

def test_list_all_lawyers():
    """Verify GET /api/v1/lawyers returns all 30 seeded lawyers by default."""
    response = client.get("/api/v1/lawyers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 30
    assert "full_name" in data[0]
    assert "bar_council_id" in data[0]

def test_filter_by_category():
    """Verify filtering by Civil, Consumer, and Criminal categories."""
    for cat in ["Civil", "Consumer", "Criminal"]:
        response = client.get(f"/api/v1/lawyers?category={cat}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        assert all(lawyer["category"] == cat for lawyer in data)

def test_filter_by_max_budget():
    """Verify filtering lawyers within a specific budget ceiling."""
    max_budget = 50000
    response = client.get(f"/api/v1/lawyers?max_budget={max_budget}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(Decimal(str(l["full_case_estimate"])) <= Decimal(str(max_budget)) for l in data)

def test_filter_by_city_and_language():
    """Verify case-insensitive city and language substring matching."""
    res_city = client.get("/api/v1/lawyers?city=bengaluru")
    assert res_city.status_code == 200
    city_data = res_city.json()
    assert len(city_data) > 0
    assert all("bengaluru" in l["city"].lower() for l in city_data)

    res_lang = client.get("/api/v1/lawyers?language=kannada")
    assert res_lang.status_code == 200
    lang_data = res_lang.json()
    assert len(lang_data) > 0
    assert all("kannada" in l["languages"].lower() for l in lang_data)

def test_sorting_endpoints():
    """Verify sorting by fee_asc, fee_desc, and experience_desc."""
    res_asc = client.get("/api/v1/lawyers?sort_by=fee_asc")
    assert res_asc.status_code == 200
    fees_asc = [Decimal(str(l["full_case_estimate"])) for l in res_asc.json()]
    assert fees_asc == sorted(fees_asc)

    res_desc = client.get("/api/v1/lawyers?sort_by=fee_desc")
    assert res_desc.status_code == 200
    fees_desc = [Decimal(str(l["full_case_estimate"])) for l in res_desc.json()]
    assert fees_desc == sorted(fees_desc, reverse=True)

    res_exp = client.get("/api/v1/lawyers?sort_by=experience_desc")
    assert res_exp.status_code == 200
    exp = [l["experience_years"] for l in res_exp.json()]
    assert exp == sorted(exp, reverse=True)

def test_single_lawyer_profile_with_fee_comparison_badge():
    """
    Verify GET /api/v1/lawyers/{lawyer_id} returns the profile with
    category_average_fee and automated comparison badge.
    """
    response = client.get("/api/v1/lawyers/1")
    assert response.status_code == 200
    data = response.json()

    assert data["lawyer_id"] == 1
    assert "category_average_fee" in data
    assert "fee_comparison_badge" in data
    assert Decimal(str(data["category_average_fee"])) > 0
    assert "Average" in data["fee_comparison_badge"]

def test_single_lawyer_not_found():
    """Verify HTTP 404 for invalid lawyer_id."""
    response = client.get("/api/v1/lawyers/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_rag_recommendation_endpoint():
    """
    Verify POST /api/v1/lawyers/recommend returns top 3 matching lawyers
    for Person 3's RAG service.
    """
    payload = {
        "recommended_case_category": "Civil",
        "urgency_level": "High",
        "max_budget": 80000.00
    }
    response = client.post("/api/v1/lawyers/recommend", json=payload)
    assert response.status_code == 200
    recommendations = response.json()

    assert len(recommendations) <= 3
    assert len(recommendations) > 0
    assert all(l["category"] == "Civil" for l in recommendations)
    assert all(Decimal(str(l["full_case_estimate"])) <= Decimal("80000.00") for l in recommendations)

def test_sub_30ms_latency_benchmark():
    """Verify endpoint response latency is well under 30ms."""
    client.get("/api/v1/lawyers?category=Civil")
    latencies = []
    for _ in range(5):
        t0 = time.perf_counter()
        res = client.get("/api/v1/lawyers?category=Consumer&city=Bengaluru")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert res.status_code == 200
        latencies.append(elapsed_ms)

    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 30.0, f"Average latency {avg_latency:.2f}ms exceeds 30ms budget"

# ================= STEP 5 AUTHENTICATION TESTS =================

def test_unauthenticated_protected_routes_return_401():
    """Verify that unauthenticated requests to protected booking routes return HTTP 401."""
    # POST /api/v1/bookings without token
    res_post = client.post("/api/v1/bookings", json={
        "user_id": 1,
        "lawyer_id": 1,
        "case_category": "Civil",
        "case_summary": "Unauthenticated booking attempt."
    })
    assert res_post.status_code == 401
    assert "Not authenticated" in res_post.json()["detail"] or "credentials" in res_post.json()["detail"].lower()

    # GET /api/v1/bookings without token
    res_get = client.get("/api/v1/bookings")
    assert res_get.status_code == 401

    # GET /api/v1/bookings/user/1 without token
    res_user = client.get("/api/v1/bookings/user/1")
    assert res_user.status_code == 401

    # PATCH /api/v1/bookings/1/milestones/1 without token
    res_patch = client.patch("/api/v1/bookings/1/milestones/1", json={"status": "IN_PROGRESS"})
    assert res_patch.status_code == 401

def test_auth_register_client_and_lawyer():
    """Verify registration for both CLIENT and LAWYER roles."""
    # Register client
    client_email = f"client.test.{int(time.time())}@example.com"
    res_client = client.post("/api/v1/auth/register", json={
        "email": client_email,
        "password": "Password123!",
        "full_name": "Test Client User",
        "role": "CLIENT",
        "phone": "+91-9900112233"
    })
    assert res_client.status_code == 201
    client_data = res_client.json()
    assert client_data["email"] == client_email
    assert client_data["role"] == "CLIENT"

    # Register lawyer
    lawyer_email = f"lawyer.test.{int(time.time())}@nyayaconnect.in"
    res_lawyer = client.post("/api/v1/auth/register", json={
        "email": lawyer_email,
        "password": "Password123!",
        "full_name": "Adv. Test Lawyer",
        "role": "LAWYER",
        "phone": "+91-9988776655"
    })
    assert res_lawyer.status_code == 201
    lawyer_data = res_lawyer.json()
    assert lawyer_data["email"] == lawyer_email
    assert lawyer_data["role"] == "LAWYER"

    # Duplicate registration fails with 400
    res_dup = client.post("/api/v1/auth/register", json={
        "email": client_email,
        "password": "Password123!",
        "full_name": "Duplicate User",
        "role": "CLIENT"
    })
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["detail"].lower()

def test_auth_login_and_me_profile():
    """Verify JWT token generation on login and decoding on /api/v1/auth/me."""
    # 1. Login with JSON payload
    res_login = client.post("/api/v1/auth/login", json={
        "email": "client.rahul@example.com",
        "password": "Password123!"
    })
    assert res_login.status_code == 200
    token_data = res_login.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["role"] == "CLIENT"

    token = token_data["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # 2. Access /api/v1/auth/me
    res_me = client.get("/api/v1/auth/me", headers=auth_header)
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["email"] == "client.rahul@example.com"
    assert me_data["role"] == "CLIENT"

    # 3. Bad credentials return 401
    res_bad = client.post("/api/v1/auth/login", json={
        "email": "client.rahul@example.com",
        "password": "WrongPassword!"
    })
    assert res_bad.status_code == 401

def test_jwt_role_verification_client_and_lawyer():
    """Verify login and JWT claims for both CLIENT and LAWYER roles."""
    from auth.jwt_handler import decode_access_token

    # Client role verification
    res_client = client.post("/api/v1/auth/login", json={
        "email": "client.rahul@example.com",
        "password": "Password123!"
    })
    assert res_client.status_code == 200
    token_client = res_client.json()["access_token"]
    payload_client = decode_access_token(token_client)
    assert payload_client["sub"] == "client.rahul@example.com"
    assert payload_client["role"] == "CLIENT"

    # Lawyer role verification
    res_lawyer = client.post("/api/v1/auth/login", json={
        "email": "lawyer.rajeshwari@nyayaconnect.in",
        "password": "Password123!"
    })
    assert res_lawyer.status_code == 200
    token_lawyer = res_lawyer.json()["access_token"]
    payload_lawyer = decode_access_token(token_lawyer)
    assert payload_lawyer["sub"] == "lawyer.rajeshwari@nyayaconnect.in"
    assert payload_lawyer["role"] == "LAWYER"

def test_cors_headers_configuration():
    """Verify CORS middleware allows Person 1 (3000) and Person 3 (8001)."""
    for origin in ["http://localhost:3000", "http://localhost:8001"]:
        response = client.options(
            "/api/v1/lawyers",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert response.headers.get("access-control-allow-credentials") == "true"


# Helper function to get valid auth headers
def _get_auth_headers(email="client.rahul@example.com", password="Password123!"):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# ================= STEP 4/5 AUTHENTICATED BOOKING TESTS =================

def test_atomic_booking_creation_and_milestones():
    """
    Verify POST /api/v1/bookings atomically creates booking and 4 sequential
    milestone rows when called with valid JWT authentication.
    """
    auth_headers = _get_auth_headers()
    payload = {
        "user_id": 1,
        "lawyer_id": 1,
        "case_category": "Civil",
        "case_summary": "Dispute regarding boundary demarcation of ancestral residential property."
    }
    response = client.post("/api/v1/bookings", json=payload, headers=auth_headers)
    assert response.status_code == 201
    booking = response.json()

    assert booking["booking_id"] > 0
    assert booking["user_id"] == 1
    assert booking["lawyer_id"] == 1
    assert booking["case_category"] == "Civil"

    total_fee = Decimal(str(booking["total_agreed_fee"]))
    assert total_fee > Decimal("0")

    milestones = booking["milestones"]
    assert len(milestones) == 4

    expected_pcts = [Decimal("15.00"), Decimal("25.00"), Decimal("30.00"), Decimal("30.00")]
    for idx, m in enumerate(milestones):
        assert m["stage_no"] == idx + 1
        assert Decimal(str(m["percentage"])) == expected_pcts[idx]
        assert m["status"] == "PENDING"
        assert Decimal(str(m["amount"])) > Decimal("0")

    milestone_sum = sum(Decimal(str(m["amount"])) for m in milestones)
    assert milestone_sum == total_fee

def test_create_booking_nonexistent_user_or_lawyer():
    """Verify HTTP 404 when referencing invalid user_id or lawyer_id."""
    auth_headers = _get_auth_headers()
    res_bad_user = client.post("/api/v1/bookings", json={
        "user_id": 99999,
        "lawyer_id": 1,
        "case_category": "Civil",
        "case_summary": "Testing invalid user handling."
    }, headers=auth_headers)
    assert res_bad_user.status_code == 404
    assert "User with ID 99999 not found" in res_bad_user.json()["detail"]

    res_bad_lawyer = client.post("/api/v1/bookings", json={
        "user_id": 1,
        "lawyer_id": 99999,
        "case_category": "Civil",
        "case_summary": "Testing invalid lawyer handling."
    }, headers=auth_headers)
    assert res_bad_lawyer.status_code == 404
    assert "Lawyer with ID 99999 not found" in res_bad_lawyer.json()["detail"]

def test_get_user_bookings_and_booking_detail():
    """Verify GET /api/v1/bookings/user/{user_id} and GET /api/v1/bookings/{booking_id} with JWT auth."""
    auth_headers = _get_auth_headers()
    res_user = client.get("/api/v1/bookings/user/1", headers=auth_headers)
    assert res_user.status_code == 200
    user_bookings = res_user.json()
    assert len(user_bookings) > 0
    first_b_id = user_bookings[0]["booking_id"]

    res_detail = client.get(f"/api/v1/bookings/{first_b_id}", headers=auth_headers)
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["booking_id"] == first_b_id
    assert len(detail["milestones"]) == 4

def test_milestone_sequential_progression_and_auditing():
    """
    Verify PATCH /api/v1/bookings/{booking_id}/milestones/{stage_no} with JWT auth
    enforces sequential progression and audits timestamps.
    """
    auth_headers = _get_auth_headers()
    b_res = client.post("/api/v1/bookings", json={
        "user_id": 1,
        "lawyer_id": 2,
        "case_category": "Civil",
        "case_summary": "Tenant eviction petition for commercial property lease default."
    }, headers=auth_headers)
    assert b_res.status_code == 201
    booking_id = b_res.json()["booking_id"]

    # Skip to Stage 2 COMPLETED -> 400
    res_skip = client.patch(
        f"/api/v1/bookings/{booking_id}/milestones/2",
        json={"status": "COMPLETED"},
        headers=auth_headers
    )
    assert res_skip.status_code == 400
    assert "Sequential progression violation" in res_skip.json()["detail"]

    # Stage 1 -> IN_PROGRESS
    res_s1_prog = client.patch(
        f"/api/v1/bookings/{booking_id}/milestones/1",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers
    )
    assert res_s1_prog.status_code == 200
    assert res_s1_prog.json()["status"] == "IN_PROGRESS"

    # Stage 1 -> COMPLETED
    res_s1_comp = client.patch(
        f"/api/v1/bookings/{booking_id}/milestones/1",
        json={"status": "COMPLETED"},
        headers=auth_headers
    )
    assert res_s1_comp.status_code == 200
    data_s1 = res_s1_comp.json()
    assert data_s1["status"] == "COMPLETED"
    assert data_s1["completed_at"] is not None

    # Stage 2 -> IN_PROGRESS & COMPLETED
    res_s2_prog = client.patch(
        f"/api/v1/bookings/{booking_id}/milestones/2",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers
    )
    assert res_s2_prog.status_code == 200

    res_s2_comp = client.patch(
        f"/api/v1/bookings/{booking_id}/milestones/2",
        json={"status": "COMPLETED"},
        headers=auth_headers
    )
    assert res_s2_comp.status_code == 200

    # Stage 4 cannot be completed because Stage 3 is still pending
    res_s4_bad = client.patch(
        f"/api/v1/bookings/{booking_id}/milestones/4",
        json={"status": "COMPLETED"},
        headers=auth_headers
    )
    assert res_s4_bad.status_code == 400
    assert "Sequential progression violation" in res_s4_bad.json()["detail"]

def test_atomic_rollback_on_milestone_failure(monkeypatch):
    """
    Verify that if milestone creation fails halfway, the entire transaction
    rolls back and no orphan booking rows remain in the database.
    """
    auth_headers = _get_auth_headers()
    from routers import bookings as bookings_router

    db = SessionLocal()
    initial_booking_count = db.query(models.Booking).count()
    db.close()

    invalid_milestones = [
        (1, "Stage 1", Decimal("0.15"), Decimal("15.00")),
        (2, None, Decimal("0.25"), Decimal("25.00")),
    ]
    monkeypatch.setattr(bookings_router, "MILESTONE_DEFINITIONS", invalid_milestones)

    res = client.post("/api/v1/bookings", json={
        "user_id": 1,
        "lawyer_id": 1,
        "case_category": "Civil",
        "case_summary": "Simulating database transaction crash."
    }, headers=auth_headers)
    assert res.status_code == 500

    db = SessionLocal()
    post_booking_count = db.query(models.Booking).count()
    db.close()

    assert post_booking_count == initial_booking_count, (
        f"Transaction did not roll back! Initial: {initial_booking_count}, Found: {post_booking_count}"
    )
