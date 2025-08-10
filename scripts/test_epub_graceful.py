#!/usr/bin/env python3
"""
Quick check that EPUB parsing fails gracefully and does not raise.

Usage:
  python scripts/test_epub_graceful.py <path_to_epub>
"""
import os
import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from epub_parser import EpubParser


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_epub_graceful.py <path_to_epub>")
        return 2

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return 2

    parser = EpubParser()
    try:
        metadata, content, cover = parser.parse_book(file_path)
    except Exception as e:
        # Should not happen after hardening
        print(f"RAISED: {e}")
        return 1

    has_text = bool(content and getattr(content, 'full_text', '').strip())
    print("Parsed title:", getattr(metadata, 'title', 'Unknown'))
    print("Text present:", has_text)
    print("Cover present:", bool(cover))
    # Exit code 0 even if no text; purpose is graceful handling
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




