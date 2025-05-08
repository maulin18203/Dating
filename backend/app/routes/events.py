from flask import request, session
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from datetime import datetime
from app import db, socketio
from app.models.user import User
from app.models.match import Match
from app.models.message import Message, ChatAttachment

def register_socket_events(socketio):
    """Register all socket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        if current_user.is_authenticated:
            # Update user status
            current_user.is_online = True
            current_user.last_seen = datetime.utcnow()
            db.session.commit()
            
            # Join user's personal room for direct messages
            join_room(f'user_{current_user.id}')
            
            # Join rooms for all active matches
            matches = Match.query.filter(
                ((Match.user1_id == current_user.id) | (Match.user2_id == current_user.id)) &
                (Match.is_active == True)
            ).all()
            
            for match in matches:
                join_room(f'match_{match.id}')
            
            return True
        return False
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        if current_user.is_authenticated:
            # Update user status
            current_user.is_online = False
            current_user.last_seen = datetime.utcnow()
            db.session.commit()
            
            # Leave user's personal room
            leave_room(f'user_{current_user.id}')
            
            # Leave rooms for all matches
            matches = Match.query.filter(
                ((Match.user1_id == current_user.id) | (Match.user2_id == current_user.id)) &
                (Match.is_active == True)
            ).all()
            
            for match in matches:
                leave_room(f'match_{match.id}')
    
    @socketio.on('join_match')
    def handle_join_match(data):
        """Join a match chat room"""
        match_id = data.get('match_id')
        
        if not match_id:
            return {'error': 'Match ID is required'}, 400
        
        # Check if match exists and user is part of it
        match = Match.query.get(match_id)
        
        if not match:
            return {'error': 'Match not found'}, 404
        
        if match.user1_id != current_user.id and match.user2_id != current_user.id:
            return {'error': 'Not authorized to join this match'}, 403
        
        # Join the match room
        join_room(f'match_{match_id}')
        
        # Get other user
        other_user_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
        other_user = User.query.get(other_user_id)
        
        # Mark all unread messages as read
        unread_messages = Message.query.filter_by(
            match_id=match_id,
            recipient_id=current_user.id,
            is_read=False
        ).all()
        
        for message in unread_messages:
            message.mark_as_read()
        
        # Notify the other user that messages have been read
        if unread_messages:
            emit('messages_read', {
                'match_id': match_id,
                'reader_id': current_user.id
            }, room=f'user_{other_user_id}')
        
        return {
            'status': 'success',
            'match_id': match_id,
            'other_user': {
                'id': other_user.id,
                'username': other_user.username,
                'profile_picture': other_user.profile_picture,
                'is_online': other_user.is_online,
                'last_seen': other_user.last_seen.isoformat() if other_user.last_seen else None
            }
        }
    
    @socketio.on('leave_match')
    def handle_leave_match(data):
        """Leave a match chat room"""
        match_id = data.get('match_id')
        
        if not match_id:
            return {'error': 'Match ID is required'}, 400
        
        # Leave the match room
        leave_room(f'match_{match_id}')
        
        return {'status': 'success', 'match_id': match_id}
    
    @socketio.on('send_message')
    def handle_send_message(data):
        """Send a message in a match"""
        match_id = data.get('match_id')
        content = data.get('content')
        
        if not match_id or not content:
            return {'error': 'Match ID and content are required'}, 400
        
        # Check if match exists and user is part of it
        match = Match.query.get(match_id)
        
        if not match:
            return {'error': 'Match not found'}, 404
        
        if match.user1_id != current_user.id and match.user2_id != current_user.id:
            return {'error': 'Not authorized to send messages in this match'}, 403
        
        if not match.is_active:
            return {'error': 'Cannot send messages in an inactive match'}, 400
        
        # Get recipient ID
        recipient_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
        
        # Create message
        message = Message(
            match_id=match_id,
            sender_id=current_user.id,
            recipient_id=recipient_id,
            content=content
        )
        
        db.session.add(message)
        
        # Update match last activity
        match.last_activity = datetime.utcnow()
        
        db.session.commit()
        
        # Send message to both users
        message_data = message.to_dict()
        emit('new_message', {'message': message_data}, room=f'match_{match_id}')
        
        # Also send to recipient's personal room in case they're not in the match room
        emit('new_message_notification', {
            'message': message_data,
            'match': match.to_dict(recipient_id)
        }, room=f'user_{recipient_id}')
        
        return {'status': 'success', 'message': message_data}
    
    @socketio.on('typing')
    def handle_typing(data):
        """Send typing indicator"""
        match_id = data.get('match_id')
        
        if not match_id:
            return {'error': 'Match ID is required'}, 400
        
        # Check if match exists and user is part of it
        match = Match.query.get(match_id)
        
        if not match:
            return {'error': 'Match not found'}, 404
        
        if match.user1_id != current_user.id and match.user2_id != current_user.id:
            return {'error': 'Not authorized to send typing indicators in this match'}, 403
        
        # Send typing indicator to match room
        emit('typing_indicator', {
            'match_id': match_id,
            'user_id': current_user.id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'match_{match_id}', include_self=False)
        
        return {'status': 'success'}
    
    @socketio.on('read_message')
    def handle_read_message(data):
        """Mark message as read"""
        message_id = data.get('message_id')
        
        if not message_id:
            return {'error': 'Message ID is required'}, 400
        
        # Check if message exists and user is the recipient
        message = Message.query.get(message_id)
        
        if not message:
            return {'error': 'Message not found'}, 404
        
        if message.recipient_id != current_user.id:
            return {'error': 'Not authorized to mark this message as read'}, 403
        
        # Mark as read
        if not message.is_read:
            message.mark_as_read()
            
            # Notify the sender
            emit('message_read', {
                'message_id': message.id,
                'match_id': message.match_id,
                'read_at': message.read_at.isoformat()
            }, room=f'user_{message.sender_id}')
        
        return {'status': 'success'}
    
    @socketio.on('join_reel_room')
    def handle_join_reel_room(data):
        """Join a room for a specific reel"""
        reel_id = data.get('reel_id')
        
        if not reel_id:
            return {'error': 'Reel ID is required'}, 400
        
        # Join the reel room
        join_room(f'reel_{reel_id}')
        
        return {'status': 'success', 'reel_id': reel_id}
    
    @socketio.on('leave_reel_room')
    def handle_leave_reel_room(data):
        """Leave a room for a specific reel"""
        reel_id = data.get('reel_id')
        
        if not reel_id:
            return {'error': 'Reel ID is required'}, 400
        
        # Leave the reel room
        leave_room(f'reel_{reel_id}')
        
        return {'status': 'success', 'reel_id': reel_id}
