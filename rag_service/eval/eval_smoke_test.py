"""
NyayaConnect - Evaluation Smoke Test (CI-Ready)
Runs a fast 5-query validation across Criminal, Civil, Consumer, and Out-of-scope negative controls.
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vector_store import hybrid_retrieve
from rag_chain import ask_constitutional_rag, normalize_text

GOLD_PATH = os.path.join(os.path.dirname(__file__), "gold.jsonl")


def test_eval_smoke_subset():
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        all_items = [json.loads(line) for line in f if line.strip()]

    # Pick 1 Criminal, 1 Civil, 1 Consumer, 1 Out-of-scope
    smoke_items = [
        all_items[0],   # Criminal (Article 22 arrest)
        all_items[15],  # Civil (Article 15/29 admission)
        all_items[35],  # Consumer (defective TV)
        all_items[50],  # Out-of-scope (chocolate chip cookie)
    ]

    for item in smoke_items:
        q = item["query"]
        is_oos = item.get("is_out_of_scope", False)
        gold_arts = item.get("gold_articles", [])

        # Retrieval check
        docs = hybrid_retrieve(q, top_k=4)
        assert len(docs) > 0, f"Retrieval must return candidates for query: {q}"

        if gold_arts:
            retrieved_arts = [d["metadata"].get("article_number", "") for d in docs]
            hit = any(
                any(g.lower() in d_art.lower() or d_art.lower() in g.lower() for g in gold_arts)
                for d_art in retrieved_arts
            )
            assert hit, f"Gold article {gold_arts} must be retrieved in top_k for query: {q}"

        # Inference check
        resp = ask_constitutional_rag(q, top_k=4)
        assert len(resp.answer) > 20

        if is_oos:
            # Out-of-scope negative control must refuse or drop citations
            assert len(resp.cited_articles) == 0 or "not contain sufficient" in resp.answer.lower() or "falls outside" in resp.answer.lower()
        else:
            assert resp.recommended_case_category in ["Civil", "Consumer", "Criminal"]
            assert resp.urgency_level in ["Low", "Medium", "High"]


if __name__ == "__main__":
    test_eval_smoke_subset()
    print("✅ Evaluation smoke test passed successfully.")
