#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
import pdfplumber
import pandas as pd

HEADER_DATE = {"ΗΜΕΡΟΜΗΝΙΑ", "ΗΜΕΡ/ΝΙΑ"}
GREEK_HEADERS = list(HEADER_DATE | {"ΗΜΕΡΑ","ΩΡΑ","ΑΙΘΟΥΣΑ","ΜΑΘΗΜΑ","ΕΞΕΤΑΣΤΗΣ"})
TIME_RE = re.compile(r"\b\d{1,2}\s*-\s*\d{1,2}\b")
DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")

# Room normalization:
ROOM_REGEX = re.compile(r"^(ΗΛ\d{0,2}|ΚΥΠΕΣ|Α\.Φ\.Ε\.)$")

def find_semester(text: str) -> str:
    m = re.search(r"ΕΞΑΜΗΝΟ\s*(\d+)", text or "")
    return m.group(1) if m else ""

def header_boxes(page):
    boxes = {}
    for w in page.extract_words(use_text_flow=True, keep_blank_chars=False):
        t = w["text"].strip()
        if t in {"ΗΜΕΡΟΜΗΝΙΑ","ΗΜΕΡ/ΝΙΑ"}:
            t_norm = "ΗΜΕΡΟΜΗΝΙΑ"
        else:
            t_norm = t
        if t_norm in GREEK_HEADERS and t_norm not in boxes:
            boxes[t_norm] = (w["x0"], w["top"], w["x1"], w["bottom"])
    return boxes

def outer_rect(page):
    best = None; best_area = 0.0
    for r in page.rects:
        w = abs(r["x1"] - r["x0"]); h = abs(r["bottom"] - r["top"])
        area = w*h
        if w > 300 and h > 150 and area > best_area:
            best = (min(r["x0"], r["x1"]), min(r["top"], r["bottom"]),
                    max(r["x0"], r["x1"]), max(r["top"], r["bottom"]))
            best_area = area
    return best

def infer_boundaries_from_headers(page):
    boxes = header_boxes(page)
    if not boxes:
        return None
    cols = sorted([(k, *boxes[k]) for k in boxes], key=lambda t: t[1])  # sort by x0
    if len(cols) < 5:
        return None
    left_edge = cols[0][1] - 10
    bounds = [left_edge]
    for i in range(len(cols)-1):
        right_i = cols[i][3]  # x1
        left_next = cols[i+1][1]  # x0
        bounds.append((right_i + left_next)/2.0)
    right_edge = cols[-1][3] + 10
    bounds.append(right_edge)
    if "ΗΜΕΡΟΜΗΝΙΑ" not in boxes:
        hdr_top = min(y0 for _,y0,_,_ in boxes.values())
        min_date_x0 = None
        for w in page.extract_words(use_text_flow=True):
            txt = w["text"].strip()
            if DATE_RE.fullmatch(txt) and w["top"] > hdr_top - 2:
                min_date_x0 = w["x0"] if min_date_x0 is None else min(min_date_x0, w["x0"])
        if min_date_x0 is not None:
            bounds = sorted([min_date_x0 - 10] + bounds)
    return sorted(bounds)

def y_cluster(values, tol: float = 4.0):
    if not values: return []
    vals = sorted(values)
    groups = [[vals[0]]]
    for v in vals[1:]:
        if abs(v - groups[-1][-1]) <= tol:
            groups[-1].append(v)
        else:
            groups.append([v])
    reps = [sorted(g)[len(g)//2] for g in groups]
    return reps

def assign_col(boundaries, xmid):
    for i in range(len(boundaries)-1):
        if boundaries[i] <= xmid <= boundaries[i+1]:
            return i
    if xmid < boundaries[0]: return 0
    return len(boundaries)-2

def normalize_room_course(room: str, course: str):
    """
    Ensure room contains only room-like tokens; push the rest to course.
    """
    tokens = room.split()
    room_keep = []
    spill = []
    for tok in tokens:
        if ROOM_REGEX.match(tok):
            room_keep.append(tok)
        else:
            spill.append(tok)
    new_room = " ".join(room_keep).strip()
    if spill:
        # prepend spill to course
        if course:
            new_course = (" ".join(spill) + " " + course).strip()
        else:
            new_course = " ".join(spill).strip()
    else:
        new_course = course
    return new_room, new_course

def parse_page(page):
    text = page.extract_text() or ""
    semester = find_semester(text)
    bounds = infer_boundaries_from_headers(page)
    if not bounds or len(bounds) < 7:
        words_all = page.extract_words(use_text_flow=True)
        if not words_all:
            return []
        left = min(w["x0"] for w in words_all) - 5
        right = max(w["x1"] for w in words_all) + 5
        step = (right - left)/6.0
        bounds = [left + i*step for i in range(7)]

    tab_rect = outer_rect(page)
    hdrs = header_boxes(page)
    top_data = max((b[3] for b in hdrs.values()), default=0) + 1

    words = []
    for w in page.extract_words(use_text_flow=True, keep_blank_chars=False):
        x0,y0,x1,y1 = w["x0"], w["top"], w["x1"], w["bottom"]
        ymid = (y0 + y1)/2.0
        if ymid < top_data:
            continue
        if tab_rect:
            if not (tab_rect[0]-5 <= x0 <= tab_rect[2]+5 and tab_rect[1]-5 <= y0 <= tab_rect[3]+5):
                continue
        words.append({"text": w["text"], "xmid": (x0+x1)/2.0, "ymid": ymid})

    y_vals = [w["ymid"] for w in words]
    y_lines = y_cluster(y_vals, tol=4.0)

    lines = []
    for y in y_lines:
        line_words = [w for w in words if abs(w["ymid"] - y) <= 4.0]
        col_text = [[] for _ in range(len(bounds)-1)]
        for w in sorted(line_words, key=lambda x: x["xmid"]):
            col = assign_col(bounds, w["xmid"])
            col_text[col].append(w["text"])
        cols_joined = [" ".join(t).strip() for t in col_text]
        lines.append(cols_joined)

    # Remove header-like lines
    clean_lines = []
    for cols in lines:
        header_like = sum(1 for h in GREEK_HEADERS if h in " ".join(cols))
        if header_like >= 2:
            continue
        clean_lines.append(cols)

    # Normalize to 6 columns
    clean_lines = [ (row + [""]*6)[:6] for row in clean_lines ]

    date_ff, day_ff, last_full_row = "", "", None
    rows = []
    for row in clean_lines:
        date, day, time, room, course, examiner = [c.strip() for c in row]

        if date: date_ff = date
        if day:  day_ff = day
        cur_date, cur_day = date_ff, day_ff

        # Full row
        if time and course:
            # clean room/course
            room, course = normalize_room_course(room, course)
            rows.append({
                "Semester": semester,
                "Date": cur_date,
                "Day": cur_day,
                "Time": time,
                "Room": room,
                "Course": course,
            })
            last_full_row = rows[-1]
            continue

        # Additional course under same time/room
        if (not time) and (not room) and (course or examiner) and last_full_row is not None:
            rows.append({
                "Semester": semester,
                "Date": cur_date,
                "Day": cur_day,
                "Time": last_full_row.get("Time",""),
                "Room": last_full_row.get("Room",""),
                "Course": course if course else "",
            })
            last_full_row = rows[-1]
            continue

        # Continuation of same course text (no time/room/examiner)
        if (not time) and (not room) and (not examiner) and course and last_full_row is not None:
            last_full_row["Course"] = (last_full_row["Course"] + " " + course).strip()
            continue

    return rows

def parse_pdf(path: str) -> pd.DataFrame:
    all_rows = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            all_rows.extend(parse_page(p))
    df = pd.DataFrame(all_rows, columns=["Semester","Date","Day","Time","Room","Course"])
    return df

def main():
    if len(sys.argv) < 3:
        print("Usage: python exam_pdf_to_csv_v4.py input.pdf output.csv")
        sys.exit(2)
    src, dst = sys.argv[1], sys.argv[2]
    df = parse_pdf(src)
    df.to_csv(dst, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(df)} rows -> {dst}")

if __name__ == "__main__":
    main()
