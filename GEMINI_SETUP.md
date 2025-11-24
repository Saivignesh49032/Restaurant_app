# Gemini API Setup Guide

This project now supports Google Gemini AI for expanded restaurant search capabilities beyond the dataset.

## Getting Your API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API Key" or navigate to API Keys section
4. Create a new API key
5. Copy the API key

## Configuration

### Option 1: Environment Variable (Recommended)

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_actual_api_key_here
```

### Option 2: System Environment Variable

Set it in your system:
- Windows: `setx GEMINI_API_KEY "your_key"`
- Linux/Mac: `export GEMINI_API_KEY="your_key"`

## Features Enabled with Gemini

- **Expanded Search**: Search restaurants in any city, not limited to dataset
- **Real-time Data**: Get current restaurant information
- **Detailed Information**: Access descriptions, reviews, and features
- **Hybrid Mode**: Automatically falls back to Gemini when dataset has no results
- **AI Recommendations**: Get AI-powered personalized recommendations

## API Endpoints

- `/api/gemini/search` - Search restaurants using Gemini
- `/api/gemini/details` - Get detailed restaurant information
- `/api/gemini/status` - Check if Gemini is available
- `/api/recommend/hybrid` - Hybrid search (dataset + Gemini fallback)

## Notes

- The app will work without Gemini API key, but Gemini features will be disabled
- Dataset-based recommendations will continue to work normally
- Gemini features are optional enhancements

