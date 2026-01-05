"""
Database Migration Script
Makes user_id nullable in reviews table to allow sample reviews
"""
import sqlite3
import shutil
from datetime import datetime

# Backup the database first
db_path = 'instance/restaurant_app.db'
backup_path = f'instance/restaurant_app_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

try:
    print(f"📦 Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("✅ Backup created successfully")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔧 Updating reviews table schema...")
    
    # Disable foreign keys temporarily
    cursor.execute('PRAGMA foreign_keys=OFF;')
    
    # Drop the new table if it exists from a previous failed migration
    cursor.execute('DROP TABLE IF EXISTS reviews_new')
    
    # Create new table with nullable user_id
    cursor.execute('''
        CREATE TABLE reviews_new (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            restaurant_id VARCHAR(200) NOT NULL,
            restaurant_name VARCHAR(200) NOT NULL,
            city VARCHAR(100) NOT NULL,
            rating INTEGER NOT NULL,
            review_text TEXT,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Copy existing data - map old columns to new columns
    # Old schema: id, user_id, restaurant_id, restaurant_name, restaurant_city, rating, review_text, created_at, updated_at, city
    # New schema: id, user_id, restaurant_id, restaurant_name, city, rating, review_text, created_at, updated_at
    # Use COALESCE to prefer 'city' column over 'restaurant_city' if both exist
    cursor.execute('''
        INSERT INTO reviews_new (id, user_id, restaurant_id, restaurant_name, city, rating, review_text, created_at, updated_at)
        SELECT id, user_id, restaurant_id, restaurant_name, COALESCE(city, restaurant_city, 'Unknown'), rating, review_text, created_at, updated_at
        FROM reviews
    ''')
    
    # Drop old table
    cursor.execute('DROP TABLE reviews')
    
    # Rename new table
    cursor.execute('ALTER TABLE reviews_new RENAME TO reviews')
    
    # Re-enable foreign keys
    cursor.execute('PRAGMA foreign_keys=ON;')
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("✅ Database schema updated successfully!")
    print("✅ user_id is now nullable - sample reviews can be generated")
    print("\n🔄 Please restart your Flask app for changes to take effect")
    
except FileNotFoundError:
    print(f"❌ Database file not found: {db_path}")
    print("The database will be created automatically when you start the app")
except Exception as e:
    print(f"❌ Error during migration: {e}")
    print(f"💾 Backup available at: {backup_path}")
