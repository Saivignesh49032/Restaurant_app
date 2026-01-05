from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reviews = db.relationship('Review', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Review(db.Model):
    """User-submitted restaurant reviews"""
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    restaurant_id = db.Column(db.String(200), nullable=False, index=True)
    restaurant_name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'restaurant_id', name='unique_user_restaurant_review'),
        db.Index('idx_restaurant_rating', 'restaurant_id', 'rating'),
    )
    
    def to_dict(self):
        """Convert review to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else 'Anonymous',
            'restaurant_id': self.restaurant_id,
            'restaurant_name': self.restaurant_name,
            'city': self.city,
            'rating': self.rating,
            'review_text': self.review_text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Review {self.id} by User {self.user_id} for {self.restaurant_name}>'


class RestaurantReview(db.Model):
    """Store Google reviews in database (Hybrid Approach)"""
    __tablename__ = 'restaurant_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(200), nullable=False, index=True)
    restaurant_name = db.Column(db.String(200))
    author_name = db.Column(db.String(100))
    author_photo = db.Column(db.String(500))
    rating = db.Column(db.Integer)
    review_text = db.Column(db.Text)
    review_time = db.Column(db.Integer)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('place_id', 'review_time', 'author_name'),
        db.Index('idx_place_fetched', 'place_id', 'fetched_at'),
    )
    
    def to_dict(self):
        return {
            'author_name': self.author_name,
            'author_photo': self.author_photo,
            'rating': self.rating,
            'text': self.review_text,
            'time': self.review_time
        }
    
    def __repr__(self):
        return f'<RestaurantReview {self.place_id}>'


class ReviewAnalysisCache(db.Model):
    """Cache AI analysis results"""
    __tablename__ = 'review_analysis_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(200), unique=True, nullable=False)
    analysis_data = db.Column(db.Text)
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_refreshed = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ReviewAnalysisCache {self.place_id}>'




class UserPreference(db.Model):
    """User preferences for personalization"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    favorite_cuisines = db.Column(db.Text)  # JSON string
    dietary_restrictions = db.Column(db.Text)  # JSON string
    budget_preference = db.Column(db.Integer, default=2)
    visit_type = db.Column(db.String(20), default='visit')
    table_booking = db.Column(db.String(10), default='No')
    moods = db.Column(db.Text)  # JSON string
    occasions = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('preferences', uselist=False))
    
    def __repr__(self):
        return f'<UserPreference for User {self.user_id}>'


def init_db(app):
    """Initialize database with app context"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully")


class GeminiRestaurant(db.Model):
    """Store restaurants fetched from Gemini API permanently."""
    __tablename__ = 'gemini_restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.String(200), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    city = db.Column(db.String(100), nullable=False, index=True)
    address = db.Column(db.Text)
    rating = db.Column(db.Float)
    cuisines = db.Column(db.Text)  # Comma-separated
    cost_for_two = db.Column(db.String(50))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    phone = db.Column(db.String(50))
    hours = db.Column(db.Text)
    features = db.Column(db.Text)  # JSON string
    description = db.Column(db.Text)
    place_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary format compatible with search results."""
        return {
            'Restaurant ID': self.restaurant_id,
            'id': self.restaurant_id,
            'Restaurant Name': self.name,
            'name': self.name,
            'City': self.city,
            'city': self.city,
            'address': self.address,
            'Aggregate rating': self.rating,
            'rating': self.rating,
            'Cuisines': self.cuisines,
            'cuisines': self.cuisines.split(',') if self.cuisines else [],
            'Average Cost for two': self.cost_for_two,
            'cost_for_two': self.cost_for_two,
            'Latitude': self.latitude,
            'latitude': self.latitude,
            'Longitude': self.longitude,
            'longitude': self.longitude,
            'phone': self.phone,
            'hours': self.hours,
            'features': self.features,
            'description': self.description,
            'place_id': self.place_id
        }

class SearchCache(db.Model):
    """Cache search results to avoid redundant API calls."""
    __tablename__ = 'search_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    search_key = db.Column(db.String(200), unique=True, nullable=False, index=True)
    city = db.Column(db.String(100), nullable=False)
    cuisines = db.Column(db.Text)
    filters = db.Column(db.Text)  # JSON string
    result_ids = db.Column(db.Text)  # Comma-separated restaurant IDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def generate_key(city, cuisines=None, filters=None):
        """Generate a unique key for search parameters."""
        import hashlib
        import json
        
        key_data = {
            'city': city.lower().strip(),
            'cuisines': sorted(cuisines) if cuisines else [],
            'filters': filters or {}
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
