#!/usr/bin/env python3
"""
Script to reorganize the full_library directory into a clean structure:
full_library_clean/<author_name>/<book_name>

This script handles:
- Alphabetical directory structures
- Special cases like "Collectif", "Anonyme", "Anthologie"
- Loose files in root directory
- Inconsistent naming patterns
- Duplicate authors across different directories
"""

import os
import shutil
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LibraryReorganizer:
    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.author_mapping = {}  # Maps original author names to normalized names
        self.processed_files = set()
        
    def normalize_author_name(self, author_name: str) -> str:
        """Normalize author name for consistent formatting."""
        # Remove common prefixes and suffixes
        author = author_name.strip()
        
        # Handle special cases
        if author.lower() in ['collectif', 'collective', 'various', 'various authors']:
            return "Collectif"
        if author.lower() in ['anonyme', 'anonymous', 'unknown']:
            return "Anonyme"
        if author.lower() in ['anthologie', 'anthology']:
            return "Anthologie"
            
        # Remove common suffixes like ", Maria" or " _ MARYRHAGE"
        author = re.sub(r'\s*[,_]\s*[A-Z\s]+$', '', author)
        
        # Normalize unicode characters
        author = unicodedata.normalize('NFD', author)
        
        # Convert to title case but preserve existing capitalization patterns
        # Split by spaces and handle each part
        parts = author.split()
        normalized_parts = []
        
        for part in parts:
            # Handle special cases like "de", "van", "von", etc.
            if part.lower() in ['de', 'van', 'von', 'del', 'della', 'di', 'du', 'le', 'la']:
                normalized_parts.append(part.lower())
            else:
                # Preserve existing capitalization but ensure first letter is uppercase
                if part:
                    normalized_parts.append(part[0].upper() + part[1:])
        
        return ' '.join(normalized_parts)
    
    def extract_author_from_filename(self, filename: str) -> Optional[str]:
        """Extract author name from filename patterns."""
        # Remove file extension
        name = Path(filename).stem
        
        # Common patterns
        patterns = [
            r'^\[([^\]]+)\]_',  # [Author Name]_Title
            r'^([^-]+)\s*-\s*',  # Author - Title
            r'^([^_]+)_',  # Author_Title
        ]
        
        for pattern in patterns:
            match = re.match(pattern, name)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_book_title(self, filename: str, author_name: str = None) -> str:
        """Extract book title from filename."""
        name = Path(filename).stem
        
        # Remove author prefix if present
        if author_name:
            # Try different patterns to remove author name
            patterns = [
                rf'^\[{re.escape(author_name)}\]_',
                rf'^{re.escape(author_name)}\s*-\s*',
                rf'^{re.escape(author_name)}_',
            ]
            
            for pattern in patterns:
                name = re.sub(pattern, '', name)
        
        # Clean up the title
        title = name.strip()
        title = re.sub(r'^[-_\s]+', '', title)  # Remove leading separators
        title = re.sub(r'[-_\s]+$', '', title)  # Remove trailing separators
        
        # Normalize unicode
        title = unicodedata.normalize('NFD', title)
        
        return title
    
    def process_directory(self, dir_path: Path) -> None:
        """Process a directory and extract author/book information."""
        logger.info(f"Processing directory: {dir_path}")
        
        for item in dir_path.iterdir():
            if item.is_file():
                self.process_file(item)
            elif item.is_dir():
                # Check if this looks like an author directory
                if self.is_author_directory(item):
                    self.process_author_directory(item)
                else:
                    # Recursively process subdirectories
                    self.process_directory(item)
    
    def is_author_directory(self, dir_path: Path) -> bool:
        """Check if a directory contains author names."""
        # Look for patterns that indicate author directories
        dir_name = dir_path.name
        
        # Skip certain directories
        if dir_name in ['_calibre', 'metadata.db', 'metadata_db_prefs_backup.json']:
            return False
            
        # Check if directory contains files (not just subdirectories)
        has_files = any(item.is_file() for item in dir_path.iterdir())
        
        # Check if directory name looks like an author name
        # Author names typically contain commas, spaces, and are capitalized
        looks_like_author = (
            ',' in dir_name or 
            (len(dir_name.split()) >= 2 and dir_name[0].isupper())
        )
        
        return has_files and looks_like_author
    
    def process_author_directory(self, author_dir: Path) -> None:
        """Process an author directory."""
        original_author = author_dir.name
        normalized_author = self.normalize_author_name(original_author)
        
        logger.info(f"Processing author: {original_author} -> {normalized_author}")
        
        # Create target author directory
        target_author_dir = self.target_dir / normalized_author
        target_author_dir.mkdir(parents=True, exist_ok=True)
        
        # Process all files in the author directory
        for file_path in author_dir.iterdir():
            if file_path.is_file():
                self.copy_file_to_author_directory(file_path, target_author_dir, normalized_author)
    
    def process_file(self, file_path: Path) -> None:
        """Process a single file."""
        if file_path in self.processed_files:
            return
            
        filename = file_path.name
        
        # Skip certain file types
        if file_path.suffix.lower() in ['.nfo', '.db', '.json']:
            return
            
        # Try to extract author from filename
        author_from_filename = self.extract_author_from_filename(filename)
        
        if author_from_filename:
            normalized_author = self.normalize_author_name(author_from_filename)
            target_author_dir = self.target_dir / normalized_author
            target_author_dir.mkdir(parents=True, exist_ok=True)
            
            self.copy_file_to_author_directory(file_path, target_author_dir, normalized_author)
        else:
            # If we can't extract author, put in "Unknown" directory
            logger.warning(f"Could not extract author from filename: {filename}")
            target_author_dir = self.target_dir / "Unknown"
            target_author_dir.mkdir(parents=True, exist_ok=True)
            
            self.copy_file_to_author_directory(file_path, target_author_dir, "Unknown")
    
    def copy_file_to_author_directory(self, source_file: Path, target_author_dir: Path, author_name: str) -> None:
        """Copy a file to the appropriate author directory with proper naming."""
        if source_file in self.processed_files:
            return
            
        filename = source_file.name
        book_title = self.extract_book_title(filename, author_name)
        
        # Create a clean filename
        clean_filename = f"{book_title}{source_file.suffix}"
        
        # Handle duplicates
        target_file = target_author_dir / clean_filename
        counter = 1
        while target_file.exists():
            clean_filename = f"{book_title}_{counter}{source_file.suffix}"
            target_file = target_author_dir / clean_filename
            counter += 1
        
        try:
            shutil.copy2(source_file, target_file)
            logger.info(f"Copied: {source_file} -> {target_file}")
            self.processed_files.add(source_file)
        except Exception as e:
            logger.error(f"Error copying {source_file}: {e}")
    
    def reorganize(self) -> None:
        """Main method to reorganize the library."""
        logger.info(f"Starting library reorganization from {self.source_dir} to {self.target_dir}")
        
        # Create target directory
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
        # Process the source directory
        self.process_directory(self.source_dir)
        
        # Generate summary
        self.generate_summary()
        
        logger.info("Library reorganization completed!")
    
    def generate_summary(self) -> None:
        """Generate a summary of the reorganization."""
        logger.info("\n" + "="*50)
        logger.info("REORGANIZATION SUMMARY")
        logger.info("="*50)
        
        total_authors = len([d for d in self.target_dir.iterdir() if d.is_dir()])
        total_files = len(self.processed_files)
        
        logger.info(f"Total authors: {total_authors}")
        logger.info(f"Total files processed: {total_files}")
        
        # List all authors
        logger.info("\nAuthors found:")
        for author_dir in sorted(self.target_dir.iterdir()):
            if author_dir.is_dir():
                file_count = len(list(author_dir.iterdir()))
                logger.info(f"  {author_dir.name}: {file_count} files")

def main():
    """Main function."""
    source_dir = "data/full_library"
    target_dir = "data/full_library_clean"
    
    reorganizer = LibraryReorganizer(source_dir, target_dir)
    reorganizer.reorganize()

if __name__ == "__main__":
    main()
