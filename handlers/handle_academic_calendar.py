import json
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

ACADEMIC_CALENDAR = "data/academic_calendar.json"

PROMPT_TEMPLATE = (
    "Answer the question based only on the following context:\n"
    "{context}\n\n"
    "---\n\n"
    "Answer the question based on the above context: {question}"
)

def handle_academic_calendar(query: str) -> str:
    with open(ACADEMIC_CALENDAR, 'r', encoding="utf-8") as file:
        data = json.load(file)
        answer = query_model(data, query)
        print(answer)
    return answer


def query_model(file, query: str) -> str:
    prompt = PromptTemplate(input_variables=["context", "question"], template=PROMPT_TEMPLATE)
    llm = OllamaLLM(model="llama3", temperature=0.2)
    formatted_prompt = prompt.format(context=file, question=query)
    return llm.invoke(formatted_prompt)