"""Evaluate the ACLED RAG pipeline with RAGAS.

Install the additional dependencies with::

    pip install ragas datasets

The script deliberately excludes STRUCTURED-only questions because they do
not produce a meaningful semantic retrieval context.
"""

from __future__ import annotations

import math
import time
from statistics import mean
from typing import Any

import pandas as pd
from datasets import Dataset

from main import run_pipeline
from rag_prototype import build_rag_chain, get_vectorstore
from router import route_query


METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)
CSV_PATH = "ragas_evaluation_results.csv"


EVALUATION_DATASET = [
    {
        "question": "What patterns of violence against civilians are commonly reported in Mali?",
        "ground_truth": "Reports from Mali commonly describe attacks, killings, intimidation, arbitrary detention, and destruction affecting civilian communities. State forces and armed groups both appear in these patterns, often amid communal and insurgent violence.",
        "category": "SEMANTIC",
    },
    {
        "question": "Which actors were involved in armed clashes in Nigeria, and what were the main circumstances?",
        "ground_truth": "Armed clashes in Nigeria commonly involve government security forces, insurgent groups, militias, and communal armed actors. They are often linked to counterinsurgency operations, territorial disputes, and competition over land or local authority.",
        "category": "SEMANTIC",
    },
    {
        "question": "What kinds of events involving civilians were reported in Myanmar?",
        "ground_truth": "Reports from Myanmar include attacks on villages, shelling, displacement, arrests, and other abuses against civilians. The events are associated with fighting between the military, ethnic armed organizations, and resistance forces.",
        "category": "SEMANTIC",
    },
    {
        "question": "Describe the role of protests and riots in Colombia's political violence.",
        "ground_truth": "Protests in Colombia can become part of broader political violence when security forces, demonstrators, or armed groups use force. Riots and clashes often reflect disputes over government policy, inequality, and local political tensions.",
        "category": "SEMANTIC",
    },
    {
        "question": "What forms of violence against civilians have been observed in Sudan?",
        "ground_truth": "Violence against civilians in Sudan includes killings, attacks on settlements, forced displacement, looting, and abductions. These incidents may involve the national army, paramilitary forces, militias, or other armed groups.",
        "category": "SEMANTIC",
    },
    {
        "question": "What actors and event types are associated with conflict in Yemen?",
        "ground_truth": "Conflict events in Yemen involve the Houthi movement, government-aligned forces, coalition actors, and local armed groups. Common event types include battles, air or missile strikes, shelling, and violence against civilians.",
        "category": "SEMANTIC",
    },
    {
        "question": "How did explosions or remote violence affect civilians in Ukraine?",
        "ground_truth": "Explosions and remote violence in Ukraine have affected civilians through missile strikes, artillery fire, and attacks on populated areas or infrastructure. The consequences include deaths, injuries, displacement, and disruption of essential services.",
        "category": "SEMANTIC",
    },
    {
        "question": "What was the context of attacks attributed to armed groups in Somalia?",
        "ground_truth": "Attacks by armed groups in Somalia are commonly connected to insurgency, territorial control, and pressure on government or civilian targets. Al-Shabaab and state or allied forces are frequent actors in this context.",
        "category": "SEMANTIC",
    },
    {
        "question": "What types of political violence were reported in Ethiopia?",
        "ground_truth": "Political violence in Ethiopia includes armed clashes, attacks on civilians, communal conflict, protests, and security-force operations. The pattern varies by region and is shaped by ethnic, political, and territorial disputes.",
        "category": "SEMANTIC",
    },
    {
        "question": "How are civilians affected by conflict events in Syria?",
        "ground_truth": "Syrian civilians are affected by airstrikes, shelling, ground fighting, arrests, displacement, and attacks on homes or public facilities. The actors include government forces, opposition groups, international forces, and other armed organizations.",
        "category": "SEMANTIC",
    },
    {
        "question": "What patterns characterize battles between armed actors in the Central African Republic?",
        "ground_truth": "Battles in the Central African Republic often involve government forces, rebel coalitions, and local militias competing for territory and political influence. Fighting can occur near towns and is frequently accompanied by civilian displacement or property destruction.",
        "category": "SEMANTIC",
    },
    {
        "question": "What types of conflict events have been reported in Afghanistan?",
        "ground_truth": "Conflict reporting from Afghanistan includes armed clashes, bombings, targeted attacks, airstrikes, and violence against civilians. The principal actors have included the Taliban, government forces, international forces, and Islamic State affiliates.",
        "category": "SEMANTIC",
    },
    {
        "question": "How do state forces and non-state groups interact in conflict events in Iraq?",
        "ground_truth": "Iraq's conflict events include clashes and attacks involving state security forces, militias, insurgent groups, and international actors. Their interaction ranges from counterinsurgency operations to attacks on bases, checkpoints, and civilian areas.",
        "category": "SEMANTIC",
    },
    {
        "question": "What contextual factors help explain violence against civilians in Burkina Faso?",
        "ground_truth": "Violence against civilians in Burkina Faso is often linked to jihadist insurgency, local self-defense groups, military operations, and communal tensions. Attacks and reprisals can produce killings, displacement, and restrictions on civilian movement.",
        "category": "SEMANTIC",
    },
    {
        "question": "Which month had the most explosions or remote violence in Ukraine in 2022, and what happened during that period?",
        "ground_truth": "The peak month should be identified from the Ukraine 2022 event counts, with the associated narrative describing the major missile, artillery, or infrastructure attacks recorded in that month. The reference emphasizes both the winning month and the civilian or strategic consequences reported then.",
        "category": "HYBRID",
    },
    {
        "question": "Tell me about the most dangerous year for civilians in Syria.",
        "ground_truth": "The most dangerous year is the year with the highest recorded civilian fatalities or violence-against-civilians burden in the available data. Its narrative would typically involve intensified attacks, displacement, and abuses by several armed actors.",
        "category": "HYBRID",
    },
    {
        "question": "What was the deadliest month for civilians in Yemen in 2021, and what happened during that period?",
        "ground_truth": "The deadliest month should be determined by civilian fatalities in Yemen during 2021. The accompanying account should describe the principal battles, airstrikes, shelling, or attacks on civilians that drove the peak.",
        "category": "HYBRID",
    },
    {
        "question": "Which year had the most violence against civilians in Sudan, and what characterized that year?",
        "ground_truth": "The winning year is the year with the largest count of violence-against-civilians events in Sudan. It would be characterized by repeated attacks on communities, displacement, and escalation among state, paramilitary, and local armed actors.",
        "category": "HYBRID",
    },
    {
        "question": "Which month had the most battles in Mali in 2020, and what were the main events?",
        "ground_truth": "The peak month should be selected from the number of battles recorded in Mali in 2020. The narrative should summarize the main clashes and the armed actors involved during that month.",
        "category": "HYBRID",
    },
    {
        "question": "What was the deadliest year for civilians in Nigeria, and what happened during that year?",
        "ground_truth": "The deadliest year is the year with the highest civilian-fatality total in the Nigerian records. The contextual explanation should cover major insurgent, communal, or security-force violence affecting civilians during that period.",
        "category": "HYBRID",
    },
    {
        "question": "Which region had the most violence against civilians in Myanmar, and what characterized the events there?",
        "ground_truth": "The leading region should be identified by its count of violence-against-civilians events. Its narrative would likely include attacks on settlements, displacement, arrests, and clashes between the military, ethnic organizations, and resistance forces.",
        "category": "HYBRID",
    },
    {
        "question": "Which year had the most explosions in Colombia, and what happened during that year?",
        "ground_truth": "The peak year should be based on the number of explosions recorded in Colombia. The narrative should describe the principal attacks, targets, and actors associated with that period.",
        "category": "HYBRID",
    },
]


def _as_text(response: Any) -> str:
    """Extract answer text from either a string or the pipeline result dict."""
    if isinstance(response, dict):
        return str(response.get("answer", response.get("text", response)))
    return str(response)


def validate_classification(dataset: list[dict[str, str]]) -> list[dict[str, str]]:
    """Compare expected categories with the live router and report mismatches."""
    mismatches = []
    for item in dataset:
        try:
            actual = str(route_query(item["question"]).query_type).upper()
        except Exception as exc:
            actual = f"ERROR: {exc}"
        expected = item["category"].upper()
        if actual != expected:
            mismatch = {
                "question": item["question"],
                "expected": expected,
                "actual": actual,
            }
            mismatches.append(mismatch)
            print(
                f"[WARNING] Classification mismatch: {item['question']} | "
                f"expected={expected}, actual={actual}"
            )
    return mismatches


def _retrieve_contexts(question: str, k: int = 5) -> list[str]:
    """Retrieve individual page contents for RAGAS context metrics."""
    retriever = get_vectorstore().as_retriever(search_kwargs={"k": k})
    documents = retriever.invoke(question)
    return [str(document.page_content) for document in documents]


def collect_evaluation_data(
    dataset: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[tuple[str, str, float]]]:
    """Generate answers and contexts, isolating failures to individual items."""
    evaluation_data = []
    execution_times = []

    for item in dataset:
        question = item["question"]
        category = item["category"].upper()
        started = time.perf_counter()
        try:
            if category == "SEMANTIC":
                contexts = _retrieve_contexts(question)
                answer = _as_text(build_rag_chain(k=5).invoke(question))
            elif category == "HYBRID":
                contexts = _retrieve_contexts(question)
                answer = _as_text(run_pipeline(question))
            else:
                raise ValueError(f"Unsupported evaluation category: {category}")

            elapsed = time.perf_counter() - started
            evaluation_data.append(
                {
                    "question": question,
                    "answer": answer,
                    "contexts": contexts,
                    "ground_truth": item["ground_truth"],
                    "category": category,
                }
            )
            execution_times.append((question, category, elapsed))
            print(f"[OK] {category}: {question} ({elapsed:.2f}s)")
        except Exception as exc:
            print(f"[WARNING] Skipping {category} question {question!r}: {exc}")

    return evaluation_data, execution_times


def _ragas_models():
    """Create the existing Groq model and local embedding model for RAGAS."""
    from langchain_groq import ChatGroq
    from langchain_huggingface import HuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper

    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return LangchainLLMWrapper(llm), LangchainEmbeddingsWrapper(embeddings)


def run_ragas_evaluation(evaluation_data: list[dict[str, Any]]):
    """Run the four requested RAGAS metrics and return its EvaluationResult."""
    if not evaluation_data:
        raise ValueError("No evaluation data available for RAGAS.")

    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    ragas_dataset = Dataset.from_list(
        [
            {
                "question": item["question"],
                "answer": item["answer"],
                "contexts": item["contexts"],
                "ground_truth": item["ground_truth"],
            }
            for item in evaluation_data
        ]
    )
    llm, embeddings = _ragas_models()
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    try:
        return evaluate(
            ragas_dataset,
            metrics=metrics,
            llm=llm,
            embeddings=embeddings,
            raise_exceptions=False,
        )
    except Exception as exc:
        raise RuntimeError(f"RAGAS evaluation failed: {exc}") from exc


def _metric_value(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if not math.isnan(numeric) else None


def _print_metric_summary(frame: pd.DataFrame, label: str) -> None:
    print(f"\n{label} metrics")
    for metric in METRIC_NAMES:
        values = [_metric_value(value) for value in frame.get(metric, [])]
        values = [value for value in values if value is not None]
        if values:
            print(f"  {metric}: {mean(values):.3f}")
        else:
            print(f"  {metric}: N/A (metric failed or returned no score)")


def print_evaluation_report(
    ragas_result: Any,
    execution_times: list[tuple[str, str, float]],
    evaluation_data: list[dict[str, Any]],
    classification_mismatches: list[dict[str, str]],
) -> None:
    """Print aggregate/per-category metrics, timings, mismatches, and save CSV."""
    try:
        frame = ragas_result.to_pandas()
    except Exception as exc:
        print(f"[WARNING] Could not convert RAGAS result to pandas: {exc}")
        return

    categories = pd.DataFrame(
        [{"category": item["category"]} for item in evaluation_data]
    )
    frame = frame.reset_index(drop=True)
    frame["category"] = categories["category"].reindex(frame.index).values

    _print_metric_summary(frame, "Overall")
    for category in ("SEMANTIC", "HYBRID"):
        _print_metric_summary(frame[frame["category"] == category], category)

    print("\nExecution times")
    for category in ("SEMANTIC", "HYBRID"):
        values = [elapsed for _, current, elapsed in execution_times if current == category]
        if values:
            print(
                f"  {category}: mean={mean(values):.2f}s, "
                f"min={min(values):.2f}s, max={max(values):.2f}s"
            )
        else:
            print(f"  {category}: N/A")

    print(f"\nClassification mismatches: {len(classification_mismatches)}")
    for mismatch in classification_mismatches:
        print(
            f"  {mismatch['question']} | expected={mismatch['expected']} | "
            f"actual={mismatch['actual']}"
        )

    columns = ["question", "category", *METRIC_NAMES]
    available_columns = [column for column in columns if column in frame]
    detail = frame[available_columns].copy()
    detail["question"] = detail["question"].astype(str).str.slice(0, 60)
    print("\nPer-question scores")
    print(detail.to_string(index=False))

    frame.to_csv(CSV_PATH, index=False)
    print(f"\nSaved complete results to {CSV_PATH}")


if __name__ == "__main__":
    print("Starting ACLED RAGAS evaluation...")
    mismatches = validate_classification(EVALUATION_DATASET)
    collected_data, timings = collect_evaluation_data(EVALUATION_DATASET)
    result = run_ragas_evaluation(collected_data)
    print_evaluation_report(result, timings, collected_data, mismatches)
    print(f"Evaluation completed. CSV available at {CSV_PATH}")