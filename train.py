import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import OneHotEncoder, RobustScaler, MinMaxScaler, MultiLabelBinarizer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.feature_selection import SelectKBest, f_regression
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

# Data validation and cleaning
print("\nInitial data validation:")
print(f"Total samples: {len(df)}")
print(f"Rating range: {df['Aggregate rating'].min():.1f} to {df['Aggregate rating'].max():.1f}")
print(f"Missing values:\n{df.isnull().sum()}")

# Remove outliers from target variable (if any)
Q1 = df['Aggregate rating'].quantile(0.25)
Q3 = df['Aggregate rating'].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR
df = df[
    (df['Aggregate rating'] >= lower_bound) & 
    (df['Aggregate rating'] <= upper_bound)
]
print(f"\nSamples after outlier removal: {len(df)}")

# Preprocessing from CIT1
df.fillna({'Cuisines': df['Cuisines'].mode()[0]}, inplace=True)
binary_features = ['Has Table booking', 'Has Online delivery', 'Is delivering now', 'Switch to order menu']
for col in binary_features:
    df[col] = df[col].map({'Yes':1 , 'No':0})

numerical_features = ['Country Code', 'Longitude', 'Latitude', 'Average Cost for two', 'Has Table booking', 'Has Online delivery', 'Is delivering now', 'Switch to order menu', 'Price range', 'Votes']
categorical_features = ['City', 'Cuisines', 'Currency','Rating color', 'Rating text']

# Create a complete preprocessing pipeline including feature selection
numerical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', RobustScaler())
])

categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

# First create the column transformer
feature_preprocessor = ColumnTransformer(
    transformers=[
        ('num', numerical_transformer, numerical_features),
        ('cat', categorical_transformer, categorical_features)
    ],
    remainder='drop'  # Drop any other columns
)

# Create complete preprocessing pipeline including feature selection
preprocessor = Pipeline([
    ('features', feature_preprocessor),
    ('selector', SelectKBest(score_func=f_regression, k=20))  # Select top 20 features
])

X = df.drop(['Aggregate rating', 'Restaurant Name', 'Address', 'Locality', 'Locality Verbose'], axis=1)
y = df['Aggregate rating']

# First split the data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

# Scale the target variable to [0, 1] range first
print("\nScaling target variable...")
target_scaler = MinMaxScaler(feature_range=(0, 1))
y_train_scaled = target_scaler.fit_transform(y_train.to_numpy().reshape(-1, 1)).ravel()
y_test_scaled = target_scaler.transform(y_test.to_numpy().reshape(-1, 1)).ravel()

# Fit and transform features using the complete pipeline
print("\nPreprocessing and selecting features...")
X_train_transformed = preprocessor.fit_transform(X_train, y_train_scaled)  # Pass scaled target for feature selection
X_test_transformed = preprocessor.transform(X_test)

print(f"\nTransformed feature space shape: {X_train_transformed.shape}")
X_train_transformed = preprocessor.transform(X_train)
X_test_transformed = preprocessor.transform(X_test)
print("Data transformed.")

# Save the rating preprocessor (different from the recommender one)
RATING_PREPROCESSOR_PATH = os.path.join(ASSETS_DIR, 'rating_preprocessor.joblib')
joblib.dump(preprocessor, RATING_PREPROCESSOR_PATH)
print(f"Rating preprocessor saved to {RATING_PREPROCESSOR_PATH}")

# Save the target scaler and preprocessor
TARGET_SCALER_PATH = os.path.join(ASSETS_DIR, 'target_scaler.joblib')
joblib.dump(target_scaler, TARGET_SCALER_PATH)
print(f"Target scaler saved to {TARGET_SCALER_PATH}")

# Save the complete preprocessor (includes feature selection)
PREPROCESSOR_PATH = os.path.join(ASSETS_DIR, 'rating_preprocessor.joblib')
joblib.dump(preprocessor, PREPROCESSOR_PATH)
print(f"Rating preprocessor saved to {PREPROCESSOR_PATH}")

# Define a simple model with appropriate regularization
model = MLPRegressor(
    hidden_layer_sizes=(20, 10),  # Simple architecture matching selected features
    activation='relu',
    solver='adam',
    alpha=0.01,  # L2 regularization
    batch_size=32,
    learning_rate='adaptive',
    learning_rate_init=0.001,
    max_iter=1000,
    random_state=42,
    early_stopping=True,
    validation_fraction=0.2,
    n_iter_no_change=20,
    tol=1e-4,
    verbose=True
)

print("\nTraining MLP model...")
print(f"Input shape: {X_train_transformed.shape}")
print(f"Target shape: {y_train_scaled.shape}")
model.fit(X_train_transformed, y_train_scaled)
print("MLP Model trained.")

# Calculate and display detailed metrics
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Training metrics (using unscaled predictions for interpretability)
y_train_pred = target_scaler.inverse_transform(model.predict(X_train_transformed).reshape(-1, 1)).ravel()
y_train_unscaled = target_scaler.inverse_transform(y_train.to_numpy().reshape(-1, 1)).ravel()
train_mse = mean_squared_error(y_train_unscaled, y_train_pred)
train_rmse = np.sqrt(train_mse)
train_mae = mean_absolute_error(y_train_unscaled, y_train_pred)
train_r2 = r2_score(y_train_unscaled, y_train_pred)

# Testing metrics (using unscaled predictions for interpretability)
y_test_pred = target_scaler.inverse_transform(model.predict(X_test_transformed).reshape(-1, 1)).ravel()
y_test_unscaled = target_scaler.inverse_transform(y_test.to_numpy().reshape(-1, 1)).ravel()
test_mse = mean_squared_error(y_test_unscaled, y_test_pred)
test_rmse = np.sqrt(test_mse)
test_mae = mean_absolute_error(y_test_unscaled, y_test_pred)
test_r2 = r2_score(y_test_unscaled, y_test_pred)

# Print additional statistics
# Get predictions (scaled)
y_train_pred_scaled = model.predict(X_train_transformed)
y_test_pred_scaled = model.predict(X_test_transformed)

# Convert predictions back to original scale
y_train_pred = target_scaler.inverse_transform(y_train_pred_scaled.reshape(-1, 1)).ravel()
y_test_pred = target_scaler.inverse_transform(y_test_pred_scaled.reshape(-1, 1)).ravel()

# Clip predictions to valid range [0, 5]
y_train_pred = np.clip(y_train_pred, 0, 5)
y_test_pred = np.clip(y_test_pred, 0, 5)

# Print feature importance information
if hasattr(preprocessor.named_steps['selector'], 'scores_'):
    feature_scores = preprocessor.named_steps['selector'].scores_
    feature_names = preprocessor.named_steps['features'].get_feature_names_out()
    feature_importance = list(zip(feature_names, feature_scores))
    feature_importance.sort(key=lambda x: x[1], reverse=True)
    
    print("\nTop 10 Most Important Features:")
    for name, score in feature_importance[:10]:
        print(f"{name}: {score:.4f}")

# Calculate metrics on original scale
y_train_orig = target_scaler.inverse_transform(y_train_scaled.reshape(-1, 1)).ravel()
y_test_orig = target_scaler.inverse_transform(y_test_scaled.reshape(-1, 1)).ravel()

train_mse = mean_squared_error(y_train_orig, y_train_pred)
train_rmse = np.sqrt(train_mse)
train_mae = mean_absolute_error(y_train_orig, y_train_pred)
train_r2 = r2_score(y_train_orig, y_train_pred)

test_mse = mean_squared_error(y_test_orig, y_test_pred)
test_rmse = np.sqrt(test_mse)
test_mae = mean_absolute_error(y_test_orig, y_test_pred)
test_r2 = r2_score(y_test_orig, y_test_pred)

print("\nPrediction Statistics:")
print(f"Training predictions range: {y_train_pred.min():.2f} to {y_train_pred.max():.2f}")
print(f"Testing predictions range: {y_test_pred.min():.2f} to {y_test_pred.max():.2f}")
print(f"Actual values range: {y_test_orig.min():.2f} to {y_test_orig.max():.2f}")

print("\nModel Performance Metrics:")
print("Training Metrics:")
print(f"R² score: {train_r2:.4f}")
print(f"RMSE: {train_rmse:.4f}")
print(f"MAE: {train_mae:.4f}")
print("\nTesting Metrics:")
print(f"R² score: {test_r2:.4f}")
print(f"RMSE: {test_rmse:.4f}")
print(f"MAE: {test_mae:.4f}")

# Save the model
RATING_MODEL_PATH = os.path.join(ASSETS_DIR, 'rating_model.joblib')
joblib.dump(model, RATING_MODEL_PATH)
print(f"\nMLP Rating Model saved to {RATING_MODEL_PATH}")


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
        ('num', RobustScaler(), recommendation_numerical_features),
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