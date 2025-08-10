#!/usr/bin/env python3
"""
Report author directory pairs that appear as reversed name orders, e.g. both
"LASTNAME, Firstname" and "Firstname, LASTNAME" existing under data/full_library.

Outputs:
- Prints pairs to stdout
- Writes detailed list to data/transfers/reversed_pairs.txt
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Set, Tuple


TARGET_DIR_DEFAULT = Path("data/full_library")
REPORT_FILE = Path("data/transfers/reversed_pairs.txt")

SPECIAL_AUTHORS = {"Collectif", "Anonyme", "Anthologie", "Unknown Author"}


def normalize_token(s: str) -> str:
    n = unicodedata.normalize("NFKD", s or "")
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = n.lower().strip()
    n = re.sub(r"\s+", " ", n)
    return n


def split_author_dir(name: str) -> Tuple[str, str] | None:
    if name in SPECIAL_AUTHORS:
        return None
    if "," not in name:
        return None
    parts = name.split(",", 1)
    left = normalize_token(parts[0])
    right = normalize_token(parts[1])
    if not left or not right:
        return None
    return left, right


def find_reversed_pairs(root: Path) -> List[Tuple[str, List[str], str, List[str]]]:
    # Map normalized tuple -> actual names
    key_to_names: Dict[Tuple[str, str], List[str]] = {}
    for d in root.iterdir():
        if not d.is_dir():
            continue
        pair = split_author_dir(d.name)
        if pair is None:
            continue
        key_to_names.setdefault(pair, []).append(d.name)

    seen: Set[Tuple[str, str]] = set()
    results: List[Tuple[str, List[str], str, List[str]]] = []
    for (a, b), names_a in key_to_names.items():
        if (a, b) in seen:
            continue
        rev = (b, a)
        if rev in key_to_names:
            names_b = key_to_names[rev]
            # Create a deterministic id for the pair
            pair_id = f"{a}__{b}" if (a, b) <= (b, a) else f"{b}__{a}"
            results.append((pair_id, sorted(set(names_a)), pair_id[::-1], sorted(set(names_b))))
            seen.add((a, b))
            seen.add(rev)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Report reversed author directory pairs in full_library")
    parser.add_argument("--target", type=Path, default=TARGET_DIR_DEFAULT, help="Target full_library root")
    args = parser.parse_args()

    root: Path = args.target
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Target directory does not exist or is not a directory: {root}")

    pairs = find_reversed_pairs(root)

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_FILE.open("w", encoding="utf-8") as f:
        for _, names_a, _, names_b in pairs:
            f.write(" | ".join([", ".join(names_a), ", ".join(names_b)]) + "\n")

    if not pairs:
        print("No reversed author directory pairs found.")
    else:
        print(f"Found {len(pairs)} reversed author directory pair(s). Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()


