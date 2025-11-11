import pandas as pd
import numpy as np
import joblib
import folium
from folium.plugins import MarkerCluster
import os
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from sklearn.preprocessing import StandardScaler, OneHotEncoder # We need these for the helper function
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.compose import ColumnTransformer # We need this for the helper function
from sklearn.pipeline import Pipeline # We need this for the helper function
from sklearn.impute import SimpleImputer # We need this for the helper function

# --- App Initialization ---
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management

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

    # 2. 4-star+ Rating Filter
    filtered_recommendations = filtered_recommendations[filtered_recommendations['Aggregate rating'] >= 4.0].copy()
    if filtered_recommendations.empty:
        return pd.DataFrame()

    # 3. Delivery/Visit Specific Filters
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

# --- Helper Routes for Autocomplete ---
@app.route('/api/cities')
def get_cities():
    """Get unique cities for autocomplete."""
    cities = original_restaurant_data['City'].unique().tolist()
    return jsonify(sorted(cities))

@app.route('/api/cuisines')
def get_cuisines():
    """Get unique cuisines for autocomplete."""
    city = request.args.get('city')
    
    if city:
        # Filter restaurants by city first
        city_restaurants = original_restaurant_data[
            original_restaurant_data['City'].str.lower() == city.lower()
        ]
        # Get cuisines only from the filtered restaurants
        all_cuisines = set()
        for cuisines in city_restaurants['Cuisines'].dropna():
            all_cuisines.update(c.strip() for c in cuisines.split(','))
    else:
        # If no city selected, return all cuisines
        all_cuisines = set()
        for cuisines in original_restaurant_data['Cuisines'].dropna():
            all_cuisines.update(c.strip() for c in cuisines.split(','))
    
    return jsonify(sorted(list(all_cuisines)))

# --- App Routes ---

@app.route('/')
def home():
    """Serves the main index.html page."""
    # Clear any old recommendations when returning to home
    if 'recommendations' in session:
        del session['recommendations']
    return render_template('index.html')

@app.route('/map')
def map_page():
    """Generates and serves the Folium map page."""
    
    # Get recommendations from session if they exist
    restaurants_to_show = None
    highlight_restaurant = None
    map_title = "All Restaurants Sample (20%)"
    
    if 'recommendations' in session:
        # Show only recommended restaurants
        recommendations = pd.DataFrame(session['recommendations'])
        if not recommendations.empty:
            if 'Restaurant ID' in recommendations.columns:
                coord_cols = ['Latitude', 'Longitude']
                missing_coords = any(
                    (col not in recommendations.columns) or recommendations[col].isnull().all()
                    for col in coord_cols
                )
                if missing_coords:
                    coord_source = original_restaurant_data[['Restaurant ID', 'Latitude', 'Longitude']]
                    recommendations = recommendations.drop(columns=[col for col in coord_cols if col in recommendations.columns], errors='ignore')
                    recommendations = recommendations.merge(coord_source, on='Restaurant ID', how='left')
            restaurants_to_show = recommendations
            map_title = f"Top {len(recommendations)} Recommended Restaurants"
    
    # Check if we're highlighting a specific restaurant
    restaurant_id = request.args.get('highlight')
    if restaurant_id and restaurants_to_show is not None and not restaurants_to_show.empty:
        if 'Restaurant ID' in restaurants_to_show.columns:
            rest_ids = pd.to_numeric(restaurants_to_show['Restaurant ID'], errors='coerce')
            highlight_rows = restaurants_to_show[rest_ids == int(restaurant_id)]
            highlight_restaurant = highlight_rows.iloc[0] if not highlight_rows.empty else None
            if highlight_restaurant is not None:
                map_title = f"Location: {highlight_restaurant['Restaurant Name']}"
    
    # If no recommendations, show a sample
    def needs_fallback(df):
        if df is None or df.empty:
            return True
        required_cols = {'Latitude', 'Longitude'}
        if not required_cols.issubset(df.columns):
            return True
        # Ensure there is at least one non-null coord
        return df[list(required_cols)].dropna(how='any').empty

    if needs_fallback(restaurants_to_show):
        MAX_MARKERS = 800
        sample_count = min(int(len(original_restaurant_data) * 0.2), MAX_MARKERS)
        restaurants_to_show = original_restaurant_data.sample(n=sample_count, random_state=42)
        highlight_restaurant = None
        map_title = "All Restaurants Sample (20%)"

    # Normalize delivery/booking flags to 0/1 for consistent display
    if 'Has Online delivery' in restaurants_to_show.columns:
        restaurants_to_show['Has Online delivery'] = _to_binary_yes_no_series(restaurants_to_show['Has Online delivery'])
    if 'Has Table booking' in restaurants_to_show.columns:
        restaurants_to_show['Has Table booking'] = _to_binary_yes_no_series(restaurants_to_show['Has Table booking'])

    # Initialize map (centered on a default location) with canvas rendering enabled for smoother panning
    # If highlighting a restaurant, center on its location
    if highlight_restaurant is not None:
        center = [highlight_restaurant['Latitude'], highlight_restaurant['Longitude']]
        zoom_start = 15
    else:
        # Center on the mean location of restaurants to show
        center = [restaurants_to_show['Latitude'].mean(), restaurants_to_show['Longitude'].mean()]
        zoom_start = 11 if 'recommendations' in session else 5
    
    m = folium.Map(location=center, zoom_start=zoom_start, width='100%', height='100%', prefer_canvas=True, control_scale=True)

    # Use MarkerCluster to group nearby markers and improve performance
    cluster = MarkerCluster(name='Restaurants', disableClusteringAtZoom=16).add_to(m)

    # Use lightweight circle markers (faster than full marker icons)
    for index, row in restaurants_to_show.iterrows():
        try:
            lat = float(row['Latitude'])
            lon = float(row['Longitude'])
        except Exception:
            continue
        
        # Enhanced popup with more details
        popup_text = f"""
            <div class='restaurant-popup'>
                <h4>{row.get('Restaurant Name', '')}</h4>
                <p><strong>Rating:</strong> {row.get('Aggregate rating', '')} ⭐</p>
                <p><strong>Cuisines:</strong> {row.get('Cuisines', '')}</p>
                <p><strong>Cost for Two:</strong> {row.get('Average Cost for two', '')} {row.get('Currency', '')}</p>
                <p><strong>Has Online Delivery:</strong> {'Yes' if row.get('Has Online delivery') == 1 else 'No'}</p>
                <p><strong>Table Booking:</strong> {'Yes' if row.get('Has Table booking') == 1 else 'No'}</p>
            </div>
        """
        
        # Highlight the selected restaurant
        is_highlighted = highlight_restaurant is not None and row['Restaurant ID'] == highlight_restaurant['Restaurant ID']
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=8 if is_highlighted else 4,
            color='#e74c3c' if is_highlighted else '#3186cc',
            fill=True,
            fill_opacity=0.9 if is_highlighted else 0.7,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(cluster)
        
    # Get the map's HTML representation
    map_html = m._repr_html_()
    
    return render_template('map.html', map_content=map_html, map_title=map_title)

@app.route('/api/recommend', methods=['POST'])
def api_recommend():
    """API endpoint to get recommendations."""
    try:
        data = request.json
        print(f"Received data: {data}")

        # Build the preference dictionary from the frontend request
        user_preferences = {
            'Cuisines': data.get('cuisines'),
            'Price range': int(data.get('priceRange')),
            'Visit_or_Delivery': data.get('visitType'),
            'Has Table booking': data.get('tableBooking'),
            'Has Online delivery': 'Yes' if data.get('visitType') == 'delivery' else 'No',
            'City': data.get('city')
        }

        # Run the recommender function
        recommended_restaurants = recommend_restaurants(
            user_preferences,
            processed_restaurants_df,
            original_restaurant_data,
            recommender_preprocessor,
            mlb_classes,
            all_features_for_recommender_pipeline
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

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)