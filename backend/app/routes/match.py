from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, not_
from datetime import datetime
import random
from math import radians, cos, sin, asin, sqrt
from app import db, socketio
from app.models.user import User, UserLike, UserBlocked
from app.models.match import Match

match_bp = Blueprint('match', __name__)

@match_bp.route('/discover', methods=['GET'])
@login_required
def discover_users():
    """Get potential matches based on preferences"""
    # Get current user preferences
    preferences = current_user.preferences
    
    if not preferences:
        return jsonify({'message': 'Please set your preferences first'}), 400
    
    # Get users already liked or blocked
    liked_ids = [like.liked_id for like in current_user.likes_given.all()]
    blocked_ids = [block.blocked_id for block in UserBlocked.query.filter_by(user_id=current_user.id).all()]
    
    # Also exclude users who blocked the current user
    blocked_by_ids = [block.user_id for block in UserBlocked.query.filter_by(blocked_id=current_user.id).all()]
    
    # Combine all IDs to exclude
    exclude_ids = liked_ids + blocked_ids + blocked_by_ids + [current_user.id]
    
    # Build the query based on preferences
    query = User.query.filter(User.id.notin_(exclude_ids))
    
    # Filter by gender preference
    if preferences.interested_in and preferences.interested_in != 'both':
        query = query.filter(User.gender == preferences.interested_in)
    
    # Filter by age range
    if preferences.min_age:
        min_date = datetime.now().replace(year=datetime.now().year - preferences.min_age)
        query = query.filter(User.birthdate <= min_date)
    if preferences.max_age:
        max_date = datetime.now().replace(year=datetime.now().year - preferences.max_age)
        query = query.filter(User.birthdate >= max_date)
    
    # Get all potential matches
    potential_matches = query.all()
    
    # Filter by distance if location is available
    if current_user.latitude and current_user.longitude and preferences.max_distance:
        filtered_matches = []
        for user in potential_matches:
            if user.latitude and user.longitude:
                dist = calculate_distance(
                    current_user.latitude, current_user.longitude,
                    user.latitude, user.longitude
                )
                if dist <= preferences.max_distance:
                    # Add distance to user object
                    user_dict = user.to_dict()
                    user_dict['distance'] = round(dist, 1)
                    filtered_matches.append(user_dict)
        
        # Sort by distance
        filtered_matches.sort(key=lambda x: x['distance'])
    else:
        # If no location, just convert to dict
        filtered_matches = [user.to_dict() for user in potential_matches]
    
    # Limit to 20 results
    return jsonify({'users': filtered_matches[:20]}), 200

@match_bp.route('/like/<int:user_id>', methods=['POST'])
@login_required
def like_user(user_id):
    """Like a user (swipe right)"""
    if user_id == current_user.id:
        return jsonify({'message': 'Cannot like yourself'}), 400
    
    # Check if user exists
    user = User.query.get_or_404(user_id)
    
    # Check if user is blocked
    block = UserBlocked.query.filter(
        ((UserBlocked.user_id == current_user.id) & (UserBlocked.blocked_id == user_id)) |
        ((UserBlocked.user_id == user_id) & (UserBlocked.blocked_id == current_user.id))
    ).first()
    
    if block:
        return jsonify({'message': 'Cannot like this user'}), 403
    
    # Check if already liked
    existing_like = UserLike.query.filter_by(
        liker_id=current_user.id, 
        liked_id=user_id
    ).first()
    
    if existing_like:
        return jsonify({'message': 'User already liked'}), 400
    
    # Get super like status
    is_super_like = request.json.get('is_super_like', False) if request.json else False
    
    # Create like
    like = UserLike(
        liker_id=current_user.id,
        liked_id=user_id,
        is_super_like=is_super_like
    )
    
    db.session.add(like)
    
    # Check if the other user has already liked current user (mutual like)
    other_like = UserLike.query.filter_by(
        liker_id=user_id, 
        liked_id=current_user.id
    ).first()
    
    is_match = False
    match_id = None
    
    if other_like:
        # Create a match
        match = Match(
            user1_id=min(current_user.id, user_id),
            user2_id=max(current_user.id, user_id)
        )
        
        db.session.add(match)
        db.session.commit()
        
        is_match = True
        match_id = match.id
        
        # Emit socket event for the match
        socketio.emit('new_match', {
            'match_id': match.id,
            'user': current_user.to_dict()
        }, room=f'user_{user_id}')
    else:
        db.session.commit()
        
        # If super like, notify the other user
        if is_super_like:
            socketio.emit('super_like', {
                'from_user': current_user.to_dict()
            }, room=f'user_{user_id}')
    
    return jsonify({
        'message': 'User liked successfully',
        'is_match': is_match,
        'match_id': match_id
    }), 200

@match_bp.route('/dislike/<int:user_id>', methods=['POST'])
@login_required
def dislike_user(user_id):
    """Dislike a user (swipe left)"""
    if user_id == current_user.id:
        return jsonify({'message': 'Cannot dislike yourself'}), 400
    
    # Check if user exists
    user = User.query.get_or_404(user_id)
    
    # No need to store dislikes in the database, just return success
    return jsonify({'message': 'User disliked'}), 200

@match_bp.route('/matches', methods=['GET'])
@login_required
def get_matches():
    """Get all user matches"""
    matches = Match.query.filter(
        ((Match.user1_id == current_user.id) | (Match.user2_id == current_user.id)) &
        (Match.is_active == True)
    ).order_by(Match.last_activity.desc()).all()
    
    return jsonify({
        'matches': [match.to_dict(current_user.id) for match in matches]
    }), 200

@match_bp.route('/matches/<int:match_id>', methods=['GET'])
@login_required
def get_match(match_id):
    """Get a specific match"""
    match = Match.query.filter_by(id=match_id).first_or_404()
    
    # Check if current user is part of the match
    if match.user1_id != current_user.id and match.user2_id != current_user.id:
        return jsonify({'message': 'Not authorized to view this match'}), 403
    
    return jsonify({'match': match.to_dict(current_user.id)}), 200

@match_bp.route('/matches/<int:match_id>/unmatch', methods=['POST'])
@login_required
def unmatch(match_id):
    """Unmatch from a user"""
    match = Match.query.filter_by(id=match_id).first_or_404()
    
    # Check if current user is part of the match
    if match.user1_id != current_user.id and match.user2_id != current_user.id:
        return jsonify({'message': 'Not authorized to modify this match'}), 403
    
    # Deactivate match
    match.is_active = False
    db.session.commit()
    
    # Get other user ID
    other_user_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
    
    # Notify other user
    socketio.emit('unmatch', {
        'match_id': match.id
    }, room=f'user_{other_user_id}')
    
    return jsonify({'message': 'Unmatched successfully'}), 200

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers using the haversine formula"""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    
    return c * r
