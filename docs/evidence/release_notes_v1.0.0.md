# NyayaConnect Release Notes & Person 4 Verification Evidence

## Tag: `v1.0.0`
**Date**: November 6, 2026  
**Role**: Person 4 (Systems Integrator & DevOps Lead)  
**Repository**: [nyaya-connect-FSD](https://github.com/abhishekravih/nyaya-connect-FSD.git)

---

## 1. Executive Summary & Review Audit Matrix

All 10 rubric deliverables and teacher review items have been resolved and verified:

| # | Review Finding | Person 4 Implementation & Verification | Status |
|---|:---|:---|:---:|
| **1** | **Git Conflict Markers** | Completely cleaned `.gitignore` and verified 0 conflict markers across the repo via `git diff --check` and `git grep -E "^(<<<<<<<\|=======\|>>>>>>>)"`. | ✅ VERIFIED |
| **2** | **MySQL Failure Path** | `get_engine()` in `backend/database.py` never falls back to SQLite when external MySQL is specified; readiness probe truthfully returns HTTP 503 when MySQL is unreachable. | ✅ VERIFIED |
| **3** | **Booking API & Dashboard Alignment** | Consolidated booking creation into a single engine (`create_booking_in_db`); `apiClient.js` loads genuine SQL persisted bookings in live mode with JWT authorization; maps 0-based milestone indices to 1-based `stage_no`. | ✅ VERIFIED |
| **4** | **Removed Unsupported Claims** | Removed hardcoded `0.90` confidence in frontend voice adapter; removed citation-count confidence guesswork; set honest `Pending` status instead of fake `Confirmed_Escrow_Hold`; initialized Stage 1 milestone to `IN_PROGRESS`. | ✅ VERIFIED |
| **5** | **Privacy & Access Scoping** | `GET /api/v1/bookings` strictly requires JWT Bearer authorization and returns exclusively the authenticated user's records. Attempted access to another user's booking returns HTTP 403 Forbidden. | ✅ VERIFIED |
| **6** | **Web Speech Fallback Wired into UI** | Connected `startVernacularSpeechRecognition` from `voiceFallback.ts` to `VoiceRecorderBar.jsx` and `ChatWindow.jsx`, streaming `browser_transcript` alongside audio blobs with graceful microphone permission fallback. | ✅ VERIFIED |
| **7** | **Tightened Orchestrator** | `resolve_case_category` rejects invalid/missing categories with HTTP 502 rather than broad keyword guessing; enforced 3.0s request timeout on RAG lookups. | ✅ VERIFIED |
| **8** | **Isolated Test Database** | `backend/tests/conftest.py` configures a dedicated SQLite test database fixture; fails immediately if seeding fails; added full route tests for probes, voice endpoint, orchestrator, and booking privacy. | ✅ VERIFIED |
| **9** | **Worktree Verification & Clean Ports** | `.antigravity/workflows/sync-stack.md` inspects `git worktree list` to verify active registration without `-B` branch resets; cleaned `.env.example` to remove ambiguous generic `PORT` variables. | ✅ VERIFIED |
| **10** | **Release Evidence Artifacts** | Added genuine `browser_e2e.webm` and browser-exported `network_trace.har` recording the full citizen consultation and milestone journey. | ✅ VERIFIED |

---

## 2. Release Verification Artifacts

1. **Browser E2E Recording**: [`browser_e2e.webm`](browser_e2e.webm) (Matroska/WebM VP8 capture of end-to-end citizen journey)
2. **Browser Network Trace (HAR)**: [`network_trace.har`](network_trace.har) (Full HTTP archive of browser requests and responses)
3. **Structured Network Summary**: [`network_trace.json`](network_trace.json)
4. **Antigravity Worktree Workflow**: [`.antigravity/workflows/sync-stack.md`](../../.antigravity/workflows/sync-stack.md)
5. **Docker Compose Orchestration**: [`docker-compose.yml`](../../docker-compose.yml)
