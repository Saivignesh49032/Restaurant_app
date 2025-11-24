"""
Google Places API Integration for Restaurant Search
Fallback when Gemini API is not available or doesn't return results
"""

import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')


class GooglePlacesSearch:
    """Handles restaurant searches using Google Places API"""
    
    def __init__(self):
        self.api_key = GOOGLE_PLACES_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api/place"
    
    def is_available(self) -> bool:
        """Check if Google Places API is available"""
        return self.api_key is not None and len(self.api_key) > 0
    
    def search_restaurants(
        self,
        city: str,
        cuisines: Optional[List[str]] = None,
        price_range: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Search for restaurants using Google Places API
        
        Args:
            city: City name
            cuisines: List of cuisine types
            price_range: Price range (1-4)
            max_results: Maximum number of results
            
        Returns:
            List of restaurant dictionaries
        """
        if not self.is_available():
            return []
        
        try:
            # Build search query
            query_parts = ["restaurants"]
            if cuisines:
                query_parts.extend(cuisines)
            query_parts.append(city)
            query = " ".join(query_parts)
            
            # Text Search API
            url = f"{self.base_url}/textsearch/json"
            params = {
                'query': query,
                'key': self.api_key,
                'type': 'restaurant'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'OK':
                print(f"Google Places API error: {data.get('status')}")
                return []
            
            restaurants = []
            results = data.get('results', [])[:max_results]
            
            for place in results:
                # Get price level (0-4, where 0 is free and 4 is very expensive)
                # Google uses 0-4, we need to map it
                google_price = place.get('price_level', -1)
                
                # Filter by price range if specified
                if price_range:
                    price_match = False
                    # Google: 1=cheap, 2=moderate, 3=expensive, 4=very expensive
                    # Our system: 1=cheap, 2=moderate, 3=expensive, 4=very expensive
                    if google_price != -1 and int(price_range) == google_price:
                        price_match = True
                    if not price_match:
                        continue
                
                # Get place details for more information
                place_id = place.get('place_id')
                details = self._get_place_details(place_id) if place_id else {}
                
                restaurant = {
                    'name': place.get('name', 'Unknown'),
                    'address': place.get('formatted_address', ''),
                    'rating': place.get('rating', 0),
                    'price_range': google_price if google_price != -1 else None,
                    'latitude': place['geometry']['location']['lat'],
                    'longitude': place['geometry']['location']['lng'],
                    'description': details.get('editorial_summary', {}).get('overview', '') or 
                                 f"A popular restaurant in {city} serving great food.",
                    'cuisines': self._extract_cuisines(place, details),
                    'features': self._extract_features(details),
                    'phone': details.get('formatted_phone_number', ''),
                    'website': details.get('website', ''),
                    'opening_hours': self._format_opening_hours(details.get('opening_hours', {})),
                    'cost_for_two': self._estimate_cost_for_two(google_price),
                    'photos': [photo.get('photo_reference') for photo in place.get('photos', [])[:3]]
                }
                
                # Only include restaurants with 4+ rating
                if restaurant['rating'] >= 4.0:
                    restaurants.append(restaurant)
            
            return restaurants[:max_results]
            
        except Exception as e:
            print(f"Error searching restaurants with Google Places: {e}")
            return []
    
    def _get_place_details(self, place_id: str) -> Dict:
        """Get detailed information about a place"""
        try:
            url = f"{self.base_url}/details/json"
            params = {
                'place_id': place_id,
                'key': self.api_key,
                'fields': 'name,formatted_phone_number,website,opening_hours,editorial_summary,types,price_level'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK':
                return data.get('result', {})
            return {}
        except Exception as e:
            print(f"Error getting place details: {e}")
            return {}
    
    def _extract_cuisines(self, place: Dict, details: Dict) -> List[str]:
        """Extract cuisine types from place data"""
        types = place.get('types', []) + details.get('types', [])
        cuisine_keywords = ['restaurant', 'food', 'meal', 'establishment']
        cuisines = []
        
        for t in types:
            if 'restaurant' in t.lower() and t != 'restaurant':
                cuisine = t.replace('_', ' ').title()
                if cuisine not in cuisines:
                    cuisines.append(cuisine)
        
        # If no specific cuisines found, use generic
        if not cuisines:
            cuisines = ['Multi-cuisine']
        
        return cuisines[:3]  # Limit to 3
    
    def _extract_features(self, details: Dict) -> List[str]:
        """Extract restaurant features"""
        features = []
        # Google Places doesn't directly provide these, but we can infer
        # This would need to be enhanced with additional API calls
        return features
    
    def _format_opening_hours(self, opening_hours: Dict) -> Dict:
        """Format opening hours"""
        if not opening_hours or 'weekday_text' not in opening_hours:
            return {}
        
        hours_dict = {}
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for i, day_text in enumerate(opening_hours.get('weekday_text', [])):
            if i < len(days):
                hours_dict[days[i]] = day_text.split(': ', 1)[-1] if ': ' in day_text else day_text
        
        return hours_dict
    
    def _estimate_cost_for_two(self, price_level: int) -> int:
        """Estimate cost for two based on price level"""
        estimates = {
            1: 400,   # Cheap
            2: 1000,  # Moderate
            3: 2000,  # Expensive
            4: 3500   # Very Expensive
        }
        return estimates.get(price_level, 1000)


# Global instance
google_places_search = GooglePlacesSearch()


def search_restaurants_google(
    city: str,
    cuisines: Optional[List[str]] = None,
    price_range: Optional[str] = None,
    max_results: int = 10
) -> List[Dict]:
    """Convenience function to search restaurants using Google Places"""
    return google_places_search.search_restaurants(
        city=city,
        cuisines=cuisines,
        price_range=price_range,
        max_results=max_results
    )


def is_google_places_available() -> bool:
    """Check if Google Places API is configured"""
    return google_places_search.is_available()
