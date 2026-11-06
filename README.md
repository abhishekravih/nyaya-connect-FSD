# NyayaConnect: Vernacular Legal Advisor & Lawyer Marketplace (FSD)

[![NyayaConnect CI](https://github.com/abhishekravih/nyaya-connect-FSD/actions/workflows/ci.yml/badge.svg)](https://github.com/abhishekravih/nyaya-connect-FSD/actions)
[![Antigravity Full-Stack](https://img.shields.io/badge/Antigravity-2.0-blue.svg)](https://github.com/abhishekravih/nyaya-connect-FSD)
[![SDG 16](https://img.shields.io/badge/SDG%2016-Peace%2C%20Justice%20%26%20Strong%20Institutions-blueviolet)](https://sdgs.un.org/goals/goal16)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js&logoColor=white)](https://nextjs.org)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-orange)](https://www.trychroma.com)

**NyayaConnect** is an integrated full-stack legal intelligence and marketplace platform engineered inside Google Antigravity. It empowers Indian citizens to ask legal questions in regional languages (Kannada, Hindi, Tamil, Telugu, Marathi, Bengali, English), grounds answers in the Constitution of India via ChromaDB RAG, and instantly connects citizens with verified affordable advocates with transparent pricing and 4 Smart Milestones.

---

## 🏛️ Person 4: Systems Integration & DevOps Architecture

As **Person 4 (Systems Integrator and DevOps Lead)**, this repository establishes the unified multi-service monorepo, container orchestration, Git worktree workflow, vernacular voice translation pipeline, and composite API gateway.

```
nyaya-connect-FSD/
├── .antigravity/
│   └── workflows/
│       └── sync-stack.md           # Safe Git worktree & branch sync workflow with collision checks
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI matrix: Frontend, Backend tests, RAG eval, Compose
├── backend/                        # Person 2 & 4 (FastAPI Marketplace Backend & Integration Gateway)
│   ├── auth/                       # JWT auth & security
│   ├── routers/
│   │   ├── voice_bridge.py         # 4-Stage Vernacular Voice-to-RAG Pipeline with streaming 10MB cap
│   │   ├── orchestrator.py         # Composite 'Ask -> Classify -> Recommend' API Gateway
│   │   ├── lawyers.py              # Lawyer marketplace, direct booking, privacy phone masking
│   │   └── bookings.py             # 4-stage smart milestone bookings (15%, 25%, 30%, 30%)
│   ├── tests/
│   │   ├── conftest.py             # Self-contained test fixture and isolated DB initialiser
│   │   ├── test_lawyers.py         # SQL lawyer retrieval and booking unit & integration tests
│   │   ├── test_health.py          # Liveness & readiness probe tests
│   │   ├── test_voice_bridge.py    # Voice pipeline & legal citation tokenization tests
│   │   └── test_marketplace.py    # Marketplace fee split & category audit tests
│   ├── database.py                 # Resilient SQLAlchemy engine with URL.create for MySQL
│   ├── schema.sql                  # MySQL 8.0 schema mapped to /docker-entrypoint-initdb.d
│   ├── seed_data.py                # 30 realistic Indian lawyers across Civil, Consumer, Criminal
│   ├── requirements.txt            # Python dependencies
│   ├── main.py                     # CORS middleware, route registration, and health probes
│   └── Dockerfile                  # Container runtime
├── frontend/                       # Person 1 (Next.js 14 Vernacular UI)
│   ├── src/
│   │   ├── app/                    # Next.js App Router (marketplace, bookings, chat)
│   │   ├── components/             # ChatWindow, VoiceRecorderBar, LawyerCard, MilestoneTracker
│   │   ├── services/
│   │   │   ├── apiClient.js        # Multipart audio upload & live API client
│   │   │   └── apiClient.ts        # Typed API contracts
│   │   └── utils/
│   │       └── voiceFallback.ts    # Web Speech API zero-latency fallback engine
│   ├── package.json
│   ├── next.config.js
│   └── Dockerfile                  # Multi-stage production container
├── rag_service/                    # Person 3 (ChromaDB Constitutional Engine)
│   ├── chroma_db/                  # Persistent vector database volume
│   ├── main.py                     # /health, /health/live, /health/ready, and POST /api/v1/rag/ask
│   ├── requirements.txt
│   └── Dockerfile                  # Python container with ChromaDB & vector index
├── docs/
│   └── evidence/                   # Release verification evidence, HAR network trace, test logs
├── .env.example                    # Standardized port and environment template
├── docker-compose.yml              # Master 4-service container orchestration
└── README.md
```

---

## 🔌 Standardized Port Allocations

All service ports are standardized across Docker containers and local development:

| Service | Port | Host Address | Description |
| :--- | :--- | :--- | :--- |
| **Frontend** | `3000` | `http://localhost:3000` | Next.js 14 Vernacular UI & Citizen Portal |
| **Marketplace Backend** | `8000` | `http://localhost:8000` | FastAPI Backend & Systems Integration Gateway |
| **Constitutional RAG** | `8001` | `http://localhost:8001` | ChromaDB Constitutional RAG Microservice |
| **Database** | `3306` | `localhost:3306` | MySQL 8.0 Relational Database |

---

## 🚀 Quickstart & Runbook

### Option A: 1-Command Boot with Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/abhishekravih/nyaya-connect-FSD.git
cd nyaya-connect-FSD

# 2. Copy environment template
cp .env.example .env
# Edit .env and supply your DB_PASSWORD and GEMINI_API_KEY

# 3. Boot all 4 containers with Docker Compose
docker compose up --build -d

# 4. Access services
# Frontend:            http://localhost:3000
# Backend Swagger:     http://localhost:8000/docs
# RAG Service Swagger: http://localhost:8001/docs
```

### Option B: Local Direct Execution (Windows / Linux)

When running services directly on the host machine outside Docker:
- Set `DB_HOST=localhost` in your local `.env` (inside Docker, `DB_HOST=db` resolves via Docker network DNS).
- Database falls back gracefully to local SQLite (`nyayaconnect.db`) if MySQL is not running on localhost:3306.

```bash
# 1. Run Backend
cd backend
pip install -r requirements.txt
python seed_data.py
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 2. Run RAG Service
cd ../rag_service
pip install -r requirements.txt
uvicorn main:main --host 0.0.0.0 --port 8001 --reload

# 3. Run Frontend
cd ../frontend
npm install
npm run dev
```

---

## 🎙️ Vernacular Voice-to-RAG Pipeline

The integration gateway exposes `POST /api/v1/voice/ask` executing a 4-stage pipeline:

```
[Citizen Audio (WebM/WAV) or Browser Transcript]
                      │
                      ▼
 ┌────────────────────────────────────────────────────────┐
 │ Stage 1: Input Validation & Streaming 10MB Cap         │
 │ - Validates BCP-47 language (kn-IN, hi-IN, ta-IN, etc) │
 │ - Enforces 10MB max binary size via 64KB chunk stream  │
 └────────────────────────────┬───────────────────────────┘
                              ▼
 ┌────────────────────────────────────────────────────────┐
 │ Stage 2: Speech-to-Text Transcription                  │
 │ - Uses Web Speech API transcript if provided (0ms)     │
 │ - Falls back to Bhashini ASR or OpenAI Whisper         │
 └────────────────────────────┬───────────────────────────┘
                              ▼
 ┌────────────────────────────────────────────────────────┐
 │ Stage 3: Vernacular to English Translation             │
 │ - Converts regional query to canonical English query   │
 └────────────────────────────┬───────────────────────────┘
                              ▼
 ┌────────────────────────────────────────────────────────┐
 │ Stage 4: Constitutional RAG & Citation Protection      │
 │ - Queries ChromaDB RAG Engine for Articles & Advise    │
 │ - Tokenizes citations (__LEGAL_CITATION_0__)           │
 │ - Translates explanation to vernacular; restores laws  │
 └────────────────────────────────────────────────────────┘
```

---

## 💳 4-Stage Smart Milestone Payments

Legal fees are split into 4 verifiable stages to protect citizens and advocates:

1. **Stage 1 (15%)**: Initial Legal Assessment & Consultation
2. **Stage 2 (25%)**: Document Drafting & Legal Notice
3. **Stage 3 (30%)**: Case Filing & First Court Appearance
4. **Stage 4 (30%)**: Final Arguments & Case Resolution

All bookings atomically persist these 4 milestones with exact `DECIMAL(10,2)` accounting. Client contact numbers are masked on public dashboards (`+91-XXXXX-1234`) for privacy protection.

---

## 🧪 Testing & CI Verification

Run the automated test suite locally:

```bash
# Backend unit & integration tests (runs self-contained with no pre-existing DB)
cd backend
PYTHONPATH=.. pytest tests/ -v

# Frontend production build verification
cd ../frontend
npm run build
```

---

## 📦 Release Evidence & Artifacts

- **Tag**: `v1.0.0`
- **Network Trace**: [`docs/evidence/network_trace.json`](docs/evidence/network_trace.json)
- **Architecture Log**: [`docs/evidence/release_notes_v1.0.0.md`](docs/evidence/release_notes_v1.0.0.md)
