"""STEP 1c/1d: create the enrollment view and sanity-check enrollment numbers."""
import duckdb
from config import DB_PATH

con = duckdb.connect(str(DB_PATH))

con.execute("""
CREATE OR REPLACE VIEW v_trial_enrollment AS
SELECT trial_id, compound_id, trial_phase, therapeutic_area, status,
       target_enrollment, actual_enrollment,
       ROUND(100.0 * actual_enrollment / target_enrollment, 1) AS enrollment_pct
FROM clinical_trials
""")

print("Phase II oncology trials below 60% enrollment:")
print(con.execute("""
    SELECT * FROM v_trial_enrollment
    WHERE trial_phase = 'Phase II' AND therapeutic_area = 'Oncology' AND enrollment_pct < 60
    ORDER BY enrollment_pct
""").df().to_string(index=False))

# Step 1d: do site-level enrollments add up to the trial-level number?
mismatch = con.execute("""
    SELECT count(*) AS n_trials,
           sum(CASE WHEN t.actual_enrollment <> COALESCE(s.site_total, 0) THEN 1 ELSE 0 END) AS n_mismatch
    FROM clinical_trials t
    LEFT JOIN (SELECT trial_id, SUM(enrollment_count) AS site_total
               FROM trial_sites GROUP BY trial_id) s ON t.trial_id = s.trial_id
""").fetchone()
print(f"\nSite-total vs trial-total enrollment: {mismatch[1]} of {mismatch[0]} trials differ.")
con.close()