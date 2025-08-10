"""
Tag Manager: centralizes loading of tag metadata (labels per language, colors)
and provides helpers for templates and services.

Data is decoupled from code via JSON resources:
- data/tags_v2/en.json and data/tags_v2/fr.json define the set of tag keys
- webapp/resources/tag_labels.json maps tag keys to display labels per language
- webapp/resources/tag_colors.json maps tag keys to CSS color classes

Both mappings are optional; sensible fallbacks are used if unavailable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, List

try:
    # Prefer the unified authorized vocabulary used by the LLM classifier
    from llm_tag_classifier import AUTHORIZED_TAGS as DEFAULT_TAG_KEYS
except Exception:  # pragma: no cover
    DEFAULT_TAG_KEYS: List[str] = [
        'biography','classic','coming-of-age','contemporary-fiction','crime','erotic','essay','fantasy','historical-fiction','horror','literary-fiction','memoir','mystery','non-fiction','philosophy','romance','science-fiction','scientific','short-stories','suspense','teen-young-adult','thriller','true-crime','war','western','womens-fiction'
    ]


class TagManager:
    def __init__(self,
                 project_root: Optional[Path] = None,
                 tags_dir: Optional[Path] = None,
                 resources_dir: Optional[Path] = None) -> None:
        root = project_root or Path(__file__).resolve().parents[1]
        self.tags_dir = tags_dir or (root / 'data' / 'tags_v2')
        self.resources_dir = resources_dir or (Path(__file__).resolve().parent / 'resources')

        self._tag_sets: Dict[str, Dict] = {}
        self._labels: Dict[str, Dict[str, str]] = {}
        self._colors: Dict[str, str] = {}

        self._load_tag_sets()
        self._load_labels()
        self._load_colors()

    def _load_json(self, path: Path) -> Dict:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            pass
        return {}

    def _load_tag_sets(self) -> None:
        # Load available tag definitions (keys define the set)
        # If JSON resources exist, use them; otherwise fall back to fixed vocabulary
        for lang in ('en', 'fr'):
            data = self._load_json(self.tags_dir / f'{lang}.json')
            if isinstance(data, dict) and data:
                self._tag_sets[lang] = data
            else:
                # Build a mapping with empty metadata, keys define the set
                self._tag_sets[lang] = {k: {} for k in DEFAULT_TAG_KEYS}

    def _load_labels(self) -> None:
        data = self._load_json(self.resources_dir / 'tag_labels.json')
        # Expect structure: { "en": {key: label}, "fr": {key: label} }
        if isinstance(data, dict):
            for lang, mapping in data.items():
                if isinstance(mapping, dict):
                    self._labels[lang] = {str(k): str(v) for k, v in mapping.items()}

    def _load_colors(self) -> None:
        data = self._load_json(self.resources_dir / 'tag_colors.json')
        # Expect structure: { key: css_class }
        if isinstance(data, dict):
            self._colors = {str(k): str(v) for k, v in data.items()}

    def reload(self) -> None:
        self._tag_sets.clear()
        self._labels.clear()
        self._colors.clear()
        self._load_tag_sets()
        self._load_labels()
        self._load_colors()

    def get_label(self, tag_key: Optional[str], language: str = 'en') -> str:
        if not tag_key:
            return ''
        key = str(tag_key)

        # Prefer explicit mapping if available
        lang = 'fr' if (language or 'en').startswith('fr') else 'en'
        if lang in self._labels and key in self._labels[lang]:
            return self._labels[lang][key]

        # Fallback: derive human label from key
        derived = key.replace('-', ' ').strip()
        # Special-case common tags for nicer presentation
        special = {
            'science-fiction': {'en': 'Science Fiction', 'fr': 'Science-fiction'},
            'magical-realism': {'en': 'Magical Realism', 'fr': 'Réalisme magique'},
            'alternate-history': {'en': 'Alternate History', 'fr': 'Histoire alternative'},
            'coming-of-age': {'en': "Coming of Age", 'fr': "Passage à l'âge adulte"},
            'true-crime': {'en': 'True Crime', 'fr': 'True crime'},
        }
        if key in special:
            return special[key].get(lang, special[key]['en'])
        # Title case reasonable default
        return derived.title()

    def get_color_class(self, tag_key: Optional[str]) -> str:
        if not tag_key:
            return 'bg-secondary'
        return self._colors.get(str(tag_key), 'bg-secondary')

    def get_labels_for_language(self, language: str = 'en') -> Dict[str, str]:
        # Return a complete mapping, falling back to derived labels for missing entries
        lang = 'fr' if (language or 'en').startswith('fr') else 'en'
        # Use EN tag set as authoritative for keys; if empty, use default
        keys = set(self._tag_sets.get('en', {}).keys()) or set(DEFAULT_TAG_KEYS)
        if not keys:
            # Fallback to FR keys if EN missing
            keys = set(self._tag_sets.get('fr', {}).keys())
        result: Dict[str, str] = {}
        for k in sorted(keys):
            result[k] = self.get_label(k, lang)
        return result

    def get_colors(self) -> Dict[str, str]:
        return dict(self._colors)


_tag_manager: Optional[TagManager] = None


def get_tag_manager() -> TagManager:
    global _tag_manager
    if _tag_manager is None:
        _tag_manager = TagManager()
    return _tag_manager


def get_tag_label(tag_key: Optional[str], language: str = 'en') -> str:
    return get_tag_manager().get_label(tag_key, language)


def get_tag_color_class(tag_key: Optional[str]) -> str:
    return get_tag_manager().get_color_class(tag_key)


def get_tag_labels_map(language: str = 'en') -> Dict[str, str]:
    return get_tag_manager().get_labels_for_language(language)


def get_tag_colors_map() -> Dict[str, str]:
    return get_tag_manager().get_colors()


