from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, concat, lit, when, coalesce, date_format, to_date
)

def get_spark_session():
    return (
        SparkSession.builder
        .appName("ACLED_Ingestion")
        .config("spark.driver.memory", "4g")
        .getOrCreate()
    )


def load_and_clean(spark, csv_path):
    df = spark.read.csv(csv_path, header=True, inferSchema=True)

    df = df.withColumn("event_date", to_date(col("event_date"), "yyyy-MM-dd"))
    df = df.withColumn("fatalities", col("fatalities").cast("int"))
    df = df.withColumn("year", col("year").cast("int"))

    text_cols_to_fill = ["location", "admin1", "admin2", "actor1", "actor2",
                          "country", "event_type", "sub_event_type",
                          "disorder_type", "notes"]
    for c in text_cols_to_fill:
        df = df.withColumn(c, coalesce(col(c), lit("")))

    return df


def build_documents_df(df):
    """
    doc_text contiene SOLO ciò che serve alla ricerca semantica:
    event type, sub-event type, attori, luogo/paese, notes.
    fatalities/lat/long/year restano solo come metadata strutturati.
    """
    actor_part = when(
        col("actor2") != "",
        concat(lit(" vs "), col("actor2"))
    ).otherwise(lit(""))

    doc_text = concat(
        lit("On "), date_format(col("event_date"), "yyyy-MM-dd"),
        lit(" in "), col("location"), lit(", "), col("admin1"), lit(", "), col("country"),
        lit(", a "), col("event_type"), lit(" ("), col("sub_event_type"), lit(") event occurred."),
        lit(" Actors involved: "), col("actor1"), actor_part, lit("."),
        lit(" Notes: "), col("notes")
    )

    return df.withColumn("doc_text", doc_text)


def iter_document_batches(csv_path, batch_size=2000):
    """
    Generatore: NON accumula mai tutti i documenti in RAM.
    Produce un batch alla volta, pronto per embedding + inserimento
    nel vector DB. Lo Spark dataframe pulito viene restituito a parte
    per la parte structured/analytics (query dirette in Spark/SQL).
    """
    spark = get_spark_session()
    df = load_and_clean(spark, csv_path)
    df = build_documents_df(df)

    metadata_cols = [
        "event_id_cnty", "event_date", "year", "disorder_type", "event_type",
        "sub_event_type", "actor1", "actor2", "country", "region", "admin1",
        "civilian_targeting", "fatalities", "latitude", "longitude"
    ]
    select_cols = ["doc_text"] + metadata_cols

    rows_iter = df.select(*select_cols).toLocalIterator()

    batch = []
    for row in rows_iter:
        row_dict = row.asDict()
        text = row_dict.pop("doc_text")
        metadata = {
            "event_id": row_dict["event_id_cnty"],
            "event_date": (
                str(row_dict["event_date"])
                if row_dict["event_date"] is not None
                else None
            ),  
            "year": row_dict["year"],
            "disorder_type": row_dict["disorder_type"],
            "event_type": row_dict["event_type"],
            "sub_event_type": row_dict["sub_event_type"],
            "actor1": row_dict["actor1"],
            "actor2": row_dict["actor2"] if row_dict["actor2"] != "" else None,
            "country": row_dict["country"],
            "region": row_dict["region"],
            "admin1": row_dict["admin1"],
            "civilian_targeting": row_dict["civilian_targeting"],
            "fatalities": row_dict["fatalities"],
            "latitude": row_dict["latitude"],
            "longitude": row_dict["longitude"],
        }
        batch.append({"text": text, "metadata": metadata})

        if len(batch) >= batch_size:
            yield batch
            batch = []

    if batch:
        yield batch

    spark.stop()


def get_structured_df(csv_path):
    """
    Per la parte analitica/aggregata: ritorna lo Spark dataframe pulito,
    da interrogare con Spark SQL (df.groupBy, df.filter, ecc.),
    separato dalla pipeline di embedding.
    """
    spark = get_spark_session()
    df = load_and_clean(spark, csv_path)
    return df, spark


if __name__ == "__main__":
    import time

    start = time.time()
    total_docs = 0
    for batch in iter_document_batches("acled_data.csv", batch_size=200):
        total_docs += len(batch)
        if total_docs == len(batch):  # primo batch, stampa un esempio
            print("--- Esempio documento 0 ---")
            print(batch[0]["text"])
            print(batch[0]["metadata"])

    elapsed = time.time() - start
    print(f"\nTempo totale: {elapsed:.2f}s, documenti processati: {total_docs}")