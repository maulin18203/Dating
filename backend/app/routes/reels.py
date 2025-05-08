from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from app import db, socketio
from app.models.user import User, UserBlocked
from app.models.media import Media, Comment, Like, Report

reels_bp = Blueprint('reels', __name__)

@reels_bp.route('/', methods=['GET'])
@login_required
def get_reels():
    """Get reels feed"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get blocked users
    blocked_ids = [block.blocked_id for block in UserBlocked.query.filter_by(user_id=current_user.id).all()]
    
    # Also exclude users who blocked the current user
    blocked_by_ids = [block.user_id for block in UserBlocked.query.filter_by(blocked_id=current_user.id).all()]
    
    # Combine all IDs to exclude
    exclude_ids = blocked_ids + blocked_by_ids
    
    # Query for reels
    reels_query = Media.query.filter(
        (Media.media_type == 'reel') &
        (Media.is_private == False)
    ).order_by(Media.created_at.desc())
    
    if exclude_ids:
        reels_query = reels_query.filter(~Media.user_id.in_(exclude_ids))
    
    # Apply filters if provided
    if 'user_id' in request.args:
        reels_query = reels_query.filter_by(user_id=request.args.get('user_id', type=int))
    
    if 'hashtag' in request.args:
        hashtag = request.args.get('hashtag')
        reels_query = reels_query.filter(Media.hashtags.like(f'%{hashtag}%'))
    
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

@reels_bp.route('/<int:reel_id>', methods=['GET'])
@login_required
def get_reel(reel_id):
    """Get a specific reel"""
    reel = Media.query.filter_by(id=reel_id, media_type='reel').first_or_404()
    
    # Check if the user is blocked
    blocked = UserBlocked.query.filter(
        ((UserBlocked.user_id == current_user.id) & (UserBlocked.blocked_id == reel.user_id)) |
        ((UserBlocked.user_id == reel.user_id) & (UserBlocked.blocked_id == current_user.id))
    ).first()
    
    if blocked:
        return jsonify({'message': 'Reel not available'}), 403
    
    # If reel is private, check if current user is the owner
    if reel.is_private and reel.user_id != current_user.id:
        return jsonify({'message': 'Reel not available'}), 403
    
    # Increment view count
    reel.increment_view()
    
    # Check if the current user liked this reel
    liked = Like.query.filter_by(
        user_id=current_user.id,
        media_id=reel.id
    ).first() is not None
    
    # Get the reel data
    reel_data = reel.to_dict()
    reel_data['liked_by_me'] = liked
    
    # Get comments
    comments = Comment.query.filter_by(media_id=reel.id, parent_id=None) \
        .order_by(Comment.created_at.desc()) \
        .limit(20).all()
    
    return jsonify({
        'reel': reel_data,
        'comments': [comment.to_dict() for comment in comments]
    }), 200

@reels_bp.route('/', methods=['POST'])
@login_required
def create_reel():
    """Create a new reel"""
    if 'video' not in request.files:
        return jsonify({'message': 'No video file provided'}), 400
    
    video = request.files['video']
    
    if video.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if video and allowed_file(video.filename, ['mp4', 'mov', 'avi']):
        # Save the video file
        video_filename = secure_filename(video.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        video_filename = f"reel_{current_user.id}_{timestamp}_{video_filename}"
        
        video_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reels', video_filename)
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        
        video.save(video_path)
        
        # Get form data
        data = request.form
        
        # Handle thumbnail if provided
        thumbnail_path = None
        if 'thumbnail' in request.files:
            thumbnail = request.files['thumbnail']
            if thumbnail.filename != '' and allowed_file(thumbnail.filename, ['jpg', 'jpeg', 'png']):
                thumbnail_filename = secure_filename(thumbnail.filename)
                thumbnail_filename = f"thumb_{current_user.id}_{timestamp}_{thumbnail_filename}"
                
                thumbnail_path_full = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reels', 'thumbnails', thumbnail_filename)
                os.makedirs(os.path.dirname(thumbnail_path_full), exist_ok=True)
                
                thumbnail.save(thumbnail_path_full)
                thumbnail_path = f"/static/uploads/reels/thumbnails/{thumbnail_filename}"
        
        # Create the reel
        reel = Media(
            user_id=current_user.id,
            media_type='reel',
            file_path=f"/static/uploads/reels/{video_filename}",
            thumbnail_path=thumbnail_path,
            caption=data.get('caption', ''),
            duration=data.get('duration', 0, type=int),
            music=data.get('music', ''),
            filter_used=data.get('filter', ''),
            hashtags=data.get('hashtags', ''),
            is_private=data.get('is_private', 'false').lower() == 'true'
        )
        
        db.session.add(reel)
        db.session.commit()
        
        return jsonify({
            'message': 'Reel created successfully',
            'reel': reel.to_dict()
        }), 201
    
    return jsonify({'message': 'File type not allowed'}), 400

@reels_bp.route('/<int:reel_id>', methods=['DELETE'])
@login_required
def delete_reel(reel_id):
    """Delete a reel"""
    reel = Media.query.filter_by(id=reel_id, media_type='reel').first_or_404()
    
    # Check if current user is the owner
    if reel.user_id != current_user.id:
        return jsonify({'message': 'Not authorized to delete this reel'}), 403
    
    # Delete the reel
    db.session.delete(reel)
    db.session.commit()
    
    return jsonify({'message': 'Reel deleted successfully'}), 200

@reels_bp.route('/<int:reel_id>/like', methods=['POST'])
@login_required
def like_reel(reel_id):
    """Like a reel"""
    reel = Media.query.filter_by(id=reel_id, media_type='reel').first_or_404()
    
    # Check if the user is blocked
    blocked = UserBlocked.query.filter(
        ((UserBlocked.user_id == current_user.id) & (UserBlocked.blocked_id == reel.user_id)) |
        ((UserBlocked.user_id == reel.user_id) & (UserBlocked.blocked_id == current_user.id))
    ).first()
    
    if blocked:
        return jsonify({'message': 'Cannot like this reel'}), 403
    
    # Check if already liked
    existing_like = Like.query.filter_by(user_id=current_user.id, media_id=reel_id).first()
    
    if existing_like:
        return jsonify({'message': 'Reel already liked'}), 400
    
    # Create like
    like = Like(
        user_id=current_user.id,
        media_id=reel_id
    )
    
    db.session.add(like)
    db.session.commit()
    
    # Notify the reel owner
    if reel.user_id != current_user.id:
        socketio.emit('reel_like', {
            'reel_id': reel.id,
            'user': current_user.to_dict()
        }, room=f'user_{reel.user_id}')
    
    return jsonify({'message': 'Reel liked successfully'}), 200

@reels_bp.route('/<int:reel_id>/like', methods=['DELETE'])
@login_required
def unlike_reel(reel_id):
    """Unlike a reel"""
    like = Like.query.filter_by(user_id=current_user.id, media_id=reel_id).first_or_404()
    
    db.session.delete(like)
    db.session.commit()
    
    return jsonify({'message': 'Reel unliked successfully'}), 200

@reels_bp.route('/<int:reel_id>/comments', methods=['GET'])
@login_required
def get_comments(reel_id):
    """Get comments for a reel"""
    reel = Media.query.filter_by(id=reel_id, media_type='reel').first_or_404()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Query for comments
    comments_query = Comment.query.filter_by(media_id=reel_id, parent_id=None) \
        .order_by(Comment.created_at.desc())
    
    # Get comments with pagination
    comments = comments_query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'comments': [comment.to_dict() for comment in comments.items],
        'total': comments.total,
        'pages': comments.pages,
        'current_page': comments.page
    }), 200

@reels_bp.route('/<int:reel_id>/comments', methods=['POST'])
@login_required
def add_comment(reel_id):
    """Add a comment to a reel"""
    reel = Media.query.filter_by(id=reel_id, media_type='reel').first_or_404()
    
    # Check if the user is blocked
    blocked = UserBlocked.query.filter(
        ((UserBlocked.user_id == current_user.id) & (UserBlocked.blocked_id == reel.user_id)) |
        ((UserBlocked.user_id == reel.user_id) & (UserBlocked.blocked_id == current_user.id))
    ).first()
    
    if blocked:
        return jsonify({'message': 'Cannot comment on this reel'}), 403
    
    data = request.get_json()
    
    if not data or not data.get('content'):
        return jsonify({'message': 'Comment content is required'}), 400
    
    # Create comment
    comment = Comment(
        user_id=current_user.id,
        media_id=reel_id,
        content=data.get('content'),
        parent_id=data.get('parent_id')  # For replies to comments
    )
    
    db.session.add(comment)
    db.session.commit()
    
    # Notify the reel owner or parent comment owner
    if comment.parent_id:
        parent_comment = Comment.query.get(comment.parent_id)
        if parent_comment and parent_comment.user_id != current_user.id:
            socketio.emit('comment_reply', {
                'comment': comment.to_dict(),
                'reel_id': reel.id
            }, room=f'user_{parent_comment.user_id}')
    elif reel.user_id != current_user.id:
        socketio.emit('reel_comment', {
            'comment': comment.to_dict(),
            'reel_id': reel.id
        }, room=f'user_{reel.user_id}')
    
    return jsonify({
        'message': 'Comment added successfully',
        'comment': comment.to_dict()
    }), 201

@reels_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    comment = Comment.query.filter_by(id=comment_id).first_or_404()
    
    # Check if current user is the owner of the comment or the reel
    reel = Media.query.get(comment.media_id)
    
    if comment.user_id != current_user.id and reel.user_id != current_user.id:
        return jsonify({'message': 'Not authorized to delete this comment'}), 403
    
    # Delete the comment
    db.session.delete(comment)
    db.session.commit()
    
    return jsonify({'message': 'Comment deleted successfully'}), 200

@reels_bp.route('/<int:reel_id>/report', methods=['POST'])
@login_required
def report_reel(reel_id):
    """Report a reel for inappropriate content"""
    reel = Media.query.filter_by(id=reel_id, media_type='reel').first_or_404()
    
    data = request.get_json()
    
    if not data or not data.get('reason'):
        return jsonify({'message': 'Report reason is required'}), 400
    
    # Create report
    report = Report(
        reporter_id=current_user.id,
        reported_user_id=reel.user_id,
        media_id=reel_id,
        reason=data.get('reason'),
        description=data.get('description', '')
    )
    
    db.session.add(report)
    db.session.commit()
    
    return jsonify({'message': 'Reel reported successfully'}), 201

def allowed_file(filename, allowed_extensions=None):
    """Check if file extension is allowed"""
    if allowed_extensions is None:
        allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
