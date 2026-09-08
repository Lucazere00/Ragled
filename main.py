from rag_prototype import (
    build_hybrid_chain,
    build_rag_chain,
    build_semantic_chart,
    get_semantic_context,
    get_semantic_context_v2,
    get_semantic_documents_v2,
)
from router import route_query
from structured import run_structured_query


EMPTY_STRUCTURED_CONTEXT = "No structured data available for these filters."
EMPTY_SEMANTIC_CONTEXT = "No relevant documents found."


def _format_optional(value):
    """Return a readable representation for optional router fields."""
    return value if value is not None else "None"


def _format_date_range(date_from, date_to):
    """Return a readable date range for the router output."""
    if date_from is None and date_to is None:
        return "None"

    return f"{_format_optional(date_from)} - {_format_optional(date_to)}"


def _ensure_context(value, placeholder):
    """Return a non-empty context string for downstream prompts."""
    if value is None:
        return placeholder

    value = str(value)
    if not value.strip():
        return placeholder

    return value


def run_pipeline(query: str) -> str | dict:
    """
    Orchestrate the RAG pipeline for a user query.

    The router decides whether the query should be handled by semantic RAG,
    a structured path, or a future hybrid path.
    """
    router_output = route_query(query)

    print("[ROUTER]")
    print(f"Query type: {router_output.query_type}")
    print(f"Country: {_format_optional(router_output.country)}")
    print(
        "Date range: "
        f"{_format_date_range(router_output.date_from, router_output.date_to)}"
    )
    print(f"Event type: {_format_optional(router_output.event_type)}")

    if router_output.query_type == "SEMANTIC":
        print("\n[SEMANTIC RAG]")
        documents = get_semantic_documents_v2(query)
        chain = build_rag_chain(docs=documents)
        response = chain.invoke(query)
        print("\n[RESPONSE]")
        print(response)
        chart = build_semantic_chart(documents, query)
        chart_message = None if chart else "Dati insufficienti per generare un grafico."
        return {
            "type": "semantic",
            "answer": str(response),
            "chart": chart,
            "chart_message": chart_message,
        }

    if router_output.query_type == "STRUCTURED":
        print("\n[STRUCTURED]")
        result = run_structured_query(router_output, query)
        response = result["text"]
        print("\n[RESPONSE]")
        print(response)
        if result["chart"]:
            print(f"[CHART] Saved to {result['chart']['path']}")
        return {"type": "structured", "answer": response, "chart": result["chart"]}

    if router_output.query_type == "HYBRID":
        print("\n[HYBRID]")
        print("\n[STRUCTURED PART]")
        structured_result = run_structured_query(router_output, query)
        structured_context = _ensure_context(
            structured_result["text"],
            EMPTY_STRUCTURED_CONTEXT,
        )
        print(structured_context)

        print("\n[SEMANTIC PART]")
        ranking = structured_result.get("ranking") or {}
        semantic_context = _ensure_context(
            get_semantic_context_v2(
                query,
                country=router_output.country,
                period=ranking.get("winner"),
                granularity=ranking.get("dimension"),
            ),
            EMPTY_SEMANTIC_CONTEXT,
        )
        print(semantic_context[:300])

        print("\n[COMBINING]")
        chain = build_hybrid_chain()
        response = chain.invoke(
            {
                "structured_context": structured_context,
                "semantic_context": semantic_context,
                "question": query,
            }
        )

        if response is None or not str(response).strip():
            print("[WARNING] Hybrid chain returned an empty response.")

        print("\n[RESPONSE]")
        print(response)
        if structured_result["chart"]:
            print(f"[CHART] Saved to {structured_result['chart']['path']}")
        return {
            "type": "hybrid",
            "answer": str(response),
            "chart": structured_result["chart"],
        }

    raise ValueError(f"Unsupported query type: {router_output.query_type}")


if __name__ == "__main__":
    test_queries = [
        "What kind of violence against civilians occurred in Algeria?",
        "What actors were involved in armed clashes in Sudan?",
        "How many events occurred in Sudan?",
        "How many armed clashes happened in Mali in 2022?",
        "How many political violence events occurred in total?",
        "How many violence against civilians events occurred in Algeria between 2018 and 2020?",
        "Which year had the most violence against civilians?",
        "How many civilians were killed in Algeria and what were the main types of violence?",
        "Which country had the most battles and what were the main actors involved?",
    ]

    for query in test_queries:
        print("=" * 80)
        print(f"Query: {query}")
        print("=" * 80)
        run_pipeline(query)
        print()
