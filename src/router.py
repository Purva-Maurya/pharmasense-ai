"""Router/Planner: classifies a question into one of the 5 specialist agents
and calls the right one. This is the orchestration layer from Step 6."""
import json
from llm import call_llm
from guardrails import apply_input_guardrails
from sql_agent import answer_sql_question
from literature_agent import answer_from_docs
from ae_triage_agent import triage_event
from report_writer import full_picture

ROUTES = ["trial_data_analyst", "literature_research", "adverse_event_triage",
          "compound_full_picture", "unclear"]

ROUTER_SYSTEM = (
    "You are a router for a pharma R&D assistant. Classify the user's question into "
    "exactly one route and extract any IDs mentioned. Reply with JSON only: "
    '{"route": "...", "event_id": "...", "compound_id": "...", "compound_name": "..."} '
    "Use null for fields that do not apply. Routes: trial_data_analyst (structured/SQL "
    "questions about trials, enrollment, sites), literature_research (questions about "
    "research findings, literature, documents), adverse_event_triage (a specific AE report "
    "to triage, needs an event_id like AE-00001), compound_full_picture (asks for 'the full "
    "picture' or a combined summary of one compound), unclear (anything else)."
)


def route(question: str):
    allowed, refusal = apply_input_guardrails(question)
    if not allowed:
        return {"route": "refused", "answer": refusal}

    raw = call_llm(question, agent="router", system=ROUTER_SYSTEM,
                    json_mode=True, max_tokens=200)
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        plan = {"route": "unclear"}

    r = plan.get("route")
    if r == "trial_data_analyst":
        return {"route": r, **answer_sql_question(question)}
    if r == "literature_research":
        return {"route": r, **answer_from_docs(question)}
    if r == "adverse_event_triage" and plan.get("event_id"):
        return {"route": r, **triage_event(plan["event_id"])}
    if r == "compound_full_picture" and plan.get("compound_id"):
        return {"route": r, **full_picture(plan["compound_id"], plan.get("compound_name"))}

    return {"route": "unclear", "answer": (
        "I couldn't confidently route this question. Try asking about a specific trial, "
        "compound, or include an event ID (e.g. AE-00001) for AE triage."
    )}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Which Phase II oncology trials are below 60% enrollment right now?"
    out = route(q)
    print("ROUTE:", out["route"])
    print(out.get("answer") or out.get("report") or out.get("verdict"))