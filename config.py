"""
Configuration for Restaurant Recommender App
"""

import os
from datetime import timedelta


# Secret key for sessions (CHANGE THIS IN PRODUCTION!)
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-12345'

# Database configuration
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///restaurant_app.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Session configuration
PERMANENT_SESSION_LIFETIME = timedelta(days=7)
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Flask-Login configuration
REMEMBER_COOKIE_DURATION = timedelta(days=30)
REMEMBER_COOKIE_SECURE = False  # Set to True in production
REMEMBER_COOKIE_HTTPONLY = True

# Pagination
RESULTS_PER_PAGE = 10
HISTORY_PER_PAGE = 20

# File upload (for future features)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# API Keys (from .env file)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')
