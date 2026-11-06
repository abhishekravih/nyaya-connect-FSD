# NyayaConnect Monorepo Stack Sync & Worktree Workflow
`sync-stack`

This workflow orchestrates multi-agent branch synchronization, provisions isolated Git worktrees for Person 1 (Frontend), Person 2 (Backend Marketplace), and Person 3 (RAG Service), and programmatically detects port or dependency collisions prior to integration merges.

---

## 1. Branch and Git Worktree Orchestration

Use Git worktrees to allow parallel development and isolated execution across services without context switching or branch pollution.

### Directory Mapping
- **Frontend (Person 1 - Next.js)**: `frontend/` (Worktree target: `../nyayaconnect-worktrees/frontend`)
- **Backend (Person 2 - FastAPI Marketplace)**: `backend/` (Worktree target: `../nyayaconnect-worktrees/backend`)
- **RAG Service (Person 3 - ChromaDB Service)**: `rag_service/` (Worktree target: `../nyayaconnect-worktrees/rag_service`)

### Worktree Initialization & Safe Branch Sync

> [!IMPORTANT]
> If a teammate branch is missing on `origin`, the script **halts with an explicit error**. It does **not** create pretend worktrees from `main` or `HEAD`.

#### PowerShell Implementation

```powershell
# 1. Fetch latest remote branches and prune deleted ones
Write-Host "Fetching latest branches from origin..." -ForegroundColor Cyan
git fetch origin --prune

# 2. Inspect available remote branches
$remoteBranches = (git branch -r) | ForEach-Object { $_.Trim() }
Write-Host "Available remote branches:"
$remoteBranches | ForEach-Object { Write-Host "  - $_" -ForegroundColor DarkGray }

# 3. Define expected teammate branches
$expectedBranches = @{
    "frontend"    = "origin/frontend-p1"
    "backend"     = "origin/backend-p2"
    "rag_service" = "origin/rag-p3"
}

$missingBranches = @()

foreach ($service in $expectedBranches.Keys) {
    $branch = $expectedBranches[$service]
    if ($remoteBranches -notcontains $branch) {
        Write-Warning "Teammate branch '${branch}' for ${service} does NOT exist on origin."
        $missingBranches += $branch
    }
}

if ($missingBranches.Count -gt 0) {
    Write-Error "Integration halted: The following teammate branches are missing on remote: $($missingBranches -join ', '). Teammates must push their branches before worktree creation."
    exit 1
}

# 4. Safely create and verify worktrees without branch resets
New-Item -ItemType Directory -Force -Path "../nyayaconnect-worktrees" | Out-Null

$activeWts = (git worktree list) -join "`n"

$worktreeMap = @(
    @{ Target = "../nyayaconnect-worktrees/frontend"; Remote = "origin/frontend-p1"; Branch = "frontend-p1" },
    @{ Target = "../nyayaconnect-worktrees/backend";  Remote = "origin/backend-p2";  Branch = "backend-p2" },
    @{ Target = "../nyayaconnect-worktrees/rag_service"; Remote = "origin/rag-p3"; Branch = "rag-p3" }
)

foreach ($wt in $worktreeMap) {
    if ($activeWts -match [regex]::Escape($wt.Branch)) {
        Write-Host "Worktree verified as active on $($wt.Branch): $($wt.Target)" -ForegroundColor Green
    } elseif (Test-Path $wt.Target) {
        Write-Warning "Target path '$($wt.Target)' exists but is not registered. Status: pending verification."
    } else {
        git worktree add $wt.Target $wt.Remote
        Write-Host "Worktree created at $($wt.Target) for $($wt.Branch)." -ForegroundColor Green
    }
}

Write-Host "Worktree verification complete:" -ForegroundColor Green
git worktree list
```

#### Bash Implementation

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Fetching latest remote branches..."
git fetch origin --prune

REMOTE_BRANCHES=$(git branch -r)
echo "Discovered remote branches:"
echo "$REMOTE_BRANCHES"

MISSING=0
for BRANCH in "origin/frontend-p1" "origin/backend-p2" "origin/rag-p3"; do
  if ! echo "$REMOTE_BRANCHES" | grep -qw "$BRANCH"; then
    echo "ERROR: Required teammate branch '$BRANCH' is not published on remote." >&2
    MISSING=1
  fi
done

if [ "$MISSING" -eq 1 ]; then
  echo "Integration halted: Teammates must publish their branches before worktree initialization." >&2
  exit 1
fi

mkdir -p ../nyayaconnect-worktrees
ACTIVE_WTS=$(git worktree list)

for ITEM in "frontend-p1:origin/frontend-p1:../nyayaconnect-worktrees/frontend" \
            "backend-p2:origin/backend-p2:../nyayaconnect-worktrees/backend" \
            "rag-p3:origin/rag-p3:../nyayaconnect-worktrees/rag_service"; do
  IFS=":" read -r BRANCH REMOTE_REF TARGET <<< "$ITEM"
  if echo "$ACTIVE_WTS" | grep -Fq "$BRANCH"; then
    echo "Worktree verified as active on $BRANCH at $TARGET."
  elif [ -d "$TARGET" ]; then
    echo "WARNING: Target path '$TARGET' exists but is not registered. Status: pending verification."
  else
    git worktree add "$TARGET" "$REMOTE_REF"
    echo "Worktree created at $TARGET for $BRANCH."
  fi
done

echo "Active worktrees verified:"
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
| **Database** | TCP / MySQL 8.0 (3306) | `3306` | Fallback to `3307` or `5432` if host MySQL active |

### Automated Port Conflict Detection Script (PowerShell)

```powershell
$ports = @(3000, 8000, 8001, 3306)
$collisions = 0

foreach ($port in $ports) {
    $occupied = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($occupied) {
        Write-Warning "Port collision detected on ${port}: Process ID $($occupied.OwningProcess)"
        $collisions++
    } else {
        Write-Host "Port ${port} is clear and ready." -ForegroundColor Green
    }
}

if ($collisions -gt 0) {
    Write-Warning "${collisions} port collision(s) detected. Stop conflicting processes before booting the stack."
} else {
    Write-Host "All ports clear." -ForegroundColor Green
}
```

---

## 3. Programmatic Dependency & Contract Collision Audits

Execute these programmatic checks against repository files before initiating merge reviews:

```powershell
# 1. Check Compose Port Declarations
$composeContent = Get-Content docker-compose.yml -Raw
$expectedComposePorts = @("3000:3000", "8000:8000", "8001:8001", "3306:3306")
foreach ($p in $expectedComposePorts) {
    if ($composeContent -notmatch [regex]::Escape($p)) {
        Write-Error "Compose configuration error: missing port mapping $p"
    } else {
        Write-Host "Compose port verified: $p" -ForegroundColor Green
    }
}

# 2. Check Pydantic Version Parity Across Backend & RAG
$backendReqs = Get-Content backend/requirements.txt -Raw
$ragReqs = Get-Content rag_service/requirements.txt -Raw

$pydanticPattern = "pydantic(\[email\])?(>=|==)2"
if ($backendReqs -match $pydanticPattern -and $ragReqs -match $pydanticPattern) {
    Write-Host "Pydantic v2 parity confirmed across backend and rag_service." -ForegroundColor Green
} else {
    Write-Error "Version discrepancy: Pydantic major version mismatch between services."
}

# 3. Check Next.js Standalone Configuration
$nextConfig = Get-Content frontend/next.config.js -Raw
if ($nextConfig -match "output:\s*'standalone'") {
    Write-Host "Frontend configured for optimized standalone Docker runtime." -ForegroundColor Green
} else {
    Write-Warning "frontend/next.config.js lacks standalone output configuration."
}
```

---

## 4. Verification Gate & Execution Log

| Check | Target | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Port Interpolation** | `${port}` syntax | ✅ PASSED | No syntax errors in PowerShell parser |
| **Teammate Branch Guard** | `origin/frontend-p1`, `backend-p2`, `rag-p3` | ⚠️ PENDING TEAMMATES | Halts cleanly if branches missing; no fallback to `main` |
| **Port Allocations** | 3000, 8000, 8001, 3306 | ✅ VERIFIED | Declared in `docker-compose.yml` and `.env.example` |
| **Pydantic v2 Contract** | `backend` and `rag_service` | ✅ PASSED | Both standardize on `pydantic>=2.6.0` |
