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
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ranking.py is the matching brain — reuse it, never reinvent it.
import ranking
import llm

# Wave 1 contacts the top N eligible donors; escalation adds the next N.
WAVE_SIZE = 8

# --- Paths --------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BACKEND_DIR)
DONORS_CSV = os.path.join(REPO_ROOT, "data", "donors.csv")

# --- In-memory state (no DB — hackathon guardrail) ----------------------------
STATE = {
    "donors": [],       # list[dict] loaded from donors.csv
    "requests": {},     # request_id -> request object
    "next_id": 1,       # incrementing request id counter
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


# --- Request bodies -----------------------------------------------------------
class ParseBody(BaseModel):
    text: str


class CreateBody(BaseModel):
    blood_group: str
    count: int = 1
    hospital: str
    urgency: str = "normal"
    location: Optional[str] = None
    raw_text: Optional[str] = None
    allow_compatible: bool = False


class RespondBody(BaseModel):
    donor_id: str
    text: str
    request_id: Optional[int] = None


# A donor is "messaged" once their status leaves 'pending' (they never go back).
_MESSAGED = {"contacted", "confirmed", "declined", "ineligible"}
# Donor reply intent -> resulting status.
_INTENT_STATUS = {"confirm": "confirmed", "decline": "declined", "eligibility_update": "ineligible"}
# A donor contacted this many times in the last 30d is treated as "fatigued".
_FATIGUE_THRESHOLD = 3


def _summary(req: dict) -> dict:
    """Live view of a request: per-status counts + donor states. Shared by
    /request/create and /request/{id}/status so the frontend sees one shape."""
    donors = req["donors"]
    confirmed = sum(1 for d in donors if d["status"] == "confirmed")
    # Network health: fatigued (over-contacted) donors we pushed to later waves
    # instead of messaging now — we protect the volunteer network.
    network_protected = sum(
        1 for d in donors
        if d["status"] == "pending" and int(d["times_contacted_last_30d"]) >= _FATIGUE_THRESHOLD
    )
    return {
        "id": req["id"],
        "blood_group": req["blood_group"],
        "count_needed": req["count_needed"],
        "hospital": req["hospital"],
        "hospital_latlng": req["hospital_latlng"],
        "urgency": req["urgency"],
        "used_compatible": req["used_compatible"],
        "total_matching": req["total_matching"],
        "exact_count": req["exact_count"],
        "current_wave": req["current_wave"],
        "contacted": sum(1 for d in donors if d["status"] in _MESSAGED),
        "confirmed": confirmed,
        "declined": sum(1 for d in donors if d["status"] == "declined"),
        "ineligible": sum(1 for d in donors if d["status"] == "ineligible"),
        "pending": sum(1 for d in donors if d["status"] == "pending"),
        "network_protected": network_protected,
        "done": confirmed >= req["count_needed"],
        "donors": donors,
    }


def _get_request(req_id: int) -> dict:
    req = STATE["requests"].get(req_id)
    if req is None:
        raise HTTPException(status_code=404, detail=f"Request {req_id} not found.")
    return req


# --- C1: natural-language intake ----------------------------------------------
@app.post("/request/parse")
def request_parse(body: ParseBody):
    """Raw text -> {blood_group, count, location, hospital, urgency, missing_fields}.
    Uses Groq with a regex fallback, so it never 500s."""
    return llm.parse_request(body.text)


# --- C2: rank donors + open a request, contact wave 1 -------------------------
@app.post("/request/create")
def request_create(body: CreateBody):
    """Resolve the hospital, rank eligible matching donors, open a request, and
    mark the top WAVE_SIZE donors as contacted (wave 1).

    Returns the ranked donor states plus `total_matching` for the Spam Shield
    ("a blast would have messaged N; we contacted M")."""
    hospital_latlng = ranking.resolve_hospital(body.hospital)
    if hospital_latlng is None:
        raise HTTPException(
            status_code=400,
            detail=f"Hospital '{body.hospital}' not recognised. "
                   f"Try one of: {', '.join(list(ranking.HOSPITALS)[:6])} ...",
        )

    # Exact blood-group match first. If that can't cover the need, broaden to
    # medically-compatible donors (e.g. an AB- patient can also receive A-/B-/O-).
    exact = ranking.rank_donors(
        STATE["donors"], body.blood_group, hospital_latlng,
        count_needed=body.count, allow_compatible=False,
    )
    ranked = exact
    used_compatible = False
    if body.allow_compatible or len(exact) < body.count:
        broadened = ranking.rank_donors(
            STATE["donors"], body.blood_group, hospital_latlng,
            count_needed=body.count, allow_compatible=True,
        )
        if body.allow_compatible or len(broadened) > len(exact):
            ranked = broadened
            used_compatible = len(broadened) > len(exact)

    # Assign waves + initial status. Wave 1 (top WAVE_SIZE) is "contacted".
    donor_states = []
    for i, d in enumerate(ranked):
        wave = i // WAVE_SIZE + 1
        donor_states.append({
            **d,
            "wave": wave,
            "status": "contacted" if wave == 1 else "pending",
        })

    req_id = STATE["next_id"]
    STATE["next_id"] += 1
    request = {
        "id": req_id,
        "raw_text": body.raw_text,
        "blood_group": body.blood_group,
        "count_needed": body.count,
        "location_text": body.location,
        "hospital": body.hospital,
        "hospital_latlng": list(hospital_latlng),
        "urgency": body.urgency,
        "allow_compatible": body.allow_compatible,
        "used_compatible": used_compatible,
        "total_matching": len(ranked),  # eligible matches in the pool we used
        "exact_count": len(exact),      # how many were an exact group match
        "current_wave": 1,
        "donors": donor_states,
    }
    STATE["requests"][req_id] = request
    return _summary(request)


# --- C5: live status, wave escalation, donor replies --------------------------
@app.get("/request/{req_id}/status")
def request_status(req_id: int):
    """Current wave, confirmed count, and donor states. Frontend polls this every 2s."""
    return _summary(_get_request(req_id))


@app.post("/request/{req_id}/escalate")
def request_escalate(req_id: int):
    """Contact the next wave: flip the next block of WAVE_SIZE pending donors to 'contacted'."""
    req = _get_request(req_id)
    next_wave = req["current_wave"] + 1
    promoted = 0
    for d in req["donors"]:
        if d["wave"] == next_wave and d["status"] == "pending":
            d["status"] = "contacted"
            promoted += 1
    if promoted:
        req["current_wave"] = next_wave
    return _summary(req)


@app.post("/donor/respond")
def donor_respond(body: RespondBody):
    """Classify a donor's free-text reply (confirm/decline/eligibility) and update state.
    If no request_id is given, applies to the most recent request (demo convenience)."""
    if body.request_id is not None:
        req = _get_request(body.request_id)
    elif STATE["requests"]:
        req = STATE["requests"][max(STATE["requests"])]
    else:
        raise HTTPException(status_code=404, detail="No active request.")

    donor = next((d for d in req["donors"] if d["donor_id"] == body.donor_id), None)
    if donor is None:
        raise HTTPException(status_code=404, detail=f"Donor {body.donor_id} not in request {req['id']}.")

    intent = llm.classify_reply(body.text)
    donor["status"] = _INTENT_STATUS.get(intent, donor["status"])
    donor["reply_text"] = body.text

    return {"donor_id": body.donor_id, "intent": intent, "status": donor["status"], **_summary(req)}


# --- POST /voice (optional, Phase 7) — audio -> Whisper -> reuse parse ---------
