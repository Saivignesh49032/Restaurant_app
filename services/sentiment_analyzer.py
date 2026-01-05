"""
Sentiment Analyzer Service
Analyzes restaurant reviews using LOCAL AI model (HuggingFace transformers)
No API costs, works offline!
"""
from .local_sentiment_model import local_sentiment_analyzer
import json
import re


class SentimentAnalyzer:
    """Service for analyzing sentiment and extracting insights from reviews"""
    
    def analyze_reviews(self, reviews):
        """
        Analyze multiple reviews and generate comprehensive insights
        
        Args:
            reviews: List of review dicts with 'text' and 'rating' fields
            
        Returns:
            dict: Complete analysis results
        """
        if not reviews:
            return self._empty_analysis()
        
        # Prepare review texts
        review_texts = [r.get('text', '') for r in reviews if r.get('text')]
        
        if not review_texts:
            return self._empty_analysis()
        
        # Analyze using LOCAL AI model
        try:
            analysis = local_sentiment_analyzer.analyze_reviews(reviews)
            return analysis
        except Exception as e:
            print(f"Error in local sentiment analysis: {str(e)}")
            return self._fallback_analysis(reviews)
    
    def _fallback_analysis(self, reviews):
        """Simple keyword-based analysis as fallback"""
        
        positive_count = sum(1 for r in reviews if r.get('rating', 0) >= 4)
        negative_count = sum(1 for r in reviews if r.get('rating', 0) <= 2)
        neutral_count = len(reviews) - positive_count - negative_count
        
        total = len(reviews)
        
        return {
            'overall_sentiment': 'positive' if positive_count > negative_count else 'negative' if negative_count > positive_count else 'neutral',
            'sentiment_percentages': {
                'positive': round((positive_count / total) * 100) if total > 0 else 0,
                'neutral': round((neutral_count / total) * 100) if total > 0 else 0,
                'negative': round((negative_count / total) * 100) if total > 0 else 0
            },
            'top_topics': ['Food Quality', 'Service', 'Ambience'],
            'positive_highlights': ['Good food', 'Friendly staff'],
            'negative_highlights': ['Slow service'] if negative_count > 0 else [],
            'best_items': [],
            'common_complaints': [],
            'ai_summary': f'Based on {total} reviews, customers have a generally {"positive" if positive_count > negative_count else "mixed"} experience.',
            'ai_recommendations': 'Try visiting during off-peak hours for better service.',
            'review_count': total,
            'review_source_used': 'Google Places API',
            'analyzed_at': None,
            'fallback_used': True
        }
    
    def _empty_analysis(self):
        """Return empty analysis structure"""
        return {
            'overall_sentiment': 'neutral',
            'sentiment_percentages': {
                'positive': 0,
                'neutral': 0,
                'negative': 0
            },
            'top_topics': [],
            'positive_highlights': [],
            'negative_highlights': [],
            'best_items': [],
            'common_complaints': [],
            'ai_summary': 'No reviews available for this restaurant yet.',
            'ai_recommendations': 'Be the first to review this restaurant!',
            'review_count': 0,
            'review_source_used': 'None',
            'analyzed_at': None
        }
    
    def analyze_single_review(self, review_text):
        """Analyze a single review for sentiment"""
        
        try:
            result = local_sentiment_analyzer.analyze_single_review(review_text)
            return result
            
        except Exception as e:
            print(f"Error analyzing single review: {str(e)}")
        
        return {
            'sentiment': 'neutral',
            'confidence': 0.5,
            'topics': [],
            'mentioned_items': []
        }
