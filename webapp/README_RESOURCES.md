# Webapp Resource Management System

This document describes the new resource management system for internationalization in the Library Explorer webapp.

## Overview

The webapp now uses a JSON-based resource management system for all text content, making it easy to:
- Add new languages
- Edit translations without touching code
- Maintain consistent translation keys
- Support nested translation keys for better organization

## File Structure

```
webapp/
├── resources/
│   ├── en.json          # English translations
│   ├── fr.json          # French translations
│   └── ...              # Additional language files
├── resource_manager.py  # Resource management system
├── languages.py         # Updated to use resource manager
└── templates/           # Updated templates using new keys
```

## Translation Keys Structure

Translations are organized into logical categories using dot notation:

### Navigation
- `navigation.nav_home` - Home
- `navigation.nav_books` - Books
- `navigation.nav_search` - Search
- `navigation.nav_stats` - Stats
- `navigation.nav_language` - Language

### Home Page
- `home.hero_title` - Main title
- `home.hero_subtitle` - Subtitle
- `home.hero_browse_books` - Browse books button
- `home.hero_search_books` - Search books button
- `home.hero_view_stats` - View stats button

### Statistics
- `statistics.stats_total_books` - Total books
- `statistics.stats_total_size` - Total size
- `statistics.stats_unique_authors` - Unique authors
- `statistics.stats_recent_books` - Recently added
- `statistics.stats_books` - Books (plural)
- `statistics.stats_authors` - Authors
- `statistics.stats_languages` - Languages
- `statistics.stats_words` - Words
- `statistics.stats_size` - Size
- `statistics.stats_count` - Count
- `statistics.stats_average` - Average
- `statistics.stats_total` - Total

### Books
- `books.books_title` - All books title
- `books.books_search_placeholder` - Search placeholder
- `books.books_filter_author` - Filter by author placeholder
- `books.books_no_results` - No results message
- `books.books_loading` - Loading message
- `books.books_error` - Error message

### Book Details
- `book_details.book_author` - Author
- `book_details.book_language` - Language
- `book_details.book_words` - Words
- `book_details.book_size` - Size
- `book_details.book_genres` - Genres
- `book_details.book_themes` - Themes
- `book_details.book_reading_time` - Reading time
- `book_details.book_description` - Description
- `book_details.book_recommendations` - Similar books

### Search
- `search.search_title` - Search title
- `search.search_placeholder` - Search placeholder
- `search.search_results` - Search results
- `search.search_no_results` - No results message
- `search.search_try_different` - Try different keywords

### Common Actions
- `common.loading` - Loading
- `common.error` - Error
- `common.success` - Success
- `common.view` - View
- `common.edit` - Edit
- `common.delete` - Delete
- `common.search` - Search
- `common.filter` - Filter
- `common.all` - All
- `common.unknown` - Unknown
- `common.yes` - Yes
- `common.no` - No

### Pagination
- `pagination.pagination_previous` - Previous
- `pagination.pagination_next` - Next
- `pagination.pagination_page` - Page
- `pagination.pagination_showing` - Showing
- `pagination.pagination_of_total` - of total

### Footer
- `footer.footer_description` - Footer description
- `footer.footer_built_with` - Built with text

### Theme
- `theme.theme_toggle_dark` - Switch to dark mode
- `theme.theme_toggle_light` - Switch to light mode

### Autocomplete
- `autocomplete.autocomplete_no_results` - No suggestions
- `autocomplete.autocomplete_loading` - Loading suggestions
- `autocomplete.autocomplete_book` - Book type
- `autocomplete.autocomplete_author` - Author type

### Debug
- `debug.debug_database` - Debug database
- `debug.debug_autocomplete` - Debug autocomplete
- `debug.debug_test_database` - Test database
- `debug.debug_reload_database` - Reload database

### Time
- `time.time_minutes` - minutes
- `time.time_hours` - hours
- `time.time_days` - days
- `time.time_weeks` - weeks
- `time.time_months` - months
- `time.time_years` - years

### Size
- `size.size_bytes` - bytes
- `size.size_kb` - KB
- `size.size_mb` - MB
- `size.size_gb` - GB
- `size.size_tb` - TB

### Numbers
- `numbers.number_thousand` - K
- `numbers.number_million` - M
- `numbers.number_billion` - B
- `numbers.number_trillion` - T

## Adding a New Language

1. Create a new JSON file in the `resources/` directory:
   ```bash
   touch webapp/resources/es.json
   ```

2. Add the language metadata and translations:
   ```json
   {
     "_meta": {
       "name": "Español",
       "flag": "🇪🇸",
       "code": "es"
     },
     "navigation": {
       "nav_home": "Inicio",
       "nav_books": "Libros",
       "nav_search": "Buscar",
       "nav_stats": "Estadísticas",
       "nav_language": "Idioma"
     },
     "home": {
       "hero_title": "Explorador de Biblioteca",
       "hero_subtitle": "Descubre y explora tu biblioteca digital con recomendaciones inteligentes y capacidades de búsqueda potentes.",
       "hero_browse_books": "Explorar Libros",
       "hero_search_books": "Buscar Libros",
       "hero_view_stats": "Ver Estadísticas"
     }
     // ... continue with all other sections
   }
   ```

3. The language will automatically be available in the language dropdown.

## Using Translations in Templates

Use the `translate` filter with the new nested key format:

```html
<!-- Old format -->
{{ 'nav_home' | translate(current_language or 'en') }}

<!-- New format -->
{{ 'navigation.nav_home' | translate(current_language or 'en') }}
```

## Using Translations in Python Code

```python
from resource_manager import get_translation

# Get a translation
title = get_translation('home.hero_title', 'en')
author_label = get_translation('book_details.book_author', 'fr')

# With placeholders
message = get_translation('search.search_no_results', 'en', query='fantasy')
```

## Resource Manager API

### Main Functions

- `get_translation(key, language='en', **kwargs)` - Get a translation
- `get_available_languages()` - Get all available languages
- `get_language_info(language_code)` - Get language metadata
- `reload_language(language_code)` - Reload a specific language
- `reload_all()` - Reload all languages

###ResourceManager Class

```python
from resource_manager import ResourceManager

# Create a custom resource manager
rm = ResourceManager('/path/to/resources')

# Load a language
rm.load_language('es')

# Get all translations for a language
translations = rm.get_all_translations('es')

# Get a specific translation
title = rm.get_translation('home.hero_title', 'es')
```

## Benefits

1. **Separation of Concerns**: Text content is separated from code
2. **Easy Maintenance**: Edit translations without touching Python code
3. **Better Organization**: Nested keys provide logical grouping
4. **Extensibility**: Easy to add new languages
5. **Fallback Support**: Automatic fallback to English if translation missing
6. **Hot Reloading**: Reload translations without restarting the app
7. **Type Safety**: Better IDE support with structured keys

## Migration from Old System

The old hardcoded translation system in `languages.py` is still available as a fallback. The new system:

1. Automatically discovers available languages from JSON files
2. Falls back to the old system if resource manager is unavailable
3. Maintains backward compatibility with existing code

## Testing

Run the test script to verify the resource manager is working:

```bash
cd webapp
python test_resource_manager.py
```

This will test:
- Language discovery
- Translation loading
- Key resolution
- Fallback behavior
- Language metadata
