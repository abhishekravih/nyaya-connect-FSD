# =====================================================================
# NyayaConnect Backend Dockerfile (Person 4: System Integration)
# Service: FastAPI Marketplace & Vernacular Voice Bridge (Port 8000)
# =====================================================================

FROM python:3.11-slim as runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install security updates and curl for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in isolated layer for build caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend application source
COPY . /app/backend

# Add /app to PYTHONPATH so backend package imports resolve cleanly
ENV PYTHONPATH="/app"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
