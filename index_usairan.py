from data_ingestion_usairan import iter_usairan_batches
from indexing import BATCH_SIZE, get_chroma_collection, index_dataset


DATASET = "usa-iran.csv"


def main():
    print("=" * 60)
    print("AVVIO INDEXING USA-IRAN")
    print("=" * 60)

    print("Dataset:", DATASET)
    print("Batch size:", BATCH_SIZE)
    print("Resume:", True)

    client, collection = get_chroma_collection()
    count_before = collection.count()

    print(
        f"\nDocumenti presenti PRIMA dell'indexing: "
        f"{count_before}"
    )

    collection = index_dataset(
        DATASET,
        iter_usairan_batches,
        batch_size=BATCH_SIZE,
        resume=True,
    )

    count_after = collection.count()

    print("\n")
    print("=" * 60)
    print("CONTROLLO DOPO INDEXING USA-IRAN")
    print("=" * 60)
    print("Documenti prima:", count_before)
    print("Documenti dopo:", count_after)
    print("Nuovi documenti aggiunti:", count_after - count_before)


if __name__ == "__main__":
    main()
