# LifeLine — Presentation Guide

> How to pitch and demo LifeLine to judges. For a full explanation of how the system works,
> see **`SYSTEM_GUIDE.md`**. This file is just for presenting.

---

## 1. The 10-second pitch (memorize this)

> *"LifeLine is an AI blood-donor matcher for Al-Khidmat. Type a request in any language; it finds
> the closest eligible donors, tells you **why** each one was chosen, and contacts them in small
> waves instead of spamming hundreds — so the volunteer network stays alive for the next emergency."*

---

## 2. The problem (set this up in 15 seconds)

> *"When a hospital needs blood, the usual fix is to forward the request to hundreds of people.
> Most are ineligible, far away, or the wrong group — and the same reliable volunteers get spammed
> every time until they stop replying. It's slow, noisy, and it burns out the network."*

Then: *"Here's how LifeLine does it instead."*

---

## 3. The 3-minute demo script

> **Before you start:** backend on `:8000`, frontend on `:5173`, `GROQ_API_KEY` set in
> `backend/.env`. Send one message beforehand to warm up the AI so the live demo is instant.

| # | Do this | Say this |
|---|---------|----------|
| 1 | Type: `AB negative chahiye jaldi, Liaquat National mein` | "I'm typing Roman Urdu — and notice it understood the group, the hospital, and flagged **high urgency** (see the red pulse)." |
| 2 | It asks for the count → type `3` | "It only asks for what's missing." |
| 3 | The map lights up, donor cards appear | "It instantly ranked the eligible donors near the hospital." |
| 4 | Point at one card's **why** sentence and read it | "Every donor comes with a reason — closest, recently rested, reliable. Not a black box." |
| 5 | Click **✅ Confirm** twice on the demo strip | "Donors are replying — the confirmed counter ticks up." |
| 6 | Click **🩸 "Gave blood last month"** | "This isn't a refusal — the AI understood it as an *eligibility update*. The person's willing, just can't right now." |
| 7 | Click **⏭ Advance wave** | "We didn't blast everyone. We reached 8, and only escalated because we needed more." |
| 8 | Point at the **Spam Shield** stat | "A mass blast would have messaged [read the number] people. We contacted [read the number]." |
| 9 | Point at the **network-health** note | "And these volunteers we deliberately held back — they've been over-contacted. We protect the people who save lives." |
| 10 | Show the green **dispatch summary** | "Target reached. The coordinator now has exactly who to call — names and phone numbers. Seconds, not hours." |
| 11 | *(Optional)* Hand over the keyboard | "Type your own request — any language. Try to break it." |

---

## 4. The four lines that win (keep these visible and say them)

1. **Explainable:** "It tells you **why** each donor — not just a score."
2. **Anti-spam:** "Waves of 8, not a blast to hundreds."
3. **The number:** "A blast would've messaged **N**; we contacted **M**." *(read the live numbers)*
4. **Network health:** "We protect the volunteers who save lives."

---

## 5. Judge Q&A (have these ready)

| Question | Answer |
|----------|--------|
| "Is this real WhatsApp?" | "Mocked by default so the demo is reliable — but there's a real Meta WhatsApp integration behind a switch. Flip it and contacted donors get an actual message." |
| "Where's the donor data from?" | "Synthetic but realistic — 220 Karachi donors with proper blood-group distribution, locations, and history, in a portable SQLite file that ships with the project." |
| "What if the AI is rate-limited mid-demo?" | "Every AI call has a regex fallback, so it never crashes. We also cache and warm up the model first." |
| "How does the ranking work?" | "Eligibility gate first — age and recovery window — then a weighted score: proximity 40%, recency 25%, reliability 20%, minus fatigue 15%." |
| "Rare blood groups?" | "If exact matches are too few, it broadens to medically-compatible groups and labels them clearly." |
| "What's next / the roadmap?" | "Real two-way WhatsApp, a donor-facing app, multi-hospital coordination, and donation-receipt verification (OCR) reusing the same chat + dashboard." |

---

## 6. Demo failure recovery (if something goes wrong)

- **AI gives a rough parse** → the regex fallback still extracts fields; just proceed, or retype more clearly.
- **Map tiles don't load** → "tiles need internet, but the donor pins still render" — keep going.
- **A click doesn't register** → use the **Advance wave** button to move forward; the flow still demos.
- **Worst case** → the Spam Shield and "why" cards are static enough to talk through even without live replies.

---

## 7. One-sentence summaries by audience

- **For a technical judge:** "FastAPI + Groq LLM with regex fallbacks, a weighted Haversine ranking engine, and a React/Leaflet live dashboard — all running free and locally."
- **For a non-technical judge:** "You type who needs blood, and it instantly tells you the best few people to call and why — without spamming everyone."
- **For Al-Khidmat:** "It makes your coordinators faster and protects your volunteers from burnout, so your network is ready every time."
