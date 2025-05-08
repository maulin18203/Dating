from datetime import datetime
from app import db

class Message(db.Model):
    """Chat messages between users"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # Relationship with chat attachments (images, etc.)
    attachments = db.relationship('ChatAttachment', backref='message', lazy='dynamic', cascade='all, delete-orphan')
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            db.session.commit()
    
    def to_dict(self):
        """Convert message to dictionary for API responses"""
        return {
            'id': self.id,
            'match_id': self.match_id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'attachments': [att.to_dict() for att in self.attachments]
        }
    
    def __repr__(self):
        return f'<Message {self.id}: from {self.sender_id} to {self.recipient_id}>'

class ChatAttachment(db.Model):
    """Attachments for chat messages (images, files, etc.)"""
    __tablename__ = 'chat_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))  # 'image', 'video', 'audio', 'document'
    file_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert attachment to dictionary for API responses"""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'file_name': self.file_name,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<ChatAttachment {self.id}: {self.file_type}>'
