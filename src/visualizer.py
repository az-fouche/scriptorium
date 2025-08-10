"""
Visualization Module

This module provides data visualization capabilities for the book collection,
including charts, graphs, and interactive visualizations.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from wordcloud import WordCloud
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Set style for matplotlib
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


class BookVisualizer:
    """Data visualization for book collection analysis"""
    
    def __init__(self, output_dir: str = "visualizations"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(exist_ok=True)
    
    def create_genre_distribution_chart(self, genre_data: Dict[str, int], 
                                      save_path: Optional[str] = None) -> str:
        """Create a bar chart of genre distribution"""
        try:
            # Prepare data
            genres = list(genre_data.keys())
            counts = list(genre_data.values())
            
            # Create figure
            plt.figure(figsize=(12, 8))
            bars = plt.bar(genres, counts, color=sns.color_palette("husl", len(genres)))
            
            # Customize chart
            plt.title('Genre Distribution in Book Collection', fontsize=16, fontweight='bold')
            plt.xlabel('Genre', fontsize=12)
            plt.ylabel('Number of Books', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Add value labels on bars
            for bar, count in zip(bars, counts):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        str(count), ha='center', va='bottom')
            
            # Save or show
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
                return ""
                
        except Exception as e:
            logger.error(f"Error creating genre distribution chart: {e}")
            return ""
    
    def create_complexity_analysis_chart(self, books: List[Dict], 
                                       save_path: Optional[str] = None) -> str:
        """Create a scatter plot of complexity vs word count"""
        try:
            # Extract data
            word_counts = [book.get('word_count', 0) for book in books]
            complexity_scores = [book.get('overall_complexity_score', 0) for book in books]
            genres = [book.get('primary_genre', 'Unknown') for book in books]
            
            # Create figure
            plt.figure(figsize=(12, 8))
            
            # Create scatter plot with color coding by genre
            unique_genres = list(set(genres))
            colors = sns.color_palette("husl", len(unique_genres))
            
            for i, genre in enumerate(unique_genres):
                mask = [g == genre for g in genres]
                plt.scatter([wc for j, wc in enumerate(word_counts) if mask[j]],
                          [cs for j, cs in enumerate(complexity_scores) if mask[j]],
                          c=[colors[i]], label=genre, alpha=0.7, s=50)
            
            plt.title('Book Complexity vs Word Count', fontsize=16, fontweight='bold')
            plt.xlabel('Word Count', fontsize=12)
            plt.ylabel('Complexity Score', fontsize=12)
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Save or show
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
                return ""
                
        except Exception as e:
            logger.error(f"Error creating complexity analysis chart: {e}")
            return ""
    
    def create_word_cloud(self, text: str, title: str = "Word Cloud", 
                         save_path: Optional[str] = None) -> str:
        """Create a word cloud from text"""
        try:
            # Generate word cloud
            wordcloud = WordCloud(
                width=800, 
                height=400, 
                background_color='white',
                max_words=100,
                colormap='viridis',
                contour_width=1,
                contour_color='steelblue'
            ).generate(text)
            
            # Create figure
            plt.figure(figsize=(12, 8))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.title(title, fontsize=16, fontweight='bold', pad=20)
            plt.tight_layout()
            
            # Save or show
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
                return ""
                
        except Exception as e:
            logger.error(f"Error creating word cloud: {e}")
            return ""
    
    def create_reading_level_distribution(self, books: List[Dict], 
                                        save_path: Optional[str] = None) -> str:
        """Create a pie chart of reading level distribution"""
        try:
            # Count reading levels
            reading_levels = [book.get('reading_level', 'Unknown') for book in books]
            level_counts = {}
            
            for level in reading_levels:
                level_counts[level] = level_counts.get(level, 0) + 1
            
            # Create pie chart
            plt.figure(figsize=(10, 8))
            colors = sns.color_palette("husl", len(level_counts))
            
            wedges, texts, autotexts = plt.pie(
                list(level_counts.values()),
                labels=list(level_counts.keys()),
                autopct='%1.1f%%',
                colors=colors,
                startangle=90
            )
            
            plt.title('Reading Level Distribution', fontsize=16, fontweight='bold')
            plt.axis('equal')
            
            # Save or show
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
                return ""
                
        except Exception as e:
            logger.error(f"Error creating reading level distribution: {e}")
            return ""
    
    def create_topic_analysis_chart(self, topic_data: Dict, 
                                  save_path: Optional[str] = None) -> str:
        """Create a horizontal bar chart of topic frequencies"""
        try:
            # Prepare data
            topics = list(topic_data.keys())
            frequencies = list(topic_data.values())
            
            # Sort by frequency
            sorted_data = sorted(zip(topics, frequencies), key=lambda x: x[1], reverse=True)
            topics, frequencies = zip(*sorted_data)
            
            # Create horizontal bar chart
            plt.figure(figsize=(12, 8))
            bars = plt.barh(topics, frequencies, color=sns.color_palette("husl", len(topics)))
            
            # Customize chart
            plt.title('Topic Frequency Analysis', fontsize=16, fontweight='bold')
            plt.xlabel('Frequency', fontsize=12)
            plt.ylabel('Topics', fontsize=12)
            plt.gca().invert_yaxis()
            
            # Add value labels
            for i, (bar, freq) in enumerate(zip(bars, frequencies)):
                plt.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                        str(freq), ha='left', va='center')
            
            plt.tight_layout()
            
            # Save or show
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
                return ""
                
        except Exception as e:
            logger.error(f"Error creating topic analysis chart: {e}")
            return ""
    
    def create_author_analysis_chart(self, books: List[Dict], 
                                   save_path: Optional[str] = None) -> str:
        """Create a chart showing author statistics"""
        try:
            # Extract author data
            author_counts = {}
            for book in books:
                authors = book.get('authors', [])
                for author in authors:
                    author_counts[author] = author_counts.get(author, 0) + 1
            
            # Get top authors
            top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:15]
            authors, counts = zip(*top_authors)
            
            # Create bar chart
            plt.figure(figsize=(14, 8))
            bars = plt.bar(authors, counts, color=sns.color_palette("husl", len(authors)))
            
            # Customize chart
            plt.title('Most Prolific Authors', fontsize=16, fontweight='bold')
            plt.xlabel('Author', fontsize=12)
            plt.ylabel('Number of Books', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels
            for bar, count in zip(bars, counts):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        str(count), ha='center', va='bottom')
            
            plt.tight_layout()
            
            # Save or show
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
                return ""
                
        except Exception as e:
            logger.error(f"Error creating author analysis chart: {e}")
            return ""
    
    def create_collection_summary_dashboard(self, books: List[Dict], 
                                          save_path: Optional[str] = None) -> str:
        """Create a comprehensive dashboard with multiple charts"""
        try:
            # Create subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. Genre distribution
            genre_counts = {}
            for book in books:
                genre = book.get('primary_genre', 'Unknown')
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            genres = list(genre_counts.keys())[:8]  # Top 8 genres
            counts = [genre_counts[g] for g in genres]
            
            ax1.bar(genres, counts, color=sns.color_palette("husl", len(genres)))
            ax1.set_title('Genre Distribution', fontweight='bold')
            ax1.set_xticklabels(genres, rotation=45, ha='right')
            
            # 2. Word count distribution
            word_counts = [book.get('word_count', 0) for book in books]
            ax2.hist(word_counts, bins=20, color='skyblue', alpha=0.7, edgecolor='black')
            ax2.set_title('Word Count Distribution', fontweight='bold')
            ax2.set_xlabel('Word Count')
            ax2.set_ylabel('Number of Books')
            
            # 3. Complexity vs word count scatter
            complexity_scores = [book.get('overall_complexity_score', 0) for book in books]
            ax3.scatter(word_counts, complexity_scores, alpha=0.6, color='coral')
            ax3.set_title('Complexity vs Word Count', fontweight='bold')
            ax3.set_xlabel('Word Count')
            ax3.set_ylabel('Complexity Score')
            
            # 4. Reading level distribution
            reading_levels = [book.get('reading_level', 'Unknown') for book in books]
            level_counts = {}
            for level in reading_levels:
                level_counts[level] = level_counts.get(level, 0) + 1
            
            ax4.pie(level_counts.values(), labels=level_counts.keys(), autopct='%1.1f%%')
            ax4.set_title('Reading Level Distribution', fontweight='bold')
            
            plt.tight_layout()
            
            # Save or show
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
                return ""
                
        except Exception as e:
            logger.error(f"Error creating collection summary dashboard: {e}")
            return ""
    
    def create_interactive_plotly_chart(self, books: List[Dict], 
                                      chart_type: str = "scatter") -> go.Figure:
        """Create an interactive Plotly chart"""
        try:
            # Prepare data
            df = pd.DataFrame([
                {
                    'title': book.get('title', ''),
                    'author': ', '.join(book.get('authors', [])),
                    'genre': book.get('primary_genre', 'Unknown'),
                    'word_count': book.get('word_count', 0),
                    'complexity': book.get('overall_complexity_score', 0),
                    'reading_level': book.get('reading_level', 'Unknown')
                }
                for book in books
            ])
            
            if chart_type == "scatter":
                fig = px.scatter(
                    df, 
                    x='word_count', 
                    y='complexity',
                    color='genre',
                    hover_data=['title', 'author'],
                    title='Book Complexity Analysis'
                )
            elif chart_type == "bar":
                genre_counts = df['genre'].value_counts()
                fig = px.bar(
                    x=genre_counts.index,
                    y=genre_counts.values,
                    title='Genre Distribution'
                )
            elif chart_type == "histogram":
                fig = px.histogram(
                    df,
                    x='word_count',
                    title='Word Count Distribution'
                )
            else:
                # Default to scatter
                fig = px.scatter(
                    df, 
                    x='word_count', 
                    y='complexity',
                    color='genre',
                    title='Book Complexity Analysis'
                )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating interactive Plotly chart: {e}")
            return go.Figure()
    
    def create_keyword_network(self, keywords: List[Tuple[str, float]], 
                             save_path: Optional[str] = None) -> str:
        """Create a network visualization of keywords"""
        try:
            # This would require networkx for a proper network visualization
            # For now, create a simple bar chart of keyword frequencies
            
            words, frequencies = zip(*keywords[:20])  # Top 20 keywords
            
            plt.figure(figsize=(12, 8))
            bars = plt.barh(words, frequencies, color=sns.color_palette("husl", len(words)))
            
            plt.title('Most Frequent Keywords', fontsize=16, fontweight='bold')
            plt.xlabel('Frequency', fontsize=12)
            plt.ylabel('Keywords', fontsize=12)
            plt.gca().invert_yaxis()
            
            # Add value labels
            for bar, freq in zip(bars, frequencies):
                plt.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                        f'{freq:.2f}', ha='left', va='center')
            
            plt.tight_layout()
            
            # Save or show
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
                return ""
                
        except Exception as e:
            logger.error(f"Error creating keyword network: {e}")
            return ""
    
    def generate_collection_report(self, books: List[Dict], 
                                 output_dir: str = None) -> Dict[str, str]:
        """Generate a comprehensive collection report with multiple visualizations"""
        try:
            output_dir = output_dir or self.output_dir
            Path(output_dir).mkdir(exist_ok=True)
            
            report_files = {}
            
            # 1. Genre distribution
            genre_counts = {}
            for book in books:
                genre = book.get('primary_genre', 'Unknown')
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            report_files['genre_distribution'] = self.create_genre_distribution_chart(
                genre_counts, 
                f"{output_dir}/genre_distribution.png"
            )
            
            # 2. Complexity analysis
            report_files['complexity_analysis'] = self.create_complexity_analysis_chart(
                books, 
                f"{output_dir}/complexity_analysis.png"
            )
            
            # 3. Reading level distribution
            report_files['reading_levels'] = self.create_reading_level_distribution(
                books, 
                f"{output_dir}/reading_levels.png"
            )
            
            # 4. Author analysis
            report_files['author_analysis'] = self.create_author_analysis_chart(
                books, 
                f"{output_dir}/author_analysis.png"
            )
            
            # 5. Collection summary dashboard
            report_files['summary_dashboard'] = self.create_collection_summary_dashboard(
                books, 
                f"{output_dir}/summary_dashboard.png"
            )
            
            # 6. Word cloud from all text
            all_text = " ".join([book.get('full_text', '') for book in books])
            if all_text.strip():
                report_files['word_cloud'] = self.create_word_cloud(
                    all_text, 
                    "Collection Word Cloud",
                    f"{output_dir}/word_cloud.png"
                )
            
            logger.info(f"Generated collection report with {len(report_files)} visualizations")
            return report_files
            
        except Exception as e:
            logger.error(f"Error generating collection report: {e}")
            return {}
