"""
Gemini API Integration for Restaurant Search and Recommendations
Uses Google's Gemini AI to find restaurants and get detailed information
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime

import google.generativeai as genai

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found in environment variables. Gemini features will be disabled.")


class GeminiRestaurantSearch:
    """Handles restaurant searches using Gemini AI"""

    def __init__(self):
        self.model = None
        if GEMINI_API_KEY:
            try:
                # First, try to list available models
                print("🔍 Listing available Gemini models...")
                try:
                    available_models = genai.list_models()
                    # Filter models that support generateContent
                    compatible_models = [
                        m.name for m in available_models 
                        if 'generateContent' in m.supported_generation_methods
                    ]
                    print(f"📋 Found {len(compatible_models)} compatible models")
                    for model_name in compatible_models[:5]:  # Show first 5
                        print(f"   - {model_name}")
                    
                    # Try to use the first compatible model
                    if compatible_models:
                        # Prefer flash models for speed
                        flash_models = [m for m in compatible_models if 'flash' in m.lower()]
                        model_to_use = flash_models[0] if flash_models else compatible_models[0]
                        
                        self.model = genai.GenerativeModel(model_to_use)
                        print(f"✅ Initialized Gemini model: {model_to_use}")
                    else:
                        raise RuntimeError("No compatible models found")
                        
                except Exception as list_error:
                    print(f"⚠️  Could not list models: {list_error}")
                    # Fallback to trying known model names without 'models/' prefix
                    fallback_models = [
                        "gemini-pro",
                        "gemini-1.5-pro-latest",
                        "gemini-1.0-pro"
                    ]
                    for model_name in fallback_models:
                        try:
                            self.model = genai.GenerativeModel(model_name)
                            print(f"✅ Initialized Gemini model (fallback): {model_name}")
                            break
                        except Exception as model_error:
                            print(f"⚠️  Failed to initialize '{model_name}': {model_error}")
                    
                if self.model is None:
                    raise RuntimeError("No compatible Gemini model could be initialized")
            except Exception as e:
                print(f"❌ Error initializing Gemini model: {e}")
                self.model = None

    def is_available(self) -> bool:
        """Check if Gemini API is available"""
        return self.model is not None and GEMINI_API_KEY is not None

    def search_restaurants(
        self,
        city: str,
        cuisines: Optional[List[str]] = None,
        price_range: Optional[str] = None,
        visit_type: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict]:
        """Use Gemini to find restaurants that match the filters."""
        if not self.is_available():
            return []

        try:
            prompt = self._build_search_prompt(city, cuisines, price_range, visit_type, max_results)
            response = self.model.generate_content(prompt)
            restaurants = self._parse_response(response.text)
            return restaurants[:max_results]
        except Exception as e:
            print(f"Error searching restaurants with Gemini: {e}")
            return []

    def get_restaurant_details(self, restaurant_name: str, city: str) -> Optional[Dict]:
        """Get detailed information about a specific restaurant."""
        if not self.is_available():
            return None

        try:
            prompt = f"""You are a restaurant information expert. Provide comprehensive, accurate information about "{restaurant_name}" located in {city}, India.

Return ONLY valid JSON with the following structure (no markdown, no extra commentary):
{{
    "name": "Restaurant Name",
    "address": "Full address with street, area, city, state",
    "cuisines": ["Cuisine1", "Cuisine2"],
    "rating": 4.5,
    "price_range": 1,
    "description": "At least 150 words covering concept, ambiance, specialties, unique points, and dining experience",
    "features": ["Online Delivery", "Table Booking", "Outdoor Seating", "Parking", "Wi-Fi", "Live Music"],
    "phone": "Phone number with country code if available",
    "email": "Email if available",
    "website": "Website URL if available",
    "opening_hours": {{
        "monday": "9:00 AM - 10:00 PM",
        "tuesday": "9:00 AM - 10:00 PM",
        "wednesday": "9:00 AM - 10:00 PM",
        "thursday": "9:00 AM - 10:00 PM",
        "friday": "9:00 AM - 11:00 PM",
        "saturday": "9:00 AM - 11:00 PM",
        "sunday": "10:00 AM - 10:00 PM"
    }},
    "specialties": ["Signature dish 1", "Signature dish 2", "Popular item 3"],
    "dietary_options": ["Vegetarian", "Vegan", "Gluten-Free", "Halal"],
    "ambiance": "casual/romantic/family-friendly/fine-dining",
    "parking": "available/not available/valet",
    "wifi": true,
    "outdoor_seating": true,
    "latitude": 12.9716,
    "longitude": 77.5946,
    "cost_for_two": 1500
}}

If the restaurant does not exist or you cannot find information, return {{"error": "Restaurant not found"}} only.
"""
            response = self.model.generate_content(prompt)
            details = self._parse_json_response(response.text)

            if details and "error" not in details:
                return details
            return None
        except Exception as e:
            print(f"Error getting restaurant details: {e}")
            return None

    def get_recommendations(
        self,
        city: str,
        preferences: Dict,
        max_results: int = 10
    ) -> List[Dict]:
        """Get AI-powered restaurant recommendations based on preferences."""
        if not self.is_available():
            return []

        try:
            prompt = f"""Based on the following preferences, recommend {max_results} restaurants in {city}, India.

Preferences:
- Cuisines: {', '.join(preferences.get('cuisines', [])) if preferences.get('cuisines') else 'Any'}
- Price Range: {preferences.get('price_range', 'Any')}
- Visit Type: {preferences.get('visit_type', 'Any')}
- Table Booking: {preferences.get('table_booking', 'Not specified')}

Return ONLY valid JSON array (no markdown) where each object contains:
{{
    "name": "Restaurant Name",
    "cuisines": ["Cuisine1", "Cuisine2"],
    "rating": 4.5,
    "price_range": "Moderate",
    "address": "Address",
    "description": "Why this restaurant matches the preferences",
    "features": ["feature1", "feature2"]
}}
"""
            response = self.model.generate_content(prompt)
            recommendations = self._parse_json_response(response.text)
            if isinstance(recommendations, list):
                return recommendations[:max_results]
            return []
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []

    def _build_search_prompt(
        self,
        city: str,
        cuisines: Optional[List[str]],
        price_range: Optional[str],
        visit_type: Optional[str],
        max_results: int
    ) -> str:
        """Build the search prompt for Gemini."""

        prompt = f"You are a restaurant search expert. Find {max_results} real, existing restaurants in {city}, India."

        if cuisines:
            prompt += f" The restaurants must serve {', '.join(cuisines)} cuisine."

        price_text = 'Any'
        if price_range:
            price_text = {
                '1': 'budget-friendly (average cost for two under ₹500)',
                '2': 'moderate (average cost for two ₹500-1500)',
                '3': 'expensive (average cost for two ₹1500-3000)',
                '4': 'very expensive (average cost for two above ₹3000)'
            }.get(str(price_range), str(price_range))
            prompt += f" Price range must be {price_text}."

        if visit_type == 'delivery':
            prompt += " The restaurants must offer reliable online delivery."
        elif visit_type == 'visit':
            prompt += " The restaurants should be suitable for dining in."

        prompt += f"""

IMPORTANT: Provide REAL, EXISTING restaurants in {city}, India with COMPLETE, accurate information.

Return ONLY valid JSON array (no markdown, no commentary). The array must contain {max_results} objects or fewer, each with COMPLETE details:
{{
    "name": "Restaurant Name",
    "cuisines": ["Cuisine1", "Cuisine2"],
    "rating": 4.5,
    "price_range": {price_range if price_range else 'null'},
    "price_range_text": "{price_text}",
    "address": "Complete street address with area, {city}, India",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "description": "Detailed 2-3 sentence description covering ambiance, specialties, and why people visit",
    "features": ["Online Delivery", "Table Booking", "Wi-Fi", "Parking", "Outdoor Seating", "Live Music"],
    "cost_for_two": 1200,
    "phone": "+91 12345 67890",
    "opening_hours": "10:00 AM - 11:00 PM",
    "specialties": ["Signature dish 1", "Signature dish 2", "Popular item 3"],
    "dietary_options": ["Vegetarian", "Vegan", "Gluten-Free"],
    "ambiance": "casual/romantic/family-friendly/fine-dining",
    "parking": "available/not available/valet",
    "wifi": true,
    "outdoor_seating": false,
    "accepts_cards": true,
    "delivery_time": "30-45 mins"
}}

CRITICAL REQUIREMENTS:
- Prefer restaurants with ratings of 3.5 or higher (but include lower if needed to reach {max_results} results)
- Each restaurant must be located in or very near {city}, India (use accurate coordinates)
- Include ALL fields for EVERY restaurant - this is a SINGLE comprehensive request
- Provide detailed descriptions (minimum 2 sentences covering ambiance and specialties)
- List actual signature dishes and specialties
- If price_range is specified, prefer matching restaurants but include others if needed
- Include accurate phone numbers and opening hours when available
- Return only valid JSON (no trailing commas or additional text)
- IMPORTANT: Return at least {max_results} restaurants if they exist in {city}

This is the ONLY request for these restaurants - provide COMPLETE information now to avoid follow-up queries.
"""
        return prompt

    def _parse_response(self, text: str) -> List[Dict]:
        """Parse Gemini response text into restaurant list."""
        try:
            restaurants = self._parse_json_response(text)
            if isinstance(restaurants, list):
                return restaurants
            return []
        except Exception as e:
            print(f"Error parsing response: {e}")
            return []

    def _parse_json_response(self, text: str):
        """Extract and parse JSON from Gemini response."""
        try:
            text = text.strip()
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            return json.loads(text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\[.*\]|\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except Exception:
                    pass
            return None


gemini_search = GeminiRestaurantSearch()


def search_restaurants_gemini(
    city: str,
    cuisines: Optional[List[str]] = None,
    price_range: Optional[str] = None,
    visit_type: Optional[str] = None,
    max_results: int = 10
) -> List[Dict]:
    """Convenience wrapper for Gemini restaurant search."""
    return gemini_search.search_restaurants(
        city=city,
        cuisines=cuisines,
        price_range=price_range,
        visit_type=visit_type,
        max_results=max_results
    )


def get_restaurant_details_gemini(restaurant_name: str, city: str) -> Optional[Dict]:
    """Convenience wrapper for Gemini restaurant detail lookup."""
    return gemini_search.get_restaurant_details(restaurant_name, city)


def is_gemini_available() -> bool:
    """Check if Gemini API is configured and available."""
    return gemini_search.is_available()
