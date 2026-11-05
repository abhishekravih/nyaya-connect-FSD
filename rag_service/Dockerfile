# =====================================================================
# NyayaConnect RAG Service Dockerfile (Person 4: System Integration)
# Service: ChromaDB Vector Store & Constitutional Engine (Port 8001)
# =====================================================================

FROM python:3.11-slim as runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8001 \
    CHROMA_PERSIST_DIRECTORY=/app/chroma_db

WORKDIR /app

# Install security updates and build dependencies required by ChromaDB / hnswlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Create persistent storage directory for ChromaDB
RUN mkdir -p /app/chroma_db

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
