"""
Recommendation System Module

This module provides book recommendation capabilities using content-based filtering,
collaborative filtering, and hybrid approaches.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class BookRecommender:
    """Advanced book recommendation system"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        self.similarity_matrix = None
        self.book_features = None
        self.book_ids = None
        
    def create_content_similarity_matrix(self, books: List[Dict]) -> np.ndarray:
        """Create similarity matrix based on book content"""
        try:
            # Extract text content for vectorization
            texts = []
            self.book_ids = []
            
            for book in books:
                text = book.get('full_text', '')
                if text:
                    texts.append(text)
                    self.book_ids.append(book.get('id', book.get('title', '')))
            
            if not texts:
                logger.warning("No text content available for similarity calculation")
                return np.array([])
            
            # Create TF-IDF vectors
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Calculate cosine similarity
            self.similarity_matrix = cosine_similarity(tfidf_matrix)
            
            logger.info(f"Created similarity matrix for {len(books)} books")
            return self.similarity_matrix
            
        except Exception as e:
            logger.error(f"Error creating similarity matrix: {e}")
            return np.array([])
    
    def get_content_based_recommendations(self, book_id: str, top_n: int = 5) -> List[Tuple[Dict, float]]:
        """Get content-based recommendations for a book"""
        if self.similarity_matrix is None or self.book_ids is None:
            return []
        
        try:
            # Find book index
            if book_id not in self.book_ids:
                logger.warning(f"Book ID {book_id} not found in similarity matrix")
                return []
            
            book_idx = self.book_ids.index(book_id)
            
            # Get similarity scores for this book
            similarities = self.similarity_matrix[book_idx]
            
            # Create book-similarity pairs
            book_similarities = []
            for i, similarity in enumerate(similarities):
                if i != book_idx and similarity > 0:  # Exclude self and zero similarities
                    book_similarities.append((self.book_ids[i], similarity))
            
            # Sort by similarity and return top N
            book_similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Convert to book objects (you'll need to pass the books list)
            recommendations = []
            for book_id, similarity in book_similarities[:top_n]:
                # This would need the actual book objects
                recommendations.append(({'id': book_id}, similarity))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting content-based recommendations: {e}")
            return []
    
    def get_hybrid_recommendations(self, book: Dict, all_books: List[Dict], 
                                 content_weight: float = 0.6, 
                                 genre_weight: float = 0.2,
                                 topic_weight: float = 0.2,
                                 top_n: int = 10) -> List[Tuple[Dict, float]]:
        """Get hybrid recommendations combining multiple factors"""
        try:
            recommendations = {}
            
            # Content similarity
            content_similarities = self._calculate_content_similarity(book, all_books)
            for book_id, similarity in content_similarities:
                recommendations[book_id] = similarity * content_weight
            
            # Genre similarity
            genre_similarities = self._calculate_genre_similarity(book, all_books)
            for book_id, similarity in genre_similarities:
                if book_id in recommendations:
                    recommendations[book_id] += similarity * genre_weight
                else:
                    recommendations[book_id] = similarity * genre_weight
            
            # Topic similarity
            topic_similarities = self._calculate_topic_similarity(book, all_books)
            for book_id, similarity in topic_similarities:
                if book_id in recommendations:
                    recommendations[book_id] += similarity * topic_weight
                else:
                    recommendations[book_id] = similarity * topic_weight
            
            # Convert to list and sort
            recommendation_list = []
            for book_id, score in recommendations.items():
                if book_id != book.get('id'):
                    recommendation_list.append((book_id, score))
            
            recommendation_list.sort(key=lambda x: x[1], reverse=True)
            
            # Convert to book objects
            final_recommendations = []
            for book_id, score in recommendation_list[:top_n]:
                target_book = next((b for b in all_books if b.get('id') == book_id), None)
                if target_book:
                    final_recommendations.append((target_book, score))
            
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Error getting hybrid recommendations: {e}")
            return []
    
    def _calculate_content_similarity(self, book: Dict, all_books: List[Dict]) -> List[Tuple[str, float]]:
        """Calculate content similarity between books"""
        similarities = []
        book_text = book.get('full_text', '')
        
        if not book_text:
            return similarities
        
        for other_book in all_books:
            if other_book.get('id') == book.get('id'):
                continue
            
            other_text = other_book.get('full_text', '')
            if not other_text:
                continue
            
            # Simple text similarity using word overlap
            book_words = set(book_text.lower().split())
            other_words = set(other_text.lower().split())
            
            if book_words and other_words:
                intersection = len(book_words & other_words)
                union = len(book_words | other_words)
                similarity = intersection / union if union > 0 else 0.0
                similarities.append((other_book.get('id'), similarity))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)
    
    def _calculate_genre_similarity(self, book: Dict, all_books: List[Dict]) -> List[Tuple[str, float]]:
        """Calculate genre similarity between books"""
        similarities = []
        book_genre = book.get('primary_genre', '')
        
        if not book_genre:
            return similarities
        
        for other_book in all_books:
            if other_book.get('id') == book.get('id'):
                continue
            
            other_genre = other_book.get('primary_genre', '')
            if not other_genre:
                continue
            
            # Exact genre match
            if book_genre == other_genre:
                similarities.append((other_book.get('id'), 1.0))
            # Check secondary genres
            elif other_genre in book.get('secondary_genres', []):
                similarities.append((other_book.get('id'), 0.7))
            elif book_genre in other_book.get('secondary_genres', []):
                similarities.append((other_book.get('id'), 0.7))
            else:
                similarities.append((other_book.get('id'), 0.0))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)
    
    def _calculate_topic_similarity(self, book: Dict, all_books: List[Dict]) -> List[Tuple[str, float]]:
        """Calculate topic similarity between books"""
        similarities = []
        book_topics = book.get('topics', {})
        book_keywords = set(word for word, _ in book_topics.get('keywords', []))
        
        if not book_keywords:
            return similarities
        
        for other_book in all_books:
            if other_book.get('id') == book.get('id'):
                continue
            
            other_topics = other_book.get('topics', {})
            other_keywords = set(word for word, _ in other_topics.get('keywords', []))
            
            if other_keywords:
                intersection = len(book_keywords & other_keywords)
                union = len(book_keywords | other_keywords)
                similarity = intersection / union if union > 0 else 0.0
                similarities.append((other_book.get('id'), similarity))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)
    
    def get_personalized_recommendations(self, user_preferences: Dict, 
                                       all_books: List[Dict],
                                       top_n: int = 10) -> List[Tuple[Dict, float]]:
        """Get personalized recommendations based on user preferences"""
        try:
            recommendations = {}
            
            # Extract user preferences
            preferred_genres = user_preferences.get('genres', [])
            preferred_topics = user_preferences.get('topics', [])
            preferred_authors = user_preferences.get('authors', [])
            preferred_complexity = user_preferences.get('complexity_level', 'difficulty_moderate')
            
            for book in all_books:
                score = 0.0
                
                # Genre preference
                if book.get('primary_genre') in preferred_genres:
                    score += 2.0
                elif any(genre in preferred_genres for genre in book.get('secondary_genres', [])):
                    score += 1.0
                
                # Topic preference
                book_topics = book.get('topics', {})
                book_keywords = [word for word, _ in book_topics.get('keywords', [])]
                topic_matches = sum(1 for topic in preferred_topics if topic.lower() in ' '.join(book_keywords).lower())
                score += topic_matches * 0.5
                
                # Author preference
                if any(author in preferred_authors for author in book.get('authors', [])):
                    score += 1.5
                
                # Complexity preference
                book_complexity = book.get('complexity_level', 'difficulty_moderate')
                if book_complexity == preferred_complexity:
                    score += 0.5
                
                if score > 0:
                    recommendations[book.get('id')] = score
            
            # Sort by score
            sorted_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
            
            # Convert to book objects
            final_recommendations = []
            for book_id, score in sorted_recommendations[:top_n]:
                target_book = next((b for b in all_books if b.get('id') == book_id), None)
                if target_book:
                    final_recommendations.append((target_book, score))
            
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {e}")
            return []
    
    def get_diverse_recommendations(self, base_book: Dict, all_books: List[Dict],
                                  top_n: int = 10, diversity_factor: float = 0.3) -> List[Tuple[Dict, float]]:
        """Get diverse recommendations to avoid filter bubbles"""
        try:
            # Get initial recommendations
            initial_recommendations = self.get_hybrid_recommendations(base_book, all_books, top_n=top_n*2)
            
            if not initial_recommendations:
                return []
            
            # Apply diversity penalty
            diverse_recommendations = []
            selected_genres = set()
            selected_topics = set()
            
            for book, score in initial_recommendations:
                # Calculate diversity penalty
                genre_penalty = 0.0
                topic_penalty = 0.0
                
                if book.get('primary_genre') in selected_genres:
                    genre_penalty = diversity_factor
                
                book_topics = book.get('topics', {})
                book_keywords = [word for word, _ in book_topics.get('keywords', [])]
                topic_overlap = len(set(book_keywords) & selected_topics)
                topic_penalty = (topic_overlap / len(book_keywords)) * diversity_factor if book_keywords else 0.0
                
                # Apply penalties
                adjusted_score = score * (1.0 - genre_penalty - topic_penalty)
                
                diverse_recommendations.append((book, adjusted_score))
                
                # Update selected sets
                selected_genres.add(book.get('primary_genre'))
                selected_topics.update(book_keywords)
            
            # Sort by adjusted score
            diverse_recommendations.sort(key=lambda x: x[1], reverse=True)
            
            return diverse_recommendations[:top_n]
            
        except Exception as e:
            logger.error(f"Error getting diverse recommendations: {e}")
            return []
    
    def analyze_recommendation_quality(self, recommendations: List[Tuple[Dict, float]], 
                                     user_feedback: Dict) -> Dict[str, any]:
        """Analyze the quality of recommendations based on user feedback"""
        try:
            total_recommendations = len(recommendations)
            if total_recommendations == 0:
                return {'accuracy': 0.0, 'coverage': 0.0, 'diversity': 0.0}
            
            # Calculate accuracy (how many were liked)
            liked_count = 0
            for book, _ in recommendations:
                if user_feedback.get(book.get('id'), False):
                    liked_count += 1
            
            accuracy = liked_count / total_recommendations
            
            # Calculate coverage (how many different genres/topics covered)
            genres = set()
            topics = set()
            
            for book, _ in recommendations:
                genres.add(book.get('primary_genre', ''))
                book_topics = book.get('topics', {})
                topics.update(word for word, _ in book_topics.get('keywords', []))
            
            coverage = (len(genres) + len(topics)) / (total_recommendations * 2)
            
            # Calculate diversity (how different the recommendations are from each other)
            similarities = []
            for i, (book1, _) in enumerate(recommendations):
                for j, (book2, _) in enumerate(recommendations[i+1:], i+1):
                    # Simple similarity based on genre and topics
                    genre_sim = 1.0 if book1.get('primary_genre') == book2.get('primary_genre') else 0.0
                    topic_sim = self._calculate_topic_similarity_simple(book1, book2)
                    similarities.append((genre_sim + topic_sim) / 2)
            
            diversity = 1.0 - (sum(similarities) / len(similarities)) if similarities else 1.0
            
            return {
                'accuracy': accuracy,
                'coverage': coverage,
                'diversity': diversity,
                'total_recommendations': total_recommendations,
                'liked_count': liked_count,
                'genres_covered': len(genres),
                'topics_covered': len(topics)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing recommendation quality: {e}")
            return {'accuracy': 0.0, 'coverage': 0.0, 'diversity': 0.0}
    
    def _calculate_topic_similarity_simple(self, book1: Dict, book2: Dict) -> float:
        """Calculate simple topic similarity between two books"""
        topics1 = book1.get('topics', {})
        topics2 = book2.get('topics', {})
        
        keywords1 = set(word for word, _ in topics1.get('keywords', []))
        keywords2 = set(word for word, _ in topics2.get('keywords', []))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        
        return intersection / union if union > 0 else 0.0
