"""
Cache Manager Service
Manages caching for review analysis results
"""
from datetime import datetime, timedelta
from models import db, ReviewAnalysisCache
import json


class CacheManager:
    """Service for managing analysis cache"""
    
    CACHE_DURATION_HOURS = 24
    
    def __init__(self):
        self.cache_duration = timedelta(hours=self.CACHE_DURATION_HOURS)
    
    def get_cached_analysis(self, place_id, allow_stale=False):
        """
        Get cached analysis for a restaurant
        
        Args:
            place_id: Google Place ID
            allow_stale: Return cache even if expired
            
        Returns:
            dict or None: Cached analysis data
        """
        cache_entry = ReviewAnalysisCache.query.filter_by(place_id=place_id).first()
        
        if not cache_entry:
            return None
        
        # Check if cache is fresh
        cache_age = datetime.utcnow() - cache_entry.last_refreshed
        
        if not allow_stale and cache_age > self.cache_duration:
            return None
        
        # Parse JSON data
        try:
            analysis_data = json.loads(cache_entry.analysis_data)
            analysis_data['cached_at'] = cache_entry.last_refreshed.isoformat()
            analysis_data['cache_age_hours'] = cache_age.total_seconds() / 3600
            return analysis_data
        except json.JSONDecodeError:
            return None
    
    def save_analysis(self, place_id, analysis_data):
        """
        Save analysis to cache
        
        Args:
            place_id: Google Place ID
            analysis_data: Analysis results dict
            
        Returns:
            bool: Success status
        """
        try:
            # Check if entry exists
            cache_entry = ReviewAnalysisCache.query.filter_by(place_id=place_id).first()
            
            # Convert to JSON
            analysis_json = json.dumps(analysis_data)
            
            if cache_entry:
                # Update existing
                cache_entry.analysis_data = analysis_json
                cache_entry.last_refreshed = datetime.utcnow()
            else:
                # Create new
                cache_entry = ReviewAnalysisCache(
                    place_id=place_id,
                    analysis_data=analysis_json,
                    analyzed_at=datetime.utcnow(),
                    last_refreshed=datetime.utcnow()
                )
                db.session.add(cache_entry)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving analysis cache: {str(e)}")
            return False
    
    def invalidate_cache(self, place_id):
        """Delete cached analysis for a restaurant"""
        try:
            ReviewAnalysisCache.query.filter_by(place_id=place_id).delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error invalidating cache: {str(e)}")
            return False
    
    def get_cache_status(self, place_id):
        """Get cache status information"""
        cache_entry = ReviewAnalysisCache.query.filter_by(place_id=place_id).first()
        
        if not cache_entry:
            return {
                'cached': False,
                'age_hours': None,
                'is_fresh': False
            }
        
        cache_age = datetime.utcnow() - cache_entry.last_refreshed
        age_hours = cache_age.total_seconds() / 3600
        
        return {
            'cached': True,
            'cached_at': cache_entry.last_refreshed.isoformat(),
            'age_hours': age_hours,
            'is_fresh': cache_age < self.cache_duration
        }
