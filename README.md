# 🍽️ Restaurant Recommender System

A comprehensive restaurant recommendation system that combines machine learning models with AI-powered search capabilities. The system provides personalized restaurant recommendations based on user preferences, location, cuisine, and price range.

## ✨ Features

### Core Features
- **ML-Based Recommendations**: Uses trained machine learning models for accurate restaurant suggestions
- **Rating Prediction**: Predicts restaurant ratings based on various features
- **Interactive Map**: Visualize restaurant locations on an interactive map
- **City & Cuisine Filtering**: Smart autocomplete for cities and cuisines
- **Multiple Search Modes**:
  - **Dataset Mode**: Fast recommendations from trained dataset
  - **Hybrid Mode**: Dataset first, AI fallback for expanded coverage
  - **AI Search**: Pure AI-powered search using Google Gemini

### AI-Powered Features (Gemini Integration)
- **Expanded Coverage**: Search restaurants in any city worldwide
- **Real-time Data**: Get current restaurant information
- **Detailed Descriptions**: AI-generated restaurant descriptions (minimum 150 words)
- **Smart Fallback**: Automatically uses AI when dataset has no results
- **Google Places Fallback**: Uses Google Places API when Gemini is unavailable

### Search Modes Explained
- **Dataset Mode**: Fast, accurate results from your trained dataset (limited to dataset cities)
- **Hybrid Mode**: Tries dataset first, automatically falls back to Gemini → Google Places if no results
- **AI Search**: Direct Gemini search, with Google Places fallback if Gemini fails

### User Interface
- **Modern, Responsive Design**: Works on desktop, tablet, and mobile
- **Interactive Dropdowns**: Easy-to-use cuisine selector
- **Real-time Search**: Instant autocomplete suggestions
- **Map Integration**: View restaurants on interactive maps
- **Directions**: Get Google Maps directions to restaurants

## 🚀 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** (Python 3.11 recommended)
- **pip** (Python package manager)
- **Git** (for cloning the repository)

## 📦 Installation

### Step 1: Clone the Repository

```bash
git clone <your-repository-url>
cd Restaurant_App
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `scikit-learn` - Machine learning models
- `flask` - Web framework
- `folium` - Map visualization
- `joblib` - Model serialization
- `google-generativeai` - Gemini AI integration
- `python-dotenv` - Environment variable management

### Step 4: Prepare Dataset and Models

Ensure you have the following files in the `assets/` directory:
- `Dataset .csv` - Restaurant dataset
- `rating_model.joblib` - Trained rating prediction model
- `rating_preprocessor.joblib` - Rating model preprocessor
- `target_scaler.joblib` - Target variable scaler
- `recommender_preprocessor.joblib` - Recommender preprocessor
- `mlb_classes.joblib` - Multi-label binarizer classes
- `processed_restaurant_vectors.csv` - Processed restaurant vectors

**Note**: If you don't have trained models, run:
```bash
python train.py
```

This will train the models and generate all required files.

## ⚙️ Configuration

### Gemini API Setup (Optional but Recommended)

The Gemini API integration expands your search capabilities beyond the dataset.

#### Step 1: Get API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API Key" or navigate to API Keys section
4. Create a new API key
5. Copy the API key

#### Step 2: Configure API Key

Create a `.env` file in the project root:

**Windows (PowerShell):**
```powershell
[System.IO.File]::WriteAllText("$PWD\.env", "GEMINI_API_KEY=your_api_key_here", [System.Text.Encoding]::UTF8)
```

**Linux/Mac:**
```bash
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

**Or manually create `.env` file:**
```
GEMINI_API_KEY=your_actual_api_key_here
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
```

### Google Places API Setup (Optional - Fallback)

Google Places API serves as a fallback when Gemini API is unavailable or returns no results.

#### Step 1: Get API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the "Places API" (New) or "Places API" (Legacy)
4. Go to "Credentials" → "Create Credentials" → "API Key"
5. Copy the API key
6. (Optional) Restrict the API key to "Places API" for security

#### Step 2: Add to `.env` File

Add the Google Places API key to your `.env` file:
```
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
```

**Important Security Notes:**
- Never commit your `.env` file to version control
- The `.env` file is already in `.gitignore`
- Regenerate your API key if it's ever exposed
- Keep your API key secure and private
- Restrict API keys in Google Cloud Console for better security

#### Step 3: Verify Configuration

The app will automatically detect if Gemini is available. You can check the status by:
- Looking at the search mode dropdown (AI option will be enabled if available)
- Visiting `/api/gemini/status` endpoint

## 🏃 Running the Application

### Start the Flask Server

```bash
python app.py
```

The application will start on `http://127.0.0.1:5000`

### Access the Application

Open your web browser and navigate to:
```
http://localhost:5000
```

## 📖 Usage Guide

### Basic Search

1. **Select City**: Type and select a city from the autocomplete dropdown
2. **Choose Cuisines**: 
   - After selecting a city, the cuisine dropdown will be enabled
   - Click the dropdown to see available cuisines for that city
   - Select multiple cuisines using checkboxes
3. **Set Price Range**: Choose from 1 (Cheap) to 4 (Very Expensive)
4. **Choose Visit Type**: Select "Visit" or "Delivery"
5. **Table Booking** (if visiting): Select if you need table booking
6. **Select Search Mode**:
   - **Dataset**: Fast, accurate results from your trained model
   - **Hybrid**: Tries dataset first, falls back to AI if no results
   - **AI Search**: Pure AI-powered search (requires Gemini API)
7. **Click "Find Restaurants"**

### Viewing Results

- Results are displayed as cards with:
  - Restaurant name and rating
  - Cuisines served
  - Average cost for two
  - Features (delivery, table booking)
  - Similarity/match score
- Sort results by Rating, Cost, or Similarity
- Click "View on Map" to see location
- Click "Directions" for Google Maps navigation

### Map View

- Click "View All on Map" to see all recommendations
- Click on any restaurant card's "View on Map" button
- Use map controls to:
  - Center map
  - Toggle clustering
  - Get directions
  - View restaurant details

## 🗂️ Project Structure

```
Restaurant_App/
│
├── app.py                      # Main Flask application
├── train.py                    # Model training script
├── gemini_api.py              # Gemini AI integration
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── CHANGELOG.md               # Version history
├── GEMINI_SETUP.md            # Gemini setup guide
├── .env                       # Environment variables (not in git)
├── .gitignore                 # Git ignore rules
│
├── assets/                    # Data and model files
│   ├── Dataset .csv           # Restaurant dataset
│   ├── rating_model.joblib   # Rating prediction model
│   ├── rating_preprocessor.joblib
│   ├── target_scaler.joblib
│   ├── recommender_preprocessor.joblib
│   ├── mlb_classes.joblib
│   └── processed_restaurant_vectors.csv
│
├── static/                    # Static files
│   ├── css/
│   │   └── style.css         # Stylesheet
│   └── js/
│       ├── main.js           # Main JavaScript
│       └── map.js            # Map functionality
│
└── templates/                 # HTML templates
    ├── index.html            # Main page
    └── map.html              # Map page
```

## 🔌 API Endpoints

### Dataset-Based Endpoints

- `GET /` - Home page
- `GET /map` - Map view page
- `POST /api/recommend` - Get recommendations (dataset)
- `POST /api/predict_rating` - Predict restaurant rating
- `GET /api/cities` - Get list of cities
- `GET /api/cuisines?city=<city>` - Get cuisines for a city

### Gemini AI Endpoints

- `POST /api/gemini/search` - AI-powered restaurant search
- `POST /api/gemini/details` - Get detailed restaurant information
- `GET /api/gemini/status` - Check Gemini API availability
- `POST /api/recommend/hybrid` - Hybrid search (dataset + AI fallback)

## 🛠️ Training Models

To train or retrain the models:

```bash
python train.py
```

This script:
1. Loads the dataset
2. Trains the rating prediction model (CIT1)
3. Creates recommender system assets (CIT2)
4. Saves all models and preprocessors

**Note**: Training may take several minutes depending on dataset size.

## 🐛 Troubleshooting

### Issue: "GEMINI_API_KEY not found"
**Solution**: 
- Ensure `.env` file exists in project root
- Check that API key is correctly formatted: `GEMINI_API_KEY=your_key`
- Verify file encoding is UTF-8 (not UTF-16)

### Issue: "Module not found" errors
**Solution**:
```bash
pip install -r requirements.txt
```

### Issue: Models not found
**Solution**:
```bash
python train.py
```

### Issue: Map not displaying
**Solution**:
- Check internet connection (maps load from external sources)
- Clear browser cache
- Check browser console for errors

### Issue: Encoding errors with .env file
**Solution** (Windows PowerShell):
```powershell
Remove-Item .env -ErrorAction SilentlyContinue
[System.IO.File]::WriteAllText("$PWD\.env", "GEMINI_API_KEY=your_key", [System.Text.Encoding]::UTF8)
```

## 🔒 Security Best Practices

1. **Never commit sensitive data**:
   - `.env` file is in `.gitignore`
   - Never commit API keys
   - Never commit model files if they contain sensitive data

2. **API Key Management**:
   - Use environment variables
   - Rotate keys regularly
   - Use different keys for development/production

3. **Production Deployment**:
   - Use a production WSGI server (Gunicorn, uWSGI)
   - Set `debug=False` in production
   - Use HTTPS
   - Implement rate limiting

## 📊 Performance Tips

- **Caching**: Models are loaded once at startup
- **Database**: Consider using a database for large datasets
- **API Limits**: Be aware of Gemini API rate limits
- **Optimization**: Use hybrid mode to balance speed and coverage

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Production (using Gunicorn)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker (Example)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 📝 Version History

- **v2.2**: Added Gemini AI integration, hybrid search, enhanced UI
- **v2.1**: Dropdown cuisine selector, bug fixes, map improvements
- **v2.0**: Initial ML-based recommendation system

See `CHANGELOG.md` for detailed version history.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is for educational purposes. Please ensure you have proper licenses for:
- Dataset usage
- Google Gemini API usage
- Any third-party libraries

## 🙏 Acknowledgments

- Google Gemini AI for restaurant search capabilities
- Folium for map visualization
- scikit-learn for machine learning models
- Flask for web framework

## 📧 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review `GEMINI_SETUP.md` for API setup help

## 🎯 Future Enhancements

- [ ] User authentication and saved preferences
- [ ] Restaurant reviews and ratings
- [ ] Advanced filtering options
- [ ] Restaurant comparison feature
- [ ] Mobile app version
- [ ] Multi-language support
- [ ] Integration with food delivery APIs

---

**Happy Restaurant Hunting! 🍽️✨**

