#!/usr/bin/env python3
"""
Regenerate Subset Database

This script creates a subset of 50 books from the main database for the webapp.
"""

import os
import sys
import sqlite3
import random
from pathlib import Path
from typing import List, Dict
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import BookDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_subset_database(source_db_path: str, target_db_path: str, num_books: int = 50):
    """Create a subset database with specified number of books"""
    
    # Connect to source database
    source_conn = sqlite3.connect(source_db_path)
    source_conn.row_factory = sqlite3.Row
    
    # Connect to target database
    target_conn = sqlite3.connect(target_db_path)
    target_conn.row_factory = sqlite3.Row
    
    try:
        # Get all books from source database
        cursor = source_conn.cursor()
        cursor.execute("SELECT * FROM books")
        all_books = cursor.fetchall()
        
        logger.info(f"Found {len(all_books)} books in source database")
        
        if len(all_books) < num_books:
            logger.warning(f"Only {len(all_books)} books available, using all of them")
            selected_books = all_books
        else:
            # Randomly select books
            selected_books = random.sample(all_books, num_books)
            logger.info(f"Randomly selected {len(selected_books)} books")
        
        # Create tables in target database
        target_cursor = target_conn.cursor()
        
        # Create books table
        target_cursor.execute('''
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
                complexity_level TEXT,
                reading_level TEXT,
                topics TEXT,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create chapters table
        target_cursor.execute('''
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
        
        # Create analysis_results table
        target_cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT,
                analysis_type TEXT,
                results TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books (id)
            )
        ''')
        
        # Clear existing data
        target_cursor.execute("DELETE FROM books")
        target_cursor.execute("DELETE FROM chapters")
        target_cursor.execute("DELETE FROM analysis_results")
        
        # Copy selected books
        for book in selected_books:
            # Insert book
            target_cursor.execute('''
                INSERT INTO books (
                    id, title, authors, language, publisher, publication_date,
                    isbn, description, subjects, rights, identifier, file_path,
                    file_size, word_count, character_count, paragraph_count,
                    sentence_count, average_sentence_length, average_word_length,
                    primary_genre, primary_confidence, secondary_genres,
                    secondary_confidences, complexity_level, reading_level,
                    topics, keywords, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                book['id'], book['title'], book['authors'], book['language'],
                book['publisher'], book['publication_date'], book['isbn'],
                book['description'], book['subjects'], book['rights'],
                book['identifier'], book['file_path'], book['file_size'],
                book['word_count'], book['character_count'], book['paragraph_count'],
                book['sentence_count'], book['average_sentence_length'],
                book['average_word_length'], book['primary_genre'],
                book['primary_confidence'], book['secondary_genres'],
                book['secondary_confidences'], book['complexity_level'],
                book['reading_level'], book['topics'], book['keywords'],
                book['created_at'], book['updated_at']
            ))
            
            # Copy chapters for this book
            cursor.execute("SELECT * FROM chapters WHERE book_id = ?", (book['id'],))
            chapters = cursor.fetchall()
            for chapter in chapters:
                target_cursor.execute('''
                    INSERT INTO chapters (book_id, chapter_id, title, content, word_count)
                    VALUES (?, ?, ?, ?, ?)
                ''', (chapter['book_id'], chapter['chapter_id'], chapter['title'],
                      chapter['content'], chapter['word_count']))
            
            # Copy analysis results for this book
            cursor.execute("SELECT * FROM analysis_results WHERE book_id = ?", (book['id'],))
            analysis_results = cursor.fetchall()
            for result in analysis_results:
                target_cursor.execute('''
                    INSERT INTO analysis_results (book_id, analysis_type, results, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (result['book_id'], result['analysis_type'], result['results'],
                      result['created_at']))
        
        # Commit changes
        target_conn.commit()
        
        # Get statistics
        target_cursor.execute("SELECT COUNT(*) as count FROM books")
        book_count = target_cursor.fetchone()['count']
        
        target_cursor.execute("SELECT COUNT(*) as count FROM chapters")
        chapter_count = target_cursor.fetchone()['count']
        
        target_cursor.execute("SELECT COUNT(*) as count FROM analysis_results")
        analysis_count = target_cursor.fetchone()['count']
        
        logger.info(f"Successfully created subset database with:")
        logger.info(f"  - {book_count} books")
        logger.info(f"  - {chapter_count} chapters")
        logger.info(f"  - {analysis_count} analysis results")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating subset database: {e}")
        return False
    
    finally:
        source_conn.close()
        target_conn.close()


def main():
    """Main function"""
    # Set random seed for reproducible results
    random.seed(42)
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    source_db_path = os.path.join(project_dir, 'databases', 'books.db')
    target_db_path = os.path.join(project_dir, 'databases', 'subset_books.db')
    
    # Check if source database exists
    if not os.path.exists(source_db_path):
        logger.error(f"Source database not found: {source_db_path}")
        return False
    
    logger.info(f"Creating subset database with 50 books...")
    logger.info(f"Source: {source_db_path}")
    logger.info(f"Target: {target_db_path}")
    
    success = create_subset_database(source_db_path, target_db_path, num_books=50)
    
    if success:
        logger.info("Subset database created successfully!")
        return True
    else:
        logger.error("Failed to create subset database")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
