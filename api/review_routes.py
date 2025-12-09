"""
Review Analysis API Routes
Endpoints for fetching and analyzing restaurant reviews
"""
from flask import Blueprint, request, jsonify
from services import ReviewFetcher, SentimentAnalyzer, CacheManager
from datetime import datetime

review_bp = Blueprint('reviews', __name__, url_prefix='/api/reviews')

# Initialize services
review_fetcher = ReviewFetcher()
sentiment_analyzer = SentimentAnalyzer()
cache_manager = CacheManager()


@review_bp.route('/fetch', methods=['POST'])
def fetch_reviews():
    """
    Fetch reviews for a restaurant
    
    Request JSON:
    {
        "place_id": "ChIJ...",
        "restaurant_name": "Pizza Palace",
        "force_refresh": false
    }
    """
    try:
        data = request.get_json()
        
        place_id = data.get('place_id') or data.get('restaurant_id')
        restaurant_name = data.get('restaurant_name')
        city = data.get('city', '')
        force_refresh = data.get('force_refresh', False)
        
        if not place_id:
            return jsonify({
                'success': False,
                'error': 'place_id is required'
            }), 400
        
        # Fetch reviews
        result = review_fetcher.fetch_reviews(
            restaurant_id=place_id,
            restaurant_name=restaurant_name,
            city=city,
            force_refresh=force_refresh
        )
        
        return jsonify({
            'success': True,
            'reviews_count': result['count'],
            'source': result['source'],
            'cached_at': result['cached_at'].isoformat() if result['cached_at'] else None,
            'reviews': result['reviews'][:10]  # Return first 10 for preview
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@review_bp.route('/analyze', methods=['POST'])
def analyze_reviews():
    """
    Analyze reviews for a restaurant
    
    Request JSON:
    {
        "place_id": "ChIJ...",
        "use_cache": true
    }
    """
    try:
        data = request.get_json()
        
        place_id = data.get('place_id')
        use_cache = data.get('use_cache', True)
        
        if not place_id:
            return jsonify({
                'success': False,
                'error': 'place_id is required'
            }), 400
        
        # Check cache first if requested
        if use_cache:
            cached_analysis = cache_manager.get_cached_analysis(place_id)
            if cached_analysis:
                return jsonify({
                    'success': True,
                    'source': 'cache',
                    **cached_analysis
                })
        
        # Fetch reviews
        restaurant_name = data.get('restaurant_name', '')
        city = data.get('city', '')
        review_result = review_fetcher.fetch_reviews(
            restaurant_id=place_id,
            restaurant_name=restaurant_name,
            city=city
        )
        
        if review_result['count'] == 0:
            return jsonify({
                'success': True,
                'source': 'no_reviews',
                **sentiment_analyzer._empty_analysis()
            })
        
        # Analyze reviews
        analysis = sentiment_analyzer.analyze_reviews(review_result['reviews'])
        analysis['analyzed_at'] = datetime.utcnow().isoformat()
        
        # Cache the analysis
        cache_manager.save_analysis(place_id, analysis)
        
        return jsonify({
            'success': True,
            'source': 'fresh_analysis',
            **analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@review_bp.route('/refresh', methods=['POST'])
def refresh_reviews():
    """
    Force refresh reviews and analysis for a restaurant
    
    Request JSON:
    {
        "place_id": "ChIJ..."
    }
    """
    try:
        data = request.get_json()
        
        place_id = data.get('place_id')
        
        if not place_id:
            return jsonify({
                'success': False,
                'error': 'place_id is required'
            }), 400
        
        # Invalidate cache
        review_fetcher.invalidate_cache(place_id)
        
        # Fetch fresh reviews
        review_result = review_fetcher.fetch_reviews(place_id, force_refresh=True)
        
        # Analyze fresh reviews
        if review_result['count'] > 0:
            analysis = sentiment_analyzer.analyze_reviews(review_result['reviews'])
            analysis['analyzed_at'] = datetime.utcnow().isoformat()
            cache_manager.save_analysis(place_id, analysis)
        else:
            analysis = sentiment_analyzer._empty_analysis()
        
        return jsonify({
            'success': True,
            'reviews_count': review_result['count'],
            'source': 'refreshed',
            **analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500




@review_bp.route('/generate-samples', methods=['POST'])
def generate_sample_reviews():
    """
    Generate sample reviews for a restaurant (for testing/demonstration)
    
    Request JSON:
    {
        "restaurant_id": "123",
        "restaurant_name": "Pizza Palace",
        "city": "Mumbai"
    }
    """
    try:
        data = request.get_json()
        
        restaurant_id = data.get('restaurant_id')
        restaurant_name = data.get('restaurant_name', 'Restaurant')
        city = data.get('city', 'City')
        
        if not restaurant_id:
            return jsonify({
                'success': False,
                'error': 'restaurant_id is required'
            }), 400
        
        # Generate sample reviews
        success = review_fetcher.add_sample_reviews(restaurant_id, restaurant_name, city)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Sample reviews added for {restaurant_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add sample reviews'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@review_bp.route('/status/<place_id>', methods=['GET'])
def get_cache_status(place_id):
    """Get cache status for a restaurant"""
    try:
        review_status = review_fetcher.get_cache_status(place_id)
        analysis_status = cache_manager.get_cache_status(place_id)
        
        return jsonify({
            'success': True,
            'reviews_cache': review_status,
            'analysis_cache': analysis_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
