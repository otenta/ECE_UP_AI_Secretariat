import argparse
from typing import List, Tuple
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from RAG.get_embedding_function import get_embedding_function

CHROMA_PATH = "chroma"
PROMPT_TEMPLATE = (
    "Answer the question based only on the following context:\n"
    "{context}\n\n"
    "---\n\n"
    "Answer the question based on the above context: {question}"
)
RERANK_PROMPT = (
    "Query: {question}\n\n"
    "Document:\n{doc_text}\n\n"
    "On a scale from 0 (not relevant) to 1 (highly relevant), "
    "rate how relevant this document is to the query above. "
    "Respond with only the numeric score."
)


def rerank_documents(
    docs: List, question: str, model_name: str, temperature: float
) -> List:
    """
    Use the LLM to score each document for relevance and return docs sorted by score descending.
    """
    llm = OllamaLLM(model=model_name, temperature=temperature)
    prompt = PromptTemplate(input_variables=["question", "doc_text"], template=RERANK_PROMPT)
    scored: List[Tuple[float, object]] = []
    for d in docs:
        text = d.page_content
        # Format rerank prompt
        formatted = prompt.format(question=question, doc_text=text)
        resp = llm.invoke(formatted).strip()
        try:
            score = float(resp)
        except ValueError:
            score = 0.0
        scored.append((score, d))
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    # Extract sorted docs
    return [d for score, d in scored]


def query_rag(query_text: str, k: int, model_name: str, temperature: float, rerank: bool):
    # Initialize embeddings & vector store
    embeddings = get_embedding_function()
    db = Chroma(
        collection_name="regulations",
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )

    # Retrieve top-k relevant documents
    retriever = db.as_retriever(search_kwargs={"k": k * (2 if rerank else 1)})
    initial_docs = retriever.invoke(query_text)

    # Optionally rerank a larger set down to k
    docs = initial_docs
    if rerank:
        docs = rerank_documents(initial_docs, query_text, model_name, temperature)[:k]

    # Build context
    context = "\n\n---\n\n".join([d.page_content for d in docs])

    # Prepare final answer prompt and LLM
    prompt = PromptTemplate(input_variables=["context", "question"], template=PROMPT_TEMPLATE)
    llm = OllamaLLM(model=model_name, temperature=temperature)
    formatted_prompt = prompt.format(context=context, question=query_text)
    answer = llm.invoke(formatted_prompt)

    # Extract source IDs
    sources = []
    for d in docs:
        meta = d.metadata or {}
        src_id = meta.get("id") or f"{meta.get('page')}_{meta.get('chunk_id')}" or meta.get("source", "unknown")
        sources.append(src_id)

    return answer, sources


def main():
    parser = argparse.ArgumentParser(description="Query RAG with optional LLM reranker")
    parser.add_argument("query_text", help="The question to ask the RAG system.")
    parser.add_argument("--k", type=int, default=5, help="Number of documents to retrieve.")
    parser.add_argument("--model", default="llama3", help="Ollama model to use (e.g., llama3, mixtral).")
    parser.add_argument("--temp", type=float, default=0.2, help="LLM temperature.")
    parser.add_argument("--rerank", action="store_true", help="Enable LLM-based reranking.")
    args = parser.parse_args()

    answer, sources = query_rag(
        query_text=args.query_text,
        k=args.k,
        model_name=args.model,
        temperature=args.temp,
        rerank=args.rerank
    )

    print("Answer:", answer)
    print("\n")
    print("Sources:", sources)

if __name__ == "__main__":
    main()

# if __name__ == "__main__":
#     answer, sources = query_rag("What is the ECTS limit in the 6th semester for full time students?",
#                                 k=5,model_name="llama3",
#                                 temperature=0.2,
#                                 rerank=True)
#     print("Answer:", answer)
#     print("\n")
#     print("Sources:", sources)
