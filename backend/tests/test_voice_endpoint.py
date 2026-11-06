"""
Full HTTP Route Tests for Vernacular Voice-to-RAG Pipeline
Tests POST /api/v1/voice/ask and POST /api/v1/voice/ask-json with multipart and validation constraints.
"""

from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import io
from main import app

client = TestClient(app)

MOCK_RAG_RESPONSE = {
    "recommended_case_category": "Criminal",
    "explanation": "Under Article 22 of the Constitution of India, an arrested individual has the right to be informed of the grounds of arrest and consult legal counsel.",
    "articles": [
        {
            "article_number": "Article 22",
            "title": "Protection against arrest and detention in certain cases",
            "relevance_summary": "Guarantees right to consult an advocate of choice."
        }
    ]
}

def test_voice_ask_multipart_with_browser_transcript():
    """Verify POST /api/v1/voice/ask accepts multipart/form-data with browser fallback transcript."""
    with patch("backend.routers.voice_bridge.query_rag_engine", new=AsyncMock(return_value=MOCK_RAG_RESPONSE)):
        res = client.post(
            "/api/v1/voice/ask",
            data={
                "source_language": "kn-IN",
                "browser_transcript": "ನನ್ನನ್ನು ಬಂಧಿಸಿದರೆ ನನಗೆ ಯಾವ ಹಕ್ಕುಗಳಿವೆ?"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["source_language"] == "kn-IN"
        assert data["speech_source"] == "browser_web_speech"
        assert data["recommended_case_category"] == "Criminal"
        assert len(data["constitutional_articles"]) == 1
        assert data["constitutional_articles"][0]["article_number"] == "Article 22"
        # Citations preserved
        assert "Article 22" in data["translated_explanation"]

def test_voice_ask_multipart_rejects_empty_payload():
    """Verify endpoint rejects requests that provide neither audio nor browser transcript with HTTP 400."""
    res = client.post(
        "/api/v1/voice/ask",
        data={"source_language": "kn-IN"}
    )
    assert res.status_code == 400
    assert "Either an audio file or a browser-supplied transcript must be provided" in res.json()["detail"]

def test_voice_ask_multipart_rejects_unsupported_language():
    """Verify endpoint rejects unsupported language codes with HTTP 400."""
    res = client.post(
        "/api/v1/voice/ask",
        data={
            "source_language": "fr-FR",
            "browser_transcript": "Bonjour"
        }
    )
    assert res.status_code == 400
    assert "Unsupported language code" in res.json()["detail"]

def test_voice_ask_multipart_rejects_oversized_audio():
    """Verify endpoint rejects audio files exceeding 10MB limit with HTTP 413."""
    oversized_data = io.BytesIO(b"x" * (11 * 1024 * 1024))
    res = client.post(
        "/api/v1/voice/ask",
        files={"audio_file": ("large_sample.wav", oversized_data, "audio/wav")},
        data={"source_language": "en-IN"}
    )
    assert res.status_code == 413
    assert "exceeds maximum size limit" in res.json()["detail"]
