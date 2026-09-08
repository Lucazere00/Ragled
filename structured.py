from datetime import date, datetime
import hashlib
import json
from pathlib import Path

from pyspark.sql import Row, SparkSession
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

    if router_output.civilian_targeting is not None and "civilian_targeting" in filtered_df.columns:
        civilian_targeting = router_output.civilian_targeting.strip().lower()
        filtered_df = filtered_df.filter(
            F.lower(F.col("civilian_targeting")).contains(civilian_targeting)
        )

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
    """Format grouped Spark rows as a sentence rather than a list."""
    description = title.removeprefix("Breakdown by ").lower()
    plural_descriptions = {
        "day": "days",
        "event type": "event types",
        "primary actor": "primary actors",
        "sub-event type": "sub-event types",
        "year": "years",
        "month": "months",
        "country": "countries",
    }
    sentence_subject = plural_descriptions.get(description, description)

    if not rows:
        return [f"No {sentence_subject} were recorded."]

    entries = []
    for row in rows:
        label = row[label_field] if row[label_field] not in (None, "") else "Unknown"
        entries.append(f"{label} ({row[count_field]})")

    return [f"The {sentence_subject} were {', '.join(entries)}."]


def _fallback_breakdown_commentary(rows, label_field, metric_field, dimension):
    """Describe multi-bucket aggregates when the commentary model is unavailable."""
    values = [int(row[metric_field] or 0) for row in rows]
    if len(values) < 2:
        return ""
    first_value, last_value = values[0], values[-1]
    if first_value:
        change = (last_value - first_value) / first_value * 100
        trend = "increased" if change > 0 else "decreased" if change < 0 else "remained stable"
        change_text = f"{abs(change):.1f}%"
        direction_text = f"{trend} by {change_text}" if change else trend
    else:
        direction_text = "changed from zero"
    maximum = max(rows, key=lambda row: int(row[metric_field] or 0))
    minimum = min(rows, key=lambda row: int(row[metric_field] or 0))
    metric_label = "fatalities" if metric_field == "fatalities" else "events"
    return (
        f"Across the {dimension.replace('_', ' ')} buckets, the number of {metric_label} "
        f"{direction_text} from {first_value} to {last_value}. The maximum was "
        f"{maximum[label_field]} ({int(maximum[metric_field] or 0)}) and the minimum was "
        f"{minimum[label_field]} ({int(minimum[metric_field] or 0)})."
    )


def _generate_breakdown_commentary(rows, label_field, metric_field, dimension, question):
    """Ask the LLM for a concise interpretation, with a local fallback."""
    if len(rows) < 2:
        return ""
    aggregate_data = [
        {"bucket": row[label_field], "value": int(row[metric_field] or 0)}
        for row in rows
    ]
    fallback = _fallback_breakdown_commentary(
        rows, label_field, metric_field, dimension
    )
    try:
        from langchain_groq import ChatGroq

        prompt = (
            "You analyze aggregated ACLED data. Write 2 concise sentences in English. "
            "Describe the direction and percentage change between the first and last "
            "bucket when meaningful, and identify the maximum and minimum bucket. "
            "Do not invent causes or facts. Question: {question}. Aggregates: {data}"
        ).format(question=question or "", data=json.dumps(aggregate_data, default=str))
        response = ChatGroq(model="openai/gpt-oss-20b", temperature=0).invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        return text.strip() or fallback
    except Exception:
        return fallback


def _format_filter_scope(router_output):
    """Describe the explicit filters so aggregate answers retain their scope."""
    parts = []
    if router_output.country is not None:
        parts.append(f"in {router_output.country}")
    if router_output.date_from is not None and router_output.date_to is not None:
        parts.append(f"between {router_output.date_from} and {router_output.date_to}")
    elif router_output.date_from is not None:
        parts.append(f"from {router_output.date_from}")
    elif router_output.date_to is not None:
        parts.append(f"through {router_output.date_to}")
    return " ".join(parts)


def _format_ranking_scope(router_output):
    """Return a concise natural-language scope for ranking introductions."""
    if router_output.date_from and router_output.date_to:
        if router_output.date_from[:4] == router_output.date_to[:4]:
            return f" in {router_output.date_from[:4]}"
        return f" between {router_output.date_from} and {router_output.date_to}"
    if router_output.date_from:
        return f" from {router_output.date_from}"
    if router_output.date_to:
        return f" through {router_output.date_to}"
    if router_output.country:
        return f" in {router_output.country}"
    if router_output.region:
        return f" in {router_output.region}"
    return ""


def _format_summary_text(router_output, total_events, total_fatalities):
    event_label = router_output.event_type.lower() if router_output.event_type else "events"
    scope = _format_filter_scope(router_output)
    scope_suffix = f" {scope}" if scope else ""
    return (
        f"The selected data contains {total_events} {event_label} and "
        f"{total_fatalities} fatalities{scope_suffix}."
    )


def _requested_metric(question, router_output=None):
    """Infer whether the question asks for event counts or fatalities."""
    if router_output is not None and router_output.ranking_metric is not None:
        return router_output.ranking_metric
    text = (question or "").lower()
    if any(term in text for term in (
        "fatalit", "deaths", "killed", "casualties", "deadliest",
        "most dangerous", "most violent", "highest death toll", "most lethal",
    )):
        return "fatalities"
    return "events"


def _requested_dimension(router_output, question):
    """Infer the single aggregation dimension explicitly requested by a question."""
    text = (question or "").lower()

    if router_output.group_by is not None:
        return router_output.group_by

    if router_output.time_granularity is not None:
        return router_output.time_granularity

    if any(term in text for term in (
        "armed group", "armed groups", "actor", "actors", "which group",
        "what group", "which faction", "what faction", "most associated with",
    )):
        return "actor1"

    if any(term in text for term in ("highest", "most", "least", "lowest", "deadliest", "dangerous")):
        if "month" in text:
            return "month"
        if "week" in text:
            return "week"
        if "year" in text:
            return "year"

    if any(term in text for term in ("yearly trend", "annual trend", "by year", "each year")):
        return "year"
    if any(term in text for term in ("monthly trend", "by month", "each month")):
        return "month"
    if any(term in text for term in ("daily trend", "by day", "each day")):
        return "day"
    if "disorder type" in text or "disorder_type" in text or "by disorder" in text:
        return "disorder_type"
    if "sub-event type" in text or "sub_event_type" in text or "by sub-event" in text:
        return "sub_event_type"
    if "event type" in text or "event types" in text or "types of attack" in text:
        return "event_type"
    if "region" in text or "by region" in text:
        return "region"
    if "country" in text or "countries" in text:
        return "country"
    if router_output.region is not None and any(term in text for term in ("highest", "most", "each")):
        return "region"
    if router_output.country is not None and any(term in text for term in ("highest", "most", "each")):
        return "country"
    if any(term in text for term in ("highest", "most", "each")):
        if "region" in text:
            return "region"
        if "country" in text or "countries" in text:
            return "country"
    if router_output.actor1 is not None and any(term in text for term in ("highest", "most", "each")):
        return "actor1"
    return None


def _requested_dimensions(router_output, question):
    """Return ordered dimensions for nested aggregations, preserving single-group compatibility."""
    dimensions = list(router_output.group_by_dimensions or [])
    if dimensions:
        return dimensions
    dimension = _requested_dimension(router_output, question)
    return [dimension] if dimension else []


def _is_comparison_question(question):
    text = (question or "").casefold()
    return "compare" in text or "comparison" in text


def _is_ranking_question(question):
    text = (question or "").casefold()
    return any(
        term in text
        for term in ("highest", "lowest", "most", "least", "top", "deadliest", "most dangerous")
    )


def _dimension_column(dimension):
    return "actor1" if dimension == "actor" else dimension


def _aggregate_rows(filtered_df, dimensions, metric):
    """Aggregate any number of dimensions into a flat, tabular row structure."""
    group_columns = [_dimension_column(dimension) for dimension in dimensions]
    grouped = filtered_df.groupBy(*group_columns)
    aggregations = [F.count(F.lit(1)).alias("count")]
    aggregations.append(F.coalesce(F.sum("fatalities"), F.lit(0)).alias("fatalities"))
    rows = grouped.agg(*aggregations).collect()
    result = []
    for row in rows:
        item = {
            dimension: row[_dimension_column(dimension)] or "Unknown"
            for dimension in dimensions
        }
        item.update({"count": int(row["count"] or 0), "fatalities": int(row["fatalities"] or 0)})
        item["metric_value"] = item["fatalities"] if metric == "fatalities" else item["count"]
        result.append(item)
    return sorted(result, key=lambda item: tuple(str(item[dimension]) for dimension in dimensions))


def _aggregate_growth_rows(filtered_df, dimensions, metric):
    """Aggregate start/end yearly values and derive absolute and relative change."""
    year_rows = (
        filtered_df.withColumn("_year", F.year(F.col("event_date")))
        .groupBy(*[_dimension_column(dimension) for dimension in dimensions], "_year")
        .agg(
            F.count(F.lit(1)).alias("count"),
            F.coalesce(F.sum("fatalities"), F.lit(0)).alias("fatalities"),
        )
        .collect()
    )
    by_key = {}
    for row in year_rows:
        key = tuple(row[_dimension_column(dimension)] or "Unknown" for dimension in dimensions)
        value = int(row["fatalities"] or 0) if metric == "fatalities" else int(row["count"] or 0)
        by_key.setdefault(key, {})[int(row["_year"])] = value
    years = sorted({year for values in by_key.values() for year in values})
    if len(years) < 2:
        return []
    start_year, end_year = years[0], years[-1]
    results = []
    for key, values in by_key.items():
        start_value = values.get(start_year, 0)
        end_value = values.get(end_year, 0)
        delta = end_value - start_value
        growth_pct = (delta / start_value * 100) if start_value else None
        item = {dimension: key[index] for index, dimension in enumerate(dimensions)}
        item.update({
            "start_year": start_year,
            "end_year": end_year,
            "start_value": start_value,
            "end_value": end_value,
            "delta": delta,
            "growth_pct": growth_pct,
            "metric_value": growth_pct if metric == "growth_pct" and growth_pct is not None else delta,
        })
        results.append(item)
    return sorted(
        results,
        key=lambda item: (
            item["growth_pct"] is not None,
            item["growth_pct"] if item["growth_pct"] is not None else float("-inf"),
            item["delta"],
        ),
        reverse=True,
    )


def _format_ranking_rows(
    rows,
    dimensions,
    metric_field,
    metric,
    scope="",
    total_count=None,
    ranking_label="top",
    limit=10,
):
    """Format ordered aggregate rows as a readable numbered ranking."""
    if not rows:
        return "No matching combinations were found."

    dimension_labels = {
        "actor1": ("actor", "actors"),
        "country": ("country", "countries"),
        "region": ("region", "regions"),
        "sub_event_type": ("sub-event type", "sub-event types"),
        "event_type": ("event type", "event types"),
        "disorder_type": ("disorder type", "disorder types"),
        "day": ("day", "days"),
        "week": ("week", "weeks"),
        "month": ("month", "months"),
        "year": ("year", "years"),
    }
    readable_dimensions = [
        dimension_labels.get(dimension, (dimension.replace("_", " "), ""))[0]
        for dimension in dimensions
    ]
    if len(readable_dimensions) == 1:
        if dimensions[0] == "actor1":
            subject = "armed groups"
        else:
            subject = dimension_labels.get(dimensions[0], (readable_dimensions[0], ""))[1]
        introduction = f"The {ranking_label} {subject} by {metric}"
        total_label = subject
    else:
        if len(readable_dimensions) == 2:
            dimension_text = " and ".join(readable_dimensions)
        else:
            dimension_text = ", ".join(readable_dimensions[:-1]) + ", and " + readable_dimensions[-1]
        introduction = f"The {ranking_label} combinations of {dimension_text} by {metric}"
        total_label = "combinations"
    introduction += f"{scope} were:"

    entries = []
    for index, row in enumerate(rows[:limit], start=1):
        combination = " — ".join(
            str(row[dimension]) if row[dimension] not in (None, "") else "Unknown"
            for dimension in dimensions
        )
        if "start_value" in row:
            value = f"{row['start_value']} to {row['end_value']} (delta {row['delta']}"
            if row["growth_pct"] is not None:
                value += f", {row['growth_pct']:.1f}%"
            value += ")"
        else:
            numeric_value = int(row[metric_field] or 0)
            metric_unit = "fatality" if metric == "fatality count" and numeric_value == 1 else (
                "fatalities" if metric == "fatality count" else "event" if numeric_value == 1 else "events"
            )
            value = f"{numeric_value:,} {metric_unit}"
        entries.append(f"{index}. {combination}: {value}")

    result = introduction + "\n" + "\n".join(entries)
    displayed_count = min(len(rows), limit)
    if total_count is not None and total_count > displayed_count:
        result += f"\n(showing top {displayed_count} of {total_count} total {total_label})"
    return result


def _generate_multidimensional_chart(rows, dimensions, metric_field, question, title):
    if not rows:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir = Path("output/charts")
    output_dir.mkdir(parents=True, exist_ok=True)
    query_hash = hashlib.sha256((question or title).encode("utf-8")).hexdigest()[:12]
    chart_path = output_dir / f"structured_{query_hash}.png"
    labels = [" | ".join(str(row[dimension]) for dimension in dimensions) for row in rows[:20]]
    values = [row[metric_field] if row[metric_field] is not None else 0 for row in rows[:20]]
    figure, axis = plt.subplots(figsize=(11, 5))
    axis.bar(labels, values, color="#54d6a8")
    axis.set_title(title)
    axis.set_xlabel(" + ".join(dimensions))
    axis.set_ylabel(metric_field.replace("_", " ").title())
    axis.tick_params(axis="x", rotation=35)
    figure.tight_layout()
    figure.savefig(chart_path, dpi=150)
    plt.close(figure)
    return {
        "path": str(chart_path),
        "chart_type": "bar",
        "labels": labels,
        "values": values,
        "dimensions": dimensions,
        "description": f"Top combinations by {' + '.join(dimensions)}.",
    }


def _generate_grouped_comparison_chart(rows, entity_field, bucket_field, metric_field, question):
    if not rows:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir = Path("output/charts")
    output_dir.mkdir(parents=True, exist_ok=True)
    query_hash = hashlib.sha256((question or "comparison").encode("utf-8")).hexdigest()[:12]
    chart_path = output_dir / f"structured_{query_hash}.png"
    entities = list(dict.fromkeys(row[entity_field] for row in rows))
    buckets = list(dict.fromkeys(row[bucket_field] for row in rows))
    figure, axis = plt.subplots(figsize=(10, 5))
    width = 0.8 / max(len(entities), 1)
    positions = list(range(len(buckets)))
    series = []
    for index, entity in enumerate(entities):
        values = [
            next((row[metric_field] for row in rows if row[entity_field] == entity and row[bucket_field] == bucket), 0)
            for bucket in buckets
        ]
        axis.bar([position + index * width for position in positions], values, width=width, label=str(entity))
        series.append({"label": entity, "values": values})
    axis.set_xticks([position + width * (len(entities) - 1) / 2 for position in positions])
    axis.set_xticklabels([str(bucket) for bucket in buckets], rotation=35)
    axis.set_ylabel(metric_field.title())
    axis.legend()
    figure.tight_layout()
    figure.savefig(chart_path, dpi=150)
    plt.close(figure)
    return {
        "path": str(chart_path),
        "chart_type": "grouped_bar",
        "labels": [str(bucket) for bucket in buckets],
        "series": series,
        "values": [series_item["values"] for series_item in series],
        "description": "Grouped comparison chart using the same aggregate rows as the text response.",
    }


def _run_comparison_query(df, router_output, question, metric):
    entities = router_output.comparison_entities
    if len(entities) != 2:
        return {
            "text": "Please specify the two entities you want to compare.",
            "chart": None,
            "rows": [],
            "needs_clarification": True,
        }
    comparison_dimension = router_output.comparison_dimension or "actor1"
    dimensions = list(router_output.group_by_dimensions or [])
    if not dimensions:
        dimensions = ["sub_event_type"] if "sub-event" in (question or "").casefold() else ["actor1"]
    bucket_dimension = dimensions[-1]
    rows = []
    filter_field = _dimension_column(comparison_dimension)
    for entity in entities:
        scoped = df.filter(F.lower(F.col(filter_field)).contains(entity.casefold()))
        aggregate_rows = _aggregate_rows(scoped, [bucket_dimension], metric)
        for row in aggregate_rows:
            row["comparison_entity"] = entity
            rows.append(row)
    rows = sorted(rows, key=lambda row: (str(row["comparison_entity"]), str(row[bucket_dimension])))
    metric_field = "fatalities" if metric == "fatalities" else "count"
    text_parts = []
    for entity in entities:
        entity_rows = [row for row in rows if row["comparison_entity"] == entity]
        text_parts.append(
            f"{entity}: " + ", ".join(f"{row[bucket_dimension]} ({row[metric_field]})" for row in entity_rows)
        )
    text = "Comparison by " + bucket_dimension.replace("_", " ") + ": " + "; ".join(text_parts) + "."
    chart = _generate_grouped_comparison_chart(
        rows, "comparison_entity", bucket_dimension, metric_field, question
    )
    return {
        "text": text,
        "chart": chart,
        "rows": rows,
        "dimensions": [comparison_dimension, bucket_dimension],
        "comparison": {"entities": entities, "dimension": comparison_dimension},
    }


def _automatic_time_granularity(date_from, date_to):
    """Choose a readable time bucket for an automatically generated chart."""
    start = _parse_iso_date(date_from)
    end = _parse_iso_date(date_to)
    if start is None or end is None or end < start:
        return None

    range_days = (end - start).days + 1
    if range_days <= 31:
        return "day"
    if range_days <= 365:
        return "month"
    return "year"


def _date_bounds(filtered_df, router_output):
    """Resolve missing date bounds from the already-filtered event data."""
    start = router_output.date_from
    end = router_output.date_to
    if start is not None and end is not None:
        return start, end

    bounds = filtered_df.agg(
        F.min("event_date").alias("date_from"),
        F.max("event_date").alias("date_to"),
    ).first()
    return (
        start or (bounds["date_from"].isoformat() if bounds["date_from"] else None),
        end or (bounds["date_to"].isoformat() if bounds["date_to"] else None),
    )


def _automatic_time_rows(filtered_df, router_output, metric="events"):
    """Group filtered events into automatic day, month, or year buckets."""
    date_from, date_to = _date_bounds(filtered_df, router_output)
    granularity = _automatic_time_granularity(date_from, date_to)
    if granularity is None:
        return None, []

    formats = {
        "day": "yyyy-MM-dd",
        "week": "YYYY-'W'ww",
        "month": "yyyy-MM",
        "year": "yyyy",
    }
    label = granularity
    grouped = filtered_df.groupBy(
        F.date_format(F.col("event_date"), formats[granularity]).alias(label)
    )
    aggregations = [F.count(F.lit(1)).alias("count")]
    if metric == "fatalities":
        aggregations.append(
            F.coalesce(F.sum("fatalities"), F.lit(0)).alias("fatalities")
        )
    rows = grouped.agg(*aggregations).orderBy(label).collect()
    return granularity, rows


def generate_chart(data, chart_type, title, x_label, y_label, query=None, highlighted_label=None):
    """Save a chart from already-aggregated data and return its path."""
    if not data:
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir = Path("output/charts")
    output_dir.mkdir(parents=True, exist_ok=True)
    query_hash = hashlib.sha256((query or title).encode("utf-8")).hexdigest()[:12]
    chart_path = output_dir / f"structured_{query_hash}.png"
    labels = [str(label) for label, _ in data]
    values = [value for _, value in data]

    figure, axis = plt.subplots(figsize=(10, 5))
    if chart_type == "line":
        axis.plot(labels, values, marker="o")
    else:
        axis.bar(
            labels,
            values,
            color=[
                "#f4bd50" if label == str(highlighted_label) else "#54d6a8"
                for label in labels
            ],
        )
    axis.set_title(title)
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    axis.tick_params(axis="x", rotation=35)
    figure.tight_layout()
    figure.savefig(chart_path, dpi=150)
    plt.close(figure)
    return str(chart_path)


def _chart_metadata(dimension, rows, question, chart_type_override=None, router_output=None):
    chart_labels = {
        "day": ("Daily event trend", "Day", "Events"),
        "disorder_type": ("Disorder type", "Disorder type", "Events"),
        "event_type": ("Event type", "Event type", "Events"),
        "sub_event_type": ("Sub-event type", "Sub-event type", "Events"),
        "actor1": ("Primary actors", "Actor", "Events"),
        "country": ("Incidents by country", "Country", "Events"),
        "region": ("Incidents by region", "Region", "Events"),
        "year": ("Yearly event trend", "Year", "Events"),
        "week": ("Weekly event trend", "Week", "Events"),
        "month": ("Monthly event trend", "Month", "Events"),
    }
    title, x_label, y_label = chart_labels[dimension]
    metric_field = "fatalities" if _requested_metric(question, router_output) == "fatalities" else "count"
    if metric_field == "fatalities":
        y_label = "Fatalities"
    data = [(row[dimension], int(row[metric_field] or 0)) for row in rows]
    winner = max(data, key=lambda item: item[1])[0] if data else None
    chart_type = chart_type_override or ("line" if dimension in ("year", "week", "month", "day") else "bar")
    path = generate_chart(data, chart_type, title, x_label, y_label, question, winner)
    if path is None:
        return None
    return {
        "path": path,
        "description": (
            f"{chart_type} chart of {'fatalities' if metric_field == 'fatalities' else 'event counts'} "
            f"by {x_label.lower()}, ordered for the requested query."
        ),
        "chart_type": chart_type,
        "labels": [str(label or "Unknown") for label, _ in data],
        "values": [value for _, value in data],
        "highlighted_label": str(winner) if winner is not None else None,
    }


def run_structured_query(router_output, question=None) -> dict:
    """
    Run aggregate ACLED analytics for a routed structured query.

    Returns a dict with the focused text response and optional chart metadata.
    """
    spark = get_spark_session()
    df = load_structured_df(spark)
    filtered_df = apply_filters(df, router_output)

    if _is_comparison_question(question):
        return _run_comparison_query(filtered_df, router_output, question, _requested_metric(question, router_output))

    total_events = filtered_df.count()
    if total_events == 0:
        return {"text": "No events found matching the specified filters.", "chart": None}

    fatalities_row = filtered_df.agg(
        F.coalesce(F.sum("fatalities"), F.lit(0)).alias("total_fatalities")
    ).first()
    total_fatalities = fatalities_row["total_fatalities"]

    metric = _requested_metric(question, router_output)
    dimensions = _requested_dimensions(router_output, question)
    if router_output.growth_metric is not None or len(dimensions) > 1:
        if router_output.growth_metric is not None:
            rows = _aggregate_growth_rows(
                filtered_df, dimensions, router_output.growth_metric
            )
            metric_field = "growth_pct" if router_output.growth_metric == "growth_pct" else "delta"
            title = "Growth by " + " + ".join(dimensions)
        else:
            rows = _aggregate_rows(filtered_df, dimensions, metric)
            rows = sorted(rows, key=lambda row: row["metric_value"], reverse=True)
            metric_field = "metric_value"
            title = "Breakdown by " + " + ".join(dimensions)
        chart_rows = rows[:20] if router_output.growth_metric is None else rows
        chart = _generate_multidimensional_chart(
            chart_rows, dimensions, metric_field, question, title
        )
        if router_output.growth_metric is not None:
            text = _format_ranking_rows(
                rows,
                dimensions,
                metric_field,
                "growth rate",
                scope=_format_ranking_scope(router_output),
                total_count=len(rows),
                ranking_label="fastest-growing",
            )
        else:
            text = _format_ranking_rows(
                rows,
                dimensions,
                metric_field,
                "fatality count" if metric == "fatalities" else "event count",
                scope=_format_ranking_scope(router_output),
                total_count=len(rows),
            )
        return {
            "text": text,
            "chart": chart,
            "rows": rows,
            "dimensions": dimensions,
            "metric": metric,
            "growth_metric": router_output.growth_metric,
        }
    dimension = _requested_dimension(router_output, question)
    if dimension is None:
        text = _format_summary_text(router_output, total_events, total_fatalities)
        if router_output.event_type is None and router_output.sub_event_type is None:
            return {"text": text, "chart": None}
        automatic_dimension, rows = _automatic_time_rows(
            filtered_df, router_output, metric
        )
        if automatic_dimension is None:
            automatic_dimension = "event_type" if router_output.event_type is not None else "sub_event_type"
            label = router_output.event_type or router_output.sub_event_type
            rows = [
                Row(
                    **{
                        automatic_dimension: label,
                        "count": total_events,
                        "fatalities": total_fatalities,
                    }
                )
            ]
        return {
            "text": text,
            "chart": _chart_metadata(automatic_dimension, rows, question, "bar", router_output),
        }

    if dimension in ("day", "week", "month", "year"):
        formats = {
            "day": "yyyy-MM-dd",
            "week": "YYYY-'W'ww",
            "month": "yyyy-MM",
            "year": "yyyy",
        }
        grouped = filtered_df.groupBy(
            F.date_format(F.col("event_date"), formats[dimension]).alias(dimension)
        )
    else:
        grouped = filtered_df.groupBy(dimension)
    aggregations = [F.count(F.lit(1)).alias("count")]
    if metric == "fatalities":
        aggregations.append(
            F.coalesce(F.sum("fatalities"), F.lit(0)).alias("fatalities")
        )
    rows_query = grouped.agg(*aggregations).orderBy(
        F.desc("fatalities" if metric == "fatalities" else "count")
    )
    is_ranking = router_output.ranking_metric is not None or _is_ranking_question(question)
    if dimension not in ("day", "week", "month", "year") and not is_ranking:
        rows_query = rows_query.limit(20)
    rows = rows_query.collect()
    if dimension in ("day", "week", "month", "year"):
        rows = sorted(rows, key=lambda row: str(row[dimension] or ""))

    titles = {
        "day": "days",
        "disorder_type": "disorder types",
        "event_type": "event types",
        "sub_event_type": "sub-event types",
        "actor1": "primary actors",
        "country": "countries",
        "region": "regions",
        "year": "years",
        "week": "weeks",
        "month": "months",
    }
    metric_field = "fatalities" if metric == "fatalities" else "count"
    if is_ranking:
        ranking_rows = sorted(rows, key=lambda row: row[metric_field] or 0, reverse=True)
        text = _format_ranking_rows(
            ranking_rows,
            [dimension],
            metric_field,
            "fatality count" if metric == "fatalities" else "event count",
            scope=_format_ranking_scope(router_output),
            total_count=len(ranking_rows),
        )
    else:
        breakdown = _format_breakdown(
            f"Breakdown by {titles[dimension]}", rows, dimension, metric_field
        )
        text = " ".join(breakdown)
    commentary = _generate_breakdown_commentary(
        rows, dimension, metric_field, dimension, question
    )
    chart = _chart_metadata(dimension, rows, question, router_output=router_output)
    winner = max(rows, key=lambda row: row[metric_field] or 0) if rows else None
    ranking = None
    if router_output.ranking_metric is not None or router_output.time_granularity is not None:
        ranking = {
            "dimension": dimension,
            "metric": metric,
            "winner": winner[dimension] if winner else None,
        }
    if commentary and not is_ranking:
        text = f"{text} {commentary}"
    return {"text": text, "chart": chart, "ranking": ranking}


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
