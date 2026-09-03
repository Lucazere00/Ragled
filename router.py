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


def route_query(query: str) -> RouterOutput:
    """Classify a user query and extract structured filters."""
    return router_chain.invoke({"query": query})


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
