import json
import sqlite3
from pathlib import Path

def load_genre_keywords():
    """Load French genre keywords"""
    with open('data/genres/french_genres_enhanced.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_book_keywords(book_title, book_text, genre_keywords):
    """Analyze which keywords are triggering genre classification"""
    text_lower = book_text.lower()
    title_lower = book_title.lower()
    
    print(f"Analyzing book: {book_title}")
    print("=" * 50)
    
    # Check each genre
    for genre, keywords in genre_keywords.items():
        matching_keywords = []
        
        for keyword in keywords:
            # Check in text
            if keyword in text_lower:
                matching_keywords.append(f"'{keyword}' (in text)")
            
            # Check in title
            if keyword in title_lower:
                matching_keywords.append(f"'{keyword}' (in title)")
        
        if matching_keywords:
            print(f"\n{genre}:")
            for match in matching_keywords:
                print(f"  - {match}")

def main():
    # Load genre keywords
    genre_keywords = load_genre_keywords()
    
    # Connect to database
    conn = sqlite3.connect('databases/books.db')
    cursor = conn.cursor()
    
    # Get the problematic books
    cursor.execute("""
        SELECT title, full_text 
        FROM books 
        WHERE title LIKE '%croisee%' OR title LIKE '%rebellion%'
    """)
    
    results = cursor.fetchall()
    
    for title, full_text in results:
        if full_text:
            # Take first 1000 characters for analysis
            sample_text = full_text[:1000]
            analyze_book_keywords(title, sample_text, genre_keywords)
            print("\n" + "="*80 + "\n")
    
    conn.close()

if __name__ == "__main__":
    main()
