import chromadb
from sentence_transformers import SentenceTransformer
from data_ingestion import iter_document_batches
import time

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "acled_events"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE = 1000


def get_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return client, collection


def clean_metadata(metadata):
    """
    Chroma non accetta valori None nei metadata: li converte in stringa vuota
    o li rimuove, altrimenti l'insert fallisce.
    """
    return {k: (v if v is not None else "") for k, v in metadata.items()}


def index_csv(csv_path, batch_size=BATCH_SIZE, resume=True):
    client, collection = get_chroma_collection()
    model = SentenceTransformer(EMBEDDING_MODEL, device='cuda')

    already_indexed = set()
    if resume:
        # recupera gli id già presenti in Chroma, per non duplicare in caso di ripresa
        existing = collection.get(include=[])  # solo gli ids
        already_indexed = set(existing["ids"])
        print(f"Documenti già indicizzati trovati: {len(already_indexed)}")

    total_indexed = 0
    total_skipped = 0
    start = time.time()

    for batch in iter_document_batches(csv_path, batch_size=batch_size):
        # filtra i documenti già indicizzati (per la ripresa dopo un crash)
        if resume and already_indexed:
            batch = [d for d in batch if d["metadata"]["event_id"] not in already_indexed]
            total_skipped += batch_size - len(batch) if len(batch) < batch_size else 0

        if not batch:
            continue

        ids = [d["metadata"]["event_id"] for d in batch]
        texts = [d["text"] for d in batch]
        metadatas = [clean_metadata(d["metadata"]) for d in batch]

        embeddings = model.encode(texts, batch_size=256, show_progress_bar=False).tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        total_indexed += len(batch)
        elapsed = time.time() - start
        print(f"Indicizzati: {total_indexed} | tempo trascorso: {elapsed:.1f}s")

    print(f"\nCompletato. Totale documenti indicizzati: {total_indexed}, skippati (già presenti): {total_skipped}")
    return collection


if __name__ == "__main__":
    # test prima sul sample
    collection = index_csv("acled_data.csv", batch_size=200, resume=True)

    # query di prova per verificare che il retrieval funzioni
    model = SentenceTransformer(EMBEDDING_MODEL, device='cuda')
    query = "attacks on civilians in Algeria"
    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )

    print("\n--- Risultati query di test ---")
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        print(doc)
        print(meta)
        print()