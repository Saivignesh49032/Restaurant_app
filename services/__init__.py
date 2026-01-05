# Services package
from .review_fetcher import ReviewFetcher
from .sentiment_analyzer import SentimentAnalyzer
from .cache_manager import CacheManager
from .local_sentiment_model import LocalSentimentAnalyzer, local_sentiment_analyzer

# Enhanced ML Analytics (CPU-Optimized)
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from ml_analytics_enhanced import (
        get_sentiment_analyzer as get_enhanced_sentiment,
        get_dish_extractor,
        get_review_summarizer,
        get_topic_extractor,
        get_fake_detector
    )
    ENHANCED_ML_AVAILABLE = True
except ImportError:
    ENHANCED_ML_AVAILABLE = False
    print("⚠️ Enhanced ML analytics not available")

__all__ = [
    'ReviewFetcher', 'SentimentAnalyzer', 'CacheManager', 
    'LocalSentimentAnalyzer', 'local_sentiment_analyzer',
    'ENHANCED_ML_AVAILABLE', 'get_enhanced_sentiment', 'get_dish_extractor',
    'get_review_summarizer', 'get_topic_extractor', 'get_fake_detector'
]
