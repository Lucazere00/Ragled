from dotenv import load_dotenv

load_dotenv()
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "acled_events"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


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


if __name__ == "__main__":
    chain = build_rag_chain(k=5)

    query = "What kind of violence against civilians happened in Algeria?"

    response = chain.invoke(query)

    print("Query:", query)
    print("\nResponse:\n", response)


vectorstore = get_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

docs = retriever.invoke("What kind of violence against civilians happened in Algeria?")
for d in docs:
    print(d.page_content)
    print("---")