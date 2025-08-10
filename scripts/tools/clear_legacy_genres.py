#!/usr/bin/env python3
"""
Clear legacy v1 genre fields from the SQLite database so only unified tags remain visible in the webapp.

Usage:
  python scripts/tools/clear_legacy_genres.py --db webapp/databases/books.db

If --db is omitted, defaults to webapp/databases/books.db relative to repo root.
"""

import argparse
import sqlite3
from pathlib import Path


def clear_genres(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        # Set legacy genre fields to empty values
        cur.execute(
            """
            UPDATE books
            SET
              primary_genre = '',
              primary_confidence = 0.0,
              secondary_genres = '[]',
              secondary_confidences = '[]'
            """
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    default_db = repo_root / 'webapp' / 'databases' / 'books.db'

    parser = argparse.ArgumentParser(description='Clear legacy genre fields from database')
    parser.add_argument('--db', type=str, default=str(default_db), help='Path to SQLite database file')
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    updated = clear_genres(db_path)
    print(f"Cleared legacy genres in {updated} rows: {db_path}")


if __name__ == '__main__':
    main()


