"""
Step 5 Verification Script (Person 2 - Backend & DB)
Validates JWT Authentication & Role-Based Protected Routes:
1. User registration supporting 'CLIENT' and 'LAWYER' roles
2. JWT token generation via POST /api/v1/auth/login
3. User profile verification via GET /api/v1/auth/me
4. Rejection of unauthenticated requests to protected booking routes (HTTP 401)
5. Successful authorized booking creation with Bearer token
"""

import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_step5_verification():
    print("=" * 80)
    print("NyayaConnect STEP 5 VERIFICATION: JWT Authentication & Route Guards")
    print("=" * 80)

    # 1. Register Client and Lawyer
    print("\n[1/5] Testing User Registration (/api/v1/auth/register):")
    timestamp = int(time.time())
    client_reg = client.post("/api/v1/auth/register", json={
        "email": f"client_{timestamp}@example.com",
        "password": "Password123!",
        "full_name": "Siddharth Rao",
        "role": "CLIENT",
        "phone": "+91-9876500001"
    })
    assert client_reg.status_code == 201
    print(f"  -> Client Registered: {client_reg.json()['email']} (Role: {client_reg.json()['role']})")

    lawyer_reg = client.post("/api/v1/auth/register", json={
        "email": f"lawyer_{timestamp}@nyayaconnect.in",
        "password": "Password123!",
        "full_name": "Adv. Siddharth Rao",
        "role": "LAWYER",
        "phone": "+91-9876500002"
    })
    assert lawyer_reg.status_code == 201
    print(f"  -> Lawyer Registered: {lawyer_reg.json()['email']} (Role: {lawyer_reg.json()['role']})")

    # 2. Login & JWT Bearer Token Generation
    print("\n[2/5] Testing User Login & JWT Token Generation (/api/v1/auth/login):")
    login_res = client.post("/api/v1/auth/login", json={
        "email": f"client_{timestamp}@example.com",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    token = token_data["access_token"]
    print(f"  -> Login Successful for: {token_data['email']}")
    print(f"  -> Token Type:           {token_data['token_type']}")
    print(f"  -> User Role:             {token_data['role']}")
    print(f"  -> JWT Access Token:     {token[:35]}...[TRUNCATED]")

    # 3. Authenticated Me Profile
    print("\n[3/5] Testing Authenticated Profile Retrieval (/api/v1/auth/me):")
    auth_headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    print(f"  -> Verified Token Decoded: {me_res.json()['full_name']} ({me_res.json()['email']})")

    # 4. Security Guardrail: Reject Unauthenticated Requests
    print("\n[4/5] Testing Security Guard on Protected Routes without Token:")
    unauth_booking = client.post("/api/v1/bookings", json={
        "user_id": 1,
        "lawyer_id": 1,
        "case_category": "Civil",
        "case_summary": "Attempting unauthenticated booking creation."
    })
    print(f"  -> Unauthenticated POST /api/v1/bookings:")
    print(f"     Status Code: {unauth_booking.status_code} (Expected: 401 Unauthorized)")
    print(f"     Detail:      '{unauth_booking.json()['detail']}'")
    assert unauth_booking.status_code == 401

    unauth_get = client.get("/api/v1/bookings")
    print(f"  -> Unauthenticated GET /api/v1/bookings:")
    print(f"     Status Code: {unauth_get.status_code} (Expected: 401 Unauthorized)")
    assert unauth_get.status_code == 401

    # 5. Authorized Booking with Bearer Token
    print("\n[5/5] Testing Authorized Booking with Valid Bearer Token:")
    auth_booking = client.post("/api/v1/bookings", json={
        "user_id": me_res.json()["user_id"],
        "lawyer_id": 1,
        "case_category": "Civil",
        "case_summary": "Authorized legal consultation for property title clearance."
    }, headers=auth_headers)
    assert auth_booking.status_code == 201
    booking_data = auth_booking.json()
    print(f"  -> Booking #{booking_data['booking_id']} successfully created!")
    print(f"  -> Linked Milestones Generated: {len(booking_data['milestones'])} stages")

    print("\n" + "=" * 80)
    print("[SUCCESS] All Step 5 JWT Authentication & Route Guard requirements PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    run_step5_verification()
