import sqlite3

conn = sqlite3.connect('databases/books.db')
cursor = conn.cursor()

# Check for the problematic books
cursor.execute("""
    SELECT title, primary_genre, secondary_genres 
    FROM books 
    WHERE title LIKE '%croisee%' OR title LIKE '%rebellion%'
""")

results = cursor.fetchall()

print("Genre assignments for problematic books:")
print("=" * 50)
for row in results:
    title, primary, secondary = row
    print(f"Title: {title}")
    print(f"Primary genre: {primary}")
    print(f"Secondary genres: {secondary}")
    print("-" * 30)

conn.close()
