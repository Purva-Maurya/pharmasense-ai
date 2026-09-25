# PharmaSense AI

A multi-agent GenAI assistant for a fictional pharma R&D and clinical operations
team. Natural-language questions are routed to specialist agents, grounded in
synthetic company data (structured tables + a document corpus), with
autonomous adverse-event triage and escalation.

Built as a portfolio project following the *PharmaSense AI — Portfolio Project
Template* (House of EdTech).

## Architecture

| Layer | This project's implementation |
|---|---|
| Application | CLI scripts per agent (`src/*.py`) — see Step 8 for a chat UI |
| Orchestration | `src/router.py` — classifies intent, fans out, merges results |
| Agents & Tools | 5 specialist agents in `src/`, tools in `src/tools/` |
| Retrieval | ChromaDB + `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Data | DuckDB (`pharmasense.duckdb`), loaded from 7 CSVs |
| LLM | Google Gemini (`gemini-2.5-flash`), via a single `call_llm()` wrapper |

The LLM layer is intentionally swappable: every agent calls `src/llm.py`'s
`call_llm()`, so switching providers (tested with Mistral, Groq, and Gemini
during development) means editing one file, not the agents.

## Agents

| Agent | File | Instructions doc |
|---|---|---|
| Trial Data Analyst | `src/sql_agent.py` | `agents/instructions/trial_data_analyst.md` |
| Literature & Document Research | `src/literature_agent.py` | `agents/instructions/literature_research.md` |
| Adverse Event Triage | `src/ae_triage_agent.py` | `agents/instructions/adverse_event_triage.md` |
| Compound Similarity | `src/tools/compound_similarity.py` | `agents/instructions/compound_similarity.md` |
| Report Writer | `src/report_writer.py` | `agents/instructions/report_writer.md` |

Tool specs (name, description, JSON parameters) for every tool: `agents/tool_specs/tool_specs.json`.

## Setup

```powershell
git clone https://github.com/Purva-Maurya/pharmasense-ai.git
cd pharmasense-ai
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your API key:
```
GEMINI_API_KEY=your_key_here
PHARMASENSE_MODEL=gemini-2.5-flash
```

## Build the data & retrieval layers

```powershell
python src/load_data.py        # loads the 7 CSVs into DuckDB
python src/check_integrity.py  # verifies foreign keys (expect 8/8 PASS)
python src/create_views.py     # creates v_trial_enrollment
python src/build_index.py      # chunks + embeds research_documents into ChromaDB
python src/eval_retrieval.py   # measures retrieval quality (no API key needed)
```

## Run an agent

```powershell
python src/literature_agent.py "What has our internal research said about JAK2 inhibitors and cardiotoxicity?"
python src/sql_agent.py "Which Phase II oncology trials are below 60% enrollment?"
python src/ae_triage_agent.py AE-00003
python src/report_writer.py CMP-0012
python src/router.py "What compounds are similar to VLX-1000?"
```

## Data notes (things I found while building this)

- `research_documents.full_text` averages ~37 words, so most documents embed
  as a single chunk rather than the 300–500 token chunks the source template
  assumes. The chunker still supports longer documents.
- `clinical_trials.actual_enrollment` and the sum of `trial_sites.enrollment_count`
  per trial don't reconcile for most trials in this dataset. I treat
  `actual_enrollment` as the source of truth and query `v_trial_enrollment`
  accordingly — the SQL agent's system prompt states this explicitly.
- Semantic search on compound codenames (e.g. "SNF-1107") is weaker than
  search on plain-language topics, since embedding models don't strongly
  encode arbitrary alphanumeric codes. Metadata enrichment (adding
  `target_protein` / `therapeutic_area` into the embedded text) partially
  addresses this — see `src/build_index.py`.

## Retrieval evaluation

<!-- TODO: paste your numbers here after running `python src/eval_retrieval.py`
     Test 1  title -> same doc, Recall@3      : __ / 250 = __%
     Test 2  compound name -> its docs, Hit@5  : __ / __ = __%
     Test 3  doc_type filter                   : PASS/FAIL -->

## Guardrails, evaluation & observability (Step 7)

<!-- TODO once Step 7 is built:
- Guardrails checklist (patient-ID redaction, prompt-injection screening,
  out-of-scope refusal rules)
- Golden-set evaluation report (pass rate, avg latency/cost per agent)
- Link to or summary of logs/llm_calls.jsonl and logs/escalations.jsonl -->

## Demo (Step 8)

<!-- TODO once Step 8 is built:
- How to run the chat UI / API
- Link to a recorded walkthrough -->

## Project structure

```
pharmasense/
├── agents/
│   ├── instructions/      # one .md per specialist agent
│   └── tool_specs/        # tool_specs.json (name, description, params)
├── data/raw/               # 7 source CSVs
├── logs/                   # llm_calls.jsonl, escalations.jsonl (generated)
├── src/
│   ├── config.py            # central paths & settings
│   ├── load_data.py         # Step 1: CSV -> DuckDB
│   ├── check_integrity.py   # Step 1: FK checks
│   ├── create_views.py      # Step 1: v_trial_enrollment
│   ├── llm.py                # Step 2: governed LLM entry point
│   ├── build_index.py       # Step 3: chunk + embed -> ChromaDB
│   ├── literature_agent.py  # Step 3/4: Literature & Document Research
│   ├── eval_retrieval.py    # Step 3: retrieval quality tests
│   ├── sql_agent.py         # Step 4/5: Trial Data Analyst
│   ├── ae_triage_agent.py   # Step 4/5: Adverse Event Triage
│   ├── report_writer.py     # Step 4/5: Report Writer (fan-out + merge)
│   ├── router.py             # Step 6: orchestration/routing
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