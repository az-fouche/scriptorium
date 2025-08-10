"""
Database models for the library webapp
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
import re
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def safe_json_loads(value):
    """Safely parse JSON string to list"""
    if not value:
        return []
    
    # Handle the case where value is already a list (shouldn't happen but just in case)
    if isinstance(value, list):
        return [str(item) for item in value]
    
    # Convert to string if it's not already
    value_str = str(value).strip()
    
    # Handle empty cases
    if value_str in ['', '[]', '"[]"', 'null', 'None']:
        return []
    
    try:
        # First, try to parse as regular JSON
        parsed = json.loads(value_str)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        else:
            return [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        pass
    
    # If that fails, try to parse as a double-quoted JSON string
    try:
        # Check if it's a double-quoted JSON string
        if value_str.startswith('"') and value_str.endswith('"'):
            # Remove outer quotes and unescape
            cleaned_value = value_str[1:-1].replace('\\"', '"')
            parsed = json.loads(cleaned_value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
            else:
                return [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        pass
    
    # If all parsing fails, treat as a single string
    return [value_str] if value_str else []


class Book(db.Model):
    """Book model for the database"""
    __tablename__ = 'books'
    
    id = db.Column(db.String(32), primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    authors = db.Column(db.Text)
    language = db.Column(db.String(10))
    publisher = db.Column(db.String(200))
    publication_date = db.Column(db.String(50))
    isbn = db.Column(db.String(20))
    description = db.Column(db.Text)
    subjects = db.Column(db.Text)
    file_path = db.Column(db.String(500), unique=True)
    file_size = db.Column(db.Integer)
    word_count = db.Column(db.Integer)
    character_count = db.Column(db.Integer)
    paragraph_count = db.Column(db.Integer)
    sentence_count = db.Column(db.Integer)
    average_sentence_length = db.Column(db.Float)
    average_word_length = db.Column(db.Float)
    primary_genre = db.Column(db.String(100))
    primary_confidence = db.Column(db.Float)
    secondary_genres = db.Column(db.Text)
    secondary_confidences = db.Column(db.Text)
    complexity_level = db.Column(db.String(50))
    reading_level = db.Column(db.String(50))
    topics = db.Column(db.Text)
    keywords = db.Column(db.Text)
    # Unified tag scores storage
    tag_scores = db.Column(db.Text)
    cover_data = db.Column(db.Text)
    cover_mime_type = db.Column(db.String(100))
    cover_file_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert book to dictionary"""
        # Normalize and deduplicate authors for consistent display
        raw_authors = safe_json_loads(self.authors)

        def _canonical_author_key(name: str) -> str:
            if not name:
                return ''
            name = name.strip()
            # If in "LAST, First" form, convert to "First Last" for keying
            if ',' in name:
                last, first = [part.strip() for part in name.split(',', 1)]
                name = f"{first} {last}"
            # Lowercase and strip all non-alphanumeric for robust matching
            name = name.lower()
            return re.sub(r'[^a-z0-9]+', '', name)

        def _display_author_name(name: str) -> str:
            if not name:
                return ''
            name = name.strip()
            # Prefer "First Last" display
            if ',' in name:
                last, first = [part.strip() for part in name.split(',', 1)]
                name = f"{first} {last}"
            # Collapse extra whitespace
            name = ' '.join(name.split())
            # Title-case for nicer display (best-effort)
            return name.title()

        seen_keys = set()
        authors_list: List[str] = []
        for author in raw_authors:
            display = _display_author_name(str(author))
            key = _canonical_author_key(display)
            if display and key not in seen_keys:
                seen_keys.add(key)
                authors_list.append(display)

        return {
            'id': self.id,
            'title': self.title,
            'authors': authors_list,
            'language': self.language,
            'publisher': self.publisher,
            'publication_date': self.publication_date,
            'isbn': self.isbn,
            'description': self.description,
            'subjects': safe_json_loads(self.subjects),
            'file_path': self.file_path,
            'file_size': self.file_size,
            'word_count': self.word_count,
            'character_count': self.character_count,
            'paragraph_count': self.paragraph_count,
            'sentence_count': self.sentence_count,
            'average_sentence_length': self.average_sentence_length,
            'average_word_length': self.average_word_length,
            'primary_genre': self.primary_genre,
            'primary_confidence': self.primary_confidence,
            'secondary_genres': safe_json_loads(self.secondary_genres),
            'secondary_confidences': safe_json_loads(self.secondary_confidences),
            'complexity_level': self.complexity_level,
            'reading_level': self.reading_level,
            'topics': safe_json_loads(self.topics),
            'keywords': safe_json_loads(self.keywords),
            # Unified tag scores for UI derivation (preserve list of dicts)
            'tag_scores': (json.loads(self.tag_scores) if self.tag_scores else []),
            'cover_data': self.cover_data,
            'cover_mime_type': self.cover_mime_type,
            'cover_file_name': self.cover_file_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def reading_time(self) -> Optional[str]:
        """Calculate estimated reading time"""
        try:
            from .utils import calculate_reading_time
        except ImportError:
            from utils import calculate_reading_time
        return calculate_reading_time(self.word_count)
    
    @property
    def author_list(self) -> List[str]:
        """Get list of authors"""
        return safe_json_loads(self.authors)
    
    @property
    def subject_list(self) -> List[str]:
        """Get list of subjects"""
        return safe_json_loads(self.subjects)
    
    @property
    def secondary_genre_list(self) -> List[str]:
        """Get list of secondary genres"""
        return safe_json_loads(self.secondary_genres)
    
    @property
    def topic_list(self) -> List[str]:
        """Get list of topics"""
        return safe_json_loads(self.topics)
    
    @property
    def keyword_list(self) -> List[str]:
        """Get list of keywords"""
        return safe_json_loads(self.keywords)
