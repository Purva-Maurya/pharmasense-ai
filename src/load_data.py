"""STEP 1a: load the 7 CSV files into a DuckDB database file."""
import duckdb
from config import RAW_DIR, DB_PATH

EXPECTED = {
    "compounds": 150, "clinical_trials": 110, "trial_sites": 375,
    "lab_results": 2000, "adverse_events": 500,
    "research_documents": 250, "agent_interaction_logs": 400,
}

csv_files = sorted(RAW_DIR.glob("*.csv"))
if not csv_files:
    raise SystemExit(f"No CSV files found in {RAW_DIR}. Copy the 7 CSVs there first.")

con = duckdb.connect(str(DB_PATH))
for f in csv_files:
    con.execute(f"""
        CREATE OR REPLACE TABLE {f.stem} AS
        SELECT * FROM read_csv_auto('{f.as_posix()}', header=true)
    """)
    n = con.execute(f"SELECT count(*) FROM {f.stem}").fetchone()[0]
    status = "OK" if EXPECTED.get(f.stem) == n else "CHECK ROW COUNT"
    print(f"{f.stem:25s} {n:5d} rows   {status}")
con.close()
print(f"\nDatabase written to: {DB_PATH}")