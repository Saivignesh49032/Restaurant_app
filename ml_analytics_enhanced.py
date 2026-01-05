"""
Enhanced ML Analytics Module - CPU Optimized
Uses VADER for sentiment, NLTK for NLP, sklearn for ML
NO GPU REQUIRED - All operations run efficiently on CPU
"""

import re
import numpy as np
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any

# VADER Sentiment Analysis (Fast & Accurate for reviews)
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    print("⚠️ VADER not available, using basic sentiment")

# NLTK for text processing
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    NLTK_AVAILABLE = True
    
    # Download required NLTK data (only once)
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        
except ImportError:
    NLTK_AVAILABLE = False
    print("⚠️ NLTK not available")

# Sklearn for ML features
try:
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ Sklearn not available")


class EnhancedSentimentAnalyzer:
    """
    Advanced sentiment analysis using VADER
    - Emotion detection
    - Aspect-based sentiment
    - Intensity scoring
    - Works great for restaurant reviews!
    """
    
    def __init__(self):
        if VADER_AVAILABLE:
            self.analyzer = SentimentIntensityAnalyzer()
        else:
            self.analyzer = None
        
        # Food-related aspects
        self.aspects = {
            'food': ['food', 'dish', 'meal', 'taste', 'flavor', 'delicious', 'cuisine', 
                    'menu', 'chicken', 'paneer', 'biryani', 'pizza', 'pasta', 'curry'],
            'service': ['service', 'staff', 'waiter', 'server', 'friendly', 'attentive', 
                       'wait', 'quick', 'slow', 'rude', 'polite', 'helpful'],
            'ambiance': ['ambiance', 'atmosphere', 'decor', 'music', 'lighting', 'cozy', 
                        'interior', 'seating', 'clean', 'dirty', 'spacious', 'crowded'],
            'value': ['price', 'value', 'expensive', 'cheap', 'worth', 'cost', 'affordable',
                     'overpriced', 'reasonable', 'money']
        }
    
    def analyze_review(self, review_text: str) -> Dict[str, Any]:
        """
        Comprehensive sentiment analysis
        
        Returns:
            {
                'sentiment_score': float (-1 to 1),
                'sentiment_label': str (positive/negative/neutral),
                'confidence': float (0 to 1),
                'emotions': dict,
                'aspects': dict,
                'keywords': list
            }
        """
        if not review_text or len(review_text.strip()) < 10:
            return self._empty_result()
        
        # VADER sentiment analysis
        if VADER_AVAILABLE and self.analyzer:
            scores = self.analyzer.polarity_scores(review_text)
            sentiment_score = scores['compound']  # -1 to 1
            confidence = max(scores['pos'], scores['neg'], scores['neu'])
            
            # Determine label
            if sentiment_score >= 0.05:
                sentiment_label = 'positive'
            elif sentiment_score <= -0.05:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'
            
            # Extract emotions from scores
            emotions = {
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu']
            }
        else:
            # Fallback to basic sentiment
            sentiment_score = self._basic_sentiment(review_text)
            confidence = 0.6
            sentiment_label = 'positive' if sentiment_score > 0.1 else ('negative' if sentiment_score < -0.1 else 'neutral')
            emotions = {}
        
        # Aspect-based sentiment
        aspects = self._extract_aspect_sentiment(review_text)
        
        # Extract keywords
        keywords = self._extract_keywords(review_text)
        
        return {
            'sentiment_score': round(sentiment_score, 3),
            'sentiment_label': sentiment_label,
            'confidence': round(confidence, 3),
            'emotions': emotions,
            'aspects': aspects,
            'keywords': keywords
        }
    
    def _extract_aspect_sentiment(self, text: str) -> Dict[str, float]:
        """Extract sentiment for each aspect"""
        aspect_sentiments = {}
        
        for aspect_name, keywords in self.aspects.items():
            # Find sentences mentioning this aspect
            sentences = []
            for sentence in text.split('.'):
                if any(keyword in sentence.lower() for keyword in keywords):
                    sentences.append(sentence)
            
            if sentences:
                aspect_text = ' '.join(sentences)
                
                if VADER_AVAILABLE and self.analyzer:
                    scores = self.analyzer.polarity_scores(aspect_text)
                    aspect_sentiments[aspect_name] = round(scores['compound'], 2)
                else:
                    aspect_sentiments[aspect_name] = round(self._basic_sentiment(aspect_text), 2)
        
        return aspect_sentiments
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords"""
        if NLTK_AVAILABLE:
            try:
                # Tokenize and remove stopwords
                words = word_tokenize(text.lower())
                stop_words = set(stopwords.words('english'))
                keywords = [w for w in words if w.isalnum() and len(w) > 3 and w not in stop_words]
                
                # Get most common
                common = Counter(keywords).most_common(10)
                return [word for word, count in common]
            except:
                pass
        
        # Fallback: simple extraction
        words = re.findall(r'\b\w{4,}\b', text.lower())
        return list(set(words))[:10]
    
    def _basic_sentiment(self, text: str) -> float:
        """Fallback basic sentiment"""
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 
                         'delicious', 'tasty', 'perfect', 'love', 'best', 'awesome']
        negative_words = ['bad', 'terrible', 'horrible', 'awful', 'poor', 'worst', 
                         'disgusting', 'disappointing', 'slow', 'rude', 'dirty']
        
        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0
        return (pos_count - neg_count) / total
    
    def _empty_result(self) -> Dict[str, Any]:
        """Empty result for invalid input"""
        return {
            'sentiment_score': 0,
            'sentiment_label': 'neutral',
            'confidence': 0,
            'emotions': {},
            'aspects': {},
            'keywords': []
        }


class DishExtractor:
    """
    Extract dish names and food items from reviews
    Uses pattern matching and food keywords
    """
    
    def __init__(self):
        # Common Indian and international dishes
        self.dish_patterns = [
            r'\b(butter chicken|paneer tikka|biryani|dal makhani|naan|roti|dosa|idli)\b',
            r'\b(pizza|pasta|burger|sandwich|salad|soup|steak|salmon)\b',
            r'\b(chicken \w+|paneer \w+|mutton \w+|fish \w+)\b',
            r'\b(\w+ curry|\w+ masala|\w+ tikka|\w+ kebab)\b',
        ]
        
        # Food indicators
        self.food_keywords = [
            'chicken', 'paneer', 'mutton', 'fish', 'prawn', 'egg',
            'biryani', 'curry', 'masala', 'tikka', 'kebab', 'tandoori',
            'pizza', 'pasta', 'burger', 'sandwich', 'noodles', 'rice'
        ]
    
    def extract_dishes(self, review_text: str) -> List[str]:
        """
        Extract dish names from review
        
        Returns:
            List of dish names found
        """
        dishes = []
        text_lower = review_text.lower()
        
        # Pattern matching
        for pattern in self.dish_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            dishes.extend(matches)
        
        # Extract noun phrases that might be dishes
        if NLTK_AVAILABLE:
            try:
                words = word_tokenize(text_lower)
                # Look for food-related bigrams and trigrams
                for i in range(len(words) - 1):
                    bigram = f"{words[i]} {words[i+1]}"
                    if any(keyword in bigram for keyword in self.food_keywords):
                        dishes.append(bigram)
            except:
                pass
        
        # Clean and deduplicate
        dishes = list(set([d.strip() for d in dishes if len(d.strip()) > 3]))
        return dishes[:10]  # Top 10 dishes


class ReviewSummarizer:
    """
    Summarize multiple reviews into key points
    Uses extractive summarization (no GPU needed)
    """
    
    def summarize_reviews(self, reviews: List[str], max_sentences: int = 5) -> str:
        """
        Create summary from multiple reviews
        
        Args:
            reviews: List of review texts
            max_sentences: Number of sentences in summary
            
        Returns:
            Summary string
        """
        if not reviews:
            return "No reviews available"
        
        # Combine all reviews
        all_text = ' '.join(reviews)
        
        if NLTK_AVAILABLE:
            try:
                # Sentence tokenization
                sentences = sent_tokenize(all_text)
                
                if len(sentences) <= max_sentences:
                    return ' '.join(sentences)
                
                # Score sentences by keyword frequency
                word_freq = self._calculate_word_frequency(all_text)
                sentence_scores = {}
                
                for sentence in sentences:
                    score = 0
                    words = word_tokenize(sentence.lower())
                    for word in words:
                        if word in word_freq:
                            score += word_freq[word]
                    sentence_scores[sentence] = score
                
                # Get top sentences
                top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:max_sentences]
                summary = ' '.join([sent for sent, score in top_sentences])
                return summary
            except:
                pass
        
        # Fallback: return first few sentences
        sentences = all_text.split('.')[:max_sentences]
        return '. '.join(sentences) + '.'
    
    def _calculate_word_frequency(self, text: str) -> Dict[str, int]:
        """Calculate word frequency for scoring"""
        try:
            words = word_tokenize(text.lower())
            stop_words = set(stopwords.words('english'))
            words = [w for w in words if w.isalnum() and w not in stop_words]
            return Counter(words)
        except:
            words = re.findall(r'\b\w+\b', text.lower())
            return Counter(words)


class TopicExtractor:
    """
    Extract topics from reviews using LDA
    Identifies what customers talk about most
    """
    
    def __init__(self):
        self.vectorizer = None
        self.lda_model = None
    
    def extract_topics(self, reviews: List[str], num_topics: int = 5, words_per_topic: int = 5) -> List[Dict]:
        """
        Extract topics from reviews
        
        Returns:
            List of topics with keywords
        """
        if not SKLEARN_AVAILABLE or not reviews or len(reviews) < 3:
            return []
        
        try:
            # Vectorize reviews
            self.vectorizer = CountVectorizer(
                max_features=100,
                stop_words='english',
                min_df=2
            )
            doc_term_matrix = self.vectorizer.fit_transform(reviews)
            
            # LDA topic modeling
            self.lda_model = LatentDirichletAllocation(
                n_components=min(num_topics, len(reviews)),
                random_state=42,
                max_iter=10
            )
            self.lda_model.fit(doc_term_matrix)
            
            # Extract topics
            topics = []
            feature_names = self.vectorizer.get_feature_names_out()
            
            for topic_idx, topic in enumerate(self.lda_model.components_):
                top_words_idx = topic.argsort()[-words_per_topic:][::-1]
                top_words = [feature_names[i] for i in top_words_idx]
                
                topics.append({
                    'topic_id': topic_idx,
                    'keywords': top_words,
                    'label': self._generate_topic_label(top_words)
                })
            
            return topics
        except Exception as e:
            print(f"Topic extraction error: {e}")
            return []
    
    def _generate_topic_label(self, keywords: List[str]) -> str:
        """Generate human-readable topic label"""
        # Map keywords to common topics
        if any(word in keywords for word in ['food', 'dish', 'taste', 'delicious']):
            return 'Food Quality'
        elif any(word in keywords for word in ['service', 'staff', 'waiter']):
            return 'Service'
        elif any(word in keywords for word in ['ambiance', 'atmosphere', 'decor']):
            return 'Ambiance'
        elif any(word in keywords for word in ['price', 'value', 'expensive']):
            return 'Pricing'
        else:
            return ' '.join(keywords[:2]).title()


class FakeReviewDetector:
    """
    Detect potentially fake/spam reviews
    Uses heuristics and patterns
    """
    
    def is_fake(self, review_text: str, rating: int, reviewer_history: int = 0) -> Dict[str, Any]:
        """
        Analyze if review might be fake
        
        Returns:
            {
                'is_suspicious': bool,
                'confidence': float,
                'reasons': list
            }
        """
        reasons = []
        suspicion_score = 0
        
        # Check 1: Too short
        if len(review_text) < 20:
            reasons.append("Very short review")
            suspicion_score += 0.2
        
        # Check 2: Too generic
        generic_phrases = ['good', 'nice', 'ok', 'fine', 'average']
        if any(phrase in review_text.lower() for phrase in generic_phrases) and len(review_text) < 50:
            reasons.append("Generic content")
            suspicion_score += 0.3
        
        # Check 3: Extreme rating with neutral text
        if VADER_AVAILABLE:
            analyzer = SentimentIntensityAnalyzer()
            sentiment = analyzer.polarity_scores(review_text)['compound']
            
            if (rating >= 4 and sentiment < 0) or (rating <= 2 and sentiment > 0):
                reasons.append("Rating-sentiment mismatch")
                suspicion_score += 0.4
        
        # Check 4: All caps or excessive punctuation
        if review_text.isupper() or review_text.count('!') > 5:
            reasons.append("Excessive formatting")
            suspicion_score += 0.2
        
        # Check 5: New reviewer with extreme rating
        if reviewer_history == 0 and (rating == 5 or rating == 1):
            reasons.append("New reviewer with extreme rating")
            suspicion_score += 0.3
        
        # Check 6: Competitor mentions
        competitor_keywords = ['better', 'worse', 'compared to', 'instead go to']
        if any(keyword in review_text.lower() for keyword in competitor_keywords):
            reasons.append("Competitor mentions")
            suspicion_score += 0.3
        
        is_suspicious = suspicion_score >= 0.5
        
        return {
            'is_suspicious': is_suspicious,
            'confidence': min(1.0, suspicion_score),
            'reasons': reasons
        }


# Singleton instances for reuse
_sentiment_analyzer = None
_dish_extractor = None
_review_summarizer = None
_topic_extractor = None
_fake_detector = None

def get_sentiment_analyzer():
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = EnhancedSentimentAnalyzer()
    return _sentiment_analyzer

def get_dish_extractor():
    global _dish_extractor
    if _dish_extractor is None:
        _dish_extractor = DishExtractor()
    return _dish_extractor

def get_review_summarizer():
    global _review_summarizer
    if _review_summarizer is None:
        _review_summarizer = ReviewSummarizer()
    return _review_summarizer

def get_topic_extractor():
    global _topic_extractor
    if _topic_extractor is None:
        _topic_extractor = TopicExtractor()
    return _topic_extractor

def get_fake_detector():
    global _fake_detector
    if _fake_detector is None:
        _fake_detector = FakeReviewDetector()
    return _fake_detector
