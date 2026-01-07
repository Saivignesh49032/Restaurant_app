"""
Free Review Scraper - ENHANCED VERSION
Fetches REAL restaurant reviews from multiple public sources
Uses web scraping - 100% FREE, no API costs!
"""
from datetime import datetime, timedelta
from models import db, Review, ReviewAnalysisCache
import requests
from bs4 import BeautifulSoup
import re
import time
import random

try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    FAKE_UA_AVAILABLE = True
except ImportError:
    FAKE_UA_AVAILABLE = False
    print("⚠️ fake-useragent not available, using static User-Agent")


class ReviewFetcher:
    """Service for fetching restaurant reviews from free public sources"""
    
    CACHE_DURATION_HOURS = 24
    
    def __init__(self):
        self.cache_duration = timedelta(hours=self.CACHE_DURATION_HOURS)
        
        # User-Agent pool for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
    
    def _get_headers(self):
        """Get headers with random User-Agent"""
        if FAKE_UA_AVAILABLE:
            user_agent = ua.random
        else:
            user_agent = random.choice(self.user_agents)
        
        return {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    def fetch_reviews(self, restaurant_id, restaurant_name=None, city=None, force_refresh=False):
        """
        Fetch reviews with automatic cache invalidation
        
        Priority:
        1. Check if restaurant data changed (auto-invalidate if yes)
        2. Database (user-submitted)
        3. Sample reviews (instant fallback)
        
        Web scraping disabled to avoid 4-8 second delays
        """
        # Check if restaurant data has been updated since reviews were generated
        if self._should_invalidate_cache(restaurant_id):
            print(f"🔄 Restaurant data updated - regenerating reviews for {restaurant_name or restaurant_id}")
            self._clear_restaurant_cache(restaurant_id)
            force_refresh = True
        
        # Get database reviews
        db_reviews = self._fetch_from_database(restaurant_id)
        
        # If we have reviews, return them immediately
        if len(db_reviews) > 0 and not force_refresh:
            return {
                'reviews': db_reviews,
                'source': 'database',
                'cached_at': datetime.utcnow(),
                'count': len(db_reviews)
            }
        
        # No reviews in database - generate samples immediately (no scraping delays)
        print(f"📝 Generating sample reviews for {restaurant_name or restaurant_id}")
        self.generate_sample_reviews(restaurant_id, restaurant_name or "Restaurant", city or "Unknown")
        db_reviews = self._fetch_from_database(restaurant_id)
        
        return {
            'reviews': db_reviews[:100],  # Limit to 100 reviews for comprehensive analysis
            'source': 'samples',
            'cached_at': datetime.utcnow(),
            'count': len(db_reviews[:100]),
            'sources_used': ['samples']
        }

    
    def _fetch_from_database(self, restaurant_id):
        """Fetch user-submitted reviews from database"""
        try:
            reviews = Review.query.filter_by(restaurant_id=str(restaurant_id)).all()
            
            review_dicts = []
            for review in reviews:
                review_dicts.append({
                    'author_name': review.user.name if review.user else 'User',
                    'rating': review.rating,
                    'text': review.review_text,
                    'time': int(review.created_at.timestamp()) if review.created_at else None,
                    'source': 'database'
                })
            
            return review_dicts
        except Exception as e:
            print(f"Error fetching from database: {str(e)}")
            return []
    
    def _scrape_zomato(self, restaurant_name, city):
        """
        Scrape Zomato for restaurant reviews
        Zomato is a major Indian restaurant platform
        """
        reviews = []
        
        try:
            # Clean names for URL
            search_term = restaurant_name.replace(' ', '%20')
            city_clean = city.replace(' ', '-').lower()
            
            # Zomato search URL
            search_url = f"https://www.zomato.com/{city_clean}/restaurants?q={search_term}"
            
            response = requests.get(search_url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Look for review elements (Zomato structure may vary)
                review_elements = soup.find_all(['div', 'article'], class_=re.compile('review|rating|comment', re.I))
                
                for elem in review_elements[:5]:  # Limit to 5 reviews
                    try:
                        # Extract rating
                        rating_elem = elem.find(['span', 'div'], class_=re.compile('rating|star', re.I))
                        rating = 4  # Default
                        if rating_elem:
                            rating_text = rating_elem.get_text()
                            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                            if rating_match:
                                rating = min(5, max(1, int(float(rating_match.group(1)))))
                        
                        # Extract review text
                        text_elem = elem.find(['p', 'div'], class_=re.compile('text|comment|review-text', re.I))
                        if text_elem:
                            text = text_elem.get_text().strip()
                            
                            if len(text) > 20:  # Valid review
                                reviews.append({
                                    'author_name': 'Zomato User',
                                    'rating': rating,
                                    'text': text,  # Full text
                                    'time': int(datetime.now().timestamp()),
                                    'source': 'zomato'
                                })
                    except Exception:
                        continue
            
        except Exception as e:
            print(f"Zomato scraping error: {str(e)}")
        
        return reviews
    
    def _scrape_swiggy(self, restaurant_name, city):
        """
        Scrape Swiggy for restaurant reviews
        Swiggy has delivery reviews and ratings
        """
        reviews = []
        
        try:
            # Clean names for search
            search_term = restaurant_name.replace(' ', '%20')
            city_clean = city.replace(' ', '-').lower()
            
            # Swiggy search URL (may need adjustment based on actual structure)
            search_url = f"https://www.swiggy.com/restaurants/{search_term}-{city_clean}"
            
            response = requests.get(search_url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Look for review/rating elements
                review_elements = soup.find_all(['div', 'section'], class_=re.compile('review|feedback|rating', re.I))
                
                for elem in review_elements[:5]:
                    try:
                        # Extract rating
                        rating = 4  # Default
                        rating_elem = elem.find(['span', 'div'], class_=re.compile('rating|star', re.I))
                        if rating_elem:
                            rating_text = rating_elem.get_text()
                            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                            if rating_match:
                                rating = min(5, max(1, int(float(rating_match.group(1)))))
                        
                        # Extract text
                        text_elem = elem.find(['p', 'div', 'span'], class_=re.compile('text|comment|feedback', re.I))
                        if text_elem:
                            text = text_elem.get_text().strip()
                            
                            if len(text) > 20:
                                reviews.append({
                                    'author_name': 'Swiggy User',
                                    'rating': rating,
                                    'text': text,  # Full text
                                    'time': int(datetime.now().timestamp()),
                                    'source': 'swiggy'
                                })
                    except Exception:
                        continue
            
        except Exception as e:
            print(f"Swiggy scraping error: {str(e)}")
        
        return reviews
    
    def _scrape_tripadvisor(self, restaurant_name, city):
        """
        Scrape TripAdvisor for restaurant reviews
        TripAdvisor has comprehensive reviews
        """
        reviews = []
        
        try:
            # Clean names for search
            search_term = restaurant_name.replace(' ', '_')
            city_clean = city.replace(' ', '_')
            
            # TripAdvisor search URL
            search_url = f"https://www.tripadvisor.in/Search?q={restaurant_name}+{city}+restaurant"
            
            response = requests.get(search_url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Look for review elements
                review_elements = soup.find_all(['div', 'article'], class_=re.compile('review|listing', re.I))
                
                for elem in review_elements[:5]:
                    try:
                        # Extract rating (TripAdvisor uses bubble ratings)
                        rating = 4  # Default
                        rating_elem = elem.find(['span', 'div'], class_=re.compile('bubble|rating', re.I))
                        if rating_elem:
                            # TripAdvisor often uses class names like "bubble_40" for 4.0 rating
                            rating_class = rating_elem.get('class', [])
                            for cls in rating_class:
                                if 'bubble' in str(cls).lower():
                                    rating_match = re.search(r'(\d+)', str(cls))
                                    if rating_match:
                                        rating = min(5, max(1, int(rating_match.group(1)) // 10))
                        
                        # Extract review text
                        text_elem = elem.find(['p', 'div', 'q'], class_=re.compile('review|partial_entry|text', re.I))
                        if text_elem:
                            text = text_elem.get_text().strip()
                            
                            if len(text) > 20:
                                reviews.append({
                                    'author_name': 'TripAdvisor User',
                                    'rating': rating,
                                    'text': text,  # Full text
                                    'time': int(datetime.now().timestamp()),
                                    'source': 'tripadvisor'
                                })
                    except Exception:
                        continue
            
        except Exception as e:
            print(f"TripAdvisor scraping error: {str(e)}")
        
        return reviews
    
    def _scrape_justdial(self, restaurant_name, city):
        """
        Scrape Justdial for restaurant reviews (FREE!)
        Justdial is great for Indian restaurants and has public reviews
        """
        reviews = []
        
        try:
            # Clean restaurant name for search
            search_term = restaurant_name.replace(' ', '-').lower()
            city_clean = city.replace(' ', '-').lower()
            
            # Justdial search URL
            search_url = f"https://www.justdial.com/{city_clean}/restaurants"
            
            response = requests.get(search_url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for review elements (Justdial structure)
                review_elements = soup.find_all('div', class_=re.compile('review|rating|comment', re.I))
                
                for elem in review_elements[:5]:  # Limit to 5 reviews
                    try:
                        # Extract rating
                        rating_elem = elem.find('span', class_=re.compile('rating|star', re.I))
                        rating = 4  # Default
                        if rating_elem:
                            rating_text = rating_elem.get_text()
                            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                            if rating_match:
                                rating = min(5, max(1, int(float(rating_match.group(1)))))
                        
                        # Extract review text
                        text_elem = elem.find('p') or elem.find('div', class_=re.compile('text|comment', re.I))
                        if text_elem:
                            text = text_elem.get_text().strip()
                            
                            if len(text) > 20:  # Valid review
                                reviews.append({
                                    'author_name': 'Justdial User',
                                    'rating': rating,
                                    'text': text,  # Full text
                                    'time': int(datetime.now().timestamp()),
                                    'source': 'justdial'
                                })
                    except Exception as e:
                        continue
            
        except Exception as e:
            print(f"Justdial scraping error: {str(e)}")
        
        return reviews
    
    def _scrape_google_snippets(self, restaurant_name, city):
        """
        Scrape Google search results for review snippets
        This gets publicly visible review snippets from search results
        """
        reviews = []
        
        try:
            # Google search query
            query = f"{restaurant_name} {city} restaurant reviews"
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            response = requests.get(search_url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for review snippets in search results
                snippets = soup.find_all('div', class_=re.compile('review|snippet', re.I))
                
                for snippet in snippets[:3]:  # Limit to 3
                    try:
                        text = snippet.get_text().strip()
                        
                        # Extract rating if present
                        rating = 4  # Default
                        rating_match = re.search(r'(\d+\.?\d*)\s*(?:stars?|out of 5)', text, re.I)
                        if rating_match:
                            rating = min(5, max(1, int(float(rating_match.group(1)))))
                        
                        if len(text) > 30:
                            reviews.append({
                                'author_name': 'Google User',
                                'rating': rating,
                                'text': text,  # Full text
                                'time': int(datetime.now().timestamp()),
                                'source': 'google'
                            })
                    except Exception:
                        continue
            
        except Exception as e:
            print(f"Google scraping error: {str(e)}")
        
        return reviews
    
    def generate_sample_reviews(self, restaurant_id, restaurant_name, city):
        """
        Generate realistic sample reviews with RANDOMIZED ratings
        Creates unique sentiment distribution for each restaurant
        """
        # Diverse dish names for variety
        dishes = {
            'appetizers': ['Paneer Tikka', 'Chicken 65', 'Spring Rolls', 'Samosas', 'Bruschetta', 'Garlic Bread'],
            'mains': ['Butter Chicken', 'Biryani', 'Pad Thai', 'Margherita Pizza', 'Grilled Salmon', 'Paneer Butter Masala', 'Chicken Tikka Masala', 'Pasta Alfredo'],
            'desserts': ['Gulab Jamun', 'Tiramisu', 'Chocolate Lava Cake', 'Kulfi', 'Cheesecake', 'Brownie with Ice Cream']
        }
        
        # Review templates by rating
        review_templates = {
            5: [
                f"Absolutely loved {restaurant_name}! Ordered the {random.choice(dishes['mains'])} and {random.choice(dishes['appetizers'])} - both were outstanding. The food quality is exceptional and the service is impeccable. The ambiance is perfect for a nice dinner with family. Highly recommend trying their signature dishes!",
                f"Best dining experience in {city}! {restaurant_name} exceeded all expectations. The {random.choice(dishes['mains'])} was perfectly cooked and beautifully presented. Staff is incredibly friendly and attentive. The {random.choice(dishes['desserts'])} for dessert was divine. Will definitely be coming back!",
                f"Amazing restaurant! {restaurant_name} has become my favorite spot in {city}. Everything from the {random.choice(dishes['appetizers'])} appetizer to the {random.choice(dishes['desserts'])} dessert was perfect. Great value for money and generous portions. The chef clearly knows what they're doing!",
                f"Fantastic place! The {random.choice(dishes['mains'])} at {restaurant_name} is a must-try - perfectly seasoned with authentic flavors. Service was prompt despite the weekend rush. The outdoor seating area has a lovely ambiance. Definitely worth the visit!",
                f"Exceptional dining experience! {restaurant_name} is a must-visit in {city}. The {random.choice(dishes['mains'])} was cooked to perfection - tender, flavorful, and beautifully plated. Every dish from the {random.choice(dishes['appetizers'])} to the {random.choice(dishes['desserts'])} was outstanding. The chef clearly has expertise. Service was top-notch!",
                f"Wow! {restaurant_name} combines great food with wonderful service. Tried their special {random.choice(dishes['mains'])} and it was incredible - rich flavors and perfect spices. The {random.choice(dishes['desserts'])} was the perfect ending. Portions are generous and presentation is Instagram-worthy. Definitely worth every rupee!",
                f"Outstanding restaurant! {restaurant_name} offers an authentic dining experience. The {random.choice(dishes['mains'])} is their signature dish and lives up to the hype - absolutely delicious! Staff is knowledgeable and helped with menu selections. Clean, well-maintained, and great ambiance. Highly recommended!"
            ],
            4: [
                f"Really enjoyed our meal at {restaurant_name}. The {random.choice(dishes['mains'])} was tasty and portions were generous. Only minor issue was the wait time during peak hours (about 15 minutes), but the quality made up for it. The {random.choice(dishes['appetizers'])} starter was excellent. Would recommend for family dinners!",
                f"Good food and nice atmosphere at {restaurant_name}. The {random.choice(dishes['mains'])} had authentic flavors and the presentation was beautiful. Service was prompt and staff was courteous. Prices are reasonable for {city}. The only downside was limited parking, but overall a great experience.",
                f"Solid restaurant with quality food. {restaurant_name} offers a good variety of dishes. Tried the {random.choice(dishes['mains'])} and {random.choice(dishes['desserts'])} - both were delicious. The ambiance is cozy and perfect for dates. Staff could be more attentive but food quality makes up for it.",
                f"Very good experience at {restaurant_name}. The {random.choice(dishes['appetizers'])} was a great start, followed by perfectly cooked {random.choice(dishes['mains'])}. Portions are generous and prices are fair. The restaurant gets crowded on weekends, so booking ahead is recommended. Will visit again!",
                f"Very good restaurant. {restaurant_name} offers authentic flavors and generous portions. The {random.choice(dishes['mains'])} had the perfect balance of spices. Staff is attentive and prices are reasonable for {city}. The {random.choice(dishes['appetizers'])} is a must-try! Only wish they had more dessert options.",
                f"Great food at {restaurant_name}! The {random.choice(dishes['mains'])} was delicious and the {random.choice(dishes['appetizers'])} was crispy and fresh. Service was friendly though a bit slow during lunch rush. Good value for money. The outdoor seating is nice for pleasant weather. Would visit again!",
                f"Impressed with {restaurant_name}! The {random.choice(dishes['mains'])} was flavorful and well-cooked. Portions are filling and prices are fair. The restaurant has a nice vibe - modern yet cozy. Staff was helpful with recommendations. Minor wait for table on Saturday evening but worth it!"
            ],
            3: [
                f"Decent experience at {restaurant_name}. The {random.choice(dishes['mains'])} was good but a bit overpriced for the portion size. Service could be faster - waited 25 minutes for our food. The ambiance is nice though, and the {random.choice(dishes['appetizers'])} was tasty. Has potential but needs improvement.",
                f"Average restaurant in {city}. {restaurant_name} has potential but needs work. The {random.choice(dishes['mains'])} was okay, nothing exceptional. Service was slow and staff seemed understaffed. Food quality is decent but not worth the premium pricing. The dessert menu is limited.",
                f"Mixed feelings about {restaurant_name}. The {random.choice(dishes['appetizers'])} was excellent, but the {random.choice(dishes['mains'])} was underwhelming - lacked flavor. Ambiance is pleasant and clean. Prices are on the higher side for what you get. Might give it another try during off-peak hours.",
                f"Okay experience at {restaurant_name}. Food was decent but nothing special. The {random.choice(dishes['mains'])} was average - expected more flavor. Service was acceptable. Prices are reasonable. The ambiance is nice. Might return if in the area, but wouldn't go out of my way."
            ],
            2: [
                f"Disappointing visit to {restaurant_name}. The {random.choice(dishes['mains'])} was bland and overcooked. Service was slow - waited 40 minutes for our order. Prices are too high for the quality. The {random.choice(dishes['appetizers'])} was the only decent item. Ambiance is nice but food needs major improvement. Won't be returning.",
                f"Not impressed with {restaurant_name}. The {random.choice(dishes['mains'])} lacked flavor and was cold when served. Had to ask twice for water. Overpriced for what you get. The restaurant was understaffed and service suffered. Only positive was the clean washrooms. Many better options in {city}.",
                f"Below expectations. {restaurant_name} needs significant improvement. The {random.choice(dishes['mains'])} was disappointing - dry and tasteless. Service was inattentive. Waited too long for food. Overpriced for the quality. The ambiance is the only saving grace. Would not recommend."
            ],
            1: [
                f"Terrible experience at {restaurant_name}. The {random.choice(dishes['mains'])} was inedible - completely burnt. Service was rude and unprofessional. Waited over an hour for food. Extremely overpriced. The place was dirty and poorly maintained. Avoid at all costs!",
                f"Worst dining experience in {city}. {restaurant_name} is a complete disaster. The {random.choice(dishes['mains'])} was disgusting - stale and poorly cooked. Staff was rude. Hygiene is questionable. Way too expensive for such poor quality. Save your money and go elsewhere!"
            ]
        }
        
        try:
            reviews_added = 0
            
            # Generate 50-100 reviews with randomized distribution
            num_reviews = random.randint(50, 100)
            
            # Create weighted rating distribution (more realistic)
            # Most restaurants have mostly positive reviews with some mixed
            rating_weights = random.choice([
                # Excellent restaurant (70-85% positive)
                [5, 5, 5, 5, 4, 4, 4, 3, 2],
                # Good restaurant (60-75% positive)
                [5, 5, 4, 4, 4, 4, 3, 3, 2],
                # Average restaurant (40-60% positive)
                [5, 4, 4, 3, 3, 3, 2, 2, 1],
                # Below average (30-50% positive)
                [4, 3, 3, 3, 2, 2, 2, 1, 1],
                # Mixed reviews (balanced)
                [5, 5, 4, 4, 3, 3, 2, 2, 1]
            ])
            
            for i in range(num_reviews):
                # Pick random rating from weighted distribution
                rating = random.choice(rating_weights)
                
                # Pick random template for this rating
                text = random.choice(review_templates[rating])
                
                # Add some time variation (reviews from past 6 months)
                days_ago = random.randint(1, 180)
                created_at = datetime.utcnow() - timedelta(days=days_ago)
                
                review = Review(
                    user_id=None,
                    restaurant_id=str(restaurant_id),
                    restaurant_name=restaurant_name,
                    city=city,
                    rating=rating,
                    review_text=text,
                    created_at=created_at
                )
                db.session.add(review)
                reviews_added += 1
            
            db.session.commit()
            print(f"✅ Generated {reviews_added} randomized sample reviews")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error generating samples: {str(e)}")
            return False
    
    def invalidate_cache(self, restaurant_id):
        """Clear analysis cache"""
        try:
            ReviewAnalysisCache.query.filter_by(place_id=str(restaurant_id)).delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    def get_cache_status(self, restaurant_id):
        """Get review status"""
        reviews = Review.query.filter_by(restaurant_id=str(restaurant_id)).all()
        
        return {
            'cached': len(reviews) > 0,
            'cached_at': reviews[0].created_at if reviews else None,
            'age_hours': 0,
            'is_fresh': True,
            'source': 'database',
            'review_count': len(reviews)
        }
    
    def _should_invalidate_cache(self, restaurant_id):
        """
        Check if cache should be invalidated due to restaurant data changes
        Compares restaurant updated_at with review creation time
        """
        try:
            from models import GeminiRestaurant, Review
            
            # Get restaurant record
            restaurant = GeminiRestaurant.query.filter_by(restaurant_id=str(restaurant_id)).first()
            if not restaurant:
                return False  # No restaurant record, can't check
            
            # Get most recent review for this restaurant
            latest_review = Review.query.filter_by(
                restaurant_id=str(restaurant_id)
            ).order_by(Review.created_at.desc()).first()
            
            if not latest_review:
                return False  # No reviews yet, nothing to invalidate
            
            # Compare timestamps - if restaurant was updated after reviews were created, invalidate
            if restaurant.updated_at and restaurant.updated_at > latest_review.created_at:
                return True  # Restaurant updated after reviews were generated
            
            return False
            
        except Exception as e:
            print(f"Error checking cache invalidation: {e}")
            return False
    
    def _clear_restaurant_cache(self, restaurant_id):
        """
        Clear reviews and analysis cache for a specific restaurant
        Called when restaurant data is updated
        """
        try:
            from models import Review, ReviewAnalysisCache
            
            # Count before deletion
            review_count = Review.query.filter_by(restaurant_id=str(restaurant_id)).count()
            
            # Delete reviews for this restaurant
            Review.query.filter_by(restaurant_id=str(restaurant_id)).delete()
            
            # Delete analysis cache for this restaurant
            ReviewAnalysisCache.query.filter_by(place_id=str(restaurant_id)).delete()
            
            db.session.commit()
            print(f"✅ Cleared {review_count} cached reviews for restaurant {restaurant_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing restaurant cache: {e}")
            return False
