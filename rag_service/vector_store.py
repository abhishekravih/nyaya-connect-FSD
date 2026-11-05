"""
NyayaConnect - Constitutional Vector Store & Hybrid Retrieval
Manages persistent ChromaDB vector storage and hybrid semantic + metadata retrieval.
"""

import os
import re
import json
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "data", "constitution_chunks.json")
COLLECTION_NAME = "constitution_rag"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

_client: Optional[chromadb.PersistentClient] = None
_embedding_fn: Optional[embedding_functions.SentenceTransformerEmbeddingFunction] = None


def get_embedding_function():
    """Initializes and caches the local HuggingFace embedding function."""
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL_NAME
        )
    return _embedding_fn


def get_chroma_client() -> chromadb.PersistentClient:
    """Returns persistent ChromaDB client."""
    global _client
    if _client is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _client


def get_collection():
    """Returns the constitution_rag collection."""
    client = get_chroma_client()
    ef = get_embedding_function()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )


def build_vector_store(force_reindex: bool = False):
    """
    Loads chunks from data/constitution_chunks.json and populates ChromaDB.
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
        return collection

    if not os.path.exists(CHUNKS_PATH):
        raise FileNotFoundError(f"Chunks file not found at {CHUNKS_PATH}. Run ingest_constitution.py first.")

    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Indexing {len(chunks)} Constitutional chunks into ChromaDB at '{CHROMA_DIR}'...")

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
            "source": c["source"]
        } for c in batch]

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f" • Indexed chunks {i + 1} to {min(i + batch_size, len(chunks))} / {len(chunks)}")

    print(f"✅ Successfully indexed {collection.count()} chunks into '{COLLECTION_NAME}'.")
    return collection


def extract_exact_article_query(query: str) -> Optional[str]:
    """
    Extracts article reference from user query (e.g. 'Article 21', 'Art 19', 'Article 32').
    """
    match = re.search(r"(?:article|art\.?)\s*(\d+[A-Z]?)", query, re.IGNORECASE)
    if match:
        art_num = match.group(1).upper()
        return f"Article {art_num}"
    
    if "preamble" in query.lower():
        return "Preamble"
        
    return None


def hybrid_retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Hybrid Retrieval:
    1. Dense vector semantic search.
    2. Metadata filtering for exact Article mentions.
    3. Merges and deduplicates ranking.
    """
    collection = get_collection()
    results: List[Dict[str, Any]] = []
    seen_ids = set()

    # 1. Exact article lookup if mentioned
    exact_art = extract_exact_article_query(query)
    if exact_art:
        try:
            exact_matches = collection.get(
                where={"article_number": exact_art},
                limit=3
            )
            if exact_matches and exact_matches.get("ids"):
                for idx, doc_id in enumerate(exact_matches["ids"]):
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        meta = exact_matches["metadatas"][idx] if exact_matches["metadatas"] else {}
                        results.append({
                            "id": doc_id,
                            "text": exact_matches["documents"][idx],
                            "metadata": meta,
                            "distance": 0.0,
                            "score": 1.0,
                            "retrieval_type": "exact_metadata"
                        })
        except Exception as e:
            print(f"Exact article metadata retrieval error: {e}")

    # 2. Dense semantic similarity search
    n_results = max(top_k, 5)
    semantic_res = collection.query(
        query_texts=[query],
        n_results=n_results
    )

    if semantic_res and semantic_res.get("ids") and semantic_res["ids"][0]:
        doc_ids = semantic_res["ids"][0]
        documents = semantic_res["documents"][0]
        metadatas = semantic_res["metadatas"][0]
        distances = semantic_res["distances"][0] if semantic_res.get("distances") else [0.5] * len(doc_ids)

        for i, doc_id in enumerate(doc_ids):
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                dist = distances[i]
                # Cosine distance to similarity score: 1 - distance
                sim_score = max(0.0, round(1.0 - dist, 4))
                results.append({
                    "id": doc_id,
                    "text": documents[i],
                    "metadata": metadatas[i],
                    "distance": dist,
                    "score": sim_score,
                    "retrieval_type": "vector_semantic"
                })

    # Return top_k ranked documents
    return results[:top_k]


if __name__ == "__main__":
    import sys
    force = "--reindex" in sys.argv or "--force" in sys.argv
    build_vector_store(force_reindex=force)
    
    # Test queries
    test_queries = [
        "What are the remedies to enforce fundamental rights in the Supreme Court?",
        "Right to life, dignity and personal liberty under Article 21",
        "Preamble socialist secular democratic republic"
    ]
    
    print("\n" + "=" * 70)
    print("🧪 Running Retrieval Verification Tests:")
    print("=" * 70)
    for q in test_queries:
        print(f"\n🔍 Query: '{q}'")
        retrieved = hybrid_retrieve(q, top_k=2)
        for r in retrieved:
            print(f"  • [{r['retrieval_type'].upper()}] {r['metadata'].get('article_number')}: {r['metadata'].get('title')} (Score: {r['score']})")
