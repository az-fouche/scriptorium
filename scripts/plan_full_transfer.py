#!/usr/bin/env python3
"""
Plan transfer from RAW_LIBRARY to full_library with preserved EPUB filenames and
unified author directories.

Inputs:
- data/transfers/raw_inventory.json (from audit)
- data/author_aliases.json (optional): {"raw_author": "CANONICAL_AUTHOR"}

Outputs (under --out):
- author_mapping.tsv: raw_author\tcanonical_author\tsource
- manifest.tsv: source_path\ttarget_path\tauthor\treasons (comma-separated)
- collisions.tsv: target_path\tcount (for pre-detected name collisions)

No files are copied; this is a dry-run planning step.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


RAW_DIR_DEFAULT = Path("data/RAW_LIBRARY")
OUT_DIR_DEFAULT = Path("data/transfers")
TARGET_DIR_DEFAULT = Path("data/full_library")


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

    # Single-word author: capitalize only first letter
    return safe_fs_name(tokens[0][:1].upper() + tokens[0][1:]) if tokens else "Unknown"


def canonical_key(name: str) -> str:
    n = unicodedata.normalize("NFKD", name)
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = n.lower()
    n = re.sub(r"\s+", " ", n).strip()
    return n


def load_inventory(inventory_file: Path) -> List[dict]:
    data = json.loads(inventory_file.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("raw_inventory.json must contain a list")
    return data


def load_aliases(aliases_file: Optional[Path]) -> Dict[str, str]:
    if not aliases_file or not aliases_file.exists():
        return {}
    data = json.loads(aliases_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("author_aliases.json must be an object mapping raw->canonical")
    return data


def choose_canonical_author(raw_author: Optional[str], aliases: Dict[str, str]) -> Tuple[str, str]:
    if not raw_author:
        return "Unknown Author", "fallback"
    if raw_author in aliases:
        return aliases[raw_author], "alias"
    # Try normalization
    norm = normalize_author_dir_name(raw_author)
    # If single-word normalized to uppercase (due to safety), adjust to capitalized form
    if "," not in norm and " " not in norm:
        norm = norm[:1].upper() + norm[1:].lower()
    return norm, "normalized"


def plan(raw_root: Path, target_root: Path, out_root: Path, aliases_file: Optional[Path]) -> None:
    inventory_file = out_root / "raw_inventory.json"
    if not inventory_file.exists():
        raise SystemExit(f"Missing inventory file: {inventory_file}. Run audit first.")
    items = load_inventory(inventory_file)
    aliases = load_aliases(aliases_file)

    # Build author mapping and target paths
    author_map: Dict[str, Tuple[str, str]] = {}  # raw -> (canonical, source)
    manifest_rows: List[Tuple[str, str, str, str]] = []
    target_name_counts: Dict[str, int] = defaultdict(int)

    for it in items:
        src = it.get("source_path")
        stem_author = it.get("author_hint")
        author_canon, source = choose_canonical_author(stem_author, aliases)
        author_map.setdefault(stem_author or "", (author_canon, source))

        src_path = Path(src)
        original_name = src_path.name  # preserve filename
        safe_name = safe_fs_name(original_name)
        target_path = target_root / author_canon / safe_name

        reasons: List[str] = []
        if safe_name != original_name:
            reasons.append("illegal_chars_fixed")
        if (it.get("author_hint_source") or ""):
            reasons.append(f"author_from_{it['author_hint_source']}")
        else:
            reasons.append("author_unknown_fallback")

        key = str(target_path).lower()
        target_name_counts[key] += 1
        if target_name_counts[key] > 1:
            reasons.append("predicted_collision")

        manifest_rows.append((src, str(target_path), author_canon, ",".join(reasons)))

    # Write outputs
    out_root.mkdir(parents=True, exist_ok=True)
    with (out_root / "author_mapping.tsv").open("w", encoding="utf-8") as f:
        f.write("raw_author\tcanonical_author\tsource\n")
        for raw_author, (canon, src) in sorted(author_map.items(), key=lambda x: (x[1][0], x[0])):
            f.write(f"{raw_author}\t{canon}\t{src}\n")

    with (out_root / "manifest.tsv").open("w", encoding="utf-8") as f:
        f.write("source_path\ttarget_path\tauthor\treasons\n")
        for row in manifest_rows:
            f.write("\t".join(row) + "\n")

    # Collisions pre-detected by same path occurrence count
    collisions = [(path, count) for path, count in target_name_counts.items() if count > 1]
    with (out_root / "collisions.tsv").open("w", encoding="utf-8") as f:
        f.write("target_path\tcount\n")
        for path, count in sorted(collisions, key=lambda x: (-x[1], x[0])):
            f.write(f"{path}\t{count}\n")

    print(f"Planned {len(manifest_rows)} EPUB transfers. Potential name collisions: {len(collisions)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan transfer to full_library with preserved filenames and unified authors")
    parser.add_argument("--source", type=Path, default=RAW_DIR_DEFAULT, help="Source RAW_LIBRARY root (for info only)")
    parser.add_argument("--target", type=Path, default=TARGET_DIR_DEFAULT, help="Target full_library root (for manifest paths)")
    parser.add_argument("--out", type=Path, default=OUT_DIR_DEFAULT, help="Output directory for plan files")
    parser.add_argument("--aliases", type=Path, default=Path("data/author_aliases.json"), help="Optional JSON mapping raw->canonical")
    args = parser.parse_args()

    plan(args.source, args.target, args.out, args.aliases)


if __name__ == "__main__":
    main()


