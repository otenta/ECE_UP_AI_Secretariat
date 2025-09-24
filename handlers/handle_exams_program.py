from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM, OllamaEmbeddings

def get_embedding_function():
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    return embeddings

CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = (
    "\nUse ONLY this context:\n{context}\n"
    "---\n"
    "Question: {question}\n\n"
    "Rules:\n"
    "1) Copy the values for Course, Date, Time and Room VERBATIM from context.\n"
    "2) Do NOT reformat or change dates or times.\n"
    "3) If a field is missing/empty, write 'not provided'.\n"
    "4) Return EXACTLY ONE sentence, no preamble.\n"
    "5) Format exactly:\n"
    "   'Based on the context, the <Course> course is scheduled to take place on <Date> "
    "during <Time> in Room <Room>.'\n"
)

def handle_exams_program(query: str) -> str:
    embeddings = get_embedding_function()
    db = Chroma(
        collection_name="exams",  # <<< match the indexer name
        persist_directory=CHROMA_PATH,  # <<< match the indexer path
        embedding_function=embeddings
    )
    try:
        count = db._collection.count()
        # print(f"Docs in collection: {count}")
    except Exception:
        count = None

    # Retrieve top-k relevant documents
    retriever = db.as_retriever(search_kwargs={"k": 3 })
    initial_docs = retriever.invoke(query)
    context = "\n\n---\n\n".join([d.page_content for d in initial_docs])
    answer = query_model(context, query)
    print(answer)
    return answer

def query_model(context, query: str) -> str:
    prompt = PromptTemplate(input_variables=["context", "question"], template=PROMPT_TEMPLATE)
    llm = OllamaLLM(model="llama3", temperature=0)
    formatted_prompt = prompt.format(context=context, question=query)
    return llm.invoke(formatted_prompt)


# def main():
#     handle_exams_program("when are the exams for introduction to computers?")
#
# if __name__=="__main__":
#     main()

