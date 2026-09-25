"""STEP 3a: chunk, embed and index research_documents.full_text into ChromaDB."""
import duckdb, chromadb
from chromadb.utils import embedding_functions
from config import DB_PATH, CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL


def chunk_text(text, max_words=300, overlap=50):
    """Word-based chunker (~300 words is roughly 400 tokens).
    Short documents (like yours, ~37 words) stay as a single chunk."""
    words = str(text).split()
    if len(words) <= max_words:
        return [" ".join(words)]
    chunks, step = [], max_words - overlap
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start:start + max_words]))
        if start + max_words >= len(words):
            break
    return chunks


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    docs = con.execute("""
        SELECT d.*, c.target_protein, c.therapeutic_area AS area
        FROM research_documents d JOIN compounds c ON d.compound_id = c.compound_id
    """).df()
    con.close()

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)

    # start clean so re-running never leaves stale or duplicate entries
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    col = client.create_collection(
        COLLECTION_NAME, embedding_function=ef, metadata={"hnsw:space": "cosine"}
    )

    ids, texts, metas = [], [], []
    for r in docs.itertuples():
        for i, ch in enumerate(chunk_text(r.full_text)):
            ids.append(f"{r.doc_id}::{i}")
            texts.append(f"{r.title}\nTarget: {r.target_protein}. Area: {r.area}.\n{ch}")     # title holds the compound name, so embed it too
            metas.append({
                "doc_id": r.doc_id,
                "chunk_idx": i,
                "compound_id": r.compound_id,
                # Chroma rejects None/NaN, so use an empty string for missing trial_id
                "trial_id": r.trial_id if isinstance(r.trial_id, str) else "",
                "doc_type": r.doc_type,
                "title": r.title,
                "date": str(r.date)[:10],
                "tags": str(r.tags),
            })

    col.upsert(ids=ids, documents=texts, metadatas=metas)
    print(f"Indexed {col.count()} chunks from {len(docs)} documents into {CHROMA_DIR}")


if __name__ == "__main__":
    main()