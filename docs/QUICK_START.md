# Quick Start Guide - Library Indexer

## 🚀 Get Started in 5 Minutes

### 1. Prerequisites
- Python 3.7 or higher
- Your EPUB books in a directory

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create Logs Directory
```bash
mkdir logs
```

### 4. Index Your Books

#### Option A: Command Line (Recommended)
```bash
# Index all EPUB files in your books directory
python index_library.py index /path/to/your/books

# Example with your data directory
python index_library.py index data
```

#### Option B: Interactive Scripts
- **Windows**: Double-click `index_books.bat`
- **Linux/Mac**: Run `./index_books.sh`

### 5. View Results
```bash
# Show statistics
python index_library.py stats

# Search books
python index_library.py search "science fiction"

# Export to JSON
python index_library.py export
```

## 📊 What You Get

After indexing, your database will contain:

- **Metadata**: Title, authors, language, publisher, ISBN
- **Content Analysis**: Word count, complexity, reading level
- **Genre Detection**: Primary and secondary genres with confidence scores
- **Topic Modeling**: Themes and keywords extracted from content
- **Search Capability**: Full-text search across all books

## 🔧 Advanced Usage

### Custom Settings
```bash
# Use more worker threads for faster processing
python index_library.py --workers 8 index data

# Specify language detection
python index_library.py --language french index data

# Use custom database
python index_library.py --db-path my_library.db index data
```

### Batch Processing
```bash
# Process multiple directories
for dir in /books/*/; do
    python index_library.py index "$dir"
done
```

### Programmatic Usage
```python
from index_library import LibraryIndexer

indexer = LibraryIndexer(db_path='my_library.db')
stats = indexer.index_directory('/path/to/books')
print(f"Indexed {stats.successful_files} books")
```

## 🧪 Testing

Run the test suite to verify everything works:
```bash
python test_indexing.py
```

## 📁 File Structure

```
poubelle_parsing/
├── index_library.py          # Main indexing tool
├── config.json               # Configuration file
├── books.db                  # SQLite database (created after indexing)
├── data/                     # Your EPUB files
│   ├── Author Name/
│   │   └── book.epub
│   └── ...
├── logs/                     # Log files
├── models/                   # ML models (created automatically)
└── visualizations/           # Generated charts
```

## 🎯 Next Steps

1. **Index your library**: `python index_library.py index data`
2. **Explore statistics**: `python index_library.py stats`
3. **Search your books**: `python index_library.py search "your query"`
4. **Export data**: `python index_library.py export`
5. **Build a frontend**: Use the exported JSON or query the database directly

## 🆘 Troubleshooting

### Common Issues

1. **"No module named 'click'"**
   ```bash
   pip install click rich
   ```

2. **"No EPUB files found"**
   - Check that your directory contains `.epub` files
   - Ensure the path is correct

3. **Memory errors**
   ```bash
   python index_library.py --workers 2 index data
   ```

4. **Slow processing**
   - Use SSD storage for database
   - Increase worker threads: `--workers 8`

### Getting Help

- Check logs in `logs/indexing.log`
- Run tests: `python test_indexing.py`
- Review the full documentation in `README_INDEXER.md`

## 🎉 Success!

Once indexing is complete, you'll have:
- A searchable database of your entire library
- Detailed analysis of each book
- Export capabilities for building frontends
- Foundation for advanced library management

Ready to build your interactive library explorer! 🚀
