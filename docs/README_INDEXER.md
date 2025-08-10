# Library Indexer

A comprehensive tool for automatically indexing and analyzing large collections of EPUB books. This tool extracts metadata, analyzes content complexity, detects genres, and identifies topics to create a searchable database for your digital library.

## Features

- **Automatic EPUB Processing**: Recursively scans directories for EPUB files
- **Metadata Extraction**: Extracts title, authors, language, publisher, ISBN, etc.
- **Content Analysis**: Analyzes text complexity, reading level, and statistics
- **Genre Detection**: Uses machine learning and rule-based classification
- **Topic Modeling**: Identifies themes and keywords using LDA and NMF
- **Parallel Processing**: Multi-threaded processing for faster indexing
- **Database Storage**: SQLite database for efficient querying
- **Rich CLI Interface**: Beautiful progress bars and statistics
- **Export Capabilities**: Export to JSON for external tools

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Download Language Models** (optional):
   ```bash
   python -m spacy download en_core_web_sm
   python -m spacy download fr_core_news_sm
   ```

3. **Create Logs Directory**:
   ```bash
   mkdir logs
   ```

## Quick Start

### Index a Directory

```bash
# Index all EPUB files in a directory
python index_library.py index /path/to/your/books

# Use specific language detection
python index_library.py --language french index /path/to/your/books

# Use more worker threads for faster processing
python index_library.py --workers 8 index /path/to/your/books
```

### View Statistics

```bash
# Show database statistics
python index_library.py stats
```

### Search Books

```bash
# Search by title, author, or content
python index_library.py search "science fiction"
python index_library.py search "Stephen King"
```

### Export Data

```bash
# Export to JSON
python index_library.py export --output-file my_library.json
```

## Command Line Options

### Global Options

- `--db-path`: Database file path (default: `books.db`)
- `--language`: Language for analysis (`auto`, `english`, `french`)
- `--workers`: Number of worker threads (default: 4)

### Index Command

- `--skip-existing`: Skip files already in database (default: true)

### Examples

```bash
# Basic indexing
python index_library.py index /books

# Advanced indexing with custom settings
python index_library.py \
  --db-path my_library.db \
  --language auto \
  --workers 8 \
  index /books \
  --skip-existing

# View statistics after indexing
python index_library.py --db-path my_library.db stats
```

## Configuration

The tool uses a `config.json` file for default settings. You can modify this file to customize:

- Database settings
- Indexing parameters
- Analysis options
- Logging configuration
- Output format

## Database Schema

The tool creates a SQLite database with the following main tables:

### Books Table
- Basic metadata (title, authors, language, etc.)
- File information (path, size, etc.)
- Content statistics (word count, complexity, etc.)
- Analysis results (genres, topics, keywords)

### Chapters Table
- Chapter-level information
- Content and word counts per chapter

### Analysis Results Table
- Detailed analysis results
- Model outputs and confidence scores

## Analysis Features

### Text Analysis
- **Complexity Analysis**: Flesch-Kincaid readability scores
- **Reading Level**: Elementary, Intermediate, Advanced
- **Statistics**: Word count, sentence length, vocabulary diversity

### Genre Detection
- **Primary Genre**: Most likely genre with confidence score
- **Secondary Genres**: Additional genres with lower confidence
- **Supported Genres**: Fiction, Non-Fiction, Science Fiction, Fantasy, Mystery, Romance, Thriller, Horror, Historical Fiction, Biography, Autobiography, Memoir, Self-Help, Business, Philosophy, Religion, Science, Technology, History, Politics, Poetry, Drama, Comedy, Adventure, Crime, War, Western, Young Adult, Children, Educational, Reference

### Topic Modeling
- **LDA Topics**: Latent Dirichlet Allocation for theme discovery
- **NMF Topics**: Non-negative Matrix Factorization
- **Keywords**: TF-IDF based keyword extraction
- **Theme Clustering**: Similar topic identification

## Performance

### Processing Speed
- **Typical Speed**: 10-50 books per minute (depends on file size and content)
- **Parallel Processing**: Configurable number of worker threads
- **Memory Usage**: ~50-200MB per worker thread

### Optimization Tips
1. **Increase Workers**: Use `--workers 8` for faster processing
2. **SSD Storage**: Store database on SSD for better performance
3. **Sufficient RAM**: Ensure adequate memory for parallel processing
4. **Skip Existing**: Use `--skip-existing` to avoid reprocessing

## Troubleshooting

### Common Issues

1. **Memory Errors**: Reduce number of workers with `--workers 2`
2. **Slow Processing**: Check disk I/O and CPU usage
3. **Failed Files**: Check logs in `logs/indexing.log`
4. **Database Errors**: Ensure write permissions to database directory

### Log Files
- **Main Log**: `logs/indexing.log`
- **Error Details**: Check console output for specific file errors
- **Database Logs**: SQLite logs in database file

### Recovery
- **Resume Indexing**: Tool automatically skips existing files
- **Database Backup**: Automatic backups every 100 books
- **Export Safety**: Export data before major operations

## Integration

### Frontend Development
The indexed database can be used to build:

- **Web Applications**: Flask/Django with SQLite
- **Desktop Apps**: Tkinter, PyQt, or Electron
- **API Services**: FastAPI or Flask REST API
- **Search Interfaces**: Full-text search with SQLite FTS

### Data Export
```python
# Example: Load exported data
import json
with open('library_index_20231201_143022.json', 'r') as f:
    library_data = json.load(f)

books = library_data['books']
print(f"Loaded {len(books)} books")
```

### API Integration
```python
# Example: Query database directly
from src.database import BookDatabase

db = BookDatabase('books.db')
books = db.search_books('science fiction')
for book in books:
    print(f"{book['title']} by {', '.join(book['authors'])}")
```

## Advanced Usage

### Custom Analysis
```python
from index_library import LibraryIndexer

indexer = LibraryIndexer(db_path='custom.db', language='english')
stats = indexer.index_directory('/path/to/books')
print(f"Processed {stats.successful_files} books successfully")
```

### Batch Processing
```bash
# Process multiple directories
for dir in /books/*/; do
    python index_library.py index "$dir"
done
```

### Scheduled Indexing
```bash
# Add to crontab for automatic updates
0 2 * * * cd /path/to/library && python index_library.py index /books
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the logs in `logs/indexing.log`
2. Review the troubleshooting section
3. Open an issue on GitHub with detailed error information
