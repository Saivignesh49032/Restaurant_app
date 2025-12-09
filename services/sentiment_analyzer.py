"""
Sentiment Analyzer Service
Analyzes restaurant reviews using Gemini API for sentiment classification and insights
"""
from gemini_api import gemini_search
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
        
        # Analyze using Gemini
        try:
            analysis = self._analyze_with_gemini(review_texts, reviews)
            return analysis
        except Exception as e:
            print(f"Error in sentiment analysis: {str(e)}")
            return self._fallback_analysis(reviews)
    
    def _analyze_with_gemini(self, review_texts, reviews):
        """Use Gemini API for comprehensive analysis"""
        
        # Check if Gemini is available
        if not gemini_search.is_available():
            print("Gemini not available, using fallback analysis")
            return self._fallback_analysis(reviews)
        
        # Prepare prompt
        prompt = self._create_analysis_prompt(review_texts)
        
        # Call Gemini
        response = gemini_search.model.generate_content(prompt)
        
        # Parse JSON response
        try:
            # Extract JSON from response
            response_text = response.text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                analysis_data = json.loads(json_match.group())
            else:
                # Fallback if JSON not found
                return self._fallback_analysis(reviews)
            
            # Add metadata
            analysis_data['review_count'] = len(reviews)
            analysis_data['review_source_used'] = 'Google Places API'
            analysis_data['analyzed_at'] = None  # Will be set by caller
            
            return analysis_data
            
        except json.JSONDecodeError as e:
            print(f"Error parsing Gemini response: {str(e)}")
            return self._fallback_analysis(reviews)
    
    def _create_analysis_prompt(self, review_texts):
        """Create comprehensive analysis prompt for Gemini"""
        
        # Combine reviews for context
        combined_reviews = "\n\n".join([f"Review {i+1}: {text}" for i, text in enumerate(review_texts[:20])])  # Limit to 20 reviews
        
        prompt = f"""Analyze these restaurant reviews and provide comprehensive insights in JSON format.

Reviews:
{combined_reviews}

Provide analysis in this exact JSON format:
{{
  "overall_sentiment": "positive/neutral/negative",
  "sentiment_percentages": {{
    "positive": 0,
    "neutral": 0,
    "negative": 0
  }},
  "top_topics": ["topic1", "topic2", "topic3"],
  "positive_highlights": ["highlight1", "highlight2", "highlight3"],
  "negative_highlights": ["complaint1", "complaint2"],
  "best_items": ["dish1", "dish2", "dish3"],
  "common_complaints": ["issue1", "issue2"],
  "ai_summary": "2-3 sentence summary of overall customer experience",
  "ai_recommendations": "Personalized suggestions for what to try or when to visit"
}}

Guidelines:
- overall_sentiment: Classify based on majority sentiment
- sentiment_percentages: Estimate percentage of positive/neutral/negative reviews (must sum to 100)
- top_topics: Main themes discussed (food quality, service, ambience, price, cleanliness)
- positive_highlights: Best aspects mentioned by customers (max 5)
- negative_highlights: Common complaints (max 5)
- best_items: Specific dishes or menu items highly praised (max 5)
- common_complaints: Recurring issues customers mention (max 5)
- ai_summary: Brief, engaging summary of the dining experience
- ai_recommendations: Helpful suggestions for potential diners

Return ONLY the JSON, no additional text."""

        return prompt
    
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
        
        prompt = f"""Analyze this restaurant review and classify its sentiment.

Review: "{review_text}"

Return JSON:
{{
  "sentiment": "positive/neutral/negative",
  "confidence": 0.0-1.0,
  "topics": ["topic1", "topic2"],
  "mentioned_items": ["item1", "item2"]
}}"""

        try:
            response = gemini_search.model.generate_content(prompt)
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            print(f"Error analyzing single review: {str(e)}")
        
        return {
            'sentiment': 'neutral',
            'confidence': 0.5,
            'topics': [],
            'mentioned_items': []
        }
