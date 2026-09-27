"""STEP 7: guardrail checks used before/after every LLM call.
These are separate from llm.py's basic redaction so they can be tested and
extended independently (prompt-injection screening, scope refusal, etc)."""
import re

PATIENT_ID_PATTERN = re.compile(r"\bPT-\d{5}\b")

# Phrases commonly used to try to override an assistant's instructions when
# they appear INSIDE retrieved documents rather than from the actual user.
INJECTION_PATTERNS = [
    r"ignore (all|any|the) (previous|above|prior) instructions",
    r"disregard (all|any|the) (previous|above|prior) instructions",
    r"you are now",
    r"system\s*:\s*",
    r"reveal your (system prompt|instructions)",
    r"act as (an?|the) unrestricted",
]
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

OUT_OF_SCOPE_PATTERNS = [
    r"\bshould (i|we|the patient|they) (take|stop|increase|decrease)\b",
    r"\bwhat dose (should|do)\b",
    r"\bdiagnos(e|is)\b.*\bme\b",
    r"\bis it safe for (me|my|this patient) to\b",
]
_SCOPE_RE = re.compile("|".join(OUT_OF_SCOPE_PATTERNS), re.IGNORECASE)


def redact_patient_ids(text: str) -> str:
    """Replaces patient codes like PT-77302 with a placeholder."""
    return PATIENT_ID_PATTERN.sub("[REDACTED_PATIENT]", text or "")


def screen_for_injection(text: str) -> dict:
    """Flags text (typically a retrieved document) that looks like it's trying
    to instruct the assistant rather than inform it. Does not block anything
    by itself -- the caller decides what to do with the flag."""
    hit = _INJECTION_RE.search(text or "")
    return {"flagged": bool(hit), "matched": hit.group(0) if hit else None}


def check_out_of_scope(question: str) -> dict:
    """Flags questions asking for individual clinical/medical advice, which
    every agent's instructions say to refuse."""
    hit = _SCOPE_RE.search(question or "")
    return {"flagged": bool(hit), "matched": hit.group(0) if hit else None}


REFUSAL_MESSAGE = (
    "I can't provide individual clinical or dosing advice. This question is "
    "outside PharmaSense AI's scope -- please consult a qualified clinician."
)


def apply_input_guardrails(question: str):
    """Run before calling any agent. Returns (allowed: bool, message: str|None)."""
    scope = check_out_of_scope(question)
    if scope["flagged"]:
        return False, REFUSAL_MESSAGE
    return True, None