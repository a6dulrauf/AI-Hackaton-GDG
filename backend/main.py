"""
LifeLine — FastAPI backend (SCAFFOLD).

Boots cleanly, enables CORS for the Vite dev server, and loads the synthetic
donor dataset into memory at startup. Feature endpoints (parse / create / status
/ escalate / respond / voice) are intentionally NOT implemented yet — they are
listed in docs/PLAN.md §8 and will be built in order on top of this shell.

Run:  cd backend && uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import csv
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ranking.py is the matching brain — reuse it, never reinvent it.
import ranking  # noqa: F401  (used by feature endpoints, kept imported to fail fast if broken)

# --- Paths --------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BACKEND_DIR)
DONORS_CSV = os.path.join(REPO_ROOT, "data", "donors.csv")

# --- In-memory state (no DB — hackathon guardrail) ----------------------------
STATE = {
    "donors": [],      # list[dict] loaded from donors.csv
    "requests": {},    # request_id -> request object (populated by feature endpoints)
}


def load_donors(path: str = DONORS_CSV) -> list[dict]:
    """Load donors.csv into a list of dicts. Returns [] (with a warning) if missing."""
    if not os.path.exists(path):
        print(f"[startup] WARNING: {path} not found. "
              f"Run `cd data && python generate_donors.py` to create it.")
        return []
    with open(path, encoding="utf-8") as f:
        donors = list(csv.DictReader(f))
    print(f"[startup] Loaded {len(donors)} donors from {path}")
    return donors


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATE["donors"] = load_donors()
    yield
    STATE["donors"].clear()
    STATE["requests"].clear()


app = FastAPI(title="LifeLine API", version="0.1.0-scaffold", lifespan=lifespan)

# CORS — allow the Vite dev server (and the alternate localhost form).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Liveness + how many donors are loaded — handy to confirm the scaffold boots."""
    return {"status": "ok", "donors_loaded": len(STATE["donors"])}


@app.get("/donors")
def get_donors():
    """List donors for the map. (Trivial passthrough of in-memory state.)"""
    return STATE["donors"]


# --- Feature endpoints (TODO — see docs/PLAN.md §8, build in order) ------------
# POST /request/parse        — raw text -> structured fields + missing_fields
# POST /request/create       — rank + open request + mark wave-1 contacted
# GET  /request/{id}/status  — wave, confirmed count, donor states (poll every 2s)
# POST /request/{id}/escalate— contact next wave
# POST /donor/respond        — {donor_id, text} -> classify confirm/decline/eligibility
# POST /voice (optional)     — audio -> Whisper -> reuse parse
