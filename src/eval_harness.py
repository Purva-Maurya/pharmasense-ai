"""STEP 7: run the golden set end-to-end, score each answer, and write a report.
Faithfulness/relevance are LLM-judged (0-2); latency/cost come straight from
the same logs/llm_calls.jsonl that call_llm() already writes."""
import json, time, sys
from pathlib import Path
from config import ROOT, LLM_LOG_PATH
from llm import call_llm
from guardrails import apply_input_guardrails
from sql_agent import answer_sql_question
from literature_agent import answer_from_docs
from ae_triage_agent import triage_event
from tools.compound_similarity import compound_similarity_tool
from router import route

GOLDEN_SET_PATH = ROOT / "eval" / "golden_set.json"
REPORT_PATH = ROOT / "eval" / "eval_report.json"

JUDGE_SYSTEM = (
    "You score an AI assistant's answer to a factual question. "
    'Reply with JSON only: {"faithfulness": 0|1|2, "relevance": 0|1|2, "reason": "..."} '
    "faithfulness: 2 = every claim is supported by the given context/result, "
    "1 = mostly supported with a minor unsupported detail, 0 = contains an "
    "unsupported or fabricated claim. relevance: 2 = directly answers the "
    "question, 1 = partially answers it, 0 = does not address it."
)


def _judge(question, answer, context):
    try:
        raw = call_llm(
            f"Question: {question}\nContext given to the assistant: {context}\n"
            f"Assistant's answer: {answer}",
            agent="eval_judge", system=JUDGE_SYSTEM, json_mode=True, max_tokens=500,
        )
    except Exception as e:
        return {"faithfulness": None, "relevance": None, "reason": f"judge call failed: {type(e).__name__}"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"faithfulness": None, "relevance": None, "reason": "judge output not valid JSON"}

def _run_one(item):
    t0 = time.time()
    result = {"id": item["id"], "type": item["type"]}
    try:
        if item["type"] == "sql":
            out = answer_sql_question(item["question"])
            result.update(answer=out["answer"], context=str(out["result"]["rows"][:10]))
        elif item["type"] == "rag":
            out = answer_from_docs(item["question"])
            result.update(answer=out["answer"], context=str([h["passage"] for h in out["sources"]]))
        elif item["type"] == "ae_triage":
            out = triage_event(item["event_id"])
            if "error" in out:
                result.update(answer=out["error"], passed=item.get("expects_error", False))
            else:
                result.update(answer=str(out["verdict"]), passed=True)
        elif item["type"] == "compound_similarity":
            out = compound_similarity_tool(item["compound_id"])
            if "error" in out:
                result.update(answer=out["error"], passed=item.get("expects_error", False))
            else:
                result.update(answer=str(out), passed=True)
        elif item["type"] == "refusal":
            allowed, msg = apply_input_guardrails(item["question"])
            result.update(answer=msg or "(not refused)")
            result["passed"] = (not allowed) == bool(item.get("expects_refusal"))
        elif item["type"] == "router":
            out = route(item["question"])
            result.update(answer=f"routed to {out['route']}",
                           passed=out["route"] == item.get("expects_route"))
        else:
            result.update(answer="(unknown type)", passed=False)
    except Exception as e:
        result.update(answer=f"ERROR: {type(e).__name__}: {e}", passed=False, error=True)

    result["latency_s"] = round(time.time() - t0, 2)

    if item["type"] in ("sql", "rag") and "error" not in result:
        judged = _judge(item.get("question", ""), result["answer"], result.get("context", ""))
        result.update(judged)
        if item.get("expects_contains"):
            result["keyword_hit"] = any(k.lower() in result["answer"].lower() for k in item["expects_contains"])
    return result


def main():
    golden = json.loads(GOLDEN_SET_PATH.read_text())
    results = []
    for i, item in enumerate(golden, 1):
        print(f"[{i}/{len(golden)}] {item['id']} ({item['type']})...")
        results.append(_run_one(item))

    n = len(results)
    n_error = sum(1 for r in results if r.get("error"))
    n_pass = sum(1 for r in results if r.get("passed") is True)
    scored = [r for r in results if r.get("faithfulness") is not None]
    avg_faith = round(sum(r["faithfulness"] for r in scored) / len(scored), 2) if scored else None
    avg_rel = round(sum(r["relevance"] for r in scored) / len(scored), 2) if scored else None
    avg_latency = round(sum(r["latency_s"] for r in results) / n, 2)

    summary = {
        "total_questions": n, "errors": n_error, "explicit_pass_checks_passed": n_pass,
        "avg_faithfulness_0to2": avg_faith, "avg_relevance_0to2": avg_rel,
        "avg_latency_s": avg_latency,
    }
    REPORT_PATH.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print("\n" + json.dumps(summary, indent=2))
    print(f"\nFull report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()