"""
Unit & Integration Tests for Vernacular Voice-to-RAG Pipeline
File: backend/tests/test_voice_bridge.py
"""

import pytest
from backend.routers.voice_bridge import (
    validate_language_code,
    validate_audio_payload,
    tokenize_all_citations,
    restore_all_citations,
    SUPPORTED_LANGUAGES
)
from fastapi import HTTPException

def test_language_code_validation():
    # Valid BCP-47 codes
    for lang in ["kn-IN", "hi-IN", "ta-IN", "te-IN", "en-IN"]:
        assert validate_language_code(lang) == lang

    # Invalid codes raise HTTP 400
    with pytest.raises(HTTPException) as exc_info:
        validate_language_code("fr-FR")
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        validate_language_code("unknown")
    assert exc_info.value.status_code == 400

def test_audio_payload_validation():
    # Valid browser transcript
    validate_audio_payload(b"", "Legal query in Kannada")

    # Valid audio bytes
    validate_audio_payload(b"RIFF....dummyWAV", None)

    # Empty payload raises HTTP 400
    with pytest.raises(HTTPException) as exc_info:
        validate_audio_payload(b"", None)
    assert exc_info.value.status_code == 400

    # Oversized audio payload raises HTTP 413
    oversized = b"x" * (11 * 1024 * 1024) # 11MB
    with pytest.raises(HTTPException) as exc_info:
        validate_audio_payload(oversized, None)
    assert exc_info.value.status_code == 413

def test_multiple_citation_tokenization_and_preservation():
    source_text = (
        "Under the Consumer Protection Act read with Article 21 and Article 39A of the Constitution of India, "
        "and Section 35 of the Act, consumers have statutory protection."
    )

    tokenized, token_map, citations = tokenize_all_citations(source_text)

    # Must find all 3 citations
    assert len(citations) == 3
    assert "Article 21" in citations
    assert "Article 39A" in citations
    assert "Section 35" in citations

    # Tokens must be substituted
    assert "__LEGAL_CITATION_0__" in tokenized
    assert "__LEGAL_CITATION_1__" in tokenized
    assert "__LEGAL_CITATION_2__" in tokenized

    # Simulated translation preserving tokens
    translated = tokenized.replace("consumers have statutory protection", "ಗ್ರಾಹಕರಿಗೆ ಶಾಸನಬದ್ಧ ರಕ್ಷಣೆ ಇದೆ")

    # Restore tokens
    restored, all_preserved = restore_all_citations(translated, token_map, citations)
    assert all_preserved is True
    assert "Article 21" in restored
    assert "Article 39A" in restored
    assert "Section 35" in restored

def test_no_hallucinated_citations():
    # When source text contains NO citations, token map should be empty and none hallucinated
    plain_text = "This is a basic dispute over unpaid rent between landlord and tenant."
    tokenized, token_map, citations = tokenize_all_citations(plain_text)
    assert len(citations) == 0
    assert token_map == {}
    assert tokenized == plain_text
