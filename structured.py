from pyspark.sql import SparkSession
from pyspark.sql import functions as F


_SPARK_SESSION = None


def get_spark_session():
    """
    Create or return the singleton SparkSession used for structured queries.

    Keeping one session alive avoids the startup cost when this module is used
    repeatedly from an interactive pipeline.
    """
    global _SPARK_SESSION

    if _SPARK_SESSION is None:
        _SPARK_SESSION = (
            SparkSession.builder
            .appName("ACLED_Structured")
            .config("spark.driver.memory", "4g")
            .getOrCreate()
        )

    return _SPARK_SESSION


def load_structured_df(spark, parquet_path="data/acled_processed.parquet"):
    """
    Load the processed ACLED dataset from Parquet.

    This function intentionally reads only the processed Parquet dataset, never
    the original CSV.
    """
    return spark.read.parquet(parquet_path)


def apply_filters(df, router_output):
    """
    Apply optional filters extracted by the router to a Spark DataFrame.

    Country matching is case-insensitive and exact. Event type matching is
    case-insensitive and partial to tolerate small naming differences between
    router output and ACLED values.
    """
    filtered_df = df

    if router_output.country is not None:
        country = router_output.country.strip().lower()
        filtered_df = filtered_df.filter(F.lower(F.col("country")) == country)

    if router_output.event_type is not None:
        event_type = router_output.event_type.strip().lower()
        event_type_col = F.lower(F.col("event_type"))
        event_type_filter = event_type_col.contains(event_type)

        if event_type.endswith("s"):
            event_type_filter = event_type_filter | event_type_col.contains(
                event_type[:-1]
            )

        filtered_df = filtered_df.filter(event_type_filter)

    if router_output.disorder_type is not None:
        disorder_type = router_output.disorder_type.strip().lower()
        disorder_type_col = F.lower(F.col("disorder_type"))
        disorder_type_filter = disorder_type_col.contains(disorder_type)

        if disorder_type.endswith("s"):
            disorder_type_filter = disorder_type_filter | disorder_type_col.contains(
                disorder_type[:-1]
            )

        filtered_df = filtered_df.filter(disorder_type_filter)

    if router_output.sub_event_type is not None:
        sub_event_type = router_output.sub_event_type.strip().lower()
        sub_event_type_col = F.lower(F.col("sub_event_type"))
        sub_event_type_filter = sub_event_type_col.contains(sub_event_type)

        if sub_event_type.endswith("s"):
            sub_event_type_filter = sub_event_type_filter | sub_event_type_col.contains(
                sub_event_type[:-1]
            )

        filtered_df = filtered_df.filter(sub_event_type_filter)

    if router_output.date_from is not None:
        filtered_df = filtered_df.filter(
            F.col("event_date") >= F.to_date(F.lit(router_output.date_from))
        )

    if router_output.date_to is not None:
        filtered_df = filtered_df.filter(
            F.col("event_date") <= F.to_date(F.lit(router_output.date_to))
        )

    return filtered_df


def _format_breakdown(title, rows, label_field, count_field="count"):
    """Format grouped Spark rows into a readable bullet list."""
    lines = [f"{title}:"]

    if not rows:
        lines.append("- None")
        return lines

    for row in rows:
        label = row[label_field] if row[label_field] not in (None, "") else "Unknown"
        lines.append(f"- {label}: {row[count_field]}")

    return lines


def run_structured_query(router_output) -> str:
    """
    Run aggregate ACLED analytics for a routed structured query.

    Returns a human-readable string. The caller decides whether to print it.
    """
    spark = get_spark_session()
    df = load_structured_df(spark)
    filtered_df = apply_filters(df, router_output)

    total_events = filtered_df.count()
    if total_events == 0:
        return "No events found matching the specified filters."

    fatalities_row = filtered_df.agg(
        F.coalesce(F.sum("fatalities"), F.lit(0)).alias("total_fatalities")
    ).first()
    total_fatalities = fatalities_row["total_fatalities"]

    event_type_rows = (
        filtered_df
        .groupBy("event_type")
        .count()
        .orderBy(F.desc("count"))
        .limit(5)
        .collect()
    )

    lines = [
        f"Total events: {total_events}",
        f"Total fatalities: {total_fatalities}",
        "",
    ]
    lines.extend(
        _format_breakdown(
            "Breakdown by event type",
            event_type_rows,
            "event_type",
        )
    )

    if router_output.sub_event_type is None:
        sub_event_type_rows = (
            filtered_df
            .groupBy("sub_event_type")
            .count()
            .orderBy(F.desc("count"))
            .limit(5)
            .collect()
        )
        lines.append("")
        lines.extend(
            _format_breakdown(
                "Breakdown by sub-event type",
                sub_event_type_rows,
                "sub_event_type",
            )
        )

    has_date_filter = (
        router_output.date_from is not None or router_output.date_to is not None
    )
    if not has_date_filter:
        year_rows = (
            filtered_df
            .groupBy("year")
            .count()
            .orderBy("year")
            .collect()
        )
        lines.append("")
        lines.extend(_format_breakdown("Breakdown by year", year_rows, "year"))

    if router_output.country is None:
        country_rows = (
            filtered_df
            .groupBy("country")
            .count()
            .orderBy(F.desc("count"))
            .limit(5)
            .collect()
        )
        lines.append("")
        lines.extend(
            _format_breakdown("Breakdown by country", country_rows, "country")
        )

    return "\n".join(lines)


if __name__ == "__main__":
    from router import RouterOutput

    test_queries = [
        RouterOutput(
            query_type="STRUCTURED",
            country="Sudan",
            date_from=None,
            date_to=None,
            event_type=None,
        ),
        RouterOutput(
            query_type="STRUCTURED",
            country="Algeria",
            date_from="2018-01-01",
            date_to="2020-12-31",
            event_type=None,
        ),
        RouterOutput(
            query_type="STRUCTURED",
            country=None,
            date_from="2023-01-01",
            date_to="2023-12-31",
            event_type="Battles",
        ),
        RouterOutput(
            query_type="STRUCTURED",
            country="Sudan",
            date_from=None,
            date_to=None,
            event_type=None,
            disorder_type="Political violence",
            sub_event_type=None,
        ),
        RouterOutput(
            query_type="STRUCTURED",
            country="Mali",
            date_from="2022-01-01",
            date_to="2022-12-31",
            event_type=None,
            disorder_type=None,
            sub_event_type="Armed clash",
        ),
        RouterOutput(
            query_type="STRUCTURED",
            country=None,
            date_from=None,
            date_to=None,
            event_type=None,
        ),
    ]

    for routed_query in test_queries:
        print("=" * 80)
        print(f"Simulated query type: {routed_query.query_type}")
        print("=" * 80)
        print(run_structured_query(routed_query))
        print()
