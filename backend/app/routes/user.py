from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from app import db
from app.models.user import User, UserPreference, UserInterest, UserBlocked, Verification
from app.models.match import Match
from app.models.media import Media

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user profile"""
    return jsonify({
        'user': current_user.to_dict(),
        'preferences': current_user.preferences.to_dict() if current_user.preferences else None
    }), 200

@user_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update user profile"""
    data = request.get_json()
    
    # Update basic profile information
    if 'first_name' in data:
        current_user.first_name = data['first_name']
    if 'last_name' in data:
        current_user.last_name = data['last_name']
    if 'bio' in data:
        current_user.bio = data['bio']
    if 'gender' in data:
        current_user.gender = data['gender']
    if 'location' in data:
        current_user.location = data['location']
    if 'latitude' in data and 'longitude' in data:
        current_user.latitude = data['latitude']
        current_user.longitude = data['longitude']
    if 'phone_number' in data:
        current_user.phone_number = data['phone_number']
    if 'birthdate' in data:
        current_user.birthdate = datetime.strptime(data['birthdate'], '%Y-%m-%d')
    
    # Update preferences if provided
    if 'preferences' in data:
        preferences = data['preferences']
        if not current_user.preferences:
            current_user.preferences = UserPreference(user_id=current_user.id)
        
        pref = current_user.preferences
        if 'interested_in' in preferences:
            pref.interested_in = preferences['interested_in']
        if 'min_age' in preferences:
            pref.min_age = preferences['min_age']
        if 'max_age' in preferences:
            pref.max_age = preferences['max_age']
        if 'max_distance' in preferences:
            pref.max_distance = preferences['max_distance']
        if 'show_online_status' in preferences:
            pref.show_online_status = preferences['show_online_status']
        if 'show_location' in preferences:
            pref.show_location = preferences['show_location']
        if 'show_age' in preferences:
            pref.show_age = preferences['show_age']
        if 'show_last_active' in preferences:
            pref.show_last_active = preferences['show_last_active']
    
    # Save changes
    current_user.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Profile updated successfully',
        'user': current_user.to_dict(),
        'preferences': current_user.preferences.to_dict() if current_user.preferences else None
    }), 200

@user_bp.route('/profile/picture', methods=['POST'])
@login_required
def update_profile_picture():
    """Update user profile picture"""
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"{current_user.id}_{timestamp}_{filename}"
        
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profile_pictures', filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file.save(file_path)
        
        # Update user profile picture
        current_user.profile_picture = f"/static/uploads/profile_pictures/{filename}"
        current_user.updated_at = datetime.utcnow()
        
        # Create a media entry for the profile picture
        media = Media(
            user_id=current_user.id,
            media_type='image',
            file_path=current_user.profile_picture,
            is_profile_picture=True
        )
        
        db.session.add(media)
        db.session.commit()
        
        return jsonify({
            'message': 'Profile picture updated successfully',
            'profile_picture': current_user.profile_picture
        }), 200
    
    return jsonify({'message': 'File type not allowed'}), 400

@user_bp.route('/profile/<int:user_id>', methods=['GET'])
@login_required
def get_user_profile(user_id):
    """Get another user's profile"""
    user = User.query.get_or_404(user_id)
    
    # Check if the user is blocked
    blocked = UserBlocked.query.filter(
        ((UserBlocked.user_id == current_user.id) & (UserBlocked.blocked_id == user_id)) |
        ((UserBlocked.user_id == user_id) & (UserBlocked.blocked_id == current_user.id))
    ).first()
    
    if blocked:
        return jsonify({'message': 'User not available'}), 403
    
    # Check if there's a match between the users
    match = Match.query.filter(
        ((Match.user1_id == current_user.id) & (Match.user2_id == user_id)) |
        ((Match.user1_id == user_id) & (Match.user2_id == current_user.id))
    ).first()
    
    # Get media
    media = Media.query.filter_by(user_id=user_id, is_private=False).order_by(Media.created_at.desc()).limit(10).all()
    
    return jsonify({
        'user': user.to_dict(),
        'is_matched': match is not None,
        'media': [m.to_dict() for m in media]
    }), 200

@user_bp.route('/block/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    """Block a user"""
    if user_id == current_user.id:
        return jsonify({'message': 'Cannot block yourself'}), 400
    
    # Check if user exists
    user = User.query.get_or_404(user_id)
    
    # Check if already blocked
    existing_block = UserBlocked.query.filter_by(
        user_id=current_user.id, 
        blocked_id=user_id
    ).first()
    
    if existing_block:
        return jsonify({'message': 'User already blocked'}), 400
    
    # Create block
    block = UserBlocked(
        user_id=current_user.id,
        blocked_id=user_id
    )
    
    # Remove any matches
    match = Match.query.filter(
        ((Match.user1_id == current_user.id) & (Match.user2_id == user_id)) |
        ((Match.user1_id == user_id) & (Match.user2_id == current_user.id))
    ).first()
    
    if match:
        match.is_active = False
        db.session.add(match)
    
    db.session.add(block)
    db.session.commit()
    
    return jsonify({'message': 'User blocked successfully'}), 200

@user_bp.route('/block/<int:user_id>', methods=['DELETE'])
@login_required
def unblock_user(user_id):
    """Unblock a user"""
    # Check if user is blocked
    block = UserBlocked.query.filter_by(
        user_id=current_user.id, 
        blocked_id=user_id
    ).first_or_404()
    
    db.session.delete(block)
    db.session.commit()
    
    return jsonify({'message': 'User unblocked successfully'}), 200

@user_bp.route('/blocked', methods=['GET'])
@login_required
def get_blocked_users():
    """Get list of blocked users"""
    blocks = UserBlocked.query.filter_by(user_id=current_user.id).all()
    blocked_users = []
    
    for block in blocks:
        user = User.query.get(block.blocked_id)
        if user:
            blocked_users.append({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'profile_picture': user.profile_picture,
                'blocked_at': block.created_at.isoformat()
            })
    
    return jsonify({'blocked_users': blocked_users}), 200

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
