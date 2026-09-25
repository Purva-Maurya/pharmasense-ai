"""STEP 3c: first end-to-end RAG answer (retrieve -> ground -> cite)."""
import sys
from llm import call_llm
from tools.vector_search import vector_search_tool


def answer_from_docs(question: str, k: int = 5):
    hits = vector_search_tool(question, k=k)
    context = "\n\n".join(
        f"{h['citation']} ({h['doc_type']}, {h['date']}): {h['passage']}" for h in hits
    )
    prompt = (
        f"Context documents:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using ONLY the context above. Cite every claim with its document ID "
        "in square brackets, like [DOC-00012]. If the context does not contain the "
        "answer, say so plainly."
    )
    try:
        answer = call_llm(prompt, agent="literature_agent")
    except Exception as e:
        answer = f"[LLM call failed: {type(e).__name__}. The retrieval below still worked.]"
    return {"answer": answer, "sources": hits}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What has our internal research said about JAK2 inhibitors and cardiotoxicity?"
    out = answer_from_docs(q)
    print("QUESTION:", q, "\n")
    print(out["answer"])
    print("\nSOURCES RETRIEVED:")
    for h in out["sources"]:
        print(f"  {h['citation']}  score={h['score']}  {h['title']}")