"""
NyayaConnect Marketplace Backend Service (FastAPI)
Person 4: System Integration & DevOps Lead
File: /backend/main.py
"""

import os
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

# Instantiate FastAPI application
app = FastAPI(
    title="NyayaConnect Marketplace API & Integration Hub",
    description="Unified API Gateway connecting Person 1 (Next.js), Person 2 (Marketplace), and Person 3 (ChromaDB RAG)",
    version="1.0.0"
)

# -----------------------------------------------------------------------------
# Standardized CORS Middleware Configuration
# Allows requests from Vercel-hosted production frontend, local dev, and preview branches
# -----------------------------------------------------------------------------
env_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]

# Default permitted origins
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://nyayaconnect.vercel.app",
    "https://legal-advisor-fsd.vercel.app"
]

for origin in default_origins:
    if origin not in allowed_origins:
        allowed_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Permits all dynamic Vercel preview branch deployments
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type"]
)

# -----------------------------------------------------------------------------
# Include Service Routers
# -----------------------------------------------------------------------------
from backend.routers.voice_bridge import router as voice_router
from backend.routers.orchestrator import router as orchestrator_router
from backend.routers.lawyers import router as lawyers_router

app.include_router(voice_router)
app.include_router(orchestrator_router)
app.include_router(lawyers_router)

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
        "vernacular_voice_bridge": "operational"
    }

@app.get("/", tags=["Root"])
async def root_index():
    return JSONResponse({
        "project": "NyayaConnect Full-Stack Legal Advisor",
        "lead": "Person 4: Systems Integration & DevOps",
        "documentation": "/docs",
        "endpoints": {
            "vernacular_voice_ask": "POST /api/v1/voice/ask",
            "unified_orchestration": "POST /api/v1/orchestrate/legal-assist",
            "lawyers_marketplace": "GET /api/v1/lawyers",
            "book_consultation": "POST /api/v1/lawyers/book",
            "health": "GET /health"
        }
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
