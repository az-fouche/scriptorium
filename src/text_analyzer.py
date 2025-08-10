"""
Text Analyzer Module

This module provides comprehensive text analysis including readability metrics,
sentiment analysis, writing style analysis, and linguistic features.
"""

import re
import string
from typing import Dict, List, Tuple, Counter
from collections import defaultdict
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
import textstat
import logging
import spacy
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')


class TextAnalyzer:
    """Advanced text analysis for books with multi-language support"""
    
    def __init__(self, language: str = 'auto'):
        self.language = language
        self.detected_language = None
        
        # Initialize language-specific components
        self.stop_words = set()
        self.lemmatizer = None
        self.punctuation = set(string.punctuation)
        
        # spaCy models for different languages
        self.nlp_models = {}
        
        # Initialize readability formulas
        self.readability_formulas = {
            'flesch_reading_ease': textstat.flesch_reading_ease,
            'flesch_kincaid_grade': textstat.flesch_kincaid_grade,
            'gunning_fog': textstat.gunning_fog,
            'smog_index': textstat.smog_index,
            'automated_readability_index': textstat.automated_readability_index,
            'coleman_liau_index': textstat.coleman_liau_index,
            'linsear_write_formula': textstat.linsear_write_formula,
            'dale_chall_readability_score': textstat.dale_chall_readability_score
        }
        
        # Initialize with English as default
        self._initialize_language('english')
    
    def _initialize_language(self, language: str):
        """Initialize language-specific components"""
        try:
            # Load stop words for the language
            if language == 'french':
                self.stop_words = set(stopwords.words('french'))
                # For French, we'll use spaCy for lemmatization
                if 'fr_core_news_sm' not in self.nlp_models:
                    try:
                        self.nlp_models['fr_core_news_sm'] = spacy.load('fr_core_news_sm')
                    except OSError:
                        logger.warning("French spaCy model not found. Install with: python -m spacy download fr_core_news_sm")
                        self.nlp_models['fr_core_news_sm'] = None
            else:
                self.stop_words = set(stopwords.words('english'))
                self.lemmatizer = WordNetLemmatizer()
                
            self.detected_language = language
            logger.info(f"Initialized text analyzer for {language}")
            
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
    
    def analyze_readability(self, text: str) -> Dict[str, float]:
        """Calculate various readability metrics"""
        try:
            readability_scores = {}
            
            for formula_name, formula_func in self.readability_formulas.items():
                try:
                    score = formula_func(text)
                    readability_scores[formula_name] = score
                except Exception as e:
                    logger.warning(f"Could not calculate {formula_name}: {e}")
                    readability_scores[formula_name] = 0.0
            
            return readability_scores
            
        except Exception as e:
            logger.error(f"Error calculating readability: {e}")
            return {formula_name: 0.0 for formula_name in self.readability_formulas.keys()}
    
    def analyze_vocabulary(self, text: str) -> Dict[str, any]:
        """Analyze vocabulary complexity and diversity"""
        # Preprocess text for language detection
        text = self._preprocess_text(text)
        
        # Tokenize and clean words
        if self.detected_language == 'french' and 'fr_core_news_sm' in self.nlp_models and self.nlp_models['fr_core_news_sm']:
            # Use spaCy for French tokenization and lemmatization
            doc = self.nlp_models['fr_core_news_sm'](text.lower())
            words = [token.lemma_ for token in doc if token.is_alpha and not token.is_stop]
        else:
            # Use NLTK for English
            words = word_tokenize(text.lower())
            words = [word for word in words if word.isalpha() and word not in self.stop_words]
        
        if not words:
            return {
                'unique_words': 0,
                'total_words': 0,
                'vocabulary_diversity': 0.0,
                'average_word_length': 0.0,
                'long_words_ratio': 0.0,
                'complex_words_ratio': 0.0,
                'language': self.detected_language
            }
        
        # Calculate vocabulary metrics
        unique_words = len(set(words))
        total_words = len(words)
        vocabulary_diversity = unique_words / total_words if total_words > 0 else 0
        
        # Word length analysis
        word_lengths = [len(word) for word in words]
        average_word_length = sum(word_lengths) / len(word_lengths)
        
        # Long words (6+ characters for French, 6+ for English)
        long_words = [word for word in words if len(word) >= 6]
        long_words_ratio = len(long_words) / total_words if total_words > 0 else 0
        
        # Complex words (3+ syllables)
        complex_words = [word for word in words if textstat.syllable_count(word) >= 3]
        complex_words_ratio = len(complex_words) / total_words if total_words > 0 else 0
        
        return {
            'unique_words': unique_words,
            'total_words': total_words,
            'vocabulary_diversity': vocabulary_diversity,
            'average_word_length': average_word_length,
            'long_words_ratio': long_words_ratio,
            'complex_words_ratio': complex_words_ratio,
            'language': self.detected_language
        }
    
    def analyze_sentence_structure(self, text: str) -> Dict[str, float]:
        """Analyze sentence structure and complexity"""
        sentences = sent_tokenize(text)
        
        if not sentences:
            return {
                'average_sentence_length': 0.0,
                'sentence_length_variance': 0.0,
                'short_sentences_ratio': 0.0,
                'long_sentences_ratio': 0.0,
                'very_long_sentences_ratio': 0.0
            }
        
        # Calculate sentence lengths
        sentence_lengths = [len(word_tokenize(sent)) for sent in sentences]
        average_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
        
        # Calculate variance
        variance = sum((length - average_sentence_length) ** 2 for length in sentence_lengths) / len(sentence_lengths)
        
        # Categorize sentences
        short_sentences = len([l for l in sentence_lengths if l <= 10])
        long_sentences = len([l for l in sentence_lengths if 10 < l <= 25])
        very_long_sentences = len([l for l in sentence_lengths if l > 25])
        
        total_sentences = len(sentence_lengths)
        
        return {
            'average_sentence_length': average_sentence_length,
            'sentence_length_variance': variance,
            'short_sentences_ratio': short_sentences / total_sentences,
            'long_sentences_ratio': long_sentences / total_sentences,
            'very_long_sentences_ratio': very_long_sentences / total_sentences
        }
    
    def analyze_writing_style(self, text: str) -> Dict[str, any]:
        """Analyze writing style characteristics"""
        # Paragraph analysis
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Dialogue analysis
        dialogue_pattern = r'["""][^"""]*["""]'
        dialogue_matches = re.findall(dialogue_pattern, text)
        dialogue_ratio = len(' '.join(dialogue_matches)) / len(text) if text else 0
        
        # Question and exclamation analysis
        questions = len(re.findall(r'\?', text))
        exclamations = len(re.findall(r'!', text))
        
        # Parenthetical expressions
        parentheses = len(re.findall(r'\([^)]*\)', text))
        
        # Capitalization analysis
        words = word_tokenize(text)
        capitalized_words = [word for word in words if word.isupper() and len(word) > 1]
        capitalization_ratio = len(capitalized_words) / len(words) if words else 0
        
        return {
            'paragraph_count': len(paragraphs),
            'average_paragraph_length': sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
            'dialogue_ratio': dialogue_ratio,
            'questions_count': questions,
            'exclamations_count': exclamations,
            'parentheses_count': parentheses,
            'capitalization_ratio': capitalization_ratio
        }
    
    def extract_keywords(self, text: str, top_n: int = 20) -> List[Tuple[str, int]]:
        """Extract most frequent keywords from text"""
        # Preprocess text for language detection
        text = self._preprocess_text(text)
        
        # Tokenize and clean based on language
        if self.detected_language == 'french' and 'fr_core_news_sm' in self.nlp_models and self.nlp_models['fr_core_news_sm']:
            # Use spaCy for French tokenization and lemmatization
            doc = self.nlp_models['fr_core_news_sm'](text.lower())
            words = [token.lemma_ for token in doc if token.is_alpha and not token.is_stop and len(token.lemma_) > 2]
        else:
            # Use NLTK for English
            words = word_tokenize(text.lower())
            words = [word for word in words if word.isalpha() and word not in self.stop_words and len(word) > 2]
        
        # Count frequencies
        word_freq = Counter(words)
        
        # Return top N keywords
        return word_freq.most_common(top_n)
    
    def analyze_text_complexity(self, text: str) -> Dict[str, any]:
        """Comprehensive text complexity analysis"""
        readability = self.analyze_readability(text)
        vocabulary = self.analyze_vocabulary(text)
        sentence_structure = self.analyze_sentence_structure(text)
        writing_style = self.analyze_writing_style(text)
        
        # Calculate overall complexity score
        complexity_factors = [
            readability.get('flesch_kincaid_grade', 0),
            vocabulary.get('complex_words_ratio', 0) * 100,
            sentence_structure.get('very_long_sentences_ratio', 0) * 100,
            vocabulary.get('average_word_length', 0) * 10
        ]
        
        overall_complexity = sum(complexity_factors) / len(complexity_factors)
        
        return {
            'readability': readability,
            'vocabulary': vocabulary,
            'sentence_structure': sentence_structure,
            'writing_style': writing_style,
            'overall_complexity_score': overall_complexity,
            'complexity_level': self._get_complexity_level(overall_complexity)
        }
    
    def _get_complexity_level(self, score: float) -> str:
        """Convert complexity score to human-readable level"""
        if score < 30:
            return "difficulty_very_easy"
        elif score < 50:
            return "difficulty_easy"
        elif score < 70:
            return "difficulty_moderate"
        elif score < 90:
            return "difficulty_hard"
        else:
            return "difficulty_very_hard"
    
    def get_reading_level(self, text: str) -> str:
        """Get recommended reading level based on text analysis"""
        try:
            flesch_grade = textstat.flesch_kincaid_grade(text)
            
            if flesch_grade <= 6:
                return "reading_level_elementary"
            elif flesch_grade <= 8:
                return "reading_level_middle_school"
            elif flesch_grade <= 12:
                return "reading_level_high_school"
            elif flesch_grade <= 16:
                return "reading_level_college"
            else:
                return "reading_level_graduate"
                
        except Exception as e:
            logger.error(f"Error calculating reading level: {e}")
            return "common.unknown"
    
    def analyze_chapter_distribution(self, chapters: List[Dict[str, str]]) -> Dict[str, any]:
        """Analyze chapter length distribution and patterns"""
        if not chapters:
            return {}
        
        chapter_lengths = [chapter.get('word_count', 0) for chapter in chapters]
        
        if not chapter_lengths:
            return {}
        
        total_words = sum(chapter_lengths)
        average_chapter_length = total_words / len(chapter_lengths)
        
        # Find longest and shortest chapters
        max_length = max(chapter_lengths)
        min_length = min(chapter_lengths)
        
        # Calculate variance
        variance = sum((length - average_chapter_length) ** 2 for length in chapter_lengths) / len(chapter_lengths)
        
        return {
            'total_chapters': len(chapters),
            'total_words': total_words,
            'average_chapter_length': average_chapter_length,
            'longest_chapter_words': max_length,
            'shortest_chapter_words': min_length,
            'chapter_length_variance': variance,
            'chapter_length_std': variance ** 0.5
        }
