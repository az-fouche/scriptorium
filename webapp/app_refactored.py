#!/usr/bin/env python3
"""
Library Explorer Webapp - Refactored Version

A Flask-based webapp for exploring the indexed library and getting book recommendations.
This version uses a modular architecture with clear separation of concerns.
"""

import os
import sys
from flask import Flask
import shutil

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from .config import config
    from .extensions import init_extensions
    from .controllers import register_routes
    from .utils import calculate_reading_time, get_genre_color, truncate_html
except ImportError:
    # Handle direct execution
    from config import config
    from extensions import init_extensions
    from controllers import register_routes
    from utils import calculate_reading_time, get_genre_color, truncate_html


def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])

    # Ensure key static assets exist (favicon)
    try:
        static_dir = os.path.join(app.root_path, 'static')
        os.makedirs(static_dir, exist_ok=True)
        static_icon = os.path.join(static_dir, 'icon.png')
        # Prefer existing static icon; otherwise copy from project img/
        if not os.path.exists(static_icon):
            project_img_dir = os.path.normpath(os.path.join(app.root_path, '..', 'img'))
            source_icon = os.path.join(project_img_dir, 'icon.png')
            if os.path.exists(source_icon):
                shutil.copyfile(source_icon, static_icon)
    except Exception:
        # Non-fatal if copying fails
        pass
    
    # Configure Flask-Session
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
    
    # Initialize extensions
    init_extensions(app)
    
    # Register template filters
    register_template_filters(app)

    # Register context processors
    register_context_processors(app)
    
    # Register routes
    register_routes(app)
    
    return app


def register_template_filters(app):
    """Register custom Jinja2 template filters"""
    
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Convert JSON string to Python object"""
        if value is None or value == '':
            return []
        try:
            import json
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    
    @app.template_filter('reading_time')
    def reading_time_filter(word_count):
        """Calculate reading time in minutes for template use"""
        if not word_count:
            return 0
        try:
            word_count = int(word_count)
        except (ValueError, TypeError):
            return 0
        return int(word_count / 200)  # 200 words per minute
    
    @app.template_filter('truncate_html')
    def truncate_html_filter(text, length=150):
        """Safely truncate HTML text while preserving tags"""
        return truncate_html(text, length)
    
    @app.template_filter('genre_color')
    def genre_color_filter(genre):
        """Get color class for a genre"""
        return get_genre_color(genre)
    
    @app.template_filter('translate')
    def translate_filter(key, language='en', **kwargs):
        """Translate a key to the specified language"""
        try:
            from .languages import get_translation
            return get_translation(key, language, **kwargs)
        except ImportError:
            from languages import get_translation
            return get_translation(key, language, **kwargs)

    # Tag helpers: label + color
    @app.template_filter('tag_label')
    def tag_label_filter(tag_key: str, language='en'):
        try:
            from .tag_manager import get_tag_label
        except ImportError:
            from tag_manager import get_tag_label
        return get_tag_label(tag_key, language)

    @app.template_filter('tag_color')
    def tag_color_filter(tag_key: str):
        try:
            from .tag_manager import get_tag_color_class
        except ImportError:
            from tag_manager import get_tag_color_class
        return get_tag_color_class(tag_key)
    
    # Primary tag color should never be grey; fallback to a color class if mapping is grey
    @app.template_filter('primary_tag_color')
    def primary_tag_color_filter(tag_key: str):
        try:
            from .tag_manager import get_tag_color_class
        except ImportError:
            from tag_manager import get_tag_color_class
        cls = get_tag_color_class(tag_key)
        return 'bg-primary' if cls == 'bg-secondary' else cls
    
    @app.template_filter('format_number')
    def format_number_filter(number, language='en'):
        """Format a number according to the language"""
        try:
            from .languages import format_number
            return format_number(number, language)
        except ImportError:
            from languages import format_number
            return format_number(number, language)
    
    @app.template_filter('format_file_size')
    def format_file_size_filter(size_bytes, language='en'):
        """Format file size according to the language"""
        try:
            from .languages import format_file_size
            return format_file_size(size_bytes, language)
        except ImportError:
            from languages import format_file_size
            return format_file_size(size_bytes, language)
    
    @app.template_filter('format_reading_time')
    def format_reading_time_filter(minutes, language='en'):
        """Format reading time according to the language"""
        try:
            from .languages import format_reading_time
            return format_reading_time(minutes, language)
        except ImportError:
            from languages import format_reading_time
            return format_reading_time(minutes, language)

    @app.template_filter('format_date')
    def format_date_filter(value, language='en'):
        """Format date/datetime strings to YYYY-MM-DD for display"""
        try:
            from .languages import format_date
            return format_date(value, language)
        except ImportError:
            from languages import format_date
            return format_date(value, language)


def register_context_processors(app):
    """Register template context processors"""
    @app.context_processor
    def inject_languages():
        try:
            from .languages import LANGUAGES, get_language_name, get_language_flag
        except ImportError:
            from languages import LANGUAGES, get_language_name, get_language_flag
        ctx = {
            'app_languages': LANGUAGES,
            'get_language_name': get_language_name,
            'get_language_flag': get_language_flag,
        }
        # Expose tag labels/colors maps for client-side rendering if needed
        try:
            from .tag_manager import get_tag_labels_map, get_tag_colors_map, get_tag_label
        except ImportError:
            from tag_manager import get_tag_labels_map, get_tag_colors_map, get_tag_label

        # Build complete tag maps that include all tags visible in catalog filters (genres + topics)
        try:
            # Start with existing maps
            labels_en = get_tag_labels_map('en')
            labels_fr = get_tag_labels_map('fr')
            colors = get_tag_colors_map()

            # Gather all dynamic tags from the catalogue filters
            try:
                from .services import BookService  # type: ignore
            except ImportError:
                from services import BookService  # type: ignore

            all_keys = set(labels_en.keys())
            try:
                for g in BookService.get_available_genres():
                    if g:
                        all_keys.add(str(g))
                for t in BookService.get_available_topics():
                    if t:
                        all_keys.add(str(t))
            except Exception:
                # If DB is unavailable during startup, proceed with static maps only
                pass

            # Deterministic, vibrant palette (no grey) for missing colors
            palette = ['bg-indigo', 'bg-purple', 'bg-warning', 'bg-success', 'bg-info', 'bg-pink', 'bg-danger', 'bg-dark', 'bg-primary']

            def assign_color_for_key(key: str) -> str:
                # Stable assignment without clustering too much on blue
                try:
                    idx = abs(hash(key)) % len(palette)
                except Exception:
                    idx = 0
                return palette[idx]

            # Ensure every key has a label in both languages and a non-grey color
            for k in sorted(all_keys):
                if k not in labels_en:
                    labels_en[k] = get_tag_label(k, 'en')
                if k not in labels_fr:
                    labels_fr[k] = get_tag_label(k, 'fr')
                cls = colors.get(k)
                if not cls or cls == 'bg-secondary':
                    colors[k] = assign_color_for_key(k)

            # Expose to templates/JS
            ctx['tag_labels_en'] = labels_en
            ctx['tag_labels_fr'] = labels_fr
            ctx['tag_colors'] = colors
        except Exception:
            pass
        return ctx

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Prefer running via webapp/run_refactored.py
    from .run_refactored import main
    main()
