# CLAUDE.md — Project Harness & Context

> This file is read automatically by Claude Code at the start of every session.
> Keep it accurate; it is the single source of truth for how this repo is built.

## What we're building
**LifeLine** — a real-time blood-donor matching prototype for Al-Khidmat Karachi
(Build With AI 2026 hackathon). A requester types a plain-language blood request
(Urdu / Roman Urdu / English); the system extracts the fields, ranks eligible nearby
donors, "contacts" them in waves, and shows a coordinator a live confirmation count.

**This is a hackathon demo.** Prioritise a clean, working end-to-end flow over completeness.

## Hard guardrails (do NOT violate)
- **WhatsApp is mocked by default.** Real Meta WhatsApp Cloud API sending exists
  behind an opt-in switch (`WHATSAPP_ENABLED`, default off, + a header toggle /
  `POST /whatsapp/toggle`) and routes through `WHATSAPP_DEMO_REDIRECT`. The wave
  flow runs fully mocked unless the switch is flipped — never make live sending
  the default. No SMS.
- **Donor data** lives in a portable SQLite file (`data/lifeline.db`) committed to
  the repo — no server, no auth, no migrations framework. **Per-request state**
  (open requests, waves, confirmations) stays **in-memory** and resets on restart.
  Do **not** add user auth or deployment infra.
- **Do not** start "stretch" features until the core flow (C1–C5) demos cleanly.
- **Do not** use any paid API. Groq + Gemini free tiers only. OSM tiles need no key.
- Keep API keys in `backend/.env` (gitignored). Never hard-code secrets.

## Stack
- **Backend:** Python 3.10+, FastAPI, uvicorn. AI via Groq (`groq` SDK). Gemini (`google-genai`) only if we expand to the OCR fallback.
- **Frontend:** React + Vite. Map via `react-leaflet` + OpenStreetMap tiles (no key).
- **Portable DB.** Donors live in `data/lifeline.db` (SQLite, stdlib `sqlite3`,
  committed to the repo) and load into memory at startup via `backend/db.py`.

## Repo structure (target)
```
.
├── CLAUDE.md
├── docs/PLAN.md                  # full build plan (read for detail)
├── data/
│   ├── generate_donors.py        # run once -> seeds lifeline.db (pure stdlib)
│   └── lifeline.db               # portable SQLite donor store (committed)
├── backend/
│   ├── main.py                   # FastAPI app + endpoints
│   ├── db.py                     # SQLite read layer (loads donors at startup)
│   ├── ranking.py                # HOSPITALS, eligibility, composite scoring (provided)
│   ├── llm.py                    # Groq intake parse + reply classification
│   ├── requirements.txt
│   └── .env                      # GROQ_API_KEY=..., GEMINI_API_KEY=...
└── frontend/
    ├── index.html
    └── src/ (App, ChatPanel, MapPanel, DashboardPanel, DonorSimPanel)
```

## Commands
- Generate/seed data: `cd data && python generate_donors.py` (drops & rebuilds `lifeline.db`)
- Inspect data: `sqlite3 data/lifeline.db "select * from donors limit 5"`
- Backend: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`
- Frontend: `cd frontend && npm install && npm run dev`
- CORS: backend must allow `http://localhost:5173` (Vite default).

## Data model (`donors` table columns)
`donor_id, name, gender, dob, age, blood_group, phone, neighbourhood, lat, lng,
last_donation_date, days_since_last_donation, total_donations,
times_contacted_last_30d, response_rate`

## Matching rules (already implemented in ranking.py — reuse, don't reinvent)
- Eligibility: age 18–60; days since last donation > 90 (Male) / > 120 (Female).
- Default match = exact blood group. Optional `allow_compatible=True` uses the
  recipient-compatibility map.
- Score = `0.40*proximity + 0.25*recency + 0.20*response_rate − 0.15*fatigue`.
- Distance = Haversine (inline, no geopy dependency required).

## Endpoints to build (in this order)
1. `GET  /donors`                  — list for the map
2. `POST /request/parse`           — raw text -> {blood_group,count,location,hospital,urgency,missing_fields}
3. `POST /request/create`          — rank + open request + mark wave-1 donors contacted
4. `GET  /request/{id}/status`     — wave, confirmed count, donor states (frontend polls every 2s)
5. `POST /request/{id}/escalate`   — contact next wave
6. `POST /donor/respond`           — {donor_id,text} -> classify confirm/decline/eligibility-update
7. `POST /voice` (optional)        — audio -> Groq Whisper -> reuse parse

## Build order (mirror docs/PLAN.md)
CORE first: C1 intake → C2 ranking → C3 chat+list → C4 map → C5 wave+live status.
Then STRETCH only if green: "why this donor" rationale → donor-fatigue indicator → Urdu voice.

## Groq usage notes
- Model: `llama-3.3-70b-versatile` for parsing/classification.
- Ask for STRICT JSON; include Urdu/Roman-Urdu/English few-shot examples.
- Always provide a regex fallback so endpoints never 500 on a rate-limit.
- Whisper model for voice: `whisper-large-v3-turbo`.

## The win condition (keep these visible in the UI)
- Explainable ranking ("why this donor" sentence, not just a number).
- A donor-fatigue / "network health" indicator (we protect the volunteer network).
- "Spam Shield" stat: "A blast would have messaged N people. We contacted M."
- Let a judge type their own messy mixed-language request and watch it work.
