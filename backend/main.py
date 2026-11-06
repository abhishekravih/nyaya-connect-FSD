"""
NyayaConnect Marketplace Backend Service & Integration Hub (FastAPI)
Unified Backend integrating:
- Person 2: Relational SQL Database, Lawyer Directory, Smart Milestones, and JWT Auth
- Person 4: Vernacular Voice Pipeline, Composite Orchestrator, and Health Diagnostics
File: /backend/main.py
"""

import os
import sys

# Ensure current directory and parent directory are on PYTHONPATH
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

import logging
import httpx
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("nyayaconnect.backend")

# Database setup (auto-creates tables on boot)
try:
    from database import engine, Base, check_db_health
except ImportError:
    from backend.database import engine, Base, check_db_health

import models
Base.metadata.create_all(bind=engine)

# Instantiate unified FastAPI application
app = FastAPI(
    title="NyayaConnect Marketplace API & Integration Hub",
    description="Unified API Gateway connecting Person 1 (Next.js), Person 2 (FastAPI Marketplace & DB), Person 3 (RAG AI), and Person 4 (DevOps & Voice)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# -----------------------------------------------------------------------------
# Standardized CORS Middleware Configuration (Explicit Origins)
# -----------------------------------------------------------------------------
DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://nyayaconnect.vercel.app",
    "https://nyaya-connect-fsd.vercel.app"
]
env_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
allowed_origins = list(set(DEFAULT_ORIGINS + env_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type"]
)

# -----------------------------------------------------------------------------
# Include Routers (Person 2 Core Marketplace + Person 4 Integration Bridges)
# -----------------------------------------------------------------------------
try:
    from routers import auth, lawyers, bookings
    from routers.voice_bridge import router as voice_router
    from routers.orchestrator import router as orchestrator_router
except ImportError:
    from backend.routers import auth, lawyers, bookings
    from backend.routers.voice_bridge import router as voice_router
    from backend.routers.orchestrator import router as orchestrator_router

app.include_router(auth.router)
app.include_router(lawyers.router)
app.include_router(bookings.router)
app.include_router(voice_router)
app.include_router(orchestrator_router)

# Mount root aliases for Person 1 Next.js client compatibility (/bookings, /lawyers)
app.include_router(bookings.router, prefix="", include_in_schema=False)
app.include_router(lawyers.router, prefix="", include_in_schema=False)

# -----------------------------------------------------------------------------
# Frontend Compatibility Bridges for Person 1
# -----------------------------------------------------------------------------
from pydantic import BaseModel
class LegalQuestionBridgeRequest(BaseModel):
    query: str
    lang: str = "English"

LANGUAGE_COMPAT_MAP = {
    "kannada": "kn-IN",
    "hindi": "hi-IN",
    "tamil": "ta-IN",
    "telugu": "te-IN",
    "marathi": "mr-IN",
    "bengali": "bn-IN",
    "english": "en-IN"
}

def resolve_compat_language(lang_str: str) -> str:
    lower_lang = str(lang_str).lower().strip()
    for name, code in LANGUAGE_COMPAT_MAP.items():
        if name in lower_lang or code.lower() in lower_lang:
            return code
    return "en-IN"

@app.post("/api/v1/legal-question", tags=["Frontend Compatibility"])
@app.post("/legal-question", tags=["Frontend Compatibility"])
async def legal_question_compatibility(payload: LegalQuestionBridgeRequest):
    from backend.routers.orchestrator import orchestrate_legal_assist, LegalAssistRequest
    lang_code = resolve_compat_language(payload.lang)
    res = await orchestrate_legal_assist(LegalAssistRequest(
        query=payload.query,
        source_language=lang_code
    ))
    return {
        "answer_text": res.explanation,
        "cited_articles": [a.model_dump() for a in res.constitutional_articles],
        "recommended_category": res.category,
        "recommended_lawyers": [l.model_dump() for l in res.recommended_lawyers],
        "confidence_score": None
    }

@app.post("/api/v1/voice-query", tags=["Frontend Compatibility"])
@app.post("/voice-query", tags=["Frontend Compatibility"])
async def voice_query_compatibility(payload: dict):
    from backend.routers.voice_bridge import voice_ask_json_endpoint, VoiceAskJSONRequest
    blob = payload.get("blob", "")
    lang = payload.get("lang", "English")
    transcript = payload.get("transcript") or payload.get("browser_transcript")
    lang_code = resolve_compat_language(lang)

    return await voice_ask_json_endpoint(VoiceAskJSONRequest(
        audio_base64=blob if isinstance(blob, str) and len(blob) > 0 else None,
        transcript=transcript if isinstance(transcript, str) and len(transcript.strip()) > 0 else None,
        source_language=lang_code
    ))

# -----------------------------------------------------------------------------
# Health Check & Gateway Diagnostics
# -----------------------------------------------------------------------------
@app.get("/health", tags=["Health & Diagnostics"])
@app.get("/health/live", tags=["Health & Diagnostics"])
@app.get("/api/v1/health", tags=["Health & Diagnostics"])
async def health_live():
    """Liveness probe: verifies process is alive and responding."""
    return {
        "status": "healthy",
        "service": "NyayaConnect Marketplace Backend",
        "port": int(os.getenv("PORT", "8000")),
        "sdg_alignment": "SDG 16: Peace, Justice, and Strong Institutions"
    }

@app.get("/health/ready", tags=["Health & Diagnostics"])
async def health_ready():
    """
    Readiness probe: actually checks connectivity to SQL database and RAG microservice.
    Returns HTTP 503 if any required dependency is unavailable.
    """
    db_ok, db_msg = check_db_health()

    rag_ok = False
    rag_url = os.getenv("RAG_SERVICE_URL", "http://rag_service:8001/api/v1")
    rag_local = os.getenv("RAG_LOCAL_URL", "http://127.0.0.1:8001/api/v1")

    for url in [rag_url.replace("/api/v1", "/health"), rag_local.replace("/api/v1", "/health"), "http://localhost:8001/health"]:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    rag_ok = True
                    break
        except Exception:
            continue

    all_ready = db_ok and rag_ok
    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "ready": all_ready,
            "database": {"status": "connected" if db_ok else "unreachable", "detail": db_msg},
            "rag_service": {"status": "connected" if rag_ok else "unreachable", "target": rag_url}
        }
    )

@app.get("/", tags=["Root"])
def root_index():
    return {
        "status": "healthy",
        "project": "NyayaConnect Full-Stack Legal Advisor",
        "service": "NyayaConnect Headless REST API & Gateway",
        "port": 8000,
        "docs": "/docs",
        "documentation": "/docs",
        "sdg_alignment": "SDG 16: Peace, Justice, and Strong Institutions",
        "endpoints": {
            "auth_register": "POST /api/v1/auth/register",
            "auth_login": "POST /api/v1/auth/login",
            "lawyers_list": "GET /api/v1/lawyers",
            "lawyers_detail": "GET /api/v1/lawyers/{lawyer_id}",
            "lawyers_recommend": "POST /api/v1/lawyers/recommend",
            "bookings_create": "POST /api/v1/bookings",
            "direct_booking": "POST /api/v1/lawyers/book",
            "dashboard_bookings": "GET /api/v1/lawyers/bookings",
            "milestone_update": "PATCH /api/v1/bookings/{booking_id}/milestones/{stage_no}",
            "vernacular_voice_ask": "POST /api/v1/voice/ask",
            "unified_orchestration": "POST /api/v1/orchestrate/legal-assist",
            "health_live": "GET /health/live",
            "health_ready": "GET /health/ready"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
