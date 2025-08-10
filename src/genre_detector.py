"""
Genre Detection Module

This module provides automatic genre classification for books using
machine learning techniques and text analysis.
"""

import re
import pickle
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline
import logging
try:
    from .resource_loader import resource_loader
except ImportError:
    from resource_loader import resource_loader

logger = logging.getLogger(__name__)


class GenreDetector:
    """Machine learning-based genre detection for books"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or "models/genre_detector.pkl"
        self.model = None
        self.vectorizer = None
        self.genres = [
            'Fiction', 'Non-Fiction', 'Science Fiction', 'Fantasy', 'Mystery',
            'Romance', 'Thriller', 'Horror', 'Historical Fiction', 'Biography',
            'Autobiography', 'Memoir', 'Self-Help', 'Business', 'Philosophy',
            'Religion', 'Science', 'Technology', 'History', 'Politics',
            'Poetry', 'Drama', 'Comedy', 'Adventure', 'Crime', 'War',
            'Western', 'Young Adult', 'Children', 'Educational', 'Reference'
        ]
        
        # Load genre keywords from JSON files
        self.french_genre_keywords = resource_loader.get_genre_keywords("french")
        self.genre_keywords = resource_loader.get_genre_keywords("english")
        
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained model if available"""
        try:
            model_file = Path(self.model_path)
            if model_file.exists():
                with open(model_file, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data['model']
                    self.vectorizer = model_data['vectorizer']
                    logger.info("Loaded pre-trained genre detection model")
            else:
                logger.info("No pre-trained model found. Will use rule-based classification.")
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
    
    def _save_model(self):
        """Save the trained model"""
        try:
            model_dir = Path(self.model_path).parent
            model_dir.mkdir(exist_ok=True)
            
            model_data = {
                'model': self.model,
                'vectorizer': self.vectorizer
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Could not save model: {e}")
    
    def rule_based_classification(self, text: str, metadata: Dict) -> List[Tuple[str, float]]:
        """Classify book using keyword-based rules with French support.

        This method favors signal presence per field (text/title/subjects)
        to avoid biasing towards genres with shorter keyword lists. It also
        uses word-boundary matching and reduces the weight of subject-only
        matches which are often too generic (e.g., Calibre subjects).
        """
        text_lower = text.lower()
        title_lower = metadata.get('title', '').lower()
        subjects = [s.lower() for s in metadata.get('subjects', [])]

        scores: Dict[str, float] = {}

        # Detect if text is French
        french_indicators = ['le', 'la', 'les', 'un', 'une', 'des', 'et', 'ou', 'dans', 'sur', 'avec', 'pour', 'par', 'de', 'du']
        is_french = any(indicator in text_lower for indicator in french_indicators)

        # Choose appropriate keyword set
        keywords_to_use = self.french_genre_keywords if is_french else self.genre_keywords

        # Hardening rules: require discriminative anchors for some genres to avoid generic false positives
        # - Science-Fiction: must hit at least one SF anchor (e.g., 'sf', 'espace', 'robot', 'planète', ...)
        # - Fantasy: must hit at least one Fantasy anchor (e.g., 'magie', 'dragon', 'elfe', ...)
        # - Roman: do NOT classify solely based on generic text words; require title/subjects to include 'roman'
        anchor_keywords: Dict[str, set] = {
            'Science-Fiction': {
                'science-fiction', 'sf', 'espace', 'vaisseau', 'planète', 'asteroïde', 'astronaute',
                'robot', 'cyborg', 'android', 'hyperespace', 'interstellaire', 'astronautique',
                'portail', 'warp', 'antimatière', 'vitesse-lumière', 'space opera'
            },
            'Fantasy': {
                'fantasy', 'magie', 'sorcier', 'sorcière', 'mage', 'dragon', 'elfe', 'orc', 'troll',
                'licorne', 'fée', 'royaume', 'enchanteur', 'sort', 'incantation', 'artefact'
            },
            'Roman': {'roman'}
        }

        # Per-field weights (title > text > subjects)
        TITLE_WEIGHT = 2.0
        TEXT_WEIGHT = 1.0
        SUBJECT_WEIGHT = 0.75  # reduced from 1.5 to limit subject-only dominance

        for genre, keywords in keywords_to_use.items():
            if not keywords:
                continue

            # Compile regex patterns with word boundaries for robust matching
            # Note: keep simple ASCII boundary; accents remain as-is in keywords file
            patterns = [re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE) for k in keywords]

            # Presence flags per field (count at most once per field)
            text_hit = any(p.search(text_lower) for p in patterns)
            title_hit = any(p.search(title_lower) for p in patterns)
            subjects_hit = any(p.search(subj) for subj in subjects for p in patterns)

            # Apply genre-specific anchoring constraints where applicable
            anchors = anchor_keywords.get(genre)
            if anchors:
                anchor_patterns = [re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE) for k in anchors]
                anchor_text_hit = any(p.search(text_lower) for p in anchor_patterns)
                anchor_title_hit = any(p.search(title_lower) for p in anchor_patterns)
                anchor_subjects_hit = any(p.search(subj) for subj in subjects for p in anchor_patterns)

                if genre in ('Science-Fiction', 'Fantasy'):
                    # Require at least one anchor anywhere to consider the genre at all
                    if not (anchor_text_hit or anchor_title_hit or anchor_subjects_hit):
                        continue

                if genre == 'Roman':
                    # Only allow 'Roman' if it's explicit in title or subjects (avoid generic text words)
                    if not (anchor_title_hit or anchor_subjects_hit):
                        continue

            if not (text_hit or title_hit or subjects_hit):
                continue

            # Score is presence-weighted, not proportional to keyword list size
            score = 0.0
            if text_hit:
                score += TEXT_WEIGHT
            if title_hit:
                score += TITLE_WEIGHT
            if subjects_hit:
                score += SUBJECT_WEIGHT

            # Optionally, require at least one of text/title to claim a genre strongly
            # If only subjects matched, downscale further to make it less dominant
            if subjects_hit and not (text_hit or title_hit):
                score *= 0.6

            # Normalize to 0..1 by dividing by maximum possible score
            max_possible = TITLE_WEIGHT + TEXT_WEIGHT + SUBJECT_WEIGHT
            normalized = min(score / max_possible, 1.0)
            scores[genre] = normalized

        # Sort by score and return top genres
        sorted_genres = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_genres[:5]  # Return top 5 genres
    
    def ml_classification(self, text: str) -> List[Tuple[str, float]]:
        """Classify book using machine learning model"""
        if self.model is None or self.vectorizer is None:
            return []
        
        try:
            # Vectorize text
            text_vector = self.vectorizer.transform([text])
            
            # Get predictions
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(text_vector)[0]
                genre_probs = list(zip(self.genres, probabilities))
                return sorted(genre_probs, key=lambda x: x[1], reverse=True)[:5]
            else:
                prediction = self.model.predict(text_vector)[0]
                return [(prediction, 1.0)]
                
        except Exception as e:
            logger.error(f"ML classification error: {e}")
            return []
    
    def classify_book(self, text: str, metadata: Dict) -> Dict[str, any]:
        """Classify a book into genres using both rule-based and ML methods"""
        # Rule-based classification
        rule_based_genres = self.rule_based_classification(text, metadata)
        
        # ML classification
        ml_genres = self.ml_classification(text)
        
        # Combine results
        combined_genres = {}
        
        # Add rule-based results
        for genre, score in rule_based_genres:
            combined_genres[genre] = score * 0.6  # Weight rule-based results
        
        # Add ML results
        for genre, score in ml_genres:
            if genre in combined_genres:
                combined_genres[genre] = max(combined_genres[genre], score * 0.4)
            else:
                combined_genres[genre] = score * 0.4
        
        # Sort by combined score
        sorted_genres = sorted(combined_genres.items(), key=lambda x: x[1], reverse=True)
        
        # Determine primary and secondary genres
        primary_genre = sorted_genres[0] if sorted_genres else ('Unknown', 0.0)
        secondary_genres = sorted_genres[1:4] if len(sorted_genres) > 1 else []
        
        return {
            'primary_genre': primary_genre[0],
            'primary_confidence': primary_genre[1],
            'secondary_genres': [g[0] for g in secondary_genres],
            'secondary_confidences': [g[1] for g in secondary_genres],
            'all_genres': sorted_genres,
            'rule_based_genres': rule_based_genres,
            'ml_genres': ml_genres
        }
    
    def train_model(self, training_data: List[Tuple[str, str, Dict]]):
        """Train the genre detection model"""
        if not training_data:
            logger.warning("No training data provided")
            return
        
        try:
            # Prepare data
            texts = []
            labels = []
            
            for text, genre, metadata in training_data:
                texts.append(text)
                labels.append(genre)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                texts, labels, test_size=0.2, random_state=42
            )
            
            # Create pipeline
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words='english',
                min_df=2,
                max_df=0.8
            )
            
            self.model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            )
            
            # Train model
            X_train_vectorized = self.vectorizer.fit_transform(X_train)
            self.model.fit(X_train_vectorized, y_train)
            
            # Evaluate
            X_test_vectorized = self.vectorizer.transform(X_test)
            y_pred = self.model.predict(X_test_vectorized)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"Model trained with accuracy: {accuracy:.3f}")
            logger.info(f"Classification report:\n{classification_report(y_test, y_pred)}")
            
            # Save model
            self._save_model()
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
    
    def get_genre_keywords(self, genre: str) -> List[str]:
        """Get keywords associated with a specific genre"""
        return self.genre_keywords.get(genre, [])
    
    def add_genre_keywords(self, genre: str, keywords: List[str]):
        """Add new keywords for a genre"""
        if genre not in self.genre_keywords:
            self.genre_keywords[genre] = []
        
        self.genre_keywords[genre].extend(keywords)
        logger.info(f"Added {len(keywords)} keywords for genre: {genre}")
    
    def analyze_genre_distribution(self, books: List[Dict]) -> Dict[str, int]:
        """Analyze genre distribution across a collection"""
        genre_counts = {}
        
        for book in books:
            primary_genre = book.get('primary_genre', 'Unknown')
            genre_counts[primary_genre] = genre_counts.get(primary_genre, 0) + 1
        
        return genre_counts
