#!/usr/bin/env python3
"""
Sanitize and deduplicate data/full_library after rebuild:

- Merge duplicate author directories differing by case/spacing/accents
  into a single canonical name using the same normalization as rebuild.
- Validate author and book filenames for forbidden characters and empty
  names, and fix them safely.
- Produce a report of changes and potential issues.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Dict


TARGET_DIR_DEFAULT = Path("data/full_library")


BOOK_EXTENSIONS = {".epub"}
SKIP_FILENAMES = {"metadata.opf", "cover.jpg", "cover.png"}
SKIP_EXTENSIONS = {".opf", ".nfo", ".html", ".jpg", ".jpeg", ".png"}


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def safe_fs_name(name: str) -> str:
    name = unicodedata.normalize("NFC", name or "").replace("\u200b", "").strip()
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"__+", "_", name)
    return name.strip(" ._") or "Untitled"


def titlecase_firstname(firstname: str) -> str:
    parts = (firstname or "").split()
    out = []
    for p in parts:
        if p.lower() in {"de", "du", "des", "le", "la", "van", "von", "del", "della", "di"}:
            out.append(p.lower())
        else:
            out.append(p[:1].upper() + p[1:])
    return " ".join(out)


def normalize_author_dir_name(author: str) -> str:
    a = unicodedata.normalize("NFKC", (author or "").strip())
    lower = a.lower()
    if lower in {"collectif", "collective", "various", "various authors"}:
        return "Collectif"
    if lower in {"anonyme", "anonymous", "unknown", "unknown author"}:
        return "Anonyme"
    if lower in {"anthologie", "anthology"}:
        return "Anthologie"

    if "," in a:
        last, first = [s.strip() for s in a.split(",", 1)]
        last_norm = last.upper()
        first_norm = titlecase_firstname(first)
        return safe_fs_name(f"{last_norm}, {first_norm}" if first_norm else last_norm)

    tokens = a.split()
    if len(tokens) >= 2:
        particles = {"de", "du", "des", "van", "von", "le", "la", "del", "della", "di"}
        if len(tokens) >= 3 and tokens[-2].lower() in particles:
            last = " ".join(tokens[-2:])
            first = " ".join(tokens[:-2])
        else:
            last = tokens[-1]
            first = " ".join(tokens[:-1])
        return safe_fs_name(f"{last.upper()}, {titlecase_firstname(first)}")

    # Single-word author: capitalize first letter only
    return safe_fs_name(tokens[0][:1].upper() + tokens[0][1:].lower()) if tokens else "Unknown"


def canonical_key(name: str) -> str:
    # Case/space/diacritics-insensitive key for merging duplicates
    n = unicodedata.normalize("NFKD", name)
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = n.lower()
    n = re.sub(r"\s+", " ", n).strip()
    return n


def merge_duplicate_authors(root: Path) -> int:
    moved = 0
    authors = [d for d in root.iterdir() if d.is_dir()]
    groups: Dict[str, list[Path]] = {}
    for d in authors:
        key = canonical_key(d.name)
        groups.setdefault(key, []).append(d)

    for key, dirs in groups.items():
        if len(dirs) <= 1:
            continue
        # Determine canonical name using normalizer on the first dir name
        canonical_name = normalize_author_dir_name(dirs[0].name)
        canonical_dir = root / canonical_name
        canonical_dir.mkdir(parents=True, exist_ok=True)

        for d in sorted(dirs, key=lambda p: p.name):
            if d == canonical_dir:
                continue
            # Move contents into canonical_dir
            for item in d.iterdir():
                target = canonical_dir / item.name
                if target.exists():
                    # Ensure uniqueness
                    base, ext = os.path.splitext(item.name)
                    c = 1
                    while True:
                        candidate = canonical_dir / f"{base}_{c}{ext}"
                        if not candidate.exists():
                            target = candidate
                            break
                        c += 1
                shutil.move(str(item), str(target))
                moved += 1
            # Remove now-empty directory
            try:
                d.rmdir()
            except OSError:
                pass
    return moved


def sanitize_filenames(root: Path) -> int:
    """Ensure filenames and author dirs are safe and non-empty."""
    fixes = 0

    # First sanitize author directory names
    for d in [p for p in root.iterdir() if p.is_dir()]:
        normalized = normalize_author_dir_name(d.name)
        if normalized != d.name:
            target = root / normalized
            if target.exists():
                # Merge if target exists
                for item in d.iterdir():
                    dest = target / item.name
                    if dest.exists():
                        base, ext = os.path.splitext(item.name)
                        c = 1
                        while True:
                            candidate = target / f"{base}_{c}{ext}"
                            if not candidate.exists():
                                dest = candidate
                                break
                            c += 1
                    shutil.move(str(item), str(dest))
                try:
                    d.rmdir()
                except OSError:
                    pass
                fixes += 1
            else:
                d.rename(target)
                fixes += 1

    # Then sanitize book filenames inside each author directory (EPUB-only)
    for author_dir in [p for p in root.iterdir() if p.is_dir()]:
        for f in author_dir.iterdir():
            if not f.is_file():
                continue
            if f.suffix.lower() not in BOOK_EXTENSIONS:
                # Strict EPUB-only: remove non-EPUB files if any slipped in
                try:
                    f.unlink()
                except Exception:
                    pass
                continue
            safe_name = safe_fs_name(f.name)
            if safe_name != f.name or not safe_name:
                target = author_dir / (safe_name or (f"Untitled{f.suffix}"))
                if target.exists():
                    base, ext = os.path.splitext(target.name)
                    c = 1
                    while True:
                        candidate = author_dir / f"{base}_{c}{ext}"
                        if not candidate.exists():
                            target = candidate
                            break
                        c += 1
                f.rename(target)
                fixes += 1

    return fixes


def main() -> None:
    parser = argparse.ArgumentParser(description="Sanitize and merge duplicate author directories in full_library")
    parser.add_argument("--target", type=Path, default=TARGET_DIR_DEFAULT, help="Target full_library root")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    setup_logging(args.verbose)
    root: Path = args.target
    if not root.exists() or not root.is_dir():
        logging.error("Target directory does not exist or is not a directory: %s", root)
        sys.exit(1)

    logging.info("Merging duplicate author directories...")
    moved = merge_duplicate_authors(root)
    logging.info("Merged/relocated %d items while consolidating author folders", moved)

    logging.info("Sanitizing names and filenames...")
    fixes = sanitize_filenames(root)
    logging.info("Applied %d naming fixes", fixes)

    # Quick report
    authors = [d for d in root.iterdir() if d.is_dir()]
    total_books = 0
    for d in authors:
        total_books += sum(1 for x in d.iterdir() if x.is_file() and x.suffix.lower() in BOOK_EXTENSIONS)
    logging.info("Authors: %d | Books: %d", len(authors), total_books)


if __name__ == "__main__":
    main()


