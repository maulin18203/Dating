from datetime import datetime
from app import db

class Match(db.Model):
    """Matches between users (when both users like each other)"""
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Define unique constraint to prevent duplicate matches
    __table_args__ = (
        db.UniqueConstraint('user1_id', 'user2_id', name='_user_match_uc'),
    )
    
    # Define relationships with both users
    user1 = db.relationship('User', foreign_keys=[user1_id], backref=db.backref('matches_as_user1', lazy='dynamic'))
    user2 = db.relationship('User', foreign_keys=[user2_id], backref=db.backref('matches_as_user2', lazy='dynamic'))
    
    # Messages in this match
    messages = db.relationship('Message', backref='match', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def other_user(self, user_id):
        """Get the other user in a match"""
        if self.user1_id == user_id:
            return self.user2
        return self.user1
    
    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self, current_user_id):
        """Convert match to dictionary for API responses"""
        other_user = self.user2 if self.user1_id == current_user_id else self.user1
        
        # Get the last message in this match if any
        last_message = self.messages.order_by(Message.created_at.desc()).first()
        
        return {
            'id': self.id,
            'matched_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'is_active': self.is_active,
            'other_user': {
                'id': other_user.id,
                'username': other_user.username,
                'first_name': other_user.first_name,
                'profile_picture': other_user.profile_picture,
                'is_online': other_user.is_online,
                'last_seen': other_user.last_seen.isoformat() if other_user.last_seen else None
            },
            'last_message': {
                'content': last_message.content if last_message else None,
                'created_at': last_message.created_at.isoformat() if last_message else None,
                'is_read': last_message.is_read if last_message else True,
                'sender_id': last_message.sender_id if last_message else None
            } if last_message else None
        }
    
    def __repr__(self):
        return f'<Match {self.id}: {self.user1_id} and {self.user2_id}>'

# Import here to avoid circular imports
from app.models.message import Message
