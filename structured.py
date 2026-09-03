from datetime import date, datetime

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

    if dict(filtered_df.dtypes).get("event_date") != "date":
        filtered_df = filtered_df.withColumn(
            "event_date",
            F.to_date(F.col("event_date")),
        )

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

    if router_output.actor1 is not None:
        actor1 = router_output.actor1.strip().lower()
        filtered_df = filtered_df.filter(F.lower(F.col("actor1")).contains(actor1))

    if router_output.actor2 is not None:
        actor2 = router_output.actor2.strip().lower()
        filtered_df = filtered_df.filter(F.lower(F.col("actor2")).contains(actor2))

    if router_output.region is not None:
        region = router_output.region.strip().lower()
        filtered_df = filtered_df.filter(F.lower(F.col("region")).contains(region))

    if router_output.admin1 is not None:
        admin1 = router_output.admin1.strip().lower()
        filtered_df = filtered_df.filter(F.lower(F.col("admin1")).contains(admin1))

    if router_output.date_from is not None:
        filtered_df = filtered_df.filter(
            F.col("event_date") >= F.to_date(F.lit(router_output.date_from))
        )

    if router_output.date_to is not None:
        filtered_df = filtered_df.filter(
            F.col("event_date") <= F.to_date(F.lit(router_output.date_to))
        )

    return filtered_df


def _parse_iso_date(value):
    if value is None:
        return None

    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    return parsed


def _date_range_within_two_years(date_from, date_to):
    start = _parse_iso_date(date_from)
    end = _parse_iso_date(date_to)

    if start is None or end is None:
        return False

    if end < start:
        return False

    try:
        two_year_limit = date(start.year + 2, start.month, start.day)
    except ValueError:
        two_year_limit = date(start.year + 2, 2, 28)

    return end <= two_year_limit


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

    actor1_rows = (
        filtered_df
        .groupBy("actor1")
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
    lines.append("")
    lines.extend(
        _format_breakdown(
            "Breakdown by primary actor",
            actor1_rows,
            "actor1",
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

        fatalities_by_year_rows = (
            filtered_df
            .groupBy("year")
            .agg(F.coalesce(F.sum("fatalities"), F.lit(0)).alias("fatalities"))
            .orderBy("year")
            .collect()
        )
        lines.append("")
        lines.append("Breakdown of fatalities by year:")
        for row in fatalities_by_year_rows:
            year = row["year"] if row["year"] not in (None, "") else "Unknown"
            lines.append(f"{year}: {row['fatalities']} fatalities")

        highest_fatalities_year = max(
            fatalities_by_year_rows,
            key=lambda row: row["fatalities"],
        )
        lines.append(
            "Year with highest fatalities: "
            f"{highest_fatalities_year['year']} "
            f"({highest_fatalities_year['fatalities']} fatalities)"
        )

    if _date_range_within_two_years(router_output.date_from, router_output.date_to):
        month_rows = (
            filtered_df
            .groupBy(F.date_format(F.col("event_date"), "yyyy-MM").alias("month"))
            .count()
            .orderBy("month")
            .collect()
        )
        lines.append("")
        lines.extend(_format_breakdown("Breakdown by month", month_rows, "month"))

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
            country="Ukraine",
            date_from=None,
            date_to=None,
            event_type="Battles",
            disorder_type=None,
            sub_event_type=None,
            actor1="Russian forces",
        ),
        RouterOutput(
            query_type="STRUCTURED",
            country=None,
            date_from=None,
            date_to=None,
            event_type=None,
            disorder_type=None,
            sub_event_type=None,
            region="Sahel",
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

    spark = get_spark_session()
    df = load_structured_df(spark)
    burkina_faso_2022 = RouterOutput(
        query_type="STRUCTURED",
        country="Burkina Faso",
        date_from="2022-01-01",
        date_to="2022-12-31",
        event_type=None,
        disorder_type=None,
        sub_event_type=None,
    )
    burkina_faso_all_dates = RouterOutput(
        query_type="STRUCTURED",
        country="Burkina Faso",
        date_from=None,
        date_to=None,
        event_type=None,
        disorder_type=None,
        sub_event_type=None,
    )

    print("=" * 80)
    print("Explicit date-filter check")
    print("=" * 80)
    print(
        "Burkina Faso events in 2022:",
        apply_filters(df, burkina_faso_2022).count(),
    )
    print(
        "Burkina Faso events without date filter:",
        apply_filters(df, burkina_faso_all_dates).count(),
    )
