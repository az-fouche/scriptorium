# French Mode for Library Explorer

## Overview

The Library Explorer webapp now supports a French mode with a language toggle feature. Users can switch between English and French interfaces seamlessly.

## Features

### Language Toggle
- **Location**: Top navigation bar (globe icon)
- **Functionality**: Dropdown menu with language options
- **Languages**: English (🇺🇸) and French (🇫🇷)
- **Persistence**: Language preference is saved in session

### Translated Content
- **Navigation**: All navigation items are translated
- **Page Titles**: Dynamic page titles in selected language
- **UI Elements**: Buttons, labels, and form placeholders
- **Statistics**: Numbers and labels in appropriate language
- **Search**: Search functionality with translated placeholders
- **Book Information**: Author, language, and metadata labels

### Language-Specific Formatting
- **Numbers**: French uses space as thousands separator (1 234 vs 1,234)
- **File Sizes**: French uses French abbreviations (Ko, Mo, Go vs KB, MB, GB)
- **Reading Time**: Time units translated (minutes, heures, jours)
- **Dates**: Future enhancement for date formatting

## Technical Implementation

### Files Added/Modified

#### New Files
- `languages.py` - Language configuration and translation system
- `test_language.py` - Test script for language functionality

#### Modified Files
- `app_refactored.py` - Added session support and template filters
- `controllers.py` - Added language detection and route support
- `templates/base.html` - Added language toggle and translations
- `templates/index.html` - Updated with translation support
- `templates/books.html` - Updated with translation support
- `templates/search.html` - Updated with translation support

### Key Functions

#### Language Detection
```python
def get_language(request):
    """Get the current language from request or session"""
    # Check URL parameters first
    lang = request.args.get('lang')
    if lang and lang in LANGUAGES:
        return lang
    
    # Check session
    if hasattr(request, 'session'):
        lang = request.session.get('language')
        if lang and lang in LANGUAGES:
            return lang
    
    # Default to English
    return DEFAULT_LANGUAGE
```

#### Translation System
```python
def get_translation(key, language=None, **kwargs):
    """Get a translation for a given key and language"""
    if language is None:
        language = DEFAULT_LANGUAGE
    
    translation = TRANSLATIONS[language].get(key, key)
    
    # Replace placeholders with kwargs
    for k, v in kwargs.items():
        translation = translation.replace(f'{{{{{k}}}}}', str(v))
    
    return translation
```

#### Template Filters
- `translate` - Get translation for a key
- `format_number` - Format numbers according to language
- `format_file_size` - Format file sizes with language-appropriate units
- `format_reading_time` - Format reading time in appropriate language

### Routes

#### Language Switching
```
GET /language/<language_code>
```
- Switches the current language
- Saves preference in session
- Redirects back to previous page

#### Updated Routes
All existing routes now include language context:
- `index()` - Home page with language support
- `books()` - Books listing with language support
- `search()` - Search page with language support
- `book_detail()` - Book details with language support
- `stats()` - Statistics page with language support

## Usage

### For Users
1. **Switch Language**: Click the globe icon in the navigation bar
2. **Select Language**: Choose between English and French
3. **Browse**: All content will be displayed in the selected language
4. **Search**: Search functionality works in both languages
5. **Navigation**: All navigation elements are translated

### For Developers
1. **Add New Translations**: Add entries to `TRANSLATIONS` in `languages.py`
2. **Use Template Filters**: Use `{{ 'key' | translate(language) }}` in templates
3. **Add Language Support**: Pass `current_language` and `app_languages` to templates
4. **Test**: Run `python test_language.py` to verify functionality

## Translation Keys

### Navigation
- `nav_home` - Home
- `nav_books` - Books
- `nav_search` - Search
- `nav_stats` - Stats
- `nav_language` - Language

### Home Page
- `hero_title` - Library Explorer
- `hero_subtitle` - Subtitle text
- `hero_browse_books` - Browse Books
- `hero_search_books` - Search Books
- `hero_view_stats` - View Statistics

### Statistics
- `stats_total_books` - Total Books
- `stats_total_size` - Total Size
- `stats_unique_authors` - Unique Authors
- `stats_recent_books` - Recently Added

### Books Page
- `books_title` - All Books
- `books_search_placeholder` - Search placeholder
- `books_filter_language` - Filter by Language
- `books_filter_author` - Filter by Author
- `books_apply_filters` - Apply Filters
- `books_clear_filters` - Clear Filters
- `books_no_results` - No books found message

### Search Page
- `search_title` - Search Books
- `search_placeholder` - Search placeholder
- `search_results` - Search Results
- `search_no_results` - No results found message
- `search_try_different` - Try different keywords message

### Book Details
- `book_details` - Book Details
- `book_author` - Author
- `book_language` - Language
- `book_words` - Words
- `book_size` - Size
- `book_genres` - Genres
- `book_themes` - Themes
- `book_reading_time` - Reading Time
- `book_description` - Description
- `book_recommendations` - Similar Books

### Common Actions
- `loading` - Loading...
- `error` - Error
- `success` - Success
- `view` - View
- `search` - Search
- `filter` - Filter
- `apply` - Apply
- `clear` - Clear
- `cancel` - Cancel
- `save` - Save
- `edit` - Edit
- `delete` - Delete

## Future Enhancements

### Planned Features
1. **More Languages**: Add support for additional languages
2. **Date Formatting**: Language-specific date and time formatting
3. **Currency Formatting**: For any future e-commerce features
4. **RTL Support**: Right-to-left language support
5. **Dynamic Content**: Translate book titles and descriptions
6. **User Preferences**: Save language preference in user accounts

### Technical Improvements
1. **Translation Management**: Web interface for managing translations
2. **Auto-translation**: Integration with translation APIs
3. **Fallback System**: Better fallback for missing translations
4. **Performance**: Caching for frequently used translations
5. **Testing**: More comprehensive test coverage

## Testing

Run the language test suite:
```bash
cd webapp
python test_language.py
```

This will verify:
- Basic translation functionality
- Language information functions
- Number and formatting functions
- Placeholder replacement

## Contributing

To add new translations:
1. Add new keys to `TRANSLATIONS` in `languages.py`
2. Provide translations for both English and French
3. Update templates to use the new keys
4. Add tests to `test_language.py`
5. Test the functionality manually

## Notes

- The language toggle is prominently placed in the navigation bar
- Language preference persists across sessions
- All major UI elements are translated
- Number formatting follows language conventions
- The system gracefully falls back to English for missing translations
