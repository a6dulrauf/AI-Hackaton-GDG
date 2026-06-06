"""
LifeLine — Groq LLM helpers (SCAFFOLD).

This module will hold:
  - parse_request(text)  -> strict JSON {blood_group, count, location, hospital,
                            urgency, missing_fields} from mixed Urdu/Roman-Urdu/English
  - classify_reply(text) -> confirm | decline | eligibility-update
  - transcribe(audio)    -> text (Whisper, optional voice feature)

Guardrails (see CLAUDE.md):
  - Model: llama-3.3-70b-versatile for parse/classify; whisper-large-v3-turbo for voice.
  - Always ask for STRICT JSON with Urdu/Roman-Urdu/English few-shot examples.
  - ALWAYS provide a regex fallback so endpoints never 500 on a rate-limit.

Nothing here is implemented yet — only the client bootstrap so the import is safe.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads backend/.env if present
except ImportError:
    pass

GROQ_MODEL = "llama-3.3-70b-versatile"
WHISPER_MODEL = "whisper-large-v3-turbo"

_groq_client = None


def get_client():
    """Lazily create the Groq client. Returns None if the SDK/key is unavailable
    so the rest of the app can fall back to regex and never crash on import."""
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[llm] GROQ_API_KEY not set — LLM calls will use regex fallback.")
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=api_key)
    except Exception as e:  # noqa: BLE001
        print(f"[llm] Groq client unavailable ({e}) — will use regex fallback.")
        return None
    return _groq_client


# --- TODO (build in order, see docs/PLAN.md §7.2) -----------------------------
# def parse_request(text: str) -> dict: ...
# def classify_reply(text: str) -> str: ...
# def transcribe(audio_bytes: bytes) -> str: ...
