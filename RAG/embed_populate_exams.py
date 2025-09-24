import argparse
import json
import os
import shutil
import unicodedata
import re

from langchain_chroma import Chroma
from get_embedding_function import get_embedding_function

EXAMS_SCHEDULE = "data/final_exams_schedule.json"

def norm_id(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return s or "untitled"

def row_to_text(course: str, row: dict) -> str:
    # Short, LLM-friendly card instead of raw JSON
    return (
        f"Course: {row.get('Course', course)}\n"
        f"Semester: {row.get('Semester','')}\n"
        f"Date: {row.get('Date','')}\n"
        f"Day: {row.get('Day','')}\n"
        f"Time: {row.get('Time','')}\n"
        f"Room: {row.get('Room','')}"
    )

def main(chroma_path: str, reset: bool = False):
    if reset and os.path.isdir(chroma_path):
        shutil.rmtree(chroma_path, ignore_errors=True)

    with open(EXAMS_SCHEDULE, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts, metadatas, ids = [], [], []
    for course, row in data.items():
        texts.append(row_to_text(course, row))
        metadatas.append({
            "course": row.get("Course", course),
            "semester": row.get("Semester", ""),
            "date": row.get("Date", ""),
            "day": row.get("Day", ""),
            "time": row.get("Time", ""),
            "room": row.get("Room", ""),
        })
        ids.append(norm_id(row.get("Course", course)))

    embeddings = get_embedding_function()

    db = Chroma(
        collection_name="exams",               # <<< keep name
        persist_directory=chroma_path,         # <<< keep path
        embedding_function=embeddings,
    )

    db.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    print(f"Indexed {len(texts)} courses into {chroma_path}/exams")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--chroma", default="chroma")
    p.add_argument("--reset", action="store_true")
    args = p.parse_args()
    main(args.chroma, args.reset)
