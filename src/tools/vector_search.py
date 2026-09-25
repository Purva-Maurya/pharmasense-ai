"""STEP 3b: the retrieval tool agents call. Returns ranked, citable passages."""
import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL

_collection = None


def _get_collection():
    global _collection
    if _collection is None:      # load the embedding model only once
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_collection(COLLECTION_NAME, embedding_function=ef)
    return _collection


def vector_search_tool(query: str, k: int = 5, doc_type: str = None, compound_id: str = None):
    """Semantic search over research documents.
    Optional filters: doc_type (e.g. 'Regulatory Briefing'), compound_id (e.g. 'CMP-0055')."""
    filters = []
    if doc_type:
        filters.append({"doc_type": doc_type})
    if compound_id:
        filters.append({"compound_id": compound_id})
    where = None if not filters else (filters[0] if len(filters) == 1 else {"$and": filters})

    res = _get_collection().query(query_texts=[query], n_results=k, where=where)
    return [
        {
            "rank": i + 1,
            "citation": f"[{m['doc_id']}]",
            "doc_id": m["doc_id"],
            "title": m["title"],
            "doc_type": m["doc_type"],
            "compound_id": m["compound_id"],
            "trial_id": m["trial_id"],
            "date": m["date"],
            "score": round(1 - dist, 3),      # cosine similarity (higher = closer)
            "passage": doc,
        }
        for i, (doc, m, dist) in enumerate(
            zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
        )
    ]