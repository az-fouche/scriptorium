# Book Library Parser & Web Explorer

A comprehensive book library indexing and analysis system with genre detection, topic modeling, and a modern web interface for exploring your book collection.

**Entirely vibe-coded in a single week-end so please be indulgent with the code quality. :)**

-> (http://my-scriptorium.fr)[My scriptorium website]

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r config/requirements.txt
```

### 2. Index Your Library
```bash
python scripts/index_library.py --directory data/full_library
```

### 3. Start the Web Application
```bash
python webapp/run_refactored.py
```

The web interface will be available at `http://localhost:5000`

## 📁 Project Structure

```
poubelle_parsing/
├── webapp/                    # Modern Flask web application
│   ├── config.py             # Configuration management
│   ├── models.py             # Database models
│   ├── services.py           # Business logic layer
│   ├── controllers.py        # Route handlers
│   ├── utils.py              # Utility functions
│   ├── extensions.py         # Flask extensions
│   ├── app_refactored.py    # Application factory
│   ├── run_refactored.py    # Web app runner
│   └── templates/            # HTML templates
├── src/                      # Core parsing modules
│   ├── epub_parser.py       # EPUB file parsing
│   ├── genre_detector.py    # Genre classification
│   ├── topic_modeler.py     # Topic modeling
│   └── database.py          # Database operations
├── scripts/                  # Indexing and utility scripts
│   ├── index_library.py     # Main indexing tool
│   ├── regenerate_subset.py # Database subset generation
│   └── tools/               # Utility tools
├── data/                     # Book library data
│   ├── full_library/        # Complete book collection
│   ├── genres/              # Genre definitions
│   └── themes/              # Theme definitions
├── databases/                # SQLite databases
│   ├── books.db             # Main database
│   └── subset_books.db      # Subset for development
├── docs/                     # Documentation
│   ├── QUICK_START.md       # Quick start guide
│   └── README_INDEXER.md    # Indexing documentation
└── config/                   # Configuration files
    └── requirements.txt      # Python dependencies
```

## ✨ Features

### 📚 Book Analysis
- **EPUB Parsing**: Extract metadata and content from EPUB files
- **Genre Detection**: Automatic genre classification using ML and rule-based methods
- **Topic Modeling**: Extract themes and topics from book content
- **Text Analysis**: Analyze text complexity, readability, and language
- **Multi-language Support**: French and English content analysis

### 🌐 Web Interface
- **Modern UI**: Clean, responsive web interface
- **Book Explorer**: Browse and search your entire library
- **Book Details**: Detailed view with metadata, analysis, and recommendations
- **Statistics**: Library overview with charts and metrics
- **Recommendations**: Find similar books based on content analysis
- **Search**: Full-text search across titles, authors, and content

### 🗄️ Data Management
- **SQLite Database**: Efficient storage with indexing
- **Auto-reload**: Database changes are automatically detected
- **Export Capabilities**: Export data in various formats
- **Backup System**: Automatic database backups

## 🛠️ Development

### Architecture
The webapp uses a modern modular architecture:
- **Models**: Database schema and data structures
- **Services**: Business logic and data processing
- **Controllers**: HTTP route handlers
- **Utils**: Helper functions and utilities
- **Extensions**: Flask extensions and middleware

### Running in Development
```bash
# Start with auto-reload
python webapp/run_refactored.py

# Or use Flask development server
export FLASK_DEBUG=True
python webapp/run_refactored.py
```

### Database Management
```bash
# Index new books
python scripts/index_library.py --directory /path/to/books

# Regenerate subset database
python scripts/regenerate_subset.py

# View database statistics
python scripts/index_library.py stats
```

### Regenerating the Webapp Database

To regenerate the webapp database using a different book collection:

1. **Using small_library folder (recommended for development):**
   ```bash
   python scripts/index_library.py --db-path databases/subset_books.db index "data/small_library"
   ```

2. **Using full_library folder (for production):**
   ```bash
   python scripts/index_library.py --db-path databases/books.db index "data/full_library"
   ```

3. **Using a custom directory:**
   ```bash
   python scripts/index_library.py --db-path databases/custom.db index "/path/to/your/books"
   ```

**Note:** The webapp is configured to use `databases/subset_books.db` by default. If you regenerate the main database (`books.db`), you'll need to either:
- Update the webapp configuration to point to the new database, or
- Run `python scripts/regenerate_subset.py` to create a subset from the main database

**Database Statistics:**
```bash
# Check database contents
python scripts/index_library.py --db-path databases/subset_books.db stats
```

## 📖 Documentation

- **Quick Start**: See `docs/QUICK_START.md` for getting started
- **Indexing Guide**: See `docs/README_INDEXER.md` for detailed indexing instructions
- **Webapp Architecture**: See `webapp/README_REFACTORED.md` for webapp documentation

## 🔧 Configuration

The application uses environment variables for configuration:
- `FLASK_DEBUG`: Enable debug mode (default: True)
- `FLASK_HOST`: Host to bind to (default: 0.0.0.0)
- `FLASK_PORT`: Port to bind to (default: 5000)
- `DATABASE_PATH`: Path to SQLite database

## 🎯 Recent Improvements

- **Refactored Webapp**: Modular architecture with clear separation of concerns
- **Improved Performance**: Optimized database queries and caching
- **Better UI**: Enhanced web interface with modern design
- **Clean Codebase**: Removed debug files and organized structure
- **Comprehensive Documentation**: Detailed guides for all components

## 📄 License

This project is for educational and personal use.
