#!/usr/bin/env python3
"""
Extract a small SQLite database from the main `books.db` for production tests.

This script copies:
- books (N selected rows)
- chapters (rows whose book_id is among selected)
- analysis_results (rows whose book_id is among selected)
- recommendations (rows where BOTH source and recommended are among selected)

Defaults:
- source: webapp/databases/books.db
- target: webapp/databases/books_small.db
- count: 50

Usage examples:
  python scripts/extract_small_db.py
  python scripts/extract_small_db.py --count 50
  python scripts/extract_small_db.py --source path/to/books.db --target path/to/books_small.db --count 50 --seed 42
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import List, Tuple
import random
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def ensure_parent_dir(path: Path) -> None:
    parent = path.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


def fetch_table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    if not cols:
        raise RuntimeError(f"No columns found for table: {table}")
    return cols


def fetch_table_sql(conn: sqlite3.Connection, table: str) -> str | None:
    cur = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def create_table_like_source(src_conn: sqlite3.Connection, dst_conn: sqlite3.Connection, table: str) -> None:
    sql = fetch_table_sql(src_conn, table)
    if not sql:
        raise RuntimeError(f"Table '{table}' not found in source database")
    # Use IF NOT EXISTS to allow re-runs
    sql = sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")
    dst_conn.execute(sql)


def copy_selected_ids(conn: sqlite3.Connection, table: str, id_column: str, count: int, seed: int | None) -> List[str]:
    if seed is not None:
        random.seed(seed)
    cur = conn.execute(f"SELECT {id_column} FROM {table}")
    all_ids = [row[0] for row in cur.fetchall()]
    if not all_ids:
        return []
    if len(all_ids) <= count:
        return all_ids
    return random.sample(all_ids, count)


def insert_rows_by_ids(src_conn: sqlite3.Connection, dst_conn: sqlite3.Connection, table: str, id_column: str, ids: List[str]) -> int:
    if not ids:
        return 0
    src_cols = fetch_table_columns(src_conn, table)
    dst_cols = fetch_table_columns(dst_conn, table)

    # Use the intersection of columns to keep compatibility across schema versions
    common_cols = [c for c in src_cols if c in dst_cols]
    if id_column not in common_cols:
        raise RuntimeError(f"ID column '{id_column}' not present in destination table '{table}'")

    placeholders = ",".join(["?"] * len(common_cols))
    column_list = ",".join(common_cols)
    select_cols = ",".join(common_cols)

    # Fetch in batches to avoid huge IN clauses; but with 50 IDs it's fine
    q_marks = ",".join(["?"] * len(ids))
    select_sql = f"SELECT {select_cols} FROM {table} WHERE {id_column} IN ({q_marks})"
    rows = src_conn.execute(select_sql, ids).fetchall()

    if not rows:
        return 0

    insert_sql = f"INSERT OR REPLACE INTO {table} ({column_list}) VALUES ({placeholders})"
    dst_conn.executemany(insert_sql, [tuple(row) for row in rows])
    return len(rows)


def insert_rows_by_foreign_ids(
    src_conn: sqlite3.Connection,
    dst_conn: sqlite3.Connection,
    table: str,
    fk_column: str,
    fk_ids: List[str],
) -> int:
    if not fk_ids:
        return 0
    src_cols = fetch_table_columns(src_conn, table)
    dst_cols = fetch_table_columns(dst_conn, table)
    common_cols = [c for c in src_cols if c in dst_cols]
    placeholders = ",".join(["?"] * len(common_cols))
    column_list = ",".join(common_cols)
    select_cols = ",".join(common_cols)
    q_marks = ",".join(["?"] * len(fk_ids))
    select_sql = f"SELECT {select_cols} FROM {table} WHERE {fk_column} IN ({q_marks})"
    rows = src_conn.execute(select_sql, fk_ids).fetchall()
    if not rows:
        return 0
    insert_sql = f"INSERT OR REPLACE INTO {table} ({column_list}) VALUES ({placeholders})"
    dst_conn.executemany(insert_sql, [tuple(row) for row in rows])
    return len(rows)


def insert_intersecting_recommendations(
    src_conn: sqlite3.Connection,
    dst_conn: sqlite3.Connection,
    selected_ids: List[str],
) -> int:
    # Only copy recommendations where both source and recommended are in the subset
    try:
        # Discover columns dynamically
        src_cols = fetch_table_columns(src_conn, "recommendations")
        dst_cols = fetch_table_columns(dst_conn, "recommendations")
    except RuntimeError:
        # Table may not exist in some datasets; skip
        return 0

    common_cols = [c for c in src_cols if c in dst_cols]
    if not common_cols:
        return 0

    column_list = ",".join(common_cols)
    select_cols = ",".join(common_cols)
    placeholders = ",".join(["?"] * len(common_cols))

    # Build query with two IN clauses
    if not selected_ids:
        return 0
    q_marks_a = ",".join(["?"] * len(selected_ids))
    q_marks_b = ",".join(["?"] * len(selected_ids))
    sql = (
        f"SELECT {select_cols} FROM recommendations "
        f"WHERE source_book_id IN ({q_marks_a}) AND recommended_book_id IN ({q_marks_b})"
    )
    rows = src_conn.execute(sql, selected_ids + selected_ids).fetchall()
    if not rows:
        return 0
    insert_sql = f"INSERT OR REPLACE INTO recommendations ({column_list}) VALUES ({placeholders})"
    dst_conn.executemany(insert_sql, [tuple(row) for row in rows])
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract a small SQLite DB from books.db")
    default_source = Path(__file__).resolve().parents[1] / "webapp" / "databases" / "books.db"
    default_target = Path(__file__).resolve().parents[1] / "webapp" / "databases" / "books_small.db"
    parser.add_argument("--source", type=Path, default=default_source, help="Path to source books.db")
    parser.add_argument("--target", type=Path, default=default_target, help="Path to target small db")
    parser.add_argument("--count", type=int, default=50, help="Number of books to extract")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    src_path: Path = args.source
    dst_path: Path = args.target
    count: int = args.count
    seed = args.seed

    if not src_path.exists():
        logger.error(f"Source database not found: {src_path}")
        return 1

    ensure_parent_dir(dst_path)

    logger.info(f"Source DB: {src_path}")
    logger.info(f"Target DB: {dst_path}")
    logger.info(f"Books to extract: {count}")

    with sqlite3.connect(str(src_path)) as src, sqlite3.connect(str(dst_path)) as dst:
        src.row_factory = sqlite3.Row
        dst.row_factory = sqlite3.Row
        # Disable foreign keys during schema creation and bulk inserts
        dst.execute("PRAGMA foreign_keys=OFF")
        try:
            # Create necessary tables by cloning source schema when available
            for table in ("books", "chapters", "analysis_results"):
                create_table_like_source(src, dst, table)
            # recommendations may or may not exist
            try:
                create_table_like_source(src, dst, "recommendations")
            except Exception:
                logger.info("No recommendations table found in source; skipping")

            # Select IDs
            selected_ids = copy_selected_ids(src, "books", "id", count, seed)
            if not selected_ids:
                logger.warning("No books found to copy. Exiting with empty target DB.")
                dst.commit()
                return 0

            # Insert books
            copied_books = insert_rows_by_ids(src, dst, "books", "id", selected_ids)

            # Insert related tables
            copied_chapters = insert_rows_by_foreign_ids(src, dst, "chapters", "book_id", selected_ids)
            copied_analysis = insert_rows_by_foreign_ids(src, dst, "analysis_results", "book_id", selected_ids)
            copied_recs = insert_intersecting_recommendations(src, dst, selected_ids)

            dst.commit()

            logger.info(
                "Copied: %s books, %s chapters, %s analysis_results, %s recommendations",
                copied_books, copied_chapters, copied_analysis, copied_recs,
            )

        finally:
            dst.execute("PRAGMA foreign_keys=ON")

    # Optional vacuum to shrink file size
    with sqlite3.connect(str(dst_path)) as dst:
        dst.execute("VACUUM")

    logger.info("Done: %s", dst_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


