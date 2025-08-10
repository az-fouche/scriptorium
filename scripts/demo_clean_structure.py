#!/usr/bin/env python3
"""
Demonstration script showing how easy it is to work with the new clean library structure.

This script demonstrates various operations that are now much simpler with the
refactored library structure.
"""

import os
from pathlib import Path
from collections import defaultdict
import json

def demo_library_operations():
    """Demonstrate various operations on the clean library structure."""
    
    library_path = Path("data/full_library_clean")
    
    print("=== Library Structure Demo ===\n")
    
    # 1. List all authors
    print("1. Listing all authors:")
    authors = [d.name for d in library_path.iterdir() if d.is_dir()]
    authors.sort()
    print(f"   Total authors: {len(authors)}")
    print(f"   First 10 authors: {authors[:10]}")
    print(f"   Last 10 authors: {authors[-10:]}")
    print()
    
    # 2. Count books per author
    print("2. Books per author (top 10):")
    author_book_counts = {}
    for author_dir in library_path.iterdir():
        if author_dir.is_dir():
            book_count = len([f for f in author_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.epub', '.pdf', '.mobi']])
            author_book_counts[author_dir.name] = book_count
    
    top_authors = sorted(author_book_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for author, count in top_authors:
        print(f"   {author}: {count} books")
    print()
    
    # 3. Find specific author
    print("3. Finding Isaac Asimov's books:")
    asimov_dir = library_path / "Isaac Asimov"
    if asimov_dir.exists():
        asimov_books = [f.name for f in asimov_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.epub', '.pdf', '.mobi']]
        print(f"   Found {len(asimov_books)} books:")
        for book in asimov_books[:5]:  # Show first 5
            print(f"     - {book}")
        if len(asimov_books) > 5:
            print(f"     ... and {len(asimov_books) - 5} more")
    print()
    
    # 4. File type statistics
    print("4. File type statistics:")
    file_types = defaultdict(int)
    total_files = 0
    
    for author_dir in library_path.iterdir():
        if author_dir.is_dir():
            for file_path in author_dir.iterdir():
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in ['.epub', '.pdf', '.mobi']:
                        file_types[ext] += 1
                        total_files += 1
    
    for ext, count in sorted(file_types.items()):
        percentage = (count / total_files) * 100
        print(f"   {ext}: {count} files ({percentage:.1f}%)")
    print()
    
    # 5. Generate library statistics
    print("5. Library statistics:")
    stats = {
        'total_authors': len(authors),
        'total_books': total_files,
        'file_types': dict(file_types),
        'top_authors': dict(top_authors[:20]),  # Top 20 authors
        'special_categories': {
            'Collectif': author_book_counts.get('Collectif', 0),
            'Anonyme': author_book_counts.get('Anonyme', 0),
            'Anthologie': author_book_counts.get('Anthologie', 0),
            'Unknown Author': author_book_counts.get('Unknown Author', 0)
        }
    }
    
    print(f"   Total authors: {stats['total_authors']}")
    print(f"   Total books: {stats['total_books']}")
    print(f"   Special categories: {stats['special_categories']}")
    print()
    
    # 6. Demonstrate easy search
    print("6. Easy search demonstration:")
    search_term = "tolkien"
    matching_authors = [author for author in authors if search_term.lower() in author.lower()]
    print(f"   Authors containing '{search_term}': {matching_authors}")
    print()
    
    # 7. Show how easy it is to get all books by an author
    print("7. Getting all books by an author (example with Douglas Adams):")
    adams_dir = library_path / "ADAMS, Douglas"
    if adams_dir.exists():
        adams_books = [f.name for f in adams_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.epub', '.pdf', '.mobi']]
        print(f"   Douglas Adams has {len(adams_books)} books:")
        for book in adams_books:
            print(f"     - {book}")
    print()
    
    # Save statistics to file
    stats_file = library_path / "library_statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"8. Statistics saved to: {stats_file}")
    
    print("\n=== Demo Complete ===")
    print("The new structure makes it incredibly easy to:")
    print("- Navigate the library programmatically")
    print("- Find specific authors and books")
    print("- Generate statistics and reports")
    print("- Build search functionality")
    print("- Create web interfaces")
    print("- Perform bulk operations")

if __name__ == "__main__":
    demo_library_operations()
