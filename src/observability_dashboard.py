"""STEP 7: reads logs/llm_calls.jsonl and logs/escalations.jsonl and prints a
plain-text observability summary (model usage, cost, latency, tool/agent
breakdown, error rate, escalations). Also writes an HTML version you can
open in a browser."""
import json
from collections import Counter, defaultdict
from config import LLM_LOG_PATH, LOG_DIR

ESCALATION_LOG = LOG_DIR / "escalations.jsonl"


def _read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def build_summary():
    calls = _read_jsonl(LLM_LOG_PATH)
    escalations = _read_jsonl(ESCALATION_LOG)

    by_agent = defaultdict(lambda: {"n": 0, "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "latency": []})
    errors = 0
    for c in calls:
        a = by_agent[c["agent"]]
        a["n"] += 1
        a["tokens_in"] += c.get("input_tokens", 0)
        a["tokens_out"] += c.get("output_tokens", 0)
        a["cost"] += c.get("cost_usd", 0.0)
        a["latency"].append(c.get("latency_ms", 0))
        if c.get("status") != "ok":
            errors += 1

    per_agent_rows = []
    for agent, d in sorted(by_agent.items()):
        avg_latency = round(sum(d["latency"]) / len(d["latency"])) if d["latency"] else 0
        per_agent_rows.append({
            "agent": agent, "calls": d["n"], "tokens_in": d["tokens_in"],
            "tokens_out": d["tokens_out"], "cost_usd": round(d["cost"], 5),
            "avg_latency_ms": avg_latency,
        })

    return {
        "total_calls": len(calls),
        "total_errors": errors,
        "error_rate_pct": round(100 * errors / len(calls), 1) if calls else 0.0,
        "total_cost_usd": round(sum(c.get("cost_usd", 0.0) for c in calls), 5),
        "models_used": dict(Counter(c["model"] for c in calls)),
        "per_agent": per_agent_rows,
        "total_escalations": len(escalations),
        "escalations": escalations[-10:],
    }


def print_text(summary):
    print("=== PharmaSense AI - Observability Summary ===")
    print(f"Total LLM calls   : {summary['total_calls']}")
    print(f"Errors            : {summary['total_errors']} ({summary['error_rate_pct']}%)")
    print(f"Total cost (USD)  : ${summary['total_cost_usd']}")
    print(f"Models used       : {summary['models_used']}")
    print(f"Total escalations : {summary['total_escalations']}")
    print("\nPer-agent breakdown:")
    for r in summary["per_agent"]:
        print(f"  {r['agent']:<20s} calls={r['calls']:<4d} "
              f"tokens_in={r['tokens_in']:<7d} tokens_out={r['tokens_out']:<7d} "
              f"cost=${r['cost_usd']:<8} avg_latency={r['avg_latency_ms']}ms")


def write_html(summary, path):
    rows = "".join(
        f"<tr><td>{r['agent']}</td><td>{r['calls']}</td><td>{r['tokens_in']}</td>"
        f"<td>{r['tokens_out']}</td><td>${r['cost_usd']}</td><td>{r['avg_latency_ms']}ms</td></tr>"
        for r in summary["per_agent"]
    )
    esc_rows = "".join(
        f"<tr><td>{e['ts']}</td><td>{e['event_id']}</td><td>{e['trial_id']}</td><td>{e['reason']}</td></tr>"
        for e in summary["escalations"]
    ) or "<tr><td colspan=4>No escalations logged yet.</td></tr>"

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>PharmaSense AI - Observability</title>
<style>
body {{ font-family: -apple-system, Arial, sans-serif; margin: 2rem; color: #1a1a1a; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #f4f4f4; }}
.stat {{ display: inline-block; margin-right: 2rem; font-size: 1.1rem; }}
.stat b {{ display: block; font-size: 1.6rem; }}
</style></head><body>
<h1>PharmaSense AI - Observability Dashboard</h1>
<div class="stat"><b>{summary['total_calls']}</b>Total LLM calls</div>
<div class="stat"><b>{summary['error_rate_pct']}%</b>Error rate</div>
<div class="stat"><b>${summary['total_cost_usd']}</b>Total cost</div>
<div class="stat"><b>{summary['total_escalations']}</b>Escalations</div>
<h2>Per-agent breakdown</h2>
<table><tr><th>Agent</th><th>Calls</th><th>Tokens in</th><th>Tokens out</th><th>Cost</th><th>Avg latency</th></tr>
{rows}</table>
<h2>Recent escalations</h2>
<table><tr><th>Time</th><th>Event</th><th>Trial</th><th>Reason</th></tr>
{esc_rows}</table>
</body></html>"""
    path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    from config import ROOT
    summary = build_summary()
    print_text(summary)
    out_path = ROOT / "eval" / "observability_dashboard.html"
    write_html(summary, out_path)
    print(f"\nHTML dashboard written to {out_path}")