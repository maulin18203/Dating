from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserLike, UserBlocked
from app.models.match import Match
from app.models.message import Message
from app.models.media import Media, Comment, Like, Report
from app.models.subscription import Subscription, Transaction
from datetime import datetime

api_bp = Blueprint('api', __name__)

# API middleware for CORS and other headers
@api_bp.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

# User endpoints
@api_bp.route('/users/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current authenticated user"""
    return jsonify({
        'user': current_user.to_dict(),
        'preferences': current_user.preferences.to_dict() if current_user.preferences else None
    }), 200

@api_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """Get user by ID"""
    user = User.query.get_or_404(user_id)
    
    # Check if blocked
    is_blocked = UserBlocked.query.filter(
        ((UserBlocked.user_id == current_user.id) & (UserBlocked.blocked_id == user_id)) |
        ((UserBlocked.user_id == user_id) & (UserBlocked.blocked_id == current_user.id))
    ).first() is not None
    
    # Check if matched
    is_matched = Match.query.filter(
        ((Match.user1_id == current_user.id) & (Match.user2_id == user_id)) |
        ((Match.user1_id == user_id) & (Match.user2_id == current_user.id))
    ).first() is not None
    
    # Check if liked
    has_liked = UserLike.query.filter_by(
        liker_id=current_user.id,
        liked_id=user_id
    ).first() is not None
    
    # Get media
    media = []
    if not is_blocked:
        media_query = Media.query.filter_by(user_id=user_id)
        
        # If not matched, only show public media
        if not is_matched and user_id != current_user.id:
            media_query = media_query.filter_by(is_private=False)
        
        media = media_query.order_by(Media.created_at.desc()).limit(10).all()
    
    return jsonify({
        'user': user.to_dict(),
        'is_blocked': is_blocked,
        'is_matched': is_matched,
        'has_liked': has_liked,
        'media': [m.to_dict() for m in media]
    }), 200

# Match endpoints
@api_bp.route('/matches', methods=['GET'])
@login_required
def get_matches():
    """Get all matches for current user"""
    matches = Match.query.filter(
        ((Match.user1_id == current_user.id) | (Match.user2_id == current_user.id)) &
        (Match.is_active == True)
    ).order_by(Match.last_activity.desc()).all()
    
    return jsonify({
        'matches': [match.to_dict(current_user.id) for match in matches]
    }), 200

# Message endpoints
@api_bp.route('/messages/unread', methods=['GET'])
@login_required
def get_unread_messages():
    """Get unread message count for current user"""
    unread_count = Message.query.filter_by(
        recipient_id=current_user.id,
        is_read=False
    ).count()
    
    return jsonify({
        'unread_count': unread_count
    }), 200

# Reels endpoints
@api_bp.route('/reels/trending', methods=['GET'])
@login_required
def get_trending_reels():
    """Get trending reels based on view count and likes"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get blocked users
    blocked_ids = [block.blocked_id for block in UserBlocked.query.filter_by(user_id=current_user.id).all()]
    blocked_by_ids = [block.user_id for block in UserBlocked.query.filter_by(blocked_id=current_user.id).all()]
    exclude_ids = blocked_ids + blocked_by_ids
    
    # Query for trending reels
    reels_query = Media.query.filter(
        (Media.media_type == 'reel') &
        (Media.is_private == False)
    )
    
    if exclude_ids:
        reels_query = reels_query.filter(~Media.user_id.in_(exclude_ids))
    
    # Order by view count and creation date
    reels_query = reels_query.order_by(Media.view_count.desc(), Media.created_at.desc())
    
    # Get reels with pagination
    reels = reels_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Check if the current user liked each reel
    reels_data = []
    for reel in reels.items:
        reel_dict = reel.to_dict()
        reel_dict['liked_by_me'] = Like.query.filter_by(
            user_id=current_user.id,
            media_id=reel.id
        ).first() is not None
        reels_data.append(reel_dict)
    
    return jsonify({
        'reels': reels_data,
        'total': reels.total,
        'pages': reels.pages,
        'current_page': reels.page
    }), 200

# Subscription endpoints
@api_bp.route('/subscriptions/plans', methods=['GET'])
@login_required
def get_subscription_plans():
    """Get available subscription plans"""
    plans = [
        {
            'id': 'basic',
            'name': 'Basic',
            'description': 'See who liked you and unlimited swipes',
            'price': 9.99,
            'currency': 'USD',
            'duration_days': 30,
            'features': [
                'See who liked you',
                'Unlimited swipes',
                'Rewind to previous profiles',
                'Hide advertisements'
            ]
        },
        {
            'id': 'premium',
            'name': 'Premium',
            'description': 'All Basic features plus profile boost and Super Likes',
            'price': 19.99,
            'currency': 'USD',
            'duration_days': 30,
            'features': [
                'All Basic features',
                'Monthly profile boost',
                '5 Super Likes per day',
                'See who viewed your profile',
                'Priority in discovery'
            ]
        },
        {
            'id': 'gold',
            'name': 'Gold',
            'description': 'Ultimate experience with all Premium features plus Reel promotion',
            'price': 29.99,
            'currency': 'USD',
            'duration_days': 30,
            'features': [
                'All Premium features',
                'Weekly profile boost',
                '10 Super Likes per day',
                'Reel promotion',
                'Premium badge on profile',
                'Priority customer support'
            ]
        }
    ]
    
    return jsonify({'plans': plans}), 200

@api_bp.route('/subscriptions/current', methods=['GET'])
@login_required
def get_current_subscription():
    """Get current user subscription"""
    subscription = Subscription.query.filter_by(user_id=current_user.id) \
        .order_by(Subscription.created_at.desc()).first()
    
    if not subscription:
        return jsonify({'subscription': None}), 200
    
    return jsonify({'subscription': subscription.to_dict()}), 200

@api_bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """Get user's transaction history"""
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Query for transactions
    transactions = Transaction.query.filter_by(user_id=current_user.id) \
        .order_by(Transaction.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'transactions': [transaction.to_dict() for transaction in transactions.items],
        'total': transactions.total,
        'pages': transactions.pages,
        'current_page': transactions.page
    }), 200
