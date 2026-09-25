"""STEP 1b: verify that foreign keys point to real rows (problems should be 0)."""
import duckdb
from config import DB_PATH

con = duckdb.connect(str(DB_PATH), read_only=True)

checks = {
    "trials -> compounds":
        "SELECT count(*) FROM clinical_trials t LEFT JOIN compounds c ON t.compound_id=c.compound_id WHERE c.compound_id IS NULL",
    "sites -> trials":
        "SELECT count(*) FROM trial_sites s LEFT JOIN clinical_trials t ON s.trial_id=t.trial_id WHERE t.trial_id IS NULL",
    "lab_results -> compounds":
        "SELECT count(*) FROM lab_results l LEFT JOIN compounds c ON l.compound_id=c.compound_id WHERE c.compound_id IS NULL",
    "adverse_events -> trials":
        "SELECT count(*) FROM adverse_events a LEFT JOIN clinical_trials t ON a.trial_id=t.trial_id WHERE t.trial_id IS NULL",
    "adverse_events -> sites":
        "SELECT count(*) FROM adverse_events a LEFT JOIN trial_sites s ON a.site_id=s.site_id WHERE s.site_id IS NULL",
    "documents -> compounds":
        "SELECT count(*) FROM research_documents d LEFT JOIN compounds c ON d.compound_id=c.compound_id WHERE c.compound_id IS NULL",
    "documents -> trials (non-null only)":
        "SELECT count(*) FROM research_documents d LEFT JOIN clinical_trials t ON d.trial_id=t.trial_id WHERE d.trial_id IS NOT NULL AND t.trial_id IS NULL",
    "AE site belongs to AE trial":
        "SELECT count(*) FROM adverse_events a JOIN trial_sites s ON a.site_id=s.site_id WHERE a.trial_id <> s.trial_id",
}

all_ok = True
for name, sql in checks.items():
    bad = con.execute(sql).fetchone()[0]
    all_ok &= (bad == 0)
    print(f"{name:40s} problems = {bad:3d}   {'PASS' if bad == 0 else 'FAIL'}")
con.close()
print("\nAll checks passed." if all_ok else "\nSome checks failed. Investigate before continuing.")