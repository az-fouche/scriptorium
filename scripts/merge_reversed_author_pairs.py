#!/usr/bin/env python3
"""
Automatically merge reversed author directory pairs by inspecting EPUB metadata.

For each pair like "A, B" and "B, A" under data/full_library:
- Collect all EPUBs from both dirs
- Parse authors from EPUB metadata and normalize to canonical dir names
- Choose canonical author by majority vote (fallback to heuristic: dir with more books,
  otherwise prefer the variant whose left part looks like a last name i.e., more uppercase)
- Move/merge all books into the chosen canonical directory with collision-safe renaming

Writes a summary to stdout and a detailed log to data/transfers/merge_reversed_pairs.log
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


# Add src to path for EpubParser import
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from epub_parser import EpubParser  # type: ignore


TARGET_DIR_DEFAULT = Path("data/full_library")
LOG_FILE = Path("data/transfers/merge_reversed_pairs.log")

SPECIAL_AUTHORS = {"Collectif", "Anonyme", "Anthologie", "Unknown Author"}


def normalize_token(s: str) -> str:
    n = unicodedata.normalize("NFKD", s or "")
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = n.lower().strip()
    n = re.sub(r"\s+", " ", n)
    return n


def titlecase_firstname(firstname: str) -> str:
    parts = (firstname or "").split()
    out: List[str] = []
    for p in parts:
        if p.lower() in {"de", "du", "des", "le", "la", "van", "von", "del", "della", "di"}:
            out.append(p.lower())
        else:
            out.append(p[:1].upper() + p[1:])
    return " ".join(out)


def safe_fs_name(name: str) -> str:
    name = unicodedata.normalize("NFC", name or "").replace("\u200b", "").strip()
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"__+", "_", name)
    return name.strip(" ._") or "Untitled"


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
        last_norm = last.upper() if last else last
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

    return safe_fs_name(tokens[0][:1].upper() + tokens[0][1:].lower()) if tokens else "Unknown Author"


def split_author_dir(name: str) -> Tuple[str, str] | None:
    if name in SPECIAL_AUTHORS:
        return None
    if "," not in name:
        return None
    left, right = [s.strip() for s in name.split(",", 1)]
    if not left or not right:
        return None
    return normalize_token(left), normalize_token(right)


def find_reversed_pairs(root: Path) -> List[Tuple[Path, Path]]:
    key_to_dir: Dict[Tuple[str, str], Path] = {}
    for d in root.iterdir():
        if not d.is_dir():
            continue
        pair = split_author_dir(d.name)
        if pair is None:
            continue
        if pair in key_to_dir:
            # Same key duplicate; ignore here (handled by sanitize)
            continue
        key_to_dir[pair] = d

    pairs: List[Tuple[Path, Path]] = []
    visited: set[Tuple[str, str]] = set()
    for (a, b), dir_a in list(key_to_dir.items()):
        if (a, b) in visited:
            continue
        rev = (b, a)
        dir_b = key_to_dir.get(rev)
        if dir_b is not None and rev not in visited:
            # Order pairs deterministically to avoid duplicates
            if str(dir_a) <= str(dir_b):
                pairs.append((dir_a, dir_b))
            else:
                pairs.append((dir_b, dir_a))
            visited.add((a, b))
            visited.add(rev)

    return pairs


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    base = path.stem
    ext = path.suffix
    parent = path.parent
    c = 2
    while True:
        candidate = parent / f"{base}_{c}{ext}"
        if not candidate.exists():
            return candidate
        c += 1


def uppercase_ratio(s: str) -> float:
    if not s:
        return 0.0
    letters = [ch for ch in s if ch.isalpha()]
    if not letters:
        return 0.0
    upp = sum(1 for ch in letters if ch.isupper())
    return upp / len(letters)


def choose_canonical_by_metadata(dir_a: Path, dir_b: Path, ep: EpubParser) -> str:
    # Collect votes for canonical author names from both dirs
    votes: Counter = Counter()
    for d in (dir_a, dir_b):
        for p in d.glob("*.epub"):
            try:
                info = ep.get_book_info(str(p))
                for a in info.get("authors") or []:
                    canon = normalize_author_dir_name(a)
                    votes[canon] += 1
            except Exception:
                continue

    if votes:
        canon, _ = votes.most_common(1)[0]
        return canon

    # Fallback heuristic: prefer the variant where left part looks like LASTNAME
    left_a = dir_a.name.split(",", 1)[0].strip()
    left_b = dir_b.name.split(",", 1)[0].strip()
    score_a = uppercase_ratio(left_a)
    score_b = uppercase_ratio(left_b)
    if score_a > score_b:
        # Keep left of dir_a as last: build canonical from dir_a order
        last = left_a
        first = dir_a.name.split(",", 1)[1].strip()
        return normalize_author_dir_name(f"{last}, {first}")
    elif score_b > score_a:
        last = left_b
        first = dir_b.name.split(",", 1)[1].strip()
        return normalize_author_dir_name(f"{last}, {first}")

    # Final fallback: prefer directory with more EPUBs
    count_a = len(list(dir_a.glob("*.epub")))
    count_b = len(list(dir_b.glob("*.epub")))
    base_dir = dir_a if count_a >= count_b else dir_b
    return normalize_author_dir_name(base_dir.name)


def merge_pair(dir_a: Path, dir_b: Path, canonical_name: str, dry_run: bool, log) -> Tuple[Path, str]:
    dest = dir_a.parent / canonical_name
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)
    moved = 0
    for d in (dir_a, dir_b):
        for item in d.iterdir():
            target = dest / item.name
            target = ensure_unique_path(target)
            if not dry_run:
                shutil.move(str(item), str(target))
            moved += 1
        if not dry_run:
            try:
                d.rmdir()
            except OSError:
                pass
    if log:
        log.write(f"MERGED\t{dir_a.name} + {dir_b.name} -> {canonical_name}\titems={moved}\n")
    return dest, "merged"


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge reversed author directory pairs into canonical form")
    parser.add_argument("--target", type=Path, default=TARGET_DIR_DEFAULT, help="Target full_library root")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not move files")
    args = parser.parse_args()

    root: Path = args.target
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Target directory does not exist or is not a directory: {root}")

    ep = EpubParser()
    pairs = find_reversed_pairs(root)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log = None if args.dry_run else LOG_FILE.open("a", encoding="utf-8")

    merged = 0
    for a, b in pairs:
        canonical = choose_canonical_by_metadata(a, b, ep)
        merge_pair(a, b, canonical, args.dry_run, log)
        merged += 1

    if log:
        log.write(f"SUMMARY\tmerged_pairs={merged}\n")
        log.close()

    print(f"Reversed pairs found: {len(pairs)} | Merged: {merged} | Log: {LOG_FILE}")


if __name__ == "__main__":
    main()


