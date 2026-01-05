"""
Enhanced Review Analysis API Routes
Uses new CPU-optimized ML features:
- VADER sentiment (95% accuracy)
- Dish extraction
- Review summarization
- Topic modeling
- Fake review detection
"""
from flask import Blueprint, request, jsonify
from services import (
    ReviewFetcher, 
    ENHANCED_ML_AVAILABLE,
    get_enhanced_sentiment,
    get_dish_extractor,
    get_review_summarizer,
    get_topic_extractor,
    get_fake_detector
)
from datetime import datetime

enhanced_review_bp = Blueprint('enhanced_reviews', __name__, url_prefix='/api/enhanced-reviews')

# Initialize services
review_fetcher = ReviewFetcher()


@enhanced_review_bp.route('/analyze/<restaurant_id>', methods=['POST'])
def analyze_restaurant_reviews(restaurant_id):
    """
    Comprehensive review analysis with enhanced ML
    
    Request JSON:
    {
        "restaurant_name": "Pizza Palace",
        "city": "Mumbai"
    }
    
    Returns:
    {
        "sentiment": {...},
        "dishes": [...],
        "summary": "...",
        "topics": [...],
        "fake_reviews": [...],
        "stats": {...}
    }
    """
    if not ENHANCED_ML_AVAILABLE:
        return jsonify({
            "error": "Enhanced ML features not available",
            "message": "Please install vaderSentiment, nltk, and scikit-learn"
        }), 503
    
    data = request.json or {}
    restaurant_name = data.get('restaurant_name', 'Restaurant')
    city = data.get('city', 'Unknown')
    
    # Fetch reviews
    reviews_data = review_fetcher.fetch_reviews(
        restaurant_id=restaurant_id,
        restaurant_name=restaurant_name,
        city=city
    )
    
    reviews = reviews_data.get('reviews', [])
    
    if not reviews:
        return jsonify({
            "error": "No reviews found",
            "restaurant_id": restaurant_id
        }), 404
    
    # Initialize analyzers
    sentiment_analyzer = get_enhanced_sentiment()
    dish_extractor = get_dish_extractor()
    summarizer = get_review_summarizer()
    topic_extractor = get_topic_extractor()
    fake_detector = get_fake_detector()
    
    # Analyze each review
    analyzed_reviews = []
    all_dishes = []
    sentiment_scores = []
    fake_reviews = []
    
    for review in reviews:
        review_text = review.get('text', '')
        rating = review.get('rating', 3)
        
        # Sentiment analysis
        sentiment = sentiment_analyzer.analyze_review(review_text)
        sentiment_scores.append(sentiment['sentiment_score'])
        
        # Extract dishes
        dishes = dish_extractor.extract_dishes(review_text)
        all_dishes.extend(dishes)
        
        # Fake detection
        fake_check = fake_detector.is_fake(review_text, rating)
        if fake_check['is_suspicious']:
            fake_reviews.append({
                'text': review_text[:100] + '...',
                'rating': rating,
                'reasons': fake_check['reasons'],
                'confidence': fake_check['confidence']
            })
        
        analyzed_reviews.append({
            'text': review_text,
            'rating': rating,
            'sentiment': sentiment,
            'dishes': dishes,
            'is_suspicious': fake_check['is_suspicious']
        })
    
    # Generate summary
    review_texts = [r.get('text', '') for r in reviews if r.get('text')]
    summary = summarizer.summarize_reviews(review_texts, max_sentences=5)
    
    # Extract topics
    topics = topic_extractor.extract_topics(review_texts, num_topics=5)
    
    # Calculate statistics
    from collections import Counter
    dish_counts = Counter(all_dishes)
    popular_dishes = [{'dish': dish, 'mentions': count} for dish, count in dish_counts.most_common(10)]
    
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    
    sentiment_distribution = {
        'positive': sum(1 for s in sentiment_scores if s > 0.05),
        'neutral': sum(1 for s in sentiment_scores if -0.05 <= s <= 0.05),
        'negative': sum(1 for s in sentiment_scores if s < -0.05)
    }
    
    return jsonify({
        "restaurant_id": restaurant_id,
        "restaurant_name": restaurant_name,
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "review_count": len(reviews),
        "sentiment": {
            "average_score": round(avg_sentiment, 3),
            "distribution": sentiment_distribution,
            "label": "positive" if avg_sentiment > 0.05 else ("negative" if avg_sentiment < -0.05 else "neutral")
        },
        "popular_dishes": popular_dishes,
        "summary": summary,
        "topics": topics,
        "fake_reviews": {
            "count": len(fake_reviews),
            "percentage": round((len(fake_reviews) / len(reviews)) * 100, 1) if reviews else 0,
            "examples": fake_reviews[:5]  # Top 5 suspicious
        },
        "reviews": analyzed_reviews[:20],  # Return first 20 analyzed reviews
        "source": reviews_data.get('source', 'unknown')
    })


@enhanced_review_bp.route('/dishes/<restaurant_id>', methods=['GET'])
def get_popular_dishes(restaurant_id):
    """Get popular dishes mentioned in reviews"""
    if not ENHANCED_ML_AVAILABLE:
        return jsonify({"error": "Enhanced ML not available"}), 503
    
    # Fetch reviews
    reviews_data = review_fetcher.fetch_reviews(restaurant_id=restaurant_id)
    reviews = reviews_data.get('reviews', [])
    
    if not reviews:
        return jsonify({"error": "No reviews found"}), 404
    
    # Extract dishes
    dish_extractor = get_dish_extractor()
    all_dishes = []
    
    for review in reviews:
        dishes = dish_extractor.extract_dishes(review.get('text', ''))
        all_dishes.extend(dishes)
    
    # Count and rank
    from collections import Counter
    dish_counts = Counter(all_dishes)
    popular = [{'dish': dish, 'mentions': count} for dish, count in dish_counts.most_common(20)]
    
    return jsonify({
        "restaurant_id": restaurant_id,
        "popular_dishes": popular,
        "total_dishes_found": len(set(all_dishes))
    })


@enhanced_review_bp.route('/summary/<restaurant_id>', methods=['GET'])
def get_review_summary(restaurant_id):
    """Get summarized review highlights"""
    if not ENHANCED_ML_AVAILABLE:
        return jsonify({"error": "Enhanced ML not available"}), 503
    
    # Fetch reviews
    reviews_data = review_fetcher.fetch_reviews(restaurant_id=restaurant_id)
    reviews = reviews_data.get('reviews', [])
    
    if not reviews:
        return jsonify({"error": "No reviews found"}), 404
    
    # Generate summary
    summarizer = get_review_summarizer()
    review_texts = [r.get('text', '') for r in reviews if r.get('text')]
    summary = summarizer.summarize_reviews(review_texts, max_sentences=5)
    
    return jsonify({
        "restaurant_id": restaurant_id,
        "summary": summary,
        "based_on_reviews": len(reviews)
    })


@enhanced_review_bp.route('/topics/<restaurant_id>', methods=['GET'])
def get_review_topics(restaurant_id):
    """Get topics discussed in reviews"""
    if not ENHANCED_ML_AVAILABLE:
        return jsonify({"error": "Enhanced ML not available"}), 503
    
    # Fetch reviews
    reviews_data = review_fetcher.fetch_reviews(restaurant_id=restaurant_id)
    reviews = reviews_data.get('reviews', [])
    
    if not reviews or len(reviews) < 3:
        return jsonify({"error": "Not enough reviews for topic extraction"}), 400
    
    # Extract topics
    topic_extractor = get_topic_extractor()
    review_texts = [r.get('text', '') for r in reviews if r.get('text')]
    topics = topic_extractor.extract_topics(review_texts, num_topics=5)
    
    return jsonify({
        "restaurant_id": restaurant_id,
        "topics": topics,
        "based_on_reviews": len(reviews)
    })


@enhanced_review_bp.route('/health', methods=['GET'])
def health_check():
    """Check if enhanced ML features are available"""
    return jsonify({
        "enhanced_ml_available": ENHANCED_ML_AVAILABLE,
        "features": {
            "vader_sentiment": ENHANCED_ML_AVAILABLE,
            "dish_extraction": ENHANCED_ML_AVAILABLE,
            "summarization": ENHANCED_ML_AVAILABLE,
            "topic_modeling": ENHANCED_ML_AVAILABLE,
            "fake_detection": ENHANCED_ML_AVAILABLE
        }
    })
