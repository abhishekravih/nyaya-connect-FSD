# NyayaConnect

NyayaConnect is a Next.js 14 demo for constitutional information, verified lawyer discovery, transparent milestone fees, and booking progress.

## Setup

```bash
npm install
npm run dev
```

Set environment variables in `.env.local`:

```env
NEXT_PUBLIC_USE_MOCKS=true
NEXT_PUBLIC_API_BASE_URL=https://your-api.example
```

`NEXT_PUBLIC_USE_MOCKS=true` (the default unless explicitly set to `false`) uses local JSON fixtures and simulated latency. The demo does not need a backend. `NEXT_PUBLIC_API_BASE_URL` is required when mocks are disabled. The browser stores demo bookings in localStorage under `nyayaconnect-bookings-v1`; clearing that key resets the demo. Voice recording requires a secure browser context and microphone permission.

## Folder structure

- `src/app/` — App Router pages and global styles
- `src/components/` — chat, voice, lawyer cards, booking modal, fee breakdown, and milestone UI
- `src/context/BookingContext.jsx` — shared chat summary and persisted mock bookings
- `src/hooks/` — client data hooks
- `src/mocks/` — lawyer and RAG response fixtures
- `src/services/apiClient.js` — all data access and mock/live switching

## API client functions

- `getLawyers(filters)` and `getLawyerById(id)` — lawyer directory and profile
- `askLegalQuestion(query, lang)` — constitutional RAG answer with citations, suggested category, and confidence
- `submitVoiceQuery(blob, lang)` — voice transcription (and optionally `rag_response` in a live response)
- `createBooking(payload)` and `getBookings()` — booking creation and retrieval
- `updateMilestone(bookingId, milestoneIndex, status)` — milestone status update

Live endpoint paths are `/lawyers`, `/lawyers/:id`, `/legal-question`, `/voice-query`, `/bookings`, and `/bookings/:id/milestones/:index`. Keep components calling the API client rather than fetching directly.
