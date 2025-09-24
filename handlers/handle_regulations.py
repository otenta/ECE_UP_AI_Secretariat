from RAG import query_data

def handle_regulations(query: str) -> str:
    answer, sources = query_data.query_rag(query_text=query, k=5, model_name="llama3", temperature=0.2, rerank=True)
    print(answer)
    print(sources)
    return answer