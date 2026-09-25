"""Central settings: every other file imports paths and names from here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # the pharmasense/ folder
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "pharmasense.duckdb"
CHROMA_DIR = ROOT / "chroma_db"
LOG_DIR = ROOT / "logs"
LLM_LOG_PATH = LOG_DIR / "llm_calls.jsonl"

COLLECTION_NAME = "research_docs"
EMBED_MODEL = "all-MiniLM-L6-v2"

LOG_DIR.mkdir(exist_ok=True)