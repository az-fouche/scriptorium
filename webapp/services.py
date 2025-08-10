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
                        # No confidence information available in topics fallback
                        b['primary_tag_score'] = None
                        b['secondary_tags_scored'] = []
                    except Exception:
                        b['primary_tag'] = ''
                        b['secondary_tags'] = []
                        b['primary_tag_score'] = None
                        b['secondary_tags_scored'] = []
                else:
                    b['primary_tag'] = ''
                    b['secondary_tags'] = []
                    b['primary_tag_score'] = None
                    b['secondary_tags_scored'] = []
                continue
            try:
                sorted_scores = sorted(
                    [d for d in tag_scores if isinstance(d, dict) and 'tag' in d],
                    key=lambda x: float(x.get('score', 0.0)),
                    reverse=True
                )
                non_zero = [d for d in sorted_scores if float(d.get('score', 0.0)) > 0]
                primary = non_zero[0]['tag'] if non_zero else ''
                primary_score = float(non_zero[0].get('score', 0.0)) if non_zero else None
                # Build secondaries with scores
                secondaries_dicts = non_zero[1:4] if non_zero else []
                secondaries = [d['tag'] for d in secondaries_dicts]
                secondaries_scored = [
                    {
                        'tag': str(d.get('tag') or ''),
                        'score': float(d.get('score', 0.0))
                    }
                    for d in secondaries_dicts
                    if d.get('tag')
                ]
                b['primary_tag'] = primary
                b['secondary_tags'] = secondaries
                b['primary_tag_score'] = primary_score
                b['secondary_tags_scored'] = secondaries_scored
            except Exception:
                b['primary_tag'] = ''
                b['secondary_tags'] = []
                b['primary_tag_score'] = None
                b['secondary_tags_scored'] = []

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
    """Service for book recommendations"""
    
    def __init__(self):
        self.books = {}
        self.load_books()
    
    def load_books(self):
        """Load all books from database"""
        books = Book.query.all()
        items = [book.to_dict() for book in books]
        BookService._derive_primary_secondary_for_items(items)
        for data in items:
            self.books[data['id']] = data
    
    def get_recommendations(self, book_id: str, limit: int = 5) -> List[Dict]:
        """Get recommendations for a book"""
        if book_id not in self.books:
            return []
        
        target_book = self.books[book_id]
        recommendations = []
        
        for other_id, other_book in self.books.items():
            if other_id == book_id:
                continue
            
            # Calculate similarity score
            score = self._calculate_similarity(target_book, other_book)
            recommendations.append({
                'book': other_book,
                'score': score,
                'reasons': self._get_recommendation_reasons(target_book, other_book, score)
            })
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    def _calculate_similarity(self, book1: Dict, book2: Dict) -> float:
        """Calculate similarity between two books"""
        score = 0.0
        
        # Language similarity (high weight)
        if book1.get('language') == book2.get('language'):
            score += 0.3
        
        # Author similarity (high weight)
        authors1 = set(book1.get('authors', []))
        authors2 = set(book2.get('authors', []))
        if authors1 and authors2:
            author_overlap = len(authors1.intersection(authors2))
            if author_overlap > 0:
                score += 0.4
        
        # Subject similarity (medium weight)
        subjects1 = set(book1.get('subjects', []))
        subjects2 = set(book2.get('subjects', []))
        if subjects1 and subjects2:
            subject_overlap = len(subjects1.intersection(subjects2))
            if subject_overlap > 0:
                score += 0.2 * subject_overlap
        
        # Publisher similarity (low weight)
        if book1.get('publisher') == book2.get('publisher'):
            score += 0.1
        
        # Word count similarity (low weight)
        wc1 = book1.get('word_count', 0)
        wc2 = book2.get('word_count', 0)
        if wc1 > 0 and wc2 > 0:
            wc_diff = abs(wc1 - wc2) / max(wc1, wc2)
            score += 0.1 * (1 - wc_diff)
        
        return min(score, 1.0)
    
    def _get_recommendation_reasons(self, book1: Dict, book2: Dict, score: float) -> List[str]:
        """Get reasons for recommendation"""
        reasons = []
        
        # Author reasons
        authors1 = set(book1.get('authors', []))
        authors2 = set(book2.get('authors', []))
        if authors1 and authors2:
            common_authors = authors1.intersection(authors2)
            if common_authors:
                reasons.append({
                    'type': 'recommendations_same_author',
                    'value': ', '.join(common_authors)
                })
        
        # Subject reasons
        subjects1 = set(book1.get('subjects', []))
        subjects2 = set(book2.get('subjects', []))
        if subjects1 and subjects2:
            common_subjects = subjects1.intersection(subjects2)
            if common_subjects:
                reasons.append({
                    'type': 'recommendations_similar_subjects',
                    'value': ', '.join(common_subjects)
                })
        
        # Language reason
        if book1.get('language') == book2.get('language'):
            reasons.append({
                'type': 'recommendations_same_language',
                'value': book1.get('language')
            })
        
        # Publisher reason
        if book1.get('publisher') == book2.get('publisher'):
            reasons.append({
                'type': 'recommendations_same_publisher',
                'value': book1.get('publisher')
            })
        
        return reasons

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
    """Fetch external user ratings for books (prototype implementation).

    Uses Google Books API by ISBN with a small in-memory TTL cache to avoid
    repeated lookups. Returns a simple dict suitable for templates:
    { 'average': float, 'count': int, 'source': str, 'url': str }
    """

    # Simple in-memory cache: { cache_key: (result_dict_or_None, expires_at_epoch) }
    _cache: Dict[str, Tuple[Optional[Dict], float]] = {}
    _ttl_seconds: int = 24 * 60 * 60  # 24 hours

    @classmethod
    def _get_cached(cls, key: str) -> Optional[Optional[Dict]]:
        import time
        entry = cls._cache.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if expires_at < time.time():
            # expired
            cls._cache.pop(key, None)
            return None
        return value

    @classmethod
    def _set_cached(cls, key: str, value: Optional[Dict]) -> None:
        import time
        cls._cache[key] = (value, time.time() + cls._ttl_seconds)

    @classmethod
    def get_rating_for_book(cls, book: Dict) -> Optional[Dict]:
        """Get external rating info for a book.

        Strategy (best-effort, fast timeouts):
        1) Try Google Books by normalized ISBN if present
        2) Try Open Library by ISBN
        3) If still missing, try Google Books by title+author
        4) Try Open Library by title+author

        Return the result with the highest rating count when multiple are available.
        """
        if not book:
            return None

        isbn_raw = (book or {}).get('isbn') or ''
        title = str((book or {}).get('title') or '').strip()
        authors = (book or {}).get('authors') or []
        language = str((book or {}).get('language') or '').strip().lower()

        # Normalize ISBN to digits only (keep 10 or 13 length if possible)
        def _normalize_isbn(value: str) -> str:
            import re as _re
            digits = ''.join(_re.findall(r'\d', str(value or '')))
            # Prefer 13 if present, else 10, else raw digits
            if len(digits) >= 13:
                return digits[-13:]
            if len(digits) == 10:
                return digits
            return digits

        isbn = _normalize_isbn(isbn_raw)

        # Attempt multiple sources, caching each attempt
        candidates: List[Dict] = []

        # Helper to fetch with cache wrapper
        def _get_with_cache(cache_key: str, fetcher):
            cached_val = cls._get_cached(cache_key)
            if cached_val is not None:
                return cached_val
            result_val = None
            try:
                result_val = fetcher()
            except Exception:
                result_val = None
            cls._set_cached(cache_key, result_val)
            return result_val

        # 1) Google by ISBN
        if isbn:
            res_g_isbn = _get_with_cache(f"google:isbn:{isbn}", lambda: cls._fetch_google_books_rating_by_isbn(isbn))
            if res_g_isbn:
                candidates.append(res_g_isbn)

        # 2) Open Library by ISBN
        if isbn:
            res_ol_isbn = _get_with_cache(f"openlibrary:isbn:{isbn}", lambda: cls._fetch_openlibrary_rating_by_isbn(isbn))
            if res_ol_isbn:
                candidates.append(res_ol_isbn)

        # Title/Author fallback only if we have at least a title
        def _first_author(auths) -> str:
            try:
                if isinstance(auths, list) and auths:
                    return str(auths[0])
                if isinstance(auths, str):
                    return auths
            except Exception:
                pass
            return ''

        first_author = _first_author(authors)
        if title:
            # 3) Google by title+author
            key = f"google:ta:{title.lower()}::{first_author.lower()}::{language}"
            res_g_ta = _get_with_cache(key, lambda: cls._fetch_google_books_rating_by_title_author(title, first_author, language))
            if res_g_ta:
                candidates.append(res_g_ta)

            # 4) Open Library by title+author
            key2 = f"openlibrary:ta:{title.lower()}::{first_author.lower()}"
            res_ol_ta = _get_with_cache(key2, lambda: cls._fetch_openlibrary_rating_by_title_author(title, first_author))
            if res_ol_ta:
                candidates.append(res_ol_ta)

        if not candidates:
            return None

        # Prefer the result with the largest number of ratings; tie-break on higher average
        def _safe_count(d: Dict) -> int:
            try:
                return int(d.get('count') or 0)
            except Exception:
                return 0
        def _safe_avg(d: Dict) -> float:
            try:
                return float(d.get('average') or 0.0)
            except Exception:
                return 0.0

        candidates.sort(key=lambda d: (_safe_count(d), _safe_avg(d)), reverse=True)
        return candidates[0]

    @staticmethod
    def _fetch_google_books_rating_by_isbn(isbn: str) -> Optional[Dict]:
        """Fetch rating via Google Books volumes API using ISBN.

        Returns None if not found or on error.
        """
        try:
            import json
            from urllib.parse import quote
            from urllib.request import urlopen, Request

            # Build request
            query = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{quote(isbn)}"
            req = Request(query, headers={
                'User-Agent': 'Scriptorium/1.0 (+https://example.local)'
            })

            with urlopen(req, timeout=3) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read().decode('utf-8', errors='ignore'))

            items = (data or {}).get('items') or []
            if not items:
                return None
            volume_info = (items[0] or {}).get('volumeInfo') or {}
            avg = volume_info.get('averageRating')
            cnt = volume_info.get('ratingsCount')
            if avg is None or cnt is None:
                return None
            link = volume_info.get('canonicalVolumeLink') or volume_info.get('infoLink') or ''
            try:
                avg_float = float(avg)
            except Exception:
                return None
            try:
                cnt_int = int(cnt)
            except Exception:
                cnt_int = 0

            return {
                'average': avg_float,
                'count': cnt_int,
                'source': 'Google Books',
                'url': link,
            }
        except Exception:
            return None

    @staticmethod
    def _fetch_google_books_rating_by_title_author(title: str, author: str, language: str = '') -> Optional[Dict]:
        """Fetch Google Books ratings using title and author as a fallback.

        Chooses the best-matching volume by simple similarity on title/author.
        """
        try:
            import json
            from urllib.parse import quote
            from urllib.request import urlopen, Request
            from difflib import SequenceMatcher

            def _norm(s: str) -> str:
                s = (s or '').strip().lower()
                return ' '.join(''.join(ch for ch in s if ch.isalnum() or ch.isspace()).split())

            q_parts = []
            if title:
                q_parts.append(f"intitle:{title}")
            if author:
                q_parts.append(f"inauthor:{author}")
            q = '+'.join(q_parts) if q_parts else quote(title)
            base = f"https://www.googleapis.com/books/v1/volumes?q={quote(q)}"
            # Restrict by language if a 2-letter code is provided
            if language and len(language) in (2, 3):
                base += f"&langRestrict={quote(language)}"
            req = Request(base, headers={'User-Agent': 'Scriptorium/1.0 (+https://example.local)'})
            with urlopen(req, timeout=3) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read().decode('utf-8', errors='ignore'))

            items = (data or {}).get('items') or []
            if not items:
                return None

            target_title = _norm(title)
            target_author = _norm(author)

            best = None
            best_score = -1.0
            for it in items:
                info = (it or {}).get('volumeInfo') or {}
                g_title = _norm(info.get('title') or '')
                g_auths = info.get('authors') or []
                g_first_author = _norm(g_auths[0] if g_auths else '')
                # Similarity on title and author
                title_sim = SequenceMatcher(a=target_title, b=g_title).ratio() if target_title and g_title else 0.0
                author_sim = SequenceMatcher(a=target_author, b=g_first_author).ratio() if target_author and g_first_author else 0.0
                sim = 0.7 * title_sim + 0.3 * author_sim
                # Prefer entries that actually have ratings
                if info.get('averageRating') is None or info.get('ratingsCount') is None:
                    continue
                if sim > best_score:
                    best = info
                    best_score = sim

            if not best:
                return None
            try:
                avg_float = float(best.get('averageRating'))
            except Exception:
                return None
            try:
                cnt_int = int(best.get('ratingsCount'))
            except Exception:
                cnt_int = 0
            link = best.get('canonicalVolumeLink') or best.get('infoLink') or ''
            return {
                'average': avg_float,
                'count': cnt_int,
                'source': 'Google Books',
                'url': link,
            }
        except Exception:
            return None

    @staticmethod
    def _fetch_openlibrary_rating_by_isbn(isbn: str) -> Optional[Dict]:
        """Fetch ratings from Open Library using ISBN via edition -> work -> ratings.

        Returns None if not found or on error.
        """
        try:
            import json
            from urllib.parse import quote
            from urllib.request import urlopen, Request

            # 1) Resolve edition to work key
            url = f"https://openlibrary.org/isbn/{quote(isbn)}.json"
            req = Request(url, headers={'User-Agent': 'Scriptorium/1.0 (+https://example.local)'})
            with urlopen(req, timeout=3) as resp:
                if resp.status != 200:
                    return None
                edition = json.loads(resp.read().decode('utf-8', errors='ignore'))
            works = (edition or {}).get('works') or []
            if not works:
                return None
            work_key = (works[0] or {}).get('key')
            if not work_key:
                return None

            # 2) Fetch ratings for work
            rurl = f"https://openlibrary.org{work_key}/ratings.json"
            rreq = Request(rurl, headers={'User-Agent': 'Scriptorium/1.0 (+https://example.local)'})
            with urlopen(rreq, timeout=3) as rresp:
                if rresp.status != 200:
                    return None
                ratings = json.loads(rresp.read().decode('utf-8', errors='ignore'))
            summary = (ratings or {}).get('summary') or {}
            counts = (ratings or {}).get('counts') or {}
            avg = summary.get('average')
            total = counts.get('total')
            if avg is None or total is None:
                return None
            return {
                'average': float(avg),
                'count': int(total),
                'source': 'Open Library',
                'url': f"https://openlibrary.org{work_key}",
            }
        except Exception:
            return None

    @staticmethod
    def _fetch_openlibrary_rating_by_title_author(title: str, author: str) -> Optional[Dict]:
        """Fetch ratings from Open Library by searching title/author -> work -> ratings."""
        try:
            import json
            from urllib.parse import quote
            from urllib.request import urlopen, Request

            # 1) Search for the work
            q = f"https://openlibrary.org/search.json?title={quote(title)}"
            if author:
                q += f"&author={quote(author)}"
            q += "&limit=5"
            req = Request(q, headers={'User-Agent': 'Scriptorium/1.0 (+https://example.local)'})
            with urlopen(req, timeout=3) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            docs = (data or {}).get('docs') or []
            if not docs:
                return None
            # Pick the top result that has a work key
            work_key = None
            for d in docs:
                key = d.get('key') or ''
                if key.startswith('/works/'):
                    work_key = key
                    break
            if not work_key:
                return None

            # 2) Fetch ratings for work
            rurl = f"https://openlibrary.org{work_key}/ratings.json"
            rreq = Request(rurl, headers={'User-Agent': 'Scriptorium/1.0 (+https://example.local)'})
            with urlopen(rreq, timeout=3) as rresp:
                if rresp.status != 200:
                    return None
                ratings = json.loads(rresp.read().decode('utf-8', errors='ignore'))
            summary = (ratings or {}).get('summary') or {}
            counts = (ratings or {}).get('counts') or {}
            avg = summary.get('average')
            total = counts.get('total')
            if avg is None or total is None:
                return None
            return {
                'average': float(avg),
                'count': int(total),
                'source': 'Open Library',
                'url': f"https://openlibrary.org{work_key}",
            }
        except Exception:
            return None

    @classmethod
    def ratings_coverage_stats(cls, sample_limit: int = 500) -> Dict[str, int]:
        """Compute naive coverage stats across a sample of books.

        Returns a dict: { total: N, with_isbn: A, found: B }
        Warning: This can trigger network calls; keep sample_limit modest.
        """
        try:
            # Lazy import to avoid circular deps
            try:
                from .models import Book  # type: ignore
            except Exception:
                from models import Book  # type: ignore

            total = 0
            with_isbn = 0
            found = 0
            # Query a deterministic sample (by title ordering) to avoid hammering APIs
            rows = Book.query.order_by(Book.title).limit(max(1, int(sample_limit))).all()
            for row in rows:
                total += 1
                item = row.to_dict()
                if item.get('isbn'):
                    with_isbn += 1
                res = None
                try:
                    res = cls.get_rating_for_book(item)
                except Exception:
                    res = None
                if res:
                    found += 1
            return { 'total': total, 'with_isbn': with_isbn, 'found': found }
        except Exception:
            return { 'total': 0, 'with_isbn': 0, 'found': 0 }