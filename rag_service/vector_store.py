"""
NyayaConnect - Multi-Source Hybrid Legal Retrieval Engine
Combines BM25 Keyword Search (rank_bm25) and Dense Vector Cosine Similarity (ChromaDB),
fused with Reciprocal Rank Fusion (RRF) and metadata exact-matching (Reviewer Requirement 3).
Supports multi-source legal texts: Constitution of India, CPA 2019, BNS 2023, BNSS 2023, RTI Act 2005, and Landmark SC Judgments.
"""

import os
import re
import json
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "data", "constitution_chunks.json")
COLLECTION_NAME = "indian_legal_corpus"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_MODEL_NAME = EMBEDDING_MODEL_NAME

# Global in-memory cache for BM25 and chunks
_bm25_index: Optional[BM25Okapi] = None
_cached_chunks: Optional[List[Dict[str, Any]]] = None
_chunk_id_map: Dict[str, Dict[str, Any]] = {}


def get_embedding_function():
    """Initializes local sentence-transformers embedding model."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )


def get_chroma_client():
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


def _load_corpus_and_bm25():
    """Lazily loads and caches the BM25 index and chunk dictionary."""
    global _bm25_index, _cached_chunks, _chunk_id_map
    if _bm25_index is not None and _cached_chunks is not None:
        return _bm25_index, _cached_chunks, _chunk_id_map

    if not os.path.exists(CHUNKS_PATH):
        raise FileNotFoundError(f"Chunks file not found at {CHUNKS_PATH}. Run ingest_constitution.py first.")

    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        _cached_chunks = json.load(f)

    _chunk_id_map = {c["id"]: c for c in _cached_chunks}
    tokenized_corpus = [re.findall(r"\w+", c["text"].lower()) for c in _cached_chunks]
    _bm25_index = BM25Okapi(tokenized_corpus)
    return _bm25_index, _cached_chunks, _chunk_id_map


def build_vector_store(force_reindex: bool = False):
    """
    Builds and persists ChromaDB vector store and preheats BM25 index.
    """
    client = get_chroma_client()
    ef = get_embedding_function()

    if force_reindex:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"Deleted existing collection '{COLLECTION_NAME}'.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )

    existing_count = collection.count()
    if existing_count > 0 and not force_reindex:
        print(f"Collection '{COLLECTION_NAME}' already populated with {existing_count} chunks. Skipping re-index.")
        _load_corpus_and_bm25()
        return collection

    if not os.path.exists(CHUNKS_PATH):
        raise FileNotFoundError(f"Chunks file not found at {CHUNKS_PATH}. Run ingest_constitution.py first.")

    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Indexing {len(chunks)} multi-source legal chunks into ChromaDB at '{CHROMA_DIR}'...")

    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        ids = [c["id"] for c in batch]
        documents = [c["text"] for c in batch]
        metadatas = [{
            "article_number": c["article_number"],
            "title": c["title"],
            "part": c["part"],
            "clause": c["clause"],
            "page_number": c["page_number"],
            "source": c["source"],
            "source_type": c.get("source_type", "Constitution")
        } for c in batch]

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f" • Indexed chunks {i + 1} to {min(i + batch_size, len(chunks))} / {len(chunks)}")

    print(f"✅ Successfully indexed {collection.count()} chunks into '{COLLECTION_NAME}'.")
    _load_corpus_and_bm25()
    return collection


def get_collection():
    client = get_chroma_client()
    ef = get_embedding_function()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )
    if collection.count() == 0:
        print("Vector collection is empty. Building index from chunks...")
        build_vector_store(force_reindex=False)
    return collection


def extract_exact_legal_references(query: str) -> List[str]:
    """
    Extracts explicit article, section, or landmark precedent mentions:
    e.g. 'Article 21', 'Section 35', 'Preamble', 'Maneka Gandhi', 'D.K. Basu', 'Puttaswamy'.
    """
    refs = []
    # Constitutional Articles e.g. Article 21, Art 19(1)(a)
    art_matches = re.findall(r"(?:article|art\.?)\s*(\d+[A-Z]?)", query, re.IGNORECASE)
    for art in art_matches:
        refs.append(f"Article {art.upper()}")

    # Statutory Sections e.g. Section 35, Sec 173
    sec_matches = re.findall(r"(?:section|sec\.?)\s*(\d+)", query, re.IGNORECASE)
    for sec in sec_matches:
        refs.append(f"Section {sec}")

    if re.search(r"\bpreamble\b", query, re.IGNORECASE):
        refs.append("Preamble")

    if re.search(r"\bmaneka\s+gandhi\b", query, re.IGNORECASE):
        refs.append("Maneka Gandhi")
    if re.search(r"\bd\.?k\.?\s*basu\b", query, re.IGNORECASE):
        refs.append("D.K. Basu")
    if re.search(r"\bputtaswamy\b", query, re.IGNORECASE):
        refs.append("Puttaswamy")

    return refs


def hybrid_retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Real Hybrid Retrieval using Reciprocal Rank Fusion (RRF) (Reviewer Requirement 3):
    1. Exact metadata & title matching (ranked first).
    2. BM25 keyword matching via rank_bm25.
    3. Dense semantic cosine similarity via ChromaDB.
    4. RRF combination: score = sum(1 / (60 + rank)).
    """
    collection = get_collection()
    bm25, chunks, chunk_id_map = _load_corpus_and_bm25()

    exact_refs = extract_exact_legal_references(query)
    q_tokens = re.findall(r"\w+", query.lower())

    # --- 1. BM25 Retrieval ---
    bm25_scores = bm25.get_scores(q_tokens)
    top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda idx: bm25_scores[idx], reverse=True)[:25]
    bm25_ranked_ids = [chunks[idx]["id"] for idx in top_bm25_indices if bm25_scores[idx] > 0]

    # --- 2. Dense Semantic Retrieval ---
    dense_ranked_ids = []
    dense_id_to_meta: Dict[str, Dict[str, Any]] = {}
    dense_id_to_doc: Dict[str, str] = {}
    dense_id_to_dist: Dict[str, float] = {}

    try:
        query_results = collection.query(
            query_texts=[query],
            n_results=min(25, collection.count())
        )
        if query_results and query_results.get("ids") and query_results["ids"][0]:
            dense_ranked_ids = query_results["ids"][0]
            for i, doc_id in enumerate(dense_ranked_ids):
                dense_id_to_meta[doc_id] = query_results["metadatas"][0][i]
                dense_id_to_doc[doc_id] = query_results["documents"][0][i]
                dense_id_to_dist[doc_id] = query_results["distances"][0][i] if query_results.get("distances") else 0.5
    except Exception as e:
        print(f"Dense retrieval exception: {e}")

    # --- 3. Reciprocal Rank Fusion (RRF) ---
    RRF_K = 60
    rrf_scores: Dict[str, float] = {}
    retrieval_reasons: Dict[str, str] = {}

    # Dense ranks
    for rank, doc_id in enumerate(dense_ranked_ids):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (RRF_K + rank + 1))
        retrieval_reasons[doc_id] = "dense_vector"

    # BM25 ranks
    for rank, doc_id in enumerate(bm25_ranked_ids):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (RRF_K + rank + 1))
        if doc_id in retrieval_reasons and retrieval_reasons[doc_id] == "dense_vector":
            retrieval_reasons[doc_id] = "hybrid_bm25_dense"
        else:
            retrieval_reasons[doc_id] = "bm25_keyword"

    # Exact reference boost: Put exact-article/statute hits first, ranked
    for doc_id, chunk in chunk_id_map.items():
        art_num = chunk.get("article_number", "")
        title = chunk.get("title", "")
        text = chunk.get("text", "")

        for ref in exact_refs:
            if ref.lower() in art_num.lower() or ref.lower() in title.lower():
                # Massive RRF boost puts exact hit at the top
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0
                retrieval_reasons[doc_id] = "exact_reference"

    # Sort all candidate IDs by final RRF score descending
    sorted_candidate_ids = sorted(rrf_scores.keys(), key=lambda did: rrf_scores[did], reverse=True)

    results: List[Dict[str, Any]] = []
    for doc_id in sorted_candidate_ids[:top_k]:
        chunk = chunk_id_map.get(doc_id, {})
        meta = dense_id_to_meta.get(doc_id) or {
            "article_number": chunk.get("article_number", ""),
            "title": chunk.get("title", ""),
            "part": chunk.get("part", ""),
            "clause": chunk.get("clause", ""),
            "page_number": chunk.get("page_number", 0),
            "source": chunk.get("source", "Constitution of India"),
            "source_type": chunk.get("source_type", "Constitution")
        }
        doc_text = dense_id_to_doc.get(doc_id) or chunk.get("text", "")
        dist = dense_id_to_dist.get(doc_id, 0.3)
        sim_score = max(0.0, round(1.0 - dist, 4)) if dist <= 1.0 else 0.5
        is_exact = (retrieval_reasons.get(doc_id) == "exact_reference")

        results.append({
            "id": doc_id,
            "text": doc_text,
            "metadata": meta,
            "distance": dist,
            "score": 1.0 if is_exact else sim_score,
            "rrf_score": round(rrf_scores[doc_id], 4),
            "retrieval_type": retrieval_reasons.get(doc_id, "hybrid")
        })

    return results


if __name__ == "__main__":
    import sys
    force = "--reindex" in sys.argv or "--force" in sys.argv
    build_vector_store(force_reindex=force)
    
    test_queries = [
        "What are the remedies to enforce fundamental rights in the Supreme Court under Article 32?",
        "Right to life, dignity and personal liberty under Article 21",
        "A shopkeeper sold a defective laptop and refused refund under Consumer Protection Act",
        "Can a police officer arrest without warrant and what are safeguards under BNSS?",
        "How many days to provide information under RTI for life and liberty?",
        "What did Supreme Court hold in D.K. Basu regarding custodial torture?"
    ]
    
    print("\n" + "=" * 70)
    print("🧪 Running Multi-Source Hybrid RRF Retrieval Verification:")
    print("=" * 70)
    for q in test_queries:
        print(f"\n🔍 Query: '{q}'")
        retrieved = hybrid_retrieve(q, top_k=2)
        for r in retrieved:
            src = r["metadata"].get("source_type", "Constitution")
            print(f"  • [{r['retrieval_type'].upper()} | {src}] {r['metadata'].get('article_number')}: {r['metadata'].get('title')} (RRF: {r.get('rrf_score')}, Score: {r['score']})")
