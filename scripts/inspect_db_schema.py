#!/usr/bin/env python3
"""
Inspect current SQLite schema of the books database.

Usage:
  python scripts/inspect_db_schema.py [db_path]
Defaults to webapp/databases/books.db
"""
import sys
from pathlib import Path
import sqlite3


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (project_root / 'webapp' / 'databases' / 'books.db')
    print(f"DB: {db_path}")
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        print("\n-- PRAGMA schema version --")
        for row in cur.execute('PRAGMA user_version'):
            print(row)
        print("\n-- Books table info --")
        for row in cur.execute('PRAGMA table_info(books)'):
            print(row)
        print("\n-- Chapters table info --")
        for row in cur.execute('PRAGMA table_info(chapters)'):
            print(row)
        print("\n-- Create statements --")
        for row in cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('books','chapters')"):
            print(row[0], ':', row[1])
    finally:
        conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())



