"""
WhatsApp messaging via the Meta WhatsApp Cloud API (official, free test tier).

Dev setup (no cost, no business verification):
  1. developers.facebook.com -> create an app -> add the "WhatsApp" product.
  2. Copy the test Phone Number ID + a temporary access token.
  3. Add your own phone as a verified test recipient.
  4. Put the values in backend/.env (see .env.example).

Functions never raise — they return (ok: bool, info) so the request flow that
calls them can degrade gracefully (the app still works without WhatsApp configured).
"""
import os

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GRAPH_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")


def _truthy(v) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


# --- The switch ---------------------------------------------------------------
# Real outreach during the wave flow is OPT-IN. It defaults OFF so a flaky/absent
# WhatsApp connection can never affect the demo — the wave engine stays fully
# mocked until someone flips this on (via WHATSAPP_ENABLED or POST /whatsapp/toggle).
_enabled = _truthy(os.getenv("WHATSAPP_ENABLED"))


def is_enabled() -> bool:
    return _enabled


def set_enabled(value: bool) -> bool:
    """Flip the runtime switch. Returns the new state."""
    global _enabled
    _enabled = bool(value)
    return _enabled


def is_live() -> bool:
    """Real messages go out only when the switch is ON *and* creds are present."""
    return is_enabled() and is_configured()


def _cfg():
    return {
        "token": os.getenv("WHATSAPP_TOKEN"),
        "phone_number_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
        # Optional: route ALL outbound to this one verified number (test-number phase).
        "redirect": os.getenv("WHATSAPP_DEMO_REDIRECT"),
    }


def is_configured() -> bool:
    c = _cfg()
    return bool(c["token"] and c["phone_number_id"])


def normalize_phone(p: str) -> str:
    """Meta wants the number with country code and digits only (no +, spaces, dashes)."""
    return "".join(ch for ch in str(p or "") if ch.isdigit())


def _post(payload: dict):
    c = _cfg()
    if not is_configured():
        return False, "WhatsApp not configured (set WHATSAPP_TOKEN + WHATSAPP_PHONE_NUMBER_ID)."
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{c['phone_number_id']}/messages"
    headers = {"Authorization": f"Bearer {c['token']}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code >= 400:
            return False, r.text
        return True, r.json()
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def _resolve_to(to: str) -> str:
    c = _cfg()
    return normalize_phone(c["redirect"] or to)


def send_text(to: str, body: str):
    """Send a free-form text. Valid only inside a 24h customer-service window or to
    test recipients — business-initiated first contact must use send_template()."""
    payload = {
        "messaging_product": "whatsapp",
        "to": _resolve_to(to),
        "type": "text",
        "text": {"body": body},
    }
    return _post(payload)


def send_template(to: str, template_name: str, lang: str = "en_US", body_params=None):
    """Send a pre-approved template (required for business-initiated outreach in prod).
    body_params: list of strings filling the template's {{1}}, {{2}}, ... placeholders."""
    components = []
    if body_params:
        components = [{
            "type": "body",
            "parameters": [{"type": "text", "text": str(p)} for p in body_params],
        }]
    payload = {
        "messaging_product": "whatsapp",
        "to": _resolve_to(to),
        "type": "template",
        "template": {"name": template_name, "language": {"code": lang}, "components": components},
    }
    return _post(payload)


def notify_donor(donor: dict, req: dict):
    """Best-effort wave outreach to one donor — used by the wave engine when the
    switch is live. Returns (ok, info); never raises. Routes via
    WHATSAPP_DEMO_REDIRECT when set, so test-number demos land on one verified phone."""
    name = donor.get("name", "")
    bg = req.get("blood_group", "")
    hosp = req.get("hospital", "")
    body = (f"\U0001FA78 LifeLine (Al-Khidmat): Assalam-o-Alaikum {name}, "
            f"{hosp} needs {bg} blood. You're an eligible match nearby. "
            f"Can you donate? Reply HAAN/YES to confirm or NAHI/NO. JazakAllah.")
    return send_text(donor.get("phone", ""), body)


def parse_inbound(body: dict):
    """Extract (from_number, text) from a Meta webhook payload, or (None, None).
    Used by the inbound webhook to turn a donor's WhatsApp reply into our flow."""
    try:
        change = body["entry"][0]["changes"][0]["value"]
        msg = change["messages"][0]
        return msg["from"], msg.get("text", {}).get("body", "")
    except (KeyError, IndexError, TypeError):
        return None, None
