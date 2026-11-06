"""
NyayaConnect - Vernacular Voice-to-RAG Pipeline (Person 4: System Integration)
File: /backend/routers/voice_bridge.py

4-Stage Vernacular Pipeline:
  Stage 1: Input Validation
           - Validates supported language code (kn-IN, hi-IN, ta-IN, te-IN, mr-IN, bn-IN, en-IN).
           - Rejects empty, invalid, or oversized (>10MB) audio payloads.
           - Requires either a valid audio blob or a browser-supplied transcript.
  Stage 2: Speech-to-Text Transcription
           - If browser transcript provided, utilizes it and reports speech_source="browser_web_speech".
           - If audio provided, routes to configured STT provider (Bhashini ASR or OpenAI Whisper).
           - If no provider configured and no transcript provided, returns HTTP 503 / HTTP 422 error.
  Stage 3: English Translation
           - Translates vernacular regional text into English for the RAG engine using live translation adapter.
           - If translation provider unconfigured for vernacular input, returns an explicit HTTP 501 error.
  Stage 4: Native Language Explanation & Citation Safeguarding
           - Queries RAG engine for legal explanation and statutory citations.
           - Tokenizes ALL citations (__LEGAL_CITATION_{i}__) to prevent corrupting legal references.
           - Translates explanation back to native language and restores all citations.
           - Never hallucinates citations or inserts default Article 21 when none exist in source.
"""

import os
import re
import time
import base64
import logging
from typing import Optional, List, Dict, Any, Tuple
import httpx
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Body, status
from pydantic import BaseModel, Field

logger = logging.getLogger("nyayaconnect.voice_bridge")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/api/v1/voice", tags=["Vernacular Voice Pipeline"])

# Maximum audio payload: 10 MB
MAX_AUDIO_BYTES = 10 * 1024 * 1024

# Supported Indian regional languages
SUPPORTED_LANGUAGES = {
    "kn-IN": "Kannada",
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "mr-IN": "Marathi",
    "bn-IN": "Bengali",
    "en-IN": "Indian English"
}

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag_service:8001/api/v1")
RAG_LOCAL_URL = os.getenv("RAG_LOCAL_URL", "http://127.0.0.1:8001/api/v1")

# Pydantic Schemas
class VoiceAskJSONRequest(BaseModel):
    audio_base64: Optional[str] = Field(None, description="Base64-encoded audio blob")
    transcript: Optional[str] = Field(None, description="Web Speech API fallback transcript")
    source_language: str = Field("kn-IN", description="BCP-47 language code (e.g. kn-IN, hi-IN)")

class ArticleCitation(BaseModel):
    article_number: str
    title: str
    relevance_summary: str

class VoiceAskResponse(BaseModel):
    success: bool
    source_language: str
    speech_source: str # "browser_web_speech" or "configured_stt_provider"
    transcribed_vernacular_text: str
    translated_english_query: str
    constitutional_articles: List[ArticleCitation]
    recommended_case_category: str
    translated_explanation: str
    original_english_explanation: str
    preserved_citations: List[str]
    pipeline_latency_ms: float

# -----------------------------------------------------------------------------
# Stage 1: Validation
# -----------------------------------------------------------------------------

def validate_language_code(language_code: str) -> str:
    """Validates language code against supported regional BCP-47 identifiers."""
    lang = language_code.strip()
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language code '{language_code}'. Supported languages are: {', '.join(SUPPORTED_LANGUAGES.keys())}"
        )
    return lang

def validate_audio_payload(audio_bytes: bytes, browser_transcript: Optional[str]):
    """Validates that either valid audio or a non-empty transcript is provided."""
    has_transcript = browser_transcript is not None and len(browser_transcript.strip()) > 0
    has_audio = audio_bytes is not None and len(audio_bytes) > 0

    if not has_transcript and not has_audio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: Either an audio file or a browser-supplied transcript must be provided."
        )

    if has_audio and len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file exceeds maximum size limit of {MAX_AUDIO_BYTES // (1024 * 1024)}MB."
        )

# -----------------------------------------------------------------------------
# Stage 2: Speech-to-Text Adapter
# -----------------------------------------------------------------------------

async def stage_2_transcribe(
    audio_bytes: bytes,
    source_language: str,
    browser_transcript: Optional[str]
) -> Tuple[str, str]:
    """
    Transcribes speech to text. Uses browser transcript if provided.
    Calls configured STT provider (Bhashini or Whisper) if audio is supplied.
    Raises explicit error if no provider is configured.
    """
    if browser_transcript and len(browser_transcript.strip()) > 0:
        return browser_transcript.strip(), "browser_web_speech"

    bhashini_key = os.getenv("BHASHINI_API_KEY")
    bhashini_pipeline_id = os.getenv("BHASHINI_PIPELINE_ID")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Provider 1: ULCA Bhashini ASR Pipeline
    if bhashini_key and bhashini_pipeline_id:
        try:
            bhashini_url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
            headers = {
                "Accept": "*/*",
                "User-Agent": "NyayaConnect/1.0",
                "Authorization": bhashini_key,
                "Content-Type": "application/json"
            }
            payload = {
                "pipelineTasks": [
                    {
                        "taskType": "asr",
                        "config": {
                            "language": {
                                "sourceLanguage": source_language.split("-")[0]
                            }
                        }
                    }
                ],
                "inputData": {
                    "audio": [
                        {
                            "audioContent": base64.b64encode(audio_bytes).decode("utf-8")
                        }
                    ]
                }
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(bhashini_url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    transcription = (
                        data.get("pipelineResponse", [{}])[0]
                        .get("output", [{}])[0]
                        .get("source", "")
                    )
                    if transcription.strip():
                        return transcription.strip(), "bhashini_asr"
        except Exception as e:
            logger.error(f"Bhashini ASR provider request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Configured Bhashini speech service failed: {str(e)}"
            )

    # Provider 2: OpenAI Whisper API
    if openai_key:
        try:
            headers = {"Authorization": f"Bearer {openai_key}"}
            files = {"file": ("audio.webm", audio_bytes, "audio/webm")}
            data = {"model": "whisper-1", "language": source_language.split("-")[0]}
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data)
                if res.status_code == 200:
                    text = res.json().get("text", "")
                    if text.strip():
                        return text.strip(), "openai_whisper"
        except Exception as e:
            logger.error(f"OpenAI Whisper request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Configured Whisper speech service failed: {str(e)}"
            )

    # No STT provider configured and no transcript provided
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "No speech recognition provider configured on backend (BHASHINI_API_KEY or OPENAI_API_KEY missing) "
            "and no browser transcript was provided. Enable Web Speech in browser or configure STT credentials."
        )
    )

# -----------------------------------------------------------------------------
# Stage 3: Translation Adapter (Vernacular -> English)
# -----------------------------------------------------------------------------

async def stage_3_translate_to_english(vernacular_text: str, source_language: str) -> str:
    """
    Translates vernacular query into English for RAG engine.
    If source language is English, returns text directly.
    Otherwise invokes configured translation provider (Bhashini or Google/OpenAI).
    """
    if source_language.startswith("en"):
        return vernacular_text

    bhashini_key = os.getenv("BHASHINI_API_KEY")
    google_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Provider 1: Bhashini NMT
    if bhashini_key:
        try:
            bhashini_url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
            headers = {
                "Authorization": bhashini_key,
                "Content-Type": "application/json"
            }
            src_lang = source_language.split("-")[0]
            payload = {
                "pipelineTasks": [
                    {
                        "taskType": "translation",
                        "config": {
                            "language": {
                                "sourceLanguage": src_lang,
                                "targetLanguage": "en"
                            }
                        }
                    }
                ],
                "inputData": {
                    "input": [{"source": vernacular_text}]
                }
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(bhashini_url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    translated = (
                        data.get("pipelineResponse", [{}])[0]
                        .get("output", [{}])[0]
                        .get("target", "")
                    )
                    if translated.strip():
                        return translated.strip()
        except Exception as e:
            logger.warning(f"Bhashini translation error: {e}")

    # Provider 2: Google Cloud Translation
    if google_key:
        try:
            url = f"https://translation.googleapis.com/language/translate/v2?key={google_key}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, json={
                    "q": vernacular_text,
                    "source": source_language.split("-")[0],
                    "target": "en",
                    "format": "text"
                })
                if res.status_code == 200:
                    return res.json()["data"]["translations"][0]["translatedText"]
        except Exception as e:
            logger.warning(f"Google Translate error: {e}")

    # Provider 3: OpenAI GPT-based legal translation
    if openai_key:
        try:
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a professional legal translator. Translate the given Indian vernacular legal inquiry into precise English. Preserve all legal and factual terms."},
                    {"role": "user", "content": vernacular_text}
                ],
                "temperature": 0.0
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"OpenAI translation error: {e}")

    # Explicit failure when vernacular input cannot be translated
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            f"Vernacular query provided in {SUPPORTED_LANGUAGES[source_language]}, but no translation service "
            "(BHASHINI_API_KEY, GOOGLE_TRANSLATE_API_KEY, or OPENAI_API_KEY) is configured on the backend. "
            "Please provide an English query or configure translation credentials in .env."
        )
    )

# -----------------------------------------------------------------------------
# Stage 4: Citation Preservation & Vernacular Translation
# -----------------------------------------------------------------------------

CITATION_PATTERN = re.compile(
    r"\b(Article\s+\d+[A-Z]?|Section\s+\d+[A-Z]?|Order\s+[IVXLCDM]+\s+Rule\s+\d+|Schedule\s+\d+|Part\s+[IVXLCDM]+)\b",
    re.IGNORECASE
)

def tokenize_all_citations(text: str) -> Tuple[str, Dict[str, str], List[str]]:
    """
    Finds and tokenizes EVERY citation in the text with unique indexed tokens.
    Never hallucinates or inserts citations that are not in the source text.
    """
    token_map = {}
    found_citations = []
    
    matches = list(CITATION_PATTERN.finditer(text))
    if not matches:
        return text, {}, []

    # Replace from end to start so character offsets remain valid
    modified_text = text
    for idx, match in enumerate(matches):
        citation = match.group(0)
        found_citations.append(citation)
        token = f"__LEGAL_CITATION_{idx}__"
        token_map[token] = citation

    # Substitute tokens
    for token, citation in token_map.items():
        modified_text = re.sub(re.escape(citation), token, modified_text, count=1)

    return modified_text, token_map, found_citations

def restore_all_citations(translated_text: str, token_map: Dict[str, str], original_citations: List[str]) -> Tuple[str, bool]:
    """
    Restores citations from token_map. Detects if translation dropped any tokens.
    Returns (restored_text, all_tokens_preserved).
    """
    restored = translated_text
    all_preserved = True

    for token, original_citation in token_map.items():
        if token in restored:
            restored = restored.replace(token, original_citation)
        else:
            all_preserved = False

    # If any token was dropped by the translation service, append missing citations safely
    if not all_preserved and original_citations:
        restored += f" [Legal Citations: {', '.join(original_citations)}]"

    return restored, all_preserved

async def stage_4_translate_to_vernacular(
    english_explanation: str,
    target_language: str
) -> Tuple[str, List[str]]:
    """
    Translates English legal advice into target native language while strictly
    preserving every Constitutional Article / Statutory citation.
    """
    # 1. Protect all citations in the source text
    tokenized_text, token_map, original_citations = tokenize_all_citations(english_explanation)

    if target_language.startswith("en"):
        # For English, return source explanation directly
        return english_explanation, original_citations

    bhashini_key = os.getenv("BHASHINI_API_KEY")
    google_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    tgt_lang = target_language.split("-")[0]

    raw_translated = None

    # Translation via Bhashini
    if bhashini_key:
        try:
            bhashini_url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
            headers = {"Authorization": bhashini_key, "Content-Type": "application/json"}
            payload = {
                "pipelineTasks": [{"taskType": "translation", "config": {"language": {"sourceLanguage": "en", "targetLanguage": tgt_lang}}}],
                "inputData": {"input": [{"source": tokenized_text}]}
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(bhashini_url, json=payload, headers=headers)
                if res.status_code == 200:
                    raw_translated = res.json().get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("target", "")
        except Exception as e:
            logger.warning(f"Bhashini reverse translation error: {e}")

    # Translation via Google
    if not raw_translated and google_key:
        try:
            url = f"https://translation.googleapis.com/language/translate/v2?key={google_key}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, json={"q": tokenized_text, "source": "en", "target": tgt_lang, "format": "text"})
                if res.status_code == 200:
                    raw_translated = res.json()["data"]["translations"][0]["translatedText"]
        except Exception as e:
            logger.warning(f"Google reverse translation error: {e}")

    # Translation via OpenAI
    if not raw_translated and openai_key:
        try:
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": f"Translate this legal explanation into {SUPPORTED_LANGUAGES[target_language]}. IMPORTANT: Do NOT alter or translate tokens formatted like __LEGAL_CITATION_0__; keep them exactly as they are."},
                    {"role": "user", "content": tokenized_text}
                ],
                "temperature": 0.0
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    raw_translated = res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"OpenAI reverse translation error: {e}")

    # Fallback when reverse translation provider is not active:
    # Safely return the English explanation with preserved citations rather than crashing or faking
    if not raw_translated:
        return english_explanation, original_citations

    # Restore every citation into the translated text
    final_text, _ = restore_all_citations(raw_translated, token_map, original_citations)
    return final_text, original_citations

# -----------------------------------------------------------------------------
# RAG Service Bridge
# -----------------------------------------------------------------------------

async def query_rag_engine(english_query: str) -> Dict[str, Any]:
    """Queries ChromaDB RAG Service on port 8001."""
    target_urls = [
        f"{RAG_SERVICE_URL}/rag/ask",
        f"{RAG_LOCAL_URL}/rag/ask"
    ]
    last_error = None
    for url in target_urls:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(url, json={"query": english_query})
                if res.status_code == 200:
                    return res.json()
                last_error = f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            last_error = str(e)
            continue

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Constitutional RAG microservice is unreachable at {RAG_SERVICE_URL}. Error: {last_error}"
    )

# -----------------------------------------------------------------------------
# Route Endpoints
# -----------------------------------------------------------------------------

@router.post("/ask", response_model=VoiceAskResponse, summary="Vernacular Voice-to-RAG 4-Stage Bridge")
async def voice_ask_endpoint(
    audio_file: Optional[UploadFile] = File(None, description="Audio blob recorded in browser"),
    source_language: str = Form("kn-IN", description="Supported BCP-47 language code"),
    browser_transcript: Optional[str] = Form(None, description="Web Speech API fallback transcript")
):
    """
    Exposes POST /api/v1/voice/ask handling multipart/form-data.
    Executes real 4-stage pipeline with strict validation and error handling.
    """
    start_time = time.time()

    # Stage 1: Bounded Streaming Read & Validation (Strict 10MB Cap)
    valid_lang = validate_language_code(source_language)
    audio_bytes = b""
    if audio_file:
        CHUNK_SIZE = 64 * 1024
        total_bytes = 0
        chunks = []
        while True:
            chunk = await audio_file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_AUDIO_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Audio file exceeds maximum size limit of {MAX_AUDIO_BYTES // (1024 * 1024)}MB."
                )
            chunks.append(chunk)
        audio_bytes = b"".join(chunks)
    validate_audio_payload(audio_bytes, browser_transcript)

    # Stage 2: STT
    vernacular_text, speech_source = await stage_2_transcribe(
        audio_bytes=audio_bytes,
        source_language=valid_lang,
        browser_transcript=browser_transcript
    )

    # Stage 3: Translation to English
    english_query = await stage_3_translate_to_english(vernacular_text, valid_lang)

    # Query RAG engine
    rag_result = await query_rag_engine(english_query)
    raw_explanation = rag_result.get("explanation", "")

    # Stage 4: Reverse translation with citation preservation
    translated_explanation, preserved_citations = await stage_4_translate_to_vernacular(
        raw_explanation, valid_lang
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return VoiceAskResponse(
        success=True,
        source_language=valid_lang,
        speech_source=speech_source,
        transcribed_vernacular_text=vernacular_text,
        translated_english_query=english_query,
        constitutional_articles=[ArticleCitation(**art) for art in rag_result.get("articles", [])],
        recommended_case_category=rag_result.get("recommended_case_category", "Consumer"),
        translated_explanation=translated_explanation,
        original_english_explanation=raw_explanation,
        preserved_citations=preserved_citations,
        pipeline_latency_ms=elapsed_ms
    )

@router.post("/ask-json", response_model=VoiceAskResponse, summary="Vernacular Voice Pipeline JSON Alternative")
async def voice_ask_json_endpoint(payload: VoiceAskJSONRequest = Body(...)):
    """
    JSON alternative endpoint accepting base64 audio or browser transcript.
    """
    start_time = time.time()

    valid_lang = validate_language_code(payload.source_language)
    audio_bytes = b""
    if payload.audio_base64:
        # Pre-check base64 encoded length against 10MB binary limit (~13.33MB)
        if len(payload.audio_base64) > int(MAX_AUDIO_BYTES * 4 / 3) + 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Audio payload exceeds maximum size limit of {MAX_AUDIO_BYTES // (1024 * 1024)}MB."
            )
        try:
            audio_bytes = base64.b64decode(payload.audio_base64, validate=True)
            if len(audio_bytes) > MAX_AUDIO_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Audio file exceeds maximum size limit of {MAX_AUDIO_BYTES // (1024 * 1024)}MB."
                )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed base64 audio string.")

    validate_audio_payload(audio_bytes, payload.transcript)

    vernacular_text, speech_source = await stage_2_transcribe(
        audio_bytes=audio_bytes,
        source_language=valid_lang,
        browser_transcript=payload.transcript
    )

    english_query = await stage_3_translate_to_english(vernacular_text, valid_lang)
    rag_result = await query_rag_engine(english_query)
    raw_explanation = rag_result.get("explanation", "")

    translated_explanation, preserved_citations = await stage_4_translate_to_vernacular(
        raw_explanation, valid_lang
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return VoiceAskResponse(
        success=True,
        source_language=valid_lang,
        speech_source=speech_source,
        transcribed_vernacular_text=vernacular_text,
        translated_english_query=english_query,
        constitutional_articles=[ArticleCitation(**art) for art in rag_result.get("articles", [])],
        recommended_case_category=rag_result.get("recommended_case_category", "Consumer"),
        translated_explanation=translated_explanation,
        original_english_explanation=raw_explanation,
        preserved_citations=preserved_citations,
        pipeline_latency_ms=elapsed_ms
    )
