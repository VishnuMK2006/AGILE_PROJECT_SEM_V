from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify, send_from_directory
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key

# Database configuration
DATABASE = 'users.db'

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with users table"""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

@app.route('/')
def index():
    """Main page route"""
    if 'user_id' in session:
        return render_template('index.html', logged_in=True, username=session.get('username'))
    return render_template('index.html', logged_in=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?',
            (username, username)
        ).fetchone()
        conn.close()
        
        if user and verify_password(password, user['password_hash']):
            # Update last login
            conn = get_db_connection()
            conn.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user['id'],)
            )
            conn.commit()
            conn.close()
            
            # Set session
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username/email or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup route"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all fields', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('signup.html')
        
        # Check if user already exists
        conn = get_db_connection()
        existing_user = conn.execute(
            'SELECT id FROM users WHERE username = ? OR email = ?',
            (username, email)
        ).fetchone()
        
        if existing_user:
            flash('Username or email already exists', 'error')
            conn.close()
            return render_template('signup.html')
        
        # Create new user
        password_hash = hash_password(password)
        try:
            conn.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            conn.commit()
            
            # Get the new user
            new_user = conn.execute(
                'SELECT * FROM users WHERE username = ?',
                (username,)
            ).fetchone()
            conn.close()
            
            # Set session
            session['user_id'] = new_user['id']
            session['username'] = new_user['username']
            flash('Account created successfully!', 'success')
            return redirect(url_for('index'))
            
        except sqlite3.Error as e:
            flash('An error occurred while creating your account', 'error')
            conn.close()
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    """Logout route"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    """User profile route"""
    if 'user_id' not in session:
        flash('Please log in to view your profile', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT username, email, created_at, last_login FROM users WHERE id = ?',
        (session['user_id'],)
    ).fetchone()
    conn.close()
    
    # Convert user row to dict and handle date conversion
    user_dict = dict(user) if user else {}
    if user_dict.get('created_at'):
        try:
            user_dict['created_at'] = datetime.strptime(user_dict['created_at'], '%Y-%m-%d %H:%M:%S')
        except:
            user_dict['created_at'] = None
    
    if user_dict.get('last_login'):
        try:
            user_dict['last_login'] = datetime.strptime(user_dict['last_login'], '%Y-%m-%d %H:%M:%S')
        except:
            user_dict['last_login'] = None
    
    return render_template('profile.html', user=user_dict)

@app.route('/api/check-auth')
def check_auth():
    """API endpoint to check authentication status"""
    return jsonify({
        'authenticated': 'user_id' in session,
        'username': session.get('username', '')
    })

@app.route('/games/<path:filename>')
def games(filename):
    """Serve game files"""
    try:
        return send_from_directory('games', filename)
    except FileNotFoundError:
        flash('Game not found', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)