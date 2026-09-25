"""Rule-based first pass at whether an adverse event needs escalation, PLUS an
LLM explanation layer. Rules run first (deterministic, auditable); the LLM only
explains, it never overrides a rule-based escalation."""
from llm import call_llm

# A serious AE, or one judged related to the drug and severe, is escalated.
# This mirrors standard pharmacovigilance practice, simplified for this project.
def _rule_based_flag(seriousness: str, causality: str, severity: str):
    seriousness = (seriousness or "").lower()
    causality = (causality or "").lower()
    severity = (severity or "").lower()
    if seriousness == "serious":
        return True, "Reported as a serious event."
    if causality == "related" and severity == "severe":
        return True, "Severe event judged related to the study drug."
    return False, "Does not meet serious/severe-and-related escalation criteria."


def ae_severity_classifier_tool(event_term: str, severity: str, seriousness: str,
                                 causality: str, explain: bool = True):
    escalate, reason = _rule_based_flag(seriousness, causality, severity)
    result = {"escalate": escalate, "rule_reason": reason}

    if explain:
        prompt = (
            f"Adverse event: {event_term}. Severity: {severity}. "
            f"Seriousness: {seriousness}. Causality: {causality}.\n"
            f"A rule-based system decided escalate={escalate} because: {reason}\n"
            "In two sentences, explain this decision in plain language for a "
            "clinical ops manager. Do not change the decision."
        )
        result["explanation"] = call_llm(prompt, agent="ae_triage", max_tokens=150)
    return result