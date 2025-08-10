#!/usr/bin/env python3
"""
Library Indexer - Comprehensive EPUB Library Indexing Tool

This tool automatically indexes entire directories of EPUB files, extracting
metadata, analyzing content, detecting genres, and identifying topics.
It builds a searchable database for interactive exploration.
"""

import os
import sys
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from epub_parser import EpubParser
from text_analyzer import TextAnalyzer
from topic_modeler import TopicModeler
from database import BookDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/indexing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Quiet noisy sub-loggers on stdout while keeping file logs
for noisy_logger in [
    'database',
    'text_analyzer',
    'topic_modeler',
    'epub_parser',
    'httpx',
    'urllib3',
]:
    try:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    except Exception:
        pass

# Demote console StreamHandler to WARNING so progress bar stays stable
try:
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        if isinstance(h, logging.StreamHandler):
            h.setLevel(logging.WARNING)
except Exception:
    pass

# Initialize Rich console
console = Console()

# Default paths aligned with webapp configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / 'webapp' / 'databases' / 'books.db'


@dataclass
class IndexingStats:
    """Statistics for indexing process"""
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    deferred_files: int = 0
    total_size: int = 0
    start_time: float = 0
    end_time: float = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.processed_files == 0:
            return 0.0
        return (self.successful_files / self.processed_files) * 100
    
    @property
    def processing_time(self) -> float:
        """Calculate total processing time"""
        return self.end_time - self.start_time
    
    @property
    def files_per_minute(self) -> float:
        """Calculate processing speed"""
        if self.processing_time == 0:
            return 0.0
        return (self.processed_files / self.processing_time) * 60


class LibraryIndexer:
    """Comprehensive library indexing tool"""
    
    def __init__(self, db_path: str = "books.db", language: str = 'auto', max_workers: int = 4, llm_api_key: Optional[str] = None, llm_model: str = 'claude-3-haiku-20240307'):
        self.db_path = db_path
        self.language = language
        self.max_workers = max_workers
        
        # Initialize components
        self.parser = EpubParser()
        self.text_analyzer = TextAnalyzer(language=language)
        self.genre_detector = None  # Removed: legacy genre detection
        self.topic_modeler = TopicModeler(language=language, llm_api_key=llm_api_key, llm_model=llm_model)
        self.database = BookDatabase(db_path)

        # Reduce per-book log spam from submodules (redundant safeguard)
        for noisy in ['database', 'text_analyzer', 'topic_modeler', 'epub_parser', 'httpx', 'urllib3']:
            try:
                logging.getLogger(noisy).setLevel(logging.WARNING)
            except Exception:
                pass
        
        # Statistics
        self.stats = IndexingStats()
        
        # Supported file extensions
        self.supported_extensions = {'.epub'}
    
    def find_epub_files(self, directory: str) -> List[str]:
        """Find all EPUB files in directory and subdirectories"""
        epub_files = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        console.print(f"[bold blue]Scanning directory: {directory}[/bold blue]")
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in self.supported_extensions:
                    epub_files.append(str(file_path))
        
        console.print(f"[green]Found {len(epub_files)} EPUB files[/green]")
        return epub_files
    
    def extract_author_from_path(self, file_path: str) -> Optional[str]:
        """Extract author name from file path in clean structure format"""
        try:
            path = Path(file_path)
            # In clean structure: /path/to/library/AUTHOR, Name/book.epub
            # Author directory is the parent of the book file
            author_dir = path.parent.name
            
            # Handle special cases
            if author_dir in ['Unknown Author', 'Collectif', 'Anonyme', 'Anthologie']:
                return author_dir
            
            # Clean up author name (remove any extra formatting)
            return author_dir.strip()
            
        except Exception as e:
            logger.warning(f"Could not extract author from path {file_path}: {str(e)}")
            return None
    
    def _detect_clean_structure(self, directory: str) -> bool:
        """Detect if the directory uses the clean structure format"""
        try:
            directory_path = Path(directory)
            
            # Look for immediate subdirectories that look like author names
            # Clean structure has author directories directly under the root
            subdirs = [d for d in directory_path.iterdir() if d.is_dir()]
            
            if not subdirs:
                return False
            
            # Check if subdirectories contain EPUB files directly
            # and if the directory names look like author names
            clean_structure_indicators = 0
            
            for subdir in subdirs[:10]:  # Check first 10 directories
                # Check if directory contains EPUB files
                epub_files = list(subdir.glob("*.epub"))
                if epub_files:
                    clean_structure_indicators += 1
                
                # Check if directory name looks like an author name (contains comma or is a known pattern)
                dir_name = subdir.name
                if (',' in dir_name or 
                    dir_name in ['Unknown Author', 'Collectif', 'Anonyme', 'Anthologie'] or
                    len(dir_name.split()) >= 2):
                    clean_structure_indicators += 1
            
            # If most directories show clean structure indicators, assume it's clean structure
            return clean_structure_indicators >= len(subdirs[:10]) * 0.7
            
        except Exception as e:
            logger.warning(f"Could not detect structure type for {directory}: {str(e)}")
            return False
    
    def analyze_single_book(self, file_path: str) -> Optional[Dict]:
        """Analyze a single book and return structured data"""
        try:
            # Parse book
            metadata, content, cover = self.parser.parse_book(file_path)
            
            # Skip if no content
            if not content.full_text.strip():
                logger.warning(f"No content found in {file_path}")
                return None
            
            # Extract author from directory structure (clean format)
            directory_author = self.extract_author_from_path(file_path)

            # Prefer EPUB metadata authors. Only fall back to directory author
            # when metadata has no authors.
            authors = metadata.authors if metadata.authors else []
            if not authors and directory_author:
                authors = [directory_author]
            
            # Handle very long texts to avoid memory issues but keep enough signal
            # Sample across beginning, middle, and end to reduce front-matter bias
            def sample_text_windows(text: str, max_chars: int = 160_000) -> str:
                if not text:
                    return ""
                if len(text) <= max_chars:
                    return text
                window = max_chars // 3
                half_window = window // 2
                start_seg = text[:window]
                mid = len(text) // 2
                mid_start = max(0, mid - half_window)
                mid_end = min(len(text), mid + half_window)
                mid_seg = text[mid_start:mid_end]
                end_seg = text[-window:]
                return "\n\n".join([start_seg, mid_seg, end_seg])

            text_for_analysis = sample_text_windows(content.full_text)
            
            # Text analysis
            try:
                text_analysis = self.text_analyzer.analyze_text_complexity(text_for_analysis)
            except Exception as e:
                logger.warning(f"Text analysis failed for {file_path}: {str(e)}")
                text_analysis = {'complexity_level': 'Unknown', 'reading_level': 'Unknown'}
            
            # Genres removed: do not produce or store legacy v1 genres
            genre_analysis = {
                'primary_genre': '',
                'primary_confidence': 0.0,
                'secondary_genres': [],
                'secondary_confidences': []
            }
            
            # Topic modeling and tags (unified)
            try:
                topic_analysis = self.topic_modeler.extract_book_topics(text_for_analysis, {
                    'title': metadata.title,
                    'authors': authors,
                    'description': metadata.description,
                    'subjects': metadata.subjects
                })
            except Exception as e:
                logger.warning(f"Topic modeling failed for {file_path}: {str(e)}")
                topic_analysis = {
                    'main_themes': [],
                    'themes_with_scores': [],
                    'primary_topic': 'Unknown',
                    'primary_confidence': 0.0,
                    'secondary_topics': [],
                    'secondary_confidences': [],
                    'keywords': [],
                    'tags': [],
                    'tags_primary': 'Unknown',
                    'tags_secondary': [],
                    'tags_detailed': []
                }
            
            # Prepare book data
            book_data = {
                'id': metadata.title,
                'title': metadata.title,
                'authors': authors,
                'directory_author': directory_author,  # Store the author from directory structure
                'language': metadata.language,
                'detected_language': self.text_analyzer.detected_language,
                'publisher': metadata.publisher,
                'publication_date': metadata.publication_date,
                'isbn': metadata.isbn,
                'description': metadata.description,
                'subjects': metadata.subjects,
                'rights': metadata.rights,
                'identifier': metadata.identifier,
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'word_count': content.word_count,
                'character_count': content.character_count,
                'paragraph_count': content.paragraph_count,
                'sentence_count': content.sentence_count,
                'average_sentence_length': content.average_sentence_length,
                'average_word_length': content.average_word_length,
                'primary_genre': genre_analysis.get('primary_genre'),
                'primary_confidence': genre_analysis.get('primary_confidence'),
                'secondary_genres': genre_analysis.get('secondary_genres', []),
                'secondary_confidences': genre_analysis.get('secondary_confidences', []),
                'complexity_level': text_analysis.get('complexity_level'),
                'reading_level': text_analysis.get('reading_level'),
                # Unified topics: keep list of tags for quick filtering if desired
                'topics': topic_analysis.get('tags') or [],
                # Persist all tag scores to avoid recomputation later
                'tag_scores': [
                    {'tag': t, 'score': float(s)} for (t, s) in (topic_analysis.get('tags_detailed') or [])
                ],
                # Store EPUB-extracted keywords
                'keywords': topic_analysis.get('keywords', []),
                'chapters': content.chapters,
                'cover_data': cover.base64_data if cover else None,
                'cover_mime_type': cover.mime_type if cover else None,
                'cover_file_name': cover.file_name if cover else None
            }
            
            return book_data
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {str(e)}")
            return None
    
    def process_file(self, file_path: str) -> Tuple[str, Optional[Dict]]:
        """Process a single file and return result"""
        try:
            # Skip relabeling: if existing record has tag scores or topics, reuse existing
            try:
                existing = self.database.get_book_by_path(file_path)
            except Exception:
                existing = None
            if existing:
                has_tags = bool(existing.get('tag_scores')) or bool(existing.get('topics'))
                if has_tags:
                    return file_path, existing

            book_data = self.analyze_single_book(file_path)
            return file_path, book_data
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return file_path, None
    
    def index_directory(self, directory: str, skip_existing: bool = True, max_files: Optional[int] = None) -> IndexingStats:
        """Index all EPUB files in a directory"""
        self.stats = IndexingStats()
        self.stats.start_time = time.time()
        
        # Detect if this is a clean structure
        is_clean_structure = self._detect_clean_structure(directory)
        if is_clean_structure:
            console.print("[bold green]Detected clean library structure (author directories)[/bold green]")
        else:
            console.print("[bold yellow]Detected legacy library structure[/bold yellow]")
        
        # Find all EPUB files
        epub_files = self.find_epub_files(directory)
        self.stats.total_files = len(epub_files)
        
        if not epub_files:
            console.print("[yellow]No EPUB files found in directory[/yellow]")
            self.stats.end_time = time.time()
            return self.stats
        
        # Check for existing books in database
        existing_files = set()
        skipped_existing_count = 0
        if skip_existing:
            existing_books = self.database.get_all_books()
            existing_files = {book['file_path'] for book in existing_books if book.get('file_path')}
            console.print(f"[blue]Found {len(existing_files)} existing books in database[/blue]")

        # Filter out already-indexed files first
        pre_max_files = [f for f in epub_files if f not in existing_files]
        skipped_existing_count = len(epub_files) - len(pre_max_files)

        # Apply optional limit (remaining files deferred, not 'skipped')
        if isinstance(max_files, int) and max_files > 0:
            files_to_process = pre_max_files[:max_files]
            self.stats.deferred_files = max(0, len(pre_max_files) - len(files_to_process))
        else:
            files_to_process = pre_max_files
            self.stats.deferred_files = 0

        # Initialize skipped with existing-only; runtime may add more (e.g., rate limited)
        self.stats.skipped_files = skipped_existing_count
        
        if not files_to_process:
            console.print("[green]All files already indexed![/green]")
            self.stats.end_time = time.time()
            return self.stats
        
        console.print(f"[bold green]Processing {len(files_to_process)} new files...[/bold green]")
        
        # Show structure-specific information
        if is_clean_structure:
            authors_found = len(set(self.extract_author_from_path(f) for f in files_to_process if self.extract_author_from_path(f)))
            console.print(f"[blue]Found books from approximately {authors_found} authors[/blue]")
        
        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
            transient=False,
            refresh_per_second=10,
        ) as progress:
            
            task = progress.add_task("Indexing books... ok: 0 fail: 0 skip: 0", total=len(files_to_process))
            
            # Process files in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self.process_file, file_path): file_path 
                    for file_path in files_to_process
                }
                
                # Process completed tasks
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    
                    try:
                        file_path, book_data = future.result()
                        
                        if book_data:
                            # If LLM was rate limited and produced no tags, skip saving (to retry later)
                            try:
                                llm = getattr(self.topic_modeler, 'llm_classifier', None)
                                rate_limited = bool(getattr(llm, 'last_rate_limited', False)) if llm else False
                            except Exception:
                                rate_limited = False
                            if rate_limited:
                                self.stats.skipped_files += 1
                                # Do not print per-file; keep progress stable
                                continue
                            # Save to database
                            success = self.database.add_book(book_data)
                            if success:
                                self.stats.successful_files += 1
                            else:
                                self.stats.failed_files += 1
                        else:
                            self.stats.failed_files += 1
                        
                    except Exception as e:
                        self.stats.failed_files += 1
                        console.print(f"[red]x[/red] {Path(file_path).name} (error: {str(e)})")
                    
                    self.stats.processed_files += 1
                    # Update task line with running counters and last file basename
                    last_name = Path(file_path).name
                    progress.update(
                        task,
                        advance=1,
                        description=f"Indexing books... ok: {self.stats.successful_files} fail: {self.stats.failed_files} skip: {self.stats.skipped_files} last: {last_name[:40]}"
                    )
        
        self.stats.end_time = time.time()
        return self.stats
    
    def print_statistics(self):
        """Print indexing statistics"""
        stats = self.stats
        
        console.print("\n[bold blue]Indexing Statistics[/bold blue]")
        console.print("=" * 50)
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total files found", str(stats.total_files))
        table.add_row("Files processed", str(stats.processed_files))
        table.add_row("Files skipped (existing/rate-limited)", str(stats.skipped_files))
        if stats.deferred_files:
            table.add_row("Files deferred (max-files)", str(stats.deferred_files))
        table.add_row("Successful", str(stats.successful_files))
        table.add_row("Failed", str(stats.failed_files))
        table.add_row("Success rate", f"{stats.success_rate:.1f}%")
        table.add_row("Processing time", f"{stats.processing_time:.1f} seconds")
        table.add_row("Speed", f"{stats.files_per_minute:.1f} files/minute")
        
        console.print(table)
        
        if stats.failed_files > 0:
            console.print(f"\n[yellow]Warning: {stats.failed_files} files failed to process. Check logs for details.[/yellow]")
    
    def get_database_statistics(self) -> Dict:
        """Get statistics about the indexed database"""
        books = self.database.get_all_books()
        
        if not books:
            return {"total_books": 0}
        
        # Calculate statistics
        total_size = sum(book.get('file_size', 0) for book in books)
        total_words = sum(book.get('word_count', 0) for book in books)
        
        # Genre distribution
        genres = {}
        for book in books:
            genre = book.get('primary_genre', 'Unknown')
            genres[genre] = genres.get(genre, 0) + 1
        
        # Language distribution
        languages = {}
        for book in books:
            lang = book.get('language', 'Unknown')
            languages[lang] = languages.get(lang, 0) + 1
        
        # Author distribution
        authors = {}
        for book in books:
            for author in book.get('authors', []):
                authors[author] = authors.get(author, 0) + 1
        
        return {
            "total_books": len(books),
            "total_size_mb": total_size / (1024 * 1024),
            "total_words": total_words,
            "average_words_per_book": total_words / len(books) if books else 0,
            "genres": genres,
            "languages": languages,
            "top_authors": sorted(authors.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def export_index(self, output_file: str = None):
        """Export the index to JSON format"""
        books = self.database.get_all_books()
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"library_index_{timestamp}.json"
        
        # Prepare data for export
        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_books": len(books),
            "books": books
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]Index exported to: {output_file}[/green]")


@click.group()
@click.option('--db-path', default=str(DEFAULT_DB_PATH), help='Database file path')
@click.option('--language', '-l', default='auto', help='Language for analysis (auto/english/french)')
@click.option('--workers', '-w', default=4, help='Number of worker threads')
@click.option('--api-key', envvar='ANTHROPIC_API_KEY', default=None, help='Anthropic API key for LLM-based tagging')
@click.option('--llm-model', default='claude-3-haiku-20240307', help='LLM model name for tagging')
@click.pass_context
def cli(ctx, db_path, language, workers, api_key, llm_model):
    """Library Indexer - Index your EPUB collection"""
    ctx.ensure_object(dict)
    ctx.obj['indexer'] = LibraryIndexer(db_path, language, workers, llm_api_key=api_key, llm_model=llm_model)


@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--skip-existing/--no-skip-existing', default=True, help='Skip files already in database')
@click.option('--max-files', type=int, default=None, help='Limit number of new files to process')
@click.pass_context
def index(ctx, directory, skip_existing, max_files):
    """Index all EPUB files in a directory"""
    indexer = ctx.obj['indexer']
    
    console.print(Panel.fit(
        f"[bold blue]Library Indexer[/bold blue]\n"
        f"Directory: {directory}\n"
        f"Database: {indexer.db_path}\n"
        f"Language: {indexer.language}\n"
        f"Workers: {indexer.max_workers}\n"
        f"LLM model: {indexer.topic_modeler.llm_classifier.model if getattr(indexer.topic_modeler, 'llm_classifier', None) else 'disabled'}\n"
        f"Max files: {max_files if max_files else 'All'}",
        title="Configuration"
    ))
    
    try:
        # Index the directory
        stats = indexer.index_directory(directory, skip_existing, max_files)
        
        # Print statistics
        indexer.print_statistics()
        
        # Show database statistics
        db_stats = indexer.get_database_statistics()
        console.print(f"\n[bold green]Database now contains {db_stats['total_books']} books[/bold green]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show database statistics"""
    indexer = ctx.obj['indexer']
    
    db_stats = indexer.get_database_statistics()
    
    if db_stats['total_books'] == 0:
        console.print(Panel.fit(
            "[yellow]No books found in database[/yellow]",
            title="Library Overview"
        ))
        return
    
    console.print(Panel.fit(
        f"[bold blue]Database Statistics[/bold blue]\n"
        f"Total books: {db_stats['total_books']}\n"
        f"Total size: {db_stats.get('total_size_mb', 0):.1f} MB\n"
        f"Total words: {db_stats.get('total_words', 0):,}\n"
        f"Average words per book: {db_stats.get('average_words_per_book', 0):.0f}",
        title="Library Overview"
    ))
    
    if db_stats['genres']:
        console.print("\n[bold]Genre Distribution:[/bold]")
        genre_table = Table(show_header=True, header_style="bold magenta")
        genre_table.add_column("Genre", style="cyan")
        genre_table.add_column("Count", style="green")
        
        for genre, count in sorted(db_stats['genres'].items(), key=lambda x: x[1], reverse=True):
            genre_table.add_row(genre, str(count))
        
        console.print(genre_table)
    
    if db_stats['top_authors']:
        console.print("\n[bold]Top Authors:[/bold]")
        author_table = Table(show_header=True, header_style="bold magenta")
        author_table.add_column("Author", style="cyan")
        author_table.add_column("Books", style="green")
        
        for author, count in db_stats['top_authors']:
            author_table.add_row(author, str(count))
        
        console.print(author_table)


@cli.command()
@click.option('--output-file', help='Output file path')
@click.pass_context
def export(ctx, output_file):
    """Export the index to JSON format"""
    indexer = ctx.obj['indexer']
    
    try:
        indexer.export_index(output_file)
    except Exception as e:
        console.print(f"[red]Error exporting index: {str(e)}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.pass_context
def search(ctx, query):
    """Search books in the database"""
    indexer = ctx.obj['indexer']
    
    try:
        results = indexer.database.search_books(query)
        
        if not results:
            console.print(f"[yellow]No books found matching '{query}'[/yellow]")
            return
        
        console.print(f"\n[bold green]Found {len(results)} books matching '{query}':[/bold green]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Title", style="cyan")
        table.add_column("Author(s)", style="green")
        table.add_column("Genre", style="yellow")
        table.add_column("Words", style="blue")
        
        for book in results[:20]:  # Limit to first 20 results
            authors = ", ".join(book.get('authors', []))
            table.add_row(
                book.get('title', 'Unknown')[:50],
                authors[:30],
                book.get('primary_genre', 'Unknown'),
                str(book.get('word_count', 0))
            )
        
        console.print(table)
        
        if len(results) > 20:
            console.print(f"\n[yellow]... and {len(results) - 20} more results[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error searching: {str(e)}[/red]")


if __name__ == '__main__':
    cli()
