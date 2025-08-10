"""
Resource manager for loading and accessing translations from JSON files
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ResourceManager:
    """Manages loading and accessing translation resources from JSON files"""
    
    def __init__(self, resources_dir: str = None):
        """Initialize the resource manager"""
        if resources_dir is None:
            # Default to the resources directory in the same folder as this file
            resources_dir = os.path.join(os.path.dirname(__file__), 'resources')
        
        self.resources_dir = Path(resources_dir)
        self._translations = {}
        self._loaded_languages = set()
        
        # Load available languages
        self.available_languages = self._discover_languages()
    
    def _discover_languages(self) -> Dict[str, Dict[str, str]]:
        """Discover available language files and their metadata"""
        languages = {}
        
        if not self.resources_dir.exists():
            return languages
        
        for json_file in self.resources_dir.glob('*.json'):
            lang_code = json_file.stem  # filename without extension

            # Skip non-language resources (like tag maps)
            if lang_code.startswith('tag_'):
                continue

            # Try to load the file to get language info
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                meta = data.get('_meta', {}) if isinstance(data, dict) else {}
                # Only accept as a language if it declares a proper meta.code
                code_from_meta = meta.get('code')
                if not code_from_meta:
                    continue

                lang_name = meta.get('name', lang_code.title())
                lang_flag = meta.get('flag', '🌐')

                languages[lang_code] = {
                    'name': lang_name,
                    'flag': lang_flag,
                    'code': lang_code
                }
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load language file {json_file}: {e}")
                # Do not add invalid files to languages
                continue
        
        return languages
    
    def load_language(self, language_code: str) -> bool:
        """Load translations for a specific language"""
        if language_code in self._loaded_languages:
            return True
        
        json_file = self.resources_dir / f"{language_code}.json"
        
        if not json_file.exists():
            print(f"Warning: Language file not found: {json_file}")
            return False
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Store the translations
            self._translations[language_code] = data
            self._loaded_languages.add(language_code)
            return True
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading language file {json_file}: {e}")
            return False
    
    def get_translation(self, key: str, language_code: str = 'en', **kwargs) -> str:
        """Get a translation for a given key and language"""
        # Load the language if not already loaded
        if language_code not in self._loaded_languages:
            if not self.load_language(language_code):
                # Fallback to English if the requested language fails to load
                if language_code != 'en':
                    return self.get_translation(key, 'en', **kwargs)
                return key  # Return the key itself as fallback
        
        # Navigate through nested keys (e.g., "navigation.nav_home")
        keys = key.split('.')
        value = self._translations.get(language_code, {})
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, key)
            else:
                value = key
                break
        
        # If we didn't find the translation, try English as fallback
        if value == key and language_code != 'en':
            return self.get_translation(key, 'en', **kwargs)
        
        # Replace placeholders with kwargs
        if isinstance(value, str):
            for k, v in kwargs.items():
                value = value.replace(f'{{{{{k}}}}}', str(v))
        
        return value
    
    def get_all_translations(self, language_code: str = 'en') -> Dict[str, Any]:
        """Get all translations for a language"""
        if language_code not in self._loaded_languages:
            self.load_language(language_code)
        
        return self._translations.get(language_code, {})
    
    def reload_language(self, language_code: str) -> bool:
        """Reload translations for a specific language"""
        if language_code in self._loaded_languages:
            self._loaded_languages.remove(language_code)
            if language_code in self._translations:
                del self._translations[language_code]
        
        return self.load_language(language_code)
    
    def reload_all(self) -> None:
        """Reload all languages"""
        self._loaded_languages.clear()
        self._translations.clear()
        self.available_languages = self._discover_languages()
    
    def get_language_info(self, language_code: str) -> Optional[Dict[str, str]]:
        """Get language metadata (name, flag, etc.)"""
        return self.available_languages.get(language_code)


# Global resource manager instance
_resource_manager = None


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


def get_translation(key: str, language_code: str = 'en', **kwargs) -> str:
    """Get a translation for a given key and language"""
    return get_resource_manager().get_translation(key, language_code, **kwargs)


def get_language_info(language_code: str) -> Optional[Dict[str, str]]:
    """Get language metadata"""
    return get_resource_manager().get_language_info(language_code)


def get_available_languages() -> Dict[str, Dict[str, str]]:
    """Get all available languages"""
    return get_resource_manager().available_languages


def reload_language(language_code: str) -> bool:
    """Reload a specific language"""
    return get_resource_manager().reload_language(language_code)


def reload_all() -> None:
    """Reload all languages"""
    get_resource_manager().reload_all()
