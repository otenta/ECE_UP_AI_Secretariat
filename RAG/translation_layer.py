#!/usr/bin/env python3
"""
Stream-optimized script to extract, chunk, translate (Greek→English), and save PDF text in JSONL for RAG ingestion.
Uses googletrans for in-code translation without requiring Hugging Face model downloads.
"""
import argparse
import json
import pdfplumber
from googletrans import Translator

def stream_chunks(pdf_path: str, max_chars: int, overlap: int):
    """
    Generator: yields (page_num, text chunk) from the PDF page-by-page.
    """
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            start = 0
            N = len(text)
            while start < N:
                end = min(start + max_chars, N)
                yield page_num, text[start:end]
                start = end - overlap if end < N else N

def translate_and_write(pdf_path: str, output_path: str, max_chars: int, overlap: int):
    """
    Streams chunks, translates via Google Translate, and writes JSONL output incrementally.
    """
    translator = Translator()
    with open(output_path, "w", encoding="utf-8") as fout:
        for idx, (page_num, chunk) in enumerate(stream_chunks(pdf_path, max_chars, overlap), start=1):
            print(f"Page {page_num}, chunk {idx} → translating...")
            try:
                en_text = translator.translate(chunk, src='el', dest='en').text
            except Exception as e:
                print(f"Translation failed for chunk {idx}: {e}")
                en_text = ""
            record = {
                "page": page_num,
                "chunk_id": idx,
                "text": en_text
            }
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Stream PDF→chunks→translate→JSONL (Greek→English) using googletrans."
    )
    parser.add_argument("pdf_path", help="Input Greek PDF file path")
    parser.add_argument(
        "--output", "-o",
        default="data/translated_stream.jsonl",
        help="Output JSONL file path"
    )
    parser.add_argument(
        "--max_chars", "-m",
        type=int, default=2000,
        help="Max chars per chunk (default 2000 for low memory)"
    )
    parser.add_argument(
        "--overlap", "-l",
        type=int, default=100,
        help="Overlap chars between chunks (default 100)"
    )
    args = parser.parse_args()

    translate_and_write(
        args.pdf_path,
        args.output,
        args.max_chars,
        args.overlap
    )
    print(f"All done! Output saved to {args.output}")

if __name__ == "__main__":
    main()
