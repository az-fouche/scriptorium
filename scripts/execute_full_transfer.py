#!/usr/bin/env python3
"""
Execute manifest-based copy from RAW_LIBRARY to full_library.

Manifest format (TSV): source_path\ttarget_path\tauthor\treasons

Rules:
- Copy only if target not present, or present but different size/hash (optional hash check).
- Ensure parent directories exist.
- Append _2, _3, ... to basename if a distinct file would overwrite an existing different file.
- Preserve timestamps with shutil.copy2.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple


TARGET_DIR_DEFAULT = Path("data/full_library")


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def ensure_unique_target(target: Path) -> Path:
    if not target.exists():
        return target
    base = target.stem
    ext = target.suffix
    parent = target.parent
    counter = 2
    while True:
        candidate = parent / f"{base}_{counter}{ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def copy_with_collision_handling(src: Path, dst: Path, compute_hash: bool) -> Tuple[Path, str]:
    # If destination exists, decide whether to skip, replace, or create a suffixed copy
    if dst.exists():
        try:
            if compute_hash:
                src_hash = file_sha256(src)
                dst_hash = file_sha256(dst)
                if src_hash == dst_hash:
                    return dst, "skipped_same_hash"
            else:
                if src.stat().st_size == dst.stat().st_size:
                    return dst, "skipped_same_size"
        except Exception:
            pass
        dst = ensure_unique_target(dst)

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst, "copied"


def execute(manifest_file: Path, target_root: Path, verify_hash: bool, log_file: Optional[Path]) -> None:
    if not manifest_file.exists():
        raise SystemExit(f"Manifest not found: {manifest_file}")

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_file.open("a", encoding="utf-8")
    else:
        log_handle = None

    copied = 0
    skipped = 0
    created_authors = 0
    seen_authors = set()

    with manifest_file.open("r", encoding="utf-8") as f:
        header = f.readline()
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            src_str, dst_str = parts[0], parts[1]
            src = Path(src_str)
            dst = Path(dst_str)

            if not src.exists():
                if log_handle:
                    log_handle.write(f"MISSING\t{src}\n")
                continue

            if dst.parent not in seen_authors and not dst.parent.exists():
                created_authors += 1
                seen_authors.add(dst.parent)

            final_dst, status = copy_with_collision_handling(src, dst, verify_hash)
            if status.startswith("skipped"):
                skipped += 1
            else:
                copied += 1
            if log_handle:
                log_handle.write(f"{status}\t{src}\t{final_dst}\n")

    if log_handle:
        log_handle.write(f"SUMMARY\tcopied={copied}\tskipped={skipped}\tauthors_created={created_authors}\n")
        log_handle.close()

    print(f"Copied: {copied} | Skipped: {skipped} | Author dirs created: {created_authors}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute manifest-based transfer to full_library")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to manifest.tsv produced by planning step")
    parser.add_argument("--target", type=Path, default=TARGET_DIR_DEFAULT, help="Target full_library root")
    parser.add_argument("--verify-hash", action="store_true", help="Compute SHA-256 to detect identical files (slower)")
    parser.add_argument("--log", type=Path, default=Path("data/transfers/transfer.log"), help="Append log file path")
    parser.add_argument("--backup", action="store_true", help="Backup existing target directory if it exists (move aside with timestamp)")
    args = parser.parse_args()

    if args.backup and args.target.exists():
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = args.target.parent / f"{args.target.name}_backup_{ts}"
        print(f"Backing up existing {args.target} -> {backup_dir}")
        shutil.move(str(args.target), str(backup_dir))

    args.target.mkdir(parents=True, exist_ok=True)

    execute(args.manifest, args.target, args.verify_hash, args.log)


if __name__ == "__main__":
    main()


