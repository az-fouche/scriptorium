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
        # Copy ICO if present to static for predictable serving by web servers/CSPs
        static_favicon_ico = os.path.join(static_dir, 'favicon.ico')
        project_img_dir = os.path.normpath(os.path.join(app.root_path, '..', 'img'))
        source_favicon_ico = os.path.join(project_img_dir, 'favicon.ico')
        if not os.path.exists(static_favicon_ico) and os.path.exists(source_favicon_ico):
            shutil.copyfile(source_favicon_ico, static_favicon_ico)

        # Also ensure legacy PNG remains available as a fallback
        static_icon_png = os.path.join(static_dir, 'icon.png')
        source_icon_png = os.path.join(project_img_dir, 'icon.png')
        if not os.path.exists(static_icon_png) and os.path.exists(source_icon_png):
            shutil.copyfile(source_icon_png, static_icon_png)
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

    # Compute inline background color style for a secondary tag given its score.
    # The color is mixed between the tag's base color and grey based on alpha derived from score.
    # Above a threshold (default 0.5), we use full color.
    @app.template_filter('secondary_tag_style')
    def secondary_tag_style_filter(tag_key: str, score: float = 0.0, threshold: float = 0.75):
        try:
            from .tag_manager import get_tag_color_class
        except ImportError:
            from tag_manager import get_tag_color_class
        try:
            s = float(score or 0.0)
        except Exception:
            s = 0.0
        # Clamp and derive alpha with a gentle curve; linear for now, can adjust later
        alpha = max(0.0, min(1.0, s))
        if alpha >= threshold:
            # Use full color via class; no inline style needed
            return ''
        base_class = get_tag_color_class(tag_key) or 'bg-secondary'
        # Map known classes to RGB
        color_map = {
            'bg-pink': (232, 62, 140),
            'bg-purple': (111, 66, 193),
            'bg-indigo': (102, 16, 242),
            'bg-danger': (220, 53, 69),
            'bg-warning': (255, 193, 7),
            'bg-info': (13, 202, 240),
            'bg-success': (25, 135, 84),
            'bg-primary': (13, 110, 253),
            'bg-dark': (33, 37, 41),
            'bg-secondary': (108, 117, 125),
        }
        r, g, b = color_map.get(base_class, (108, 117, 125))
        # Grey to blend with
        gr, gg, gb = (108, 117, 125)
        mix = lambda c, gc: int(round(alpha * c + (1.0 - alpha) * gc))
        mr, mg, mb = mix(r, gr), mix(g, gg), mix(b, gb)
        # Inline background-color + text color for contrast when blending towards grey
        text_color = '#000000' if (0.299*mr + 0.587*mg + 0.114*mb) > 186 else '#ffffff'
        return f"background-color: rgb({mr}, {mg}, {mb}) !important; color: {text_color} !important;"

    @app.template_filter('secondary_tag_use_full')
    def secondary_tag_use_full_filter(score: float = 0.0, threshold: float = 0.75):
        try:
            s = float(score or 0.0)
        except Exception:
            s = 0.0
        return s >= threshold

    @app.template_filter('secondary_tag_bg')
    def secondary_tag_bg_filter(tag_key: str, score: float = 0.0, threshold: float = 0.75):
        try:
            from .tag_manager import get_tag_color_class
        except ImportError:
            from tag_manager import get_tag_color_class
        try:
            s = float(score or 0.0)
        except Exception:
            s = 0.0
        if s >= threshold:
            return ''
        base_class = get_tag_color_class(tag_key) or 'bg-secondary'
        color_map = {
            'bg-pink': (232, 62, 140),
            'bg-purple': (111, 66, 193),
            'bg-indigo': (102, 16, 242),
            'bg-danger': (220, 53, 69),
            'bg-warning': (255, 193, 7),
            'bg-info': (13, 202, 240),
            'bg-success': (25, 135, 84),
            'bg-primary': (13, 110, 253),
            'bg-dark': (33, 37, 41),
            'bg-secondary': (108, 117, 125),
        }
        r, g, b = color_map.get(base_class, (108, 117, 125))
        gr, gg, gb = (108, 117, 125)
        alpha = max(0.0, min(1.0, s))
        mr = int(round(alpha * r + (1.0 - alpha) * gr))
        mg = int(round(alpha * g + (1.0 - alpha) * gg))
        mb = int(round(alpha * b + (1.0 - alpha) * gb))
        return f"rgb({mr}, {mg}, {mb})"

    @app.template_filter('secondary_tag_fg')
    def secondary_tag_fg_filter(tag_key: str, score: float = 0.0, threshold: float = 0.75):
        # Foreground color based on mixed background luminance
        try:
            from .tag_manager import get_tag_color_class
        except ImportError:
            from tag_manager import get_tag_color_class
        try:
            s = float(score or 0.0)
        except Exception:
            s = 0.0
        if s >= threshold:
            return ''
        color_map = {
            'bg-pink': (232, 62, 140),
            'bg-purple': (111, 66, 193),
            'bg-indigo': (102, 16, 242),
            'bg-danger': (220, 53, 69),
            'bg-warning': (255, 193, 7),
            'bg-info': (13, 202, 240),
            'bg-success': (25, 135, 84),
            'bg-primary': (13, 110, 253),
            'bg-dark': (33, 37, 41),
            'bg-secondary': (108, 117, 125),
        }
        base_class = get_tag_color_class(tag_key) or 'bg-secondary'
        r, g, b = color_map.get(base_class, (108, 117, 125))
        gr, gg, gb = (108, 117, 125)
        alpha = max(0.0, min(1.0, s))
        mr = int(round(alpha * r + (1.0 - alpha) * gr))
        mg = int(round(alpha * g + (1.0 - alpha) * gg))
        mb = int(round(alpha * b + (1.0 - alpha) * gb))
        return '#000000' if (0.299*mr + 0.587*mg + 0.114*mb) > 186 else '#ffffff'
    
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
        # Add favicon version for cache-busting
        try:
            static_dir = os.path.join(app.root_path, 'static')
            favicon_path = os.path.join(static_dir, 'favicon.ico')
            ctx['favicon_version'] = str(int(os.path.getmtime(favicon_path))) if os.path.exists(favicon_path) else '1'
        except Exception:
            ctx['favicon_version'] = '1'
        return ctx

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Prefer running via webapp/run_refactored.py
    from .run_refactored import main
    main()
