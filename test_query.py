import chromadb
from sentence_transformers import SentenceTransformer


CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "acled_events"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ============================================================
# CONNESSIONE
# ============================================================

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

collection = client.get_collection(
    name=COLLECTION_NAME
)

model = SentenceTransformer(
    EMBEDDING_MODEL
)


print("=" * 70)
print("TEST VECTOR DB ACLED")
print("=" * 70)

print("\nDocumenti presenti nel ChromaDB:", collection.count())


# ============================================================
# FUNZIONE QUERY SEMANTICA
# ============================================================

def semantic_query(query, n_results=5):

    print("\n")
    print("=" * 70)
    print("QUERY:", query)
    print("=" * 70)

    query_embedding = model.encode(
        [query]
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results
    )

    for i, (doc, meta, distance) in enumerate(
        zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ):

        print(f"\n--- RISULTATO {i + 1} ---")

        print("ID:", results["ids"][0][i])

        print("DISTANCE:", round(distance, 4))

        print("\nDOCUMENTO:")
        print(doc)

        print("\nMETADATA:")
        print(meta)

        print("-" * 70)


# ============================================================
# TEST SEMANTICI
# ============================================================

semantic_queries = [

    "attacks on civilians in Algeria",

    "violent conflict involving armed groups",

    "protests and demonstrations in Algeria",

    "violence against civilians in Morocco",

    "armed groups attacking villages",

    "political violence in Northern Africa",

    "military forces involved in violent events",

    "events involving civilian targeting",

    "conflict between armed groups",

    "violent events with many fatalities",

]

print("\n\n")
print("#" * 70)
print("# TEST QUERY SEMANTICHE")
print("#" * 70)

for query in semantic_queries:
    semantic_query(query, n_results=5)


# ============================================================
# TEST QUERY NUMERICHE / STRUTTURATE
# ============================================================

print("\n\n")
print("#" * 70)
print("# TEST QUERY NUMERICHE / STRUTTURATE")
print("#" * 70)


# ------------------------------------------------------------
# 1. Eventi con più di 10 vittime
# ------------------------------------------------------------

print("\n")
print("QUERY: fatalities > 10")

results = collection.get(
    where={
        "fatalities": {
            "$gt": 10
        }
    },
    limit=10,
    include=[
        "documents",
        "metadatas"
    ]
)

print("Risultati:", len(results["ids"]))

for i in range(len(results["ids"])):

    meta = results["metadatas"][i]

    print(
        f"\n{i + 1}. "
        f"ID={results['ids'][i]} | "
        f"Paese={meta.get('country')} | "
        f"Data={meta.get('event_date')} | "
        f"Fatalities={meta.get('fatalities')}"
    )


# ------------------------------------------------------------
# 2. Eventi con almeno 50 vittime
# ------------------------------------------------------------

print("\n")
print("QUERY: fatalities >= 50")

results = collection.get(
    where={
        "fatalities": {
            "$gte": 50
        }
    },
    limit=10,
    include=[
        "documents",
        "metadatas"
    ]
)

print("Risultati:", len(results["ids"]))

for i in range(len(results["ids"])):

    meta = results["metadatas"][i]

    print(
        f"\n{i + 1}. "
        f"ID={results['ids'][i]} | "
        f"Paese={meta.get('country')} | "
        f"Data={meta.get('event_date')} | "
        f"Fatalities={meta.get('fatalities')}"
    )


# ------------------------------------------------------------
# 3. Eventi in Algeria
# ------------------------------------------------------------

print("\n")
print("QUERY: country = Algeria")

results = collection.get(
    where={
        "country": "Algeria"
    },
    limit=10,
    include=[
        "documents",
        "metadatas"
    ]
)

print("Risultati:", len(results["ids"]))

for i in range(len(results["ids"])):

    meta = results["metadatas"][i]

    print(
        f"\n{i + 1}. "
        f"ID={results['ids'][i]} | "
        f"Data={meta.get('event_date')} | "
        f"Tipo={meta.get('event_type')} | "
        f"Fatalities={meta.get('fatalities')}"
    )


# ------------------------------------------------------------
# 4. Eventi del 1997
# ------------------------------------------------------------

print("\n")
print("QUERY: year = 1997")

results = collection.get(
    where={
        "year": 1997
    },
    limit=10,
    include=[
        "documents",
        "metadatas"
    ]
)

print("Risultati:", len(results["ids"]))

for i in range(len(results["ids"])):

    meta = results["metadatas"][i]

    print(
        f"\n{i + 1}. "
        f"ID={results['ids'][i]} | "
        f"Paese={meta.get('country')} | "
        f"Data={meta.get('event_date')} | "
        f"Fatalities={meta.get('fatalities')}"
    )


# ------------------------------------------------------------
# 5. Algeria + fatalities > 10
# ------------------------------------------------------------

print("\n")
print("QUERY: Algeria AND fatalities > 10")

results = collection.get(
    where={
        "$and": [
            {
                "country": "Algeria"
            },
            {
                "fatalities": {
                    "$gt": 10
                }
            }
        ]
    },
    limit=10,
    include=[
        "documents",
        "metadatas"
    ]
)

print("Risultati:", len(results["ids"]))

for i in range(len(results["ids"])):

    meta = results["metadatas"][i]

    print(
        f"\n{i + 1}. "
        f"ID={results['ids'][i]} | "
        f"Data={meta.get('event_date')} | "
        f"Fatalities={meta.get('fatalities')} | "
        f"Tipo={meta.get('event_type')}"
    )


# ------------------------------------------------------------
# 6. Algeria + anno 1997
# ------------------------------------------------------------

print("\n")
print("QUERY: Algeria AND year = 1997")

results = collection.get(
    where={
        "$and": [
            {
                "country": "Algeria"
            },
            {
                "year": 1997
            }
        ]
    },
    limit=10,
    include=[
        "documents",
        "metadatas"
    ]
)

print("Risultati:", len(results["ids"]))

for i in range(len(results["ids"])):

    meta = results["metadatas"][i]

    print(
        f"\n{i + 1}. "
        f"ID={results['ids'][i]} | "
        f"Data={meta.get('event_date')} | "
        f"Fatalities={meta.get('fatalities')} | "
        f"Tipo={meta.get('event_type')}"
    )


# ============================================================
# CONTROLLO EMBEDDING
# ============================================================

print("\n\n")
print("#" * 70)
print("# CONTROLLO EMBEDDING")
print("#" * 70)

embedding_test = collection.get(
    limit=5,
    include=[
        "embeddings"
    ]
)

if embedding_test["embeddings"] is not None:

    for i, embedding in enumerate(
        embedding_test["embeddings"]
    ):

        print(
            f"Embedding {i + 1}: "
            f"dimensione = {len(embedding)}"
        )

else:

    print("ERRORE: embeddings non disponibili.")


# ============================================================
# CONTROLLO METADATA
# ============================================================

print("\n\n")
print("#" * 70)
print("# CONTROLLO METADATA")
print("#" * 70)

metadata_test = collection.get(
    limit=5,
    include=[
        "documents",
        "metadatas"
    ]
)

required_fields = [
    "event_id",
    "event_date",
    "year",
    "country",
    "event_type",
    "sub_event_type",
    "fatalities",
    "latitude",
    "longitude"
]

for i, meta in enumerate(
    metadata_test["metadatas"]
):

    missing = [
        field
        for field in required_fields
        if field not in meta
    ]

    if missing:

        print(
            f"Documento {i + 1}: "
            f"MANCANO {missing}"
        )

    else:

        print(
            f"Documento {i + 1}: OK"
        )


print("\n")
print("=" * 70)
print("TUTTI I TEST COMPLETATI")
print("=" * 70)

print("Documenti presenti nel ChromaDB:", collection.count())

print("\nPrimi 10 ID:")
ids = collection.get(
    limit=10,
    include=[]
)

print(ids["ids"])