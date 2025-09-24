import json
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

OFFICE_HOURS = "data/office_hours.json"

PROMPT_TEMPLATE = (
    "Use ONLY this context:\n{context}\n"
"---\n"
"Question: {question}\n\n"
"Rules (read carefully and follow in order):\n"
"1) Identify the professor:\n"
"   - If an exact case-insensitive match to 'display_name' exists, use that JSON entry ONLY.\n"
"   - Otherwise pick the SINGLE closest 'display_name' by similarity and use that entry ONLY.\n"
"   - Never combine data across different professors.\n\n"
"2) Collect office-hour rows ONLY from the matched professor’s entry. Ignore any other entries.\n\n"
"3) Normalize and validate time slots:\n"
"   - Accept slots only if they contain a start and end time that can be parsed from one of these patterns:\n"
"     a) 'H-H', 'HH-HH', 'H-HH', 'HH-H' (e.g., 9-12, 10-13)\n"
"     b) 'H:MM-H:MM' or 'HH:MM-HH:MM' (e.g., 09:00-12:30)\n"
"     c) With optional spaces around the hyphen (e.g., '09:00 - 12:30')\n"
"   - Treat ANY of the following as 'no hours' for that row/field: empty string, null, missing field, '—', '-', 'N/A', 'NA', 'none', 'no hours', 'tbd', 'TBD', [].\n"
"   - If minutes are omitted (e.g., '9-12'), interpret as '9:00' to '12:00'.\n"
"   - Convert 24-hour times to 12-hour with am/pm (examples: '9-12' → '9am to 12pm'; '09:00-12:30' → '9:00am to 12:30pm').\n\n"
"4) Build the set of VALID slots:\n"
"   - For each weekday present in the matched entry, include every valid slot found for that day.\n"
"   - If a weekday has multiple valid slots, include them all for that day separated by commas.\n"
"   - Keep weekday order as it appears in the JSON (do NOT reorder).\n\n"
"5) Output (MUTUALLY EXCLUSIVE):\n"
"   - If at least one VALID slot exists across all weekdays, return EXACTLY ONE sentence in this format:\n"
"     'Based on the context, the office hours for professor <display_name> are <Weekday> from <Start> to <End>[, <Weekday> from <Start> to <End>[, <Start> to <End> if multiple], ...]. Contact details are email, <Email> and phone, <Phone>'\n"
"   - If NO VALID slots exist, return EXACTLY ONE sentence in this format:\n"
"     'Based on the context, professor <display_name> has no listed office hours. Contact details are email, <Email> and phone, <Phone>'\n\n"
"6) Contact details:\n"
"   - Use only values present in the matched entry.\n"
"   - If Email is missing/empty, write 'email not provided'.\n"
"   - If Phone is missing/empty, write 'phone not provided'.\n\n"
"7) Do NOT invent or infer data. When uncertain about a time, exclude it. Prefer the 'no listed office hours' sentence over outputting uncertain hours.\n\n"
"8) Return EXACTLY ONE sentence, no preamble, no second sentence, no extra text.\n"
"9) USE ONLY 12 HOUR FORMAT.\n"
"10) IF THE HOURS ROW IS EMPTY OR [] SAY 'NONE'.\n"
)
import re, unicodedata

ZERO_WIDTH = r"[\u200B-\u200D\uFEFF]"
NBSP = u"\u00A0"

def sanitize_query(q: str) -> str:
    # Unicode normalize to NFC so accents/greek lookups are consistent
    q = unicodedata.normalize("NFC", q)
    # Replace NBSP with space
    q = q.replace(NBSP, " ")
    # Remove zero-width chars
    q = re.sub(ZERO_WIDTH, "", q)
    # Unify various dashes to ASCII hyphen
    q = q.replace("–", "-").replace("—", "-").replace("−", "-")
    # Normalize quotes
    q = q.replace("“","\"").replace("”","\"").replace("‘","'").replace("’","'")
    # Collapse whitespace
    q = re.sub(r"\s+", " ", q).strip()
    return q

def handle_office_hours(query: str) -> str:
    sanitized = sanitize_query(query)
    with open(OFFICE_HOURS, 'r', encoding="utf-8") as file:
        data = json.load(file)
        answer = query_model(data, sanitized)
        print(answer)
    return answer

def query_model(file, query: str) -> str:
    prompt = PromptTemplate(input_variables=["context", "question"], template=PROMPT_TEMPLATE)
    llm = OllamaLLM(model="llama3", temperature=0.2)
    formatted_prompt = prompt.format(context=file, question=query)
    return llm.invoke(formatted_prompt)