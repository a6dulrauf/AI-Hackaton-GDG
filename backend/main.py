"""
LifeLine — FastAPI backend (SCAFFOLD).

Boots cleanly, enables CORS for the Vite dev server, and loads the synthetic
donor dataset into memory at startup. Feature endpoints (parse / create / status
/ escalate / respond / voice) are intentionally NOT implemented yet — they are
listed in docs/PLAN.md §8 and will be built in order on top of this shell.

Run:  cd backend && uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ranking.py is the matching brain — reuse it, never reinvent it.
import ranking
import llm
import whatsapp
import db  # portable SQLite donor store (data/lifeline.db)

# Wave 1 contacts the top N eligible donors; escalation adds the next N.
WAVE_SIZE = 8

# --- In-memory request state --------------------------------------------------
# Donors live in SQLite (db.py); per-request waves/confirmations are ephemeral
# demo state and intentionally reset on restart.
STATE = {
    "donors": [],       # list[dict] loaded from data/lifeline.db at startup
    "requests": {},     # request_id -> request object
    "next_id": 1,       # incrementing request id counter
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATE["donors"] = db.load_donors()
    # Warm up Groq off the event loop so the first real parse isn't cold.
    # Fire-and-forget — never blocks startup or crashes if Groq is unavailable.
    asyncio.get_running_loop().run_in_executor(None, llm.warmup)
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


def _dispatch_whatsapp(background: BackgroundTasks, req: dict, donors: list) -> None:
    """When the WhatsApp switch is live, message freshly-contacted donors in the
    background so outbound latency never affects the API response. No-op (fully
    mocked) when the switch is off — the default."""
    if not whatsapp.is_live():
        return
    for d in donors:
        background.add_task(whatsapp.notify_donor, d, req)


# --- C1: natural-language intake ----------------------------------------------
@app.post("/request/parse")
def request_parse(body: ParseBody):
    """Raw text -> {blood_group, count, location, hospital, urgency, missing_fields}.
    Uses Groq with a regex fallback, so it never 500s."""
    return llm.parse_request(body.text)


# --- C2: rank donors + open a request, contact wave 1 -------------------------
@app.post("/request/create")
def request_create(body: CreateBody, background: BackgroundTasks):
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
    # Wave 1 is "contacted" — if the WhatsApp switch is live, reach them for real.
    _dispatch_whatsapp(background, request, [d for d in donor_states if d["status"] == "contacted"])
    return _summary(request)


# --- C5: live status, wave escalation, donor replies --------------------------
@app.get("/request/{req_id}/status")
def request_status(req_id: int):
    """Current wave, confirmed count, and donor states. Frontend polls this every 2s."""
    return _summary(_get_request(req_id))


@app.post("/request/{req_id}/escalate")
def request_escalate(req_id: int, background: BackgroundTasks):
    """Contact the next wave: flip the next block of WAVE_SIZE pending donors to 'contacted'."""
    req = _get_request(req_id)
    next_wave = req["current_wave"] + 1
    promoted = []
    for d in req["donors"]:
        if d["wave"] == next_wave and d["status"] == "pending":
            d["status"] = "contacted"
            promoted.append(d)
    if promoted:
        req["current_wave"] = next_wave
    # Newly contacted this wave — WhatsApp them too when the switch is live.
    _dispatch_whatsapp(background, req, promoted)
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


# --- S1: voice intake — audio -> Whisper -> transcript (reuses /request/parse) -
@app.post("/voice")
async def voice(file: UploadFile = File(...)):
    """Transcribe an uploaded audio clip with Groq Whisper. The frontend feeds the
    returned text back through the normal parse flow, so voice == typing."""
    audio = await file.read()
    text = llm.transcribe(audio, file.filename or "voice.webm")
    if not text:
        raise HTTPException(status_code=503, detail="Transcription unavailable. Try typing instead.")
    return {"text": text}


# --- WhatsApp (Meta Cloud API) — config check + test send ---------------------
class WaTestBody(BaseModel):
    to: Optional[str] = None        # digits + country code; falls back to WHATSAPP_DEMO_REDIRECT
    use_template: bool = True       # first contact must be a template; hello_world ships by default
    template: str = "hello_world"
    text: str = "🩸 LifeLine test message — your WhatsApp integration works!"


class WaToggleBody(BaseModel):
    enabled: bool


def _wa_status() -> dict:
    """Shared WhatsApp switch state — consumed by the frontend header toggle."""
    return {
        "configured": whatsapp.is_configured(),   # creds present in .env
        "enabled": whatsapp.is_enabled(),          # the switch
        "live": whatsapp.is_live(),                # switch ON *and* configured
        "has_demo_redirect": bool(os.getenv("WHATSAPP_DEMO_REDIRECT")),
        "api_version": whatsapp.GRAPH_VERSION,
    }


@app.get("/whatsapp/status")
def whatsapp_status():
    """Quick check of the WhatsApp switch + env (without exposing the token)."""
    return _wa_status()


@app.post("/whatsapp/toggle")
def whatsapp_toggle(body: WaToggleBody):
    """Flip the live-sending switch at runtime. Can't enable without creds."""
    if body.enabled and not whatsapp.is_configured():
        raise HTTPException(
            status_code=400,
            detail="Cannot enable: set WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID in backend/.env.",
        )
    whatsapp.set_enabled(body.enabled)
    return _wa_status()


@app.post("/whatsapp/test")
def whatsapp_test(body: WaTestBody):
    """Send one real WhatsApp message to verify the integration end-to-end."""
    if not whatsapp.is_configured():
        raise HTTPException(status_code=400,
                            detail="Set WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID in backend/.env.")
    to = body.to or os.getenv("WHATSAPP_DEMO_REDIRECT")
    if not to:
        raise HTTPException(status_code=400, detail="Provide 'to' or set WHATSAPP_DEMO_REDIRECT.")
    if body.use_template:
        ok, info = whatsapp.send_template(to, body.template, "en_US")
    else:
        ok, info = whatsapp.send_text(to, body.text)
    if not ok:
        raise HTTPException(status_code=502, detail=f"WhatsApp send failed: {info}")
    return {"sent": True, "to": whatsapp.normalize_phone(to), "via": "template" if body.use_template else "text", "response": info}
