"""
Topic Modeling Module

This module provides topic extraction and modeling capabilities for books,
using techniques like LDA (Latent Dirichlet Allocation) and keyword extraction.
"""

import re
from typing import Dict, List, Tuple, Optional
from collections import Counter
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation, NMF
from sklearn.cluster import KMeans
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import logging
from pathlib import Path
import spacy
from langdetect import detect, LangDetectException
# Legacy resource loader used only for old theme keywords (removed)

# LLM-based tag classifier (Claude)
try:
    from llm_tag_classifier import LLMTagClassifier, AUTHORIZED_TAGS
except Exception:  # pragma: no cover
    LLMTagClassifier = None  # type: ignore
    AUTHORIZED_TAGS = []  # type: ignore

logger = logging.getLogger(__name__)


class TopicModeler:
    """Topic modeling and extraction for books"""
    
    def __init__(self, num_topics: int = 10, max_features: int = 1000, language: str = 'auto', llm_api_key: Optional[str] = None, llm_model: str = 'claude-3-haiku-20240307'):
        self.num_topics = num_topics
        self.max_features = max_features
        self.language = language
        self.detected_language = None
        
        # Initialize language-specific components
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
        
        # Initialize vectorizers with English as default
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        
        self.count_vectorizer = CountVectorizer(
            max_features=max_features,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        
        # Topic models
        self.lda_model = None
        self.nmf_model = None
        self.kmeans_model = None
        
        # Topic keywords cache
        self.topic_keywords = {}
        
        # spaCy models for different languages
        self.nlp_models = {}
        
        # Initialize with English as default
        self._initialize_language('english')

        # Initialize LLM Tag Classifier if available
        self.llm_classifier = None
        try:
            if LLMTagClassifier is not None:
                self.llm_classifier = LLMTagClassifier(api_key=llm_api_key, model=llm_model)
                logger.info("Initialized LLMTagClassifier (Claude) for tagging")
        except Exception as e:  # pragma: no cover
            logger.warning(f"Could not initialize LLMTagClassifier: {e}")
    
    def _initialize_language(self, language: str):
        """Initialize language-specific components"""
        try:
            if language == 'french':
                self.stop_words = set(stopwords.words('french'))
                # For French, we'll use spaCy for lemmatization
                if 'fr_core_news_sm' not in self.nlp_models:
                    try:
                        self.nlp_models['fr_core_news_sm'] = spacy.load('fr_core_news_sm')
                    except OSError:
                        logger.warning("French spaCy model not found. Install with: python -m spacy download fr_core_news_sm")
                        self.nlp_models['fr_core_news_sm'] = None
                
                # Update vectorizers for French - use custom stop words list since scikit-learn doesn't support 'french'
                self.tfidf_vectorizer = TfidfVectorizer(
                    max_features=self.max_features,
                    stop_words=list(self.stop_words),
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.8
                )
                
                self.count_vectorizer = CountVectorizer(
                    max_features=self.max_features,
                    stop_words=list(self.stop_words),
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.8
                )
            else:
                self.stop_words = set(stopwords.words('english'))
                self.lemmatizer = WordNetLemmatizer()
                
                # Update vectorizers for English
                self.tfidf_vectorizer = TfidfVectorizer(
                    max_features=self.max_features,
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.8
                )
                
                self.count_vectorizer = CountVectorizer(
                    max_features=self.max_features,
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.8
                )
                
            self.detected_language = language
            logger.info(f"Initialized topic modeler for {language}")
            
        except Exception as e:
            logger.warning(f"Could not initialize {language} components: {e}")
            # Fallback to English
            self.stop_words = set(stopwords.words('english'))
            self.lemmatizer = WordNetLemmatizer()
            self.detected_language = 'english'
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the text"""
        try:
            # Use a sample of the text for detection
            sample_text = text[:1000] if len(text) > 1000 else text
            detected = detect(sample_text)
            
            # Map detected language to our supported languages
            if detected in ['fr', 'fra']:
                return 'french'
            elif detected in ['en', 'eng']:
                return 'english'
            else:
                # Default to English for unsupported languages
                return 'english'
                
        except LangDetectException:
            return 'english'
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text based on detected language"""
        if self.language == 'auto':
            detected_lang = self.detect_language(text)
            if detected_lang != self.detected_language:
                self._initialize_language(detected_lang)
        
        return text
    
    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text for topic modeling"""
        # Preprocess text for language detection
        text = self._preprocess_text(text)
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces (preserve French accents)
        if self.detected_language == 'french':
            text = re.sub(r'[^a-zA-ZÀ-ÿ\s]', ' ', text)
        else:
            text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def extract_keywords(self, text: str, top_n: int = 20) -> List[Tuple[str, float]]:
        """Extract keywords using TF-IDF"""
        try:
            # Preprocess text
            processed_text = self.preprocess_text(text)
            
            # Create a more lenient vectorizer for single documents
            single_doc_vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                stop_words=list(self.stop_words),
                ngram_range=(1, 2),
                min_df=1,  # Allow single occurrence
                max_df=1.0  # Allow all terms
            )
            
            # Vectorize
            tfidf_matrix = single_doc_vectorizer.fit_transform([processed_text])
            feature_names = single_doc_vectorizer.get_feature_names_out()
            
            # Get TF-IDF scores
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # Create keyword-score pairs
            keywords = list(zip(feature_names, tfidf_scores))
            
            # Sort by score and return top N
            keywords.sort(key=lambda x: x[1], reverse=True)
            return keywords[:top_n]
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []
    
    def train_lda_model(self, texts: List[str], num_topics: Optional[int] = None) -> Dict:
        """Train LDA topic model"""
        if not texts:
            logger.warning("No texts provided for LDA training")
            return {}
        
        try:
            num_topics = num_topics or self.num_topics
            
            # Preprocess texts
            processed_texts = [self.preprocess_text(text) for text in texts]
            
            # Vectorize
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(processed_texts)
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            
            # Train LDA
            self.lda_model = LatentDirichletAllocation(
                n_components=num_topics,
                random_state=42,
                max_iter=20,
                learning_method='batch'
            )
            
            lda_output = self.lda_model.fit_transform(tfidf_matrix)
            
            # Extract topics
            topics = self._extract_lda_topics(feature_names)
            
            return {
                'model': self.lda_model,
                'vectorizer': self.tfidf_vectorizer,
                'topics': topics,
                'document_topics': lda_output
            }
            
        except Exception as e:
            logger.error(f"Error training LDA model: {e}")
            return {}
    
    def train_nmf_model(self, texts: List[str], num_topics: Optional[int] = None) -> Dict:
        """Train NMF topic model"""
        if not texts:
            logger.warning("No texts provided for NMF training")
            return {}
        
        try:
            num_topics = num_topics or self.num_topics
            
            # Preprocess texts
            processed_texts = [self.preprocess_text(text) for text in texts]
            
            # Vectorize
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(processed_texts)
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            
            # Train NMF
            self.nmf_model = NMF(
                n_components=num_topics,
                random_state=42,
                max_iter=200
            )
            
            nmf_output = self.nmf_model.fit_transform(tfidf_matrix)
            
            # Extract topics
            topics = self._extract_nmf_topics(feature_names)
            
            return {
                'model': self.nmf_model,
                'vectorizer': self.tfidf_vectorizer,
                'topics': topics,
                'document_topics': nmf_output
            }
            
        except Exception as e:
            logger.error(f"Error training NMF model: {e}")
            return {}
    
    def _extract_lda_topics(self, feature_names: np.ndarray, top_n: int = 10) -> List[Dict]:
        """Extract topics from LDA model"""
        topics = []
        
        for topic_idx, topic in enumerate(self.lda_model.components_):
            top_words_idx = topic.argsort()[-top_n:][::-1]
            top_words = [feature_names[i] for i in top_words_idx]
            top_weights = [topic[i] for i in top_words_idx]
            
            topics.append({
                'topic_id': topic_idx,
                'words': top_words,
                'weights': top_weights,
                'topic_name': self._generate_topic_name(top_words)
            })
        
        return topics
    
    def _extract_nmf_topics(self, feature_names: np.ndarray, top_n: int = 10) -> List[Dict]:
        """Extract topics from NMF model"""
        topics = []
        
        for topic_idx, topic in enumerate(self.nmf_model.components_):
            top_words_idx = topic.argsort()[-top_n:][::-1]
            top_words = [feature_names[i] for i in top_words_idx]
            top_weights = [topic[i] for i in top_words_idx]
            
            topics.append({
                'topic_id': topic_idx,
                'words': top_words,
                'weights': top_weights,
                'topic_name': self._generate_topic_name(top_words)
            })
        
        return topics
    
    def _generate_topic_name(self, words: List[str]) -> str:
        """Generate a human-readable name for a topic"""
        # Use the top 3 words to create a topic name
        top_words = words[:3]
        return " & ".join(top_words).title()
    
    def get_document_topics(self, text: str, model_type: str = 'lda') -> List[Tuple[str, float]]:
        """Get topic distribution for a single document"""
        try:
            # Preprocess text
            processed_text = self.preprocess_text(text)
            
            # Vectorize
            if model_type == 'lda' and self.lda_model is not None:
                vectorizer = self.tfidf_vectorizer
                model = self.lda_model
            elif model_type == 'nmf' and self.nmf_model is not None:
                vectorizer = self.tfidf_vectorizer
                model = self.nmf_model
            else:
                logger.warning(f"No {model_type.upper()} model available")
                return []
            
            # Transform text
            text_vector = vectorizer.transform([processed_text])
            topic_distribution = model.transform(text_vector)[0]
            
            # Create topic-score pairs
            topics = []
            for i, score in enumerate(topic_distribution):
                if score > 0.01:  # Only include topics with significant weight
                    topic_name = f"Topic {i+1}"
                    topics.append((topic_name, float(score)))
            
            # Sort by score
            topics.sort(key=lambda x: x[1], reverse=True)
            return topics
            
        except Exception as e:
            logger.error(f"Error getting document topics: {e}")
            return []
    
    def extract_book_topics(self, text: str, metadata: Dict) -> Dict[str, any]:
        """Extract tags from a book using the unified TagClassifier.

        Returns a dict that preserves previous keys (derived from tags) for
        compatibility, plus explicit primary/secondary tags and detailed scores.
        """
        # Keywords extracted from EPUB text (a)
        keywords = self.extract_keywords(text, top_n=15)

        # Tag classification (LLM-based)
        tags_primary = 'Unknown'
        tags_secondary: List[str] = []
        tags_detailed: List[Tuple[str, float]] = []
        tags_list: List[str] = []

        try:
            if self.llm_classifier is not None:
                title = metadata.get('title') or ''
                description = metadata.get('description') or ''
                subjects = metadata.get('subjects') or []
                results = self.llm_classifier.classify(
                    title=title,
                    description=description,
                    subjects=subjects,
                    text=text or '',
                )
                if results:
                    # Sort by score already; pick primary and a few secondary
                    tags_detailed = [(r.tag, float(r.score)) for r in results]
                    non_zero = [r for r in results if r.score > 0.05]
                    if non_zero:
                        tags_primary = non_zero[0].tag
                        tags_secondary = [r.tag for r in non_zero[1:6]]
                        tags_list = [tags_primary] + tags_secondary
                    else:
                        tags_list = []
                else:
                    # If due to rate limiting, signal upstream to optionally skip saving
                    tags_detailed = [(t, 0.0) for t in (AUTHORIZED_TAGS or [])]
                    tags_list = []
            else:
                logger.warning("LLM tag classifier not available; no tags will be produced")
        except Exception as e:
            logger.warning(f"Tag classification failed: {e}")

        # Analyze topic coherence on keywords (unchanged)
        topic_coherence = self._calculate_topic_coherence(keywords)

        # Preserve legacy-shaped fields but tie them to unified tags for compatibility
        themes_with_scores = tags_detailed
        main_themes = tags_list
        primary_topic = tags_primary if tags_primary else 'Unknown'
        secondary_topics = tags_secondary

        return {
            # (a) Keywords extracted from EPUB
            'keywords': keywords,
            # Unified tags used as topics
            'tags': tags_list,
            'tags_primary': primary_topic,
            'tags_secondary': secondary_topics,
            # Full score vector for all tags (ordered by vocabulary definition)
            'tags_detailed': themes_with_scores,
            # Legacy-compatible fields
            'main_themes': main_themes,
            'themes_with_scores': themes_with_scores,
            'primary_topic': primary_topic,
            'primary_confidence': themes_with_scores[0][1] if themes_with_scores else 0.0,
            'secondary_topics': secondary_topics,
            'secondary_confidences': [score for _, score in themes_with_scores[1:4]] if len(themes_with_scores) > 1 else [],
            'lda_topics': [],
            'nmf_topics': [],
            'topic_coherence': topic_coherence,
        }
    
    # Legacy theme extraction removed
    
    def _calculate_topic_coherence(self, keywords: List[Tuple[str, float]]) -> float:
        """Calculate topic coherence score"""
        if not keywords:
            return 0.0
        
        # Simple coherence based on score distribution
        scores = [score for _, score in keywords]
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        
        # Higher coherence if scores are more uniform
        coherence = 1.0 - (std_score / mean_score) if mean_score > 0 else 0.0
        return min(coherence, 1.0)
    
    def analyze_collection_topics(self, books: List[Dict]) -> Dict[str, any]:
        """Analyze topics across the entire collection"""
        all_keywords = []
        all_themes = []
        
        for book in books:
            topics = book.get('topics', {})
            all_keywords.extend(topics.get('keywords', []))
            all_themes.extend(topics.get('main_themes', []))
        
        # Aggregate keyword frequencies
        keyword_freq = Counter()
        for word, score in all_keywords:
            keyword_freq[word] += score
        
        # Most common keywords
        top_keywords = keyword_freq.most_common(20)
        
        # Theme distribution
        theme_freq = Counter(all_themes)
        top_themes = theme_freq.most_common(10)
        
        return {
            'top_keywords': top_keywords,
            'top_themes': top_themes,
            'total_books': len(books),
            'unique_keywords': len(keyword_freq),
            'unique_themes': len(theme_freq)
        }
    
    def find_similar_books_by_topics(self, target_book: Dict, all_books: List[Dict], top_n: int = 5) -> List[Tuple[Dict, float]]:
        """Find books with similar topics"""
        target_topics = target_book.get('topics', {})
        target_keywords = set(word for word, _ in target_topics.get('keywords', []))
        
        similarities = []
        
        for book in all_books:
            if book['id'] == target_book['id']:
                continue
            
            book_topics = book.get('topics', {})
            book_keywords = set(word for word, _ in book_topics.get('keywords', []))
            
            # Calculate Jaccard similarity
            intersection = len(target_keywords & book_keywords)
            union = len(target_keywords | book_keywords)
            
            similarity = intersection / union if union > 0 else 0.0
            similarities.append((book, similarity))
        
        # Sort by similarity and return top N
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]
