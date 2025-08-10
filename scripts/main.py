#!/usr/bin/env python3
"""
Ebook Collection Analyzer - Main CLI Interface

A comprehensive tool for analyzing and exploring large collections of ebooks.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from epub_parser import EpubParser
from text_analyzer import TextAnalyzer
from genre_detector import GenreDetector
from topic_modeler import TopicModeler
from recommender import BookRecommender
from database import BookDatabase
from visualizer import BookVisualizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console()


class EbookAnalyzer:
    """Main analyzer class that coordinates all components"""
    
    def __init__(self, db_path: str = "books.db", language: str = 'auto'):
        self.db_path = db_path
        self.language = language
        self.parser = EpubParser()
        self.text_analyzer = TextAnalyzer(language=language)
        self.genre_detector = GenreDetector()
        self.topic_modeler = TopicModeler(language=language)
        self.recommender = BookRecommender()
        self.database = BookDatabase(db_path)
        self.visualizer = BookVisualizer()
    
    def analyze_single_book(self, file_path: str) -> Dict:
        """Analyze a single book"""
        try:
            with console.status(f"[bold green]Analyzing {Path(file_path).name}..."):
                # Parse book
                metadata, content = self.parser.parse_book(file_path)
                
                # Text analysis
                text_analysis = self.text_analyzer.analyze_text_complexity(content.full_text)
                
                # Genre detection
                genre_analysis = self.genre_detector.classify_book(content.full_text, {
                    'title': metadata.title,
                    'subjects': metadata.subjects
                })
                
                # Topic modeling
                topic_analysis = self.topic_modeler.extract_book_topics(content.full_text, {
                    'title': metadata.title,
                    'authors': metadata.authors
                })
                
                # Prepare book data
                book_data = {
                    'id': metadata.title,
                    'title': metadata.title,
                    'authors': metadata.authors,
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
                    'full_text': content.full_text,
                    'chapters': content.chapters,
                    'word_count': content.word_count,
                    'character_count': content.character_count,
                    'paragraph_count': content.paragraph_count,
                    'sentence_count': content.sentence_count,
                    'average_sentence_length': content.average_sentence_length,
                    'average_word_length': content.average_word_length,
                    'primary_genre': genre_analysis.get('primary_genre', 'Unknown'),
                    'primary_confidence': genre_analysis.get('primary_confidence', 0.0),
                    'secondary_genres': genre_analysis.get('secondary_genres', []),
                    'secondary_confidences': genre_analysis.get('secondary_confidences', []),
                    'complexity_level': text_analysis.get('complexity_level', 'Unknown'),
                    'reading_level': self.text_analyzer.get_reading_level(content.full_text),
                    'overall_complexity_score': text_analysis.get('overall_complexity_score', 0.0),
                    'topics': topic_analysis,
                    'keywords': topic_analysis.get('keywords', [])
                }
                
                # Save to database
                self.database.add_book(book_data)
                
                return book_data
                
        except Exception as e:
            logger.error(f"Error analyzing book {file_path}: {e}")
            raise
    
    def analyze_collection(self, directory: str) -> List[Dict]:
        """Analyze all books in a directory"""
        try:
            directory_path = Path(directory)
            if not directory_path.exists():
                raise ValueError(f"Directory does not exist: {directory}")
            
            # Find all EPUB files
            epub_files = list(directory_path.rglob("*.epub"))
            
            if not epub_files:
                console.print(f"[yellow]No EPUB files found in {directory}[/yellow]")
                return []
            
            console.print(f"[green]Found {len(epub_files)} EPUB files[/green]")
            
            analyzed_books = []
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                task = progress.add_task("Analyzing books...", total=len(epub_files))
                
                for epub_file in epub_files:
                    try:
                        progress.update(task, description=f"Analyzing {epub_file.name}...")
                        book_data = self.analyze_single_book(str(epub_file))
                        analyzed_books.append(book_data)
                        
                    except Exception as e:
                        console.print(f"[red]Error analyzing {epub_file.name}: {e}[/red]")
                    
                    progress.advance(task)
            
            console.print(f"[green]Successfully analyzed {len(analyzed_books)} books[/green]")
            return analyzed_books
            
        except Exception as e:
            logger.error(f"Error analyzing collection: {e}")
            raise
    
    def get_recommendations(self, book_title: str, top_n: int = 5) -> List[Dict]:
        """Get recommendations for a book"""
        try:
            # Get all books from database
            all_books = self.database.get_all_books()
            
            # Find the target book
            target_book = None
            for book in all_books:
                if book['title'].lower() == book_title.lower():
                    target_book = book
                    break
            
            if not target_book:
                console.print(f"[red]Book '{book_title}' not found in database[/red]")
                return []
            
            # Get recommendations
            recommendations = self.recommender.get_hybrid_recommendations(
                target_book, all_books, top_n=top_n
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
    
    def filter_books(self, filters: Dict) -> List[Dict]:
        """Filter books based on criteria"""
        try:
            return self.database.filter_books(filters)
        except Exception as e:
            logger.error(f"Error filtering books: {e}")
            return []
    
    def search_books(self, query: str) -> List[Dict]:
        """Search books by query"""
        try:
            return self.database.search_books(query)
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """Get collection statistics"""
        try:
            return self.database.get_book_statistics()
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def generate_visualizations(self, output_dir: str = "visualizations"):
        """Generate visualizations for the collection"""
        try:
            books = self.database.get_all_books()
            if not books:
                console.print("[yellow]No books found in database[/yellow]")
                return
            
            with console.status("[bold green]Generating visualizations..."):
                report_files = self.visualizer.generate_collection_report(books, output_dir)
            
            console.print(f"[green]Generated {len(report_files)} visualizations in {output_dir}[/green]")
            return report_files
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")
            return {}
    
    def export_data(self, format: str = "json", output_file: str = None):
        """Export collection data"""
        try:
            books = self.database.get_all_books()
            
            if format.lower() == "json":
                output_file = output_file or "books_export.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(books, f, indent=2, ensure_ascii=False)
            
            elif format.lower() == "csv":
                import pandas as pd
                output_file = output_file or "books_export.csv"
                
                # Flatten the data for CSV
                flattened_books = []
                for book in books:
                    flat_book = {
                        'title': book.get('title', ''),
                        'authors': ', '.join(book.get('authors', [])),
                        'genre': book.get('primary_genre', ''),
                        'word_count': book.get('word_count', 0),
                        'complexity_level': book.get('complexity_level', ''),
                        'reading_level': book.get('reading_level', ''),
                        'language': book.get('language', ''),
                        'publisher': book.get('publisher', ''),
                        'publication_date': book.get('publication_date', ''),
                        'isbn': book.get('isbn', '')
                    }
                    flattened_books.append(flat_book)
                
                df = pd.DataFrame(flattened_books)
                df.to_csv(output_file, index=False)
            
            console.print(f"[green]Exported data to {output_file}[/green]")
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")


def create_book_table(books: List[Dict]) -> Table:
    """Create a rich table for displaying books"""
    table = Table(title="Book Collection")
    
    table.add_column("Title", style="cyan", no_wrap=True)
    table.add_column("Author", style="magenta")
    table.add_column("Genre", style="green")
    table.add_column("Words", justify="right", style="blue")
    table.add_column("Complexity", style="yellow")
    table.add_column("Reading Level", style="red")
    
    for book in books:
        table.add_row(
            book.get('title', 'Unknown')[:50] + "..." if len(book.get('title', '')) > 50 else book.get('title', 'Unknown'),
            ', '.join(book.get('authors', [])[:2]) + "..." if len(book.get('authors', [])) > 2 else ', '.join(book.get('authors', [])),
            book.get('primary_genre', 'Unknown'),
            str(book.get('word_count', 0)),
            book.get('complexity_level', 'Unknown'),
            book.get('reading_level', 'Unknown')
        )
    
    return table


@click.group()
@click.option('--db-path', default='books.db', help='Database file path')
@click.pass_context
def cli(ctx, db_path):
    """Ebook Collection Analyzer - A powerful tool for analyzing ebook collections"""
    ctx.ensure_object(dict)
    ctx.obj['analyzer'] = EbookAnalyzer(db_path)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--language', '-l', default='auto', help='Language for analysis (auto/english/french)')
@click.pass_context
def analyze_book(ctx, file_path, language):
    """Analyze a single book"""
    # Create analyzer with specified language
    analyzer = EbookAnalyzer(language=language)
    
    try:
        book_data = analyzer.analyze_single_book(file_path)
        
        # Display results
        topics = book_data.get('topics', {})
        main_themes = topics.get('main_themes', [])
        themes_with_scores = topics.get('themes_with_scores', [])
        
        # Format genres with scores
        genres_info = f"{book_data['primary_genre']} ({book_data['primary_confidence']:.2f})"
        if book_data.get('secondary_genres'):
            secondary_genres = []
            for i, genre in enumerate(book_data['secondary_genres']):
                confidence = book_data['secondary_confidences'][i] if i < len(book_data['secondary_confidences']) else 0.0
                secondary_genres.append(f"{genre} ({confidence:.2f})")
            genres_info += f" | {', '.join(secondary_genres)}"
        
        # Format topics with scores
        if themes_with_scores:
            topics_display = []
            for theme, score in themes_with_scores[:3]:
                topics_display.append(f"{theme} ({score:.2f})")
            topics_text = ' | '.join(topics_display)
        elif main_themes:
            topics_text = ', '.join(main_themes[:3])
        else:
            topics_text = "No themes detected"
        
        console.print(Panel.fit(
            f"[bold green]Analysis Complete![/bold green]\n\n"
            f"[bold]Title:[/bold] {book_data['title']}\n"
            f"[bold]Author(s):[/bold] {', '.join(book_data['authors'])}\n"
            f"[bold]Language:[/bold] {book_data.get('detected_language', 'Unknown')}\n"
            f"[bold]Genres:[/bold] {genres_info}\n"
            f"[bold]Word Count:[/bold] {book_data['word_count']:,}\n"
            f"[bold]Complexity Level:[/bold] {book_data['complexity_level']}\n"
            f"[bold]Reading Level:[/bold] {book_data['reading_level']}\n"
            f"[bold]Topics:[/bold] {topics_text}",
            title="Book Analysis Results"
        ))
        
        # Save to database
        analyzer.database.add_book(book_data)
        console.print(f"\n[green]Book saved to database[/green]")
        
    except Exception as e:
        console.print(f"[red]Error analyzing book: {e}[/red]")


@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--language', '-l', default='auto', help='Language for analysis (auto/english/french)')
@click.pass_context
def analyze_collection(ctx, directory, language):
    """Analyze all books in a directory"""
    # Create analyzer with specified language
    analyzer = EbookAnalyzer(language=language)
    
    try:
        books = analyzer.analyze_collection(directory)
        
        if books:
            console.print(f"\n[bold green]Collection Analysis Complete![/bold green]")
            console.print(f"Analyzed {len(books)} books\n")
            console.print(f"[blue]Language setting: {language}[/blue]\n")
            
            # Show summary table
            table = create_book_table(books)
            console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error analyzing collection: {e}[/red]")


@cli.command()
@click.argument('book_title')
@click.option('--top-n', default=5, help='Number of recommendations')
@click.pass_context
def recommend(ctx, book_title, top_n):
    """Get book recommendations"""
    analyzer = ctx.obj['analyzer']
    
    try:
        recommendations = analyzer.get_recommendations(book_title, top_n)
        
        if recommendations:
            console.print(f"\n[bold green]Recommendations for '{book_title}':[/bold green]\n")
            
            table = Table(title="Book Recommendations")
            table.add_column("Title", style="cyan")
            table.add_column("Author", style="magenta")
            table.add_column("Genre", style="green")
            table.add_column("Similarity", justify="right", style="yellow")
            
            for book, similarity in recommendations:
                table.add_row(
                    book.get('title', 'Unknown'),
                    ', '.join(book.get('authors', [])),
                    book.get('primary_genre', 'Unknown'),
                    f"{similarity:.3f}"
                )
            
            console.print(table)
        else:
            console.print(f"[yellow]No recommendations found for '{book_title}'[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error getting recommendations: {e}[/red]")


@cli.command()
@click.option('--genre', help='Filter by genre')
@click.option('--min-words', type=int, help='Minimum word count')
@click.option('--max-words', type=int, help='Maximum word count')
@click.option('--complexity', help='Filter by complexity level')
@click.option('--author', help='Filter by author')
@click.option('--language', help='Filter by language')
@click.pass_context
def filter(ctx, genre, min_words, max_words, complexity, author, language):
    """Filter books by various criteria"""
    analyzer = ctx.obj['analyzer']
    
    try:
        filters = {}
        if genre:
            filters['genre'] = genre
        if min_words:
            filters['min_words'] = min_words
        if max_words:
            filters['max_words'] = max_words
        if complexity:
            filters['complexity'] = complexity
        if author:
            filters['author'] = author
        if language:
            filters['language'] = language
        
        books = analyzer.filter_books(filters)
        
        if books:
            console.print(f"\n[bold green]Found {len(books)} books matching criteria:[/bold green]\n")
            table = create_book_table(books)
            console.print(table)
        else:
            console.print("[yellow]No books found matching the criteria[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error filtering books: {e}[/red]")


@cli.command()
@click.argument('query')
@click.pass_context
def search(ctx, query):
    """Search books by query"""
    analyzer = ctx.obj['analyzer']
    
    try:
        books = analyzer.search_books(query)
        
        if books:
            console.print(f"\n[bold green]Search results for '{query}':[/bold green]\n")
            table = create_book_table(books)
            console.print(table)
        else:
            console.print(f"[yellow]No books found matching '{query}'[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error searching books: {e}[/red]")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show collection statistics"""
    analyzer = ctx.obj['analyzer']
    
    try:
        stats = analyzer.get_statistics()
        
        if stats:
            console.print(Panel.fit(
                f"[bold green]Collection Statistics[/bold green]\n\n"
                f"[bold]Total Books:[/bold] {stats.get('total_books', 0)}\n"
                f"[bold]Average Words:[/bold] {stats.get('word_statistics', {}).get('avg_words', 0):,.0f}\n"
                f"[bold]Total Words:[/bold] {stats.get('word_statistics', {}).get('total_words', 0):,.0f}\n"
                f"[bold]Genres:[/bold] {len(stats.get('genre_distribution', {}))}\n"
                f"[bold]Languages:[/bold] {len(stats.get('language_distribution', {}))}",
                title="Statistics"
            ))
            
            # Show genre distribution
            if stats.get('genre_distribution'):
                console.print("\n[bold]Genre Distribution:[/bold]")
                for genre, count in sorted(stats['genre_distribution'].items(), key=lambda x: x[1], reverse=True)[:10]:
                    console.print(f"  {genre}: {count}")
        
    except Exception as e:
        console.print(f"[red]Error getting statistics: {e}[/red]")


@cli.command()
@click.option('--output-dir', default='visualizations', help='Output directory for visualizations')
@click.pass_context
def visualize(ctx, output_dir):
    """Generate visualizations for the collection"""
    analyzer = ctx.obj['analyzer']
    
    try:
        report_files = analyzer.generate_visualizations(output_dir)
        
        if report_files:
            console.print(f"\n[bold green]Generated visualizations:[/bold green]")
            for chart_type, file_path in report_files.items():
                console.print(f"  {chart_type}: {file_path}")
        else:
            console.print("[yellow]No visualizations generated[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error generating visualizations: {e}[/red]")


@cli.command()
@click.option('--format', type=click.Choice(['json', 'csv']), default='json', help='Export format')
@click.option('--output-file', help='Output file path')
@click.pass_context
def export(ctx, format, output_file):
    """Export collection data"""
    analyzer = ctx.obj['analyzer']
    
    try:
        analyzer.export_data(format, output_file)
        
    except Exception as e:
        console.print(f"[red]Error exporting data: {e}[/red]")


@cli.command()
@click.pass_context
def list(ctx):
    """List all books in the collection"""
    analyzer = ctx.obj['analyzer']
    
    try:
        books = analyzer.database.get_all_books()
        
        if books:
            console.print(f"\n[bold green]Collection ({len(books)} books):[/bold green]\n")
            table = create_book_table(books)
            console.print(table)
        else:
            console.print("[yellow]No books found in database[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error listing books: {e}[/red]")


if __name__ == '__main__':
    cli()
