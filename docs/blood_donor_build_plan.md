# Build With AI 2026 — Build Plan
## Al-Khidmat Problem 1: Real-Time Blood Donor Matching

**Stack:** FastAPI (Python) backend + React (Vite) frontend
**AI:** Groq (chat parsing + free Whisper voice) · Gemini (reserved for Problem-2 OCR fallback)
**Channel:** WhatsApp-style chat UI (mocked — no real WhatsApp sending)
**Timebox:** 5–6 hours on the clock (+ a short pre-hackathon prep phase)
**Posture:** Ship the core flow first. Treat every "wow" feature as optional. Problem 2 is the scope-expansion backup.

---

## 1. What we are committing to (and what we are not)

**Committed core (must work end-to-end):**
A web app where a requester types a plain-language blood request, the system extracts the key fields, finds and ranks eligible nearby donors from a sample dataset, "contacts" them in waves, and shows a coordinator a live confirmation count plus a final summary.

**Optional stretch (only if time allows — never promised):**
Voice input, donor-side conversational replies, blood-group compatibility fallback, map animations, "Spam Shield" stat.

**Explicitly out of scope:** real WhatsApp/SMS sending, real PII, production auth, real-time scale. We say "prototype," "simulated," and "sample data" everywhere.

---

## 2. Core features (the committed MVP)

| # | Feature | What it does | Confidence |
|---|---------|--------------|-----------|
| C1 | Natural-language intake | LLM turns a mixed Urdu/Roman-Urdu/English message into structured fields (group, count, location, hospital, urgency) + asks for what's missing | High |
| C2 | Eligibility + ranking | Filter ineligible donors, score the rest by proximity + recency + response history + fatigue | High |
| C3 | Donor list + map | Show ranked donors with *why* they ranked (distance, days since donation, history); pins on a map | High |
| C4 | Wave-based outreach | Contact a first wave of top donors; track commitments; escalate if short | High |
| C5 | Live status + summary | "X of Y confirmed" counter; final coordinator summary | High |

## 3. Stretch features (optional, ordered by payoff-per-hour)

| # | Feature | Effort | Payoff |
|---|---------|--------|--------|
| S1 | "Spam Shield" stat ("a blast would message 1,240; we messaged 9") | ~15 min | Very high |
| S2 | Explainable score chips already in C3 — just style them | ~20 min | High |
| S3 | One donor-side reply interpreted ("gave blood last month" → eligibility update) | ~45 min | High (the official bonus) |
| S4 | Voice input (Groq Whisper → text → parse) | ~40 min | High |
| S5 | Blood-group compatibility fallback (no exact O− → suggest compatible) | ~30 min | Medium |
| S6 | Map animation of wave dispatch | ~45 min | Medium |

**Rule:** do not start any S-item until all C-items demo cleanly.

---

## 4. Architecture

```
┌─────────────────────────── React (Vite) frontend ───────────────────────────┐
│  ChatPanel (WhatsApp-style)   MapPanel (Leaflet+OSM)   DashboardPanel         │
│  - requester types/speaks     - hospital marker        - wave status          │
│  - shows extracted chips      - donor pins by status   - "X of Y confirmed"   │
│  DonorSimPanel (demo control: click to simulate donor replies)                │
└───────────────▲───────────────────────────────────────────────▲──────────────┘
                │ REST (fetch) + polling for live status          │
┌───────────────┴───────────────── FastAPI backend ──────────────┴──────────────┐
│  /request/parse   /request/create   /request/{id}/status   /donor/respond      │
│  /request/{id}/escalate   /donors   (/voice optional)                          │
│                                                                                │
│  In-memory state: donors[] (from CSV), requests{}, wave state                  │
│  Ranking engine (geopy Haversine + composite score)                            │
│  Wave engine (timer/manual advance, commitment tracking)                       │
│  LLM client → Groq (intake parse, reply interpretation)                        │
└────────────────────────────────────────────────────────────────────────────────┘
        │                                   │
   Groq API (free)                    Gemini API (free)  ← only if Problem-2 fallback
   chat + Whisper                     vision/OCR
```

State lives in memory (a dict) — no database needed for a 6-hour demo. Loading the CSV at startup is enough.

---

## 5. Accounts, API keys & tools to set up BEFORE the clock starts

| Item | Where | Cost | Notes |
|------|-------|------|-------|
| Groq API key | console.groq.com → API Keys | Free plan | Core LLM + Whisper. Note rate limits (e.g. ~30 req/min). |
| Gemini API key | aistudio.google.com/apikey | Free tier | Only needed if you pivot to/expand with Problem 2 OCR. |
| OpenStreetMap tiles | Used via Leaflet directly | Free, no key | Respect usage policy; fine for a demo. |
| Node.js + npm | nodejs.org | Free | For React/Vite. |
| Python 3.10+ | python.org | Free | For FastAPI. |
| GitHub repo | github.com | Free | Scaffold ahead of time. |

**Python deps:** `fastapi uvicorn[standard] groq google-genai geopy pandas pydantic python-multipart`
**JS deps:** `react react-dom vite leaflet react-leaflet` (+ optional `tailwindcss`)

> Keep API keys in a `.env` file (backend), never hard-coded. Add `.env` to `.gitignore`.

---

## 6. Data model

### 6.1 Donor dataset (sample CSV — generate ~200 rows in prep)
| column | type | used for |
|--------|------|----------|
| donor_id | string | identity |
| name | string | display |
| gender | Male/Female | eligibility window |
| dob / age | date / int | eligibility (18–60) |
| blood_group | enum (O+,O−,A+,A−,B+,B−,AB+,AB−) | matching |
| phone | string (fake) | display only |
| neighbourhood | string | display + sanity |
| lat, lng | float | proximity (Haversine) |
| last_donation_date | date | eligibility + recency score |
| days_since_last_donation | int | derived, convenience |
| total_donations | int | reliability signal |
| times_contacted_last_30d | int | fatigue penalty |
| response_rate | 0–1 | history score |

### 6.2 Hospital lookup (hardcode ~20–30 Karachi hospitals → coords)
`{"Indus Hospital": (24.918, 67.131), "Liaquat National": (24.881, 67.064), ...}`
Fallback for unknown names: optional Nominatim geocode (free, rate-limited) or ask the user to pick from a list.

### 6.3 Runtime objects
```
Request   = {id, raw_text, blood_group, count_needed, location_text,
             hospital, hospital_latlng, urgency, missing_fields[]}
DonorState= {donor_id, score, distance_km, eligible, reason, wave, status}
            status ∈ {pending, contacted, confirmed, declined, ineligible}
```

---

## 7. The two pieces that need real care

### 7.1 Ranking (deterministic — the "brain")
1. **Gate:** drop/grey-out ineligible: age not 18–60, or last donation < 90 days (men) / < 120 days (women).
2. **Match:** exact blood group by default. (Stretch S5: recipient-compatibility map below.)
3. **Score** (weighted, all normalized 0–1):
   `score = 0.40*proximity + 0.25*recency + 0.20*response_rate − 0.15*fatigue (+ small time-of-day nudge)`
   - proximity = 1 / (1 + distance_km)
   - recency = min(days_since_last / 365, 1)
   - fatigue = min(times_contacted_last_30d / 5, 1)
4. **Sort** descending → ranked donor list with a human-readable `reason` string.

**Recipient compatibility (for S5 fallback) — who a patient of group X can receive from:**
```
O+  ← O+, O−          O−  ← O−
A+  ← A+, A−, O+, O−  A−  ← A−, O−
B+  ← B+, B−, O+, O−  B−  ← B−, O−
AB+ ← everyone        AB− ← AB−, A−, B−, O−
```

### 7.2 LLM intake (Groq — the "ears")
- Ask for **strict JSON** output: `{blood_group, count, location, hospital, urgency, missing_fields}`.
- Give 3–4 few-shot examples mixing Urdu / Roman Urdu / English.
- If `missing_fields` non-empty, the chat asks one targeted follow-up.
- Cache/last-good fallback so a rate-limit hiccup doesn't kill the demo.

### 7.3 Wave engine
- Wave size 8–10; take top-N eligible not yet contacted.
- Mark `contacted`; show a countdown (demo: short window, or a manual **"Advance wave"** button for full control on stage).
- Donor responses: simplest = buttons in DonorSimPanel ("Confirm" / "Can't" / "Gave blood last month"); LLM interprets the text ones.
- When `confirmed >= count_needed`, stop and render the summary.

---

## 8. Backend endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/donors` | list donors (for the map) |
| POST | `/request/parse` | raw text → structured fields + missing_fields |
| POST | `/request/create` | create request, run ranking, return ranked donors + wave 1 |
| GET | `/request/{id}/status` | current wave, confirmed count, donor states (poll this) |
| POST | `/request/{id}/escalate` | advance to next wave |
| POST | `/donor/respond` | {donor_id, text} → LLM interprets → updates status |
| POST | `/voice` *(optional)* | audio → Whisper transcribe → reuse /request/parse |

---

## 9. Hour-by-hour plan

**Phase 0 — pre-hackathon (off the clock):** create repo + scaffold FastAPI and Vite apps, get both API keys into `.env`, generate the synthetic donor CSV, write the hospital lookup table. Confirm `uvicorn` and `npm run dev` both start.

**Phase 1 (~60 min) — Backend data + ranking.** Load CSV at startup, implement `/donors`, write the eligibility gate + composite score, expose nothing-fancy `/request/create` that returns a ranked list. Test with curl/Swagger before touching the UI.

**Phase 2 (~60 min) — LLM intake.** Implement `/request/parse` against Groq with JSON output + few-shot examples. Test the three sample messages from the brief.

**Phase 3 (~60 min) — Frontend shell + chat.** Vite React app, WhatsApp-style ChatPanel, call `/request/parse` then `/request/create`, render extracted chips + the ranked donor list with reasons.

**Phase 4 (~60 min) — Map + dashboard.** Leaflet map with hospital marker + donor pins colored by eligibility/status; DashboardPanel with the donor list and the live counter placeholder.

**Phase 5 (~60 min) — Wave engine + live status.** Wire wave dispatch, `/request/{id}/status` polling, "X of Y confirmed" ring, escalation, DonorSimPanel buttons, final summary. Add the **Spam Shield** stat (S1).

**Phase 6 (~30–60 min) — Polish + rehearse.** Emergency theme, one donor-reply interpretation (S3) and/or voice (S4) *only if green*, then run the demo script twice. Freeze.

> If anything in Phases 1–5 slips, **cut stretch items, not core**. A clean C1–C5 demo beats a broken fancy one.

---

## 10. Build prompts (paste into your AI coding assistant, in order)

> Each prompt assumes the previous step's code exists. Replace paths/names as needed.

**Prompt 1 — Backend scaffold + data + ranking**
> "Create a FastAPI app. On startup, load `donors.csv` (columns: donor_id, name, gender, age, blood_group, phone, neighbourhood, lat, lng, last_donation_date, days_since_last_donation, total_donations, times_contacted_last_30d, response_rate) into memory. Add a hardcoded `HOSPITALS` dict mapping ~20 Karachi hospital names to (lat,lng). Implement a `rank_donors(blood_group, hospital_latlng, count)` function: gate out donors not aged 18–60 or whose last donation is < 90 days (Male) / < 120 days (Female); for eligible exact-blood-group matches compute distance with geopy Haversine and a composite score = 0.40*proximity + 0.25*recency + 0.20*response_rate − 0.15*fatigue; return a sorted list with a human-readable `reason` per donor. Expose `GET /donors` and `POST /request/create` (body: blood_group, count, hospital, urgency) that returns the ranked list. Enable CORS for localhost."

**Prompt 2 — LLM intake parsing (Groq)**
> "Add `POST /request/parse` that takes `{text}` and calls the Groq API (model llama-3.3-70b-versatile) to extract strict JSON `{blood_group, count, location, hospital, urgency, missing_fields}`. The input may be Urdu, Roman Urdu, English, or mixed. Include 3 few-shot examples (e.g. 'need 5 O+ donors near Gulshan urgent, patient at Indus Hospital' and 'AB negative chahiye jaldi, Liaquat National mein'). Read the Groq key from env. If the call fails, return a regex-based best-effort fallback so the endpoint never 500s."

**Prompt 3 — React shell + chat**
> "Create a Vite React app with three columns: ChatPanel (left, WhatsApp-style bubbles), MapPanel (center), DashboardPanel (right). In ChatPanel, on send, POST the text to `/request/parse`, render the extracted fields as chips; if `missing_fields` is non-empty, show a follow-up question; otherwise POST to `/request/create` and store the ranked donors in state."

**Prompt 4 — Map + donor list**
> "Add react-leaflet to MapPanel using OpenStreetMap tiles (no API key). Plot the hospital as a distinct marker and each donor as a pin colored by status (eligible=green, ineligible=grey, contacted=amber, confirmed=blue). In DashboardPanel, list the ranked donors showing name, distance_km, days since last donation, response_rate, and the `reason` string."

**Prompt 5 — Wave engine + live status**
> "Add wave logic: `POST /request/create` also creates an in-memory request with wave=1 and marks the top 8 eligible donors as 'contacted'. Add `GET /request/{id}/status` returning wave, confirmed count, and donor states, and `POST /request/{id}/escalate` to contact the next 8. Add `POST /donor/respond` ({donor_id, text}) that uses Groq to classify the reply as confirm / decline / eligibility-update and updates state. On the frontend, poll `/status` every 2s, show a 'X of Y confirmed' progress ring, add DonorSimPanel buttons to simulate replies, and an 'Advance wave' button."

**Prompt 6 — Spam Shield + summary + polish**
> "Add a 'Spam Shield' stat to the dashboard: total matching donors in the DB vs. how many we actually contacted, phrased as 'A blast would have messaged N people. We contacted M.' When confirmed ≥ count_needed, render a coordinator summary card (confirmed donor names, phones, hospital, ETA placeholder). Apply a dark 'emergency' theme with a red pulse on high-urgency requests."

**Prompt 7 — (optional) Voice input**
> "Add `POST /voice` that accepts an audio file, transcribes it with Groq Whisper (whisper-large-v3-turbo), and feeds the text into the existing parse flow. Add a mic button to ChatPanel."

---

## 11. Demo script (≈3 minutes)

1. Type **"AB negative chahiye jaldi, Liaquat National mein"** → fields pop out as chips. (Mixed-language hook.)
2. System asks the one missing thing (e.g. count) → answer "3".
3. Map lights up: hospital + ranked donors; read one **reason** aloud ("0.8 km, eligible 47 days, responds 4/5").
4. Wave 1 dispatches → counter ticks → simulate two confirms + one "gave blood last month" (silently updates eligibility, not a refusal).
5. Short of target → **auto-escalate** to wave 2 → reach "3 of 3 confirmed".
6. Point at the **Spam Shield**: "A blast would have messaged 240 people. We contacted 9." Show the coordinator summary.

---

## 12. Fallback plan — Problem 2 as a scope expander

If a stretch feature blocks you, do **not** thrash on it — pivot the spare time into Problem 2, which **reuses most of this app**:
- Same WhatsApp-style ChatPanel and coordinator DashboardPanel.
- Same LLM-intent mapping pattern (free-text purpose → active project, like the donor-reply classifier).
- New parts: a Gemini-vision `POST /screenshot` endpoint (OCR amount/time/reference from an uploaded image) + a matcher against a provided bank-statement table returning verified / flagged / pending.
- Killer demo line carried over: "let a judge upload their own screenshot and watch it process."
This turns a blocked afternoon into a *second* working flow rather than a half-broken feature.

---

## 13. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| LLM rate limit / latency mid-demo | Cache last good parse; regex fallback; pre-run the demo inputs once to warm cache. |
| Live timing feels random on stage | Use the manual **"Advance wave"** + DonorSim buttons instead of pure timers. |
| Map tiles slow / blocked | Keep a static fallback; pins still render without tiles. |
| Scope creep | Lock C1–C5 first; S-items only when core is green. |
| Hospital name not found | Hardcoded lookup + "pick from list" fallback. |
| OCR flakiness (if Problem 2) | "Flag for human review" is in-scope by design — imperfect reads are acceptable. |

---

## 14. Pre-start checklist (print this)

- [ ] Repo created; FastAPI + Vite scaffolds run locally
- [ ] Groq key + Gemini key in `.env`; `.env` gitignored
- [ ] `donors.csv` (~200 rows, with lat/lng) generated
- [ ] `HOSPITALS` lookup table written (~20–30 Karachi hospitals)
- [ ] Python + JS deps installed
- [ ] One teammate owns backend, one owns frontend, one owns demo/data
- [ ] Demo inputs (the 3 sample messages) decided and saved
- [ ] Core (C1–C5) agreed as the non-negotiable; stretch list pinned but optional
