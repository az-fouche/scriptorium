"""
Language configuration and translations for the Library Explorer webapp
"""

from datetime import datetime
import re
import math

try:
    from .resource_manager import get_available_languages, get_translation as get_translation_new
    USE_RESOURCE_MANAGER = True
except ImportError:
    USE_RESOURCE_MANAGER = False

# Default language
DEFAULT_LANGUAGE = 'fr'

# Legacy translations (fallback if resource manager is not available)
LEGACY_TRANSLATIONS = {
    'en': {
        # Navigation
        'nav_home': 'Home',
        'nav_books': 'Books',
        'nav_search': 'Search',
        'nav_stats': 'Stats',
        'nav_language': 'Language',
        
        # Home page
        'hero_title': 'Library Explorer',
        'hero_subtitle': 'Discover and explore your digital library with intelligent recommendations and powerful search capabilities.',
        'hero_browse_books': 'Browse Books',
        'hero_view_stats': 'View Statistics',
        'hero_search_books': 'Search Books',
        
        # Statistics
        'stats_total_books': 'Total Books',
        'stats_total_size': 'Total Size',
        'stats_unique_authors': 'Unique Authors',
        'stats_avg_words': 'Average Words',
        'stats_recent_books': 'Recently Added',
        'stats_language_distribution': 'Language Distribution',
        'stats_word_count_stats': 'Word Count Statistics',
        'stats_file_size_stats': 'File Size Statistics',
        'stats_top_authors': 'Top Authors',
        
        # Books page
        'books_title': 'All Books',
        'books_search_placeholder': 'Search books by title, author, or description...',
        'books_filter_language': 'Filter by Language',
        'books_filter_author': 'Filter by Author',
        'books_apply_filters': 'Apply Filters',
        'books_clear_filters': 'Clear Filters',
        'books_no_results': 'No books found matching your criteria.',
        'books_loading': 'Loading books...',
        'books_error': 'Error loading books. Please try again.',
        
        # Book details
        'book_details': 'Book Details',
        'book_author': 'Author',
        'book_language': 'Language',
        'book_words': 'Words',
        'book_size': 'Size',
        'book_genres': 'Genres',
        'book_themes': 'Themes',
        'book_reading_time': 'Reading Time',
        'book_description': 'Description',
        'book_recommendations': 'Similar Books',
        'book_no_description': 'No description available.',
        'book_no_recommendations': 'No recommendations available.',
        
        # Search
        'search_title': 'Search Books',
        'search_placeholder': 'Enter your search query...',
        'search_results': 'Search Results',
        'search_no_results': 'No results found for "{{query}}".',
        'search_try_different': 'Try different keywords or browse all books.',
        
        # Common
        'loading': 'Loading...',
        'error': 'Error',
        'success': 'Success',
        'cancel': 'Cancel',
        'save': 'Save',
        'edit': 'Edit',
        'delete': 'Delete',
        'view': 'View',
        'back': 'Back',
        'next': 'Next',
        'previous': 'Previous',
        'close': 'Close',
        'open': 'Open',
        'download': 'Download',
        'upload': 'Upload',
        'refresh': 'Refresh',
        'reload': 'Reload',
        'search': 'Search',
        'filter': 'Filter',
        'sort': 'Sort',
        'all': 'All',
        'none': 'None',
        'unknown': 'Unknown',
        'yes': 'Yes',
        'no': 'No',
        'ok': 'OK',
        'apply': 'Apply',
        'clear': 'Clear',
        'reset': 'Reset',
        'submit': 'Submit',
        'confirm': 'Confirm',
        'cancel': 'Cancel',
        'delete_confirm': 'Are you sure you want to delete this item?',
        'action_success': 'Action completed successfully.',
        'action_error': 'An error occurred. Please try again.',
        
        # Pagination
        'pagination_previous': 'Previous',
        'pagination_next': 'Next',
        'pagination_page': 'Page',
        'pagination_of': 'of',
        'pagination_showing': 'Showing',
        'pagination_to': 'to',
        'pagination_of_total': 'of',
        'pagination_entries': 'entries',
        
        # Footer
        'footer_description': 'Explore your digital library and discover new books.',
        'footer_built_with': 'Risitop x Cursor',
        
        # Theme toggle
        'theme_toggle_dark': 'Switch to dark mode',
        'theme_toggle_light': 'Switch to light mode',
        
        # Autocomplete
        'autocomplete_no_results': 'No suggestions found',
        'autocomplete_loading': 'Loading suggestions...',
        'autocomplete_book': 'Book',
        'autocomplete_author': 'Author',
        
        # Debug
        'debug_database': 'Debug Database',
        'debug_autocomplete': 'Debug Autocomplete',
        'debug_test_database': 'Test Database',
        'debug_reload_database': 'Reload Database',
        
        # Stats
        'stats_books': 'Books',
        'stats_authors': 'Authors',
        'stats_languages': 'Languages',
        'stats_genres': 'Genres',
        'stats_themes': 'Themes',
        'stats_words': 'Words',
        'stats_size': 'Size',
        'stats_files': 'Files',
        'stats_percentage': 'Percentage',
        'stats_count': 'Count',
        'stats_average': 'Average',
        'stats_median': 'Median',
        'stats_minimum': 'Minimum',
        'stats_maximum': 'Maximum',
        'stats_total': 'Total',
        
        # Time
        'time_minutes': 'minutes',
        'time_hours': 'hours',
        'time_days': 'days',
        'time_weeks': 'weeks',
        'time_months': 'months',
        'time_years': 'years',
        
        # Size
        'size_bytes': 'bytes',
        'size_kb': 'KB',
        'size_mb': 'MB',
        'size_gb': 'GB',
        'size_tb': 'TB',
        
        # Numbers
        'number_thousand': 'K',
        'number_million': 'M',
        'number_billion': 'B',
        'number_trillion': 'T',
    },
    
    'fr': {
        # Navigation
        'nav_home': 'Accueil',
        'nav_books': 'Livres',
        'nav_search': 'Recherche',
        'nav_stats': 'Statistiques',
        'nav_language': 'Langue',
        
        # Home page
        'hero_title': 'Explorateur de Bibliothèque',
        'hero_subtitle': 'Découvrez et explorez votre bibliothèque numérique avec des recommandations intelligentes et des capacités de recherche puissantes.',
        'hero_browse_books': 'Parcourir les Livres',
        'hero_view_stats': 'Voir les Statistiques',
        'hero_search_books': 'Rechercher des Livres',
        
        # Statistics
        'stats_total_books': 'Total des Livres',
        'stats_total_size': 'Taille Totale',
        'stats_unique_authors': 'Auteurs Uniques',
        'stats_avg_words': 'Mots Moyens',
        'stats_recent_books': 'Ajoutés Récemment',
        'stats_language_distribution': 'Distribution des Langues',
        'stats_word_count_stats': 'Statistiques de Mots',
        'stats_file_size_stats': 'Statistiques de Taille',
        'stats_top_authors': 'Meilleurs Auteurs',
        
        # Books page
        'books_title': 'Tous les Livres',
        'books_search_placeholder': 'Rechercher des livres par titre, auteur ou description...',
        'books_filter_language': 'Filtrer par Langue',
        'books_filter_author': 'Filtrer par Auteur',
        'books_apply_filters': 'Appliquer les Filtres',
        'books_clear_filters': 'Effacer les Filtres',
        'books_no_results': 'Aucun livre trouvé correspondant à vos critères.',
        'books_loading': 'Chargement des livres...',
        'books_error': 'Erreur lors du chargement des livres. Veuillez réessayer.',
        
        # Book details
        'book_details': 'Détails du Livre',
        'book_author': 'Auteur',
        'book_language': 'Langue',
        'book_words': 'Mots',
        'book_size': 'Taille',
        'book_genres': 'Genres',
        'book_themes': 'Thèmes',
        'book_reading_time': 'Temps de Lecture',
        'book_description': 'Description',
        'book_recommendations': 'Livres Similaires',
        'book_no_description': 'Aucune description disponible.',
        'book_no_recommendations': 'Aucune recommandation disponible.',
        
        # Search
        'search_title': 'Rechercher des Livres',
        'search_placeholder': 'Entrez votre requête de recherche...',
        'search_results': 'Résultats de Recherche',
        'search_no_results': 'Aucun résultat trouvé pour "{{query}}".',
        'search_try_different': 'Essayez des mots-clés différents ou parcourez tous les livres.',
        
        # Common
        'loading': 'Chargement...',
        'error': 'Erreur',
        'success': 'Succès',
        'cancel': 'Annuler',
        'save': 'Enregistrer',
        'edit': 'Modifier',
        'delete': 'Supprimer',
        'view': 'Voir',
        'back': 'Retour',
        'next': 'Suivant',
        'previous': 'Précédent',
        'close': 'Fermer',
        'open': 'Ouvrir',
        'download': 'Télécharger',
        'upload': 'Téléverser',
        'refresh': 'Actualiser',
        'reload': 'Recharger',
        'search': 'Rechercher',
        'filter': 'Filtrer',
        'sort': 'Trier',
        'all': 'Tous',
        'none': 'Aucun',
        'unknown': 'Inconnu',
        'yes': 'Oui',
        'no': 'Non',
        'ok': 'OK',
        'apply': 'Appliquer',
        'clear': 'Effacer',
        'reset': 'Réinitialiser',
        'submit': 'Soumettre',
        'confirm': 'Confirmer',
        'delete_confirm': 'Êtes-vous sûr de vouloir supprimer cet élément ?',
        'action_success': 'Action terminée avec succès.',
        'action_error': 'Une erreur s\'est produite. Veuillez réessayer.',
        
        # Pagination
        'pagination_previous': 'Précédent',
        'pagination_next': 'Suivant',
        'pagination_page': 'Page',
        'pagination_of': 'sur',
        'pagination_showing': 'Affichage de',
        'pagination_to': 'à',
        'pagination_of_total': 'sur',
        'pagination_entries': 'entrées',
        
        # Footer
        'footer_description': 'Explorez votre bibliothèque numérique et découvrez de nouveaux livres.',
        'footer_built_with': 'Risitop x Cursor',
        
        # Theme toggle
        'theme_toggle_dark': 'Passer au mode sombre',
        'theme_toggle_light': 'Passer au mode clair',
        
        # Autocomplete
        'autocomplete_no_results': 'Aucune suggestion trouvée',
        'autocomplete_loading': 'Chargement des suggestions...',
        'autocomplete_book': 'Livre',
        'autocomplete_author': 'Auteur',
        
        # Debug
        'debug_database': 'Déboguer la Base de Données',
        'debug_autocomplete': 'Déboguer l\'Autocomplétion',
        'debug_test_database': 'Tester la Base de Données',
        'debug_reload_database': 'Recharger la Base de Données',
        
        # Stats
        'stats_books': 'Livres',
        'stats_authors': 'Auteurs',
        'stats_languages': 'Langues',
        'stats_genres': 'Genres',
        'stats_themes': 'Thèmes',
        'stats_words': 'Mots',
        'stats_size': 'Taille',
        'stats_files': 'Fichiers',
        'stats_percentage': 'Pourcentage',
        'stats_count': 'Compte',
        'stats_average': 'Moyenne',
        'stats_median': 'Médiane',
        'stats_minimum': 'Minimum',
        'stats_maximum': 'Maximum',
        'stats_total': 'Total',
        
        # Time
        'time_minutes': 'minutes',
        'time_hours': 'heures',
        'time_days': 'jours',
        'time_weeks': 'semaines',
        'time_months': 'mois',
        'time_years': 'années',
        
        # Size
        'size_bytes': 'octets',
        'size_kb': 'Ko',
        'size_mb': 'Mo',
        'size_gb': 'Go',
        'size_tb': 'To',
        
        # Numbers
        'number_thousand': 'K',
        'number_million': 'M',
        'number_billion': 'G',
        'number_trillion': 'T',
    }
}

# Get available languages
if USE_RESOURCE_MANAGER:
    LANGUAGES = get_available_languages()
else:
    LANGUAGES = {
        'en': {
            'name': 'English',
            'flag': '🇺🇸',
            'code': 'en'
        },
        'fr': {
            'name': 'Français',
            'flag': '🇫🇷',
            'code': 'fr'
        }
    }

def get_language(request):
    """Get the current language from request args, Flask session, or cookie"""
    # 1) URL parameter has highest priority
    lang = request.args.get('lang')
    if lang and lang in LANGUAGES:
        return lang

    # 2) Flask session (set in controllers set_language route)
    try:
        from flask import session as flask_session
        lang = flask_session.get('language')
        if lang and lang in LANGUAGES:
            return lang
    except Exception:
        pass

    # 3) Cookie fallback
    try:
        lang = request.cookies.get('language')
        if lang and lang in LANGUAGES:
            return lang
    except Exception:
        pass

    # Default
    return DEFAULT_LANGUAGE

def get_translation(key, language=None, **kwargs):
    """Get a translation for a given key and language"""
    if language is None:
        language = DEFAULT_LANGUAGE
    
    # Use resource manager if available
    if USE_RESOURCE_MANAGER:
        return get_translation_new(key, language, **kwargs)
    
    # Fallback to legacy translations
    if language not in LEGACY_TRANSLATIONS:
        language = DEFAULT_LANGUAGE
    
    translation = LEGACY_TRANSLATIONS[language].get(key, key)
    
    # Replace placeholders with kwargs
    for k, v in kwargs.items():
        translation = translation.replace(f'{{{{{k}}}}}', str(v))
    
    return translation

def get_language_name(language_code):
    """Get the display name for a language code"""
    return LANGUAGES.get(language_code, {}).get('name', language_code)

def get_language_flag(language_code):
    """Get the flag emoji for a language code"""
    return LANGUAGES.get(language_code, {}).get('flag', '🌐')

def format_number(number, language='en'):
    """Format a number according to the language"""
    if language == 'fr':
        # French number formatting (space as thousands separator)
        return f"{number:,}".replace(',', ' ')
    else:
        # English number formatting (comma as thousands separator)
        return f"{number:,}"

def format_file_size(size_bytes, language='en'):
    """Format file size according to the language"""
    if size_bytes < 1024:
        return f"{size_bytes} {get_translation('size_bytes', language)}"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} {get_translation('size_kb', language)}"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} {get_translation('size_mb', language)}"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} {get_translation('size_gb', language)}"

def format_reading_time(minutes, language='en'):
    """Format reading time with hour granularity rounded up.

    We intentionally round up to the next whole hour (e.g., 2h05 -> 3 hours).
    """
    # Support both Resource Manager (nested keys) and legacy flat keys
    def t_time(key_flat: str) -> str:
        if USE_RESOURCE_MANAGER:
            return get_translation(f"time.{key_flat}", language)
        return get_translation(key_flat, language)

    try:
        minutes_int = int(minutes)
    except Exception:
        minutes_int = 0

    if minutes_int <= 0:
        hours = 0
    else:
        hours = max(1, math.ceil(minutes_int / 60))

    # Compact format like 8h
    if language == 'fr':
        return f"{hours} h"
    return f"{hours}h"
    
def format_date(value, language='en'):
    """Format a date/datetime string to a simple YYYY-MM-DD date.
    
    Accepts ISO 8601 strings (e.g., 2013-03-04T13:10:15+00:00 or with Z),
    date-only strings (YYYY-MM-DD), or datetime objects. Falls back to the
    original value on parse failure.
    
    The language parameter is reserved for future localization.
    """
    if not value:
        return ''
    try:
        # If already a datetime-like object
        if hasattr(value, 'date'):
            return value.date().isoformat()
        if isinstance(value, str):
            s = value.strip()
            # Fast path: already starts with YYYY-MM-DD
            if len(s) >= 10 and re.match(r'^\d{4}-\d{2}-\d{2}', s):
                return s[:10]
            # Try ISO 8601 parsing (handle Z suffix)
            s_iso = s.replace('Z', '+00:00')
            dt = datetime.fromisoformat(s_iso)
            return dt.date().isoformat()
    except Exception:
        pass
    return str(value)
