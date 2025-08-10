#!/usr/bin/env python3
"""
Scan data/full_library author directories, fix those that can be normalized,
and prefix remaining outliers with "__OUTLIER__ ".

Behavior:
- Author dirs that already conform are left untouched.
- If a dir can be normalized to a conforming canonical name, it is renamed/merged.
- If it still does not conform, it is renamed to "__OUTLIER__ <original>".

Outputs a summary and writes a detailed report to data/transfers/outliers_report.txt
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import unicodedata
from pathlib import Path
from typing import List, Tuple


TARGET_DIR_DEFAULT = Path("data/full_library")
REPORT_FILE = Path("data/transfers/outliers_report.txt")


SPECIAL_AUTHORS = {"Collectif", "Anonyme", "Anthologie", "Unknown Author"}


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

    # Single-word author: capitalize first letter only
    return safe_fs_name(tokens[0][:1].upper() + tokens[0][1:].lower()) if tokens else "Unknown Author"


def is_conforming_author_dir(name: str) -> bool:
    if name in SPECIAL_AUTHORS:
        return True
    # Already outlier tagged
    if name.startswith("__OUTLIER__ "):
        return False
    # Single-word author, capitalized
    if "," not in name and " " not in name:
        return bool(re.match(r"^[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’.\-]*$", name))
    # Standard "LASTNAME, Firstname" with one comma
    if name.count(",") != 1:
        return False
    last, first = [s.strip() for s in name.split(",", 1)]
    if not last or not first:
        return False
    # Last name should be mostly uppercase letters/spaces/hyphens/periods/’
    if not re.match(r"^[A-Z0-9À-ÖØ-Þ '’.\-]+$", last):
        return False
    # First name should start uppercase; allow lowercase particles within
    if not re.match(r"^[A-ZÀ-ÖØ-ß]", first):
        return False
    return True


def ensure_unique_dir(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.parent / f"{path.name}_{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def merge_or_rename(src_dir: Path, dest_dir: Path) -> Tuple[Path, str]:
    if src_dir == dest_dir:
        return dest_dir, "noop"
    dest_dir = ensure_unique_dir(dest_dir) if dest_dir.exists() and dest_dir.resolve() != src_dir.resolve() else dest_dir
    if not dest_dir.exists():
        src_dir.rename(dest_dir)
        return dest_dir, "renamed"
    # Merge contents
    for item in src_dir.iterdir():
        target = dest_dir / item.name
        if target.exists():
            base, ext = os.path.splitext(item.name)
            c = 1
            while True:
                candidate = dest_dir / f"{base}_{c}{ext}"
                if not candidate.exists():
                    target = candidate
                    break
                c += 1
        if item.is_dir():
            shutil.move(str(item), str(target))
        else:
            shutil.move(str(item), str(target))
    try:
        src_dir.rmdir()
    except OSError:
        pass
    return dest_dir, "merged"


def process_authors(root: Path, dry_run: bool = False) -> Tuple[int, int, int]:
    fixed = 0
    flagged = 0
    conforming = 0
    lines: List[str] = []

    authors = [d for d in root.iterdir() if d.is_dir()]
    for d in sorted(authors, key=lambda p: p.name.lower()):
        name = d.name
        if is_conforming_author_dir(name):
            conforming += 1
            lines.append(f"OK   | {name}")
            continue

        # Try to normalize
        canon = normalize_author_dir_name(name)
        if is_conforming_author_dir(canon):
            lines.append(f"FIX  | {name} -> {canon}")
            if not dry_run:
                dest = d.parent / canon
                _, action = merge_or_rename(d, dest)
            fixed += 1
            continue

        # Still not conforming: prefix as outlier
        out_name = f"__OUTLIER__ {safe_fs_name(name)}"
        lines.append(f"FLAG | {name} -> {out_name}")
        if not dry_run:
            dest = d.parent / out_name
            dest = ensure_unique_dir(dest)
            d.rename(dest)
        flagged += 1

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    return fixed, flagged, conforming


def main() -> None:
    parser = argparse.ArgumentParser(description="Flag and fix outlier author directories in full_library")
    parser.add_argument("--target", type=Path, default=TARGET_DIR_DEFAULT, help="Target full_library root")
    parser.add_argument("--dry-run", action="store_true", help="Only report, do not perform changes")
    args = parser.parse_args()

    root: Path = args.target
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Target directory does not exist or is not a directory: {root}")

    fixed, flagged, conforming = process_authors(root, dry_run=args.dry_run)
    print(f"Conforming: {conforming} | Fixed: {fixed} | Flagged: {flagged}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()


