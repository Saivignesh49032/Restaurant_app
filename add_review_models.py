"""
Script to add new database models for review analysis
"""

# Read the models.py file
with open(r'c:\Users\saivi\OneDrive\Desktop\Restaurant_App\models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# New models to add
new_models = '''

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

'''

# Find the position to insert (before init_db function)
insert_pos = content.find('def init_db(app):')

if insert_pos == -1:
    print("Error: Could not find init_db function")
else:
    # Insert the new models
    new_content = content[:insert_pos] + new_models + '\n' + content[insert_pos:]
    
    # Write back
    with open(r'c:\Users\saivi\OneDrive\Desktop\Restaurant_App\models.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Successfully added RestaurantReview and ReviewAnalysisCache models")
