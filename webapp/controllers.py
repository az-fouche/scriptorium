"""
Route handlers and request processing for the library webapp
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from flask import (
    Flask, render_template, request, jsonify, redirect, 
    url_for, Response, current_app, session, abort
)
from sqlalchemy import text

try:
    from .models import db, Book
    from .services import BookService, StatisticsService, RecommendationService, CoverService, ExternalRatingsService
    from .utils import calculate_reading_time, get_genre_color, truncate_html
    from .languages import get_language, get_translation
    from .resource_manager import reload_language as reload_i18n_language
except ImportError:
    from models import db, Book
    from services import BookService, StatisticsService, RecommendationService, CoverService, ExternalRatingsService
    from utils import calculate_reading_time, get_genre_color, truncate_html
    from languages import get_language, get_translation
    from resource_manager import reload_language as reload_i18n_language


    


def register_routes(app: Flask):
    """Register all routes with the Flask app"""
    
    @app.route('/')
    def index():
        """Home page"""
        # Get current language
        language = get_language(request)
        # Ensure freshest translations from JSON (avoid stale cache)
        try:
            reload_i18n_language(language)
        except Exception:
            pass
        
        # Get basic statistics
        stats = StatisticsService.get_basic_stats()
        
        # Get 4 random books for Explore section
        explore_books = BookService.get_random_books(limit=4)
        
        return render_template('index.html', 
                             total_books=stats['total_books'],
                             explore_books=explore_books,
                             total_size_mb=stats['total_size_mb'],
                             unique_authors=stats['unique_authors'],
                             current_language=language)
    
    @app.route('/random')
    def random_book():
        """Redirect to a random book"""
        # Get current language for consistency
        current_language = get_language(request)
        book = BookService.get_random_book()
        if not book:
            # If no book, send back to home
            return redirect(url_for('index'))
        return redirect(url_for('book_detail', book_id=book['id']))

    
    
    @app.route('/books')
    def books():
        """Books listing page"""
        # Get current language
        current_language = get_language(request)
        
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Get search parameters (single bar for title or author)
        search = request.args.get('search', '')
        language = ''  # language filter removed from UI
        author = ''    # author field removed; handled via single search bar
        # Multi-select filters (repeated params or comma-separated)
        def _parse_multi(param_name: str):
            values = request.args.getlist(param_name)
            # support comma-separated in single value
            if len(values) == 1 and ',' in values[0]:
                values = [v.strip() for v in values[0].split(',') if v.strip()]
            return [v for v in values if v]
        selected_genres = _parse_multi('genre')
        selected_topics = _parse_multi('topic')
        
        # Get books with filters
        books_list, total, pages = BookService.get_books_with_filters(
            search=search,
            language=language,
            author=author,
            genres=selected_genres,
            topics=selected_topics,
            page=page,
            per_page=per_page
        )
        
        # Create a custom pagination object that uses to_dict() for items
        class CustomPagination:
            def __init__(self, items, total, pages, page, per_page):
                self._items = items
                self._total = total
                self._pages = pages
                self._page = page
                self._per_page = per_page
            
            @property
            def items(self):
                return self._items
            
            @property
            def total(self):
                return self._total
            
            @property
            def pages(self):
                return self._pages
            
            @property
            def page(self):
                return self._page
            
            @property
            def per_page(self):
                return self._per_page
            
            @property
            def has_prev(self):
                return self._page > 1
            
            @property
            def has_next(self):
                return self._page < self._pages
            
            @property
            def prev_num(self):
                return self._page - 1 if self._page > 1 else None
            
            @property
            def next_num(self):
                return self._page + 1 if self._page < self._pages else None
            
            def iter_pages(self):
                # Simple page iteration
                start = max(1, self._page - 2)
                end = min(self._pages, self._page + 2)
                return range(start, end + 1)
        
        books = CustomPagination(books_list, total, pages, page, per_page)
        
        # Get available filters
        languages = []  # not used in UI anymore
        # Use unified tags for filter options to avoid duplicates in UI
        all_genres = BookService.get_available_genres()
        all_topics = []
        
        return render_template('books.html', 
                             books=books,
                             search=search,
                             language=language,
                             author=author,
                             languages=languages,
                             all_genres=all_genres,
                             all_topics=all_topics,
                             selected_genres=selected_genres,
                             selected_topics=selected_topics,
                             current_language=current_language)
    
    @app.route('/book/<book_id>')
    def book_detail(book_id):
        """Book detail page"""
        # Get current language
        current_language = get_language(request)
        
        book = BookService.get_book_by_id(book_id)
        if not book:
            return render_template('404.html'), 404
        
        # Get recommendations
        recommendation_service = RecommendationService()
        recommendations = recommendation_service.get_recommendations(book_id, limit=6)

        # External user rating (non-blocking best-effort)
        try:
            external_rating = ExternalRatingsService.get_rating_for_book(book) if book else None
        except Exception:
            external_rating = None
        
        return render_template('book_detail.html', 
                             book=book,
                             recommendations=recommendations,
                             external_rating=external_rating,
                             current_language=current_language)
    
    @app.route('/api/books')
    def api_books():
        """API endpoint for books"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')

        # Multi-select filters (repeated params or comma-separated)
        def _parse_multi(param_name: str):
            values = request.args.getlist(param_name)
            if len(values) == 1 and ',' in values[0]:
                values = [v.strip() for v in values[0].split(',') if v.strip()]
            return [v for v in values if v]
        selected_genres = _parse_multi('genre')
        selected_topics = _parse_multi('topic')

        books_list, total, pages = BookService.get_books_with_filters(
            search=search,
            genres=selected_genres,
            topics=selected_topics,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'books': books_list,
            'total': total,
            'pages': pages,
            'current_page': page
        })

    @app.route('/api/random_books')
    def api_random_books():
        """API endpoint to fetch random books, excluding a set of IDs"""
        limit = request.args.get('limit', 4, type=int)
        exclude = request.args.get('exclude', '', type=str)
        exclude_ids = [bid for bid in exclude.split(',') if bid]

        books = BookService.get_random_books(limit=limit, exclude_ids=exclude_ids)
        return jsonify(books)
    
    @app.route('/api/book/<book_id>/recommendations')
    def api_recommendations(book_id):
        """API endpoint for book recommendations"""
        recommendation_service = RecommendationService()
        recommendations = recommendation_service.get_recommendations(book_id, limit=10)
        return jsonify(recommendations)
    
    @app.route('/stats')
    def stats():
        """Statistics page"""
        # Get current language
        current_language = get_language(request)
        
        # Basic stats
        basic_stats = StatisticsService.get_basic_stats()
        # File size stats (used by overview card at the top)
        size_stats = StatisticsService.get_size_stats()
        
        # Top authors (initial slice)
        top_authors = StatisticsService.get_top_authors(20)

        return render_template('stats.html',
                             total_books=basic_stats['total_books'],
                             size_stats=size_stats,
                             top_authors=top_authors,
                             current_language=current_language)

    @app.route('/api/top-authors')
    def api_top_authors():
        """Paginated API for top authors for infinite scrolling on stats page."""
        try:
            offset = request.args.get('offset', 0, type=int)
            limit = request.args.get('limit', 20, type=int)
        except Exception:
            offset, limit = 0, 20
        items, total = StatisticsService.get_top_authors_paginated(offset=offset, limit=limit)
        return jsonify({
            'items': items,
            'total': total,
            'offset': offset,
            'limit': limit
        })
    
    @app.route('/api/debug-database')
    def api_debug_database():
        """Debug database connection and content"""
        if not current_app.config.get('DEBUG', False):
            return abort(404)
        try:
            # Direct SQL query
            result = db.session.execute(text("SELECT COUNT(*) as count FROM books")).fetchone()
            sql_count = result.count if result else 0
            
            # SQLAlchemy query
            orm_count = BookService.get_total_books()
            
            # Check database file
            db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            file_exists = os.path.exists(db_path)
            file_size = os.path.getsize(db_path) if file_exists else 0
            file_mtime = os.path.getmtime(db_path) if file_exists else 0
            
            return jsonify({
                'sql_count': sql_count,
                'orm_count': orm_count,
                'file_exists': file_exists,
                'file_size': file_size,
                'file_mtime': file_mtime,
                'db_uri': current_app.config['SQLALCHEMY_DATABASE_URI'],
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/api/reload-database')
    def api_reload_database():
        """Manually trigger database reload"""
        try:
            if hasattr(current_app, 'db_reloader'):
                success = current_app.db_reloader.reload_database()
                return jsonify({
                    'success': success,
                    'message': 'Database reloaded successfully' if success else 'Database reload failed',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Database reloader not available',
                    'timestamp': datetime.now().isoformat()
                }), 500
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @app.route('/cover/<book_id>')
    def book_cover(book_id):
        """Serve book cover image"""
        try:
            cover_data = CoverService.get_cover_data(book_id)

            if not cover_data:
                # Generate a clean, readable SVG placeholder as default cover
                from html import escape
                import textwrap
                book = BookService.get_book_by_id(book_id) or {}
                raw_title = book.get('title') or 'Unknown'
                # Wrap the title across up to 3 lines to avoid overflow in the SVG
                wrapped_lines = textwrap.wrap(raw_title, width=18)
                is_truncated = len(wrapped_lines) > 3
                wrapped_lines = wrapped_lines[:3] if wrapped_lines else ['Unknown']
                if is_truncated:
                    # Add ellipsis to the last visible line
                    last = wrapped_lines[-1]
                    wrapped_lines[-1] = (last[:-1] + '…') if len(last) > 1 else '…'

                # Build tspans centered with consistent vertical rhythm
                tspans = []
                for idx, line in enumerate(wrapped_lines):
                    safe_line = escape(line)
                    dy = '-1.2em' if idx == 0 else '1.2em'
                    tspans.append(f"<tspan x='50%' dy='{dy}'>" + safe_line + "</tspan>")
                tspans_markup = ''.join(tspans)

                # Derive author display string
                authors = book.get('authors') or []
                if isinstance(authors, list):
                    authors_text = ', '.join([str(a) for a in authors if a]) or 'Unknown Author'
                else:
                    authors_text = str(authors) or 'Unknown Author'
                safe_authors = escape(authors_text)

                svg = f"""
                <svg xmlns='http://www.w3.org/2000/svg' width='600' height='900' viewBox='0 0 600 900'>
                  <defs>
                    <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
                      <stop offset='0%' stop-color='#4b6ea8'/>
                      <stop offset='100%' stop-color='#2d3f66'/>
                    </linearGradient>
                    <filter id='s' x='-20%' y='-20%' width='140%' height='140%'>
                      <feDropShadow dx='0' dy='6' stdDeviation='12' flood-color='rgba(0,0,0,0.35)'/>
                    </filter>
                  </defs>
                  <rect width='600' height='900' fill='url(#g)'/>
                  <rect x='28' y='28' width='544' height='844' fill='none' stroke='rgba(255,255,255,0.35)' stroke-width='2' rx='12'/>
                  <g filter='url(#s)'>
                    <text x='50%' y='45%' dominant-baseline='middle' text-anchor='middle' font-family='Georgia, Times, serif' font-size='34' fill='rgba(255,255,255,0.95)' letter-spacing='0.5'>
                      {tspans_markup}
                    </text>
                  </g>
                  <text x='50%' y='62%' dominant-baseline='middle' text-anchor='middle' font-family='Georgia, Times, serif' font-size='20' fill='rgba(255,255,255,0.7)'>
                    {safe_authors}
                  </text>
                </svg>
                """.strip()
                response = Response(svg.encode('utf-8'), mimetype='image/svg+xml')
                response.headers['Cache-Control'] = 'public, max-age=86400'
                return response

            image_data, mime_type = cover_data

            # Create response with proper headers
            response = Response(image_data, mimetype=mime_type)
            response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache for 1 year
            return response
            
        except Exception as e:
            print(f"Error serving cover for book {book_id}: {e}")
            # Fallback to a minimal SVG placeholder
            fallback_svg = """
            <svg xmlns='http://www.w3.org/2000/svg' width='600' height='900' viewBox='0 0 600 900'>
              <rect width='600' height='900' fill='#2d3f66'/>
              <text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' font-family='Georgia, Times, serif' font-size='36' fill='rgba(255,255,255,0.9)'>No Cover</text>
            </svg>
            """.strip()
            return Response(fallback_svg.encode('utf-8'), mimetype='image/svg+xml')
    
    @app.route('/api/autocomplete')
    def api_autocomplete():
        """API endpoint for search autocomplete"""
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify([])
        
        try:
            # Get autocomplete suggestions
            suggestions = BookService.get_autocomplete_suggestions(query, limit=10)
            
            # Debug logging via app logger
            try:
                current_app.logger.debug("Autocomplete query='%s' suggestions=%d", query, len(suggestions))
            except Exception:
                pass
            
            return jsonify(suggestions)
        except Exception as e:
            try:
                current_app.logger.exception("Error in autocomplete API: %s", e)
            except Exception:
                pass
            return jsonify([])
    
    @app.route('/search')
    def search():
        """Deprecated: redirect to books with query mapped to 'search' filter"""
        query = request.args.get('q', '').strip()
        if query:
            return redirect(url_for('books', search=query))
        return redirect(url_for('books'))
    
    @app.route('/language/<language_code>')
    def set_language(language_code):
        """Switch UI language and persist preference"""
        try:
            from .languages import LANGUAGES
        except ImportError:
            from languages import LANGUAGES

        lang = language_code if language_code in LANGUAGES else 'en'
        session['language'] = lang

        # Redirect back to the referring page or home
        response = redirect(request.referrer or url_for('index'))
        # Also set a cookie for client-side access if needed
        response.set_cookie('language', lang, max_age=60*60*24*365)
        return response

    @app.route('/debug-autocomplete')
    def debug_autocomplete():
        """Debug page for autocomplete functionality"""
        if not current_app.config.get('DEBUG', False):
            return abort(404)
        # Get current language
        current_language = get_language(request)
        
        return render_template('debug_autocomplete.html', current_language=current_language)
    
    @app.route('/api/test-database')
    def api_test_database():
        """Test endpoint to check database content"""
        if not current_app.config.get('DEBUG', False):
            return abort(404)
        try:
            total_books = BookService.get_total_books()
            sample_books = BookService.get_recent_books(5)
            
            return jsonify({
                'total_books': total_books,
                'sample_books': sample_books,
                'database_working': True
            })
        except Exception as e:
            return jsonify({
                'error': str(e),
                'database_working': False
            })
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon for browsers requesting /favicon.ico"""
        from flask import send_from_directory
        static_dir = os.path.join(app.root_path, 'static')
        # Prefer a dedicated favicon.ico if present; otherwise use PNGs
        ico_path = os.path.join(static_dir, 'favicon.ico')
        png_static_path = os.path.join(static_dir, 'icon.png')
        if os.path.exists(ico_path):
            return send_from_directory(static_dir, 'favicon.ico', cache_timeout=31536000)
        if os.path.exists(png_static_path):
            return send_from_directory(static_dir, 'icon.png', cache_timeout=31536000)
        # Fallback to project-level img/icon.png
        project_img_dir = os.path.normpath(os.path.join(app.root_path, '..', 'img'))
        png_project_path = os.path.join(project_img_dir, 'icon.png')
        if os.path.exists(png_project_path):
            return send_from_directory(project_img_dir, 'icon.png', cache_timeout=31536000)
        # If nothing found, 404
        return abort(404)
    
    return app
