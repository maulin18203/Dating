from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from app import db, socketio
from app.models.user import User, UserBlocked
from app.models.match import Match
from app.models.message import Message, ChatAttachment

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/matches/<int:match_id>/messages', methods=['GET'])
@login_required
def get_messages(match_id):
    """Get messages for a match"""
    match = Match.query.filter_by(id=match_id).first_or_404()
    
    # Check if current user is part of the match
    if match.user1_id != current_user.id and match.user2_id != current_user.id:
        return jsonify({'message': 'Not authorized to view these messages'}), 403
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get messages with pagination
    messages = Message.query.filter_by(match_id=match_id) \
        .order_by(Message.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)
    
    # Mark messages as read if current user is the recipient
    for msg in messages.items:
        if msg.recipient_id == current_user.id and not msg.is_read:
            msg.mark_as_read()
    
    # Get other user info
    other_user_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
    other_user = User.query.get(other_user_id)
    
    return jsonify({
        'messages': [msg.to_dict() for msg in messages.items],
        'total': messages.total,
        'pages': messages.pages,
        'current_page': messages.page,
        'other_user': {
            'id': other_user.id,
            'username': other_user.username,
            'first_name': other_user.first_name,
            'profile_picture': other_user.profile_picture,
            'is_online': other_user.is_online,
            'last_seen': other_user.last_seen.isoformat() if other_user.last_seen else None
        }
    }), 200

@chat_bp.route('/matches/<int:match_id>/messages', methods=['POST'])
@login_required
def send_message(match_id):
    """Send a message in a match"""
    match = Match.query.filter_by(id=match_id).first_or_404()
    
    # Check if current user is part of the match
    if match.user1_id != current_user.id and match.user2_id != current_user.id:
        return jsonify({'message': 'Not authorized to send messages in this match'}), 403
    
    # Check if match is active
    if not match.is_active:
        return jsonify({'message': 'Cannot send messages in an inactive match'}), 400
    
    # Get message content
    data = request.form if request.form else request.get_json()
    
    if not data or not data.get('content'):
        return jsonify({'message': 'Message content is required'}), 400
    
    # Get recipient ID
    recipient_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
    
    # Create message
    message = Message(
        match_id=match_id,
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=data.get('content')
    )
    
    db.session.add(message)
    
    # Handle attachments if any
    if request.files and 'attachment' in request.files:
        file = request.files['attachment']
        
        if file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            filename = f"chat_{match_id}_{timestamp}_{filename}"
            
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chat_attachments', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            file.save(file_path)
            
            # Determine file type
            file_type = get_file_type(filename)
            
            # Create attachment
            attachment = ChatAttachment(
                message=message,
                file_path=f"/static/uploads/chat_attachments/{filename}",
                file_type=file_type,
                file_name=file.filename
            )
            
            db.session.add(attachment)
    
    # Update match last activity
    match.last_activity = datetime.utcnow()
    
    db.session.commit()
    
    # Emit socket event with the new message
    socketio.emit('new_message', {
        'message': message.to_dict()
    }, room=f'user_{recipient_id}')
    
    return jsonify({
        'message': 'Message sent successfully',
        'message_data': message.to_dict()
    }), 201

@chat_bp.route('/messages/<int:message_id>/read', methods=['POST'])
@login_required
def mark_message_read(message_id):
    """Mark a message as read"""
    message = Message.query.filter_by(id=message_id).first_or_404()
    
    # Check if current user is the recipient
    if message.recipient_id != current_user.id:
        return jsonify({'message': 'Not authorized to mark this message as read'}), 403
    
    # Mark as read
    message.mark_as_read()
    
    # Emit socket event to notify the sender
    socketio.emit('message_read', {
        'message_id': message.id,
        'match_id': message.match_id,
        'read_at': message.read_at.isoformat()
    }, room=f'user_{message.sender_id}')
    
    return jsonify({'message': 'Message marked as read'}), 200

@chat_bp.route('/matches/<int:match_id>/typing', methods=['POST'])
@login_required
def typing_indicator(match_id):
    """Send typing indicator to match"""
    match = Match.query.filter_by(id=match_id).first_or_404()
    
    # Check if current user is part of the match
    if match.user1_id != current_user.id and match.user2_id != current_user.id:
        return jsonify({'message': 'Not authorized to send typing indicators in this match'}), 403
    
    # Get recipient ID
    recipient_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
    
    # Emit socket event
    socketio.emit('typing', {
        'match_id': match_id,
        'user_id': current_user.id
    }, room=f'user_{recipient_id}')
    
    return jsonify({'message': 'Typing indicator sent'}), 200

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_file_type(filename):
    """Determine file type based on extension"""
    ext = filename.rsplit('.', 1)[1].lower()
    
    if ext in ['jpg', 'jpeg', 'png', 'gif']:
        return 'image'
    elif ext in ['mp4', 'mov', 'avi']:
        return 'video'
    elif ext in ['mp3', 'wav', 'ogg']:
        return 'audio'
    else:
        return 'document'
