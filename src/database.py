"""
Database Module

This module handles data storage, retrieval, and management for the book collection.
It provides a simple but effective way to store and query book data.
"""

import json
import sqlite3
import pickle
import threading
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BookDatabase:
    """Database manager for book collection"""
    
    def __init__(self, db_path: str = "books.db"):
        self.db_path = db_path
        self.connection = None
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables"""
        try:
            # Ensure parent directory exists for file-based SQLite paths
            try:
                db_path_obj = Path(self.db_path)
                if db_path_obj.parent and str(db_path_obj.parent) not in ("", "."):
                    db_path_obj.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"Could not ensure database directory exists: {e}")

            # Allow safe use across worker threads. We still guard all DB
            # operations with a lock to avoid concurrent write issues.
            self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            
            # Create tables
            self._create_tables()
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.connection.cursor()
        
        # Books table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                authors TEXT,
                language TEXT,
                publisher TEXT,
                publication_date TEXT,
                isbn TEXT,
                description TEXT,
                subjects TEXT,
                rights TEXT,
                identifier TEXT,
                file_path TEXT UNIQUE,
                file_size INTEGER,
                word_count INTEGER,
                character_count INTEGER,
                paragraph_count INTEGER,
                sentence_count INTEGER,
                average_sentence_length REAL,
                average_word_length REAL,
                  primary_genre TEXT,
                  primary_confidence REAL,
                  secondary_genres TEXT,
                  secondary_confidences TEXT,
                tag_scores TEXT,
                complexity_level TEXT,
                reading_level TEXT,
                topics TEXT,
                keywords TEXT,
                cover_data TEXT,
                cover_mime_type TEXT,
                cover_file_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Backward-compatible migration: add columns if missing
        try:
            cursor.execute('PRAGMA table_info(books)')
            existing_cols = {row[1] for row in cursor.fetchall()}
            if 'tag_scores' not in existing_cols:
                cursor.execute('ALTER TABLE books ADD COLUMN tag_scores TEXT')
            # Optionally clear legacy genres if present but unused (non-destructive schema-wise)
        except Exception as e:
            logger.warning(f"Could not run books table migration checks: {e}")
        
        # Chapters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT,
                chapter_id TEXT,
                title TEXT,
                content TEXT,
                word_count INTEGER,
                FOREIGN KEY (book_id) REFERENCES books (id)
            )
        ''')
        
        # Analysis results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT,
                analysis_type TEXT,
                results TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books (id)
            )
        ''')
        
        # User preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                preference_type TEXT,
                preference_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Recommendations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_book_id TEXT,
                recommended_book_id TEXT,
                similarity_score REAL,
                recommendation_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_book_id) REFERENCES books (id),
                FOREIGN KEY (recommended_book_id) REFERENCES books (id)
            )
        ''')
        
        self.connection.commit()
    
    def add_book(self, book_data: Dict) -> bool:
        """Add a book to the database"""
        try:
            with self._lock:
                cursor = self.connection.cursor()
            
            # Prepare data
            book_id = book_data.get('id', book_data.get('title', ''))
            
            # Convert lists to JSON strings
            authors = json.dumps(book_data.get('authors', []))
            subjects = json.dumps(book_data.get('subjects', []))
            secondary_genres = json.dumps(book_data.get('secondary_genres', []))
            secondary_confidences = json.dumps(book_data.get('secondary_confidences', []))
            tag_scores = json.dumps(book_data.get('tag_scores', []))
            topics = json.dumps(book_data.get('topics', []))
            keywords = json.dumps(book_data.get('keywords', []))
            
            cursor.execute('''
                INSERT OR REPLACE INTO books (
                    id, title, authors, language, publisher, publication_date,
                    isbn, description, subjects, rights, identifier, file_path,
                    file_size, word_count, character_count, paragraph_count,
                    sentence_count, average_sentence_length, average_word_length,
                    primary_genre, primary_confidence, secondary_genres,
                    secondary_confidences, tag_scores, complexity_level, reading_level,
                    topics, keywords, cover_data, cover_mime_type, cover_file_name, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                book_id,
                book_data.get('title', ''),
                authors,
                book_data.get('language', ''),
                book_data.get('publisher', ''),
                book_data.get('publication_date', ''),
                book_data.get('isbn', ''),
                book_data.get('description', ''),
                subjects,
                book_data.get('rights', ''),
                book_data.get('identifier', ''),
                book_data.get('file_path', ''),
                book_data.get('file_size', 0),
                book_data.get('word_count', 0),
                book_data.get('character_count', 0),
                book_data.get('paragraph_count', 0),
                book_data.get('sentence_count', 0),
                book_data.get('average_sentence_length', 0.0),
                book_data.get('average_word_length', 0.0),
                book_data.get('primary_genre', ''),
                book_data.get('primary_confidence', 0.0),
                secondary_genres,
                secondary_confidences,
                tag_scores,
                book_data.get('complexity_level', ''),
                book_data.get('reading_level', ''),
                topics,
                keywords,
                book_data.get('cover_data'),
                book_data.get('cover_mime_type'),
                book_data.get('cover_file_name'),
                datetime.now().isoformat()
            ))
            
            # Add chapters if available
            chapters = book_data.get('chapters', [])
            for chapter in chapters:
                cursor.execute('''
                    INSERT OR REPLACE INTO chapters (
                        book_id, chapter_id, title, content, word_count
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    book_id,
                    chapter.get('id', ''),
                    chapter.get('title', ''),
                    chapter.get('content', ''),
                    chapter.get('word_count', 0)
                ))
            
            self.connection.commit()
            logger.info(f"Added book to database: {book_data.get('title', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding book to database: {e}")
            return False
    
    def get_book(self, book_id: str) -> Optional[Dict]:
        """Get a book from the database"""
        try:
            with self._lock:
                cursor = self.connection.cursor()
                cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
                row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting book from database: {e}")
            return None

    def get_book_by_path(self, file_path: str) -> Optional[Dict]:
        """Get a book from the database by its file path."""
        try:
            with self._lock:
                cursor = self.connection.cursor()
                cursor.execute('SELECT * FROM books WHERE file_path = ?', (file_path,))
                row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None
        except Exception as e:
            logger.error(f"Error getting book by path from database: {e}")
            return None
    
    def get_all_books(self) -> List[Dict]:
        """Get all books from the database"""
        try:
            with self._lock:
                cursor = self.connection.cursor()
                cursor.execute('SELECT * FROM books ORDER BY title')
                rows = cursor.fetchall()
            
            return [self._row_to_dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting all books from database: {e}")
            return []
    
    def search_books(self, query: str, search_fields: List[str] = None) -> List[Dict]:
        """Search books by various criteria"""
        try:
            with self._lock:
                cursor = self.connection.cursor()
            
            if search_fields is None:
                search_fields = ['title', 'authors', 'description', 'subjects']
            
            # Build search query
            search_conditions = []
            search_params = []
            
            for field in search_fields:
                search_conditions.append(f"{field} LIKE ?")
                search_params.append(f"%{query}%")
            
            where_clause = " OR ".join(search_conditions)
            
            cursor.execute(f'''
                SELECT * FROM books 
                WHERE {where_clause}
                ORDER BY title
            ''', search_params)
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return []
    
    def filter_books(self, filters: Dict) -> List[Dict]:
        """Filter books by various criteria"""
        try:
            with self._lock:
                cursor = self.connection.cursor()
            
            # Build filter conditions
            conditions = []
            params = []
            
            for field, value in filters.items():
                if value is not None:
                    if field == 'genre':
                        conditions.append("primary_genre = ?")
                        params.append(value)
                    elif field == 'min_words':
                        conditions.append("word_count >= ?")
                        params.append(value)
                    elif field == 'max_words':
                        conditions.append("word_count <= ?")
                        params.append(value)
                    elif field == 'complexity':
                        conditions.append("complexity_level = ?")
                        params.append(value)
                    elif field == 'author':
                        conditions.append("authors LIKE ?")
                        params.append(f"%{value}%")
                    elif field == 'language':
                        conditions.append("language = ?")
                        params.append(value)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor.execute(f'''
                SELECT * FROM books 
                WHERE {where_clause}
                ORDER BY title
            ''', params)
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error filtering books: {e}")
            return []
    
    def get_book_statistics(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            with self._lock:
                cursor = self.connection.cursor()
            
            # Total books
            cursor.execute('SELECT COUNT(*) FROM books')
            total_books = cursor.fetchone()[0]
            
            # Genre distribution
            cursor.execute('''
                SELECT primary_genre, COUNT(*) as count 
                FROM books 
                WHERE primary_genre IS NOT NULL 
                GROUP BY primary_genre 
                ORDER BY count DESC
            ''')
            genre_distribution = dict(cursor.fetchall())
            
            # Language distribution
            cursor.execute('''
                SELECT language, COUNT(*) as count 
                FROM books 
                WHERE language IS NOT NULL 
                GROUP BY language 
                ORDER BY count DESC
            ''')
            language_distribution = dict(cursor.fetchall())
            
            # Complexity distribution
            cursor.execute('''
                SELECT complexity_level, COUNT(*) as count 
                FROM books 
                WHERE complexity_level IS NOT NULL 
                GROUP BY complexity_level 
                ORDER BY count DESC
            ''')
            complexity_distribution = dict(cursor.fetchall())
            
            # Word count statistics
            cursor.execute('''
                SELECT 
                    MIN(word_count) as min_words,
                    MAX(word_count) as max_words,
                    AVG(word_count) as avg_words,
                    SUM(word_count) as total_words
                FROM books 
                WHERE word_count > 0
            ''')
            word_stats = cursor.fetchone()
            
            return {
                'total_books': total_books,
                'genre_distribution': genre_distribution,
                'language_distribution': language_distribution,
                'complexity_distribution': complexity_distribution,
                'word_statistics': {
                    'min_words': word_stats[0],
                    'max_words': word_stats[1],
                    'avg_words': word_stats[2],
                    'total_words': word_stats[3]
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting book statistics: {e}")
            return {}
    
    def save_analysis_results(self, book_id: str, analysis_type: str, results: Dict):
        """Save analysis results for a book"""
        try:
            with self._lock:
                cursor = self.connection.cursor()
            
            results_json = json.dumps(results)
            
            cursor.execute('''
                INSERT OR REPLACE INTO analysis_results (
                    book_id, analysis_type, results
                ) VALUES (?, ?, ?)
            ''', (book_id, analysis_type, results_json))
            
            self.connection.commit()
            logger.info(f"Saved analysis results for {book_id}: {analysis_type}")
            
        except Exception as e:
            logger.error(f"Error saving analysis results: {e}")
    
    def get_analysis_results(self, book_id: str, analysis_type: str = None) -> List[Dict]:
        """Get analysis results for a book"""
        try:
            with self._lock:
                cursor = self.connection.cursor()
            
            if analysis_type:
                cursor.execute('''
                    SELECT * FROM analysis_results 
                    WHERE book_id = ? AND analysis_type = ?
                    ORDER BY created_at DESC
                ''', (book_id, analysis_type))
            else:
                cursor.execute('''
                    SELECT * FROM analysis_results 
                    WHERE book_id = ?
                    ORDER BY created_at DESC
                ''', (book_id,))
            
            rows = cursor.fetchall()
            results = []
            
            for row in rows:
                result = dict(row)
                result['results'] = json.loads(result['results'])
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting analysis results: {e}")
            return []
    
    def save_recommendations(self, source_book_id: str, recommendations: List[Tuple[Dict, float]], 
                           recommendation_type: str = 'hybrid'):
        """Save recommendations to database"""
        try:
            with self._lock:
                cursor = self.connection.cursor()
            
            for book, score in recommendations:
                cursor.execute('''
                    INSERT OR REPLACE INTO recommendations (
                        source_book_id, recommended_book_id, similarity_score, recommendation_type
                    ) VALUES (?, ?, ?, ?)
                ''', (source_book_id, book.get('id'), score, recommendation_type))
            
            self.connection.commit()
            logger.info(f"Saved {len(recommendations)} recommendations for {source_book_id}")
            
        except Exception as e:
            logger.error(f"Error saving recommendations: {e}")
    
    def get_recommendations(self, book_id: str, recommendation_type: str = None) -> List[Dict]:
        """Get recommendations for a book"""
        try:
            with self._lock:
                cursor = self.connection.cursor()
            
            if recommendation_type:
                cursor.execute('''
                    SELECT r.*, b.title, b.authors, b.primary_genre
                    FROM recommendations r
                    JOIN books b ON r.recommended_book_id = b.id
                    WHERE r.source_book_id = ? AND r.recommendation_type = ?
                    ORDER BY r.similarity_score DESC
                ''', (book_id, recommendation_type))
            else:
                cursor.execute('''
                    SELECT r.*, b.title, b.authors, b.primary_genre
                    FROM recommendations r
                    JOIN books b ON r.recommended_book_id = b.id
                    WHERE r.source_book_id = ?
                    ORDER BY r.similarity_score DESC
                ''', (book_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
    
    def _row_to_dict(self, row) -> Dict:
        """Convert database row to dictionary"""
        row_dict = dict(row)
        
        # Parse JSON fields
        for field in ['authors', 'subjects', 'secondary_genres', 'secondary_confidences', 'tag_scores', 'topics', 'keywords']:
            if row_dict.get(field):
                try:
                    row_dict[field] = json.loads(row_dict[field])
                except:
                    row_dict[field] = []
        
        return row_dict
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
