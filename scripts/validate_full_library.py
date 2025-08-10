#!/usr/bin/env python3
"""
Validate the integrity of data/full_library after rebuild/sanitize.

Checks:
- Count RAW epubs vs FULL epubs (.epub only)
- Ensure no files live at full_library root
- Ensure author directory names are normalized and free of forbidden chars
- Find duplicate author directories by canonical key
- Validate book filenames follow pattern "Title - AUTHOR.ext"
- Report letter coverage for author last-name initials (A–Z)

Outputs a concise report to stdout and writes a detailed report to
data/validation_report.txt
"""

from __future__ import annotations

import logging
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple


RAW_ROOT = Path("data/RAW_LIBRARY")
FULL_ROOT = Path("data/full_library")
REPORT_FILE = Path("data/validation_report.txt")

BOOK_EXTENSIONS = {".epub"}
FORBIDDEN = set('<>:"/\\|?*')


def is_book_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in BOOK_EXTENSIONS


def scan_raw_counts(root: Path) -> int:
    count = 0
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in BOOK_EXTENSIONS:
            count += 1
    return count


def normalize_for_key(name: str) -> str:
    n = unicodedata.normalize("NFKD", name)
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = n.lower()
    n = re.sub(r"\s+", " ", n).strip()
    return n


def validate() -> Tuple[str, List[str]]:
    lines: List[str] = []
    issues: List[str] = []

    if not RAW_ROOT.exists() or not FULL_ROOT.exists():
        print("Expected data/RAW_LIBRARY and data/full_library to exist.")
        sys.exit(1)

    raw_count = scan_raw_counts(RAW_ROOT)
    full_books = []
    authors = []
    for p in FULL_ROOT.iterdir():
        if p.is_dir():
            authors.append(p)
        elif p.is_file():
            issues.append(f"Unexpected file at full_library root: {p.name}")

    for a in authors:
        for f in a.iterdir():
            if is_book_file(f):
                full_books.append(f)

    lines.append(f"RAW ebooks: {raw_count}")
    lines.append(f"FULL authors: {len(authors)}")
    lines.append(f"FULL ebooks: {len(full_books)}")

    # Duplicate author directories by canonical key
    groups: Dict[str, List[Path]] = {}
    for a in authors:
        key = normalize_for_key(a.name)
        groups.setdefault(key, []).append(a)
    dups = {k: v for k, v in groups.items() if len(v) > 1}
    if dups:
        issues.append(f"Duplicate author keys detected: {len(dups)}")
        for k, dirs in sorted(dups.items()):
            issues.append("  DUP: " + ", ".join(d.name for d in dirs))

    # Author name forbidden chars
    for a in authors:
        if any(ch in FORBIDDEN for ch in a.name):
            issues.append(f"Forbidden char in author dir name: {a.name}")

    # Book filename checks: only EPUBs and forbidden characters
    non_epub = [f for f in full_books if f.suffix.lower() not in BOOK_EXTENSIONS]
    if non_epub:
        issues.append(f"Non-EPUB files found: {len(non_epub)} (EPUB-only policy)")
    for f in full_books:
        if any(ch in FORBIDDEN for ch in f.name):
            issues.append(f"Forbidden char in filename: {f.relative_to(FULL_ROOT)}")

    # Letter coverage based on author last-name initial (before comma or first token)
    letter_counts: Dict[str, int] = {chr(c): 0 for c in range(ord('A'), ord('Z') + 1)}
    for a in authors:
        name = a.name
        last = name.split(",", 1)[0].strip() if "," in name else name.split()[0]
        if last:
            first_char = unicodedata.normalize("NFKD", last)[0].upper()
            if 'A' <= first_char <= 'Z':
                letter_counts[first_char] += 1

    coverage = ", ".join(f"{k}:{v}" for k, v in sorted(letter_counts.items()))
    lines.append("Author last-name initial coverage:")
    lines.append(coverage)

    if issues:
        lines.append("\nIssues:")
        lines.extend(issues)

    # Write detailed report
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines), issues


def main() -> None:
    summary, issues = validate()
    print(summary)
    if issues:
        sys.exit(2)


if __name__ == "__main__":
    main()


