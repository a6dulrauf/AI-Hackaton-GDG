# LifeLine — System & Presentation Guide

> One-stop reference: what the system is, what it does, who it's for, why it matters,
> and exactly how to demo it to judges. Written for the Build With AI 2026 hackathon
> (Al-Khidmat Karachi — Problem 1: Real-Time Blood Donor Matching).

---

## 1. The one-liner

**LifeLine turns a messy, plain-language blood request into the *right few* donors to call —
ranked, explained, and contacted in protective waves — instead of a panic blast to hundreds.**

A coordinator types *"AB negative chahiye jaldi, Liaquat National mein"* and within seconds sees
the closest eligible donors, **why** each one was picked, and a live "X of Y confirmed" counter.

---

## 2. The problem we're solving

When a hospital needs blood urgently, the current playbook in many volunteer networks is:

- Someone forwards a request to **every** donor in a WhatsApp group / spreadsheet.
- Hundreds get messaged — most are **ineligible** (donated too recently), **far away**, or the
  **wrong blood group**.
- The same reliable volunteers get spammed **every time** → they burn out and stop replying.
- There's **no visibility**: who was contacted? who confirmed? are we there yet?

The result is slow, noisy, and it **erodes the volunteer network** — the most precious asset.

---

## 3. What LifeLine does (the flow)

```
Coordinator types a request (Urdu / Roman Urdu / English — typing or voice)
        │  Groq LLM extracts: blood group · count · hospital · urgency
        ▼
Missing something? → the chatbot asks ONE follow-up question, then proceeds
        ▼
System ranks every eligible donor:
   • Eligibility gate  → age 18–60, recovered from last donation (90d men / 120d women)
   • Composite score   → proximity + recency + reliability − fatigue
   • Explains each pick in plain English ("why this donor")
        ▼
Contacts WAVE 1 (top 8) — not all 37 matches. The rest wait.
        ▼
Live dashboard: confirmed/needed ring · map pins · "Spam Shield" stat · network health
        ▼
Donors reply (free text) → LLM classifies:
   confirm · decline · "gave blood recently" (eligibility update, NOT a refusal)
        ▼
Still short? → "Advance wave" contacts the next 8. Repeat until target met.
        ▼
Target reached → coordinator dispatch summary (names + phones to call)
```

---

## 4. Features

### Core (the committed MVP)

| Feature | What it does | Why it's impressive |
|---------|--------------|---------------------|
| **Natural-language intake** | Understands English, Urdu, Roman Urdu, and any mix; extracts structured fields + replies conversationally | A judge can type their *own* messy message and it just works |
| **Eligibility + smart ranking** | Filters out ineligible donors, scores the rest on proximity, recency, response history, and fatigue | It's not a keyword filter — it's a real matching engine |
| **"Why this donor" rationale** | Every donor comes with a plain-English reason, not just a number | Explainable AI — trust, not a black box |
| **Wave-based outreach** | Contacts 8 at a time; you escalate deliberately | The anti-spam mechanic made visible |
| **Live status** | "X of Y confirmed" ring, donor states, map pins, all polling every 2s | Feels alive on stage |
| **Donor reply understanding** | Classifies free-text replies; *"I gave blood last month"* is treated as an eligibility update, not a refusal | Nuance most demos miss |
| **Spam Shield stat** | *"A blast would have messaged 37. We contacted 8."* | The single most quotable line |
| **Network-health indicator** | Flags over-contacted volunteers held back to later waves | "We protect the people who save lives" |

### Map & UX
- Leaflet + OpenStreetMap (no API key): hospital marker + donor pins **colored by status**
  (eligible/contacted/confirmed/declined).
- **Emergency theme** with a red pulse on high-urgency requests.
- Optional **Urdu voice input** (mic → Groq Whisper → same parse flow).

### Bonus — WhatsApp switch (opt-in)
- A header toggle: **Mocked ↔ Live**.
- **Off by default** → the whole demo is safely simulated; a flaky connection can never break it.
- **On** (with Meta Cloud API creds) → contacted donors get a *real* WhatsApp message, sent in
  the background so it never slows the UI. All messages can be routed to one verified test number.

---

## 5. Understanding "waves" (and the Advance-wave button)

This is the heart of the pitch, so know it cold:

- All eligible matches are ranked and sliced into **waves of 8**.
- **Wave 1** is contacted immediately. Everyone else waits as `pending`.
- **"Advance wave"** promotes the next 8 to `contacted` — a *deliberate* escalation.
- It's **manual** (a button, not a timer) because that's more reliable on stage and, more
  importantly, it mirrors how responsible outreach *should* work: reach a few, see who says yes,
  escalate only if needed.

**The contrast you're selling:** a blast messages everyone once and burns the network. LifeLine
messages the *best* few, measures the response, and grows only as much as it must.

---

## 6. Who it's for (use cases & beneficiaries)

| Stakeholder | What they get |
|-------------|---------------|
| **Al-Khidmat / NGO coordinators** | Stop manually scanning spreadsheets; get a ranked shortlist + live tracking in seconds |
| **Hospitals / attendants** | Faster sourcing of the right blood group during emergencies |
| **Donors / volunteers** | Contacted only when they're genuinely eligible and not over-asked — less spam, less burnout |
| **Patients & families** | Faster matches when minutes matter |

**Use cases:** emergency blood requests, planned surgeries needing specific groups, rare-group
sourcing (e.g., negative groups via compatibility fallback), and managing a sustainable volunteer
roster over time.

---

## 7. Benefits & impact

- **Faster** — seconds from a typed message to a ranked, contactable shortlist.
- **Smarter** — eligibility + distance + reliability + fatigue, not a blunt group filter.
- **Kinder to volunteers** — the Spam Shield and network-health logic actively protect donors,
  keeping the network responsive for the *next* emergency.
- **Trustworthy** — explainable picks; a coordinator can defend every choice.
- **Inclusive** — works in the languages people actually type and speak in Karachi.
- **Zero-friction to run** — portable SQLite dataset ships with the repo; no DB server, no setup.

---

## 8. How it's built (tech stack)

- **Backend:** Python · FastAPI · uvicorn. AI via **Groq** (`llama-3.3-70b-versatile` for
  parsing/classification, `whisper-large-v3-turbo` for voice). Robust regex fallback so it
  **never crashes** on a rate limit.
- **Data:** **portable SQLite** (`data/lifeline.db`, 220 synthetic Karachi donors) loaded into
  memory at startup. Per-request state is in-memory and resets on restart.
- **Matching brain:** `ranking.py` — Haversine distance + composite score
  `0.40·proximity + 0.25·recency + 0.20·response_rate − 0.15·fatigue`.
- **Frontend:** React + Vite. Map via react-leaflet + OpenStreetMap (no key).
- **Optional outreach:** Meta WhatsApp Cloud API behind an opt-in switch.

Everything runs locally and free (Groq free tier; OSM needs no key).

---

## 9. The demo script (≈ 3 minutes)

> Have the backend (`:8000`) and frontend (`:5173`) running. Make sure `GROQ_API_KEY` is in
> `backend/.env`. Warm it up once before judging so the first parse is instant.

1. **Set the scene (15s).** *"When a hospital needs blood, the usual answer is to spam hundreds of
   people. Most are ineligible or far away, and the reliable volunteers burn out. LifeLine fixes
   that."*

2. **Type a real, messy request (30s).**
   `AB negative chahiye jaldi, Liaquat National mein`
   → Point out it understood Roman Urdu, flagged **high urgency** (watch the red pulse), and asked
   only for the missing field.

3. **Answer the follow-up (10s).** Type `3`.
   → The map lights up; the donor list ranks by score.

4. **Read ONE "why" out loud (20s).** e.g. *"Recommending Ahmed — closest eligible AB- donor, last
   gave blood 140 days ago, responds 90% of the time."*
   → *"It explains every pick. This isn't a black box."*

5. **Simulate replies (30s).** Use the demo strip: click **Confirm** twice, then click
   **"Gave blood last month."**
   → Point out: *"That last one isn't a 'no' — the AI understood it as an eligibility update."*
   The confirmed ring ticks up.

6. **Advance the wave (15s).** Click **Advance wave**.
   → *"We didn't blast everyone. We reached 8, and only escalated to the next 8 because we needed
   more."*

7. **Land the Spam Shield (20s).** Point at the stat:
   *"A mass blast would have messaged [N] people. We contacted [M]."* (read the live numbers)
   → *"And these volunteers" (point at network-health note) "we deliberately held back — they've
   been contacted too often. We protect the people who save lives."*

8. **Close on the summary (15s).** Once confirmed ≥ needed, show the dispatch card with names +
   phones. *"The coordinator now has exactly who to call. Seconds, not hours."*

9. **(Optional) The mic-drop:** *"Want to try your own message? Type anything — any language."*
   Hand the keyboard to a judge.

---

## 10. Win-condition talking points (keep these visible & spoken)

- **Explainable ranking** — "why this donor", not just a score.
- **Network health / Spam Shield** — "we protect the volunteer network."
- **The contrast number** — "a blast would message N; we contacted M."
- **Judge-proof intake** — let them type their own mixed-language request and watch it work.

---

## 11. Likely judge questions (and answers)

- **"Is this real WhatsApp?"** → "It's mocked by default so the demo is reliable, but there's a
  real Meta WhatsApp Cloud API integration behind a switch — flip it and contacted donors get an
  actual message."
- **"Where's the donor data from?"** → "Synthetic but realistic — 220 Karachi donors with proper
  blood-group distribution, locations, and donation history, in a portable SQLite file."
- **"What if the AI is down or rate-limited?"** → "Every LLM call has a regex fallback, so the app
  never 500s. We also cache and warm up the model before the demo."
- **"How does ranking work?"** → "Eligibility gate first, then a weighted score: proximity 40%,
  recency 25%, response history 20%, minus fatigue 15%."
- **"Does it handle rare blood groups?"** → "Yes — if exact matches are too few, it broadens to
  medically-compatible groups and labels them clearly."
- **"What's the roadmap?"** → "Real channel integration, donor-facing app, multi-hospital
  coordination, and Problem-2 donation verification (OCR) which reuses the same chat + dashboard."

---

## 12. The 10-second elevator pitch

> *"LifeLine is an AI blood-donor matcher for Al-Khidmat. Type a request in any language; it finds
> the closest eligible donors, tells you **why** each one, and contacts them in small waves instead
> of spamming hundreds — so the volunteer network stays alive for the next emergency."*
