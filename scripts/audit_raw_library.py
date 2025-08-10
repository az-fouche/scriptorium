#!/usr/bin/env python3
"""
Audit RAW_LIBRARY: inventory of EPUB candidates, structure overview, and author hints.

Outputs (under data/transfers/ by default):
- raw_inventory.json: list of files with metadata and author/title hints (EPUB only by default)
- raw_inventory_summary.txt: counts and structure summary
- raw_authors_raw.txt: distinct raw author strings observed from paths/filenames

This script is read-only and does not modify RAW.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


RAW_DIR_DEFAULT = Path("data/RAW_LIBRARY")
OUT_DIR_DEFAULT = Path("data/transfers")


SUPPORTED_EXTENSIONS = {".epub"}
SKIP_FILENAMES = {"metadata.opf", "cover.jpg", "cover.png"}
SKIP_EXTENSIONS = {".opf", ".nfo", ".html", ".jpg", ".jpeg", ".png", ".mobi", ".pdf"}


def is_epub(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def looks_like_author(s: str) -> bool:
    if not s:
        return False
    if "," in s:
        return True
    words = s.split()
    capitalized = sum(1 for w in words if w[:1].isupper())
    if capitalized >= 2 and len(words) <= 5:
        return True
    blocked = {"tome", "vol", "volume", "partie", "part", "livre"}
    if any(tok.lower() in blocked for tok in words):
        return False
    return False


def clean_title(raw_title: str) -> str:
    title = raw_title.replace("_", " ")
    title = re.sub(r"\s*[\[(]b-ok\.[^)\]]*[)\]]\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\((Ebook-Gratuit\.[^)]+)\)\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+-\s+", " - ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


@dataclass
class FileRecord:
    source_path: str
    rel_path: str
    ext: str
    size: int
    author_hint: Optional[str]
    title_hint: Optional[str]
    author_hint_source: Optional[str]


def parse_filename_for_title_author(stem: str) -> Optional[Tuple[str, str]]:
    m = re.match(r"^\[([^\]]+)\][ _-]+(.+)$", stem)
    if m:
        author_raw = m.group(1).replace("_", " ").strip()
        title_raw = m.group(2).strip()
        return clean_title(title_raw), author_raw

    parts = [p.strip() for p in stem.split(" - ")]
    if len(parts) >= 2:
        last_part = parts[-1]
        first_part = parts[0]
        if looks_like_author(last_part):
            title_raw = " - ".join(parts[:-1])
            return clean_title(title_raw), last_part
        if looks_like_author(first_part):
            author_raw = first_part
            title_raw = " - ".join(parts[1:])
            return clean_title(title_raw), author_raw

    m = re.match(r"^(.+)\s*\(([^)]+)\)\s*$", stem)
    if m and looks_like_author(m.group(2)):
        return clean_title(m.group(1)), m.group(2).strip()

    m = re.match(r"^(.+?)[ _-]+by[ _-]+(.+)$", stem, re.IGNORECASE)
    if m:
        return clean_title(m.group(1)), m.group(2).strip()

    return None


def walk_epubs(root: Path) -> Iterable[Path]:
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            p = Path(dirpath) / fname
            if p.name.lower() in SKIP_FILENAMES:
                continue
            if p.suffix.lower() in SKIP_EXTENSIONS:
                continue
            if is_epub(p):
                yield p


def collect_inventory(raw_root: Path, out_root: Path) -> Tuple[List[FileRecord], Dict[str, int], Set[str]]:
    records: List[FileRecord] = []
    author_strings: Set[str] = set()
    counts: Dict[str, int] = {"epub": 0, "other_skipped": 0}

    for p in walk_epubs(raw_root):
        counts["epub"] += 1
        rel = str(p.relative_to(raw_root))
        size = p.stat().st_size
        stem = p.stem
        guess = parse_filename_for_title_author(stem)
        author_hint = None
        title_hint = None
        author_hint_source = None
        if guess:
            title_hint, author_hint = guess
            author_hint_source = "filename"
        else:
            parent = p.parent.name
            if looks_like_author(parent):
                author_hint = parent
                title_hint = clean_title(stem)
                author_hint_source = "parent_dir"
        if author_hint:
            author_strings.add(author_hint)
        records.append(
            FileRecord(
                source_path=str(p),
                rel_path=rel,
                ext=p.suffix.lower(),
                size=size,
                author_hint=author_hint,
                title_hint=title_hint,
                author_hint_source=author_hint_source,
            )
        )

    # Write outputs
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "raw_inventory.json").write_text(
        json.dumps([asdict(r) for r in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_root / "raw_authors_raw.txt").write_text(
        "\n".join(sorted(author_strings)), encoding="utf-8"
    )

    summary_lines = [
        f"RAW root: {raw_root}",
        f"EPUB files: {counts['epub']}",
        f"Distinct author hints: {len(author_strings)}",
        "Note: Only .epub were inventoried; other extensions are ignored.",
    ]
    (out_root / "raw_inventory_summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    return records, counts, author_strings


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit RAW_LIBRARY for EPUB inventory and author hints")
    parser.add_argument("--source", type=Path, default=RAW_DIR_DEFAULT, help="Source RAW_LIBRARY root")
    parser.add_argument("--out", type=Path, default=OUT_DIR_DEFAULT, help="Output directory for audit files")
    args = parser.parse_args()

    raw_root: Path = args.source
    if not raw_root.exists() or not raw_root.is_dir():
        raise SystemExit(f"Source directory does not exist or is not a directory: {raw_root}")

    records, counts, authors = collect_inventory(raw_root, args.out)
    print(f"EPUB files: {counts['epub']} | Distinct author hints: {len(authors)}")


if __name__ == "__main__":
    main()


