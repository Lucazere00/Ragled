import re
from typing import Literal, Optional

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field


load_dotenv()


class RouterOutput(BaseModel):
    """Structured output returned by the ACLED query router."""

    query_type: Literal["STRUCTURED", "SEMANTIC", "HYBRID"] = Field(
        description=(
            "STRUCTURED for calculations, aggregations, rankings, and filters; "
            "SEMANTIC for qualitative descriptions or retrieved event context; "
            "HYBRID when both structured analysis and semantic explanation are needed."
        )
    )
    country: Optional[str] = Field(
        default=None,
        description="Country explicitly mentioned in the query, if any.",
    )
    date_from: Optional[str] = Field(
        default=None,
        description="Start date in YYYY-MM-DD format when explicitly stated.",
    )
    date_to: Optional[str] = Field(
        default=None,
        description="End date in YYYY-MM-DD format when explicitly stated.",
    )
    event_type: Optional[str] = Field(
        default=None,
        description=(
            "ACLED event type explicitly mentioned, such as Battles, Protests, "
            "Riots, Violence against civilians, or Explosions/Remote violence."
        ),
    )
    disorder_type: Optional[str] = Field(
        default=None,
        description=(
            "Broad ACLED disorder category, such as Political violence, "
            "Demonstrations, or Strategic developments."
        ),
    )
    sub_event_type: Optional[str] = Field(
        default=None,
        description=(
            "Detailed ACLED sub-event type, such as Armed clash, Attack, "
            "Peaceful protest, or Looting/property destruction."
        ),
    )
    actor1: Optional[str] = Field(
        default=None,
        description="Primary actor explicitly mentioned in the query, if any.",
    )
    actor2: Optional[str] = Field(
        default=None,
        description="Secondary actor explicitly mentioned in the query, if any.",
    )
    region: Optional[str] = Field(
        default=None,
        description="Region explicitly mentioned in the query, if any.",
    )
    admin1: Optional[str] = Field(
        default=None,
        description="First-level administrative area explicitly mentioned, if any.",
    )
    time_granularity: Optional[Literal["day", "week", "month", "year"]] = Field(
        default=None,
        description="Temporal group-by requested explicitly, if any.",
    )
    ranking_metric: Optional[Literal["events", "fatalities"]] = Field(
        default=None,
        description=(
            "Metric for a ranking: events for incident counts, fatalities for "
            "danger/death rankings."
        ),
    )
    group_by: Optional[Literal[
        "day", "week", "month", "year", "disorder_type", "event_type",
        "sub_event_type", "actor1", "country", "region",
    ]] = Field(
        default=None,
        description=(
            "Dimension to group the result by. Use actor1 for armed groups, "
            "actors, factions, or which group questions."
        ),
    )
    group_by_dimensions: list[Literal[
        "day", "week", "month", "year", "disorder_type", "event_type",
        "sub_event_type", "actor1", "country", "region",
    ]] = Field(
        default_factory=list,
        description="Ordered dimensions for a nested or combination breakdown.",
    )
    comparison_entities: list[str] = Field(
        default_factory=list,
        description="Exactly two named entities when the question asks for a comparison.",
    )
    comparison_dimension: Optional[Literal[
        "actor1", "country", "region",
    ]] = Field(
        default=None,
        description="Dimension containing the two entities being compared.",
    )
    growth_metric: Optional[Literal["delta", "growth_pct"]] = Field(
        default=None,
        description="Use growth_pct for fastest growth, otherwise delta for biggest increase/decrease.",
    )
    civilian_targeting: Optional[str] = Field(
        default=None,
        description="Use Civilian targeting when the question explicitly asks about civilians.",
    )


ROUTER_SYSTEM_PROMPT = """
You are a query router for a system analyzing ACLED conflict event data.

Classify each user question into exactly one query_type:

STRUCTURED:
Use when the answer requires counting, summing, ranking, comparing, filtering,
or calculating over the ACLED dataset.
Examples:
- How many events occurred in Sudan in 2023?
- Which year had the most violence against civilians?
- Which country had the highest number of battles?

SEMANTIC:
Use when the answer requires retrieving, understanding, or summarizing event
content and narrative context, without a numerical calculation.
Examples:
- What kind of violence against civilians occurred in Algeria?
- What actors were involved in armed clashes in Sudan?
- What tactics were used by a group?

HYBRID:
Use when the answer requires both a calculation and a qualitative explanation.
Examples:
- How many civilians were killed in Algeria and what were the main types of violence?
- Which country had the most battles and what were the main actors involved?
- Describe the violence in the year with the highest number of events.

Extract filters only when they are explicitly mentioned or directly represented
in the question:
- country
- date_from
- date_to
- event_type
- disorder_type
- sub_event_type
- actor1
- actor2
- region
- admin1

Ranking and temporal grouping:
- Set time_granularity to month, year, week, or day when the question asks
    which period had the most/highest/least events or fatalities, including
    wording such as "most dangerous year" or "deadliest month".
- Set ranking_metric to fatalities for most dangerous, deadliest, most violent,
    highest death toll, most lethal, deaths, fatalities, or civilian death
    rankings. Set it to events for most events, most incidents, most active, or
    generic event rankings.
- Use HYBRID when a ranking is combined with narrative wording such as "what
    happened", "tell me about", "describe", or "what were the main patterns".
- Set group_by to actor1 when the question asks for armed groups, actors,
    factions, which group, or what group is most associated with a filter.
- Set group_by to region, country, event_type, sub_event_type, or a temporal
    dimension when the question explicitly requests that breakdown.
- Set group_by_dimensions to every requested dimension, in outer-to-inner order,
    for nested wording such as "country within each region" or "combination of
    country, actor, and sub-event type". Use actor1 for actor type.
- For comparisons, extract exactly two named entities into comparison_entities,
    set comparison_dimension, and set group_by_dimensions to the distribution
    dimension after the compared entity. For a comparison without two names,
    leave comparison_entities empty so the application can ask for clarification.
- Set growth_metric to growth_pct for fastest growth and to delta for biggest
    increase or decrease.

Dates:
Return dates as YYYY-MM-DD. If only a year is mentioned, convert it to the full
year range. For example, 2023 means date_from = "2023-01-01" and
date_to = "2023-12-31". For a range such as 2018 to 2020, use
"2018-01-01" to "2020-12-31". Do not invent dates for vague wording such as
"recently", "recent years", or "the last few years".

ACLED hierarchy:
- disorder_type is broad, such as Political violence, Demonstrations, or
  Strategic developments.
- event_type is intermediate, such as Battles, Protests, Riots, Violence
  against civilians, Explosions/Remote violence, or Strategic developments.
- sub_event_type is specific, such as Armed clash, Attack, Peaceful protest,
  Excessive force against protesters, or Looting/property destruction.

Preserve standard ACLED capitalization and spacing when possible. Use null for
any field that is not explicitly present or cannot be reliably inferred.

Return only the structured RouterOutput object.
"""


def get_router_llm():
    """Create the Groq LLM used for routing and structured extraction."""
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    return llm.with_structured_output(RouterOutput)


def build_router_chain():
    """Build the LangChain router."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            ("human", "{query}"),
        ]
    )
    return prompt | get_router_llm()


router_chain = build_router_chain()


def _infer_event_type(query: str) -> str | None:
    """Recover common ACLED event types when the LLM leaves the field empty."""
    text = query.casefold()
    event_types = (
        ("violence against civilians", "Violence against civilians"),
        ("explosions or remote violence", "Explosions/Remote violence"),
        ("explosions/remote violence", "Explosions/Remote violence"),
        ("remote violence", "Explosions/Remote violence"),
        ("protests", "Protests"),
        ("protest", "Protests"),
        ("battles", "Battles"),
        ("battle", "Battles"),
        ("riots", "Riots"),
        ("riot", "Riots"),
    )
    for phrase, event_type in event_types:
        if phrase in text:
            return event_type
    return None


def _infer_disorder_type(query: str) -> str | None:
    """Recover common ACLED disorder types if structured output parsing fails."""
    text = query.casefold()
    disorder_types = (
        ("political violence", "Political violence"),
        ("demonstrations", "Demonstrations"),
        ("demonstration", "Demonstrations"),
        ("strategic developments", "Strategic developments"),
        ("strategic development", "Strategic developments"),
    )
    for phrase, disorder_type in disorder_types:
        if phrase in text:
            return disorder_type
    return None


def _infer_time_granularity(query: str) -> str | None:
    text = query.casefold()
    if re.search(r"\bmonths?\b", text):
        return "month"
    if re.search(r"\bweeks?\b", text):
        return "week"
    if re.search(r"\byears?\b|\bannual\b", text):
        return "year"
    if re.search(r"\bdays?\b|\bdaily\b", text):
        return "day"
    return None


def _infer_ranking_metric(query: str) -> str | None:
    text = query.casefold()
    fatality_terms = (
        "most dangerous",
        "deadliest",
        "most violent",
        "highest death toll",
        "most lethal",
        "fatalities",
        "deaths",
        "killed",
        "casualties",
    )
    event_terms = (
        "most events",
        "most incidents",
        "most active",
        "highest number of events",
        "highest number of incidents",
    )
    if any(term in text for term in fatality_terms):
        return "fatalities"
    if any(term in text for term in event_terms):
        return "events"
    if any(term in text for term in ("most", "highest", "least", "lowest")):
        return "fatalities" if "civilian" in text or "danger" in text else "events"
    return None


def _infer_group_by(query: str) -> str | None:
    """Infer the requested breakdown for fallback routing."""
    text = query.casefold()
    actor_terms = (
        "armed group", "armed groups", "actors", "which group",
        "what group", "which faction", "what faction", "most associated with",
    )
    if any(term in text for term in actor_terms):
        return "actor1"
    if "year over year" in text or "by year" in text or "each year" in text:
        return "year"
    if "by region" in text or "trend of events by region" in text:
        return "region"
    if "by country" in text or "by countries" in text:
        return "country"
    return None


def _dimension_from_text(value: str) -> str | None:
    text = value.casefold().strip()
    if "sub-event" in text or "sub_event" in text:
        return "sub_event_type"
    if "event type" in text:
        return "event_type"
    if "actor" in text or "armed group" in text or "faction" in text:
        return "actor1"
    if "country" in text:
        return "country"
    if "region" in text:
        return "region"
    if "year" in text:
        return "year"
    if "month" in text:
        return "month"
    return None


def _infer_group_by_dimensions(query: str) -> list[str]:
    text = query.casefold()
    dimensions = []
    if "region-country-actor" in text:
        dimensions.extend(["region", "country", "actor1"])
    combination = re.search(
        r"(?:combination of|region-country-actor)\s+([^?]+)", text
    )
    if combination:
        source = combination.group(1).casefold()
        for name in ("region", "country", "actor", "sub-event type", "event type"):
            matches_sub_event = name == "sub-event type" and (
                "sub-event type" in source or "sub event type" in source
            )
            has_sub_event = "sub-event type" in source or "sub event type" in source
            matches_event = name == "event type" and "event type" in source and not has_sub_event
            if matches_event or matches_sub_event or (name not in ("event type", "sub-event type") and name in source):
                dimension = _dimension_from_text(name)
                if dimension and dimension not in dimensions:
                    dimensions.append(dimension)
    if "within each region" in text and "region" not in dimensions:
        dimensions.insert(0, "region")
    if "by country" in text and "country" not in dimensions:
        dimensions.append("country")
    if "broken down by actor" in text or "by actor type" in text:
        if "actor1" not in dimensions:
            dimensions.append("actor1")
    if "by sub-event" in text or "sub-event distribution" in text:
        if "sub_event_type" not in dimensions:
            dimensions.append("sub_event_type")
    if "by region" in text and "region" not in dimensions:
        dimensions.append("region")
    return dimensions


def _infer_comparison_entities(query: str) -> list[str]:
    text = query.strip()
    patterns = (
        r"between\s+([^,?.]+?)\s+and\s+([^,?.]+?)(?:\s+(?:by|for|broken|with)|[?.]|$)",
        r"e\.g\.?[,]?\s*([^,?.]+?)\s+and\s+([^,?.]+?)[).?]",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            values = [part.strip(" '()") for part in match.groups()]
            if all(values) and not any(value.casefold() in {"two", "x", "y"} for value in values):
                return values
    return []


def _infer_comparison_dimension(query: str) -> str | None:
    text = query.casefold()
    if re.search(r"between[^.?!]*\bregions?\b", text):
        return "region"
    if re.search(r"between[^.?!]*\bcountries?\b", text):
        return "country"
    if "armed group" in text or "actor" in text or "faction" in text:
        return "actor1"
    if "region" in text:
        return "region"
    if "country" in text:
        return "country"
    return None


def _infer_growth_metric(query: str) -> str | None:
    text = query.casefold()
    if "fastest growth" in text or "growth" in text:
        return "growth_pct"
    if "biggest increase" in text or "biggest decrease" in text or "largest increase" in text:
        return "delta"
    return None


def _infer_region(query: str) -> str | None:
    """Recover common region filters for fallback routing."""
    text = query.casefold()
    regions = {
        "middle east": "Middle East",
        "north africa": "North Africa",
        "western africa": "Western Africa",
        "eastern africa": "Eastern Africa",
        "southern africa": "Southern Africa",
        "central africa": "Central Africa",
        "sahel": "Sahel",
    }
    for phrase, region in regions.items():
        if phrase in text:
            return region
    return None


def _infer_query_type(query: str, current: str) -> str:
    text = query.casefold()
    has_ranking = _infer_ranking_metric(query) is not None
    has_comparison = "compare" in text or "comparison" in text
    has_growth = _infer_growth_metric(query) is not None
    has_narrative = any(
        phrase in text
        for phrase in ("what happened", "tell me about", "describe", "main patterns", "what were")
    )
    if has_ranking and has_narrative:
        return "HYBRID"
    if has_ranking or has_comparison or has_growth:
        return "STRUCTURED"
    return current


def _fallback_route_query(query: str) -> RouterOutput:
    """Build a minimal structured route when the provider returns invalid JSON."""
    text = query.casefold()
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    date_from = date_to = None
    if years:
        date_from = f"{years[0]}-01-01"
        date_to = f"{years[-1]}-12-31"

    if any(term in text for term in (
        "how many", "highest", "most", "number of", "count", "trend",
        "show the trend", "year over year", "break down", "by country",
        "by region", "combination of",
    )):
        query_type = "STRUCTURED"
    else:
        query_type = "SEMANTIC"

    return RouterOutput(
        query_type=_infer_query_type(query, query_type),
        date_from=date_from,
        date_to=date_to,
        event_type=_infer_event_type(query),
        disorder_type=_infer_disorder_type(query),
        region=_infer_region(query),
        time_granularity=_infer_time_granularity(query),
        ranking_metric=_infer_ranking_metric(query),
        group_by=_infer_group_by(query),
        group_by_dimensions=_infer_group_by_dimensions(query),
        comparison_entities=_infer_comparison_entities(query),
        comparison_dimension=_infer_comparison_dimension(query),
        growth_metric=_infer_growth_metric(query),
        civilian_targeting=("Civilian targeting" if "civilian" in text else None),
    )


def route_query(query: str) -> RouterOutput:
    """Classify a user query and extract structured filters."""
    try:
        output = router_chain.invoke({"query": query})
    except Exception as exc:
        if "tool_use_failed" not in str(exc) and "invalid_request_error" not in str(exc):
            raise
        output = _fallback_route_query(query)
    if output.event_type is None:
        inferred_event_type = _infer_event_type(query)
        if inferred_event_type is not None:
            output = output.model_copy(update={"event_type": inferred_event_type})
    updates = {
        "query_type": _infer_query_type(query, output.query_type),
        "time_granularity": output.time_granularity or _infer_time_granularity(query),
        "ranking_metric": output.ranking_metric or _infer_ranking_metric(query),
        "group_by": output.group_by or _infer_group_by(query),
        "group_by_dimensions": output.group_by_dimensions or _infer_group_by_dimensions(query),
        "comparison_entities": output.comparison_entities or _infer_comparison_entities(query),
        "comparison_dimension": output.comparison_dimension or _infer_comparison_dimension(query),
        "growth_metric": output.growth_metric or _infer_growth_metric(query),
        "region": output.region or _infer_region(query),
        "civilian_targeting": output.civilian_targeting
        or ("Civilian targeting" if "civilian" in query.casefold() else None),
    }
    output = output.model_copy(update=updates)
    return output


if __name__ == "__main__":
    test_queries = [
        "How many violence against civilians events occurred in Algeria between 2018 and 2020?",
        "Which year had the most violence against civilians?",
        "What actors were involved in armed clashes in Sudan?",
        "How many civilians were killed in Algeria and what were the main types of violence?",
        "How many battles involving Russian forces occurred in Ukraine?",
    ]

    for query in test_queries:
        print("=" * 80)
        print(query)
        result = route_query(query)
        print(result.model_dump())
