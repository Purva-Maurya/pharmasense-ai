# PharmaSense AI

A multi-agent GenAI assistant for a fictional pharma R&D and clinical operations
team. Natural-language questions are routed to specialist agents, grounded in
synthetic company data (structured tables + a document corpus), with
autonomous adverse-event triage and escalation.

Built as a portfolio project following the *PharmaSense AI — Portfolio Project
Template* (House of EdTech).

**Status: all 8 steps complete and verified with real API calls** (data layer,
governed LLM wrapper, RAG, 5 agents + router, guardrails, golden-set
evaluation, observability, and a Streamlit chat demo).

## Architecture

| Layer | This project's implementation |
|---|---|
| Application | `src/app.py` — Streamlit chat UI in front of the router |
| Orchestration | `src/router.py` — classifies intent, fans out, merges results |
| Agents & Tools | 5 specialist agents in `src/`, tools in `src/tools/` |
| Retrieval | ChromaDB + `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Data | DuckDB (`pharmasense.duckdb`), loaded from 7 CSVs |
| LLM | Groq (`openai/gpt-oss-20b`), via a single `call_llm()` wrapper |
| Guardrails | `src/guardrails.py` — redaction, injection screening, scope refusal |
| Evaluation | `eval/golden_set.json` + `src/eval_harness.py` (LLM-judged) |
| Observability | `src/observability_dashboard.py` — cost/latency/error dashboard |

The LLM layer is intentionally swappable: every agent calls `src/llm.py`'s
`call_llm()`, so switching providers means editing one file, not the agents.
During development this project ran, in order, on **Mistral, Gemini, and
Groq** — see "Lessons learned" below for why.

## Agents

| Agent | File | Instructions doc |
|---|---|---|
| Trial Data Analyst | `src/sql_agent.py` | `agents/instructions/trial_data_analyst.md` |
| Literature & Document Research | `src/literature_agent.py` | `agents/instructions/literature_research.md` |
| Adverse Event Triage | `src/ae_triage_agent.py` | `agents/instructions/adverse_event_triage.md` |
| Compound Similarity | `src/tools/compound_similarity.py` | `agents/instructions/compound_similarity.md` |
| Report Writer | `src/report_writer.py` | `agents/instructions/report_writer.md` |

Tool specs (name, description, JSON parameters) for every tool:
`agents/tool_specs/tool_specs.json`.

## Setup

```powershell
git clone https://github.com/yourusername/pharmasense-ai.git
cd pharmasense-ai
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Groq key (free, no card required,
from console.groq.com):
```
GROQ_API_KEY=your_key_here
PHARMASENSE_MODEL=openai/gpt-oss-20b
```

## Build the data & retrieval layers

```powershell
python src/load_data.py        # loads the 7 CSVs into DuckDB
python src/check_integrity.py  # verifies foreign keys (8/8 PASS)
python src/create_views.py     # creates v_trial_enrollment
python src/build_index.py      # chunks + embeds research_documents into ChromaDB (250 chunks)
python src/eval_retrieval.py   # measures retrieval quality (no API key needed)
```

## Run an agent (CLI)

```powershell
python src/literature_agent.py "What has our internal research said about JAK2 inhibitors and cardiotoxicity?"
python src/sql_agent.py "Which Phase II oncology trials are below 60% enrollment?"
python src/ae_triage_agent.py AE-00003
python src/report_writer.py CMP-0012
python src/router.py "What compounds are similar to VLX-1000?"
```

## Run the chat demo

```powershell
streamlit run src/app.py
```
Opens at `http://localhost:8501`. One chat box, routed automatically to all
5 specialist agents. See `eval/demo_script.md` for a timed 2–3 minute
walkthrough hitting every agent.

## Evaluation & observability

```powershell
python src/eval_harness.py            # runs the 24-question golden set
python src/observability_dashboard.py # aggregates logs into a report + HTML
```

<!-- eval-numbers-start -->
**Retrieval evaluation** (`eval_retrieval.py`, no LLM involved):
- Test 1 — title → same document, Recall@3: **_70/250 = 28.0%_**
- Test 2 — compound name → its docs, Hit@5: **_54/123 = 43.9%_**
- Test 3 — `doc_type` metadata filter: **_PASS_**

**Golden-set evaluation** (`eval_harness.py`, 24 questions across SQL, RAG,
AE triage, compound similarity, refusal, and routing):
- Errors: **0 / 24**
- Explicit pass/fail checks passed: **10 / 10**
- Average faithfulness: **1.92 / 2.0**
- Average relevance: **2.0 / 2.0**
- Average latency: **4.87s** per question
<!-- eval-numbers-end -->

Full per-question results (including judge reasoning) are in
`eval/eval_report.json` after running the harness.

## Guardrails checklist

See `eval/guardrails_checklist.md` for the full mapping of guardrail →
enforcing code → test evidence. Summary:

1. Patient identifiers (`PT-#####`) redacted before reaching the LLM
2. Retrieved documents screened for prompt-injection phrases
3. Individual clinical/dosing questions refused before routing
4. SQL tool is read-only, single-statement, keyword-blocklisted
5. AE escalation is a deterministic rule, not an LLM decision — the LLM only
   explains the verdict afterward, never overrides it
6. Every LLM call (success or failure) is logged with model, tokens,
   latency, and cost

## Data notes (things I found while building this)

- `research_documents.full_text` averages ~37 words, so most documents embed
  as a single chunk rather than the 300–500 token chunks the source template
  assumes. The chunker still supports longer documents.
- `clinical_trials.actual_enrollment` and the sum of `trial_sites.enrollment_count`
  per trial don't reconcile for most trials in this dataset (105 of 110
  differ). I treat `actual_enrollment` as the source of truth and the SQL
  agent's schema prompt states this explicitly.
- Semantic search on compound codenames (e.g. "SNF-1107") is weaker than
  search on plain-language topics. Metadata enrichment (adding
  `target_protein` / `therapeutic_area` into the embedded text) partially
  addresses this — see `src/build_index.py`.
- `clinical_trials.status` values are case-sensitive exact strings
  (`'Terminated'`, not `'terminated'`) — the text-to-SQL agent initially
  guessed the wrong case and silently returned zero rows. The schema prompt
  in `sql_agent.py` now states the exact values.

## Lessons learned

Building the LLM layer surfaced several real, non-obvious failure modes —
documented here rather than glossed over, since they're representative of
what building production LLM systems actually involves:

- **Free-tier providers are unreliable enough to design around, not just a
  one-off annoyance.** This project ran, in order, on Mistral (hit a
  persistent 429), Gemini (hit a 404 on a deprecated model, then a 20/day
  quota wall on its replacement, then a 503 overload), and finally Groq. The
  `call_llm()` wrapper made every switch a one-file change — this is the
  entire reason Step 2 designs the LLM layer as a swappable single entry
  point rather than calling a provider SDK directly from each agent.
- **Reasoning models truncate silently under low `max_tokens`.** `gpt-oss-20b`
  spends part of its token budget on hidden reasoning before writing visible
  output. Three separate calls (SQL explanation, report merge, AE
  explanation) returned empty strings until their `max_tokens` was raised —
  not an error, just silent data loss. Every LLM call in this project now
  has an explicit `max_tokens` and an empty-response fallback.
- **LLM-generated SQL guesses plausible-but-wrong literals.** The text-to-SQL
  agent twice picked a schema detail that "sounded right" but wasn't: once
  querying `compound_name` with an ID value, and once using `'terminated'`
  instead of the dataset's actual `'Terminated'`. Both were fixed by making
  the schema prompt state exact column semantics and exact string values —
  a real argument for constrained/validated SQL generation in production.
- **JSON-mode isn't 100% reliable.** The LLM-judge step in `eval_harness.py`
  occasionally failed Groq's own JSON-mode validation (a 400 error, not
  malformed text). The harness now catches this and records the question as
  unscored rather than crashing the entire 24-question run — a single flaky
  call shouldn't lose the rest of an evaluation.
- **Honest "I don't know" is a feature, not a gap.** The Literature agent
  correctly reported that internal research doesn't specifically cover
  cardiotoxicity for JAK2 inhibitors, rather than inventing a plausible
  finding — this is the core value proposition of grounding answers in
  retrieval rather than model memory, borne out in the eval's 2.0/2.0
  average relevance score.

## Project structure

```
pharmasense/
├── agents/
│   ├── instructions/      # one .md per specialist agent
│   └── tool_specs/        # tool_specs.json (name, description, params)
├── data/raw/               # 7 source CSVs
├── eval/
│   ├── golden_set.json           # 24-question eval set
│   ├── eval_report.json          # generated by eval_harness.py
│   ├── observability_dashboard.html  # generated by observability_dashboard.py
│   ├── guardrails_checklist.md
│   └── demo_script.md
├── logs/                   # llm_calls.jsonl, escalations.jsonl (generated)
├── src/
│   ├── config.py             # central paths & settings
│   ├── load_data.py          # Step 1: CSV -> DuckDB
│   ├── check_integrity.py    # Step 1: FK checks
│   ├── create_views.py       # Step 1: v_trial_enrollment
│   ├── llm.py                 # Step 2: governed LLM entry point (Groq)
│   ├── build_index.py        # Step 3: chunk + embed -> ChromaDB
│   ├── literature_agent.py   # Step 3/4: Literature & Document Research
│   ├── eval_retrieval.py     # Step 3: retrieval quality tests
│   ├── sql_agent.py          # Step 4/5: Trial Data Analyst
│   ├── ae_triage_agent.py    # Step 4/5: Adverse Event Triage
│   ├── report_writer.py      # Step 4/5: Report Writer (fan-out + merge)
│   ├── router.py              # Step 6: orchestration/routing
│   ├── guardrails.py         # Step 7: input/output guardrail checks
│   ├── eval_harness.py       # Step 7: golden-set evaluation
│   ├── observability_dashboard.py  # Step 7: cost/latency/error dashboard
│   ├── app.py                 # Step 8: Streamlit chat demo
│   └── tools/                 # Step 5: individual tool implementations
├── requirements.txt
└── .env.example
```

## Stack rationale

This follows the reference template's "any-platform" track (DuckDB + Chroma +
sentence-transformers + a swappable LLM wrapper) instead of the Dataiku +
Snowflake reference stack, since the underlying pattern — five distinct
layers (application, orchestration, agents/tools, retrieval, data) — is what
matters, not the specific vendor.