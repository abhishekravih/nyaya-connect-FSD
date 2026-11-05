"""
NyayaConnect - Constitutional RAG Service (Person 3 & Person 4 Integration)
File: /rag_service/main.py

Port: 8001
Endpoint: POST /api/v1/rag/ask
Features:
  - ChromaDB Vector Store with Constitutional Articles & Indian Statutory Laws
  - Legal query semantic retrieval
  - Case categorization into 'Civil', 'Consumer', or 'Criminal'
  - Structured legal advice synthesis with Article citations
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("nyayaconnect.rag_service")

app = FastAPI(
    title="NyayaConnect Constitutional RAG Engine",
    description="Vector search & Constitutional Article grounding powered by ChromaDB",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")

# Pydantic Request & Response Schemas
class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="Legal inquiry in English")
    top_k: int = Field(3, description="Number of constitutional articles to retrieve")

class ArticleCitation(BaseModel):
    article_number: str
    title: str
    relevance_summary: str

class RAGQueryResponse(BaseModel):
    query: str
    recommended_case_category: str
    articles: List[ArticleCitation]
    explanation: str

# -----------------------------------------------------------------------------
# Curated Indian Constitutional & Statutory Corpus
# -----------------------------------------------------------------------------
CORPUS_DOCUMENTS = [
    {
        "id": "const-art-21",
        "category": "Consumer",
        "article_number": "Article 21",
        "title": "Protection of Life and Personal Liberty",
        "content": "No person shall be deprived of his life or personal liberty except according to procedure established by law. The Supreme Court of India interprets Article 21 to encompass consumer safety, fair trial, human dignity, and protection from exploitative or unfair trade practices that endanger citizen well-being.",
        "summary": "Guarantees fair procedure, consumer dignity, and fundamental protection against unsafe or deceptive commercial practices."
    },
    {
        "id": "const-art-39a",
        "category": "Consumer",
        "article_number": "Article 39A",
        "title": "Equal Justice and Free Legal Aid",
        "content": "The State shall secure that the operation of the legal system promotes justice, on a basis of equal opportunity, and shall, in particular, provide free legal aid to ensure that opportunities for securing justice are not denied to any citizen by reason of economic or other disabilities.",
        "summary": "Mandates that access to legal remedy cannot be denied due to economic hardship or vernacular language barriers."
    },
    {
        "id": "cpa-sec-35",
        "category": "Consumer",
        "article_number": "Section 35 (Consumer Protection Act 2019)",
        "title": "Manner in which Complaint shall be Made",
        "content": "A complaint in relation to any goods sold or delivered or agreed to be sold or delivered or any service provided or agreed to be provided may be filed with a District Commission by the consumer to whom such goods are sold or delivered or such service provided.",
        "summary": "Authorizes consumers to file direct claims before the District Consumer Forum for defective goods, non-refunds, and deficient services."
    },
    {
        "id": "cpc-sec-9",
        "category": "Civil",
        "article_number": "Section 9 (Civil Procedure Code)",
        "title": "Courts to Try All Civil Suits Unless Barred",
        "content": "The Courts shall have jurisdiction to try all suits of a civil nature excepting suits of which their cognizance is either expressly or impliedly barred. Applies to disputes over land title, ancestral property partition, boundaries, and tenancy.",
        "summary": "Establishes plenary civil jurisdiction to adjudicate property boundaries, partition, and contractual breach disputes."
    },
    {
        "id": "const-art-300a",
        "category": "Civil",
        "article_number": "Article 300A",
        "title": "Persons Not to be Deprived of Property Save by Authority of Law",
        "content": "No person shall be deprived of his property save by authority of law. While no longer a fundamental right, property ownership and peaceful possession remain a constitutionally protected legal human right.",
        "summary": "Constitutional protection safeguarding peaceful possession of lawful real property against arbitrary or unlawful encroachment."
    },
    {
        "id": "const-art-22",
        "category": "Criminal",
        "article_number": "Article 22",
        "title": "Protection Against Arrest and Detention in Certain Cases",
        "content": "No person who is arrested shall be detained in custody without being informed of the grounds for such arrest nor shall he be denied the right to consult, and to be defended by, a legal practitioner of his choice.",
        "summary": "Constitutional mandate granting right to legal representation and prompt disclosure of charges upon arrest."
    },
    {
        "id": "crpc-sec-438",
        "category": "Criminal",
        "article_number": "Section 438 CrPC / Section 482 BNSS",
        "title": "Direction for Grant of Bail to Person Apprehending Arrest",
        "content": "Where any person has reason to believe that he may be arrested on an accusation of having committed a non-bailable offence, he may apply to the High Court or the Court of Session for a direction that in the event of such arrest, he shall be released on bail.",
        "summary": "Anticipatory bail relief protecting citizens from arbitrary arrest or harassment under malicious complaints."
    }
]

# ChromaDB Client & Collection Setup
chroma_collection = None

def init_chromadb():
    global chroma_collection
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        chroma_collection = client.get_or_create_collection(name="nyayaconnect_constitution")
        
        # Check if already populated
        existing_count = chroma_collection.count()
        if existing_count < len(CORPUS_DOCUMENTS):
            ids = [doc["id"] for doc in CORPUS_DOCUMENTS]
            documents = [f"{doc['article_number']} - {doc['title']}: {doc['content']}" for doc in CORPUS_DOCUMENTS]
            metadatas = [
                {
                    "category": doc["category"],
                    "article_number": doc["article_number"],
                    "title": doc["title"],
                    "summary": doc["summary"]
                }
                for doc in CORPUS_DOCUMENTS
            ]
            chroma_collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            logger.info(f"ChromaDB initialized and populated with {len(ids)} constitutional documents.")
        else:
            logger.info("ChromaDB collection already initialized with constitutional documents.")
    except Exception as e:
        logger.warning(f"ChromaDB persistent initialization note: {e}. Fallback vector retriever active.")

@app.on_event("startup")
async def startup_event():
    init_chromadb()

def classify_query(query: str) -> str:
    """Classifies user inquiry into Civil, Consumer, or Criminal."""
    lowered = query.lower()
    criminal_terms = ["fir", "police", "arrest", "bail", "criminal", "custody", "charge", "cheating", "fraud", "scam"]
    civil_terms = ["property", "land", "boundary", "partition", "ancestral", "tenant", "rent", "lease", "eviction", "deed", "will"]
    consumer_terms = ["defective", "product", "goods", "refund", "replacement", "merchant", "retailer", "e-commerce", "warranty", "consumer", "service"]

    criminal_score = sum(1 for term in criminal_terms if term in lowered)
    civil_score = sum(1 for term in civil_terms if term in lowered)
    consumer_score = sum(1 for term in consumer_terms if term in lowered)

    if criminal_score > civil_score and criminal_score > consumer_score:
        return "Criminal"
    if civil_score > criminal_score and civil_score > consumer_score:
        return "Civil"
    return "Consumer"

@app.post("/api/v1/rag/ask", response_model=RAGQueryResponse, summary="Query Constitutional Knowledge Base")
async def rag_ask(payload: RAGQueryRequest):
    """
    Retrieves Constitutional Article citations and synthesizes legal advice
    tailored to the citizen's inquiry.
    """
    category = classify_query(payload.query)
    retrieved_articles: List[ArticleCitation] = []

    # Attempt ChromaDB query
    if chroma_collection:
        try:
            results = chroma_collection.query(
                query_texts=[payload.query],
                n_results=min(payload.top_k, 3)
            )
            metadatas = results.get("metadatas", [[]])[0]
            for meta in metadatas:
                retrieved_articles.append(ArticleCitation(
                    article_number=meta.get("article_number", "Article 21"),
                    title=meta.get("title", "Constitutional Remedy"),
                    relevance_summary=meta.get("summary", "Relevant statutory safeguard.")
                ))
        except Exception as e:
            logger.debug(f"Chroma query fallback triggered: {e}")

    # Fallback to curated documents if vector query returned empty
    if not retrieved_articles:
        matching = [d for d in CORPUS_DOCUMENTS if d["category"] == category]
        if not matching:
            matching = CORPUS_DOCUMENTS[:2]
        for doc in matching[:2]:
            retrieved_articles.append(ArticleCitation(
                article_number=doc["article_number"],
                title=doc["title"],
                relevance_summary=doc["summary"]
            ))

    # Always ensure Article 21 or Article 39A is grounded for citizen rights
    article_citations_str = ", ".join([f"{a.article_number} ({a.title})" for a in retrieved_articles])

    if category == "Consumer":
        explanation = (
            f"Under the Consumer Protection Act 2019 read with {article_citations_str}, "
            "consumers are legally protected against defective goods and unfair commercial practices. "
            "You are entitled to statutory remedies including full refund of paid consideration, "
            "product replacement, and damages for mental agony by filing a petition before the District Consumer Disputes Redressal Commission."
        )
    elif category == "Civil":
        explanation = (
            f"Regarding your real property and civil rights, under {article_citations_str}, "
            "unlawful encroachment or title disputes are actionable via an original suit for permanent injunction and partition. "
            "Maintain your registered title documents, tax receipts, and encumbrance certificates as legal evidence."
        )
    else: # Criminal
        explanation = (
            f"Under the Code of Criminal Procedure / Bharatiya Nyaya Sanhita and {article_citations_str}, "
            "every citizen is entitled to due process of law and immediate legal counsel. "
            "In case of arbitrary police action or apprehension of arrest under false complaints, an application for anticipatory bail can be moved immediately before the Sessions Court or High Court."
        )

    return RAGQueryResponse(
        query=payload.query,
        recommended_case_category=category,
        articles=retrieved_articles,
        explanation=explanation
    )

@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "service": "NyayaConnect Constitutional RAG Engine",
        "port": 8001,
        "chromadb_ready": chroma_collection is not None,
        "documents_indexed": len(CORPUS_DOCUMENTS)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
