"""
Step 4 Verification Script (Person 2 - Backend & DB)
Demonstrates the Smart Milestone Booking & Fee Engine:
1. Atomic Booking Creation & 4-Stage Milestone Generation (15%/25%/30%/30%)
2. Exact DECIMAL(10,2) mathematical precision
3. Sequential stage transition enforcement ('PENDING' -> 'IN_PROGRESS' -> 'COMPLETED')
4. User Dashboard retrieval (GET /api/v1/bookings/user/{user_id})
5. Atomic rollback protection on failure (zero orphan records)
"""

from decimal import Decimal
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models

client = TestClient(app)

def run_step4_verification():
    print("=" * 80)
    print("NyayaConnect STEP 4 VERIFICATION: Smart Milestone Booking & Fee Engine")
    print("=" * 80)

    # 1. Create Atomic Booking
    print("\n[1/5] Creating Atomic Booking via POST /api/v1/bookings...")
    payload = {
        "user_id": 1,
        "lawyer_id": 1,
        "case_category": "Civil",
        "case_summary": "Property partition deed registration and encumbrance certificate dispute."
    }
    res_booking = client.post("/api/v1/bookings", json=payload)
    assert res_booking.status_code == 201, f"Failed: {res_booking.text}"
    booking = res_booking.json()
    b_id = booking["booking_id"]
    total_fee = Decimal(str(booking["total_agreed_fee"]))

    print(f"  -> Booking ID Created: #{b_id}")
    print(f"  -> Client ID:          {booking['user_id']}")
    print(f"  -> Lawyer ID:          {booking['lawyer_id']}")
    print(f"  -> Category:           {booking['case_category']}")
    print(f"  -> Total Agreed Fee:   Rs {total_fee:,.2f}")

    # 2. Inspect 4 Linked Milestones
    print("\n[2/5] Inspecting Generated 4-Stage Milestones (15% / 25% / 30% / 30%):")
    milestones = booking["milestones"]
    assert len(milestones) == 4, f"Expected 4 milestones, got {len(milestones)}"

    sum_milestones = Decimal("0.00")
    for m in milestones:
        amount = Decimal(str(m["amount"]))
        sum_milestones += amount
        print(f"     Stage {m['stage_no']}: {m['stage_name']:<35} | {m['percentage']}% | Rs {amount:>9,.2f} | Status: {m['status']}")

    print(f"  -> Milestone Total Sum: Rs {sum_milestones:,.2f}")
    assert sum_milestones == total_fee, "Milestone sum does not equal total agreed fee!"
    print("  -> Precision Check:     100% Exact match (Zero floating-point drift)")

    # 3. Sequential Stage Progression & Guard Check
    print("\n[3/5] Testing Sequential State Machine & Guardrails:")
    # Attempt invalid skip: Stage 2 COMPLETED before Stage 1
    res_skip = client.patch(f"/api/v1/bookings/{b_id}/milestones/2", json={"status": "COMPLETED"})
    print(f"  -> Attempting Stage 2 'COMPLETED' while Stage 1 is 'PENDING':")
    print(f"     Status Code: {res_skip.status_code} (Expected: 400 Bad Request)")
    print(f"     Error Detail: '{res_skip.json()['detail']}'")
    assert res_skip.status_code == 400

    # Valid transition: Stage 1 -> IN_PROGRESS -> COMPLETED
    print("  -> Performing valid sequential progression for Stage 1:")
    res_s1_prog = client.patch(f"/api/v1/bookings/{b_id}/milestones/1", json={"status": "IN_PROGRESS"})
    assert res_s1_prog.status_code == 200
    print(f"     Stage 1 Status -> {res_s1_prog.json()['status']}")

    res_s1_comp = client.patch(f"/api/v1/bookings/{b_id}/milestones/1", json={"status": "COMPLETED"})
    assert res_s1_comp.status_code == 200
    data_s1 = res_s1_comp.json()
    print(f"     Stage 1 Status -> {data_s1['status']} | Completed At: {data_s1['completed_at']}")

    # Valid transition: Stage 2 -> IN_PROGRESS
    res_s2_prog = client.patch(f"/api/v1/bookings/{b_id}/milestones/2", json={"status": "IN_PROGRESS"})
    assert res_s2_prog.status_code == 200
    print(f"     Stage 2 Status -> {res_s2_prog.json()['status']}")

    # 4. User Dashboard Retrieval
    print("\n[4/5] Retrieving Client Bookings for Person 1 Dashboard (GET /api/v1/bookings/user/1):")
    res_user = client.get("/api/v1/bookings/user/1")
    assert res_user.status_code == 200
    user_bookings = res_user.json()
    print(f"  -> Total Bookings found for User 1: {len(user_bookings)}")
    print(f"  -> Latest Booking #{user_bookings[0]['booking_id']} with {len(user_bookings[0]['milestones'])} linked stages.")

    # 5. Atomic Rollback Verification
    print("\n[5/5] Testing Atomic Rollback on Failure:")
    from routers import bookings as bookings_router
    orig_milestones = bookings_router.MILESTONE_DEFINITIONS

    db = SessionLocal()
    initial_count = db.query(models.Booking).count()
    db.close()

    try:
        # Inject invalid definition with None as stage_name (nullable=False) to force integrity crash
        bookings_router.MILESTONE_DEFINITIONS = [
            (1, "Stage 1", Decimal("0.15"), Decimal("15.00")),
            (2, None, Decimal("0.25"), Decimal("25.00")),
        ]
        fail_res = client.post("/api/v1/bookings", json={
            "user_id": 1,
            "lawyer_id": 1,
            "case_category": "Civil",
            "case_summary": "Rollback test simulation."
        })
        assert fail_res.status_code == 500
        print("  -> Corrupted milestone creation properly triggered HTTP 500.")
    finally:
        bookings_router.MILESTONE_DEFINITIONS = orig_milestones

    db = SessionLocal()
    post_count = db.query(models.Booking).count()
    db.close()

    print(f"  -> Pre-failure Booking Count:  {initial_count}")
    print(f"  -> Post-failure Booking Count: {post_count}")
    assert initial_count == post_count, "Orphan booking record detected!"
    print("  -> Rollback Check: Clean atomic rollback verified (Zero orphan records).")

    print("\n" + "=" * 80)
    print("[SUCCESS] All Step 4 Smart Milestone Engine requirements PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    run_step4_verification()
