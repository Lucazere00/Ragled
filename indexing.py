import chromadb
from sentence_transformers import SentenceTransformer
from data_ingestion import iter_document_batches
import time

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "acled_events"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE = 500


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
    model = SentenceTransformer(EMBEDDING_MODEL)

    already_indexed = set()
    if resume:
        # recupera gli id già presenti in Chroma, per non duplicare in caso di ripresa
        existing = collection.get(include=[])
        already_indexed = set(existing["ids"])

        print(
            f"Documenti già indicizzati trovati: "
            f"{len(already_indexed)}"
        )

    total_indexed = 0
    total_skipped = 0
    start = time.time()

    for batch in iter_document_batches(
        csv_path,
        batch_size=batch_size
    ):

        # filtra i documenti già indicizzati
        if resume and already_indexed:
            batch = [
                d for d in batch
                if d["metadata"]["event_id"] not in already_indexed
            ]

            total_skipped += (
                batch_size - len(batch)
                if len(batch) < batch_size
                else 0
            )

        if not batch:
            continue

        ids = [
            d["metadata"]["event_id"]
            for d in batch
        ]

        texts = [
            d["text"]
            for d in batch
        ]

        metadatas = [
            clean_metadata(d["metadata"])
            for d in batch
        ]

        embeddings = model.encode(
            texts,
            batch_size=256,
            show_progress_bar=False
        ).tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        total_indexed += len(batch)

        elapsed = time.time() - start

        print(
            f"Indicizzati: {total_indexed} | "
            f"tempo trascorso: {elapsed:.1f}s"
        )

    print(
        f"\nCompletato. "
        f"Totale documenti indicizzati: {total_indexed}, "
        f"skippati (già presenti): {total_skipped}"
    )

    return collection


# ============================================================
# CONTROLLO VECTOR DB
# ============================================================

def check_vector_db(collection):

    print("\n")
    print("=" * 60)
    print("CONTROLLO VECTOR DB")
    print("=" * 60)

    count = collection.count()

    print(f"Documenti presenti nel ChromaDB: {count}")

    if count == 0:
        print("ERRORE: il ChromaDB è vuoto.")
        return

    # Recuperiamo 5 documenti per controllare il contenuto
    result = collection.get(
        limit=5,
        include=[
            "documents",
            "metadatas",
            "embeddings"
        ]
    )

    print(
        f"Documenti recuperati per il controllo: "
        f"{len(result['ids'])}"
    )

    print("\n--- ESEMPI DOCUMENTI ---")

    for i in range(len(result["ids"])):

        print(f"\nDOCUMENTO {i + 1}")

        print("ID:")
        print(result["ids"][i])

        print("\nTESTO:")
        print(result["documents"][i][:500])

        print("\nMETADATA:")
        print(result["metadatas"][i])

        if result["embeddings"] is not None:
            print(
                "\nDimensione embedding:",
                len(result["embeddings"][i])
            )

        print("-" * 60)

    # Controllo ID
    unique_ids = len(set(result["ids"]))

    print("\n--- CONTROLLO ID ---")
    print("ID controllati:", len(result["ids"]))
    print("ID unici:", unique_ids)

    if unique_ids == len(result["ids"]):
        print("OK: nessun duplicato tra gli ID controllati.")
    else:
        print("ATTENZIONE: sono stati trovati duplicati!")

    print("=" * 60)


# ============================================================
# TEST RETRIEVAL
# ============================================================

def test_retrieval(collection):

    print("\n")
    print("=" * 60)
    print("TEST RETRIEVAL")
    print("=" * 60)

    model = SentenceTransformer(
        EMBEDDING_MODEL
    )

    test_queries = [
        "attacks on civilians in Algeria",
        "violent conflict involving armed groups",
        "protests and demonstrations"
    ]

    for query in test_queries:

        print("\n")
        print("-" * 60)
        print("QUERY:")
        print(query)
        print("-" * 60)

        query_embedding = model.encode(
            [query]
        ).tolist()

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=3
        )

        for i, (doc, meta, distance) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ):

            print(f"\nRISULTATO {i + 1}")

            print("Distance:")
            print(distance)

            print("\nDocument:")
            print(doc[:500])

            print("\nMetadata:")
            print(meta)

    print("\n")
    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    DATASET = "acled_data.csv"

    print("=" * 60)
    print("AVVIO INDEXING")
    print("=" * 60)

    print("Dataset:", DATASET)
    print("Batch size:", 200)
    print("Resume:", True)

    # --------------------------------------------------------
    # CONTROLLO PRIMA DELL'INDEXING
    # --------------------------------------------------------

    client, collection = get_chroma_collection()

    count_before = collection.count()

    print(
        f"\nDocumenti presenti PRIMA dell'indexing: "
        f"{count_before}"
    )

    # --------------------------------------------------------
    # INDEXING
    # --------------------------------------------------------

    collection = index_csv(
        DATASET,
        batch_size=200,
        resume=True
    )

    # --------------------------------------------------------
    # CONTROLLO DOPO L'INDEXING
    # --------------------------------------------------------

    count_after = collection.count()

    print("\n")
    print("=" * 60)
    print("CONTROLLO DOPO INDEXING")
    print("=" * 60)

    print("Documenti prima:", count_before)
    print("Documenti dopo:", count_after)

    print(
        "Nuovi documenti aggiunti:",
        count_after - count_before
    )

    if count_after >= count_before:
        print("OK: il numero di documenti è coerente.")
    else:
        print("ATTENZIONE: il numero di documenti è diminuito!")

    # --------------------------------------------------------
    # CONTROLLO CONTENUTO VECTOR DB
    # --------------------------------------------------------

    check_vector_db(collection)

    # --------------------------------------------------------
    # TEST RETRIEVAL
    # --------------------------------------------------------

    test_retrieval(collection)