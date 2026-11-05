# NyayaConnect Monorepo Stack Sync & Worktree Workflow
`sync-stack`

This workflow orchestrates multi-agent branch synchronization, provisions isolated Git worktrees for Person 1 (Frontend), Person 2 (Backend Marketplace), and Person 3 (RAG Service), and detects port or dependency collisions prior to integration merges.

---

## 1. Branch and Git Worktree Orchestration

Use Git worktrees to allow parallel development and isolated execution across services without context switching or branch pollution.

### Directory Mapping
- **Frontend (Person 1 - Next.js)**: `frontend/` (Worktree target: `../nyayaconnect-worktrees/frontend`)
- **Backend (Person 2 - FastAPI Marketplace)**: `backend/` (Worktree target: `../nyayaconnect-worktrees/backend`)
- **RAG Service (Person 3 - ChromaDB Service)**: `rag_service/` (Worktree target: `../nyayaconnect-worktrees/rag_service`)

### Worktree Initialization & Branch Sync Commands

```bash
# 1. Fetch latest changes from remote
git fetch origin

# 2. Setup isolated worktrees for each service branch (if working in parallel branch mode)
git worktree add -B frontend-p1 ../nyayaconnect-worktrees/frontend origin/frontend-p1 2>/dev/null || git worktree add -B frontend-p1 ../nyayaconnect-worktrees/frontend HEAD
git worktree add -B backend-p2 ../nyayaconnect-worktrees/backend origin/backend-p2 2>/dev/null || git worktree add -B backend-p2 ../nyayaconnect-worktrees/backend HEAD
git worktree add -B rag-p3 ../nyayaconnect-worktrees/rag_service origin/rag-p3 2>/dev/null || git worktree add -B rag-p3 ../nyayaconnect-worktrees/rag_service HEAD

# 3. List active worktrees
git worktree list
```

---

## 2. Port Collision Verification

Standardized port allocations must remain strictly separated across all container and host services:

| Service | Protocol / Container Port | Host Port | Collision Safeguard Rule |
| :--- | :--- | :--- | :--- |
| **Frontend** | HTTP / Next.js (3000) | `3000` | Verify no stale Node/React server on 3000 |
| **Marketplace Backend** | HTTP / FastAPI (8000) | `8000` | Verify no conflicting local API on 8000 |
| **RAG Service** | HTTP / FastAPI + ChromaDB (8001) | `8001` | Verify isolated port distinct from backend |
| **Database** | TCP / MySQL 8.0 (3306) | `3306` | Fallback to `3307` or `5432` if host MySQL/Postgres active |

### Automated Port Conflict Detection Script

```powershell
# Windows PowerShell Port Check
$ports = @(3000, 8000, 8001, 3306)
foreach ($port in $ports) {
    $occupied = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($occupied) {
        Write-Warning "Port collision detected on $port: Process ID $($occupied.OwningProcess)"
    } else {
        Write-Host "Port $port is clear and ready." -ForegroundColor Green
    }
}
```

```bash
# Linux / macOS Port Check
for port in 3000 8000 8001 3306; do
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
    echo "WARNING: Port $port is in use! Collision detected."
  else
    echo "Port $port is free."
  fi
done
```

---

## 3. Dependency & Contract Collision Check

Before merging service branches into the main monorepo, perform automated dependency and schema validation:

1. **FastAPI & Pydantic Consistency**:
   - Backend and RAG services must both standardize on Pydantic v2 schemas.
   - Verify `POST /api/v1/orchestrate/legal-assist` payload contract matches `POST /api/v1/rag/ask` response schema (`articles`, `explanation`, `recommended_case_category`).

2. **Frontend Environment Flag**:
   - Verify `NEXT_PUBLIC_USE_MOCKS=false` in production.
   - Verify `NEXT_PUBLIC_API_BASE_URL` targets `http://localhost:8000/api/v1` locally or the cloud backend URL in production.

3. **CORS Headers Check**:
   - Verify Backend `CORSMiddleware` includes `ALLOWED_ORIGINS` covering the Next.js port (`http://localhost:3000`) and the Vercel deployment URL (`https://*.vercel.app`).

---

## 4. Single-Command Monorepo Boot Verification

```bash
# Boot complete orchestrated stack
docker compose up --build -d

# Verify all containers are healthy
docker compose ps

# Run health checks
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:8001/health || exit 1
curl -f http://localhost:3000 || exit 1
```
