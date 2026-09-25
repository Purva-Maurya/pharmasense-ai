"""Trial Data Analyst agent: answers structured questions with sql_query_tool,
then has the LLM explain the result in plain language."""
from llm import call_llm
from tools.sql_query import sql_query_tool
import re

def _clean_sql(text: str):
    """Strip markdown code fences (```sql ... ``` or ``` ... ```) and any
    trailing prose the LLM adds after the query."""
    text = text.strip()
    # remove a fenced block if present, keep only what's inside it
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        text = m.group(1)
    text = text.strip().rstrip(";").strip()
    return text

SCHEMA_SUMMARY = """
Tables (all read-only):
- compounds(compound_id PK, compound_name, chemical_class, therapeutic_area, target_protein,
  mechanism_of_action, discovery_phase, molecular_weight_da, solubility_mg_ml, toxicity_score,
  lead_scientist, synthesis_date)
- clinical_trials(trial_id PK, compound_id FK, trial_phase, therapeutic_area, status,
  target_enrollment, actual_enrollment, start_date, actual_end_date, ...)
- v_trial_enrollment(trial_id, compound_id, trial_phase, therapeutic_area, status,
  target_enrollment, actual_enrollment, enrollment_pct)  -- use this view for enrollment %
- trial_sites(site_id PK, trial_id FK, enrollment_count, principal_investigator, ...)
- lab_results(result_id PK, compound_id FK, experiment_type, ...)
- adverse_events(event_id PK, trial_id FK, site_id FK, severity, seriousness,
  causality_assessment, adverse_event_term, ...)

NOTE: clinical_trials.actual_enrollment is the source of truth for enrollment questions;
per-site totals in trial_sites do not reliably sum to it in this dataset.
"""


def answer_sql_question(question: str):
    sql_prompt = (
        f"{SCHEMA_SUMMARY}\n"
        f"Write ONE read-only DuckDB SELECT query (no semicolon) that answers:\n"
        f"\"{question}\"\nReply with ONLY the SQL query, nothing else."
    )
    sql = call_llm(sql_prompt, agent="sql_agent", temperature=0.0).strip()
    sql =_clean_sql(sql)
    print("DEBUG SQL:", repr(sql))   # remove once this is working reliably

    result = sql_query_tool(sql)

    explain_prompt = (
        f"Question: {question}\nSQL used: {sql}\n"
        f"Result rows (first 10): {result['rows'][:10]}\n"
        "Answer the question in 2-4 sentences using only this result. "
        "Mention the SQL result count where relevant."
    )
    answer = call_llm(explain_prompt, agent="sql_agent")
    return {"answer": answer, "sql": sql, "result": result}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Which Phase II oncology trials are below 60% enrollment right now?"
    out = answer_sql_question(q)
    print("SQL:", out["sql"])
    print("\nANSWER:", out["answer"])