"""
EPUB Parser Module

This module handles parsing of EPUB files, extracting text content,
metadata, and structural information.
"""

import os
import re
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


@dataclass
class BookMetadata:
    """Container for book metadata"""
    title: str
    authors: List[str]
    language: str
    publisher: str
    publication_date: str
    isbn: str
    description: str
    subjects: List[str]
    rights: str
    identifier: str


@dataclass
class BookContent:
    """Container for book content analysis"""
    full_text: str
    chapters: List[Dict[str, str]]
    word_count: int
    character_count: int
    paragraph_count: int
    sentence_count: int
    average_sentence_length: float
    average_word_length: float


@dataclass
class BookCover:
    """Container for book cover information"""
    image_data: Optional[bytes]
    mime_type: str
    file_name: str
    base64_data: Optional[str] = None


class EpubParser:
    """Parser for EPUB files with comprehensive text extraction and analysis"""
    
    def __init__(self):
        self.supported_extensions = {'.epub'}
    
    def can_parse(self, file_path: str) -> bool:
        """Check if the file can be parsed by this parser"""
        return Path(file_path).suffix.lower() in self.supported_extensions
    
    def parse_metadata(self, book: epub.EpubBook) -> BookMetadata:
        """Extract metadata from EPUB book"""
        metadata = book.get_metadata('DC', 'title')
        title = metadata[0][0] if metadata else "Unknown Title"
        
        # Clean up title - remove leading dashes and extra whitespace
        if title.startswith('-'):
            title = title[1:].strip()
        title = title.strip()
        
        # Additional title cleaning
        title = title.replace('  ', ' ')  # Remove double spaces
        title = title.strip()
        
        authors = []
        author_metadata = book.get_metadata('DC', 'creator')
        if author_metadata:
            authors = [author[0] for author in author_metadata]
        
        language = ""
        lang_metadata = book.get_metadata('DC', 'language')
        if lang_metadata:
            language = lang_metadata[0][0]
        
        publisher = ""
        pub_metadata = book.get_metadata('DC', 'publisher')
        if pub_metadata:
            publisher = pub_metadata[0][0]
        
        publication_date = ""
        date_metadata = book.get_metadata('DC', 'date')
        if date_metadata:
            publication_date = date_metadata[0][0]
        
        isbn = ""
        isbn_metadata = book.get_metadata('DC', 'identifier')
        if isbn_metadata:
            for identifier in isbn_metadata:
                if 'isbn' in identifier[0].lower() or len(identifier[0]) in [10, 13]:
                    isbn = identifier[0]
                    break
        
        description = ""
        desc_metadata = book.get_metadata('DC', 'description')
        if desc_metadata:
            description = desc_metadata[0][0]
        
        subjects = []
        subject_metadata = book.get_metadata('DC', 'subject')
        if subject_metadata:
            subjects = [subject[0] for subject in subject_metadata]
        
        rights = ""
        rights_metadata = book.get_metadata('DC', 'rights')
        if rights_metadata:
            rights = rights_metadata[0][0]
        
        identifier = ""
        id_metadata = book.get_metadata('DC', 'identifier')
        if id_metadata:
            identifier = id_metadata[0][0]
        
        return BookMetadata(
            title=title,
            authors=authors,
            language=language,
            publisher=publisher,
            publication_date=publication_date,
            isbn=isbn,
            description=description,
            subjects=subjects,
            rights=rights,
            identifier=identifier
        )
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}]', '', text)
        return text.strip()
    
    def extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text and clean it
        text = soup.get_text()
        return self.clean_text(text)
    
    def parse_content(self, book: epub.EpubBook) -> BookContent:
        """Extract and analyze book content"""
        full_text = ""
        chapters = []
        
        # Process all items in the book
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                html_content = item.get_content().decode('utf-8')
                text = self.extract_text_from_html(html_content)
                
                if text.strip():
                    full_text += text + "\n\n"
                    
                    # Store chapter information
                    chapter_info = {
                        'id': item.get_id(),
                        'title': item.get_name(),
                        'content': text,
                        'word_count': len(text.split())
                    }
                    chapters.append(chapter_info)
        
        # Calculate statistics
        words = full_text.split()
        sentences = re.split(r'[.!?]+', full_text)
        paragraphs = [p for p in full_text.split('\n\n') if p.strip()]
        
        word_count = len(words)
        character_count = len(full_text)
        paragraph_count = len(paragraphs)
        sentence_count = len([s for s in sentences if s.strip()])
        
        average_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        average_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
        
        return BookContent(
            full_text=full_text,
            chapters=chapters,
            word_count=word_count,
            character_count=character_count,
            paragraph_count=paragraph_count,
            sentence_count=sentence_count,
            average_sentence_length=average_sentence_length,
            average_word_length=average_word_length
        )
    
    def extract_cover_image(self, book: epub.EpubBook) -> Optional[BookCover]:
        """Extract cover image from EPUB book"""
        try:
            # Look for cover image in spine
            spine = book.spine
            for item in spine:
                if hasattr(item, 'id') and 'cover' in item.id.lower():
                    cover_item = book.get_item_by_id(item.id)
                    if cover_item:
                        return self._process_cover_item(cover_item, book)
            
            # Look for images with cover-related names
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    item_name = item.get_name().lower()
                    if any(keyword in item_name for keyword in ['cover', 'title', 'front']):
                        return self._process_cover_item(item, book)
            
            # Look for cover in OPF metadata
            try:
                opf_content = None
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT and 'package.opf' in item.get_name():
                        opf_content = item.get_content().decode('utf-8')
                        break
                
                if opf_content:
                    soup = BeautifulSoup(opf_content, 'xml')
                    # Look for cover meta tag
                    cover_meta = soup.find('meta', {'name': 'cover'})
                    if cover_meta and cover_meta.get('content'):
                        cover_id = cover_meta.get('content')
                        cover_item = book.get_item_by_id(cover_id)
                        if cover_item:
                            return self._process_cover_item(cover_item, book)
            except Exception as e:
                logger.warning(f"Error parsing OPF for cover: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting cover image: {e}")
            return None
    
    def _process_cover_item(self, item: epub.EpubItem, book: epub.EpubBook) -> BookCover:
        """Process a cover item and return BookCover object"""
        try:
            image_data = item.get_content()
            file_name = item.get_name()
            
            # Determine MIME type based on file extension
            mime_type = "image/jpeg"  # Default
            if file_name.lower().endswith('.png'):
                mime_type = "image/png"
            elif file_name.lower().endswith('.gif'):
                mime_type = "image/gif"
            elif file_name.lower().endswith('.webp'):
                mime_type = "image/webp"
            
            # Convert to base64 for easy storage and serving
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            return BookCover(
                image_data=image_data,
                mime_type=mime_type,
                file_name=file_name,
                base64_data=base64_data
            )
        except Exception as e:
            logger.error(f"Error processing cover item: {e}")
            return None
    
    def parse_book(self, file_path: str) -> Tuple[BookMetadata, BookContent, Optional[BookCover]]:
        """Parse a complete EPUB book and return metadata, content, and cover"""
        try:
            book = epub.read_epub(file_path)
            
            metadata = self.parse_metadata(book)
            content = self.parse_content(book)
            cover = self.extract_cover_image(book)
            
            logger.info(f"Successfully parsed: {metadata.title}")
            return metadata, content, cover
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {str(e)}")
            raise
    
    def get_book_info(self, file_path: str) -> Dict:
        """Get basic book information without full text extraction"""
        try:
            book = epub.read_epub(file_path)
            metadata = self.parse_metadata(book)
            
            return {
                'file_path': file_path,
                'title': metadata.title,
                'authors': metadata.authors,
                'language': metadata.language,
                'publisher': metadata.publisher,
                'publication_date': metadata.publication_date,
                'isbn': metadata.isbn,
                'subjects': metadata.subjects,
                'file_size': os.path.getsize(file_path)
            }
            
        except Exception as e:
            logger.error(f"Error getting info for {file_path}: {str(e)}")
            return {
                'file_path': file_path,
                'title': 'Unknown',
                'authors': [],
                'error': str(e)
            }
