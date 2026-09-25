"""Finds compounds numerically similar to a given one (same target, or nearby
molecular weight / solubility / toxicity), for questions like
"what else looks like DKU-1042?"."""
import duckdb
from config import DB_PATH

_FEATURES = ["molecular_weight_da", "solubility_mg_ml", "toxicity_score"]


def compound_similarity_tool(compound_id: str, k: int = 5):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        target = con.execute(
            "SELECT * FROM compounds WHERE compound_id = ?", [compound_id]
        ).df()
        if target.empty:
            return {"error": f"No compound with id {compound_id}"}
        t = target.iloc[0]

        others = con.execute(
            "SELECT * FROM compounds WHERE compound_id != ?", [compound_id]
        ).df()
    finally:
        con.close()

    # min-max normalize each numeric feature across all compounds, then compute
    # a simple Euclidean distance; same target_protein counts as a strong bonus.
    ranges = {f: (others[f].min(), others[f].max()) for f in _FEATURES}

    def dist(row):
        d = 0.0
        for f in _FEATURES:
            lo, hi = ranges[f]
            span = (hi - lo) or 1.0
            d += ((row[f] - t[f]) / span) ** 2
        d = d ** 0.5
        if row["target_protein"] != t["target_protein"]:
            d += 0.5   # penalty for a different mechanism/target
        return d

    others["distance"] = others.apply(dist, axis=1)
    top = others.nsmallest(k, "distance")
    return {
        "reference": {"compound_id": t.compound_id, "compound_name": t.compound_name,
                       "target_protein": t.target_protein},
        "similar": [
            {"compound_id": r.compound_id, "compound_name": r.compound_name,
             "target_protein": r.target_protein, "therapeutic_area": r.therapeutic_area,
             "distance": round(r.distance, 3)}
            for r in top.itertuples()
        ],
    }