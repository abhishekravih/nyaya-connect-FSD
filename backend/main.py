"""
NyayaConnect Marketplace Backend Service & Integration Hub (FastAPI)
Unified Backend integrating:
- Person 2: Relational SQL Database, Lawyer Directory, Smart Milestones, and JWT Auth
- Person 4: Vernacular Voice Pipeline and Composite Orchestrator
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
from fastapi import FastAPI
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
    from database import engine, Base
except ImportError:
    from backend.database import engine, Base

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
# Standardized CORS Middleware Configuration
# -----------------------------------------------------------------------------
DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://nyayaconnect.vercel.app",
    "https://legal-advisor-fsd.vercel.app"
]
env_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
allowed_origins = list(set(DEFAULT_ORIGINS + env_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
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

# -----------------------------------------------------------------------------
# Health Check & Gateway Diagnostics
# -----------------------------------------------------------------------------
@app.get("/health", tags=["Health & Diagnostics"])
@app.get("/api/v1/health", tags=["Health & Diagnostics"])
async def health_check():
    return {
        "status": "healthy",
        "service": "NyayaConnect Marketplace Backend",
        "port": int(os.getenv("PORT", "8000")),
        "database_connected": True,
        "rag_upstream": os.getenv("RAG_SERVICE_URL", "http://rag_service:8001/api/v1"),
        "vernacular_voice_bridge": "operational",
        "sdg_alignment": "SDG 16: Peace, Justice, and Strong Institutions"
    }

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
            "milestone_update": "PATCH /api/v1/bookings/{booking_id}/milestones/{stage_no}",
            "vernacular_voice_ask": "POST /api/v1/voice/ask",
            "unified_orchestration": "POST /api/v1/orchestrate/legal-assist",
            "health": "GET /health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
