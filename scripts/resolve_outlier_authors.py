#!/usr/bin/env python3
"""
Resolve outlier author directories by inspecting EPUB metadata.

Process:
- Locate author directories in full_library starting with "__OUTLIER__ ".
- For each, parse contained .epub files to extract authors.
- If a clear canonical author emerges (e.g., single author or strong majority),
  move EPUBs into the canonical author directory (creating/merging as needed).
- Otherwise, leave the outlier directory in place for manual review.

Writes a detailed report to data/transfers/outliers_resolved.txt
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


# Add src to path for EpubParser import
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from epub_parser import EpubParser  # type: ignore


TARGET_DIR_DEFAULT = Path("data/full_library")
REPORT_FILE = Path("data/transfers/outliers_resolved.txt")


def safe_fs_name(name: str) -> str:
    name = unicodedata.normalize("NFC", name or "").replace("\u200b", "").strip()
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"__+", "_", name)
    return name.strip(" ._") or "Untitled"


def titlecase_firstname(firstname: str) -> str:
    parts = (firstname or "").split()
    out: List[str] = []
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


def canonical_key(name: str) -> str:
    n = unicodedata.normalize("NFKD", name)
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = n.lower()
    n = re.sub(r"\s+", " ", n).strip()
    return n


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


def collect_author_votes(epub_paths: List[Path], parser: EpubParser) -> Tuple[Counter, Dict[str, str], List[Tuple[Path, List[str]]]]:
    votes: Counter = Counter()
    canon_to_display: Dict[str, str] = {}
    details: List[Tuple[Path, List[str]]] = []
    for p in epub_paths:
        try:
            info = parser.get_book_info(str(p))
            authors = info.get('authors') or []
        except Exception:
            authors = []
        details.append((p, authors))
        for a in authors:
            canon_display = normalize_author_dir_name(a)
            key = canonical_key(canon_display)
            votes[key] += 1
            canon_to_display.setdefault(key, canon_display)
    return votes, canon_to_display, details


def resolve_outlier_dir(outlier_dir: Path, dry_run: bool, parser: EpubParser, majority_threshold: float = 0.8) -> Tuple[str, List[str]]:
    actions: List[str] = []
    epubs = [p for p in outlier_dir.rglob('*.epub') if p.is_file()]
    if not epubs:
        actions.append("no_epubs_found")
        return outlier_dir.name, actions

    votes, canon_to_display, details = collect_author_votes(epubs, parser)
    total_votes = sum(votes.values())
    if total_votes == 0:
        actions.append("no_authors_in_metadata")
        return outlier_dir.name, actions

    key, count = votes.most_common(1)[0]
    top_ratio = count / total_votes if total_votes > 0 else 0.0
    target_author = canon_to_display[key]

    # Decide if we are confident enough to move
    if len(votes) == 1 or top_ratio >= majority_threshold:
        dest_dir = outlier_dir.parent / target_author
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
        moved = 0
        for p in epubs:
            target = dest_dir / p.name
            target = ensure_unique_path(target)
            if not dry_run:
                shutil.move(str(p), str(target))
            moved += 1
        # Clean up outlier dir if empty
        if not dry_run:
            try:
                # Remove any empty subdirs, then the dir itself if empty
                for sub in sorted(outlier_dir.rglob('*'), key=lambda x: len(str(x).split(os.sep)), reverse=True):
                    if sub.is_dir():
                        try:
                            sub.rmdir()
                        except OSError:
                            pass
                outlier_dir.rmdir()
            except OSError:
                pass
        actions.append(f"moved_to:{target_author}:{moved}")
    else:
        actions.append(f"ambiguous_authors:{dict(votes)}")

    return outlier_dir.name, actions


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve outlier author dirs by inspecting EPUB metadata")
    parser.add_argument("--target", type=Path, default=TARGET_DIR_DEFAULT, help="Target full_library root")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not move files")
    parser.add_argument("--threshold", type=float, default=0.8, help="Majority threshold for author consensus")
    args = parser.parse_args()

    root: Path = args.target
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Target directory does not exist or is not a directory: {root}")

    outliers = [d for d in root.iterdir() if d.is_dir() and d.name.startswith("__OUTLIER__ ")]
    outliers.sort(key=lambda p: p.name.lower())

    ep = EpubParser()

    lines: List[str] = []
    fixed = 0
    ambiguous = 0
    for d in outliers:
        name, actions = resolve_outlier_dir(d, args.dry_run, ep, args.threshold)
        lines.append(f"{name}\t{';'.join(actions)}")
        if any(a.startswith("moved_to:") for a in actions):
            fixed += 1
        elif any(a.startswith("ambiguous_authors:") for a in actions):
            ambiguous += 1

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Outliers: {len(outliers)} | Fixed: {fixed} | Ambiguous: {ambiguous}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()


