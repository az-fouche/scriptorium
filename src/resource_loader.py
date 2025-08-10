"""
Resource Loader Module

This module provides utilities for loading JSON resource files
containing genre and theme definitions.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ResourceLoader:
    """Load and manage JSON resource files for genres and themes"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._genres_cache = {}
        self._themes_cache = {}
    
    def load_genres(self, language: str = "english") -> Dict:
        """Load genre definitions for the specified language"""
        if language in self._genres_cache:
            return self._genres_cache[language]
        
        try:
            file_path = self.data_dir / "genres" / f"{language}_genres.json"
            if not file_path.exists():
                logger.warning(f"Genre file not found: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                genres = json.load(f)
            
            self._genres_cache[language] = genres
            logger.info(f"Loaded {len(genres)} genres for {language}")
            return genres
            
        except Exception as e:
            logger.error(f"Error loading genres for {language}: {e}")
            return {}
    
    def load_themes(self, language: str = "english") -> Dict:
        """Load theme definitions for the specified language"""
        if language in self._themes_cache:
            return self._themes_cache[language]
        
        try:
            file_path = self.data_dir / "themes" / f"{language}_themes.json"
            if not file_path.exists():
                logger.warning(f"Theme file not found: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                themes = json.load(f)
            
            self._themes_cache[language] = themes
            logger.info(f"Loaded {len(themes)} themes for {language}")
            return themes
            
        except Exception as e:
            logger.error(f"Error loading themes for {language}: {e}")
            return {}
    
    def get_genre_keywords(self, language: str = "english") -> Dict[str, List[str]]:
        """Get genre keywords dictionary for the specified language"""
        genres = self.load_genres(language)
        result = {}
        for genre, data in genres.items():
            if isinstance(data, dict) and "keywords" in data:
                result[genre] = data["keywords"]
            elif isinstance(data, list):
                result[genre] = data
            else:
                result[genre] = []
        return result
    
    def get_theme_keywords(self, language: str = "english") -> Dict[str, List[str]]:
        """Get theme keywords dictionary for the specified language"""
        themes = self.load_themes(language)
        result = {}
        for theme, data in themes.items():
            if isinstance(data, dict) and "keywords" in data:
                result[theme] = data["keywords"]
            elif isinstance(data, list):
                result[theme] = data
            else:
                result[theme] = []
        return result
    
    def get_genre_descriptions(self, language: str = "english") -> Dict[str, str]:
        """Get genre descriptions for the specified language"""
        genres = self.load_genres(language)
        result = {}
        for genre, data in genres.items():
            if isinstance(data, dict) and "description" in data:
                result[genre] = data["description"]
            else:
                result[genre] = ""
        return result
    
    def get_theme_descriptions(self, language: str = "english") -> Dict[str, str]:
        """Get theme descriptions for the specified language"""
        themes = self.load_themes(language)
        result = {}
        for theme, data in themes.items():
            if isinstance(data, dict) and "description" in data:
                result[theme] = data["description"]
            else:
                result[theme] = ""
        return result
    
    def list_available_languages(self) -> List[str]:
        """List available languages based on existing JSON files"""
        languages = []
        
        # Check genres directory
        genres_dir = self.data_dir / "genres"
        if genres_dir.exists():
            for file_path in genres_dir.glob("*_genres.json"):
                lang = file_path.stem.replace("_genres", "")
                languages.append(lang)
        
        # Check themes directory
        themes_dir = self.data_dir / "themes"
        if themes_dir.exists():
            for file_path in themes_dir.glob("*_themes.json"):
                lang = file_path.stem.replace("_themes", "")
                if lang not in languages:
                    languages.append(lang)
        
        return languages
    
    def add_genre(self, language: str, genre: str, keywords: List[str], description: str = ""):
        """Add a new genre to the JSON file"""
        try:
            file_path = self.data_dir / "genres" / f"{language}_genres.json"
            
            # Load existing genres
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    genres = json.load(f)
            else:
                genres = {}
            
            # Add new genre
            genres[genre] = {
                "keywords": keywords,
                "description": description
            }
            
            # Save back to file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(genres, f, indent=2, ensure_ascii=False)
            
            # Clear cache
            if language in self._genres_cache:
                del self._genres_cache[language]
            
            logger.info(f"Added genre '{genre}' to {language}")
            
        except Exception as e:
            logger.error(f"Error adding genre '{genre}' to {language}: {e}")
    
    def add_theme(self, language: str, theme: str, keywords: List[str], description: str = ""):
        """Add a new theme to the JSON file"""
        try:
            file_path = self.data_dir / "themes" / f"{language}_themes.json"
            
            # Load existing themes
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    themes = json.load(f)
            else:
                themes = {}
            
            # Add new theme
            themes[theme] = {
                "keywords": keywords,
                "description": description
            }
            
            # Save back to file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(themes, f, indent=2, ensure_ascii=False)
            
            # Clear cache
            if language in self._themes_cache:
                del self._themes_cache[language]
            
            logger.info(f"Added theme '{theme}' to {language}")
            
        except Exception as e:
            logger.error(f"Error adding theme '{theme}' to {language}: {e}")
    
    def validate_resources(self) -> Dict[str, List[str]]:
        """Validate all resource files and return any issues"""
        issues = []
        
        # Check if data directory exists
        if not self.data_dir.exists():
            issues.append(f"Data directory does not exist: {self.data_dir}")
            return {"errors": issues}
        
        # Check genres
        genres_dir = self.data_dir / "genres"
        if not genres_dir.exists():
            issues.append(f"Genres directory does not exist: {genres_dir}")
        else:
            for file_path in genres_dir.glob("*_genres.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        genres = json.load(f)
                    
                    for genre, data in genres.items():
                        if "keywords" not in data:
                            issues.append(f"Genre '{genre}' in {file_path.name} missing 'keywords'")
                        if "description" not in data:
                            issues.append(f"Genre '{genre}' in {file_path.name} missing 'description'")
                            
                except Exception as e:
                    issues.append(f"Error loading {file_path.name}: {e}")
        
        # Check themes
        themes_dir = self.data_dir / "themes"
        if not themes_dir.exists():
            issues.append(f"Themes directory does not exist: {themes_dir}")
        else:
            for file_path in themes_dir.glob("*_themes.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        themes = json.load(f)
                    
                    for theme, data in themes.items():
                        if "keywords" not in data:
                            issues.append(f"Theme '{theme}' in {file_path.name} missing 'keywords'")
                        if "description" not in data:
                            issues.append(f"Theme '{theme}' in {file_path.name} missing 'description'")
                            
                except Exception as e:
                    issues.append(f"Error loading {file_path.name}: {e}")
        
        return {"errors": issues, "warnings": []} if issues else {"errors": [], "warnings": []}


# Global resource loader instance
resource_loader = ResourceLoader()
