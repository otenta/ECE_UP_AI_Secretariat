import csv, json, re, calendar
from dateutil import parser
from datetime import datetime, time

INVALID = {"", "-", "—", "N/A", "NA", "none", "tbd", "TBD"}

def normalize_date_iso(raw_date: str) -> str | None:
    if not raw_date or raw_date.strip() in INVALID:
        return None
    try:
        dt = parser.parse(raw_date, dayfirst=True, yearfirst=False, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None

def date_long_from_iso(iso_date: str) -> str:
    y, m, d = map(int, iso_date.split("-"))
    dt = datetime(y, m, d)
    weekday = calendar.day_name[dt.weekday()]      # Monday
    month = calendar.month_name[m]                 # September
    return f"{weekday}, {d} {month} {y}"

def fmt_12h(h: int, m: int = 0) -> str:
    t = time(hour=h, minute=m)
    s = t.strftime("%I:%M%p").lower()  # "09:00am"
    return s.lstrip("0")               # "9:00am"

H_H = re.compile(r"^\s*(\d{1,2})\s*-\s*(\d{1,2})\s*$")
HMM_HMM = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*$")

def split_time_ampm(raw_time: str):
    if not raw_time or raw_time.strip() in INVALID:
        return None, None, None  # start, end, pretty_range
    s = raw_time.strip()
    m = H_H.match(s)
    if m:
        h1, h2 = map(int, m.groups())
        start, end = fmt_12h(h1), fmt_12h(h2)
        return start, end, f"{start}-{end}"
    m = HMM_HMM.match(s)
    if m:
        h1, m1, h2, m2 = map(int, m.groups())
        start, end = fmt_12h(h1, m1), fmt_12h(h2, m2)
        return start, end, f"{start}-{end}"
    # Already am/pm range like "9:00am-12:00pm": trust it, but also split safely
    if "-" in s and ("am" in s.lower() or "pm" in s.lower()):
        parts = [p.strip() for p in s.split("-", 1)]
        if len(parts) == 2:
            return parts[0], parts[1], s.lower()
    return None, None, s  # leave as-is

# Wire up your converter
import_path = "data/final_exams_schedule.csv"
export_path = "data/final_exams_schedule.json"

data = {}
with open(import_path, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        course = row["Course"]

        iso = normalize_date_iso(row.get("Date", ""))
        if iso:
            # row["DateISO"] = iso
            # row["DateLong"] = date_long_from_iso(iso)
            row["Date"] = date_long_from_iso(iso)  # keep Date as ISO to be unambiguous

        ts, te, pretty = split_time_ampm(row.get("Time", ""))
        # row["TimeStartAmPm"] = ts or ""
        # row["TimeEndAmPm"]   = te or ""
        row["Time"]      = pretty or ""

        data[course] = row

with open(export_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(data)} courses to {export_path}")
