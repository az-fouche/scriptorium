#!/usr/bin/env python3
"""
Rebuild data/full_library from data/RAW_LIBRARY without modifying RAW.

- Reads every ebook from RAW, including:
  - Alphabetical ranges like "AA à AM", "RA à RN", etc. (contain author subdirs)
  - Single-letter buckets like "E", "F", "T", "W", "XYZ" (contain loose files)
  - Special folders: "_calibre", "1 - Anthologie - Collectif - Anonyme",
    "ZZ-gchampoux.com", "ZZ-www.claryan.com"
  - Loose files in RAW root

- Writes to data/full_library with structure:
  data/full_library/<AUTHOR_DIR>/<TITLE> - <AUTHOR>.ext

  Where <AUTHOR_DIR> is normalized like "LASTNAME, Firstname" when possible.

- Skips non-book files (.opf, .nfo, .html, images) and handles duplicates safely.
- Optionally backs up existing full_library to data/full_library_backup_<timestamp>.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


RAW_DIR_DEFAULT = Path("data/RAW_LIBRARY")
TARGET_DIR_DEFAULT = Path("data/full_library")


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


BOOK_EXTENSIONS = {".epub", ".mobi", ".pdf"}
SKIP_FILENAMES = {"metadata.opf", "cover.jpg", "cover.png"}
SKIP_EXTENSIONS = {".opf", ".nfo", ".html", ".jpg", ".jpeg", ".png"}


def is_book_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name.lower() in SKIP_FILENAMES:
        return False
    if path.suffix.lower() in SKIP_EXTENSIONS:
        return False
    return path.suffix.lower() in BOOK_EXTENSIONS


def safe_fs_name(name: str) -> str:
    # Normalize unicode and remove control chars
    name = unicodedata.normalize("NFC", name)
    name = name.replace("\u200b", "").strip()
    # Windows-forbidden chars: <>:"/\|?*
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Collapse whitespace and underscores
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"__+", "_", name)
    return name.strip(" ._")


def titlecase_firstname(firstname: str) -> str:
    parts = firstname.split()
    out: list[str] = []
    for p in parts:
        if p.lower() in {"de", "du", "des", "le", "la", "van", "von", "del", "della", "di"}:
            out.append(p.lower())
        else:
            out.append(p[:1].upper() + p[1:])
    return " ".join(out)


def normalize_author_dir_name(author: str) -> str:
    # Normalize unicode and spacing
    a = unicodedata.normalize("NFKC", author).strip()
    # Common aliases
    lower = a.lower()
    if lower in {"collectif", "collective", "various", "various authors"}:
        return "Collectif"
    if lower in {"anonyme", "anonymous", "unknown", "unknown author"}:
        return "Anonyme"
    if lower in {"anthologie", "anthology"}:
        return "Anthologie"

    # If already "LASTNAME, Firstname" keep format but normalize spaces/case
    if "," in a:
        last, first = [s.strip() for s in a.split(",", 1)]
        if last:
            last_norm = last.upper()
        else:
            last_norm = last
        first_norm = titlecase_firstname(first)
        return safe_fs_name(f"{last_norm}, {first_norm}" if first_norm else last_norm)

    # Otherwise try to split into Firstname Lastname -> LASTNAME, Firstname
    tokens = a.split()
    if len(tokens) >= 2:
        # Handle particles that might belong to last name (best-effort)
        particles = {"de", "du", "des", "van", "von", "le", "la", "del", "della", "di"}
        # If penultimate is a particle, include it with last name
        if len(tokens) >= 3 and tokens[-2].lower() in particles:
            last = " ".join(tokens[-2:])
            first = " ".join(tokens[:-2])
        else:
            last = tokens[-1]
            first = " ".join(tokens[:-1])
        return safe_fs_name(f"{last.upper()}, {titlecase_firstname(first)}")

    # Fallback
    return safe_fs_name(a)


def clean_title(raw_title: str) -> str:
    title = raw_title
    title = title.replace("_", " ")
    # Remove common source suffixes in parentheses/brackets
    title = re.sub(r"\s*[\[(]b-ok\.[^)\]]*[)\]]\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\((Ebook-Gratuit\.[^)]+)\)\s*", "", title, flags=re.IGNORECASE)
    # Trim repeated separators/spaces
    title = re.sub(r"\s+-\s+", " - ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return safe_fs_name(title)


@dataclass
class ParsedName:
    title: str
    author: str


def looks_like_author(s: str) -> bool:
    # Heuristic: contains comma OR 2+ capitalized words OR typical name-like pattern
    if "," in s:
        return True
    words = s.split()
    capitalized = sum(1 for w in words if w[:1].isupper())
    if capitalized >= 2 and len(words) <= 5:
        return True
    # Avoid series markers
    if any(tok.lower() in {"tome", "vol", "volume", "partie", "part", "livre"} for tok in words):
        return False
    return False


def parse_filename_for_title_author(stem: str) -> Optional[ParsedName]:
    # [Author]_Title
    m = re.match(r"^\[([^\]]+)\][ _-]+(.+)$", stem)
    if m:
        author_raw = m.group(1).replace("_", " ").strip()
        title_raw = m.group(2).strip()
        return ParsedName(title=clean_title(title_raw), author=author_raw)

    # Title - ... - Author (author at end)
    parts = [p.strip() for p in stem.split(" - ")]
    if len(parts) >= 2:
        last_part = parts[-1]
        first_part = parts[0]
        # Case A: Title ... - Author
        if looks_like_author(last_part):
            title_raw = " - ".join(parts[:-1])
            return ParsedName(title=clean_title(title_raw), author=last_part)
        # Case B: Author - Title ...
        if looks_like_author(first_part):
            author_raw = first_part
            title_raw = " - ".join(parts[1:])
            return ParsedName(title=clean_title(title_raw), author=author_raw)

    # Title (Author)
    m = re.match(r"^(.+)\s*\(([^)]+)\)\s*$", stem)
    if m and looks_like_author(m.group(2)):
        return ParsedName(title=clean_title(m.group(1)), author=m.group(2).strip())

    # Title_by_Author
    m = re.match(r"^(.+?)[ _-]+by[ _-]+(.+)$", stem, re.IGNORECASE)
    if m:
        return ParsedName(title=clean_title(m.group(1)), author=m.group(2).strip())

    return None


def build_target_filename(title: str, author_dir_name: str, ext: str) -> str:
    # Display author in file name as "Title - Author"
    author_display = author_dir_name
    # Remove commas in display if desired, but keep as-is for consistency with existing index
    return f"{title} - {author_display}{ext}"


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    base = path.stem
    ext = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{base}_{counter}{ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def copy_book_to_library(source: Path, target_author_dir: Path, author_dir_name: str) -> Optional[Path]:
    if not is_book_file(source):
        return None

    stem = source.stem
    parsed = parse_filename_for_title_author(stem)

    if parsed is None:
        # Fallback: try to infer from parent dir name if looks like author
        parent_name = source.parent.name
        if looks_like_author(parent_name):
            author_raw = parent_name
            title_raw = stem
            parsed = ParsedName(title=clean_title(title_raw), author=author_raw)
        else:
            parsed = ParsedName(title=clean_title(stem), author=author_dir_name or "Unknown Author")

    canonical_author = normalize_author_dir_name(parsed.author)
    title = parsed.title

    # Final target path
    final_author_dir = target_author_dir.parent / canonical_author
    final_author_dir.mkdir(parents=True, exist_ok=True)
    filename = build_target_filename(title, canonical_author, source.suffix)
    target_path = final_author_dir / safe_fs_name(filename)
    target_path = ensure_unique_path(target_path)

    shutil.copy2(source, target_path)
    logging.debug("Copied %s -> %s", source, target_path)
    return target_path


def process_author_directory(author_dir: Path, target_root: Path) -> int:
    count = 0
    author_name_hint = author_dir.name
    for item in author_dir.iterdir():
        if item.is_file():
            if is_book_file(item):
                if copy_book_to_library(item, target_root / author_name_hint, author_name_hint):
                    count += 1
        elif item.is_dir():
            # Nested folders (e.g., calibre book folders)
            for sub in item.rglob("*"):
                if sub.is_file() and is_book_file(sub):
                    if copy_book_to_library(sub, target_root / author_name_hint, author_name_hint):
                        count += 1
    return count


def process_alphabetical_range_dir(alpha_dir: Path, target_root: Path) -> int:
    count = 0
    for item in alpha_dir.iterdir():
        if item.is_dir():
            count += process_author_directory(item, target_root)
    return count


def process_loose_bucket_dir(bucket_dir: Path, target_root: Path) -> int:
    # Directly contains many files, parse each
    count = 0
    for item in bucket_dir.iterdir():
        if item.is_file() and is_book_file(item):
            if copy_book_to_library(item, target_root / "Unknown Author", "Unknown Author"):
                count += 1
    return count


def rebuild_library(raw_root: Path, target_root: Path) -> None:
    logging.info("Rebuilding full library from %s -> %s", raw_root, target_root)

    processed = 0

    # First pass: handle known special directories
    special_dirs = [raw_root / "_calibre", raw_root / "1 - Anthologie - Collectif - Anonyme"]
    for sdir in special_dirs:
        if sdir.exists() and sdir.is_dir():
            for item in sdir.iterdir():
                if item.is_dir():
                    processed += process_author_directory(item, target_root)

    # Second pass: alphabetical ranges like "AA à AM", "RA à RN", etc.
    for item in raw_root.iterdir():
        if item.is_dir():
            name = item.name
            if name in {"_calibre", "1 - Anthologie - Collectif - Anonyme"}:
                continue
            # Ranges contain digits or the "à" separator
            if any(ch.isdigit() for ch in name) or ("à" in name):
                processed += process_alphabetical_range_dir(item, target_root)

    # Third pass: single-letter buckets like "E", "F", "T", "U", "V", "W", "XYZ"
    for item in raw_root.iterdir():
        if item.is_dir():
            name = item.name
            if name in {"_calibre", "1 - Anthologie - Collectif - Anonyme"}:
                continue
            if (len(name) == 1 and name.isalpha()) or name in {"XYZ", "ZZ-gchampoux.com", "ZZ-www.claryan.com"}:
                processed += process_loose_bucket_dir(item, target_root)

    # Fourth pass: loose files in RAW root
    for item in raw_root.iterdir():
        if item.is_file() and is_book_file(item):
            if copy_book_to_library(item, target_root / "Unknown Author", "Unknown Author"):
                processed += 1

    logging.info("Completed. Total books processed: %s", processed)


def backup_existing_target(target_root: Path) -> Optional[Path]:
    if not target_root.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = target_root.parent / f"{target_root.name}_backup_{timestamp}"
    logging.info("Backing up existing %s -> %s", target_root, backup_dir)
    shutil.move(str(target_root), str(backup_dir))
    return backup_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild full_library from RAW_LIBRARY")
    parser.add_argument("--source", type=Path, default=RAW_DIR_DEFAULT, help="Source RAW_LIBRARY root")
    parser.add_argument("--target", type=Path, default=TARGET_DIR_DEFAULT, help="Target full_library root")
    parser.add_argument("--backup", action="store_true", help="Backup existing target directory if it exists")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    src: Path = args.source
    dst: Path = args.target

    if not src.exists() or not src.is_dir():
        logging.error("Source directory does not exist or is not a directory: %s", src)
        sys.exit(1)

    if args.backup and dst.exists():
        backup_existing_target(dst)

    dst.mkdir(parents=True, exist_ok=True)
    rebuild_library(src, dst)


if __name__ == "__main__":
    main()


