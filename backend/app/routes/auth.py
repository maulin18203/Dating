from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import check_password_hash
import jwt
from datetime import datetime, timedelta
from app import db, bcrypt
from app.models.user import User, UserPreference

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    if current_user.is_authenticated:
        return jsonify({'message': 'Already authenticated'}), 400
    
    data = request.get_json()
    
    # Check if email or username already exists
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'message': 'Email already registered'}), 400
    
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({'message': 'Username already taken'}), 400
    
    # Create new user
    user = User(
        email=data.get('email'),
        username=data.get('username'),
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        birthdate=datetime.strptime(data.get('birthdate'), '%Y-%m-%d') if data.get('birthdate') else None,
        gender=data.get('gender'),
    )
    
    # Set password
    user.set_password(data.get('password'))
    
    # Create user preferences
    preferences = UserPreference(
        user=user,
        interested_in=data.get('interested_in'),
        min_age=data.get('min_age', 18),
        max_age=data.get('max_age', 100),
        max_distance=data.get('max_distance', 50)
    )
    
    # Add to database
    db.session.add(user)
    db.session.add(preferences)
    db.session.commit()
    
    # Generate JWT token
    token = generate_token(user)
    
    return jsonify({
        'message': 'User registered successfully',
        'token': token,
        'user': user.to_dict()
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login a user"""
    if current_user.is_authenticated:
        return jsonify({'message': 'Already authenticated'}), 400
    
    data = request.get_json()
    
    # Check if user exists
    user = User.query.filter((User.email == data.get('username')) | 
                            (User.username == data.get('username'))).first()
    
    if not user or not user.check_password(data.get('password')):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # Update user status
    user.is_online = True
    user.last_seen = datetime.utcnow()
    db.session.commit()
    
    # Generate JWT token
    token = generate_token(user)
    
    # Log in user with Flask-Login
    login_user(user, remember=data.get('remember', False))
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout a user"""
    # Update user status
    current_user.is_online = False
    current_user.last_seen = datetime.utcnow()
    db.session.commit()
    
    # Log out user
    logout_user()
    
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    """Refresh JWT token"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'message': 'Missing or invalid token'}), 401
    
    token = auth_header.split(' ')[1]
    
    try:
        # Decode token
        payload = jwt.decode(
            token, 
            current_app.config['JWT_SECRET_KEY'], 
            algorithms=['HS256']
        )
        
        # Check if token is refresh type
        if payload.get('type') != 'refresh':
            return jsonify({'message': 'Not a refresh token'}), 401
        
        # Get user
        user = User.query.get(payload.get('sub'))
        
        if not user:
            return jsonify({'message': 'User not found'}), 401
        
        # Generate new tokens
        new_token = generate_token(user)
        
        return jsonify({
            'message': 'Token refreshed',
            'token': new_token
        }), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid token'}), 401

def generate_token(user):
    """Generate JWT tokens for a user"""
    # Access token payload
    access_payload = {
        'sub': user.id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
        'type': 'access'
    }
    
    # Refresh token payload
    refresh_payload = {
        'sub': user.id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES'],
        'type': 'refresh'
    }
    
    # Generate tokens
    access_token = jwt.encode(
        access_payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    refresh_token = jwt.encode(
        refresh_payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires': access_payload['exp']
    }
