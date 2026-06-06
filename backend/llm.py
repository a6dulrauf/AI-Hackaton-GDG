"""
LifeLine — Groq LLM helpers.

  parse_request(text)  -> {blood_group, count, location, hospital, urgency, missing_fields}
                          from mixed Urdu / Roman-Urdu / English. Always returns a
                          valid dict — falls back to regex if Groq is unavailable.

Guardrails (CLAUDE.md):
  - Model: llama-3.3-70b-versatile, STRICT JSON, few-shot examples.
  - NEVER 500 on a rate-limit — regex fallback covers every failure path.
"""
import os
import re
import json
from typing import Optional

import ranking  # reuse the hospital aliases/list for fallback hospital detection

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads backend/.env if present
except ImportError:
    pass

GROQ_MODEL = "llama-3.3-70b-versatile"
WHISPER_MODEL = "whisper-large-v3-turbo"

REQUIRED_FIELDS = ["blood_group", "count", "hospital"]
VALID_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}

# Demo-latency guardrails: cap how long we wait on Groq before falling back to
# regex, and don't retry (a hung demo is worse than a slightly-rougher parse).
LLM_TIMEOUT_S = 6.0       # parse / classify
TRANSCRIBE_TIMEOUT_S = 30.0  # audio upload + transcription needs longer

_groq_client = None
# Cache successful LLM parses by exact text, so a repeated demo line is instant.
_PARSE_CACHE = {}


def get_client():
    """Lazily create the Groq client. Returns None if the SDK/key is unavailable
    so callers transparently fall back to regex and never crash."""
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[llm] GROQ_API_KEY not set — using regex fallback.")
        return None
    try:
        from groq import Groq
        # Fail fast: bounded timeout, no retries (regex fallback covers failures).
        _groq_client = Groq(api_key=api_key, timeout=LLM_TIMEOUT_S, max_retries=0)
    except Exception as e:  # noqa: BLE001
        print(f"[llm] Groq client unavailable ({e}) — using regex fallback.")
        return None
    return _groq_client


def warmup():
    """Prime the Groq connection/model once at startup so the first real
    request isn't cold. Safe to call repeatedly; never raises."""
    try:
        parse_request("O+ 2 Indus")
    except Exception:  # noqa: BLE001
        pass


# --- Prompt -------------------------------------------------------------------
SYSTEM_PROMPT = """You are an intake parser for a blood-donation coordinator in Karachi, Pakistan.
Extract structured fields from a blood request that may be written in English, Urdu, Roman Urdu, or a mix.
Return STRICT JSON only (no prose, no markdown) with EXACTLY these keys:
  "blood_group": one of "A+","A-","B+","B-","AB+","AB-","O+","O-", or null
  "count": integer number of donors/units needed, or null
  "location": area/neighbourhood mentioned, or null
  "hospital": hospital name mentioned, or null
  "urgency": "high" or "normal"
  "missing_fields": array with any of "blood_group","count","hospital" whose value is null

Rules:
- "negative"/"-ve"/"neg" -> "-";  "positive"/"+ve"/"pos" -> "+".
- Roman/Urdu cues for "needed": chahiye, darkaar, zaroorat, chaiye.
- Roman/Urdu cues for HIGH urgency: jaldi, urgent, foran, emergency, asap, abhi, turant. Otherwise "normal".
- Only blood_group, count and hospital are required; everything null among those goes in missing_fields."""

FEWSHOT = [
    {"role": "user", "content": "AB negative chahiye jaldi, Liaquat National mein"},
    {"role": "assistant", "content": '{"blood_group":"AB-","count":null,"location":null,"hospital":"Liaquat National Hospital","urgency":"high","missing_fields":["count"]}'},
    {"role": "user", "content": "Need 3 units O+ at Indus Hospital"},
    {"role": "assistant", "content": '{"blood_group":"O+","count":3,"location":null,"hospital":"Indus Hospital","urgency":"normal","missing_fields":[]}'},
    {"role": "user", "content": "mujhe B positive ke 2 donor chahiye gulshan ke paas AKU"},
    {"role": "assistant", "content": '{"blood_group":"B+","count":2,"location":"Gulshan","hospital":"Aga Khan University Hospital","urgency":"normal","missing_fields":[]}'},
]


def parse_request(text: str) -> dict:
    """Parse a free-text request into structured fields. Never raises."""
    key = (text or "").strip().lower()
    if key in _PARSE_CACHE:
        return _PARSE_CACHE[key]

    client = get_client()
    if client is not None:
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + FEWSHOT + \
                       [{"role": "user", "content": text}]
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
                timeout=LLM_TIMEOUT_S,
            )
            data = json.loads(resp.choices[0].message.content)
            result = _normalize(data)
            _PARSE_CACHE[key] = result  # cache only good LLM parses
            return result
        except Exception as e:  # noqa: BLE001
            print(f"[llm] parse_request fell back to regex: {e}")
    return _regex_parse(text)


# --- Normalisation + regex fallback ------------------------------------------
def _normalize(data: dict) -> dict:
    """Coerce an LLM result into the canonical shape and recompute missing_fields."""
    bg = data.get("blood_group")
    if isinstance(bg, str):
        bg = bg.strip().upper().replace(" ", "")
        bg = bg if bg in VALID_GROUPS else None
    else:
        bg = None

    count = data.get("count")
    try:
        count = int(count) if count is not None else None
    except (TypeError, ValueError):
        count = None

    hospital = data.get("hospital") or None
    # Canonicalise the hospital name against the known list when we can.
    if hospital:
        coords = ranking.resolve_hospital(hospital)
        if coords:
            for name, c in ranking.HOSPITALS.items():
                if c == coords:
                    hospital = name
                    break

    urgency = data.get("urgency")
    urgency = "high" if str(urgency).lower() == "high" else "normal"

    out = {
        "blood_group": bg,
        "count": count,
        "location": data.get("location") or None,
        "hospital": hospital,
        "urgency": urgency,
    }
    out["missing_fields"] = [f for f in REQUIRED_FIELDS if not out.get(f)]
    return out


## --- Donor reply classification (C5) -----------------------------------------
CLASSIFY_PROMPT = """You classify a blood donor's free-text reply into exactly ONE intent.
Return STRICT JSON: {"intent": "confirm" | "decline" | "eligibility_update"}.
- "confirm": they agree to donate, are available, or are coming.
- "decline": they refuse, are busy, or can't make it.
- "eligibility_update": they are WILLING but recently donated / are medically unable right now
  (e.g. "gave blood last month", "abhi pichle hafte diya tha"). This is NOT a refusal.
The reply may be in English, Urdu, or Roman Urdu."""

CLASSIFY_FEWSHOT = [
    {"role": "user", "content": "Haan ji bilkul, main aa raha hoon"},
    {"role": "assistant", "content": '{"intent":"confirm"}'},
    {"role": "user", "content": "Sorry yaar abhi nahi aa sakta, busy hoon"},
    {"role": "assistant", "content": '{"intent":"decline"}'},
    {"role": "user", "content": "Maine pichle mahine hi blood diya tha"},
    {"role": "assistant", "content": '{"intent":"eligibility_update"}'},
]

VALID_INTENTS = {"confirm", "decline", "eligibility_update"}


def classify_reply(text: str) -> str:
    """Classify a donor reply -> 'confirm' | 'decline' | 'eligibility_update'. Never raises."""
    client = get_client()
    if client is not None:
        try:
            messages = [{"role": "system", "content": CLASSIFY_PROMPT}] + CLASSIFY_FEWSHOT + \
                       [{"role": "user", "content": text}]
            resp = client.chat.completions.create(
                model=GROQ_MODEL, messages=messages, temperature=0,
                response_format={"type": "json_object"},
                timeout=LLM_TIMEOUT_S,
            )
            intent = json.loads(resp.choices[0].message.content).get("intent")
            if intent in VALID_INTENTS:
                return intent
        except Exception as e:  # noqa: BLE001
            print(f"[llm] classify_reply fell back to regex: {e}")
    return _regex_classify(text)


## --- Voice transcription (S1, Groq Whisper) ----------------------------------
def transcribe(audio_bytes: bytes, filename: str = "voice.webm") -> Optional[str]:
    """Transcribe audio via Groq Whisper. Returns the text, or None if unavailable."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=(filename, audio_bytes),
            timeout=TRANSCRIBE_TIMEOUT_S,
        )
        text = getattr(resp, "text", None)
        return text.strip() if text else None
    except Exception as e:  # noqa: BLE001
        print(f"[llm] transcribe failed: {e}")
        return None


def _regex_classify(text: str) -> str:
    t = (text or "").lower()
    # Eligibility cues first — "gave blood last month" must not read as a refusal.
    if re.search(r"gave blood|donated|last month|last week|recently|pichl[ae]|diya tha|diya hai|kiya tha", t):
        return "eligibility_update"
    if re.search(r"\b(no|nahi|nai|can'?t|cannot|busy|unable|sorry|mana|nahin)\b", t):
        return "decline"
    if re.search(r"\b(yes|haan|han|ji|ok|okay|theek|sure|ready|aa raha|aata|available|confirm|done)\b", t):
        return "confirm"
    return "confirm"  # optimistic default for ambiguous positive-ish replies


def _regex_parse(text: str) -> dict:
    """Best-effort parse with no LLM. Keeps endpoints alive on rate-limit/outage."""
    t = text or ""

    # Blood group: match AB before A/B; capture a sign keyword.
    bg = None
    m = re.search(r"\b(AB|A|B|O)\s*[-\s]*\(?\s*(positive|negative|pos|neg|\+ve|-ve|\+|-)\b?",
                  t, re.IGNORECASE)
    if m:
        letter = m.group(1).upper()
        sign_raw = m.group(2).lower()
        sign = "+" if sign_raw in ("positive", "pos", "+ve", "+") else "-"
        cand = f"{letter}{sign}"
        bg = cand if cand in VALID_GROUPS else None

    # Count: first small integer in the text.
    count = None
    mc = re.search(r"\b(\d{1,2})\b", t)
    if mc:
        count = int(mc.group(1))

    # Hospital: reuse ranking's alias/substring resolver over the whole text.
    hospital = None
    coords = ranking.resolve_hospital(t)
    if coords:
        for name, c in ranking.HOSPITALS.items():
            if c == coords:
                hospital = name
                break

    urgency = "high" if re.search(r"jaldi|urgent|foran|emergency|asap|abhi|turant",
                                  t, re.IGNORECASE) else "normal"

    out = {"blood_group": bg, "count": count, "location": None,
           "hospital": hospital, "urgency": urgency}
    out["missing_fields"] = [f for f in REQUIRED_FIELDS if not out.get(f)]
    return out
