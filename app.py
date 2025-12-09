import math
import os
import uuid
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import requests
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from sklearn.compose import ColumnTransformer  # We need this for the helper function
from sklearn.impute import SimpleImputer  # We need this for the helper function
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline  # We need this for the helper function
from sklearn.preprocessing import StandardScaler, OneHotEncoder  # We need these for the helper function
from dotenv import load_dotenv
from flask_login import LoginManager, login_required, current_user
from models import db, User, Review

from personalization_store import (
    add_bookmark,
    add_history_event,
    add_interaction,
    get_analytics_snapshot,
    get_profile,
    list_bookmarks,
    list_history,
    list_interactions,
    list_ratings,
    record_search_analytics,
    remove_bookmark,
    set_rating,
    update_profile,
    clear_history
)

# Load environment variables
load_dotenv()

# Import Gemini API integration
try:
    from gemini_api import (
        search_restaurants_gemini, 
        get_restaurant_details_gemini,
        is_gemini_available
    )
    GEMINI_ENABLED = True
except ImportError:
    print("Warning: Gemini API module not available")
    GEMINI_ENABLED = False

# Import Google Places API integration
try:
    from google_places_api import (
        search_restaurants_google,
        is_google_places_available
    )
    GOOGLE_PLACES_ENABLED = True
except ImportError:
    print("Warning: Google Places API module not available")
    GOOGLE_PLACES_ENABLED = False

# --- App Initialization ---
app = Flask(__name__)

# Load configuration from config module
import config as app_config
app.config.from_object(app_config)

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '🔐 Please login to access this page.'
login_manager.login_message_category = 'info'

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register authentication blueprint
from auth import auth_bp
from api import review_bp
app.register_blueprint(auth_bp)
app.register_blueprint(review_bp)

# Create database tables
with app.app_context():
    db.create_all()
    print("✅ Database initialized successfully!")

def _ensure_user_id():
    if current_user.is_authenticated:
        return str(current_user.id)
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']

@app.before_request
def assign_user():
    _ensure_user_id()


def _resolve_budget_floor(profile: dict) -> int:
    return int(profile.get('budget') or profile.get('budget_band_min') or 2)

# --- Load All Assets ONCE on Startup ---
print("Loading application assets...")
ASSETS_DIR = 'assets'

# Load dataset
DATASET_PATH = os.path.join(ASSETS_DIR, 'Dataset .csv')
original_restaurant_data = pd.read_csv(DATASET_PATH)

# Load CIT1 Rating Model and Preprocessors
RATING_MODEL_PATH = os.path.join(ASSETS_DIR, 'rating_model.joblib')
rating_model = joblib.load(RATING_MODEL_PATH)

RATING_PREPROCESSOR_PATH = os.path.join(ASSETS_DIR, 'rating_preprocessor.joblib')
rating_preprocessor = joblib.load(RATING_PREPROCESSOR_PATH)

TARGET_SCALER_PATH = os.path.join(ASSETS_DIR, 'target_scaler.joblib')
target_scaler = joblib.load(TARGET_SCALER_PATH)

# Load CIT2 Recommender Assets
PREPROCESSOR_PATH = os.path.join(ASSETS_DIR, 'recommender_preprocessor.joblib')
MLB_CLASSES_PATH = os.path.join(ASSETS_DIR, 'mlb_classes.joblib')
VECTORS_PATH = os.path.join(ASSETS_DIR, 'processed_restaurant_vectors.csv')

recommender_preprocessor = joblib.load(PREPROCESSOR_PATH)
mlb_classes = joblib.load(MLB_CLASSES_PATH)
processed_restaurants_df = pd.read_csv(VECTORS_PATH, index_col=0)
all_features_for_recommender_pipeline = processed_restaurants_df.columns.tolist()

# Cache numpy matrix for similarity computations to speed up recommendations
try:
    processed_restaurants_matrix = processed_restaurants_df.values
except Exception:
    processed_restaurants_matrix = np.asarray(processed_restaurants_df)

# Price range mapping
price_range_map = {1: 'Cheap', 2: 'Moderate', 3: 'Expensive', 4: 'Very Expensive'}

print("Assets loaded successfully.")

# --- Helper Functions (Copied from CIT2) ---
# We must copy these functions from your notebook so the app can use them.

def create_user_preference_vector(user_preferences, preprocessor, mlb_cuisines_classes, all_features_list):
    """
    Transforms user preferences into a numerical vector.
    """
    # Create a template DataFrame with the exact columns expected by the preprocessor's input
    # The columns must be in the same order as when the preprocessor was fitted.
    
    # Get the feature names from the fitted preprocessor
    # This assumes the preprocessor was fitted on a DataFrame with these columns
    
    # Extract numerical feature names
    num_features = preprocessor.named_transformers_['num'].feature_names_in_
    # Extract categorical feature names
    cat_features = preprocessor.named_transformers_['cat'].feature_names_in_
    # Extract binary (passthrough) feature names
    bin_features = preprocessor.named_transformers_['bin'].feature_names_in_
    # Extract cuisine (passthrough) feature names
    cuis_features = preprocessor.named_transformers_['cuis'].feature_names_in_
    
    # Combine all feature names in the correct order
    all_input_features_ordered = list(num_features) + list(cat_features) + list(bin_features) + list(cuis_features)
    
    # Create a template dictionary
    user_data_dict = {col: 0 for col in all_input_features_ordered}
    
    # Populate with user's specific choices
    user_cuisines = [c.strip() for c in user_preferences['Cuisines'].split(',') if c.strip()]
    for cuisine in user_cuisines:
        if cuisine in mlb_cuisines_classes:
            user_data_dict[cuisine] = 1

    if user_preferences['Price range'] is not None:
        user_data_dict['Price range'] = float(user_preferences['Price range'])
    
    user_data_dict['Has Online delivery'] = 1 if user_preferences.get('Has Online delivery') == 'Yes' else 0
    user_data_dict['Has Table booking'] = 1 if user_preferences.get('Has Table booking') == 'Yes' else 0
    
    # Set the city
    user_data_dict['City'] = user_preferences['City']
    
    # Set defaults for other fields if not provided
    # The preprocessor's imputer will handle NaNs if we use them
    user_data_dict.setdefault('Average Cost for two', np.nan) 
    user_data_dict.setdefault('Votes', np.nan)
    user_data_dict.setdefault('Currency', np.nan) # Imputer will use most_frequent
    user_data_dict.setdefault('Is delivering now', 0)
    user_data_dict.setdefault('Switch to order menu', 0)

    # Convert the dictionary to a DataFrame, ensuring column order
    user_df_raw = pd.DataFrame([user_data_dict])
    user_df_input = user_df_raw[all_input_features_ordered] # Enforce the correct order
    
    # Apply the same preprocessor
    # --- Coerce dtypes to avoid mixed-type issues during transformation ---
    # Numeric features -> numeric
    try:
        user_df_input[num_features] = user_df_input[num_features].apply(pd.to_numeric, errors='coerce')
    except Exception:
        # If num_features is empty or not present, skip
        pass
    # Categorical features used by OneHotEncoder -> string
    try:
        user_df_input[cat_features] = user_df_input[cat_features].astype(str).fillna('')
    except Exception:
        pass
    # Binary / passthrough features and cuisine binary columns -> numeric (0/1)
    try:
        for col in list(bin_features) + list(cuis_features):
            if col in user_df_input.columns:
                user_df_input[col] = pd.to_numeric(user_df_input[col], errors='coerce').fillna(0).astype(int)
    except Exception:
        pass

    user_vector = preprocessor.transform(user_df_input)
    return user_vector


def _to_binary_yes_no_series(series):
    """Convert a pandas Series of varied Yes/No/1/0/True/False values into 0/1 ints."""
    def conv(v):
        if pd.isna(v):
            return 0
        if isinstance(v, (int, float)):
            try:
                return 1 if float(v) == 1 else 0
            except Exception:
                return 0
        s = str(v).strip().lower()
        if s in ('yes', 'y', 'true', 't', '1'):
            return 1
        return 0
    return series.apply(conv)

def recommend_restaurants(user_preferences, processed_restaurants_df, original_restaurant_data, recommendation_preprocessor, mlb_cuisines_classes, all_features_for_recommender_pipeline):
    """
    Recommends restaurants based on user preferences using cosine similarity and filters.
    """
    user_vector = create_user_preference_vector(user_preferences, recommendation_preprocessor, mlb_cuisines_classes, all_features_for_recommender_pipeline)
    
    # Ensure processed_restaurants_df is an array for fast similarity computation
    # Prefer the cached matrix if available (faster)
    if 'processed_restaurants_matrix' in globals():
        processed_matrix = processed_restaurants_matrix
    else:
        try:
            processed_matrix = processed_restaurants_df.values if hasattr(processed_restaurants_df, 'values') else np.asarray(processed_restaurants_df)
        except Exception:
            processed_matrix = np.asarray(processed_restaurants_df)

    similarities = cosine_similarity(user_vector, processed_matrix)
    similarity_scores = similarities.flatten()

    # Create a Series of similarity scores indexed by the processed_restaurants_df index (safe alignment)
    try:
        sim_index = processed_restaurants_df.index
    except Exception:
        sim_index = np.arange(len(similarity_scores))

    sim_series = pd.Series(similarity_scores, index=sim_index, name='Similarity Score')

    # Work on a copy of the original data; join similarity scores by index so lengths don't have to match
    recommendations_df = original_restaurant_data.copy()
    # Join will align by index; restaurants not present in processed vectors will get NaN similarities
    recommendations_df = recommendations_df.join(sim_series, how='left')
    # Fill NaN similarities with 0
    recommendations_df['Similarity Score'] = pd.to_numeric(recommendations_df['Similarity Score'], errors='coerce').fillna(0)

    # Ensure 'Aggregate rating' is numeric so comparisons/sorting won't fail if mixed types exist
    if 'Aggregate rating' in recommendations_df.columns:
        recommendations_df['Aggregate rating'] = pd.to_numeric(recommendations_df['Aggregate rating'], errors='coerce')
    # Ensure similarity score is numeric
    recommendations_df['Similarity Score'] = pd.to_numeric(recommendations_df['Similarity Score'], errors='coerce').fillna(0)

    # Apply Filters
    # 1. City Filter (coerce to string for safety)
    city = str(user_preferences.get('City', '')).strip().lower()
    city_filter = recommendations_df['City'].astype(str).str.strip().str.lower() == city
    filtered_recommendations = recommendations_df[city_filter].copy()
    if filtered_recommendations.empty:
        return pd.DataFrame()

    # 2. Price Range Filter
    if user_preferences.get('Price range') is not None:
        price_range = int(user_preferences.get('Price range'))
        if 'Price range' in filtered_recommendations.columns:
            # Ensure Price range is numeric
            filtered_recommendations['Price range'] = pd.to_numeric(filtered_recommendations['Price range'], errors='coerce')
            filtered_recommendations = filtered_recommendations[filtered_recommendations['Price range'] == price_range].copy()
    if filtered_recommendations.empty:
        return pd.DataFrame()

    # 3. 4-star+ Rating Filter
    filtered_recommendations = filtered_recommendations[filtered_recommendations['Aggregate rating'] >= 4.0].copy()
    if filtered_recommendations.empty:
        return pd.DataFrame()

    # 4. Delivery/Visit Specific Filters
    if user_preferences.get('Visit_or_Delivery') == 'delivery':
        if 'Has Online delivery' in filtered_recommendations.columns:
            filtered_recommendations['Has Online delivery'] = _to_binary_yes_no_series(filtered_recommendations['Has Online delivery'])
            filtered_recommendations = filtered_recommendations[filtered_recommendations['Has Online delivery'] == 1].copy()
    elif user_preferences.get('Visit_or_Delivery') == 'visit':
        if user_preferences.get('Has Table booking') == 'Yes' and 'Has Table booking' in filtered_recommendations.columns:
            filtered_recommendations['Has Table booking'] = _to_binary_yes_no_series(filtered_recommendations['Has Table booking'])
            filtered_recommendations = filtered_recommendations[filtered_recommendations['Has Table booking'] == 1].copy()

    if filtered_recommendations.empty:
        return pd.DataFrame()

    # Sort and get top 10
    final_recommendations = filtered_recommendations.sort_values(
        by=['Similarity Score', 'Aggregate rating'],
        ascending=[False, False]
    ).drop_duplicates(subset=['Restaurant Name']).head(10)
    
    return final_recommendations

# --- Indian Capital Cities List ---
INDIAN_CAPITAL_CITIES = [
    'Agra', 'Ahmedabad', 'Allahabad', 'Amritsar', 'Aurangabad',
    'Bangalore', 'Bhopal', 'Bhubaneshwar', 'Chandigarh', 'Chennai',
    'Coimbatore', 'Dehradun', 'Faridabad', 'Ghaziabad', 'Goa',
    'Gurgaon', 'Guwahati', 'Hyderabad', 'Indore', 'Jaipur',
    'Kanpur', 'Kochi', 'Kolkata', 'Lucknow', 'Ludhiana',
    'Mangalore', 'Mohali', 'Mumbai', 'Mysore', 'Nagpur',
    'Nashik', 'New Delhi', 'Noida', 'Panchkula', 'Patna',
    'Puducherry', 'Pune', 'Ranchi', 'Secunderabad', 'Surat',
    'Vadodara', 'Varanasi', 'Vizag',
    # Additional major Indian cities
    'Aizawl', 'Amaravati', 'Bengaluru', 'Bilaspur', 'Dispur',
    'Gandhinagar', 'Gangtok', 'Imphal', 'Itanagar', 'Jammu',
    'Kavaratti', 'Kohima', 'Panaji', 'Port Blair', 'Raipur',
    'Shillong', 'Shimla', 'Srinagar', 'Thiruvananthapuram', 'Agartala'
]

# Common Indian cuisines mapping for cities not in dataset
COMMON_INDIAN_CUISINES = [
    'North Indian', 'South Indian', 'Chinese', 'Continental', 'Italian',
    'Mughlai', 'Rajasthani', 'Gujarati', 'Bengali', 'Punjabi',
    'Maharashtrian', 'Kerala', 'Andhra', 'Tamil', 'Karnataka',
    'Hyderabadi', 'Kashmiri', 'Goan', 'Assamese', 'Bihari',
    'Fast Food', 'Biryani', 'Street Food', 'Desserts', 'Beverages',
    'Seafood', 'Vegetarian', 'Non-Vegetarian', 'Vegan', 'Jain'
]

# City name normalization mapping (handles variations like Bangalore/Bengaluru)
CITY_NORMALIZATION = {
    'bengaluru': 'Bangalore',
    'bangalore': 'Bangalore',
    'mumbai': 'Mumbai',
    'bombay': 'Mumbai',
    'calcutta': 'Kolkata',
    'kolkata': 'Kolkata',
    'madras': 'Chennai',
    'chennai': 'Chennai',
    'new delhi': 'New Delhi',
    'delhi': 'New Delhi',
    'ncr': 'New Delhi'
}

def normalize_city_name(city: str) -> str:
    """Normalize city name to handle variations."""
    if not city:
        return city
    city_lower = city.strip().lower()
    return CITY_NORMALIZATION.get(city_lower, city.strip())

MOOD_TO_FILTERS = {
    'family_dinner': {'min_rating': 4.0, 'ambiance': ['family-friendly', 'casual']},
    'date_night': {'min_rating': 4.2, 'ambiance': ['romantic', 'fine-dining']},
    'business_lunch': {'min_rating': 4.0, 'ambiance': ['business', 'fine-dining']},
    'celebration': {'min_rating': 4.3, 'ambiance': ['fine-dining']},
    'solo_work': {'ambiance': ['casual'], 'features': ['wifi']}
}

OCCASION_TO_FILTERS = {
    'birthday': {'ambiance': ['celebratory', 'fine-dining']},
    'anniversary': {'ambiance': ['romantic']},
    'team_outing': {'features': ['group seating']},
    'family_trip': {'ambiance': ['family-friendly']}
}


def _current_time_context():
    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 11:
        segment = 'breakfast'
    elif 11 <= hour < 16:
        segment = 'lunch'
    elif 16 <= hour < 20:
        segment = 'evening'
    else:
        segment = 'late-night'
    return {'segment': segment, 'weekday': now.strftime('%A'), 'hour': hour}


def _get_weather_context(city: str) -> dict:
    if not city:
        return {"summary": "Unknown", "temp_c": None, "is_rainy": False, "is_hot": False}
    try:
        resp = requests.get(f"https://wttr.in/{city}?format=j1", timeout=4)
        data = resp.json()
        current = data.get('current_condition', [{}])[0]
        summary = current.get('weatherDesc', [{'value': 'Clear'}])[0].get('value', 'Clear')
        temp_c = float(current.get('temp_C', 30))
        is_rainy = 'rain' in summary.lower() or float(current.get('precipMM', 0)) > 0
        is_hot = temp_c >= 32
        return {"summary": summary, "temp_c": temp_c, "is_rainy": is_rainy, "is_hot": is_hot}
    except Exception:
        return {"summary": "Unknown", "temp_c": None, "is_rainy": False, "is_hot": False}


def build_contextual_preferences(city: str, mood: str = None, occasion: str = None) -> dict:
    time_context = _current_time_context()
    weather_context = _get_weather_context(city)
    mood_filters = MOOD_TO_FILTERS.get(mood, {})
    occasion_filters = OCCASION_TO_FILTERS.get(occasion, {})
    return {
        "time": time_context,
        "weather": weather_context,
        "mood": mood,
        "occasion": occasion,
        "mood_filters": mood_filters,
        "occasion_filters": occasion_filters
    }


def _normalize_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def apply_personalization_bias(df, profile: dict, bookmarks: list, ratings: dict, context: dict):
    if df.empty:
        return df

    favorite_cuisines = set(map(str.lower, profile.get('favorite_cuisines', [])))
    bookmarked_ids = {str(b.get('restaurant_id')) for b in bookmarks if b.get('restaurant_id')}
    rated_ids = {str(rid): details.get('rating', 0) for rid, details in ratings.items()}

    def cuisine_boost(cuisine_string):
        cuisines = [c.strip().lower() for c in str(cuisine_string).split(',')]
        overlap = favorite_cuisines.intersection(cuisines)
        return 0.07 * len(overlap)

    def bookmark_boost(rest_id):
        if rest_id and str(rest_id) in bookmarked_ids:
            return 0.05
        if rest_id and str(rest_id) in rated_ids:
            rating = float(rated_ids[str(rest_id)])
            return (rating - 3) * 0.02
        return 0

    def context_boost(row):
        bonus = 0
        time_segment = context.get('time', {}).get('segment')
        cuisines = str(row.get('Cuisines', '')).lower()
        if time_segment == 'breakfast' and ('cafe' in cuisines or 'bakery' in cuisines):
            bonus += 0.03
        if time_segment == 'late-night' and ('bar' in cuisines or 'fast food' in cuisines):
            bonus += 0.02
        weather = context.get('weather', {})
        if weather.get('is_rainy') and ('rooftop' in cuisines or 'outdoor' in cuisines):
            bonus -= 0.02
        if weather.get('is_hot') and 'ice cream' in cuisines:
            bonus += 0.02
        return bonus

    personalization_scores = []
    for _, row in df.iterrows():
        rest_id = row.get('Restaurant ID') or row.get('Restaurant Name')
        bonus = cuisine_boost(row.get('Cuisines', ''))
        bonus += bookmark_boost(rest_id)
        bonus += context_boost(row)
        personalization_scores.append(bonus)

    df['Personalization Score'] = personalization_scores
    df['Similarity Score'] = df['Similarity Score'] + df['Personalization Score']
    return df.sort_values(by=['Similarity Score', 'Aggregate rating'], ascending=[False, False])


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def build_itinerary(stops: list):
    if len(stops) <= 1:
        return stops
    route = [stops[0]]
    remaining = stops[1:]
    while remaining:
        current = route[-1]
        next_stop = min(
            remaining,
            key=lambda stop: _haversine(
                current['latitude'], current['longitude'],
                stop['latitude'], stop['longitude']
            )
        )
        route.append(next_stop)
        remaining.remove(next_stop)
    return route

# --- Helper Routes for Autocomplete ---
@app.route('/api/cities')
def get_cities():
    """Get unique cities for autocomplete, including all Indian capital cities."""
    # Get cities from dataset
    dataset_cities = set(original_restaurant_data['City'].unique().tolist())
    
    # Add all Indian capital cities
    all_cities = dataset_cities.union(set(INDIAN_CAPITAL_CITIES))
    
    # Sort and return
    return jsonify(sorted(list(all_cities)))

@app.route('/api/cuisines')
def get_cuisines():
    """Get unique cuisines for autocomplete, with support for cities not in dataset."""
    city = request.args.get('city')
    
    if city:
        # Normalize city name for comparison
        city_normalized = normalize_city_name(city)
        
        # Check if city exists in dataset
        city_restaurants = original_restaurant_data[
            original_restaurant_data['City'].str.strip().str.lower() == city_normalized.lower()
        ]
        
        if not city_restaurants.empty:
            # City is in dataset - get cuisines from dataset
            all_cuisines = set()
            for cuisines in city_restaurants['Cuisines'].dropna():
                all_cuisines.update(c.strip() for c in cuisines.split(','))
        else:
            # City not in dataset - try to get cuisines using Gemini or use common Indian cuisines
            all_cuisines = set(COMMON_INDIAN_CUISINES)
            
            # Try to enhance with Gemini if available
            if GEMINI_ENABLED and is_gemini_available():
                try:
                    # Use Gemini to get city-specific cuisines
                    prompt = f"""List the most popular and common restaurant cuisines available in {city_normalized}, India. 
Return only a comma-separated list of cuisine names, nothing else. 
Examples: North Indian, South Indian, Chinese, Italian, etc."""
                    
                    from gemini_api import gemini_search
                    if gemini_search.is_available():
                        response = gemini_search.model.generate_content(prompt)
                        gemini_cuisines = response.text.strip()
                        
                        # Parse the response
                        if gemini_cuisines:
                            # Remove markdown if present
                            gemini_cuisines = gemini_cuisines.replace('```', '').strip()
                            # Split by comma and clean
                            gemini_list = [c.strip() for c in gemini_cuisines.split(',') if c.strip()]
                            if gemini_list:
                                all_cuisines.update(gemini_list)
                except Exception as e:
                    print(f"Error getting cuisines from Gemini for {city}: {e}")
                    # Fallback to common cuisines already set
    else:
        # If no city selected, return all cuisines from dataset plus common Indian cuisines
        all_cuisines = set(COMMON_INDIAN_CUISINES)
        for cuisines in original_restaurant_data['Cuisines'].dropna():
            all_cuisines.update(c.strip() for c in cuisines.split(','))
    
    return jsonify(sorted(list(all_cuisines)))


def _normalize_restaurant_payload(raw: dict) -> dict:
    if not raw:
        return {}
    restaurant_id = raw.get('Restaurant ID') or raw.get('restaurant_id') or raw.get('id') or raw.get('name')
    return {
        "bookmark_id": raw.get('bookmark_id'),
        "restaurant_id": str(restaurant_id) if restaurant_id is not None else None,
        "name": raw.get('Restaurant Name') or raw.get('name'),
        "city": raw.get('City') or raw.get('city'),
        "cuisines": raw.get('Cuisines') or raw.get('cuisines'),
        "rating": raw.get('Aggregate rating') or raw.get('rating'),
        "price_range": raw.get('Price range') or raw.get('price_range'),
        "average_cost_for_two": raw.get('Average Cost for two') or raw.get('cost_for_two'),
        "latitude": raw.get('Latitude') or raw.get('latitude'),
        "longitude": raw.get('Longitude') or raw.get('longitude'),
        "snapshot": raw
    }


@app.route('/api/v1/preferences', methods=['GET', 'PUT', 'POST'])
def api_v1_preferences():
    user_id = _ensure_user_id()
    if request.method == 'GET':
        return jsonify(get_profile(user_id))

    data = request.json or {}
    try:
        budget_band_min = int(data.get('budget_band_min')) if data.get('budget_band_min') is not None else None
        budget_band_max = int(data.get('budget_band_max')) if data.get('budget_band_max') is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "budget_band_min and budget_band_max must be integers"}), 400

    flexible = data.get('flexible_prefs')
    if flexible is not None and not isinstance(flexible, dict):
        return jsonify({"error": "flexible_prefs must be an object"}), 400

    profile = update_profile(user_id, {
        "favorite_cuisines": data.get('favorite_cuisines'),
        "dietary_needs": data.get('dietary_needs'),
        "budget_band_min": budget_band_min,
        "budget_band_max": budget_band_max,
        "flexible_prefs": flexible,
        "preferred_visit_type": data.get('preferred_visit_type'),
        "preferred_table_booking": data.get('preferred_table_booking'),
        "mood_tags": data.get('mood_tags'),
        "occasion_tags": data.get('occasion_tags')
    })
    return jsonify(profile)


@app.route('/api/v1/interactions', methods=['GET', 'POST'])
def api_v1_interactions():
    user_id = _ensure_user_id()
    if request.method == 'POST':
        data = request.json or {}
        entity_id = data.get('entity_id')
        interaction_type = data.get('interaction_type')
        if not entity_id or not interaction_type:
            return jsonify({"error": "entity_id and interaction_type are required"}), 400

        interaction = add_interaction(user_id, {
            "entity_id": entity_id,
            "entity_type": data.get('entity_type', 'restaurant'),
            "interaction_type": interaction_type,
            "value": data.get('value'),
            "metadata": data.get('metadata')
        })

        metadata = data.get('metadata') or {}
        if interaction_type == 'bookmark' and metadata:
            add_bookmark(user_id, _normalize_restaurant_payload(metadata))
        if interaction_type == 'rating' and data.get('value'):
            target_id = metadata.get('restaurant_id') or metadata.get('Restaurant ID') or entity_id
            try:
                rating_value = float(data.get('value'))
                if target_id:
                    set_rating(user_id, str(target_id), rating_value)
            except (TypeError, ValueError):
                pass

        return jsonify(interaction)

    type_filter = request.args.get('type')
    interactions = list_interactions(user_id, type_filter)
    return jsonify(interactions)


@app.route('/api/profile', methods=['GET', 'POST'])
def api_profile():
    user_id = _ensure_user_id()
    if request.method == 'GET':
        return jsonify(get_profile(user_id))

    data = request.json or {}
    budget_value = int(data.get('budget')) if data.get('budget') else None
    updates = {
        "favorite_cuisines": _normalize_list(data.get('favorite_cuisines')),
        "dietary_needs": _normalize_list(data.get('dietary_needs')),
        "budget_band_min": budget_value,
        "budget_band_max": budget_value,
        "preferred_visit_type": data.get('preferred_visit_type'),
        "preferred_table_booking": data.get('preferred_table_booking'),
        "mood_tags": _normalize_list(data.get('mood_tags')),
        "occasion_tags": _normalize_list(data.get('occasion_tags')),
        "saved_filters": data.get('saved_filters')
    }
    profile = update_profile(user_id, updates)
    return jsonify(profile)


@app.route('/api/bookmarks', methods=['GET', 'POST', 'DELETE'])
def api_bookmarks():
    user_id = _ensure_user_id()
    if request.method == 'GET':
        return jsonify(list_bookmarks(user_id))

    if request.method == 'POST':
        payload = request.json or {}
        bookmark = add_bookmark(user_id, _normalize_restaurant_payload(payload))
        return jsonify(bookmark)

    # DELETE
    data = request.json or {}
    bookmark_id = data.get('bookmark_id')
    if not bookmark_id:
        return jsonify({"error": "bookmark_id required"}), 400
    updated = remove_bookmark(user_id, bookmark_id)
    return jsonify(updated)


@app.route('/api/ratings', methods=['GET', 'POST'])
def api_ratings():
    user_id = _ensure_user_id()
    if request.method == 'GET':
        return jsonify(list_ratings(user_id))

    data = request.json or {}
    restaurant_id = str(data.get('restaurant_id'))
    rating = float(data.get('rating', 0))
    if not restaurant_id:
        return jsonify({"error": "restaurant_id required"}), 400
    updated = set_rating(user_id, restaurant_id, rating)
    return jsonify(updated)


@app.route('/api/history', methods=['GET', 'DELETE'])
def api_history():
    user_id = _ensure_user_id()
    
    if request.method == 'DELETE':
        # Clear history
        clear_history(user_id)
        return jsonify({"message": "History cleared successfully"})
    
    # GET method - list history
    limit = int(request.args.get('limit', 25))
    return jsonify(list_history(user_id, limit=limit))


@app.route('/api/history/clear', methods=['POST'])
@login_required
def api_clear_history():
    user_id = _ensure_user_id()
    clear_history(user_id)
    return jsonify({"message": "History cleared successfully"})


@app.route('/api/admin/analytics', methods=['GET'])
def api_admin_analytics():
    snapshot = get_analytics_snapshot()
    return jsonify(snapshot)


@app.route('/api/itinerary', methods=['POST'])
def api_itinerary():
    user_id = _ensure_user_id()
    data = request.json or {}
    stops = data.get('stops', [])
    if not stops:
        return jsonify({"error": "At least one stop is required"}), 400

    enriched_stops = []
    for stop in stops:
        rest_id = stop.get('restaurant_id') or stop.get('Restaurant ID')
        lat = stop.get('latitude') or stop.get('Latitude')
        lon = stop.get('longitude') or stop.get('Longitude')
        if rest_id and (lat is None or lon is None):
            try:
                rest_int = int(rest_id)
                dataset_row = original_restaurant_data[original_restaurant_data['Restaurant ID'] == rest_int]
                if not dataset_row.empty:
                    lat = float(dataset_row.iloc[0]['Latitude'])
                    lon = float(dataset_row.iloc[0]['Longitude'])
            except (ValueError, TypeError):
                pass
        if lat is None or lon is None:
            continue
        enriched_stops.append({
            "restaurant_id": rest_id,
            "name": stop.get('name') or stop.get('Restaurant Name'),
            "latitude": float(lat),
            "longitude": float(lon),
            "city": stop.get('city') or stop.get('City'),
            "cuisines": stop.get('cuisines') or stop.get('Cuisines'),
            "rating": stop.get('rating') or stop.get('Aggregate rating'),
            "average_cost_for_two": stop.get('Average Cost for two') or stop.get('cost_for_two')
        })

    if not enriched_stops:
        return jsonify({"error": "No stops with valid coordinates"}), 400

    optimized_route = build_itinerary(enriched_stops)
    legs = []
    total_distance = 0

    for index in range(len(optimized_route) - 1):
        current = optimized_route[index]
        nxt = optimized_route[index + 1]
        distance = _haversine(current['latitude'], current['longitude'], nxt['latitude'], nxt['longitude'])
        total_distance += distance
        travel_time_hours = distance / 25  # assume 25 km/h city average
        legs.append({
            "from": current,
            "to": nxt,
            "distance_km": round(distance, 2),
            "travel_time_minutes": round(travel_time_hours * 60)
        })

    total_travel_time = sum(leg['travel_time_minutes'] for leg in legs)
    add_history_event(user_id, {
        "type": "itinerary",
        "stops": len(optimized_route),
        "total_distance_km": round(total_distance, 2)
    })

    share_path = '/'.join(f"{stop['latitude']},{stop['longitude']}" for stop in optimized_route)

    return jsonify({
        "route": optimized_route,
        "legs": legs,
        "total_distance_km": round(total_distance, 2),
        "total_travel_time_minutes": total_travel_time,
        "share_link": f"https://www.google.com/maps/dir/{share_path}"
    })


# --- Review API Routes ---
@app.route('/api/reviews/<restaurant_id>', methods=['GET'])
def api_get_reviews(restaurant_id):
    """Get all reviews for a specific restaurant"""
    try:
        reviews = Review.query.filter_by(restaurant_id=str(restaurant_id)).order_by(Review.created_at.desc()).all()
        return jsonify([review.to_dict() for review in reviews])
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reviews', methods=['POST'])
@login_required
def api_create_review():
    """Create a new review (requires login)"""
    try:
        data = request.json or {}
        
        # Validate required fields
        restaurant_id = str(data.get('restaurant_id'))
        restaurant_name = data.get('restaurant_name')
        rating = data.get('rating')
        
        if not restaurant_id or not restaurant_name:
            return jsonify({"error": "restaurant_id and restaurant_name are required"}), 400
        
        if not rating or not (1 <= float(rating) <= 5):
            return jsonify({"error": "rating must be between 1 and 5"}), 400
        
        # Check if user already reviewed this restaurant
        existing_review = Review.query.filter_by(
            user_id=current_user.id,
            restaurant_id=restaurant_id
        ).first()
        
        if existing_review:
            return jsonify({"error": "You have already reviewed this restaurant. Use PUT to update."}), 409
        
        # Create new review
        review = Review(
            user_id=current_user.id,
            restaurant_id=restaurant_id,
            restaurant_name=restaurant_name,
            restaurant_city=data.get('restaurant_city'),
            rating=float(rating),
            review_text=data.get('review_text', '')
        )
        
        db.session.add(review)
        db.session.commit()
        
        return jsonify(review.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating review: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reviews/<int:review_id>', methods=['PUT'])
@login_required
def api_update_review(review_id):
    """Update an existing review (requires login, own reviews only)"""
    try:
        review = Review.query.get(review_id)
        
        if not review:
            return jsonify({"error": "Review not found"}), 404
        
        # Check if the review belongs to the current user
        if review.user_id != current_user.id:
            return jsonify({"error": "You can only edit your own reviews"}), 403
        
        data = request.json or {}
        
        # Update fields
        if 'rating' in data:
            rating = float(data['rating'])
            if not (1 <= rating <= 5):
                return jsonify({"error": "rating must be between 1 and 5"}), 400
            review.rating = rating
        
        if 'review_text' in data:
            review.review_text = data['review_text']
        
        review.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(review.to_dict())
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating review: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@login_required
def api_delete_review(review_id):
    """Delete a review (requires login, own reviews only)"""
    try:
        review = Review.query.get(review_id)
        
        if not review:
            return jsonify({"error": "Review not found"}), 404
        
        # Check if the review belongs to the current user
        if review.user_id != current_user.id:
            return jsonify({"error": "You can only delete your own reviews"}), 403
        
        db.session.delete(review)
        db.session.commit()
        
        return jsonify({"message": "Review deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting review: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reviews/user/<restaurant_id>', methods=['GET'])
@login_required
def api_get_user_review(restaurant_id):
    """Get current user's review for a specific restaurant"""
    try:
        review = Review.query.filter_by(
            user_id=current_user.id,
            restaurant_id=str(restaurant_id)
        ).first()
        
        if review:
            return jsonify(review.to_dict())
        else:
            return jsonify(None), 200
            
    except Exception as e:
        print(f"Error fetching user review: {e}")
        return jsonify({"error": str(e)}), 500


# --- App Routes ---

@app.route('/')
def home():
    """Serves the main index.html page."""
    # Clear any old recommendations when returning to home
    if 'recommendations' in session:
        del session['recommendations']
    return render_template('index.html')




@app.route('/profile')
def profile_page():
    return render_template('profile.html')

@app.route('/api/recommend', methods=['POST'])
@login_required
def api_recommend():
    """API endpoint to get recommendations."""
    try:
        data = request.json
        print(f"Received data: {data}")
        user_id = _ensure_user_id()
        profile = get_profile(user_id)
        saved_bookmarks = list_bookmarks(user_id)
        saved_ratings = list_ratings(user_id)

        # Normalize city name
        city = normalize_city_name(data.get('city', ''))

        cuisines = data.get('cuisines') or ','.join(profile.get('favorite_cuisines', []))
        if isinstance(cuisines, list):
            cuisines = ','.join(cuisines)
        price_range = data.get('priceRange') or _resolve_budget_floor(profile)

        visit_type = data.get('visitType') or profile.get('preferred_visit_type', 'visit')
        table_booking = data.get('tableBooking') or profile.get('preferred_table_booking', 'No')
        mood = data.get('mood')
        occasion = data.get('occasion')

        # Build the preference dictionary from the frontend request
        user_preferences = {
            'Cuisines': cuisines,
            'Price range': int(price_range),
            'Visit_or_Delivery': visit_type,
            'Has Table booking': table_booking,
            'Has Online delivery': 'Yes' if visit_type == 'delivery' else 'No',
            'City': city
        }

        context = build_contextual_preferences(city, mood=mood, occasion=occasion)

        # Run the recommender function
        recommended_restaurants = recommend_restaurants(
            user_preferences,
            processed_restaurants_df,
            original_restaurant_data,
            recommender_preprocessor,
            mlb_classes,
            all_features_for_recommender_pipeline
        )

        if not recommended_restaurants.empty:
            recommended_restaurants = apply_personalization_bias(
                recommended_restaurants,
                profile,
                saved_bookmarks,
                saved_ratings,
                context
            )
        
        # Normalize delivery/booking columns to 0/1 for JSON
        if 'Has Online delivery' in recommended_restaurants.columns:
            recommended_restaurants['Has Online delivery'] = _to_binary_yes_no_series(recommended_restaurants['Has Online delivery'])
        if 'Has Table booking' in recommended_restaurants.columns:
            recommended_restaurants['Has Table booking'] = _to_binary_yes_no_series(recommended_restaurants['Has Table booking'])

        # Convert the results to a JSON-friendly format
        results = recommended_restaurants.to_dict('records')
        
        # Store in session for map view
        session['recommendations'] = results
        session['search_type'] = 'dataset'

        filters_used = {
            "mood": mood,
            "occasion": occasion,
            "dietary": data.get('dietary'),
            "ambiance": data.get('ambiance'),
            "features": data.get('features')
        }
        record_search_analytics(user_id, city, filters_used, source='dataset')
        add_history_event(user_id, {
            "type": "search",
            "city": city,
            "cuisines": cuisines,
            "results": len(results),
            "context": context
        })
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict_rating', methods=['POST'])
def api_predict_rating():
    """API endpoint to predict a restaurant's rating."""
    try:
        data = request.json
        print(f"Rating prediction data received: {data}")

        # Convert the single JSON object into a DataFrame
        new_data_df = pd.DataFrame([data])

        try:
            # Transform features using the complete pipeline
            new_data_transformed = rating_preprocessor.transform(new_data_df)
            
            # Get scaled prediction
            scaled_prediction = rating_model.predict(new_data_transformed)
            
            # Unscale the prediction
            prediction = target_scaler.inverse_transform(scaled_prediction.reshape(-1, 1))
            
            # Get the prediction value and ensure it's within reasonable bounds
            predicted_rating = float(prediction[0][0])
            predicted_rating = max(0, min(5, predicted_rating))  # Clamp between 0 and 5
            
            # Round to 1 decimal place for consistency with actual ratings
            predicted_rating = round(predicted_rating, 1)
            
            # Add confidence level based on prediction range
            confidence = "high" if 2.0 <= predicted_rating <= 4.9 else "low"
            
            return jsonify({
                'predicted_rating': predicted_rating,
                'confidence': confidence
            })
            
        except Exception as e:
            print(f"Error in prediction pipeline: {str(e)}")
            return jsonify({"error": "Failed to generate prediction"}), 500

    except Exception as e:
        print(f"Error processing rating prediction: {e}")
        return jsonify({"error": str(e)}), 500

# --- Gemini API Routes ---
@app.route('/api/gemini/search', methods=['POST'])
@login_required
def api_gemini_search():
    """API endpoint for Gemini-powered restaurant search."""
    user_id = _ensure_user_id()
    if not GEMINI_ENABLED or not is_gemini_available():
        # Fallback to Google Places if Gemini not available
        if GOOGLE_PLACES_ENABLED and is_google_places_available():
            try:
                data = request.json
                city = normalize_city_name(data.get('city', ''))
                cuisines = data.get('cuisines', '').split(',') if data.get('cuisines') else None
                cuisines = [c.strip() for c in cuisines if c.strip()] if cuisines else None
                price_range = data.get('priceRange')
                
                if not city:
                    return jsonify({"error": "City is required"}), 400
                
                results = search_restaurants_google(
                    city=city,
                    cuisines=cuisines,
                    price_range=price_range,
                    max_results=10
                )
                
                if results:
                    session['recommendations'] = results
                    session['search_type'] = 'google'
                    record_search_analytics(user_id, city, {"source": "gemini-fallback"}, source='google')
                    add_history_event(user_id, {
                        "type": "search",
                        "city": city,
                        "results": len(results),
                        "mode": "google-fallback"
                    })
                
                return jsonify(results)
            except Exception as e:
                print(f"Error in Google Places search: {e}")
                return jsonify({"error": str(e)}), 500
        return jsonify({"error": "Gemini API is not available. Please configure GEMINI_API_KEY."}), 503
    
    try:
        data = request.json
        city = normalize_city_name(data.get('city', ''))
        cuisines = data.get('cuisines', '').split(',') if data.get('cuisines') else None
        cuisines = [c.strip() for c in cuisines if c.strip()] if cuisines else None
        price_range = data.get('priceRange')
        visit_type = data.get('visitType')
        mood = data.get('mood')
        occasion = data.get('occasion')
        context = build_contextual_preferences(city, mood=mood, occasion=occasion)
        
        if not city:
            return jsonify({"error": "City is required"}), 400
        
        # Search using Gemini
        results = search_restaurants_gemini(
            city=city,
            cuisines=cuisines,
            price_range=price_range,
            visit_type=visit_type,
            max_results=10
        )
        
        # If Gemini returns no results, try Google Places
        if not results and GOOGLE_PLACES_ENABLED and is_google_places_available():
            print("Gemini returned no results, trying Google Places...")
            results = search_restaurants_google(
                city=city,
                cuisines=cuisines,
                price_range=price_range,
                max_results=10
            )
            if results:
                session['search_type'] = 'google'
        
        # Store in session for map view
        if results:
            session['recommendations'] = results
            session['search_type'] = 'gemini'
            record_search_analytics(user_id, city, {
                "mood": mood,
                "occasion": occasion
            }, source='gemini')
            add_history_event(user_id, {
                "type": "search",
                "city": city,
                "results": len(results),
                "context": context,
                "mode": "gemini"
            })
        
        # Ensure each result has an ID for frontend navigation
        if results:
            for i, restaurant in enumerate(results):
                if 'Restaurant ID' not in restaurant and 'id' not in restaurant:
                    # Generate a unique ID from name
                    name = restaurant.get('name') or restaurant.get('Restaurant Name', f'restaurant_{i}')
                    restaurant['id'] = name.replace(' ', '_').replace("'", '').lower()
                    restaurant['Restaurant ID'] = restaurant['id']
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Error in Gemini search: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/gemini/details', methods=['POST'])
def api_gemini_details():
    """API endpoint to get detailed restaurant information from Gemini."""
    if not GEMINI_ENABLED or not is_gemini_available():
        return jsonify({"error": "Gemini API is not available"}), 503
    
    try:
        data = request.json
        restaurant_name = data.get('name')
        city = data.get('city')
        
        if not restaurant_name or not city:
            return jsonify({"error": "Restaurant name and city are required"}), 400
        
        details = get_restaurant_details_gemini(restaurant_name, city)
        
        if details:
            return jsonify(details)
        else:
            return jsonify({"error": "Restaurant details not found"}), 404
            
    except Exception as e:
        print(f"Error getting Gemini details: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/gemini/status', methods=['GET'])
def api_gemini_status():
    """Check if Gemini API is available."""
    return jsonify({
        "enabled": GEMINI_ENABLED,
        "available": is_gemini_available() if GEMINI_ENABLED else False
    })

@app.route('/api/recommend/hybrid', methods=['POST'])
@login_required
def api_recommend_hybrid():
    """Hybrid recommendation: Try dataset first, fallback to Gemini if no results."""
    try:
        data = request.json
        user_id = _ensure_user_id()
        profile = get_profile(user_id)
        saved_bookmarks = list_bookmarks(user_id)
        saved_ratings = list_ratings(user_id)
        
        # Normalize city name
        city = normalize_city_name(data.get('city', ''))

        cuisines = data.get('cuisines') or ','.join(profile.get('favorite_cuisines', []))
        if isinstance(cuisines, list):
            cuisines = ','.join(cuisines)
        price_range = data.get('priceRange') or _resolve_budget_floor(profile)
        visit_type = data.get('visitType') or profile.get('preferred_visit_type', 'visit')
        table_booking = data.get('tableBooking') or profile.get('preferred_table_booking', 'No')
        mood = data.get('mood')
        occasion = data.get('occasion')
        context = build_contextual_preferences(city, mood=mood, occasion=occasion)
        
        # First, try the dataset-based recommendation
        user_preferences = {
            'Cuisines': cuisines,
            'Price range': int(price_range),
            'Visit_or_Delivery': visit_type,
            'Has Table booking': table_booking,
            'Has Online delivery': 'Yes' if visit_type == 'delivery' else 'No',
            'City': city
        }
        
        recommended_restaurants = recommend_restaurants(
            user_preferences,
            processed_restaurants_df,
            original_restaurant_data,
            recommender_preprocessor,
            mlb_classes,
            all_features_for_recommender_pipeline
        )
        
        # If we have results from dataset, return them
        if not recommended_restaurants.empty:
            recommended_restaurants = apply_personalization_bias(
                recommended_restaurants,
                profile,
                saved_bookmarks,
                saved_ratings,
                context
            )
            results = recommended_restaurants.to_dict('records')
            session['recommendations'] = results
            session['search_type'] = 'hybrid-dataset'
            filters_used = {
                "mood": mood,
                "occasion": occasion,
                "dietary": data.get('dietary'),
                "ambiance": data.get('ambiance'),
                "features": data.get('features')
            }
            record_search_analytics(user_id, city, filters_used, source='hybrid', hybrid_fallback='dataset')
            add_history_event(user_id, {
                "type": "search",
                "city": city,
                "cuisines": cuisines,
                "results": len(results),
                "context": context,
                "mode": "hybrid-dataset"
            })
            return jsonify(results)
        
        # If no results, try Gemini (if available)
        if GEMINI_ENABLED and is_gemini_available():
            # Use normalized city (already defined above)
            cuisines = data.get('cuisines', '').split(',') if data.get('cuisines') else None
            cuisines = [c.strip() for c in cuisines if c.strip()] if cuisines else None
            price_range = data.get('priceRange')
            
            print(f"Trying Gemini API for city: {city}, cuisines: {cuisines}, price_range: {price_range}")
            gemini_results = search_restaurants_gemini(
                city=city,
                cuisines=cuisines,
                price_range=price_range,
                visit_type=data.get('visitType'),
                max_results=10
            )
            
            print(f"Gemini returned {len(gemini_results) if gemini_results else 0} results")
            
            # Filter Gemini results by price range if specified
            if gemini_results and price_range:
                filtered_gemini_results = []
                for result in gemini_results:
                    # Check if price_range matches (can be number or text)
                    result_price = result.get('price_range') or result.get('price_range_text', '')
                    price_match = False
                    
                    # Try numeric match
                    try:
                        if int(result_price) == int(price_range):
                            price_match = True
                    except (ValueError, TypeError):
                        pass
                    
                    # Try text match
                    if not price_match:
                        price_text_map = {
                            '1': ['cheap', 'budget', '1'],
                            '2': ['moderate', '2'],
                            '3': ['expensive', '3'],
                            '4': ['very expensive', '4']
                        }
                        price_keywords = price_text_map.get(str(price_range), [])
                        result_price_lower = str(result_price).lower()
                        if any(keyword in result_price_lower for keyword in price_keywords):
                            price_match = True
                    
                    if price_match:
                        filtered_gemini_results.append(result)
                
                gemini_results = filtered_gemini_results
            
            if gemini_results:
                session['recommendations'] = gemini_results
                session['search_type'] = 'hybrid-gemini'
                record_search_analytics(user_id, city, {
                    "mood": mood,
                    "occasion": occasion
                }, source='hybrid', hybrid_fallback='gemini')
                add_history_event(user_id, {
                    "type": "search",
                    "city": city,
                    "cuisines": cuisines,
                    "results": len(gemini_results),
                    "context": context,
                    "mode": "hybrid-gemini"
                })
                return jsonify(gemini_results)
        
        # If still no results, try Google Places API (if available)
        if GOOGLE_PLACES_ENABLED and is_google_places_available():
            # Use normalized city (already defined above)
            cuisines = data.get('cuisines', '').split(',') if data.get('cuisines') else None
            cuisines = [c.strip() for c in cuisines if c.strip()] if cuisines else None
            price_range = data.get('priceRange')
            
            print(f"Trying Google Places API for city: {city}, cuisines: {cuisines}, price_range: {price_range}")
            google_results = search_restaurants_google(
                city=city,
                cuisines=cuisines,
                price_range=price_range,
                max_results=10
            )
            
            print(f"Google Places returned {len(google_results) if google_results else 0} results")
            
            if google_results:
                session['recommendations'] = google_results
                session['search_type'] = 'hybrid-google'
                record_search_analytics(user_id, city, {
                    "mood": mood,
                    "occasion": occasion
                }, source='hybrid', hybrid_fallback='google')
                add_history_event(user_id, {
                    "type": "search",
                    "city": city,
                    "cuisines": cuisines,
                    "results": len(google_results),
                    "context": context,
                    "mode": "hybrid-google"
                })
                return jsonify(google_results)
        
        # No results from any source
        return jsonify([])
        
    except Exception as e:
        print(f"Error in hybrid recommendation: {e}")
        return jsonify({"error": str(e)}), 500

# --- Restaurant Details Route ---




# Flexible route for restaurant details (handles both int and string IDs)
@app.route('/restaurant/<path:restaurant_id>')
def restaurant_details_any(restaurant_id):
    """Handle restaurant details for any ID type."""
    # Try to convert to int
    try:
        numeric_id = int(restaurant_id)
        return restaurant_details(numeric_id)
    except (ValueError, TypeError):
        # String ID - likely from Gemini, extract name and try to get details
        import urllib.parse
        # Decode and convert underscores back to spaces
        restaurant_name = urllib.parse.unquote(str(restaurant_id)).replace('_', ' ')
        
        # Try to get details from Gemini
        if GEMINI_ENABLED and is_gemini_available():
            try:
                # Extract city from the name if it's in parentheses
                city = "India"
                if '(' in restaurant_name and ')' in restaurant_name:
                    parts = restaurant_name.split('(')
                    restaurant_name = parts[0].strip()
                    city_part = parts[1].split(')')[0].strip()
                    city = city_part if city_part else "India"
                
                gemini_details = get_restaurant_details_gemini(restaurant_name, city)
                
                if gemini_details:
                    # Create restaurant data from Gemini response
                    restaurant_data = {
                        'Restaurant Name': gemini_details.get('name', restaurant_name),
                        'Restaurant ID': restaurant_id,
                        'City': gemini_details.get('address', city),
                        'Aggregate rating': gemini_details.get('rating', 0),
                        'Cuisines': ', '.join(gemini_details.get('cuisines', [])) if isinstance(gemini_details.get('cuisines'), list) else gemini_details.get('cuisines', 'Not specified'),
                        'Average Cost for two': gemini_details.get('cost_for_two', 'N/A'),
                        'Latitude': gemini_details.get('latitude'),
                        'Longitude': gemini_details.get('longitude'),
                    }
                    
                    return render_template(
                        'restaurant_details.html',
                        restaurant=restaurant_data,
                        gemini_details=gemini_details,
                        gemini_available=True
                    )
            except Exception as e:
                print(f"Error fetching Gemini details for {restaurant_name}: {e}")
        
        # Fallback: create basic restaurant data
        restaurant_data = {
            'Restaurant Name': restaurant_name,
            'Restaurant ID': restaurant_id,
            'City': 'Unknown',
            'Aggregate rating': 0,
            'Cuisines': 'Not specified',
        }
        
        return render_template(
            'restaurant_details.html',
            restaurant=restaurant_data,
            gemini_details=None,
            gemini_available=False
        )

@app.route('/restaurant/<int:restaurant_id>')
def restaurant_details(restaurant_id):
    """Display detailed information about a restaurant."""
    try:
        # Try to find restaurant in dataset first
        restaurant = original_restaurant_data[original_restaurant_data['Restaurant ID'] == restaurant_id]
        
        restaurant_data = None
        gemini_details = None
        
        if not restaurant.empty:
            restaurant_data = restaurant.iloc[0].to_dict()
            # Try to get enhanced details from Gemini
            if GEMINI_ENABLED and is_gemini_available():
                try:
                    gemini_details = get_restaurant_details_gemini(
                        restaurant_data.get('Restaurant Name', ''),
                        restaurant_data.get('City', '')
                    )
                except Exception as e:
                    print(f"Error fetching Gemini details: {e}")
        
        # If not in dataset, try Gemini only
        if restaurant_data is None and GEMINI_ENABLED and is_gemini_available():
            # This would require name and city from query params
            name = request.args.get('name')
            city = request.args.get('city')
            if name and city:
                gemini_details = get_restaurant_details_gemini(name, city)
                if gemini_details:
                    restaurant_data = gemini_details
        
        if restaurant_data is None:
            return render_template('error.html', 
                                 error="Restaurant not found",
                                 message="The restaurant you're looking for doesn't exist in our database."), 404
        
        return render_template('restaurant_details.html', 
                             restaurant=restaurant_data,
                             gemini_details=gemini_details,
                             gemini_available=GEMINI_ENABLED and is_gemini_available())
        
    except Exception as e:
        print(f"Error loading restaurant details: {e}")
        return render_template('error.html', 
                             error="Error loading restaurant",
                             message=str(e)), 500

# --- ML Analytics API Endpoints ---

# Import ML analytics module
try:
    from ml_analytics import RatingPredictor, SentimentAnalyzer, RecommendationEngine
    from models import RestaurantRatingHistory, RestaurantPrediction, AIRecommendation, ReviewSentiment
    ML_ANALYTICS_ENABLED = True
except ImportError as e:
    print(f"⚠️ ML Analytics not fully available: {e}")
    ML_ANALYTICS_ENABLED = False


@app.route('/api/analytics/rating-prediction/<restaurant_id>', methods=['GET'])
def get_rating_prediction(restaurant_id):
    """Get ML-based rating prediction for a restaurant"""
    try:
        if not ML_ANALYTICS_ENABLED:
            return jsonify({'error': 'ML Analytics not available'}), 503
        
        # Get historical ratings from database
        history = RestaurantRatingHistory.query.filter_by(
            restaurant_id=str(restaurant_id)
        ).order_by(RestaurantRatingHistory.date).all()
        
        historical_ratings = [h.average_rating for h in history if h.average_rating]
        
        # Get current reviews
        reviews = Review.query.filter_by(restaurant_id=str(restaurant_id)).all()
        
        if reviews:
            current_rating = sum(r.rating for r in reviews) / len(reviews)
            review_count = len(reviews)
        else:
            current_rating = 0
            review_count = 0
        
        restaurant_data = {
            'current_rating': current_rating,
            'review_count': review_count
        }
        
        # Create predictor and get predictions
        predictor = RatingPredictor()
        
        predictions = {
            '30_days': predictor.predict_rating(restaurant_data, historical_ratings, days_ahead=30),
            '60_days': predictor.predict_rating(restaurant_data, historical_ratings, days_ahead=60),
            '90_days': predictor.predict_rating(restaurant_data, historical_ratings, days_ahead=90)
        }
        
        return jsonify(predictions)
        
    except Exception as e:
        print(f"❌ Error in rating prediction: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/sentiment/<restaurant_id>', methods=['GET'])
def get_sentiment_analysis(restaurant_id):
    """Get sentiment analysis of reviews for a restaurant"""
    try:
        if not ML_ANALYTICS_ENABLED:
            return jsonify({'error': 'ML Analytics not available'}), 503
        
        # Get all reviews for this restaurant
        reviews = Review.query.filter_by(restaurant_id=str(restaurant_id)).all()
        
        if not reviews:
            return jsonify({
                'overall_sentiment': 0,
                'sentiment_distribution': {'positive': 0, 'neutral': 0, 'negative': 0},
                'aspect_scores': {},
                'common_keywords': []
            })
        
        analyzer = SentimentAnalyzer()
        
        results = {
            'overall_sentiment': 0,
            'sentiment_distribution': {'positive': 0, 'neutral': 0, 'negative': 0},
            'aspect_scores': {'food': [], 'service': [], 'ambiance': [], 'value': []},
            'common_keywords': []
        }
        
        all_keywords = []
        
        for review in reviews:
            # Check if already analyzed
            existing = ReviewSentiment.query.filter_by(review_id=review.id).first()
            
            if not existing and review.review_text:
                # Analyze
                analysis = analyzer.analyze_review(review.review_text)
                
                # Save to database
                sentiment = ReviewSentiment(
                    review_id=review.id,
                    sentiment_score=analysis['sentiment_score'],
                    sentiment_label=analysis['sentiment_label'],
                    aspects=analysis['aspects'],
                    keywords=analysis['keywords']
                )
                db.session.add(sentiment)
                db.session.commit()
            elif existing:
                analysis = {
                    'sentiment_score': existing.sentiment_score,
                    'sentiment_label': existing.sentiment_label,
                    'aspects': existing.aspects or {},
                    'keywords': existing.keywords or []
                }
            else:
                continue
            
            # Aggregate results
            results['overall_sentiment'] += analysis['sentiment_score']
            results['sentiment_distribution'][analysis['sentiment_label']] += 1
            
            for aspect, score in analysis['aspects'].items():
                if aspect in results['aspect_scores']:
                    results['aspect_scores'][aspect].append(score)
            
            all_keywords.extend(analysis['keywords'])
        
        # Calculate averages
        if reviews:
            results['overall_sentiment'] /= len(reviews)
            results['overall_sentiment'] = round(results['overall_sentiment'], 2)
            
            for aspect in results['aspect_scores']:
                if results['aspect_scores'][aspect]:
                    results['aspect_scores'][aspect] = round(
                        sum(results['aspect_scores'][aspect]) / len(results['aspect_scores'][aspect]), 2
                    )
                else:
                    results['aspect_scores'][aspect] = 0
        
        # Get most common keywords
        from collections import Counter
        keyword_counts = Counter(all_keywords)
        results['common_keywords'] = [
            {'word': k, 'count': v} for k, v in keyword_counts.most_common(20)
        ]
        
        return jsonify(results)
        
    except Exception as e:
        print(f"❌ Error in sentiment analysis: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/recommendations/<restaurant_id>', methods=['GET'])
def get_ai_recommendations(restaurant_id):
    """Get AI-generated recommendations for a restaurant"""
    try:
        if not ML_ANALYTICS_ENABLED:
            return jsonify({'error': 'ML Analytics not available'}), 503
        
        # Get restaurant data from dataset
        restaurant_row = original_restaurant_data[
            original_restaurant_data['Restaurant ID'] == int(restaurant_id)
        ]
        
        if restaurant_row.empty:
            return jsonify({'error': 'Restaurant not found'}), 404
        
        restaurant_info = restaurant_row.iloc[0].to_dict()
        
        # Get reviews
        reviews = Review.query.filter_by(restaurant_id=str(restaurant_id)).all()
        
        restaurant_data = {
            'current_rating': restaurant_info.get('Aggregate rating', 0),
            'review_count': len(reviews),
            'responded_review_count': 0,  # Placeholder
            'photo_count': 0,  # Placeholder
            'has_delivery': restaurant_info.get('Has Online delivery', False),
            'has_parking': False,
            'has_wifi': False,
            'has_outdoor_seating': False,
            'avg_cost_for_two': restaurant_info.get('Average Cost for two', 0),
            'cuisines': restaurant_info.get('Cuisines', '')
        }
        
        # Get competitors (same city, similar price range)
        city = restaurant_info.get('City', '')
        price_range = restaurant_info.get('Price range', 2)
        
        competitors_df = original_restaurant_data[
            (original_restaurant_data['City'] == city) &
            (original_restaurant_data['Price range'] == price_range) &
            (original_restaurant_data['Restaurant ID'] != int(restaurant_id))
        ].head(10)
        
        competitors_data = []
        for _, comp in competitors_df.iterrows():
            competitors_data.append({
                'has_delivery': comp.get('Has Online delivery', False),
                'has_parking': False,
                'has_wifi': False,
                'has_outdoor_seating': False,
                'avg_cost_for_two': comp.get('Average Cost for two', 0)
            })
        
        # Market trends (placeholder)
        market_trends = {
            'vegan_search_increase': 35,
            'trending_cuisines': ['Korean', 'Mediterranean'],
            'peak_search_hours': [12, 13, 19, 20]
        }
        
        # Generate recommendations
        engine = RecommendationEngine()
        recommendations = engine.generate_recommendations(
            restaurant_data,
            competitors_data,
            market_trends
        )
        
        # Save to database
        for rec in recommendations:
            # Check if similar recommendation already exists
            existing = AIRecommendation.query.filter_by(
                restaurant_id=str(restaurant_id),
                title=rec['title'],
                status='pending'
            ).first()
            
            if not existing:
                ai_rec = AIRecommendation(
                    restaurant_id=str(restaurant_id),
                    recommendation_type=rec['type'],
                    title=rec['title'],
                    description=rec['description'],
                    impact_score=rec['impact_score'],
                    priority=rec['priority'],
                    status='pending'
                )
                db.session.add(ai_rec)
        
        db.session.commit()
        
        return jsonify(recommendations)
        
    except Exception as e:
        print(f"❌ Error generating recommendations: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/competitor-benchmark/<restaurant_id>', methods=['GET'])
def get_competitor_benchmark(restaurant_id):
    """Get competitor benchmarking data"""
    try:
        # Get restaurant details
        restaurant_row = original_restaurant_data[
            original_restaurant_data['Restaurant ID'] == int(restaurant_id)
        ]
        
        if restaurant_row.empty:
            return jsonify({'error': 'Restaurant not found'}), 404
        
        restaurant = restaurant_row.iloc[0]
        
        # Find competitors (same city, similar price range)
        city = restaurant['City']
        price_range = restaurant.get('Price range', 2)
        
        competitors = original_restaurant_data[
            (original_restaurant_data['City'] == city) &
            (original_restaurant_data['Price range'] == price_range) &
            (original_restaurant_data['Restaurant ID'] != int(restaurant_id))
        ].head(10)
        
        benchmark = {
            'your_rating': restaurant['Aggregate rating'],
            'competitor_avg_rating': competitors['Aggregate rating'].mean() if not competitors.empty else 0,
            'your_rank': None,
            'total_in_category': len(competitors) + 1,
            'competitors': []
        }
        
        # Calculate rank
        all_restaurants = pd.concat([restaurant_row, competitors])
        all_restaurants_sorted = all_restaurants.sort_values('Aggregate rating', ascending=False)
        benchmark['your_rank'] = list(all_restaurants_sorted['Restaurant ID']).index(int(restaurant_id)) + 1
        
        # Add competitor details
        for _, comp in competitors.iterrows():
            benchmark['competitors'].append({
                'name': comp['Restaurant Name'],
                'rating': comp['Aggregate rating'],
                'features': {
                    'delivery': comp.get('Has Online delivery', False),
                    'table_booking': comp.get('Has Table booking', False)
                }
            })
        
        return jsonify(benchmark)
        
    except Exception as e:
        print(f"❌ Error in competitor benchmark: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/ml-analytics-demo')
def ml_analytics_demo():
    """Demo page for ML analytics features"""
    return render_template('ml_analytics_demo.html')


# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)