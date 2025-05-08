from datetime import datetime
from app import db

class Media(db.Model):
    """User media content (photos, reels, etc.)"""
    __tablename__ = 'media'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Media details
    media_type = db.Column(db.String(20), nullable=False)  # 'image', 'video', 'reel'
    file_path = db.Column(db.String(255), nullable=False)
    thumbnail_path = db.Column(db.String(255))
    caption = db.Column(db.Text)
    
    # For reels
    duration = db.Column(db.Integer)  # in seconds
    music = db.Column(db.String(255))
    filter_used = db.Column(db.String(50))
    
    # Status and visibility
    is_profile_picture = db.Column(db.Boolean, default=False)
    is_private = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    
    # Metrics
    view_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='media', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='media', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('Report', backref='media', lazy='dynamic')
    
    # Tags
    hashtags = db.Column(db.String(255))
    
    def increment_view(self):
        """Increment the view count"""
        self.view_count += 1
        db.session.commit()
    
    def get_hashtags_list(self):
        """Get hashtags as a list"""
        if self.hashtags:
            return self.hashtags.split(',')
        return []
    
    def get_likes_count(self):
        """Get total likes count"""
        return self.likes.count()
    
    def get_comments_count(self):
        """Get total comments count"""
        return self.comments.count()
    
    def to_dict(self):
        """Convert media to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username,
            'profile_picture': self.user.profile_picture,
            'media_type': self.media_type,
            'file_path': self.file_path,
            'thumbnail_path': self.thumbnail_path,
            'caption': self.caption,
            'duration': self.duration,
            'music': self.music,
            'filter_used': self.filter_used,
            'view_count': self.view_count,
            'likes_count': self.get_likes_count(),
            'comments_count': self.get_comments_count(),
            'hashtags': self.get_hashtags_list(),
            'is_private': self.is_private,
            'is_featured': self.is_featured,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Media {self.id}: {self.media_type} by {self.user_id}>'

class Comment(db.Model):
    """Comments on media content"""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Parent comment for replies
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]),
                             lazy='dynamic')
    
    def to_dict(self):
        """Convert comment to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username,
            'profile_picture': self.user.profile_picture,
            'media_id': self.media_id,
            'content': self.content,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat(),
            'replies_count': self.replies.count()
        }
    
    def __repr__(self):
        return f'<Comment {self.id} by {self.user_id} on {self.media_id}>'

class Like(db.Model):
    """Likes on media content"""
    __tablename__ = 'likes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Define unique constraint to prevent duplicate likes
    __table_args__ = (
        db.UniqueConstraint('user_id', 'media_id', name='_user_media_like_uc'),
    )
    
    def __repr__(self):
        return f'<Like by {self.user_id} on {self.media_id}>'

class Report(db.Model):
    """User reports for inappropriate content"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'))
    
    # Report details
    reason = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # 'pending', 'reviewed', 'resolved'
    admin_notes = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reported_user = db.relationship('User', foreign_keys=[reported_user_id])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def __repr__(self):
        return f'<Report {self.id}: {self.reason}>'
