"""
Step 3 Verification Script (Person 2 - Backend & DB)
Demonstrates and validates all Lawyer Directory & Multi-Filter Search Endpoints,
the category fee benchmark comparison badge, the RAG recommendation endpoint,
and response latency (< 30ms).
"""

import time
from decimal import Decimal
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_step3_verification():
    print("=" * 80)
    print("NyayaConnect STEP 3 VERIFICATION: Lawyer Directory & Search APIs")
    print("=" * 80)

    # 1. Total Lawyers
    res = client.get("/api/v1/lawyers")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    all_lawyers = res.json()
    print(f"\n[1/7] Total Lawyers: {len(all_lawyers)} retrieved (Expected: 30)")

    # 2. Category Filtering
    print("\n[2/7] Category Filtering Test:")
    for cat in ["Civil", "Consumer", "Criminal"]:
        r = client.get(f"/api/v1/lawyers?category={cat}")
        data = r.json()
        print(f"  -> Category '{cat}': {len(data)} lawyers returned")
        assert len(data) == 10 and all(l["category"] == cat for l in data)

    # 3. Budget and City Filtering
    print("\n[3/7] Budget & City Filtering Test:")
    r_filter = client.get("/api/v1/lawyers?city=bengaluru&max_budget=60000")
    bengaluru_budget = r_filter.json()
    print(f"  -> Bengaluru lawyers with budget <= Rs 60,000: {len(bengaluru_budget)} found")
    for l in bengaluru_budget:
        print(f"     * {l['full_name']} ({l['category']}) - Rs {l['full_case_estimate']} - {l['city']}")

    # 4. Language Filtering
    print("\n[4/7] Language Substring Matching Test:")
    r_kannada = client.get("/api/v1/lawyers?language=kannada")
    kannada_lawyers = r_kannada.json()
    print(f"  -> Lawyers fluent in Kannada: {len(kannada_lawyers)} found")
    assert len(kannada_lawyers) > 0

    # 5. Sorting Verification
    print("\n[5/7] Sorting Test (Fee Ascending & Experience Descending):")
    r_fee_asc = client.get("/api/v1/lawyers?sort_by=fee_asc")
    lowest = r_fee_asc.json()[0]
    r_exp_desc = client.get("/api/v1/lawyers?sort_by=experience_desc")
    most_exp = r_exp_desc.json()[0]
    print(f"  -> Lowest Fee Lawyer: {lowest['full_name']} (Rs {lowest['full_case_estimate']})")
    print(f"  -> Most Experienced:  {most_exp['full_name']} ({most_exp['experience_years']} years)")

    # 6. Single Lawyer Detail & Comparison Badge
    print("\n[6/7] Single Lawyer Detail & Algorithmic Fee Benchmark Badge:")
    r_detail = client.get("/api/v1/lawyers/1")
    lawyer_detail = r_detail.json()
    print(f"  -> Name:               {lawyer_detail['full_name']}")
    print(f"  -> Bar Council ID:     {lawyer_detail['bar_council_id']}")
    print(f"  -> Category:           {lawyer_detail['category']}")
    print(f"  -> Full Case Estimate: Rs {lawyer_detail['full_case_estimate']}")
    print(f"  -> Category Average:   Rs {lawyer_detail['category_average_fee']}")
    print(f"  -> Comparison Badge:   '{lawyer_detail['fee_comparison_badge']}'")

    # 7. RAG Recommendation Endpoint (Person 3)
    print("\n[7/7] RAG AI Recommendation Service Integration (POST /recommend):")
    rag_payload = {
        "recommended_case_category": "Criminal",
        "urgency_level": "High",
        "max_budget": 120000.00
    }
    r_rag = client.post("/api/v1/lawyers/recommend", json=rag_payload)
    top3 = r_rag.json()
    print(f"  -> Top {len(top3)} Recommended Lawyers for High Urgency Criminal Case (Budget <= Rs 1,20,000):")
    for idx, l in enumerate(top3, 1):
        print(f"     {idx}. {l['full_name']} | Rating: {l['rating']}★ | Fee: Rs {l['full_case_estimate']} | Exp: {l['experience_years']} yrs")

    # Latency Benchmark
    print("\n" + "-" * 80)
    print("FastAPI Response Latency Benchmark (< 30ms requirement):")
    latencies = []
    for _ in range(10):
        t0 = time.perf_counter()
        res = client.get("/api/v1/lawyers?category=Civil&sort_by=fee_asc")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

    avg_latency = sum(latencies) / len(latencies)
    print(f"  -> Measured Average Latency: {avg_latency:.2f} ms")
    print(f"  -> Verification Status:     {'PASS (<30ms)' if avg_latency < 30.0 else 'FAIL'}")
    print("=" * 80)

if __name__ == "__main__":
    run_step3_verification()
