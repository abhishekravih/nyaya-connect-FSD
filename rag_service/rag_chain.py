"""
NyayaConnect - Constitutional RAG Chain & Structured Generation
Implements zero-hallucination prompt engineering and Pydantic schema validation.
"""

import os
import json
from typing import List, Literal, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from vector_store import hybrid_retrieve

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL_NAME = os.getenv("LLM_MODEL", "gemini-2.5-flash")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))


class CitedArticle(BaseModel):
    article: str = Field(description="Article citation e.g. 'Article 22(1) & 22(2)'")
    part: Optional[str] = Field(default="", description="Part title e.g. 'Part III – Fundamental Rights'")
    exact_quote: Optional[str] = Field(default="", description="Exact quote from the constitutional text")


class RAGLegalResponse(BaseModel):
    query: str = Field(description="The original user legal query")
    answer: str = Field(description="Clear, grounded constitutional explanation citing provisions")
    cited_articles: List[CitedArticle] = Field(
        default_factory=list,
        description="Structured articles cited with exact quotes and parts"
    )
    recommended_case_category: Literal["Civil", "Consumer", "Criminal"] = Field(
        description="The primary legal classification for court or paralegal intake"
    )
    urgency_level: Literal["Low", "Medium", "High"] = Field(
        description="Severity and time-sensitivity of legal action"
    )
    suggested_action: str = Field(
        description="Next concrete step for the citizen or paralegal, e.g. 'File a Writ Petition under Article 226 before the High Court'"
    )


CONSTITUTIONAL_SYSTEM_PROMPT = """You are NyayaConnect's Constitutional Legal Assistant for Indian citizens and paralegals.
Your job is to provide accurate, grounded legal explanations based STRICTLY on the retrieved Articles and Schedules of the Constitution of India provided in the Context below.

CRITICAL RULES:
1. ZERO HALLUCINATIONS: Ground your answer ONLY in the retrieved Indian Constitutional provisions in the context. Never cite an Article that is not present in the context or does not exist in the Constitution.
2. If the context does NOT contain constitutional provisions to answer the question (e.g. private consumer product defects, commercial contracts, statutory consumer complaints), state: "The Constitution of India does not directly govern this private statutory dispute. It is governed by specific legislation (such as the Consumer Protection Act, 2019 or statutory civil/criminal codes)." Set cited_articles to [].
3. Classify the matter into EXACTLY one recommended_case_category for lawyer matchmaking:
   - 'Criminal': Matters involving physical liberty, wrongful arrest, police detention, custody, accused rights, self-incrimination, criminal trial, bail, habeas corpus, cognizable offences.
   - 'Consumer': Matters involving commercial purchase, defective goods, product warranty, service deficiency, consumer refund, misleading advertisements, airline/hospital/builder disputes.
   - 'Civil': Matters involving fundamental rights violations, equality, discrimination, speech, property rights, non-custodial writs (mandamus, certiorari), civil service, public contracts.
4. Urgency Level:
   - 'High': Imminent arrest, unlawful detention, risk to life, physical harm (habeas corpus, Article 21/22).
   - 'Medium': Ongoing discrimination, consumer loss, loss of livelihood, property dispute, immediate court petition required.
   - 'Low': General legal inquiry, procedural advice, RTI, long-term statutory compliance.
5. Provide a realistic, concrete suggested_action tailored to Indian legal procedures (e.g. filing a Writ Petition under Article 226/32, approaching District Legal Services Authority (DLSA), filing a complaint before the Consumer Commission, or filing a police/bail petition).
6. Output MUST strictly conform to the JSON schema.
"""


def classify_legal_domain(query: str):
    q = query.lower()
    if any(k in q for k in ["tapping", "surveillance", "privacy", "wiretap"]):
        return "Civil", "Medium", "File a Writ Petition under Article 226/32 challenging unauthorized surveillance and violation of privacy under Article 21."
    elif any(k in q for k in ["arrest", "police", "custody", "detain", "detention", "bail", "fir", "criminal", "accused", "witness", "habeas", "torture", "jeopardy", "prosecut"]):
        return "Criminal", "High", "Seek immediate legal counsel to file a Bail application or petition for a Writ of Habeas Corpus under Article 226/32."
    elif any(k in q for k in ["consumer", "refrigerator", "warranty", "refund", "counterfeit", "hospital bill", "builder delay", "airline", "billing", "insurance claim", "dealer", "expired", "defective goods"]):
        return "Consumer", "Medium", "File a consumer grievance on the National Consumer Helpline (NCH) or approach the District Consumer Disputes Redressal Commission."
    else:
        urgency = "Medium" if any(k in q for k in ["discrimination", "equality", "writ", "speech", "religion", "mandamus"]) else "Low"
        return "Civil", urgency, "Approach the District Legal Services Authority (DLSA) or file a Writ Petition under Article 226/32 before the High Court."


def _generate_offline_fallback_response(query: str, retrieved_docs: List[Dict[str, Any]]) -> RAGLegalResponse:
    """
    High-fidelity offline fallback generator when GEMINI_API_KEY is not set or network fails.
    Ensures that teammates' UI tests and hackathon demos never crash.
    """
    category, urgency, action = classify_legal_domain(query)

    # Extract cited articles with rich metadata
    cited_articles = []
    if category != "Consumer":
        for d in retrieved_docs[:3]:
            art_num = d["metadata"].get("article_number", "")
            title = d["metadata"].get("title", "")
            part = d["metadata"].get("part", "")
            body = d.get("text", "")
            quote = body.split("\n\n")[-1][:250].strip().replace("\n", " ")
            if art_num:
                cited_articles.append(CitedArticle(
                    article=f"{art_num} ({title})",
                    part=part,
                    exact_quote=quote
                ))

    if not retrieved_docs or category == "Consumer":
        return RAGLegalResponse(
            query=query,
            answer="The Constitution of India does not directly govern private commercial or consumer disputes. This matter is regulated under the Consumer Protection Act, 2019 and consumer dispute redressal commissions.",
            cited_articles=[],
            recommended_case_category="Consumer" if category == "Consumer" else category,
            urgency_level=urgency,
            suggested_action=action
        )

    # Synthesize answer from top retrieved text
    top_doc = retrieved_docs[0]
    top_art = top_doc["metadata"].get("article_number", "The Constitution")
    top_title = top_doc["metadata"].get("title", "")
    top_part = top_doc["metadata"].get("part", "")
    top_content = top_doc["text"].strip()
    
    preview = top_content[:500].replace("\n", " ")

    answer_text = (
        f"Under {top_art} ({top_title}) of {top_part}, the Indian Constitution provides: \"{preview}...\". "
        f"This provision directly protects rights regarding {top_title.lower()} and binds state action. "
        f"Remedies may be pursued before the High Court under Article 226 or the Supreme Court under Article 32."
    )

    return RAGLegalResponse(
        query=query,
        answer=answer_text,
        cited_articles=cited_articles[:3],
        recommended_case_category=category,
        urgency_level=urgency,
        suggested_action=action
    )


def ask_constitutional_rag(query: str, top_k: int = 4) -> RAGLegalResponse:
    """
    Main RAG pipeline:
    1. Hybrid retrieval from ChromaDB.
    2. Zero-hallucination prompt assembly.
    3. Structured JSON generation via Google Gemini.
    4. Fallback resilience on quota or key unavailability.
    """
    retrieved_docs = hybrid_retrieve(query, top_k=top_k)

    # Confidence threshold guardrail (Filters truly out-of-domain queries e.g. recipes, non-legal text)
    top_score = retrieved_docs[0].get("score", 0.0) if retrieved_docs else 0.0
    is_exact = any(d.get("retrieval_type") == "exact_metadata" for d in retrieved_docs)
    category, urgency, action = classify_legal_domain(query)
    
    if (top_score < 0.35 and not is_exact) or category == "Consumer":
        ans = (
            "The Constitution of India does not directly govern private commercial, consumer, or contractual disputes. "
            "This matter is governed by specific statutory codes such as the Consumer Protection Act, 2019."
            if category == "Consumer"
            else "The provided Constitutional provisions do not contain sufficient information to answer this query with high confidence. The matter falls outside direct constitutional provisions and requires specific statutory remedies."
        )
        return RAGLegalResponse(
            query=query,
            answer=ans,
            cited_articles=[],
            recommended_case_category=category,
            urgency_level=urgency,
            suggested_action=action
        )

    # Format context
    context_blocks = []
    for i, doc in enumerate(retrieved_docs):
        meta = doc.get("metadata", {})
        art = meta.get("article_number", "Article")
        title = meta.get("title", "")
        part = meta.get("part", "")
        clause = meta.get("clause", "")
        body = doc.get("text", "").strip()
        context_blocks.append(
            f"--- PROVISION {i+1}: {art} - {title} ({part}, Clause {clause}) ---\n{body}"
        )
    context_str = "\n\n".join(context_blocks)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        # Graceful fallback to offline grounded response
        return _generate_offline_fallback_response(query, retrieved_docs)

    prompt = f"""{CONSTITUTIONAL_SYSTEM_PROMPT}

CONTEXT OF RETRIEVED CONSTITUTIONAL PROVISIONS:
{context_str}

USER QUERY:
{query}

Generate a JSON object matching this exact schema:
{{
  "query": "{query}",
  "answer": "string",
  "cited_articles": [
    {{
      "article": "string (e.g. Article 22(1))",
      "part": "string (e.g. Part III – Fundamental Rights)",
      "exact_quote": "string"
    }}
  ],
  "recommended_case_category": "Civil" | "Consumer" | "Criminal",
  "urgency_level": "Low" | "Medium" | "High",
  "suggested_action": "string"
}}
"""

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        candidate_models = [MODEL_NAME, "gemini-3.1-flash-lite", "gemini-3.5-flash"]
        # Remove duplicates while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        for model_id in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=TEMPERATURE,
                        response_mime_type="application/json",
                        response_schema=RAGLegalResponse,
                    ),
                )
                raw_json = response.text.strip()
                data = json.loads(raw_json)
                return RAGLegalResponse(**data)
            except Exception as m_err:
                print(f"Model '{model_id}' failed: {m_err}. Trying next candidate...")

        # If all candidates threw exceptions, fallback
        print("All Gemini models exhausted. Utilizing grounded fallback.")
        return _generate_offline_fallback_response(query, retrieved_docs)

    except Exception as err:
        print(f"⚠️ Gemini API invocation failed ({err}). Utilizing grounded fallback.")
        return _generate_offline_fallback_response(query, retrieved_docs)


if __name__ == "__main__":
    test_cases = [
        "A citizen was detained by the police for 48 hours without being presented before a magistrate. What are their constitutional rights?",
        "Can a citizen be denied admission to a state university solely based on their religion or caste?",
        "What does the Preamble say about justice, liberty, and equality?",
        "A shopkeeper refused to replace an expired television set. Does the Constitution cover this?"
    ]

    print("=" * 70)
    print("🇮🇳 Testing NyayaConnect RAG Chain (Zero-Hallucination & Pydantic Schema)")
    print("=" * 70)

    for tc in test_cases:
        print(f"\n❓ Query: {tc}")
        response = ask_constitutional_rag(tc)
        print(f"📋 Category:  {response.recommended_case_category} | Urgency: {response.urgency_level}")
        print(f"📜 Articles:  {response.cited_articles}")
        print(f"💡 Action:    {response.suggested_action}")
        print(f"📖 Answer:    {response.answer[:200]}...")
