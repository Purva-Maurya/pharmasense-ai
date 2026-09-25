"""Simulated escalation tool: writes a log line (and could call a real webhook
later). Every escalation call is auditable in logs/escalations.jsonl."""
import json, uuid, datetime as dt
from config import LOG_DIR

ESCALATION_LOG = LOG_DIR / "escalations.jsonl"


def escalation_notifier_tool(event_id: str, trial_id: str, reason: str, severity: str = "unknown"):
    rec = {
        "escalation_id": str(uuid.uuid4()),
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "event_id": event_id, "trial_id": trial_id,
        "reason": reason, "severity": severity,
        "notified": "simulated: would call webhook/email here",
    }
    with open(ESCALATION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return {"status": "escalated", "escalation_id": rec["escalation_id"], "logged_to": str(ESCALATION_LOG)}