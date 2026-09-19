"""Loads the 8 Zepto policy documents, embeds each (one chunk per document,
given their short length) with all-MiniLM-L6-v2, and stores them in a
persistent ChromaDB collection using cosine similarity.
"""
import os

import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
COLLECTION_NAME = "zepto_policies"

_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
_client = chromadb.PersistentClient(path=CHROMA_PATH)


def _ingest(collection) -> None:
    doc_files = sorted(f for f in os.listdir(DOCS_DIR) if f.endswith(".txt"))
    documents, ids, metadatas = [], [], []

    for fname in doc_files:
        with open(os.path.join(DOCS_DIR, fname), encoding="utf-8") as f:
            text = f.read().strip()
        doc_id = os.path.splitext(fname)[0]  # "doc_01.txt" -> "doc_01"
        documents.append(text)
        ids.append(doc_id)
        metadatas.append({"source": fname})

    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    print(f"Ingested {len(documents)} documents into ChromaDB collection '{COLLECTION_NAME}'")


def get_collection():
    """Returns the ChromaDB collection, ingesting the corpus on first use."""
    collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
    if collection.count() == 0:
        _ingest(collection)
    return collection


if __name__ == "__main__":
    col = get_collection()
    print(f"Collection '{COLLECTION_NAME}' has {col.count()} chunks")

    # quick sanity check
    results = col.query(query_texts=["What happens if my order arrives damaged?"], n_results=3)
    for doc_id, doc_text, distance in zip(
        results["ids"][0], results["documents"][0], results["distances"][0]
    ):
        print(f"\n[{doc_id}] (distance={distance:.4f})\n{doc_text[:150]}...")
