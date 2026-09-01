from dotenv import load_dotenv

# Carica GROQ_API_KEY dal file .env
load_dotenv()

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Optional, Literal


# ============================================================
# OUTPUT DEL ROUTER
# ============================================================

class RouterOutput(BaseModel):
    query_type: Literal["STRUCTURED", "SEMANTIC", "HYBRID"] = Field(
        description=(
            "STRUCTURED if the answer requires a calculation or aggregation "
            "over data (counts, sums, averages, trends, comparisons, rankings). "
            "SEMANTIC if the answer requires understanding or summarizing "
            "the content or context of events. "
            "HYBRID if the answer requires both a calculation and a "
            "description/summary."
        )
    )

    country: Optional[str] = Field(
        default=None,
        description="Country explicitly mentioned in the query, if any."
    )

    date_from: Optional[str] = Field(
        default=None,
        description=(
            "Start date in YYYY-MM-DD format, if an explicit date or "
            "year/range is mentioned."
        )
    )

    date_to: Optional[str] = Field(
        default=None,
        description=(
            "End date in YYYY-MM-DD format, if an explicit date or "
            "year/range is mentioned."
        )
    )

    event_type: Optional[str] = Field(
        default=None,
        description=(
            "Event type explicitly mentioned in the query, if any "
            "(e.g. 'Violence against civilians', 'Battles')."
        )
    )

    disorder_type: Optional[str] = Field(
        default=None,
        description=(
            "Macro-level ACLED disorder category, if explicitly mentioned "
            "(e.g. 'Political violence', 'Strategic developments', "
            "'Demonstrations')."
        )
    )

    sub_event_type: Optional[str] = Field(
        default=None,
        description=(
            "Specific ACLED sub-event category, more detailed than event_type, "
            "if explicitly mentioned (e.g. 'Armed clash', "
            "'Looting/property destruction', 'Attack', 'Peaceful protest')."
        )
    )


# ============================================================
# SYSTEM PROMPT
# ============================================================

ROUTER_SYSTEM_PROMPT = """
You are a query router for a system analyzing ACLED conflict event data.

Your task is to classify a user question into exactly one of three types:

------------------------------------------------------------
1. STRUCTURED
------------------------------------------------------------

Use STRUCTURED when answering the question requires a calculation,
aggregation, filtering, comparison, ranking, or numerical analysis
over the ACLED dataset.

Examples:

- "How many events occurred in Sudan in 2023?"
- "How many civilians were killed in Algeria?"
- "Which year had the most violence against civilians?"
- "Which country had the highest number of battles?"
- "How did fatalities change over the last 5 years?"

These questions require querying and calculating over the dataset.

------------------------------------------------------------
2. SEMANTIC
------------------------------------------------------------

Use SEMANTIC when answering the question requires understanding,
retrieving, or summarizing the CONTENT of ACLED events.

Examples:

- "What kind of violence against civilians occurred in Algeria?"
- "What happened during the attacks on schools in Nigeria?"
- "What tactics were used by group X?"
- "What actors were involved in armed clashes in Sudan?"

These questions do NOT require a numerical calculation.

------------------------------------------------------------
3. HYBRID
------------------------------------------------------------

Use HYBRID when answering the question requires BOTH:

1. a calculation/aggregation over the dataset
AND
2. a semantic description, explanation, or summary.

Examples:

- "How many civilians were killed in Algeria and what were the main
  types of violence?"
- "Describe the violence in the year with the highest number of events."
- "Which country had the most battles and what were the main actors involved?"

------------------------------------------------------------
IMPORTANT CLASSIFICATION RULE
------------------------------------------------------------

Do NOT classify questions only by looking for keywords such as
"how many", "what", or "which".

Reason about what the answer actually requires.

For example:

"Which year had the most violence against civilians?"

must be STRUCTURED because it requires calculating and comparing
the number of events for different years.

"Describe the violence in the year with the highest number of events."

must be HYBRID because:

1. the year with the highest number of events must first be calculated;
2. then the violence during that year must be semantically described.

------------------------------------------------------------
FILTER EXTRACTION
------------------------------------------------------------

Also extract the following information when explicitly mentioned:

- country
- date_from
- date_to
- event_type
- disorder_type
- sub_event_type

Country:
Return the country name mentioned in the query.

Dates:
Return dates using YYYY-MM-DD format.

If only a year is explicitly mentioned, convert it to:

2023 → date_from = "2023-01-01"
       date_to   = "2023-12-31"

If an explicit range is mentioned:

2018 to 2020 →
date_from = "2018-01-01"
date_to   = "2020-12-31"

Only extract dates that are explicitly stated or clearly represented
as explicit years/ranges in the query.

DO NOT invent dates.

DO NOT infer exact dates from vague expressions such as:

- "recently"
- "recent years"
- "the last few years"

For such expressions, leave date_from and date_to as null.

ACLED event hierarchy:
ACLED has three event classification levels:

1. disorder_type: broad macro category.
   Examples: "Political violence", "Strategic developments",
   "Demonstrations"

2. event_type: intermediate category.
   Examples: "Battles", "Violence against civilians", "Protests",
   "Explosions/Remote violence", "Strategic developments", "Riots"

3. sub_event_type: specific detailed category.
   Examples: "Armed clash", "Looting/property destruction", "Attack",
   "Peaceful protest"

Extract the correct level based on how specific the user's term is.

Generic terms such as "political violence" should be extracted as
disorder_type.

Intermediate terms such as "battles" or "protests" should be extracted as
event_type.

Very specific terms such as "armed clash" or "looting" should be extracted as
sub_event_type.

More than one level may be extracted at the same time if the query justifies
it. Fields that are not mentioned or cannot be reliably inferred must remain
null.

Event type:
Extract the event type if it is explicitly mentioned.

Examples:

"violence against civilians" →
"Violence against civilians"

"battles" →
"Battles"

When extracting event_type, preserve the exact spacing and wording.
For example, always write "Violence against civilians", never
"Violence againstcivilians".

If a field is not mentioned or cannot be reliably inferred,
return null.

------------------------------------------------------------
OUTPUT
------------------------------------------------------------

Return only the structured RouterOutput object.
"""


# ============================================================
# ROUTER LLM
# ============================================================

def get_router_llm():
    """
    Creates the Groq LLM used by the router.

    GPT-OSS 20B is used for query classification and
    structured output extraction.
    """

    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0
    )

    return llm.with_structured_output(RouterOutput)


# ============================================================
# BUILD ROUTER CHAIN
# ============================================================

def build_router_chain():
    """
    Builds the router chain.
    """

    llm = get_router_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", ROUTER_SYSTEM_PROMPT),
        ("human", "{query}"),
    ])

    return prompt | llm


# ============================================================
# BUILD THE ROUTER ONLY ONCE
# ============================================================

router_chain = build_router_chain()


# ============================================================
# ROUTE QUERY
# ============================================================

def route_query(query: str) -> RouterOutput:
    """
    Classifies a user query and extracts useful filters.
    """

    return router_chain.invoke({
        "query": query
    })


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_queries = [

        # ----------------------------------------------------
        # STRUCTURED
        # ----------------------------------------------------

        "How many violence against civilians events occurred in Algeria between 2018 and 2020?",

        "How many events occurred in Algeria?",

        "Which year had the most violence against civilians?",

        "How many political violence events occurred in Sudan?",

        "How many armed clashes happened in Mali in 2022?",

        "How many battles occurred in Ukraine?",

        # ----------------------------------------------------
        # SEMANTIC
        # ----------------------------------------------------

        "What kind of violence against civilians occurred in Algeria?",

        "What happened in Algeria?",

        "What actors were involved in armed clashes in Sudan?",

        # ----------------------------------------------------
        # HYBRID
        # ----------------------------------------------------

        "How many civilians were killed in Algeria and what were the main types of violence?",

        "Describe the violence against civilians in the year with the highest number of events.",

        "Which country had the most battles and what were the main actors involved?",
    ]


    print("=" * 80)
    print("ACLED QUERY ROUTER TEST")
    print("=" * 80)


    for i, query in enumerate(test_queries, 1):

        print(f"\n{'-' * 80}")
        print(f"TEST {i}")
        print(f"{'-' * 80}")

        print(f"Query: {query}")

        try:

            result = route_query(query)

            print("\nRouter output:")
            print(result.model_dump())

            print("\nClassification:")
            print(f"  Query type : {result.query_type}")
            print(f"  Country    : {result.country}")
            print(f"  Date from  : {result.date_from}")
            print(f"  Date to    : {result.date_to}")
            print(f"  Event type : {result.event_type}")
            print(f"  Disorder   : {result.disorder_type}")
            print(f"  Sub-event  : {result.sub_event_type}")

        except Exception as e:

            print("\nERROR:")
            print(e)


    print("\n" + "=" * 80)
    print("ROUTER TEST COMPLETED")
    print("=" * 80)
