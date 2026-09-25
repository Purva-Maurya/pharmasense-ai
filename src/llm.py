"""STEP 2: the ONE governed entry point for every LLM call (Gemini).
Every agent calls call_llm(). Guardrails, retries and cost/latency logging live here."""
import os, time, json, uuid, re, datetime as dt
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, InternalServerError, APIConnectionError
from config import ROOT, LLM_LOG_PATH

load_dotenv(ROOT / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found. Check that .env is in the project root.")

# Gemini exposes an OpenAI-compatible endpoint, so we reuse the openai package.
_client = OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# Free tier covers the Flash models. Check aistudio.google.com for current model names.
DEFAULT_MODEL = os.getenv("PHARMASENSE_MODEL", "gemini-2.0-flash")

# USD per 1M tokens. Fill in from Google's pricing page if you move to a paid tier.
PRICING = {
    "gemini-2.0-flash": {"in": 0.0, "out": 0.0},
    "gemini-1.5-flash": {"in": 0.0, "out": 0.0},
}

BASE_SYSTEM = (
    "You are a pharma R&D assistant. Answer only from the provided context or tool "
    "results. If the context is insufficient, say so. Never give patient-specific "
    "medical advice. Cite sources by ID (e.g. DOC-00012, TRL-0032)."
)

DEFAULT_GUARDRAILS = {
    "max_input_chars": 20000,
    "redact_patterns": [r"PT-\d{5}"],   # masks patient codes before text leaves your machine
}


def _apply_guardrails(text, g):
    if len(text) > g["max_input_chars"]:
        raise ValueError("Input exceeds max_input_chars guardrail")
    for pat in g["redact_patterns"]:
        text = re.sub(pat, "[REDACTED_PATIENT]", text)
    return text


def call_llm(prompt, model=None, guardrails=None, system=None,
             max_tokens=1024, agent="unknown", temperature=0.0,
             json_mode=False, max_retries=4):
    """
    prompt      : the user message
    agent       : name of the calling agent (recorded in the log)
    json_mode   : True forces valid JSON output (used later by the AE triage agent)
    max_retries : retries on rate-limit errors (429) with increasing waits
    """
    model = model or DEFAULT_MODEL
    g = {**DEFAULT_GUARDRAILS, **(guardrails or {})}
    prompt = _apply_guardrails(prompt, g)

    call_id, t0, status = str(uuid.uuid4()), time.time(), "ok"
    tin = tout = 0

    kwargs = dict(
        model=model, max_tokens=max_tokens, temperature=temperature,
        messages=[
            {"role": "system", "content": system or BASE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        for attempt in range(max_retries + 1):
            try:
                resp = _client.chat.completions.create(**kwargs)
                break
            except (RateLimitError, InternalServerError, APIConnectionError):
                if attempt == max_retries:
                    raise
                time.sleep([5, 15, 30, 60][min(attempt, 3)])   # waits 5s, 15s, 30s, 60s   # waits 5s, 15s, 30s, 60s
        if resp.usage:
            tin, tout = resp.usage.prompt_tokens, resp.usage.completion_tokens
        return resp.choices[0].message.content
    except Exception as e:
        status = f"error: {type(e).__name__}"
        raise
    finally:
        p = PRICING.get(model, {"in": 0.0, "out": 0.0})
        rec = {
            "call_id": call_id,
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "agent": agent, "model": model,
            "latency_ms": int((time.time() - t0) * 1000),
            "input_tokens": tin, "output_tokens": tout,
            "cost_usd": (tin * p["in"] + tout * p["out"]) / 1e6,
            "status": status,
        }
        with open(LLM_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")