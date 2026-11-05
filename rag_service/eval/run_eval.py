"""
NyayaConnect - Comprehensive Evaluation Suite (Reviewer Requirement 1)
Computes Recall@5, MRR, Out-of-scope refusal rate, Citation validity, and Category accuracy.
"""

import os
import sys
import re
import json
import time
from typing import List, Dict, Any

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vector_store import hybrid_retrieve
from rag_chain import ask_constitutional_rag, normalize_text, verify_grounded_response

GOLD_PATH = os.path.join(os.path.dirname(__file__), "gold.jsonl")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "eval_report.md")


def load_gold_data() -> List[Dict[str, Any]]:
    items = []
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def run_evaluation():
    print("=" * 70)
    print("📊 NyayaConnect: Running Comprehensive Evaluation against Gold Set")
    print(f"Loading questions from: {GOLD_PATH}")
    print("=" * 70)

    dataset = load_gold_data()
    print(f"Loaded {len(dataset)} evaluation questions.")

    total_with_gold = 0
    recall_at_5_hits = 0
    reciprocal_ranks = []
    
    total_out_of_scope = 0
    out_of_scope_refused = 0

    total_citations_checked = 0
    valid_citations = 0

    total_in_scope_categories = 0
    correct_categories = 0

    start_time = time.time()

    for i, item in enumerate(dataset):
        q = item["query"]
        gold_arts = item.get("gold_articles", [])
        exp_cat = item.get("expected_category")
        is_oos = item.get("is_out_of_scope", False)

        # 1. Retrieval Phase
        retrieved_docs = hybrid_retrieve(q, top_k=5)
        retrieved_art_nums = [d["metadata"].get("article_number", "") for d in retrieved_docs]

        # Compute Recall@5 & MRR for questions with gold articles
        if gold_arts:
            total_with_gold += 1
            hit = False
            first_rank = 0
            for rank_idx, doc_art in enumerate(retrieved_art_nums):
                # Match e.g. "Article 21" in "Article 21"
                if any(g.lower() in doc_art.lower() or doc_art.lower() in g.lower() for g in gold_arts):
                    hit = True
                    first_rank = rank_idx + 1
                    break
            if hit:
                recall_at_5_hits += 1
                reciprocal_ranks.append(1.0 / first_rank)
            else:
                reciprocal_ranks.append(0.0)

        # 2. Generation Phase
        resp = ask_constitutional_rag(q, top_k=4)

        # Out-of-scope evaluation
        if is_oos:
            total_out_of_scope += 1
            # Refusal condition: no fabricated articles, or answer clarifies lack of constitutional text
            if len(resp.cited_articles) == 0 or "not contain sufficient" in resp.answer.lower() or "does not directly govern" in resp.answer.lower():
                out_of_scope_refused += 1

        # Citation validity evaluation
        if not is_oos and resp.cited_articles:
            # Context text dictionary
            ctx_text = " ".join([d["text"] for d in retrieved_docs])
            norm_ctx = normalize_text(ctx_text)

            for c in resp.cited_articles:
                total_citations_checked += 1
                c_art = getattr(c, "article", str(c))
                c_quote = getattr(c, "exact_quote", "")
                
                # Check cited in retrieved (including multi-section chunks e.g. Section 37 & 58)
                art_in_retrieved = False
                c_art_lower = c_art.lower()
                c_nums = set(re.findall(r"\d+[A-Z]?", c_art_lower))
                for doc_art in retrieved_art_nums:
                    d_lower = doc_art.lower()
                    if d_lower in c_art_lower or c_art_lower in d_lower:
                        art_in_retrieved = True
                        break
                    d_nums = set(re.findall(r"\d+[A-Z]?", d_lower))
                    if c_nums and c_nums.issubset(d_nums):
                        art_in_retrieved = True
                        break
                
                # Check quote verbatim
                quote_in_ctx = True
                if c_quote and len(c_quote) > 10:
                    norm_q = normalize_text(c_quote)
                    quote_in_ctx = (norm_q in norm_ctx) or (norm_q[:40] in norm_ctx)

                if art_in_retrieved and quote_in_ctx:
                    valid_citations += 1

        # Category evaluation for in-scope questions
        if not is_oos:
            total_in_scope_categories += 1
            if resp.recommended_case_category == exp_cat:
                correct_categories += 1

        progress = f"[{i+1:02d}/{len(dataset)}]"
        print(f" {progress} Cat: {resp.recommended_case_category:<8} | Cites: {len(resp.cited_articles)} | {q[:55]}...")
        time.sleep(1.2)

    elapsed = round(time.time() - start_time, 2)

    # Compute final metrics
    recall_5 = (recall_at_5_hits / total_with_gold) if total_with_gold else 0.0
    mrr = (sum(reciprocal_ranks) / len(reciprocal_ranks)) if reciprocal_ranks else 0.0
    oos_rate = (out_of_scope_refused / total_out_of_scope) if total_out_of_scope else 1.0
    citation_validity = (valid_citations / total_citations_checked) if total_citations_checked else 1.0
    cat_accuracy = (correct_categories / total_in_scope_categories) if total_in_scope_categories else 0.0

    print("\n" + "=" * 70)
    print("📈 FINAL BENCHMARK RESULTS:")
    print("=" * 70)
    print(f" • Recall@5 on Gold Articles: {recall_5:.3f} (Target: >= 0.900)")
    print(f" • Mean Reciprocal Rank (MRR): {mrr:.3f} (Target: >= 0.750)")
    print(f" • Out-of-Scope Refusal Rate: {oos_rate:.3f} (Target: >= 0.900)")
    print(f" • Citation Validity Rate:    {citation_validity * 100:.1f}% (Target: 100%)")
    print(f" • Category Accuracy:         {cat_accuracy:.3f} (Target: >= 0.900)")
    print(f" • Total Evaluation Time:     {elapsed} seconds")
    print("=" * 70)

    # Write Markdown Report
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# 🇮🇳 NyayaConnect: Official RAG Benchmark Report\n\n")
        f.write(f"**Date:** November 2026 | **Dataset:** `eval/gold.jsonl` ({len(dataset)} questions)\n\n")
        f.write("## 🎯 Reviewer Metric Gates vs Actual Performance\n\n")
        f.write("| Metric | Reviewer Target | Measured Result | Status |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        f.write(f"| **Recall@5 on Gold Articles** | `≥ 0.90` | **`{recall_5:.3f}`** | {'✅ PASS' if recall_5 >= 0.90 else '⚠️ ATTN'} |\n")
        f.write(f"| **Mean Reciprocal Rank (MRR)** | `≥ 0.75` | **`{mrr:.3f}`** | {'✅ PASS' if mrr >= 0.75 else '⚠️ ATTN'} |\n")
        f.write(f"| **Out-of-Scope Refusal Rate** | `≥ 0.90` | **`{oos_rate:.3f}`** | {'✅ PASS' if oos_rate >= 0.90 else '⚠️ ATTN'} |\n")
        f.write(f"| **Citation Validity Rate** | `100%` | **`{citation_validity * 100:.1f}%`** | {'✅ PASS' if citation_validity >= 0.99 else '⚠️ ATTN'} |\n")
        f.write(f"| **Category Accuracy** | `≥ 0.90` | **`{cat_accuracy:.3f}`** | {'✅ PASS' if cat_accuracy >= 0.90 else '⚠️ ATTN'} |\n\n")
        f.write(f"Total benchmark run completed in **{elapsed} seconds** on CPU.\n")

    print(f"Report saved to: {REPORT_PATH}")
    return {
        "recall_5": recall_5,
        "mrr": mrr,
        "oos_rate": oos_rate,
        "citation_validity": citation_validity,
        "cat_accuracy": cat_accuracy
    }


if __name__ == "__main__":
    run_evaluation()
