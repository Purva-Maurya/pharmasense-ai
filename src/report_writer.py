"""Report Writer: fans out to the Trial Data Analyst, Literature agent and
Compound Similarity tool for one compound, then merges everything into one report."""
from llm import call_llm
from sql_agent import answer_sql_question
from literature_agent import answer_from_docs
from tools.compound_similarity import compound_similarity_tool


def full_picture(compound_id: str, compound_name: str = None):
    name = compound_name or compound_id
    trials = answer_sql_question(
        f"List all clinical trials where compound_id equals '{compound_id}' "
        "(compound_id is an exact code like 'CMP-0012', not a name), with phase and status"
    )
    lit = answer_from_docs(f"What does our internal research say about {name} ({compound_id})?")
    similar = compound_similarity_tool(compound_id, k=5)

    merge_prompt = (
        f"Write a short briefing on compound {compound_id} ({name}) for a clinical ops manager, "
        f"using ONLY the sections below. Keep citations exactly as given.\n\n"
        f"TRIALS:\n{trials['answer']}\n\n"
        f"LITERATURE:\n{lit['answer']}\n\n"
        f"SIMILAR COMPOUNDS:\n{[s['compound_id'] for s in similar.get('similar', [])]}\n\n"
        "Structure: Trials, Safety/Literature, Related Compounds. 5-8 sentences total."
    )
    report = call_llm(merge_prompt, agent="report_writer", max_tokens=1500)
    if not report or not report.strip():
        report = "(No report text was generated. See trials/literature/similar sections below.)"
    return {"report": report, "trials": trials, "literature": lit, "similar": similar}


if __name__ == "__main__":
    import sys
    cid = sys.argv[1] if len(sys.argv) > 1 else "CMP-0001"
    out = full_picture(cid)
    print("TRIALS SECTION:", out["trials"]["answer"])
    print("\nLITERATURE SECTION:", out["literature"]["answer"])
    print("\n--- MERGED REPORT ---")
    print(out["report"])