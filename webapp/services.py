"""
Business logic and data processing services for the library webapp
"""

from typing import Dict, List, Optional, Tuple
import random
from sqlalchemy import text, or_
import time
from flask import current_app

try:
    from .models import db, Book
    from .utils import calculate_reading_time, get_genre_color, normalize_characters
except ImportError:
    from models import db, Book
    from utils import calculate_reading_time, get_genre_color, normalize_characters


# Simple in-memory caches for filters
_CACHES: Dict[str, Dict[str, object]] = {
    # key: { 'data': Any, 'expires': float }
}
_CACHE_TTL_SECONDS = 30 * 60  # 30 minutes


class BookService:
    """Service for book-related operations"""
    
    @staticmethod
    def get_total_books() -> int:
        """Get total number of books"""
        return Book.query.count()
    
    @staticmethod
    def get_recent_books(limit: int = 5) -> List[Dict]:
        """Get recently added books"""
        books = Book.query.order_by(Book.created_at.desc()).limit(limit).all()
        items = [book.to_dict() for book in books]
        BookService._derive_primary_secondary_for_items(items)
        return items
    
    @staticmethod
    def get_books_with_filters(
        search: str = '',
        language: str = '',
        author: str = '',
        page: int = 1,
        per_page: int = 20,
        genres: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
    ) -> Tuple[List[Dict], int, int]:
        """Get books with filters and pagination.

        Push as much filtering to SQL as possible to avoid Python full-table scans.
        """
        query = Book.query

        # Normalize optional list filters
        selected_genres = [g for g in (genres or []) if g]
        selected_topics = [t for t in (topics or []) if t]

        if search:
            like = f"%{search}%"
            query = query.filter(
                or_(
                    Book.title.ilike(like),
                    Book.authors.ilike(like),
                )
            )

        if language:
            query = query.filter(Book.language == language)

        if author:
            like = f"%{author}%"
            query = query.filter(Book.authors.ilike(like))

        # Unify filtering by displayed tags (derived from tag_scores or topics fallback)
        # This aligns the catalog filter with the tags shown on book cards
        # AND semantics across all selected tags
        selected_tags = []
        if selected_genres:
            selected_tags.extend([g for g in selected_genres if g])
        if selected_topics:
            selected_tags.extend([t for t in selected_topics if t])
        # Deduplicate while preserving order
        seen = set()
        selected_tags = [t for t in selected_tags if not (t in seen or seen.add(t))]
        if selected_tags:
            for tag in selected_tags:
                # Match unified tags primarily via tag_scores JSON, with a fallback to topics JSON
                # We intentionally do NOT match legacy primary/secondary_genre fields here to avoid
                # mismatches between displayed tags and filter semantics.
                query = query.filter(
                    or_(
                        # Match a tag object like {"tag":"horror", ...}
                        Book.tag_scores.like(f'%"tag":"{tag}"%'),
                        # Fallback: topics list contains the tag
                        Book.topics.like(f'%"{tag}"%')
                    )
                )

        # Refine results if tag filters are present to require displayed tags to match
        if selected_tags:
            # Fetch minimal fields for derivation and filter in Python to ensure
            # the selected tags exist among displayed tags (primary + secondary)
            candidates = query.with_entities(
                Book.id, Book.title, Book.tag_scores, Book.topics
            ).order_by(Book.title).all()

            import json
            light_items: List[Dict] = []
            for row in candidates:
                try:
                    tag_scores = []
                    topics_list = []
                    if row.tag_scores:
                        try:
                            tag_scores = json.loads(row.tag_scores) or []
                        except Exception:
                            tag_scores = []
                    if row.topics:
                        try:
                            topics_list = json.loads(row.topics) or []
                        except Exception:
                            topics_list = []
                    light_items.append({
                        'id': row.id,
                        'title': row.title,
                        'tag_scores': tag_scores,
                        'topics': topics_list,
                    })
                except Exception:
                    continue

            BookService._derive_primary_secondary_for_items(light_items)

            def displayed_contains_all(item: Dict, tags: List[str]) -> bool:
                displayed = []
                if item.get('primary_tag'):
                    displayed.append(item['primary_tag'])
                displayed.extend(item.get('secondary_tags') or [])
                s = set([t for t in displayed if t])
                return all(t in s for t in tags)

            filtered = [it for it in light_items if displayed_contains_all(it, selected_tags)]

            # Manual pagination after shuffling to randomize discovery
            import random as _rnd
            _rnd.shuffle(filtered)
            total = len(filtered)
            pages = (total + per_page - 1) // per_page if per_page > 0 else 1
            start = max(0, (page - 1) * per_page)
            end = start + per_page
            page_ids = [it['id'] for it in filtered[start:end]]

            if page_ids:
                page_books = Book.query.filter(Book.id.in_(page_ids)).all()
                by_id = {b.id: b for b in page_books}
                ordered_books = [by_id.get(bid) for bid in page_ids if by_id.get(bid)]
            else:
                ordered_books = []

            books = [b.to_dict() for b in ordered_books]
            BookService._derive_primary_secondary_for_items(books)
            # Randomize the order of previews to provide a sense of discovery
            random.shuffle(books)
        else:
            # Randomize ordering for discovery using SQL RANDOM()
            books_paginated = query.order_by(text('RANDOM()')).paginate(
                page=page, per_page=per_page, error_out=False
            )

            books = [book.to_dict() for book in books_paginated.items]
            # Derive primary/secondary tags from tag_scores
            BookService._derive_primary_secondary_for_items(books)
            total = books_paginated.total
            pages = books_paginated.pages
        try:
            from .tag_manager import get_tag_label
        except Exception:
            try:
                from tag_manager import get_tag_label
            except Exception:
                get_tag_label = None  # type: ignore
        if get_tag_label:
            # Determine language from request context if available
            try:
                from flask import request
                lang = (request.args.get('lang') or request.headers.get('X-Language') or 'en')
            except Exception:
                lang = 'en'
            for b in books:
                # Legacy genre labels
                if b.get('primary_genre'):
                    b['primary_genre_label'] = get_tag_label(b.get('primary_genre'), lang)
                if isinstance(b.get('secondary_genres'), list):
                    b['secondary_genres_labels'] = [get_tag_label(g, lang) for g in b.get('secondary_genres')]
                # Unified tag labels
                if b.get('primary_tag'):
                    b['primary_tag_label'] = get_tag_label(b.get('primary_tag'), lang)
                if isinstance(b.get('secondary_tags'), list):
                    b['secondary_tags_labels'] = [get_tag_label(t, lang) for t in b.get('secondary_tags')]
        return books, total, pages
    
    @staticmethod
    def _derive_primary_secondary_for_items(items: List[Dict]) -> None:
        """Derive primary and secondary tags from tag_scores for each item in-place.

        - Select the highest-scoring tag as primary if score > 0
        - Select the next 3 highest as secondary
        """
        if not items:
            return
        for b in items:
            tag_scores = b.get('tag_scores') or []
            if not isinstance(tag_scores, list) or not tag_scores:
                # Fallback to topics if tag_scores are missing; topics are ordered with primary first
                topics = b.get('topics') or []
                if isinstance(topics, list) and topics:
                    try:
                        b['primary_tag'] = str(topics[0]) if topics else ''
                        b['secondary_tags'] = [str(t) for t in topics[1:4]] if len(topics) > 1 else []
                    except Exception:
                        b['primary_tag'] = ''
                        b['secondary_tags'] = []
                else:
                    b['primary_tag'] = ''
                    b['secondary_tags'] = []
                continue
            try:
                sorted_scores = sorted(
                    [d for d in tag_scores if isinstance(d, dict) and 'tag' in d],
                    key=lambda x: float(x.get('score', 0.0)),
                    reverse=True
                )
                non_zero = [d for d in sorted_scores if float(d.get('score', 0.0)) > 0]
                primary = non_zero[0]['tag'] if non_zero else ''
                secondaries = [d['tag'] for d in non_zero[1:4]] if non_zero else []
                b['primary_tag'] = primary
                b['secondary_tags'] = secondaries
            except Exception:
                b['primary_tag'] = ''
                b['secondary_tags'] = []

    @staticmethod
    def get_book_by_id(book_id: str) -> Optional[Dict]:
        """Get book by ID"""
        book = Book.query.get(book_id)
        if not book:
            return None
        data = book.to_dict()
        BookService._derive_primary_secondary_for_items([data])
        return data
    
    @staticmethod
    def get_random_book() -> Optional[Dict]:
        """Get a random book"""
        # SQLite supports RANDOM(); for other DBs this may need adaptation
        book = Book.query.order_by(text('RANDOM()')).first()
        if not book:
            return None
        data = book.to_dict()
        BookService._derive_primary_secondary_for_items([data])
        return data
    
    @staticmethod
    def get_random_books(limit: int = 4, exclude_ids: Optional[List[str]] = None) -> List[Dict]:
        """Get a list of random unique books"""
        query = Book.query
        if exclude_ids:
            query = query.filter(~Book.id.in_(exclude_ids))
        books = query.order_by(text('RANDOM()')).limit(limit).all()
        result = [book.to_dict() for book in books]
        BookService._derive_primary_secondary_for_items(result)
        return result
    
    @staticmethod
    def search_books(query: str, limit: int = 50) -> List[Dict]:
        """Search books in title, authors, and description with character variant insensitivity"""
        # Normalize the search query
        normalized_query = normalize_characters(query)
        
        # Get all books and filter them in Python for character variant insensitivity
        all_books = Book.query.all()
        results = []
        
        for book in all_books:
            # Normalize book fields for comparison
            normalized_title = normalize_characters(book.title or "")
            normalized_authors = normalize_characters(book.authors or "")
            normalized_description = normalize_characters(book.description or "")
            
            # Check if normalized query appears in any normalized field
            if (normalized_query in normalized_title or 
                normalized_query in normalized_authors or 
                normalized_query in normalized_description):
                results.append(book)
                
                # Stop if we've reached the limit
                if len(results) >= limit:
                    break
        
        # Sort by title and return as dictionaries
        results.sort(key=lambda book: book.title or "")
        data = [book.to_dict() for book in results]
        BookService._derive_primary_secondary_for_items(data)
        return data
    
    @staticmethod
    def get_autocomplete_suggestions(query: str, limit: int = 10) -> List[Dict]:
        """Get autocomplete suggestions for search with character variant insensitivity"""
        # Normalize the search query
        normalized_query = normalize_characters(query)
        
        # Get all books and filter them in Python for character variant insensitivity
        all_books = Book.query.all()
        title_matches = []
        author_matches = []
        
        for book in all_books:
            # Normalize book fields for comparison
            normalized_title = normalize_characters(book.title or "")
            
            # Handle authors as JSON string
            authors_list = []
            if book.authors:
                try:
                    import json
                    authors_list = json.loads(book.authors)
                except (json.JSONDecodeError, TypeError):
                    # If it's not JSON, treat as plain string
                    authors_list = [book.authors]
            
            # Check title matches
            if normalized_query in normalized_title:
                title_matches.append(book)
            
            # Check author matches
            for author in authors_list:
                normalized_author = normalize_characters(str(author))
                if normalized_query in normalized_author:
                    author_matches.append((book, author))
                    break  # Only add once per book
        
        # Sort and limit title matches
        title_matches.sort(key=lambda book: book.title or "")
        title_matches = title_matches[:limit]
        
        # Sort and limit author matches
        author_matches.sort(key=lambda x: str(x[1]))
        author_matches = author_matches[:limit]
        
        # Combine and deduplicate results
        suggestions = []
        seen_titles = set()
        seen_authors = set()
        
        # Add title suggestions
        # Helper to pretty format an author string like "LAST, First" -> "First LAST"
        def _pretty_author_name(name: str) -> str:
            pretty = (name or '').strip()
            if not pretty:
                return pretty
            if ',' in pretty:
                last, first = [part.strip() for part in pretty.split(',', 1)]
                pretty = f"{first} {last}"
            # Collapse extra spaces and Title Case for first names, preserve last name capitalization
            parts = [p for p in pretty.split() if p]
            if not parts:
                return pretty
            if len(parts) == 1:
                return parts[0].title()
            first_names = ' '.join(parts[:-1]).title()
            last_name = parts[-1]
            return f"{first_names} {last_name}"

        for book in title_matches:
            if book.title not in seen_titles:
                # Derive a readable single-line author string
                author_text = 'book_details.book_unknown_author'
                try:
                    from .models import safe_json_loads  # type: ignore
                except Exception:
                    from models import safe_json_loads  # type: ignore
                raw_list = safe_json_loads(book.authors) if getattr(book, 'authors', None) else []
                if isinstance(raw_list, list) and raw_list:
                    # Pick the first author and format nicely
                    author_text = _pretty_author_name(str(raw_list[0]))
                elif isinstance(book.authors, str) and book.authors:
                    author_text = _pretty_author_name(book.authors)

                suggestions.append({
                    'type': 'title',
                    'text': book.title,
                    'author': author_text,
                    'id': book.id
                })
                seen_titles.add(book.title)
        
        # Add author suggestions
        for book, author in author_matches:
            if author not in seen_authors:
                suggestions.append({
                    'type': 'author',
                    'text': _pretty_author_name(str(author)),
                    'count': 1,  # Could be enhanced to count books per author
                    'id': None
                })
                seen_authors.add(author)
        
        # Limit total suggestions
        result = suggestions[:limit]
        
        # Debug logging
        try:
            current_app.logger.debug(
                "Autocomplete debug query='%s' normalized='%s' title_matches=%d author_matches=%d returned=%d",
                query, normalized_query, len(title_matches), len(author_matches), len(result)
            )
        except Exception:
            pass
        
        return result
    
    @staticmethod
    def get_available_languages() -> List[str]:
        """Get list of available languages"""
        languages = db.session.execute(text(
            "SELECT DISTINCT language FROM books WHERE language IS NOT NULL"
        )).fetchall()
        return [lang.language for lang in languages]

    @staticmethod
    def get_available_genres() -> List[str]:
        """Get list of available unified tags (used as genres in the UI) with caching.

        Sourced from tag_scores primary/secondary tags with a fallback to topics
        for books that do not yet have tag_scores. This keeps the filter list
        consistent with the tags displayed on book cards.
        """
        now = time.time()
        cache = _CACHES.get('genres')
        if cache and cache['expires'] > now:
            return cache['data']

        import json
        tag_set = set()
        # Scan tag_scores first
        for row in Book.query.with_entities(Book.tag_scores, Book.topics).all():
            # tag_scores: JSON array of {"tag": str, "score": float}
            ts = (row.tag_scores or '').strip() if hasattr(row, 'tag_scores') else ''
            if ts:
                try:
                    for entry in json.loads(ts) or []:
                        if isinstance(entry, dict):
                            tag = str(entry.get('tag') or '').strip()
                            score = float(entry.get('score', 0) or 0)
                            if tag and score > 0:
                                tag_set.add(tag)
                except Exception:
                    pass
            # Fallback to topics
            tops = (row.topics or '').strip() if hasattr(row, 'topics') else ''
            if tops:
                try:
                    for t in json.loads(tops) or []:
                        t_str = str(t).strip()
                        if t_str:
                            tag_set.add(t_str)
                except Exception:
                    pass

        data = sorted(tag_set, key=lambda s: s.lower())
        _CACHES['genres'] = { 'data': data, 'expires': now + _CACHE_TTL_SECONDS }
        return data

    @staticmethod
    def get_available_topics() -> List[str]:
        """Get list of available topics with simple in-memory caching."""
        now = time.time()
        cache = _CACHES.get('topics')
        if cache and cache['expires'] > now:
            return cache['data']

        topic_set = set()
        try:
            from .models import safe_json_loads  # lazy import
        except Exception:
            from models import safe_json_loads
        for row in Book.query.with_entities(Book.topics).filter(Book.topics.isnot(None)).all():
            for t in (safe_json_loads(row.topics) or []):
                if t:
                    topic_set.add(t)
        data = sorted(topic_set, key=lambda s: s.lower())
        _CACHES['topics'] = { 'data': data, 'expires': now + _CACHE_TTL_SECONDS }
        return data


class StatisticsService:
    """Deprecated: statistics features removed in single-page mode"""
    pass


class RecommendationService:
    """Deprecated: recommendations removed with book detail page"""
    pass

    @staticmethod
    def _derive_primary_secondary_for_items(items: List[Dict]) -> None:
        """Derive primary and secondary tags from tag_scores for each item in-place.

        - Select the highest-scoring tag as primary if score > 0
        - Select the next 3 highest as secondary
        """
        if not items:
            return
        for b in items:
            tag_scores = b.get('tag_scores') or []
            if not isinstance(tag_scores, list) or not tag_scores:
                # Fallback to topics if tag_scores are missing; topics are ordered with primary first
                topics = b.get('topics') or []
                if isinstance(topics, list) and topics:
                    try:
                        b['primary_tag'] = str(topics[0]) if topics else ''
                        b['secondary_tags'] = [str(t) for t in topics[1:4]] if len(topics) > 1 else []
                    except Exception:
                        b['primary_tag'] = ''
                        b['secondary_tags'] = []
                else:
                    b['primary_tag'] = ''
                    b['secondary_tags'] = []
                continue
            try:
                sorted_scores = sorted(
                    [d for d in tag_scores if isinstance(d, dict) and 'tag' in d],
                    key=lambda x: float(x.get('score', 0.0)),
                    reverse=True
                )
                non_zero = [d for d in sorted_scores if float(d.get('score', 0.0)) > 0]
                primary = non_zero[0]['tag'] if non_zero else ''
                secondaries = [d['tag'] for d in non_zero[1:4]] if non_zero else []
                b['primary_tag'] = primary
                b['secondary_tags'] = secondaries
            except Exception:
                b['primary_tag'] = ''
                b['secondary_tags'] = []


class CoverService:
    """Service for book cover handling"""
    
    @staticmethod
    def get_cover_data(book_id: str) -> Optional[Tuple[bytes, str]]:
        """Get book cover data and mime type"""
        book = Book.query.get(book_id)
        if not book or not book.cover_data or not book.cover_mime_type:
            return None
        
        import base64
        image_data = base64.b64decode(book.cover_data)
        return image_data, book.cover_mime_type


class ExternalRatingsService:
    """Deprecated: external ratings not used in single-page mode"""
    pass