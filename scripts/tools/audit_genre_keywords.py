#!/usr/bin/env python3
"""
Audit genre keywords to detect overly broad terms.

This script computes, for selected genres, how frequently each keyword
matches across the books database (title, description, subjects).
It flags keywords whose coverage (fraction of books matched) exceeds a threshold.

Usage:
  python scripts/tools/audit_genre_keywords.py \
    --db databases/books.db \
    --lang french \
    --genres Essai Horreur Policier \
    --threshold 0.05
"""

import argparse
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple


def load_genre_keywords(data_dir: Path, language: str) -> Dict[str, List[str]]:
    genres_file = data_dir / "genres" / f"{language}_genres.json"
    if not genres_file.exists():
        raise FileNotFoundError(f"Genre file not found: {genres_file}")
    with open(genres_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalize to {genre: [keywords]}
    normalized: Dict[str, List[str]] = {}
    for genre, value in data.items():
        if isinstance(value, dict) and "keywords" in value:
            normalized[genre] = [str(k).lower() for k in value["keywords"]]
        elif isinstance(value, list):
            normalized[genre] = [str(k).lower() for k in value]
        else:
            normalized[genre] = []
    return normalized


def fetch_books(conn: sqlite3.Connection) -> List[Tuple[str, str, str, str]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, IFNULL(description, ''), IFNULL(subjects, '')
        FROM books
        """
    )
    return [(r[0], r[1] or "", r[2] or "", r[3] or "") for r in cur.fetchall()]


def text_blob(title: str, description: str, subjects: str) -> str:
    value = " \n ".join([title, description, subjects]).lower()
    # light cleanup
    value = re.sub(r"\s+", " ", value)
    return value


def audit_keywords(
    books: List[Tuple[str, str, str, str]],
    keywords: List[str],
) -> Dict[str, int]:
    counts: Dict[str, int] = {kw: 0 for kw in keywords}

    # Pre-compose blobs for performance
    blobs = [text_blob(t, d, s) for _, t, d, s in books]

    for kw in keywords:
        # match as substring; can be enhanced to word-boundary where appropriate
        kw_l = kw.lower()
        hit = sum(1 for blob in blobs if kw_l in blob)
        counts[kw] = hit
    return counts


def main():
    parser = argparse.ArgumentParser(description="Audit genre keywords for broadness")
    parser.add_argument("--db", default=str(Path("databases") / "books.db"), help="Path to sqlite database")
    parser.add_argument("--lang", default="french", choices=["french", "english"], help="Language of genre file")
    parser.add_argument("--genres", nargs="+", required=True, help="Genres to audit (exact keys in JSON)")
    parser.add_argument("--threshold", type=float, default=0.05, help="Flag keywords with coverage above this fraction")
    parser.add_argument("--top", type=int, default=30, help="Show top-N keywords by coverage for each genre")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        # try fallbacks
        alt_paths = [Path("books.db"), Path("databases") / "subset_books.db"]
        found = None
        for p in alt_paths:
            if p.exists():
                found = p
                break
        if found is None:
            raise FileNotFoundError(f"Database not found at {db_path} or fallbacks: {alt_paths}")
        db_path = found

    data_dir = Path("data")
    genres = load_genre_keywords(data_dir, args.lang)

    # Connect DB and fetch books
    conn = sqlite3.connect(str(db_path))
    try:
        books = fetch_books(conn)
    finally:
        conn.close()

    total = len(books)
    if total == 0:
        print("No books found in database.")
        return

    print(f"Auditing {len(args.genres)} genre(s) on {total} books from {db_path} (lang={args.lang})")
    print("=" * 80)

    for genre in args.genres:
        if genre not in genres:
            print(f"- Skipping unknown genre: {genre}")
            continue
        kws = genres[genre]
        if not kws:
            print(f"- No keywords for genre: {genre}")
            continue

        counts = audit_keywords(books, kws)
        # Compute coverage
        coverage = [(kw, c, c / total) for kw, c in counts.items()]
        coverage.sort(key=lambda x: x[2], reverse=True)

        print(f"\nGenre: {genre}")
        print("- Potentially broad keywords (above threshold):")
        flagged = [(kw, c, frac) for kw, c, frac in coverage if frac >= args.threshold]
        if not flagged:
            print("  none")
        else:
            for kw, c, frac in flagged[: args.top]:
                print(f"  {kw:25s}  {c:6d}  {frac:7.2%}")

        print("- Top matches:")
        for kw, c, frac in coverage[: args.top]:
            print(f"  {kw:25s}  {c:6d}  {frac:7.2%}")

    print("\nHint: consider removing or tightening keywords that match a large fraction of books.")


if __name__ == "__main__":
    main()


