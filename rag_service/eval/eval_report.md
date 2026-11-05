# 🇮🇳 NyayaConnect: Official Legal RAG Benchmark Report

**Date:** November 2026 | **Dataset:** `eval/gold.jsonl` (120 benchmark queries) | **Mode:** `Gemini Live API`

## 🎯 Primary Reviewer Metric Gates vs Actual Performance

| Metric | Reviewer Target | Measured Result | Status |
| :--- | :---: | :---: | :---: |
| **Recall@5 on Gold Provisions (Overall)** | `≥ 0.900` | **`0.905`** | ✅ PASS |
| **Mean Reciprocal Rank (MRR)** | `≥ 0.750` | **`0.853`** | ✅ PASS |
| **Out-of-Scope Refusal Rate (Overall)** | `≥ 0.900` | **`100.0%`** | ✅ PASS |
| **Out-of-Scope Near-Miss Refusal** | `≥ 0.900` | **`100.0%`** | ✅ PASS |
| **Strict Citation Validity (Cited ⊂ Context)** | `100.0%` | **`100.0%`** | ✅ PASS |
| **Category Accuracy (Independent Labels)** | `≥ 0.900` | **`89.5%`** | ⚠️ ATTN |

## 🔬 Sub-Domain & Ablation Breakdowns

| Evaluation Dimension | Sample Count | Recall@5 | MRR | Description |
| :--- | :---: | :---: | :---: | :--- |
| **Statutory Enactments (BNSS/BNS/CPA/RTI)** | 94 | **`0.904`** | `0.851` | Measures modern statutes and landmark precedents |
| **Constitution of India (Articles 1-395)** | 1 | **`1.000`** | `1.000` | Official gazetted text & constitutional schedules |
| **Implicit Scenarios (No Article Named)** | 47 | **`0.808`** | `0.702` | Real citizen facts without legal terminology |
| **Test Split (Frozen Evaluation)** | 64 | **`0.938`** | `0.889` | Independent evaluation split |
| **Dev Split (Threshold Tuning)** | 31 | **`0.839`** | `0.777` | Calibrated cutoff tuning split |

## 🛡️ Code-Level Grounding & Conversational Polish

- **Dropped Citation Rate:** `21.1%` (32 hallucinated or ungrounded quotes dropped without overwriting)
- **Contextual Query Rewriter Hit Rate:** `100.0%` (15/15 conversational pronoun follow-ups resolved to gold provisions)
- **Benchmark Wall Time:** `359.84s` on local machine
