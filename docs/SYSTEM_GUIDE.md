# LifeLine — Understand the Whole System (Plain-English Guide)

> This guide explains **everything** about LifeLine in simple words: what it is, what each
> part does, what every number on the screen means, and exactly what happens at each step —
> from the moment you type a message to the final list of donors to call.
> Read this top to bottom and you'll understand the entire project.

---

## Part 1 — What is LifeLine, in one paragraph?

A hospital needs blood urgently. Normally, a volunteer coordinator forwards that request to
**hundreds** of people in a WhatsApp group — most of whom can't help (wrong blood group, donated
too recently, live far away). It's slow, noisy, and the few reliable volunteers get spammed every
time until they stop replying.

**LifeLine replaces that.** You type the request in plain language (English, Urdu, Roman Urdu, or
a mix). The system reads it, finds the **best few** eligible donors near the hospital, explains
**why** it chose each one, and contacts them in small **waves** of 8 instead of blasting everyone.
A live dashboard shows how many have confirmed. The result: faster matches, and a volunteer
network that doesn't burn out.

---

## Part 2 — The three screens (what you see)

The app is one page split into three columns, with a control strip at the bottom.

```
┌──────────── HEADER:  🩸 LifeLine · [HIGH URGENCY] · WhatsApp: Mocked · New request ┐
├───────────────┬──────────────────────────┬──────────────────────────────────────┤
│   CHAT        │          MAP             │        COORDINATOR DASHBOARD          │
│ (you type     │  (hospital + donor pins  │  (the confirmed ring, Spam Shield,    │
│  here)        │   on a Karachi map)      │   and the DONOR CARDS — the heart)    │
├───────────────┴──────────────────────────┴──────────────────────────────────────┤
│  DEMO STRIP:  next reply from <donor>:  ✅ Confirm  ❌ Decline  🩸 "Gave blood"  ⏭ Advance wave │
└──────────────────────────────────────────────────────────────────────────────────┘
```

1. **Chat (left)** — where you type the request, like a WhatsApp chat.
2. **Map (middle)** — a real map of Karachi showing the hospital and every matched donor as a colored dot.
3. **Dashboard (right)** — the most important panel: the **donor cards**, plus the live counters.
4. **Demo strip (bottom)** — buttons to simulate donor replies and advance waves during a demo.

---

## Part 3 — The donor cards (THE most important part)

When a request is created, the dashboard shows a list of **donor cards**, ranked best-first.
Each card is one donor the system recommends. Here is a real card, annotated:

```
  ┃ Ahmed Khan   AB-   [compatible]              Contacted · W1
  ┃ 2.3 km · 140d since last · responds 90% · 1×/30d
  ┃ Recommending Ahmed Khan — closest eligible AB- donor, last gave
  ┃ blood 140 days ago, responds 90% of the time.
  ↑
  colored left edge = status
```

Let's break down **every single piece** of that card:

### 3a. The colored left edge (status)
The thin vertical bar on the left tells you the donor's state at a glance:

| Color | Status | Means |
|-------|--------|-------|
| Dim grey | **Pending** | Eligible and ranked, but **not contacted yet** (waiting in a later wave) |
| Amber/yellow | **Contacted** | We've messaged them this wave; **waiting for their reply** |
| Blue | **Confirmed** | They said **yes** — they're coming to donate |
| Faded grey | **Declined** | They said **no** (busy/can't make it) |

(A donor can also become **ineligible** if they reply that they donated recently — see Part 6.)

### 3b. The header row
- **Name** — the donor's name (e.g., *Ahmed Khan*).
- **Blood group** (red text) — their group, e.g., *AB-*.
- **`[compatible]` tag** — appears only when this donor's group is **not the exact group requested**
  but is **medically safe** to give to the patient. Example: the request is for AB-, but this donor
  is O- — O- can safely be given to an AB- patient, so it's shown with a "compatible" tag.
- **Status badge + wave** — e.g., `Contacted · W1`. The `W1` means **Wave 1** (the first 8 donors).
  `W2` = the next 8, and so on.

### 3c. The stats row (the four numbers)
This is `2.3 km · 140d since last · responds 90% · 1×/30d`. Each number is a real factor in the ranking:

| Number | What it is | Why it matters |
|--------|-----------|----------------|
| **2.3 km** | Straight-line distance from the **hospital** to the donor | Closer donors can arrive faster — the biggest scoring factor |
| **140d since last** | Days since this donor **last gave blood** | They must have recovered (men need >90 days, women >120). More days = more "ready" |
| **responds 90%** | Their historical **response rate** — how often they reply when contacted | A reliable donor is worth contacting |
| **1×/30d** | How many times they've been **contacted in the last 30 days** ("fatigue") | High = we've been bothering them a lot. **Shown in yellow if 3 or more** — a warning |

### 3d. The "why" sentence (explainable AI)
The italic line at the bottom is a **plain-English reason** the system picked this donor, e.g.:
*"Recommending Ahmed Khan — closest eligible AB- donor, last gave blood 140 days ago, responds 90%
of the time."*

This is a key selling point: the system doesn't just output a score, it **explains itself** so a
coordinator can trust and defend each choice.

### 3e. How the cards are ordered
The cards are sorted **best donor first**. "Best" is decided by a single score (explained in Part 5).
The top 8 cards are Wave 1 (contacted immediately); the rest wait.

---

## Part 4 — Who counts as "eligible" (the gate)

Before ranking anyone, the system **filters out** donors who shouldn't be asked. A donor is
**eligible** only if **all** of these are true:

1. **Age 18–60** — standard donation age range.
2. **Recovered from their last donation:**
   - **Men:** more than **90 days** since last donation.
   - **Women:** more than **120 days** (a longer recovery window).
3. **Right blood group** — by default, an **exact** match to what was requested.

Anyone failing these is removed before scoring — they never appear as a card. This is why you might
have 220 donors in the database but only, say, 37 show up for an "O+" request.

**Compatibility fallback:** if there aren't enough exact-group matches, the system **broadens** to
medically-compatible groups (e.g., an AB- patient can also receive A-, B-, or O-). Those donors get
the `[compatible]` tag. This is controlled automatically, or by an `allow_compatible` flag.

---

## Part 5 — How a donor's score is calculated (in plain words)

Every eligible donor gets a score from **0 to 1**. Higher = better. The formula:

```
score = 0.40 × proximity      (how close they are)
      + 0.25 × recency        (how long since they last donated)
      + 0.20 × response_rate  (how reliably they reply)
      − 0.15 × fatigue         (how much we've contacted them lately)
```

In everyday language: **"Pick people who are close, well-rested, reliable, and whom we haven't been
pestering."**

- **Proximity (40%)** — the closer to the hospital, the higher. Distance is measured with the
  Haversine formula (straight-line distance between two lat/long points).
- **Recency (25%)** — the longer since their last donation (up to a year), the more "ready" they are.
- **Response rate (20%)** — a donor who usually replies is more useful than one who never does.
- **Fatigue (−15%)** — a **penalty**. The more times we've contacted them in 30 days, the lower
  their score, so we naturally spread the load instead of always hitting the same people.

The donors are then sorted by this score, best first — and that's the order of the cards.

---

## Part 6 — Understanding donor replies (the clever bit)

When a contacted donor replies in free text, the system uses the LLM to classify it into one of
**three** intents — and this is more nuanced than a simple yes/no:

| Reply (any language) | Classified as | Card becomes |
|----------------------|---------------|--------------|
| *"Haan ji, main aa raha hoon"* (yes, I'm coming) | **confirm** | Confirmed (blue) — counts toward the target |
| *"Sorry, abhi nahi aa sakta"* (can't make it) | **decline** | Declined (faded) |
| *"Maine pichle mahine blood diya tha"* (I gave blood last month) | **eligibility_update** | Ineligible — **NOT a refusal** |

That third case is important: the person is **willing**, they just **can't right now** because they
recently donated. A naive system would mark this as a "no." LifeLine understands it's an eligibility
issue, which is more accurate and respectful.

(If the LLM is unavailable, a keyword-based fallback handles these so the app never breaks.)

---

## Part 7 — What "waves" mean and the "Advance wave" button

This is the anti-spam heart of the system.

- When a request is created, **all** eligible donors are ranked and split into **waves of 8**.
- **Wave 1** (the best 8) is contacted **immediately**.
- Waves 2, 3, … wait as **Pending**.
- The **"Advance wave"** button contacts the **next 8** — only when you decide you need more.

So instead of messaging all 37 matches at once (a "blast"), you message 8, watch who confirms, and
escalate one wave at a time. It's a **manual button** (not an automatic timer) because that's more
reliable during a live demo and it reflects how responsible outreach should actually work.

---

## Part 8 — The dashboard counters explained

At the top of the dashboard, above the cards:

- **The ring** — shows **confirmed / needed** (e.g., 2/3). It fills up like a progress circle as
  donors confirm.
- **"Contacted" number** — how many donors we've messaged so far (8 after wave 1, 16 after wave 2…).
- **"Spam Shield" stat** — shows **contacted / total matching** (e.g., 8 / 37). This is the
  headline number: *"a mass blast would have messaged 37 people; we contacted 8."*

Below the cards you'll also see notes when relevant:
- **🌐 Network health** — *"N over-contacted volunteers held back to later waves"* (these are
  eligible people we deliberately delayed because we've been messaging them too often lately).
- **🛡️ Spam Shield note** — the same blast-vs-contacted message in a sentence.
- **🧬 Compatibility note** — appears if we had to broaden to compatible blood groups.
- **✅ Dispatch summary** — once enough donors confirm, a green card lists the confirmed donors with
  their **names and phone numbers** to call. This is the coordinator's final deliverable.

---

## Part 9 — The map explained

- A real **Karachi map** (OpenStreetMap — no API key needed).
- A **red marker** = the hospital, labeled with its name.
- Every matched donor is a **colored dot**, using the same status colors as the cards
  (green = eligible/pending, amber = contacted, blue = confirmed, grey = declined).
- The map **auto-zooms** to the hospital when a request starts.
- **Hover a dot** to see that donor's name, group, status, and distance.
- A **legend** at the bottom explains the colors.

---

## Part 10 — What happens at each step (the full run, in order)

Here is the entire system, step by step, in plain words.

### Step 0 — Startup (before you do anything)
- The backend opens `data/lifeline.db` (a small SQLite file with 220 synthetic Karachi donors) and
  loads them into memory.
- It quietly "warms up" the Groq AI connection so the first real request is fast.

### Step 1 — You type a request
- In the **Chat** panel you type, e.g., *"AB negative chahiye jaldi, Liaquat National mein."*
- The frontend sends this text to the backend endpoint **`/request/parse`**.

### Step 2 — The AI reads your message
- The backend asks **Groq** (the LLM) to extract structured fields:
  **blood group, count, hospital, urgency**, plus a friendly **reply** sentence.
- It figures out *AB-*, hospital *Liaquat National*, urgency *high* (because of "jaldi").
- It returns which fields are still **missing** (here, the count).
- If Groq is slow or down, a **regex fallback** extracts what it can — the app never crashes.

### Step 3 — The chat fills in the gaps
- The extracted fields appear as **chips** at the top of the chat (Group, Hospital, Urgency…).
- Because **count** is missing, the bot asks one follow-up: *"How many units/donors are needed?"*
- You answer *"3"*. Now all required fields are present.

### Step 4 — The system builds the donor list
- The frontend calls **`/request/create`** with the complete request.
- The backend:
  1. Converts the hospital name to map coordinates (`resolve_hospital`).
  2. Filters to **eligible** donors (Part 4) and **scores** them (Part 5) via `rank_donors`.
  3. If exact matches are too few, **broadens** to compatible groups.
  4. Splits the ranked list into **waves of 8**; marks Wave 1 as **contacted**.
  5. (If the WhatsApp switch is ON) sends real messages to Wave 1 **in the background**.
  6. Returns the full list plus counts (total matching, contacted, network-protected…).

### Step 5 — The dashboard and map come alive
- The donor **cards** render (best first), the **map** lights up with pins, and the **counters**
  appear (ring at 0/3, Spam Shield at 8/37).
- The frontend now **polls `/request/{id}/status` every 2 seconds** to stay live.

### Step 6 — Donors respond
- In a real deployment, donors reply on WhatsApp. In the demo, you use the **demo strip** buttons.
- Each reply hits **`/donor/respond`**, the LLM classifies it (Part 6), and the donor's card updates
  (turns blue for confirm, faded for decline, or ineligible for "gave blood recently").
- The confirmed ring ticks up.

### Step 7 — Escalate if needed
- If you still need more confirmations, click **Advance wave** → **`/request/{id}/escalate`** →
  the next 8 donors flip to **contacted**.

### Step 8 — Done
- When **confirmed ≥ needed**, the request is **done**: polling stops and the green **dispatch
  summary** appears with the confirmed donors' names and phone numbers. The coordinator now knows
  exactly who to call.

---

## Part 11 — What each file does (the codebase map)

| File | Plain-English job |
|------|-------------------|
| `data/generate_donors.py` | Creates the 220 fake-but-realistic donors and saves them to `lifeline.db` |
| `data/lifeline.db` | The portable donor database that ships with the project |
| `backend/db.py` | Loads donors from `lifeline.db` into memory at startup |
| `backend/ranking.py` | The "matching brain": eligibility gate, distance, scoring, and the "why" sentences |
| `backend/llm.py` | Talks to Groq: parses requests, classifies replies, transcribes voice (with regex fallbacks) |
| `backend/whatsapp.py` | Optional real WhatsApp sending via Meta's API (behind the switch) |
| `backend/main.py` | The web server: defines all the endpoints and holds the in-memory request state |
| `frontend/src/App.jsx` | The brain of the UI: tracks the conversation, calls the backend, polls for status |
| `frontend/src/components/ChatPanel.jsx` | The chat box, field chips, and microphone |
| `frontend/src/components/MapPanel.jsx` | The Karachi map with hospital and donor pins |
| `frontend/src/components/DashboardPanel.jsx` | The donor cards, ring, Spam Shield, and dispatch summary |
| `frontend/src/components/DonorSimPanel.jsx` | The demo strip (simulate replies + advance wave) |
| `frontend/src/components/WhatsAppToggle.jsx` | The Mocked/Live WhatsApp switch in the header |

---

## Part 12 — The endpoints (how the frontend talks to the backend)

| Endpoint | What it does |
|----------|--------------|
| `GET /health` | Is the server up? How many donors loaded? |
| `GET /donors` | The full donor list (used by the map) |
| `POST /request/parse` | Text → structured fields + missing fields + a reply |
| `POST /request/create` | Rank donors, open a request, contact wave 1 |
| `GET /request/{id}/status` | Live state: counts + every donor's status (polled every 2s) |
| `POST /request/{id}/escalate` | Contact the next wave of 8 |
| `POST /donor/respond` | A donor's reply → classify → update their card |
| `POST /voice` | Audio → Whisper transcription → reuse the parse flow |
| `GET /whatsapp/status` | Is the WhatsApp switch configured / on / live? |
| `POST /whatsapp/toggle` | Turn live WhatsApp sending on or off |

---

## Part 13 — Key things to remember

- The **donor cards** are the product: ranked, color-coded, and each with a reason.
- **Eligibility first, then score.** Distance matters most; fatigue is a penalty.
- **Waves, not blasts.** 8 at a time, escalate on purpose.
- **"Gave blood recently" is not a no** — it's an eligibility update.
- **Spam Shield** is the headline: *"a blast would've messaged N; we contacted M."*
- **Nothing crashes** — every AI call has a fallback; WhatsApp is off by default.
