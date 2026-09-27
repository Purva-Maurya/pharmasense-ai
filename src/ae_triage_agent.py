"""Adverse Event Triage agent: looks up an AE by event_id, classifies it, and
escalates automatically when the classifier says so."""
from tools.sql_query import sql_query_tool
from tools.ae_severity_classifier import ae_severity_classifier_tool
from tools.escalation_notifier import escalation_notifier_tool


def triage_event(event_id: str):
    row = sql_query_tool(
        "SELECT * FROM adverse_events WHERE event_id = ?", [event_id]
    )["rows"]
    if not row:
        return {"error": f"No adverse event found with id {event_id}"}
    e = row[0]

    verdict = ae_severity_classifier_tool(
        event_term=e["adverse_event_term"], severity=e["severity"],
        seriousness=e["seriousness"], causality=e["causality_assessment"],
    )

    escalation = None
    if verdict["escalate"]:
        escalation = escalation_notifier_tool(
            event_id=e["event_id"], trial_id=e["trial_id"],
            reason=verdict["rule_reason"], severity=e["severity"],
        )

    return {"event": e, "verdict": verdict, "escalation": escalation}


if __name__ == "__main__":
    import sys
    eid = sys.argv[1] if len(sys.argv) > 1 else "AE-00001"
    out = triage_event(eid)
    print(out)