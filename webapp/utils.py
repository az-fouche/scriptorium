"""
Utility functions for the library webapp
"""

import json
import unicodedata
from typing import Optional, List, Dict, Any
from datetime import datetime
import time
import os
from sqlalchemy import text
from flask import current_app

try:
    from .models import db, Book
except ImportError:
    from models import db, Book


def normalize_characters(text: str) -> str:
    """
    Normalize characters to handle diacritics and character variants.
    For example, 'a' will match 'a', 'â', 'ä', 'à', etc.
    """
    if not text:
        return ""
    
    # Normalize unicode characters (NFD = Canonical Decomposition)
    # This separates base characters from their diacritical marks
    normalized = unicodedata.normalize('NFD', text.lower())
    
    # Remove diacritical marks (combining characters)
    # This keeps only the base characters
    cleaned = ''.join(
        char for char in normalized 
        if not unicodedata.combining(char)
    )
    
    return cleaned


def calculate_reading_time(word_count: Optional[int], words_per_minute: int = 200) -> Optional[str]:
    """Calculate estimated reading time in minutes"""
    if not word_count:
        return None
    
    minutes = word_count / words_per_minute
    if minutes < 60:
        return f"{int(minutes)} min"
    else:
        hours = int(minutes // 60)
        remaining_minutes = int(minutes % 60)
        if remaining_minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {remaining_minutes}min"


def truncate_html(text: str, length: int = 150) -> str:
    """Safely truncate HTML text while preserving tags"""
    if not text:
        return ""
    
    # If text is shorter than length, return as is
    if len(text) <= length:
        return text
    
    # Simple truncation - in a real app you might want to use a proper HTML parser
    # This is a basic implementation that just truncates at the character level
    truncated = text[:length]
    
    # Try to close any open tags by finding the last complete tag
    last_tag_start = truncated.rfind('<')
    last_tag_end = truncated.rfind('>')
    
    if last_tag_start > last_tag_end:
        # We have an unclosed tag, try to find a good cutoff point
        # Look for the last space before the unclosed tag
        last_space = truncated.rfind(' ', 0, last_tag_start)
        if last_space > length * 0.8:  # If we can find a space in the last 20%
            truncated = truncated[:last_space]
        else:
            # Just truncate and add ellipsis
            truncated = truncated[:length-3] + "..."
    else:
        truncated += "..."
    
    return truncated


def get_genre_color(genre: str) -> str:
    """Get color class for a genre or v2 tag via TagManager mapping."""
    if not genre:
        return 'bg-secondary'
    try:
        from .tag_manager import get_tag_color_class
    except Exception:
        try:
            from tag_manager import get_tag_color_class
        except Exception:
            get_tag_color_class = None  # type: ignore
    if get_tag_color_class:
        return get_tag_color_class(genre)
    return 'bg-secondary'


def row_to_dict(row) -> Dict[str, Any]:
    """Convert database row to dictionary with proper author parsing"""
    return {
        'id': row[0],
        'title': row[1],
        'authors': safe_json_loads(row[2]),
        'language': row[3],
        'publisher': row[4],
        'publication_date': row[5],
        'isbn': row[6],
        'description': row[7],
        'subjects': safe_json_loads(row[8]),
        'file_path': row[9],
        'file_size': row[10],
        'word_count': row[11],
        'character_count': row[12],
        'paragraph_count': row[13],
        'sentence_count': row[14],
        'average_sentence_length': row[15],
        'average_word_length': row[16],
        'created_at': row[17],
        'primary_genre': row[18] if len(row) > 18 else None,
        'primary_confidence': row[19] if len(row) > 19 else None,
        'secondary_genres': safe_json_loads(row[20]) if len(row) > 20 else [],
        'secondary_confidences': safe_json_loads(row[21]) if len(row) > 21 else [],
        'complexity_level': row[22] if len(row) > 22 else None,
        'reading_level': row[23] if len(row) > 23 else None,
        'topics': safe_json_loads(row[24]) if len(row) > 24 else [],
        'keywords': safe_json_loads(row[25]) if len(row) > 25 else []
    }


def safe_json_loads(value):
    """Safely parse JSON string to list"""
    if not value:
        return []
    try:
        # First, try to parse as regular JSON
        parsed = json.loads(value)
        if isinstance(parsed, list):
            # Handle case where list contains single string with dash separator
            result = []
            for item in parsed:
                if isinstance(item, str) and ' - ' in item:
                    # Split by dash separator and clean up
                    authors = [author.strip() for author in item.split(' - ')]
                    result.extend(authors)
                else:
                    result.append(str(item))
            return result
        else:
            # Special case: if the parsed value is exactly "[]", return empty list
            if str(parsed) == '[]':
                return []
            return [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        # If that fails, try to parse as a double-quoted JSON string
        try:
            # Remove outer quotes if they exist
            cleaned_value = value.strip()
            if cleaned_value.startswith('"') and cleaned_value.endswith('"'):
                cleaned_value = cleaned_value[1:-1]
                # Unescape the inner JSON
                cleaned_value = cleaned_value.replace('\\"', '"')
                parsed = json.loads(cleaned_value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
                else:
                    return [str(parsed)]
        except (json.JSONDecodeError, TypeError):
            pass
        
        # If all parsing fails, treat as a single string
        # But don't treat empty strings or "[]" as single strings
        if value == '[]' or value == '"[]"':
            return []
        # Also handle the case where the value is just a string representation of an empty array
        if str(value).strip() in ['[]', '"[]"']:
            return []
        # Special case: if the value is exactly "[]" (double-quoted empty array), return empty list
        if str(value).strip() == '"[]"':
            return []
        return [str(value)] if value else []
