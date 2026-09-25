"""STEP 3d: measure retrieval quality (no LLM or API key needed)."""
import duckdb
from config import DB_PATH
from tools.vector_search import vector_search_tool

con = duckdb.connect(str(DB_PATH), read_only=True)
docs = con.execute("SELECT doc_id, title FROM research_documents").df()
comp = con.execute("""
    SELECT DISTINCT c.compound_id, c.compound_name
    FROM compounds c JOIN research_documents d ON c.compound_id = d.compound_id
""").df()
con.close()

# Test 1: use each document's title as the query; the document should rank in the top 3.
hits = 0
for r in docs.itertuples():
    top = vector_search_tool(r.title, k=3)
    hits += any(h["doc_id"] == r.doc_id for h in top)
print(f"Test 1  title -> same doc, Recall@3      : {hits}/{len(docs)} = {hits/len(docs):.1%}")

# Test 2: ask about a compound by name; at least one of the top 5 should be about that compound.
hits = 0
for r in comp.itertuples():
    top = vector_search_tool(f"{r.compound_name} research findings", k=5)
    hits += any(h["compound_id"] == r.compound_id for h in top)
print(f"Test 2  compound name -> its docs, Hit@5 : {hits}/{len(comp)} = {hits/len(comp):.1%}")

# Test 3: metadata filter works (only regulatory briefings should come back).
top = vector_search_tool("safety data supporting submission", k=5, doc_type="Regulatory Briefing")
ok = all(h["doc_type"] == "Regulatory Briefing" for h in top)
print(f"Test 3  doc_type filter returns only that type: {'PASS' if ok else 'FAIL'}")