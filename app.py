from flask import Flask, render_template, redirect, url_for, flash, send_from_directory
import os

app = Flask(__name__)
app.secret_key = 'dev-key-for-arcade-zone'  # Simplified secret key

@app.route('/')
def index():
    """Main page route"""
    return render_template('index.html')

@app.route('/games/<path:filename>')
def games(filename):
    """Serve game files"""
    try:
        return send_from_directory('games', filename)
    except FileNotFoundError:
        flash('Game not found', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)