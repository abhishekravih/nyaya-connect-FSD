"""
NyayaConnect - Canonical Legal RAG Server Entry Point
Re-exports the unified FastAPI app from main.py to eliminate architectural drift (Reviewer Upgrade 5).
"""

import os
import uvicorn
from main import app, AskRequest, ComprehensiveRAGResponse

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    # Reviewer Item 1 Fix: Default fallback to 8001 to prevent port collision with Person 4 backend on 8000
    port = int(os.getenv("PORT", 8001))
    print(f"🚀 Starting NyayaConnect Legal RAG Server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
