#!/usr/bin/env python3
"""
Small helper to re-index a subset (10 books) into the webapp database.

Usage:
  python scripts/reindex_10.py
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    db_path = PROJECT_ROOT / "webapp" / "databases" / "books.db"
    data_dir = PROJECT_ROOT / "data" / "small_library"
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "index_library.py"),
        "--db-path", str(db_path),
        "--workers", "2",
        "index", str(data_dir),
        "--max-files", "10",
        "--no-skip-existing",
    ]
    return subprocess.call(cmd)

if __name__ == "__main__":
    raise SystemExit(main())


