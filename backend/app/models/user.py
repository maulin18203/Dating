from datetime import datetime
import uuid
from flask_login import UserMixin
from flask_security import RoleMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

# Role and UserRoles association table for Flask-Security
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('roles.id'))
)

# User-Interest many-to-many relationship table
user_interests = db.Table('user_interests',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interests.id'), primary_key=True)
)

class Role(db.Model, RoleMixin):
    """Role model for Flask-Security"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))
    
    def __str__(self):
        return self.name

class User(db.Model, UserMixin):
    """User model for authentication and profile information"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    fs_uniquifier = db.Column(db.String(255), unique=True, default=lambda: str(uuid.uuid4()))
    active = db.Column(db.Boolean(), default=True)
    confirmed_at = db.Column(db.DateTime())
    
    # Profile information
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    birthdate = db.Column(db.Date)
    gender = db.Column(db.String(20))
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(255))
    location = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    phone_number = db.Column(db.String(20))
    
    # Account information
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    premium_until = db.Column(db.DateTime)
    
    # Verification
    is_verified = db.Column(db.Boolean, default=False)
    
    # Relationships
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
    preferences = db.relationship('UserPreference', backref='user', uselist=False, cascade='all, delete-orphan')
    verification = db.relationship('Verification', backref='user', uselist=False, cascade='all, delete-orphan')
    interests = db.relationship('UserInterest', secondary=user_interests, backref=db.backref('users', lazy='dynamic'))
    
    # Messages
    sent_messages = db.relationship('Message', 
                                    foreign_keys='Message.sender_id',
                                    backref='sender', 
                                    lazy='dynamic', 
                                    cascade='all, delete-orphan')
    received_messages = db.relationship('Message', 
                                       foreign_keys='Message.recipient_id',
                                       backref='recipient', 
                                       lazy='dynamic')
    
    # Media relationships
    media_uploads = db.relationship('Media', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    reports_made = db.relationship('Report', foreign_keys='Report.reporter_id', backref='reporter', lazy='dynamic')
    
    # Subscription relationship
    subscriptions = db.relationship('Subscription', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        # Create default preferences when user is created
        if self.preferences is None:
            self.preferences = UserPreference(user_id=self.id)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_age(self):
        """Calculate user age from birthdate"""
        if self.birthdate:
            today = datetime.today()
            return today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))
        return None
    
    def update_last_seen(self):
        """Update last seen timestamp"""
        self.last_seen = datetime.utcnow()
        db.session.commit()
    
    def is_admin(self):
        """Check if user has admin role"""
        return any(role.name == 'admin' for role in self.roles)
    
    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'age': self.get_age(),
            'gender': self.gender,
            'bio': self.bio,
            'profile_picture': self.profile_picture,
            'location': self.location,
            'is_verified': self.is_verified,
            'is_premium': self.is_premium,
            'is_online': self.is_online,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

class UserPreference(db.Model):
    """User preferences for matching and privacy"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    
    # Matching preferences
    interested_in = db.Column(db.String(20))  # 'men', 'women', 'both', 'other'
    min_age = db.Column(db.Integer, default=18)
    max_age = db.Column(db.Integer, default=100)
    max_distance = db.Column(db.Integer, default=50)  # in kilometers
    
    # Privacy preferences
    show_online_status = db.Column(db.Boolean, default=True)
    show_location = db.Column(db.Boolean, default=True)
    show_age = db.Column(db.Boolean, default=True)
    show_last_active = db.Column(db.Boolean, default=True)
    
    # Notification preferences
    email_matches = db.Column(db.Boolean, default=True)
    email_messages = db.Column(db.Boolean, default=True)
    email_likes = db.Column(db.Boolean, default=True)
    push_matches = db.Column(db.Boolean, default=True)
    push_messages = db.Column(db.Boolean, default=True)
    push_likes = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<UserPreference {self.user_id}>'

class UserInterest(db.Model):
    """Interests/hobbies that users can select"""
    __tablename__ = 'interests'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50))
    
    def __repr__(self):
        return f'<Interest {self.name}>'

class UserBlocked(db.Model):
    """Blocked users relationship"""
    __tablename__ = 'user_blocks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    blocked_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Define unique constraint to prevent duplicate blocks
    __table_args__ = (db.UniqueConstraint('user_id', 'blocked_id', name='_user_blocked_uc'),)
    
    # Define relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('blocked_users', lazy='dynamic'))
    blocked = db.relationship('User', foreign_keys=[blocked_id])
    
    def __repr__(self):
        return f'<UserBlocked {self.user_id} blocked {self.blocked_id}>'

class UserLike(db.Model):
    """Likes between users (for swiping right)"""
    __tablename__ = 'user_likes'
    
    id = db.Column(db.Integer, primary_key=True)
    liker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    liked_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_super_like = db.Column(db.Boolean, default=False)
    
    # Define unique constraint to prevent duplicate likes
    __table_args__ = (db.UniqueConstraint('liker_id', 'liked_id', name='_user_liked_uc'),)
    
    # Define relationships
    liker = db.relationship('User', foreign_keys=[liker_id], backref=db.backref('likes_given', lazy='dynamic'))
    liked = db.relationship('User', foreign_keys=[liked_id], backref=db.backref('likes_received', lazy='dynamic'))
    
    def __repr__(self):
        return f'<UserLike {self.liker_id} likes {self.liked_id}>'

class Verification(db.Model):
    """User verification information"""
    __tablename__ = 'verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    
    # Verification details
    id_type = db.Column(db.String(20))  # 'passport', 'driver_license', 'id_card'
    id_number = db.Column(db.String(50))
    selfie_image = db.Column(db.String(255))
    id_image = db.Column(db.String(255))
    
    # Verification status
    is_verified = db.Column(db.Boolean, default=False)
    verification_date = db.Column(db.DateTime)
    rejected_reason = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Verification {self.user_id} {"verified" if self.is_verified else "pending"}>'
