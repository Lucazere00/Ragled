import csv
from functools import lru_cache
from datetime import date
from pathlib import Path
from typing import Literal

import pyarrow.dataset as ds
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from groq import RateLimitError
from pydantic import BaseModel, Field

from main import run_pipeline


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    context: dict | None = None


class ChatResponse(BaseModel):
    type: Literal["text", "semantic", "structured", "hybrid"]
    answer: str
    chart: dict | None = None
    chart_message: str | None = None


app = FastAPI(title="Ragled API")
DATASET_PATH = Path(__file__).parent / "data" / "acled_processed.parquet"
MAX_MAP_EVENTS = 5000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Ragled API", "health": "/health", "chat": "/api/chat"}


@lru_cache(maxsize=1)
def event_filter_options() -> dict:
    """Build filter values from the complete CSV, not from the map point limit."""
    years: set[int] = set()
    countries: set[str] = set()
    regions: set[str] = set()
    event_types: set[str] = set()
    disorder_types: set[str] = set()
    sub_event_types: set[str] = set()
    sub_event_types_by_event_type: dict[str, set[str]] = {}

    dataset = ds.dataset(str(DATASET_PATH), format="parquet")
    columns = ["event_date", "country", "region", "event_type", "disorder_type", "sub_event_type"]
    for batch in dataset.scanner(columns=columns, batch_size=100_000).to_batches():
        for row in batch.to_pylist():
            event_date = row.get("event_date")
            if event_date:
                years.add(event_date.year)
            for values, field in (
                (countries, "country"),
                (regions, "region"),
                (event_types, "event_type"),
                (disorder_types, "disorder_type"),
                (sub_event_types, "sub_event_type"),
            ):
                value = (row.get(field) or "").strip()
                if value:
                    values.add(value)
            event_type = (row.get("event_type") or "").strip()
            sub_event_type = (row.get("sub_event_type") or "").strip()
            if event_type and sub_event_type:
                sub_event_types_by_event_type.setdefault(event_type, set()).add(sub_event_type)

    return {
        "years": sorted(years),
        "countries": sorted(countries, key=str.casefold),
        "regions": sorted(regions, key=str.casefold),
        "eventTypes": sorted(event_types, key=str.casefold),
        "disorderTypes": sorted(disorder_types, key=str.casefold),
        "subEventTypes": sorted(sub_event_types, key=str.casefold),
        "subEventTypesByEventType": {
            event_type: sorted(values, key=str.casefold)
            for event_type, values in sorted(sub_event_types_by_event_type.items(), key=lambda item: item[0].casefold())
        },
    }


@app.get("/api/events/options")
def events_options() -> dict:
    if not DATASET_PATH.exists():
        raise HTTPException(status_code=500, detail="Dataset ACLED non trovato sul backend.")
    return event_filter_options()


@app.get("/api/events")
def events(
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    fatalities_min: int | None = Query(default=None, alias="fatalitiesMin", ge=0),
    fatalities_max: int | None = Query(default=None, alias="fatalitiesMax", ge=0),
    event_type: str | None = Query(default=None, alias="eventType"),
    disorder_type: str | None = Query(default=None, alias="disorderType"),
    sub_event_type: str | None = Query(default=None, alias="subEventType"),
    region: str | None = None,
    country: str | None = None,
    category: list[str] | None = None,
) -> list[dict]:
    """Return map-ready ACLED events, applying every active filter with AND semantics."""
    if not DATASET_PATH.exists():
        raise HTTPException(status_code=500, detail="Dataset ACLED non trovato sul backend.")

    try:
        start = date.fromisoformat(date_from) if date_from else None
        end = date.fromisoformat(date_to) if date_to else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Formato data non valido, usare YYYY-MM-DD.") from exc

    if start and end and start > end:
        raise HTTPException(status_code=422, detail="L'intervallo date non e valido.")
    if fatalities_min is not None and fatalities_max is not None and fatalities_min > fatalities_max:
        raise HTTPException(status_code=422, detail="L'intervallo fatalities non e valido.")

    # Do not expose the complete dataset when the map has no active selection.
    # This also protects the UI if the endpoint is called directly or accidentally.
    has_filter = any((date_from, date_to, fatalities_min is not None, fatalities_max is not None,
                      event_type, disorder_type, sub_event_type, region, country, category))
    if not has_filter:
        return []

    selected_categories = {value.casefold() for value in (category or [])}
    dataset = ds.dataset(str(DATASET_PATH), format="parquet")
    expression = (ds.field("latitude").is_valid() & ds.field("longitude").is_valid())
    if start:
        expression = expression & (ds.field("event_date") >= start)
    if end:
        expression = expression & (ds.field("event_date") <= end)
    if fatalities_min is not None:
        expression = expression & (ds.field("fatalities") >= fatalities_min)
    if fatalities_max is not None:
        expression = expression & (ds.field("fatalities") <= fatalities_max)
    for field, value in (("event_type", event_type), ("disorder_type", disorder_type), ("sub_event_type", sub_event_type), ("region", region), ("country", country)):
        if value:
            expression = expression & (ds.field(field) == value)
    if selected_categories:
        expression = expression & ds.field("event_type").isin(list(selected_categories))

    results: list[dict] = []
    columns = ["event_id_cnty", "event_date", "country", "region", "location", "event_type", "disorder_type", "sub_event_type", "latitude", "longitude", "fatalities", "notes"]
    for batch in dataset.scanner(columns=columns, filter=expression, batch_size=10_000).to_batches():
        for row in batch.to_pylist():
            event_date = row["event_date"]
            event_value = row.get("event_type") or ""
            sub_event_value = row.get("sub_event_type") or ""
            disorder_value = row.get("disorder_type") or ""
            fatalities = int(row.get("fatalities") or 0)
            results.append({
                "id": row.get("event_id_cnty") or f"event-{len(results)}",
                "title": f"{event_value}: {sub_event_value}".strip(": "),
                "date": event_date.isoformat() if event_date else "",
                "country": row.get("country") or "",
                "region": row.get("region") or "",
                "place": row.get("location") or "",
                "category": event_value,
                "disorderType": disorder_value,
                "subEventType": sub_event_value,
                "lat": float(row["latitude"]),
                "lng": float(row["longitude"]),
                "fatalities": fatalities,
                "intensity": min(100, fatalities * 10),
                "description": row.get("notes") or "",
            })
            if len(results) >= MAX_MAP_EVENTS:
                return results

    return results


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = run_pipeline(request.message.strip())
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="Limite Groq raggiunto. Riprova tra qualche minuto o verifica il piano/API key.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Impossibile elaborare la domanda.") from exc

    if isinstance(result, dict):
        chart = result.get("chart")
        if chart:
            chart = {
                "chartType": chart["chart_type"],
                "labels": chart["labels"],
                "series": [{
                    "name": "Fatalities" if "fatalit" in chart["description"].lower() else "Events",
                    "values": chart["values"],
                }],
                "path": chart["path"],
                "description": chart["description"],
                "highlightedLabel": chart.get("highlighted_label"),
            }
        return ChatResponse(
            type=result.get("type", "structured"),
            answer=str(result.get("answer", "")),
            chart=chart,
            chart_message=result.get("chart_message"),
        )

    return ChatResponse(type="text", answer=str(result))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=False)
