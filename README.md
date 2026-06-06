# 🩸 LifeLine — Real-Time Blood Donor Matching

A hackathon prototype for **Al-Khidmat Karachi** (Build With AI 2026). A coordinator types a
plain-language blood request (Urdu / Roman Urdu / English); LifeLine extracts the fields, ranks
eligible nearby donors with an explainable score, "contacts" them in waves, protects the volunteer
network from over-asking, and shows a live confirmation count.

> **This is a demo.** State is in-memory, the chat is a mocked web UI (no real WhatsApp/SMS),
> and donors come from a synthetic dataset. See [`docs/PLAN.md`](docs/PLAN.md) for the full build plan
> and [`CLAUDE.md`](CLAUDE.md) for the project harness.

---

## Getting started

### Prerequisites
- **Node.js 18+** and **npm** ([nodejs.org](https://nodejs.org))
- **Python 3.10+** ([python.org](https://python.org) — on Windows, `winget install Python.Python.3.12`)
- A free **Groq API key** ([console.groq.com](https://console.groq.com) → API Keys) — needed for the
  natural-language intake (C1). The app boots without it but falls back to regex parsing.

### Quick start (recommended)

A single launcher handles everything — finds Python, creates the backend venv, installs both dependency
sets, generates the donor dataset, and starts both servers.

**Windows:** double-click **`run.cmd`**, or from any terminal:
```
run.cmd
```

**macOS / Linux:**
```bash
./dev.sh
```

Then open **http://localhost:5173**. API docs are at **http://localhost:8000/docs**.

The first run auto-installs everything (donor dataset, Python venv + backend deps, frontend npm deps),
then opens two windows — one per server. No admin rights needed.

> First run also creates `backend/.env` from the template. **Add your `GROQ_API_KEY` to it**, then
> restart the backend before using the chat intake.

Launcher flags:

| Command | What it does |
|---------|--------------|
| `run.cmd` / `./dev.sh` | Setup-if-needed, then start both servers |
| `run.cmd setup` / `./dev.sh setup` | Prepare deps & data only — don't start servers |
| `run.cmd fresh` / `./dev.sh fresh` | Wipe and reinstall both dependency sets, then start |

### Manual setup (if you prefer)

```bash
# 1. (Optional) re-seed the donor dataset — a prebuilt data/lifeline.db ships with the repo
cd data
python generate_donors.py            # drops & rebuilds lifeline.db (220 rows)

# 2. Backend — FastAPI on :8000
cd ../backend
python -m venv .venv
.venv\Scripts\activate                # Windows
# source .venv/bin/activate           # macOS/Linux
pip install -r requirements.txt
cp .env.example .env                  # then add your GROQ_API_KEY
uvicorn main:app --reload --port 8000

# 3. Frontend — Vite + React on :5173 (new terminal)
cd ../frontend
npm install
npm run dev
```

> **Windows note:** if `python`/`uvicorn` aren't on your PATH (common when Python was installed for the
> current user only), call the venv directly: `.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000`.
> The `run.cmd` launcher handles this for you.

---

## Project structure

```
.
├── run.cmd / dev.sh         # one-command dev launchers (Windows / Unix)
├── CLAUDE.md                # project harness & context
├── docs/PLAN.md             # full build plan (read for detail)
├── data/
│   ├── generate_donors.py   # synthetic dataset seeder (pure stdlib)
│   └── lifeline.db          # portable SQLite donor store (committed to the repo)
├── backend/                 # FastAPI app (Python)
│   ├── main.py              # app, CORS, startup donor load, endpoints
│   ├── db.py                # SQLite data layer — loads donors into memory
│   ├── ranking.py           # matching brain: eligibility + composite score
│   ├── llm.py               # Groq intake parse + reply classification
│   ├── whatsapp.py          # optional Meta WhatsApp Cloud API outreach (switch)
│   ├── requirements.txt
│   └── .env.example         # copy to .env, add keys (gitignored)
└── frontend/                # React + Vite
    └── src/
        ├── App.jsx
        └── components/      # ChatPanel · MapPanel · DashboardPanel · DonorSimPanel
```

## Tech stack

- **Backend:** Python · FastAPI · uvicorn · Groq (`llama-3.3-70b-versatile` for parsing, `whisper-large-v3-turbo` for optional voice)
- **Frontend:** React · Vite · react-leaflet + OpenStreetMap tiles (no key)
- **Portable SQLite** — donors load from `data/lifeline.db` into memory at startup (no server, no driver, ships with the repo). Per-request state (waves, confirmations) stays in memory and resets on restart.

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness + donor count |
| `GET` | `/donors` | List donors (for the map) |
| `POST` | `/request/parse` | Raw text → structured fields + missing fields |
| `POST` | `/request/create` | Rank donors, open request, contact wave 1 |
| `GET` | `/request/{id}/status` | Wave, confirmed count, donor states (poll every 2s) |
| `POST` | `/request/{id}/escalate` | Contact the next wave |
| `POST` | `/donor/respond` | Classify a donor reply (confirm / decline / eligibility) |
| `POST` | `/voice` *(optional)* | Audio → Whisper → reuse parse |
| `GET` | `/whatsapp/status` | WhatsApp switch state (configured / enabled / live) |
| `POST` | `/whatsapp/toggle` | Flip live WhatsApp outreach on/off at runtime |

> All endpoints above are implemented. WhatsApp outreach is **off by default** (fully mocked); flip it
> on with the header toggle only when Meta Cloud API creds are set in `backend/.env`.

## Troubleshooting

- **"Python was not found"** — the Windows Store stub is on PATH but real Python isn't.
  Install it (`winget install Python.Python.3.12`) and re-run `run.cmd`, which finds it automatically.
- **Chat returns rough/empty parses** — `GROQ_API_KEY` isn't set in `backend/.env`. The app falls
  back to regex so it never crashes, but the LLM intake needs the key.
- **Map tiles don't load** — OSM tiles need internet; donor pins still render without them.
- **CORS errors** — the backend only allows `http://localhost:5173`. Run the frontend on that port.
