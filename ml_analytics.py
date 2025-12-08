"""
ML Analytics Module for Restaurant Owners
Provides rating prediction, sentiment analysis, and AI-powered recommendations
"""

import numpy as np
from datetime import datetime
from collections import Counter

# Try to import TextBlob, fallback to basic sentiment if not available
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    print("⚠️ TextBlob not available, using basic sentiment analysis")



class RatingPredictor:
    """Predict future ratings based on historical data and trends"""
    
    def predict_rating(self, restaurant_data, historical_ratings, days_ahead=30):
        """
        Predict rating for X days in the future
        
        Args:
            restaurant_data: Dict with current restaurant metrics
            historical_ratings: List of historical rating values
            days_ahead: Number of days to predict ahead (30, 60, or 90)
            
        Returns:
            Dict with predicted_rating, confidence, current_rating, trend
        """
        current_rating = restaurant_data.get('current_rating', 4.0)
        
        # Calculate trend if we have enough historical data
        if len(historical_ratings) >= 7:
            recent_ratings = historical_ratings[-30:] if len(historical_ratings) >= 30 else historical_ratings
            if len(recent_ratings) > 1:
                # Calculate linear trend
                trend_slope = np.polyfit(range(len(recent_ratings)), recent_ratings, 1)[0]
                predicted_rating = current_rating + (trend_slope * days_ahead)
            else:
                predicted_rating = current_rating
        else:
            predicted_rating = current_rating
        
        # Clamp between 1 and 5
        predicted_rating = max(1.0, min(5.0, predicted_rating))
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(historical_ratings)
        
        # Determine trend direction
        if predicted_rating > current_rating + 0.1:
            trend = 'improving'
        elif predicted_rating < current_rating - 0.1:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'predicted_rating': round(predicted_rating, 2),
            'confidence': confidence,
            'current_rating': current_rating,
            'trend': trend
        }
    
    def _calculate_confidence(self, historical_ratings):
        """Calculate prediction confidence based on data quality"""
        if len(historical_ratings) < 7:
            return 0.3  # Low confidence
        elif len(historical_ratings) < 30:
            return 0.6  # Medium confidence
        else:
            # Check variance - high variance = lower confidence
            variance = np.var(historical_ratings[-30:])
            if variance > 0.5:
                return 0.7
            else:
                return 0.85  # High confidence


class SentimentAnalyzer:
    """Analyze review sentiment and extract insights"""
    
    def analyze_review(self, review_text):
        """
        Analyze sentiment of a single review
        
        Args:
            review_text: String containing the review
            
        Returns:
            Dict with sentiment_score, sentiment_label, aspects, keywords
        """
        if not review_text or len(review_text.strip()) < 10:
            return {
                'sentiment_score': 0,
                'sentiment_label': 'neutral',
                'aspects': {},
                'keywords': []
            }
        
        # Get overall sentiment
        if TEXTBLOB_AVAILABLE:
            try:
                from textblob import TextBlob
                blob = TextBlob(review_text)
                sentiment_score = blob.sentiment.polarity  # -1 to 1
            except:
                sentiment_score = self._basic_sentiment(review_text)
        else:
            sentiment_score = self._basic_sentiment(review_text)
        
        # Determine label
        if sentiment_score > 0.1:
            sentiment_label = 'positive'
        elif sentiment_score < -0.1:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        # Extract aspects
        aspects = self._extract_aspects(review_text)
        
        # Extract keywords
        keywords = self._extract_keywords(review_text)
        
        return {
            'sentiment_score': round(sentiment_score, 2),
            'sentiment_label': sentiment_label,
            'aspects': aspects,
            'keywords': keywords
        }
    
    def _basic_sentiment(self, text):
        """Basic sentiment analysis using keyword matching"""
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 
                         'delicious', 'tasty', 'perfect', 'love', 'best', 'awesome', 'nice']
        negative_words = ['bad', 'terrible', 'horrible', 'awful', 'poor', 'worst', 'disgusting',
                         'disappointing', 'slow', 'rude', 'dirty', 'expensive', 'overpriced']
        
        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0
        
        return (pos_count - neg_count) / total
    
    def _extract_aspects(self, text):
        """Extract sentiment for specific aspects (food, service, ambiance, value)"""
        aspects = {}
        
        # Aspect keywords
        aspect_keywords = {
            'food': ['food', 'dish', 'meal', 'taste', 'flavor', 'delicious', 'cuisine', 'menu'],
            'service': ['service', 'staff', 'waiter', 'server', 'friendly', 'attentive', 'wait'],
            'ambiance': ['ambiance', 'atmosphere', 'decor', 'music', 'lighting', 'cozy', 'interior'],
            'value': ['price', 'value', 'expensive', 'cheap', 'worth', 'cost', 'affordable']
        }
        
        for aspect, keywords in aspect_keywords.items():
            # Find sentences mentioning this aspect
            sentences = []
            for sentence in text.split('.'):
                if any(keyword in sentence.lower() for keyword in keywords):
                    sentences.append(sentence)
            
            if sentences:
                # Analyze sentiment of those sentences
                aspect_text = ' '.join(sentences)
                if TEXTBLOB_AVAILABLE:
                    try:
                        from textblob import TextBlob
                        aspect_sentiment = TextBlob(aspect_text).sentiment.polarity
                    except:
                        aspect_sentiment = self._basic_sentiment(aspect_text)
                else:
                    aspect_sentiment = self._basic_sentiment(aspect_text)
                aspects[aspect] = round(aspect_sentiment, 2)
        
        return aspects
    
    def _extract_keywords(self, text):
        """Extract important keywords from review"""
        if TEXTBLOB_AVAILABLE:
            try:
                from textblob import TextBlob
                blob = TextBlob(text)
                # Get noun phrases
                noun_phrases = list(blob.noun_phrases)
                # Get most common words
                words = [word.lower() for word in blob.words if len(word) > 3]
                common_words = [word for word, count in Counter(words).most_common(10)]
                # Combine and deduplicate
                keywords = list(set(noun_phrases[:5] + common_words[:5]))[:10]
                return keywords
            except:
                pass
        
        # Fallback: simple word extraction
        words = text.lower().split()
        words = [w.strip('.,!?;:') for w in words if len(w) > 4]
        common_words = [word for word, count in Counter(words).most_common(10)]
        return common_words


class RecommendationEngine:
    """Generate actionable recommendations for restaurant owners"""
    
    def generate_recommendations(self, restaurant_data, competitors_data, market_trends):
        """
        Generate personalized recommendations
        
        Args:
            restaurant_data: Dict with restaurant info and metrics
            competitors_data: List of competitor restaurant dicts
            market_trends: Dict with market trend data
            
        Returns:
            List of recommendation dicts sorted by impact score
        """
        recommendations = []
        
        # Feature gap analysis
        feature_recs = self._analyze_feature_gaps(restaurant_data, competitors_data)
        recommendations.extend(feature_recs)
        
        # Review response recommendations
        review_recs = self._analyze_review_response(restaurant_data)
        recommendations.extend(review_recs)
        
        # Photo recommendations
        photo_recs = self._analyze_photos(restaurant_data)
        recommendations.extend(photo_recs)
        
        # Pricing recommendations
        pricing_recs = self._analyze_pricing(restaurant_data, competitors_data)
        recommendations.extend(pricing_recs)
        
        # Trend-based recommendations
        trend_recs = self._analyze_trends(restaurant_data, market_trends)
        recommendations.extend(trend_recs)
        
        # Sort by impact score (descending)
        recommendations.sort(key=lambda x: x['impact_score'], reverse=True)
        
        return recommendations[:10]  # Top 10 recommendations
    
    def _analyze_feature_gaps(self, restaurant, competitors):
        """Identify missing features that competitors have"""
        recs = []
        
        if not competitors:
            return recs
        
        # Check common features
        features_to_check = [
            ('has_delivery', 'Online Delivery', 45),
            ('has_parking', 'Parking', 30),
            ('has_wifi', 'Free WiFi', 25),
            ('has_outdoor_seating', 'Outdoor Seating', 35),
        ]
        
        for feature_key, feature_name, base_impact in features_to_check:
            if not restaurant.get(feature_key):
                # Check how many competitors have it
                competitors_with_feature = sum(1 for c in competitors if c.get(feature_key))
                competitor_percentage = (competitors_with_feature / len(competitors)) * 100
                
                if competitor_percentage > 50:  # More than half have it
                    impact = base_impact + (competitor_percentage - 50) * 0.5
                    recs.append({
                        'type': 'feature',
                        'title': f'Add {feature_name}',
                        'description': f'{competitor_percentage:.0f}% of similar restaurants offer {feature_name}. Adding this could increase your visibility by {base_impact}%.',
                        'impact_score': min(100, impact),
                        'priority': 'high' if competitor_percentage > 70 else 'medium'
                    })
        
        return recs
    
    def _analyze_review_response(self, restaurant):
        """Analyze review response rate"""
        recs = []
        
        total_reviews = restaurant.get('review_count', 0)
        responded_reviews = restaurant.get('responded_review_count', 0)
        
        if total_reviews > 0:
            response_rate = (responded_reviews / total_reviews) * 100
            
            if response_rate < 50:
                recs.append({
                    'type': 'engagement',
                    'title': 'Respond to More Reviews',
                    'description': f'You\'ve responded to only {response_rate:.0f}% of reviews. Restaurants that respond to 80%+ of reviews get 23% more bookmarks.',
                    'impact_score': 60,
                    'priority': 'high'
                })
        
        return recs
    
    def _analyze_photos(self, restaurant):
        """Analyze photo count"""
        recs = []
        
        photo_count = restaurant.get('photo_count', 0)
        
        if photo_count < 5:
            recs.append({
                'type': 'content',
                'title': 'Add More Photos',
                'description': f'You have only {photo_count} photos. Restaurants with 10+ photos get 35% more clicks. Add high-quality images of your food, ambiance, and exterior.',
                'impact_score': 55,
                'priority': 'high'
            })
        
        return recs
    
    def _analyze_pricing(self, restaurant, competitors):
        """Analyze pricing strategy"""
        recs = []
        
        if not competitors:
            return recs
        
        restaurant_price = restaurant.get('avg_cost_for_two', 0)
        competitor_prices = [c.get('avg_cost_for_two', 0) for c in competitors if c.get('avg_cost_for_two')]
        
        if competitor_prices and restaurant_price > 0:
            avg_competitor_price = np.mean(competitor_prices)
            price_diff_pct = ((restaurant_price - avg_competitor_price) / avg_competitor_price) * 100
            
            if price_diff_pct > 20:
                recs.append({
                    'type': 'pricing',
                    'title': 'Consider Price Adjustment',
                    'description': f'Your prices are {price_diff_pct:.0f}% higher than similar restaurants (₹{restaurant_price} vs ₹{avg_competitor_price:.0f}). This may be limiting your customer base.',
                    'impact_score': 40,
                    'priority': 'medium'
                })
        
        return recs
    
    def _analyze_trends(self, restaurant, market_trends):
        """Analyze market trends and suggest adaptations"""
        recs = []
        
        # Example: Vegan trend
        if market_trends.get('vegan_search_increase', 0) > 30:
            cuisines = restaurant.get('cuisines', '').lower()
            if 'vegan' not in cuisines:
                recs.append({
                    'type': 'menu',
                    'title': 'Add Vegan Options',
                    'description': f'Vegan searches in your city increased by {market_trends["vegan_search_increase"]}%. Consider adding vegan menu items to attract this growing segment.',
                    'impact_score': 50,
                    'priority': 'medium'
                })
        
        return recs
