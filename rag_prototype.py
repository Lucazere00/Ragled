from dotenv import load_dotenv

load_dotenv()
import re
from typing import Literal

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "acled_events"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DatasetRoute = Literal["acled", "usa_iran_conflict", "ambiguous"]

USA_IRAN_STRONG_TERMS = {
    "iran",
    "iranian",
    "tehran",
    "irgc",
    "islamic revolutionary guard",
    "quds force",
    "usa-iran",
    "us-iran",
    "u.s.-iran",
    "united states and iran",
    "iran and the united states",
    "persian gulf",
    "strait of hormuz",
    "hormuz",
    "gulf of oman",
    "dubai",
    "dubai airport",
    "houthi",
    "houthis",
}

USA_TERMS = {
    "usa",
    "u.s.",
    "us",
    "united states",
    "america",
    "american",
}

USA_IRAN_REGION_TERMS = {
    "middle east",
    "iraq",
    "syria",
    "yemen",
    "oman",
    "qatar",
    "bahrain",
    "kuwait",
    "saudi arabia",
    "united arab emirates",
    "uae",
    "gulf",
}

USA_IRAN_BASE_TERMS = {
    "us military base",
    "u.s. military base",
    "american military base",
    "us forces",
    "u.s. forces",
    "american forces",
    "al asad",
    "al-asad",
    "ain al-asad",
    "al udeid",
    "al-udeid",
    "al dhafra",
    "al-dhafra",
    "al tanf",
    "al-tanf",
    "camp taji",
    "erbil air base",
    "tower 22",
}

ACLED_SOURCE_TERMS = {
    "acled",
    "algeria",
    "sudan",
    "mali",
    "ukraine",
    "nigeria",
    "ethiopia",
    "somalia",
    "civilian",
    "civilians",
    "protest",
    "protests",
    "riot",
    "riots",
    "battle",
    "battles",
    "armed clash",
    "violence against civilians",
}


def get_vectorstore():
    """
    Si aggancia alla collection ChromaDB già popolata da indexing.py,
    usando lo stesso embedding model per coerenza tra query e documenti.
    """
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH,
    )

    return vectorstore


def format_docs(docs):
    """
    Trasforma i documenti recuperati in un unico blocco di testo
    da inserire nel prompt come contesto.
    """
    return "\n\n".join(
        f"- {doc.page_content}" for doc in docs
    )


def _contains_term(text: str, term: str) -> bool:
    pattern = r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)"
    return re.search(pattern, text) is not None


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(_contains_term(text, term) for term in terms)


def classify_semantic_dataset(query: str) -> DatasetRoute:
    """
    Classify which semantic corpus should be favored for a single query.

    The classifier is intentionally lightweight: it uses transparent keyword
    signals and leaves generic conflict questions on the original ACLED path.
    """
    query_text = query.lower()

    has_strong_usa_iran_signal = _contains_any(query_text, USA_IRAN_STRONG_TERMS)
    has_us_signal = _contains_any(query_text, USA_TERMS)
    has_region_signal = _contains_any(query_text, USA_IRAN_REGION_TERMS)
    has_base_signal = _contains_any(query_text, USA_IRAN_BASE_TERMS)
    has_acled_signal = _contains_any(query_text, ACLED_SOURCE_TERMS)

    has_usa_iran_signal = (
        has_strong_usa_iran_signal
        or has_base_signal
        or (has_us_signal and has_region_signal)
    )

    if has_usa_iran_signal and "acled" in query_text:
        return "ambiguous"

    if has_usa_iran_signal and has_acled_signal:
        acled_terms_outside_conflict = {
            "algeria",
            "sudan",
            "mali",
            "ukraine",
            "nigeria",
            "ethiopia",
            "somalia",
        }
        if _contains_any(query_text, acled_terms_outside_conflict):
            return "ambiguous"

    if has_usa_iran_signal:
        return "usa_iran_conflict"

    return "acled"


def _dedupe_documents(docs):
    unique_docs = []
    seen = set()

    for doc in docs:
        metadata = doc.metadata or {}
        key = (
            metadata.get("id")
            or metadata.get("event_id_cnty")
            or metadata.get("source_id")
            or (doc.page_content, tuple(sorted(metadata.items())))
        )
        if key in seen:
            continue

        seen.add(key)
        unique_docs.append(doc)

    return unique_docs


def _similarity_search(vectorstore, query: str, k: int, dataset: str | None = None):
    if k <= 0:
        return []

    if dataset is None:
        return vectorstore.similarity_search(query, k=k)

    return vectorstore.similarity_search(
        query,
        k=k,
        filter={"dataset": dataset},
    )


def get_semantic_documents_v2(query: str, k: int = 5):
    """
    Retrieve semantic documents with per-query dataset routing.

    - acled: original unfiltered retrieval, preserving existing behavior.
    - usa_iran_conflict: filtered retrieval against the small USA-Iran corpus.
    - ambiguous: balanced retrieval from USA-Iran plus unfiltered results.
    """
    vectorstore = get_vectorstore()
    dataset_route = classify_semantic_dataset(query)

    if dataset_route == "acled":
        return _similarity_search(vectorstore, query, k=k)

    if dataset_route == "usa_iran_conflict":
        return _similarity_search(
            vectorstore,
            query,
            k=k,
            dataset="usa_iran_conflict",
        )

    usa_iran_k = max(1, k // 2)
    unfiltered_k = max(0, k - usa_iran_k)
    docs = [
        *_similarity_search(
            vectorstore,
            query,
            k=usa_iran_k,
            dataset="usa_iran_conflict",
        ),
        *_similarity_search(vectorstore, query, k=unfiltered_k),
    ]
    return _dedupe_documents(docs)[:k]


def build_rag_chain(k=5):
    vectorstore = get_vectorstore()

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": k}
    )

    prompt = ChatPromptTemplate.from_template(
        """You are an assistant answering questions about armed conflict events (ACLED data).

Use ONLY the context below to answer the question.
If the context doesn't contain enough information, say so explicitly instead of guessing.

Context:
{context}

Question: {question}

Answer:"""
    )

    # Llama tramite Groq
    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0
    )

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


def get_semantic_context(query: str, k: int = 5) -> str:
    vectorstore = get_vectorstore()

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": k}
    )

    docs = retriever.invoke(query)
    return format_docs(docs)


def get_semantic_context_v2(query: str, k: int = 5) -> str:
    docs = get_semantic_documents_v2(query, k=k)
    return format_docs(docs)


def build_hybrid_chain():
    prompt = ChatPromptTemplate.from_template(
        """You are an assistant answering questions about armed conflict events (ACLED data).

You will receive two different sources of context:
- Structured context: aggregated quantitative data such as counts, fatalities, and breakdowns.
- Semantic context: retrieved event descriptions and qualitative details.

Compose one coherent answer that integrates both sources.
Use the structured context for all numerical and statistical claims.
Use the semantic context for descriptions, interpretation, and concrete event examples when relevant.
Do not invent numbers that are not present in the structured context.
Base qualitative descriptions only on the semantic context.
If either source lacks the information needed for part of the question, say so explicitly.

Structured context:
{structured_context}

Semantic context:
{semantic_context}

Question: {question}

Answer:"""
    )

    # Llama tramite Groq
    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0
    )

    chain = prompt | llm | StrOutputParser()

    return chain


if __name__ == "__main__":
    chain = build_rag_chain(k=5)

    query = "What kind of violence against civilians happened in Algeria?"

    response = chain.invoke(query)

    print("Query:", query)
    print("\nResponse:\n", response)
