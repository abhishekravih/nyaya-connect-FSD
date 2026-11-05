# 🇮🇳 NyayaConnect - Constitutional RAG Service (Person 3)

The intelligence and constitutional reasoning microservice of **NyayaConnect**, delivering zero-hallucination legal information grounded in the official gazetted Constitution of India.

---

## 🏛️ System Features
- **Constitutional Corpus:** 1,030 semantically chunked legal articles across Articles 1–395, Preamble, and Schedules 1–12.
- **Persistent ChromaDB:** Cosine vector storage (`constitution_rag`) with local `sentence-transformers/all-MiniLM-L6-v2` embeddings (zero API cost, 100% offline retrieval).
- **Zero-Hallucination Generation:** Google Gemini (`gemini-3.1-flash-lite` / `gemini-3.5-flash` @ `temperature=0.1`) with Pydantic structured output.
- **Fail-Safe Fallback:** Automatic failover to offline grounded synthesis if network or rate-limits occur.
- **High Performance:** In-memory LRU caching delivering sub-5ms responses on repeated queries.

---

## 🔌 API Endpoints (Port 8001)

### `POST /api/v1/rag/ask`
Accepts legal inquiries and returns grounded advice with citations, category (`Civil`, `Consumer`, `Criminal`), urgency, and suggested actions.

```bash
curl -X POST http://localhost:8001/api/v1/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "The police detained my brother for 36 hours without producing him before a magistrate."}'
```

### `GET /api/v1/rag/health`
Returns ChromaDB vector store readiness, chunk count, and LLM status.

### `GET /health`
Docker container health check.

---

## 🧪 Testing & Audit Reports
- **Subagent Specification:** [`.antigravity/agents/legal-rag-auditor.md`](./.antigravity/agents/legal-rag-auditor.md)
- **30-Query Benchmark Report:** [`artifacts/rag_audit_report.md`](./artifacts/rag_audit_report.md) (100% classification accuracy)
- **Person 1 UI Contract:** [`rag_responses_contract.json`](./rag_responses_contract.json)
