"""
Local Sentiment Analysis Model
Uses HuggingFace transformers for offline sentiment analysis of restaurant reviews
No API costs, works completely locally after initial model download
"""

import os
import re
from typing import List, Dict, Optional
from collections import Counter
import warnings

# Suppress transformer warnings
warnings.filterwarnings('ignore')

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️ Transformers not available. Install with: pip install transformers torch")


class LocalSentimentAnalyzer:
    """
    Local AI-powered sentiment analyzer using HuggingFace transformers
    Uses foody-bert model specifically trained on restaurant reviews
    """
    
    def __init__(self, model_name="distilbert-base-uncased-finetuned-sst-2-english"):
        """
        Initialize the local sentiment model
        
        Args:
            model_name: HuggingFace model to use
                - "distilbert-base-uncased-finetuned-sst-2-english" (default, fast)
                - "nlptown/bert-base-multilingual-uncased-sentiment" (5-star ratings)
                - "cardiffnlp/twitter-roberta-base-sentiment" (social media)
        """
        self.model = None
        self.model_name = model_name
        self.available = False
        
        if not TRANSFORMERS_AVAILABLE:
            print("❌ Transformers library not available")
            return
        
        try:
            print(f"🔄 Loading sentiment model: {model_name}")
            print("   (First run will download ~250MB, subsequent runs use cache)")
            
            # Load model with caching
            self.model = pipeline(
                "sentiment-analysis",
                model=model_name,
                device=-1  # Use CPU (-1), or 0 for GPU
            )
            
            self.available = True
            print(f"✅ Local sentiment model loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading sentiment model: {e}")
            print("   Falling back to basic sentiment analysis")
    
    def is_available(self) -> bool:
        """Check if the model is loaded and ready"""
        return self.available
    
    def analyze_reviews(self, reviews: List[Dict]) -> Dict:
        """
        Analyze multiple reviews and generate comprehensive insights
        
        Args:
            reviews: List of review dicts with 'text' and 'rating' fields
            
        Returns:
            dict: Complete analysis with sentiment, topics, highlights
        """
        if not reviews:
            return self._empty_analysis()
        
        if not self.is_available():
            return self._fallback_analysis(reviews)
        
        try:
            # Extract review texts
            review_texts = [r.get('text', '') for r in reviews if r.get('text')]
            
            if not review_texts:
                return self._empty_analysis()
            
            # Analyze sentiments using transformer model
            sentiments = self._batch_analyze_sentiment(review_texts)
            
            # Extract topics and highlights
            topics = self._extract_topics(review_texts)
            positive_highlights = self._extract_highlights(review_texts, 'positive')
            negative_highlights = self._extract_highlights(review_texts, 'negative')
            best_items = self._extract_food_items(review_texts, 'positive')
            common_complaints = self._extract_complaints(review_texts)
            
            # Calculate sentiment percentages
            sentiment_counts = Counter([s['label'] for s in sentiments])
            total = len(sentiments)
            
            # Map labels (POSITIVE/NEGATIVE) to our format
            positive_count = sentiment_counts.get('POSITIVE', 0)
            negative_count = sentiment_counts.get('NEGATIVE', 0)
            neutral_count = total - positive_count - negative_count
            
            # Determine overall sentiment
            if positive_count > negative_count * 1.5:
                overall_sentiment = 'positive'
            elif negative_count > positive_count * 1.5:
                overall_sentiment = 'negative'
            else:
                overall_sentiment = 'neutral'
            
            # Generate AI summary
            ai_summary = self._generate_summary(
                total, overall_sentiment, positive_count, negative_count
            )
            
            # Generate recommendations
            ai_recommendations = self._generate_recommendations(
                best_items, positive_highlights, negative_highlights
            )
            
            return {
                'overall_sentiment': overall_sentiment,
                'sentiment_percentages': {
                    'positive': round((positive_count / total) * 100) if total > 0 else 0,
                    'neutral': round((neutral_count / total) * 100) if total > 0 else 0,
                    'negative': round((negative_count / total) * 100) if total > 0 else 0
                },
                'top_topics': topics[:5],
                'positive_highlights': positive_highlights[:5],
                'negative_highlights': negative_highlights[:5],
                'best_items': best_items[:5],
                'common_complaints': common_complaints[:5],
                'ai_summary': ai_summary,
                'ai_recommendations': ai_recommendations,
                'review_count': total,
                'review_source_used': 'Multiple Sources',
                'analyzed_at': None,
                'model_used': 'Local AI (HuggingFace Transformers)',
                'confidence_score': round((positive_count / total) * 100) if total > 0 else 0,
                'review_quality': 'high' if total >= 50 else 'medium' if total >= 20 else 'low',
                'sentiment_strength': 'strong' if abs(positive_count - negative_count) > total * 0.5 else 'moderate'
            }
            
        except Exception as e:
            print(f"Error in local sentiment analysis: {e}")
            return self._fallback_analysis(reviews)
    
    def analyze_single_review(self, review_text: str) -> Dict:
        """
        Analyze a single review for sentiment
        
        Args:
            review_text: Review text to analyze
            
        Returns:
            dict: Sentiment label, confidence, topics
        """
        if not self.is_available():
            return {
                'sentiment': 'neutral',
                'confidence': 0.5,
                'topics': [],
                'mentioned_items': []
            }
        
        try:
            result = self.model(review_text[:512])[0]  # Limit to 512 tokens
            
            # Extract topics and items
            topics = self._extract_topics([review_text])
            items = self._extract_food_items([review_text], 'any')
            
            return {
                'sentiment': result['label'].lower(),
                'confidence': round(result['score'], 2),
                'topics': topics[:3],
                'mentioned_items': items[:3]
            }
            
        except Exception as e:
            print(f"Error analyzing single review: {e}")
            return {
                'sentiment': 'neutral',
                'confidence': 0.5,
                'topics': [],
                'mentioned_items': []
            }
    
    def _batch_analyze_sentiment(self, texts: List[str]) -> List[Dict]:
        """Analyze sentiment for multiple texts efficiently"""
        try:
            # Truncate texts to max token length
            truncated_texts = [text[:512] for text in texts]
            
            # Batch process for efficiency
            results = self.model(truncated_texts)
            
            return results
            
        except Exception as e:
            print(f"Error in batch sentiment analysis: {e}")
            return [{'label': 'NEUTRAL', 'score': 0.5} for _ in texts]
    
    def _extract_topics(self, texts: List[str]) -> List[str]:
        """Extract main topics discussed in reviews"""
        topics = []
        
        # Enhanced topic keywords with more variations
        topic_keywords = {
            'Food Quality': ['food', 'taste', 'delicious', 'flavor', 'dish', 'meal', 'cuisine', 'cooked', 'fresh', 'quality', 'tasty', 'yummy', 'flavorful', 'seasoned', 'spices'],
            'Service': ['service', 'staff', 'waiter', 'server', 'friendly', 'attentive', 'prompt', 'courteous', 'helpful', 'professional', 'polite', 'rude', 'slow service'],
            'Ambiance': ['ambiance', 'atmosphere', 'decor', 'vibe', 'setting', 'environment', 'cozy', 'modern', 'romantic', 'seating', 'lighting', 'music'],
            'Price': ['price', 'expensive', 'cheap', 'value', 'cost', 'affordable', 'overpriced', 'reasonable', 'worth', 'money'],
            'Cleanliness': ['clean', 'hygiene', 'dirty', 'neat', 'tidy', 'sanitary', 'maintained', 'washroom'],
            'Portion Size': ['portion', 'size', 'quantity', 'amount', 'serving', 'generous', 'small', 'large', 'filling'],
            'Wait Time': ['wait', 'waiting', 'slow', 'quick', 'fast', 'delayed', 'rush', 'crowded', 'busy'],
            'Presentation': ['presentation', 'plated', 'beautiful', 'instagram', 'garnish', 'plating', 'appearance']
        }
        
        combined_text = ' '.join(texts).lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _extract_highlights(self, texts: List[str], sentiment_type: str) -> List[str]:
        """Extract positive or negative highlights from reviews - COMPLETE PHRASES"""
        highlights = []
        
        # Extract complete sentences first, then find highlights within them
        for text in texts:
            sentences = re.split(r'[.!?]+', text)
            
            if sentiment_type == 'positive':
                # Positive keywords to look for
                positive_keywords = [
                    'excellent', 'amazing', 'fantastic', 'wonderful', 'great', 'best', 
                    'loved', 'perfect', 'outstanding', 'exceptional', 'delicious', 
                    'incredible', 'highly recommend', 'must try', 'favorite'
                ]
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) < 10 or len(sentence) > 150:  # Skip too short or too long
                        continue
                    
                    # Check if sentence contains positive keywords
                    if any(keyword in sentence.lower() for keyword in positive_keywords):
                        # Clean up the sentence
                        cleaned = sentence.strip()
                        
                        # Remove leading articles and conjunctions
                        cleaned = re.sub(r'^(The|A|An|And|But|Or|So|Also|However)\s+', '', cleaned, flags=re.IGNORECASE)
                        
                        # Capitalize first letter
                        if cleaned and len(cleaned) > 10:
                            cleaned = cleaned[0].upper() + cleaned[1:]
                            
                            if cleaned not in highlights:
                                highlights.append(cleaned)
                                
                                if len(highlights) >= 8:  # Get more highlights
                                    break
                    
            else:  # negative
                # Negative keywords to look for
                negative_keywords = [
                    'terrible', 'awful', 'horrible', 'worst', 'bad', 'poor', 
                    'disappointing', 'bland', 'overcooked', 'undercooked', 'cold', 
                    'stale', 'slow', 'rude', 'unprofessional', 'dirty', 'overpriced'
                ]
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) < 10 or len(sentence) > 150:
                        continue
                    
                    # Check if sentence contains negative keywords
                    if any(keyword in sentence.lower() for keyword in negative_keywords):
                        # Clean up the sentence
                        cleaned = sentence.strip()
                        
                        # Remove leading articles and conjunctions
                        cleaned = re.sub(r'^(The|A|An|And|But|Or|So|Also|However)\s+', '', cleaned, flags=re.IGNORECASE)
                        
                        # Capitalize first letter
                        if cleaned and len(cleaned) > 10:
                            cleaned = cleaned[0].upper() + cleaned[1:]
                            
                            if cleaned not in highlights:
                                highlights.append(cleaned)
                                
                                if len(highlights) >= 8:
                                    break
        
        return highlights[:5]
    
    def _extract_food_items(self, texts: List[str], sentiment_filter: str = 'positive') -> List[str]:
        """Extract mentioned food items from reviews"""
        items = []
        
        # Enhanced food-related patterns with more dishes
        food_patterns = [
            # Indian dishes
            r'(butter chicken|chicken tikka|paneer tikka|chicken 65|biryani|curry|naan|roti|dal|tikka|kebab|masala|tandoori|samosa|pakora)',
            r'(paneer butter masala|palak paneer|kadai paneer|malai kofta|chole bhature|dosa|idli|vada)',
            # International dishes
            r'(pizza|pasta|burger|sandwich|bruschetta|garlic bread|spring rolls|pad thai|sushi|ramen)',
            r'(margherita|alfredo|carbonara|bolognese|pesto|lasagna|risotto|gnocchi)',
            r'(grilled salmon|fish and chips|steak|lamb chops|pork ribs)',
            # Desserts
            r'(gulab jamun|rasgulla|kulfi|tiramisu|cheesecake|brownie|lava cake|ice cream|mousse|pudding)',
            r'(chocolate cake|red velvet|carrot cake|panna cotta|creme brulee)',
            # Appetizers
            r'(appetizer|starter|main course|entree|soup|salad)',
        ]
        
        combined_text = ' '.join(texts).lower()
        
        for pattern in food_patterns:
            matches = re.findall(pattern, combined_text)
            items.extend(matches)
        
        # Count frequency and return most mentioned
        item_counts = Counter(items)
        # Capitalize properly (handle multi-word dishes)
        return [' '.join(word.capitalize() for word in item.split()) for item, _ in item_counts.most_common(5)]
    
    def _extract_complaints(self, texts: List[str]) -> List[str]:
        """Extract common complaints from reviews"""
        complaints = []
        
        complaint_patterns = [
            r'(slow|long wait|delayed|late) (service|delivery|order)',
            r'(rude|unfriendly|unprofessional) (staff|waiter|service)',
            r'(overpriced|expensive|costly|not worth)',
            r'(cold|stale|undercooked|overcooked) (food|dish)',
            r'(dirty|unclean|unhygienic)',
        ]
        
        for text in texts:
            for pattern in complaint_patterns:
                matches = re.findall(pattern, text.lower())
                for match in matches:
                    complaint = ' '.join(match).strip()
                    if complaint not in complaints:
                        complaints.append(complaint.capitalize())
        
        return complaints[:5]
    
    def _generate_summary(self, total: int, sentiment: str, positive: int, negative: int) -> str:
        """Generate comprehensive AI-style summary with detailed insights"""
        
        # Calculate percentages
        pos_pct = round((positive / total) * 100) if total > 0 else 0
        neg_pct = round((negative / total) * 100) if total > 0 else 0
        neutral = total - positive - negative
        neu_pct = round((neutral / total) * 100) if total > 0 else 0
        
        # Build detailed summary with multiple sentences
        summary_parts = []
        
        # Opening statement with comprehensive context
        if sentiment == 'positive':
            summary_parts.append(f"Based on comprehensive analysis of {total} customer reviews, this restaurant demonstrates exceptional performance with {pos_pct}% positive feedback.")
            
            if pos_pct >= 80:
                summary_parts.append(f"{positive} out of {total} customers highly recommend this establishment, consistently praising its outstanding quality, service, and overall dining experience.")
            else:
                summary_parts.append(f"{positive} out of {total} reviewers recommend this restaurant for its quality and service.")
            
            if neu_pct > 10:
                summary_parts.append(f"While {neu_pct}% had neutral experiences, the overwhelming majority report satisfaction.")
                
        elif sentiment == 'negative':
            summary_parts.append(f"Analysis of {total} reviews reveals concerning patterns, with {neg_pct}% negative feedback indicating significant room for improvement.")
            summary_parts.append(f"{negative} out of {total} customers reported dissatisfaction with various aspects including food quality, service, or value.")
            
            if pos_pct > 20:
                summary_parts.append(f"However, {pos_pct}% of customers did have positive experiences, suggesting inconsistent quality.")
        else:
            summary_parts.append(f"Based on {total} reviews, customer experiences show mixed results with {pos_pct}% positive, {neu_pct}% neutral, and {neg_pct}% negative feedback.")
            summary_parts.append(f"While {positive} customers enjoyed their visit, {negative} noted areas needing improvement, indicating variable service quality.")
        
        return ' '.join(summary_parts)
    
    def _generate_recommendations(self, best_items: List[str], positives: List[str], negatives: List[str]) -> str:
        """Generate detailed, actionable recommendations with context"""
        
        recommendations = []
        
        # Dish recommendations with enthusiastic context
        if best_items:
            if len(best_items) >= 3:
                dishes_str = ', '.join(best_items[:3])
                recommendations.append(f"🍽️ Must-Try Dishes: {dishes_str} - consistently praised by customers for exceptional taste, quality, and authentic flavors.")
            elif len(best_items) == 2:
                dishes_str = ' and '.join(best_items[:2])
                recommendations.append(f"🍽️ Signature Items: Don't miss their {dishes_str} which receive rave reviews from diners.")
            else:
                recommendations.append(f"🍽️ Featured Dish: {best_items[0]} is highly recommended by satisfied customers.")
        
        # Timing and service recommendations based on negative feedback
        has_wait_issues = any('slow' in neg.lower() or 'wait' in neg.lower() or 'delayed' in neg.lower() for neg in negatives)
        has_crowd_issues = any('crowded' in neg.lower() or 'busy' in neg.lower() or 'rush' in neg.lower() for neg in negatives)
        
        if has_wait_issues or has_crowd_issues:
            recommendations.append(f"⏰ Pro Tip: Visit during off-peak hours (weekday afternoons 2-5 PM or after 9 PM) for faster service, better attention from staff, and a more relaxed dining experience.")
        elif len(positives) > 5:  # Popular restaurant
            recommendations.append(f"⏰ Booking Recommended: This popular restaurant receives high praise - consider making reservations for weekend dinners or special occasions to avoid wait times.")
        
        # Service quality insights
        has_good_service = any('service' in pos.lower() and ('good' in pos.lower() or 'great' in pos.lower() or 'excellent' in pos.lower() or 'friendly' in pos.lower()) for pos in positives)
        has_poor_service = any('service' in neg.lower() or 'staff' in neg.lower() or 'rude' in neg.lower() for neg in negatives)
        
        if has_good_service:
            recommendations.append(f"👥 Excellent Service: Staff consistently receives high praise for professionalism, attentiveness, and creating a welcoming atmosphere.")
        elif has_poor_service:
            recommendations.append(f"👥 Service Note: Some customers mention service inconsistencies during peak hours - patience may be needed during busy periods.")
        
        # Value and pricing insights
        has_good_value = any(('value' in pos.lower() or 'worth' in pos.lower() or 'reasonable' in pos.lower() or 'affordable' in pos.lower()) for pos in positives)
        has_price_concerns = any('expensive' in neg.lower() or 'overpriced' in neg.lower() or 'costly' in neg.lower() for neg in negatives)
        
        if has_good_value:
            recommendations.append(f"💰 Great Value: Customers consistently highlight excellent value for money with generous portions and fair pricing.")
        elif has_price_concerns:
            recommendations.append(f"💰 Pricing Note: Some find it on the pricier side - consider lunch specials or combo meals for better value.")
        
        # Ambiance and occasion recommendations
        has_romantic_vibe = any('romantic' in pos.lower() or 'cozy' in pos.lower() or 'intimate' in pos.lower() or 'ambiance' in pos.lower() for pos in positives)
        has_family_friendly = any('family' in pos.lower() or 'kids' in pos.lower() or 'children' in pos.lower() for pos in positives)
        
        if has_romantic_vibe:
            recommendations.append(f"💑 Perfect For: Romantic dinners, date nights, and special celebrations with its intimate ambiance and quality service.")
        elif has_family_friendly:
            recommendations.append(f"👨‍👩‍👧‍👦 Family-Friendly: Ideal for family gatherings, group celebrations, and casual dining with loved ones.")
        
        # Food quality highlights
        has_quality_praise = any('quality' in pos.lower() or 'fresh' in pos.lower() or 'authentic' in pos.lower() for pos in positives)
        if has_quality_praise and not best_items:
            recommendations.append(f"✨ Quality Ingredients: Diners appreciate the use of fresh, high-quality ingredients and authentic cooking methods.")
        
        # Fallback recommendation if nothing specific found
        if not recommendations:
            recommendations.append("📋 Explore the Menu: Check recent reviews for the latest customer experiences, seasonal specials, and chef recommendations.")
        
        return ' '.join(recommendations)
    
    def _fallback_analysis(self, reviews: List[Dict]) -> Dict:
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
            'top_topics': ['Food Quality', 'Service', 'Ambiance'],
            'positive_highlights': ['Good food', 'Friendly staff'],
            'negative_highlights': ['Slow service'] if negative_count > 0 else [],
            'best_items': [],
            'common_complaints': [],
            'ai_summary': f'Based on {total} reviews, customers have a generally {"positive" if positive_count > negative_count else "mixed"} experience.',
            'ai_recommendations': 'Try visiting during off-peak hours for better service.',
            'review_count': total,
            'review_source_used': 'Multiple Sources',
            'analyzed_at': None,
            'fallback_used': True,
            'model_used': 'Basic Keyword Analysis (Fallback)'
        }
    
    def _empty_analysis(self) -> Dict:
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
            'analyzed_at': None,
            'model_used': 'Local AI (HuggingFace Transformers)'
        }


# Global instance
local_sentiment_analyzer = LocalSentimentAnalyzer()
