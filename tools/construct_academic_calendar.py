#!/usr/bin/env python3

from datetime import date
from pathlib import Path
import json
from typing import Union, List, Dict


def construct_academic_calendar(output_path: Union[str, Path] = "../data/academic_calendar.json") -> List[Dict]:
    y = date.today().year  # current year
    ny = y + 1  # next year

    rows = [
        {"event": f"September {y} exam period", "start_date": f"{y}-08-28", "end_date": f"{y}-09-25"},
        {"event": "Winter semester classes period", "start_date": f"{y}-09-30", "end_date": f"{ny}-01-10"},
        {"event": "Winter semester exams", "start_date": f"{ny}-01-20", "end_date": f"{ny}-02-07"},
        {"event": "Spring semester classes period", "start_date": f"{ny}-02-17", "end_date": f"{ny}-05-30"},
        {"event": "Spring semester exams", "start_date": f"{ny}-06-10", "end_date": f"{ny}-06-27"},
    ]

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return rows


if __name__ == "__main__":
    construct_academic_calendar()  # writes ./academic_calendar.json
    print("Wrote academic_calendar.json")
