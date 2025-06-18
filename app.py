from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import numpy as np 
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scores.db'
db = SQLAlchemy(app)
model = None
scaler = None
last_modified_time = None

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    time = db.Column(db.Integer, nullable=False) 
    difficulty = db.Column(db.String(10), nullable=False)  
    date = db.Column(db.DateTime, default=datetime.utcnow)

def train_model():
    global model, scaler, last_modified_time
    
    df = pd.read_csv('dataset.csv')

    last_modified_time = os.path.getmtime('dataset.csv')

    X = df[['score', 'time', 'difficulty']]
    y = df['label']
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale the features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    # Train the model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    return model, scaler

def check_and_retrain():
    global last_modified_time
    
    current_modified_time = os.path.getmtime('dataset.csv')
    if last_modified_time is None or current_modified_time > last_modified_time:
        train_model()

@app.route('/')
def home():
    return render_template('game.html')

@app.route('/save_score', methods=['POST'])
def save_score():
    data = request.get_json()
    new_score = Score(
        name=data['name'],
        score=data['score'],
        time=data['time'],
        difficulty=data['difficulty']
    )
    db.session.add(new_score)
    db.session.commit()
    new_data = pd.DataFrame({
        'score': [data['score']],
        'time': [data['time']],
        'difficulty': [data['difficulty']],
        'label': ['Good' if data['score'] > 10 else 'Need Practice'] 
    })

    if os.path.exists('dataset.csv'):
        new_data.to_csv('dataset.csv', mode='a', header=False, index=False)
    else:
        new_data.to_csv('dataset.csv', index=False)

    train_model()

    features = np.array([[data['score'], data['time'], data['difficulty']]])

    if model is not None and scaler is not None:
        features_scaled = scaler.transform(features)
        prediction = model.predict(features_scaled)[0]
    else:
        prediction = 'Unknown'
    
    return jsonify({
        'message': 'Score saved!',
        'performance': prediction
    })

@app.route('/get_leaderboard')
def get_leaderboard():
    scores = Score.query.order_by(Score.score.desc()).limit(10).all()
    leaderboard = [{
        'name': score.name,
        'score': score.score,
        'time': score.time,
        'difficulty': score.difficulty,
        'date': score.date.isoformat()
    } for score in scores]
    return jsonify(leaderboard)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    train_model()
    app.run(debug=True)