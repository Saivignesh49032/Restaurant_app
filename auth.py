"""
Authentication routes for Restaurant Recommender App
Handles login, signup, logout, and user session management
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from models import db, User, UserPreference
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not email or not password or not name:
            flash('All fields are required!', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return render_template('signup.html')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered! Please login instead.', 'error')
            return redirect(url_for('auth.login'))
        
        # Create new user
        try:
            new_user = User(email=email, name=name)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            # Create default preferences
            preferences = UserPreference(user_id=new_user.id)
            db.session.add(preferences)
            db.session.commit()
            
            flash(f'🎉 Welcome {name}! Your account has been created successfully!', 'success')
            
            # Auto-login after signup
            login_user(new_user, remember=True)
            return redirect(url_for('home'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating account: {str(e)}', 'error')
            return render_template('signup.html')
    
    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Email and password are required!', 'error')
            return render_template('login.html')
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid email or password!', 'error')
            return render_template('login.html')
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Login user
        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name}! 🍕', 'success')
        
        # Redirect to next page or home
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('home')
        
        return redirect(next_page)
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout current user"""
    logout_user()
    flash('You have been logged out successfully. See you soon! 👋', 'info')
    return redirect(url_for('home'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with stats and preferences"""
    # Get user statistics
    from models import SearchHistory, Bookmark
    
    search_count = SearchHistory.query.filter_by(user_id=current_user.id).count()
    bookmark_count = Bookmark.query.filter_by(user_id=current_user.id).count()
    
    # Get recent searches
    recent_searches = SearchHistory.query.filter_by(user_id=current_user.id)\
        .order_by(SearchHistory.searched_at.desc())\
        .limit(5)\
        .all()
    
    # Get bookmarks
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id)\
        .order_by(Bookmark.bookmarked_at.desc())\
        .limit(10)\
        .all()
    
    return render_template('dashboard.html',
                         search_count=search_count,
                         bookmark_count=bookmark_count,
                         recent_searches=recent_searches,
                         bookmarks=bookmarks)


@auth_bp.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    """Edit user preferences"""
    user_pref = UserPreference.query.filter_by(user_id=current_user.id).first()
    
    if not user_pref:
        # Create if doesn't exist
        user_pref = UserPreference(user_id=current_user.id)
        db.session.add(user_pref)
        db.session.commit()
    
    if request.method == 'POST':
        # Update preferences
        user_pref.favorite_cuisines = request.form.getlist('cuisines')
        user_pref.dietary_restrictions = request.form.getlist('dietary')
        user_pref.budget_preference = int(request.form.get('budget', 2))
        user_pref.preferred_features = request.form.getlist('features')
        user_pref.preferred_city = request.form.get('city', '')
        user_pref.min_rating = float(request.form.get('min_rating', 3.0))
        
        db.session.commit()
        flash('✅ Your preferences have been updated!', 'success')
        return redirect(url_for('auth.dashboard'))
    
    return render_template('preferences.html', preferences=user_pref)
