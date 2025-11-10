import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import OneHotEncoder, StandardScaler, MultiLabelBinarizer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
import os

print("Starting training script...")

# --- Create assets directory ---
ASSETS_DIR = 'assets'
if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)
    
DATASET_PATH = os.path.join(ASSETS_DIR, 'Dataset .csv')

# --- Part 1: CIT1 (Rating Prediction Model) ---
print("Loading data for Rating Model...")
df = pd.read_csv(DATASET_PATH)

# Preprocessing from CIT1
df.fillna({'Cuisines': df['Cuisines'].mode()[0]}, inplace=True)
binary_features = ['Has Table booking', 'Has Online delivery', 'Is delivering now', 'Switch to order menu']
for col in binary_features:
    df[col] = df[col].map({'Yes':1 , 'No':0})

numerical_features = ['Country Code', 'Longitude', 'Latitude', 'Average Cost for two', 'Has Table booking', 'Has Online delivery', 'Is delivering now', 'Switch to order menu', 'Price range', 'Votes']
categorical_features = ['City', 'Cuisines', 'Currency','Rating color', 'Rating text']

numerical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])
catergorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numerical_transformer, numerical_features),
        ('cat', catergorical_transformer, categorical_features)
    ],
    remainder='passthrough'
)

X = df.drop(['Aggregate rating', 'Restaurant Name', 'Address', 'Locality', 'Locality Verbose'], axis=1)
y = df['Aggregate rating']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

model_pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', LinearRegression())
])

print("Training Rating Model...")
model_pipeline.fit(X_train, y_train)
print("Rating Model trained.")

# Save the rating model
RATING_MODEL_PATH = os.path.join(ASSETS_DIR, 'rating_model.joblib')
joblib.dump(model_pipeline, RATING_MODEL_PATH)
print(f"Rating Model saved to {RATING_MODEL_PATH}")


# --- Part 2: CIT2 (Recommender System Assets) ---
print("\nStarting Recommender System asset creation...")
df_recommender = pd.read_csv(DATASET_PATH)

# Preprocessing from CIT2
df_recommender['Cuisines'] = df_recommender['Cuisines'].fillna('')
for col in binary_features:
    df_recommender[col] = df_recommender[col].map({'Yes': 1, 'No': 0})

# MultiLabelBinarizer for Cuisines
mlb = MultiLabelBinarizer()
df_recommender['Cuisines_List'] = df_recommender['Cuisines'].apply(lambda x: [c.strip() for c in str(x).split(',') if c.strip()])
mlb.fit(df_recommender['Cuisines_List'])
cuisines_encoded = mlb.transform(df_recommender['Cuisines_List'])
cuisines_df = pd.DataFrame(cuisines_encoded, columns=mlb.classes_, index=df_recommender.index)

df_processed_for_recommender = df_recommender.drop(columns=['Cuisines', 'Cuisines_List'])
df_processed_for_recommender = pd.concat([df_processed_for_recommender, cuisines_df], axis=1)

columns_to_drop_for_recommender_final = [
    'Restaurant ID', 'Restaurant Name', 'Address', 'Locality',
    'Locality Verbose', 'Rating color', 'Rating text', 'Country Code', 'Longitude', 'Latitude'
]
df_processed_for_recommender.drop(columns=columns_to_drop_for_recommender_final, errors='ignore', inplace=True)

# Define features for the recommendation preprocessor
recommendation_numerical_features = ['Average Cost for two', 'Votes', 'Price range']
recommendation_categorical_features = ['City', 'Currency']
recommendation_binary_features_pass = ['Has Table booking', 'Has Online delivery', 'Is delivering now', 'Switch to order menu']
recommendation_cuisine_features_pass = list(mlb.classes_)

all_features_for_recommender_pipeline = (
    recommendation_numerical_features +
    recommendation_categorical_features +
    recommendation_binary_features_pass +
    recommendation_cuisine_features_pass
)

recommendation_preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), recommendation_numerical_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), recommendation_categorical_features),
        ('bin', 'passthrough', recommendation_binary_features_pass),
        ('cuis', 'passthrough', recommendation_cuisine_features_pass)
    ],
    remainder='drop'
)

df_for_preprocessor_input = df_processed_for_recommender[all_features_for_recommender_pipeline]

print("Fitting recommender preprocessor...")
restaurant_feature_vectors_transformed = recommendation_preprocessor.fit_transform(df_for_preprocessor_input)
processed_feature_names = recommendation_preprocessor.get_feature_names_out()
processed_restaurants_df = pd.DataFrame(restaurant_feature_vectors_transformed, columns=processed_feature_names, index=df_recommender.index)
print("Preprocessor fitted.")

# Save the recommender assets
PREPROCESSOR_PATH = os.path.join(ASSETS_DIR, 'recommender_preprocessor.joblib')
MLB_CLASSES_PATH = os.path.join(ASSETS_DIR, 'mlb_classes.joblib')
VECTORS_PATH = os.path.join(ASSETS_DIR, 'processed_restaurant_vectors.csv')

joblib.dump(recommendation_preprocessor, PREPROCESSOR_PATH)
print(f"Recommender preprocessor saved to {PREPROCESSOR_PATH}")
joblib.dump(mlb.classes_, MLB_CLASSES_PATH)
print(f"MLB classes saved to {MLB_CLASSES_PATH}")
processed_restaurants_df.to_csv(VECTORS_PATH)
print(f"Restaurant vectors saved to {VECTORS_PATH}")

print("\n--- Training script finished successfully! ---")