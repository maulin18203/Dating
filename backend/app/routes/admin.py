from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from app import db
from app.models.user import User, Verification
from app.models.media import Media, Report
from app.models.match import Match
from app.models.message import Message
from app.models.subscription import Subscription, Transaction

admin_bp = Blueprint('admin', __name__)

# Admin middleware to check if user has admin role
@admin_bp.before_request
def check_admin():
    if not current_user.is_authenticated or not current_user.is_admin():
        return jsonify({'message': 'Admin access required'}), 403

@admin_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Get admin dashboard statistics"""
    # Get date range from query parameters or default to last 30 days
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # User statistics
    total_users = User.query.count()
    new_users = User.query.filter(User.created_at >= start_date).count()
    active_users = User.query.filter(User.last_seen >= (datetime.utcnow() - timedelta(days=7))).count()
    verified_users = User.query.filter_by(is_verified=True).count()
    premium_users = User.query.filter_by(is_premium=True).count()
    
    # Match statistics
    total_matches = Match.query.count()
    new_matches = Match.query.filter(Match.created_at >= start_date).count()
    active_conversations = Match.query.filter(Match.last_activity >= start_date).count()
    
    # Message statistics
    total_messages = Message.query.count()
    new_messages = Message.query.filter(Message.created_at >= start_date).count()
    
    # Media statistics
    total_reels = Media.query.filter_by(media_type='reel').count()
    new_reels = Media.query.filter(Media.media_type == 'reel', Media.created_at >= start_date).count()
    
    # Report statistics
    pending_reports = Report.query.filter_by(status='pending').count()
    
    # Verification statistics
    pending_verifications = Verification.query.filter_by(is_verified=False).filter(Verification.rejected_reason == None).count()
    
    # Revenue statistics
    revenue = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.status == 'completed',
        Transaction.created_at >= start_date
    ).scalar() or 0
    
    return jsonify({
        'user_stats': {
            'total_users': total_users,
            'new_users': new_users,
            'active_users': active_users,
            'verified_users': verified_users,
            'premium_users': premium_users
        },
        'interaction_stats': {
            'total_matches': total_matches,
            'new_matches': new_matches,
            'active_conversations': active_conversations,
            'total_messages': total_messages,
            'new_messages': new_messages
        },
        'content_stats': {
            'total_reels': total_reels,
            'new_reels': new_reels
        },
        'moderation_stats': {
            'pending_reports': pending_reports,
            'pending_verifications': pending_verifications
        },
        'revenue_stats': {
            'revenue': revenue
        }
    }), 200

@admin_bp.route('/users', methods=['GET'])
@login_required
def get_users():
    """Get list of users with filtering options"""
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query with filters
    query = User.query
    
    # Apply filters if provided
    if 'search' in request.args:
        search = f"%{request.args.get('search')}%"
        query = query.filter(
            (User.username.like(search)) |
            (User.email.like(search)) |
            (User.first_name.like(search)) |
            (User.last_name.like(search))
        )
    
    if 'is_verified' in request.args:
        is_verified = request.args.get('is_verified').lower() == 'true'
        query = query.filter_by(is_verified=is_verified)
    
    if 'is_premium' in request.args:
        is_premium = request.args.get('is_premium').lower() == 'true'
        query = query.filter_by(is_premium=is_premium)
    
    if 'created_after' in request.args:
        created_after = datetime.fromisoformat(request.args.get('created_after'))
        query = query.filter(User.created_at >= created_after)
    
    if 'created_before' in request.args:
        created_before = datetime.fromisoformat(request.args.get('created_before'))
        query = query.filter(User.created_at <= created_before)
    
    # Order by
    sort_by = request.args.get('sort_by', 'created_at')
    sort_direction = request.args.get('sort_direction', 'desc')
    
    if sort_direction.lower() == 'desc':
        query = query.order_by(desc(getattr(User, sort_by)))
    else:
        query = query.order_by(getattr(User, sort_by))
    
    # Get users with pagination
    users = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'users': [user.to_dict() for user in users.items],
        'total': users.total,
        'pages': users.pages,
        'current_page': users.page
    }), 200

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """Get detailed user information"""
    user = User.query.get_or_404(user_id)
    
    # Get additional statistics
    matches_count = Match.query.filter(
        (Match.user1_id == user_id) | (Match.user2_id == user_id)
    ).count()
    
    media_count = Media.query.filter_by(user_id=user_id).count()
    
    reels_count = Media.query.filter_by(user_id=user_id, media_type='reel').count()
    
    reports_received = Report.query.filter_by(reported_user_id=user_id).count()
    
    reports_made = Report.query.filter_by(reporter_id=user_id).count()
    
    # Get subscription information
    subscription = Subscription.query.filter_by(user_id=user_id).order_by(Subscription.created_at.desc()).first()
    
    # Get transactions
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).limit(10).all()
    
    # Get media
    media = Media.query.filter_by(user_id=user_id).order_by(Media.created_at.desc()).limit(10).all()
    
    return jsonify({
        'user': user.to_dict(),
        'preferences': user.preferences.to_dict() if user.preferences else None,
        'statistics': {
            'matches_count': matches_count,
            'media_count': media_count,
            'reels_count': reels_count,
            'reports_received': reports_received,
            'reports_made': reports_made
        },
        'subscription': subscription.to_dict() if subscription else None,
        'transactions': [transaction.to_dict() for transaction in transactions],
        'media': [item.to_dict() for item in media]
    }), 200

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Update user information or status"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    # Update user fields
    if 'active' in data:
        user.active = data['active']
    
    if 'is_verified' in data:
        user.is_verified = data['is_verified']
    
    if 'is_premium' in data:
        user.is_premium = data['is_premium']
        if data['is_premium']:
            if 'premium_until' in data:
                user.premium_until = datetime.fromisoformat(data['premium_until'])
            else:
                user.premium_until = datetime.utcnow() + timedelta(days=30)
    
    # Add to admin role if specified
    if 'is_admin' in data:
        from app.models.user import Role
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            if data['is_admin'] and admin_role not in user.roles:
                user.roles.append(admin_role)
            elif not data['is_admin'] and admin_role in user.roles:
                user.roles.remove(admin_role)
    
    db.session.commit()
    
    return jsonify({
        'message': 'User updated successfully',
        'user': user.to_dict()
    }), 200

@admin_bp.route('/verifications', methods=['GET'])
@login_required
def get_verifications():
    """Get verification requests"""
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query with filters
    query = Verification.query
    
    # Filter by status
    status = request.args.get('status', 'pending')
    if status == 'pending':
        query = query.filter_by(is_verified=False).filter(Verification.rejected_reason == None)
    elif status == 'verified':
        query = query.filter_by(is_verified=True)
    elif status == 'rejected':
        query = query.filter_by(is_verified=False).filter(Verification.rejected_reason != None)
    
    # Order by creation date
    query = query.order_by(Verification.created_at.desc())
    
    # Get verifications with pagination
    verifications = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Format response
    result = []
    for verification in verifications.items:
        user = User.query.get(verification.user_id)
        result.append({
            'id': verification.id,
            'user_id': verification.user_id,
            'username': user.username if user else None,
            'id_type': verification.id_type,
            'id_number': verification.id_number,
            'id_image': verification.id_image,
            'selfie_image': verification.selfie_image,
            'is_verified': verification.is_verified,
            'verification_date': verification.verification_date.isoformat() if verification.verification_date else None,
            'rejected_reason': verification.rejected_reason,
            'created_at': verification.created_at.isoformat()
        })
    
    return jsonify({
        'verifications': result,
        'total': verifications.total,
        'pages': verifications.pages,
        'current_page': verifications.page
    }), 200

@admin_bp.route('/verifications/<int:verification_id>', methods=['PUT'])
@login_required
def update_verification(verification_id):
    """Approve or reject a verification request"""
    verification = Verification.query.get_or_404(verification_id)
    user = User.query.get(verification.user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    data = request.get_json()
    
    # Approve or reject
    if 'approve' in data:
        if data['approve']:
            verification.is_verified = True
            verification.verification_date = datetime.utcnow()
            verification.rejected_reason = None
            
            # Update user verified status
            user.is_verified = True
        else:
            verification.is_verified = False
            verification.rejected_reason = data.get('reason', 'Verification rejected by admin')
            
            # Update user verified status
            user.is_verified = False
    
    db.session.commit()
    
    return jsonify({
        'message': 'Verification updated successfully',
        'verification': {
            'id': verification.id,
            'user_id': verification.user_id,
            'is_verified': verification.is_verified,
            'verification_date': verification.verification_date.isoformat() if verification.verification_date else None,
            'rejected_reason': verification.rejected_reason
        }
    }), 200

@admin_bp.route('/reports', methods=['GET'])
@login_required
def get_reports():
    """Get reports with filtering options"""
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query with filters
    query = Report.query
    
    # Filter by status
    status = request.args.get('status', 'pending')
    query = query.filter_by(status=status)
    
    # Order by creation date
    query = query.order_by(Report.created_at.desc())
    
    # Get reports with pagination
    reports = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Format response
    result = []
    for report in reports.items:
        reporter = User.query.get(report.reporter_id)
        reported_user = User.query.get(report.reported_user_id) if report.reported_user_id else None
        
        result.append({
            'id': report.id,
            'reporter': {
                'id': reporter.id,
                'username': reporter.username
            } if reporter else None,
            'reported_user': {
                'id': reported_user.id,
                'username': reported_user.username
            } if reported_user else None,
            'media_id': report.media_id,
            'reason': report.reason,
            'description': report.description,
            'status': report.status,
            'admin_notes': report.admin_notes,
            'created_at': report.created_at.isoformat()
        })
    
    return jsonify({
        'reports': result,
        'total': reports.total,
        'pages': reports.pages,
        'current_page': reports.page
    }), 200

@admin_bp.route('/reports/<int:report_id>', methods=['PUT'])
@login_required
def update_report(report_id):
    """Update report status"""
    report = Report.query.get_or_404(report_id)
    data = request.get_json()
    
    # Update status
    if 'status' in data:
        report.status = data['status']
    
    if 'admin_notes' in data:
        report.admin_notes = data['admin_notes']
    
    report.reviewed_by = current_user.id
    report.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Report updated successfully',
        'report': {
            'id': report.id,
            'status': report.status,
            'admin_notes': report.admin_notes
        }
    }), 200

@admin_bp.route('/content', methods=['GET'])
@login_required
def get_content():
    """Get content (reels, images) with filtering options"""
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query with filters
    query = Media.query
    
    # Apply filters
    if 'media_type' in request.args:
        query = query.filter_by(media_type=request.args.get('media_type'))
    
    if 'user_id' in request.args:
        query = query.filter_by(user_id=request.args.get('user_id', type=int))
    
    if 'is_featured' in request.args:
        is_featured = request.args.get('is_featured').lower() == 'true'
        query = query.filter_by(is_featured=is_featured)
    
    if 'date_after' in request.args:
        date_after = datetime.fromisoformat(request.args.get('date_after'))
        query = query.filter(Media.created_at >= date_after)
    
    # Order by creation date
    query = query.order_by(Media.created_at.desc())
    
    # Get content with pagination
    content = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'content': [item.to_dict() for item in content.items],
        'total': content.total,
        'pages': content.pages,
        'current_page': content.page
    }), 200

@admin_bp.route('/content/<int:media_id>', methods=['PUT'])
@login_required
def update_content(media_id):
    """Update content settings (featured status, etc.)"""
    media = Media.query.get_or_404(media_id)
    data = request.get_json()
    
    if 'is_featured' in data:
        media.is_featured = data['is_featured']
    
    if 'is_private' in data:
        media.is_private = data['is_private']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Content updated successfully',
        'content': media.to_dict()
    }), 200

@admin_bp.route('/content/<int:media_id>', methods=['DELETE'])
@login_required
def delete_content(media_id):
    """Delete content (for moderation purposes)"""
    media = Media.query.get_or_404(media_id)
    
    # Delete the media
    db.session.delete(media)
    db.session.commit()
    
    return jsonify({'message': 'Content deleted successfully'}), 200
