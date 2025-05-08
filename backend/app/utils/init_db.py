from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import db
from app.models.user import User, Role, UserPreference, UserInterest
from app.models.match import Match
from app.models.message import Message
from app.models.media import Media, Comment, Like
from app.models.subscription import Subscription

def init_db():
    """Initialize the database with sample data for development"""
    print("Initializing database with sample data...")
    
    # Create roles
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='Administrator role')
        db.session.add(admin_role)
    
    user_role = Role.query.filter_by(name='user').first()
    if not user_role:
        user_role = Role(name='user', description='Regular user role')
        db.session.add(user_role)
    
    premium_role = Role.query.filter_by(name='premium').first()
    if not premium_role:
        premium_role = Role(name='premium', description='Premium subscriber role')
        db.session.add(premium_role)
    
    db.session.commit()
    
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(email='admin@datify.com').first()
    if not admin:
        admin = User(
            email='admin@datify.com',
            username='admin',
            password_hash=generate_password_hash('admin123'),
            first_name='Admin',
            last_name='User',
            birthdate=datetime.strptime('1990-01-01', '%Y-%m-%d'),
            gender='other',
            bio='Administrator account',
            location='Server Room',
            latitude=0,
            longitude=0,
            is_verified=True,
            created_at=datetime.utcnow()
        )
        admin.roles.append(admin_role)
        db.session.add(admin)
        
        # Create admin preferences
        admin_prefs = UserPreference(
            user=admin,
            interested_in='both',
            min_age=18,
            max_age=65,
            max_distance=50
        )
        db.session.add(admin_prefs)
    
    # Create test users if they don't exist
    test_users = []
    for i in range(1, 6):
        user = User.query.filter_by(email=f'user{i}@datify.com').first()
        if not user:
            # Create with alternating genders
            gender = 'male' if i % 2 == 0 else 'female'
            
            user = User(
                email=f'user{i}@datify.com',
                username=f'user{i}',
                password_hash=generate_password_hash('password123'),
                first_name=f'Test{i}',
                last_name='User',
                birthdate=datetime.strptime(f'199{i}-01-01', '%Y-%m-%d'),
                gender=gender,
                bio=f'Test user {i} bio text. This is a sample bio for demonstration purposes.',
                location='New York',
                latitude=40.7128,
                longitude=-74.0060,
                is_verified=True,
                created_at=datetime.utcnow()
            )
            user.roles.append(user_role)
            
            # Make one user premium
            if i == 1:
                user.is_premium = True
                user.premium_until = datetime.utcnow() + timedelta(days=30)
                user.roles.append(premium_role)
            
            db.session.add(user)
            
            # Create user preferences
            interested_in = 'female' if gender == 'male' else 'male'
            user_prefs = UserPreference(
                user=user,
                interested_in=interested_in,
                min_age=18,
                max_age=35,
                max_distance=25
            )
            db.session.add(user_prefs)
            
            test_users.append(user)
    
    db.session.commit()
    
    # Add some interests
    interests = [
        'Travel', 'Music', 'Movies', 'Reading', 'Sports', 'Cooking', 
        'Photography', 'Art', 'Gaming', 'Fitness', 'Dance', 'Hiking'
    ]
    
    for interest_name in interests:
        interest = UserInterest.query.filter_by(name=interest_name).first()
        if not interest:
            interest = UserInterest(name=interest_name)
            db.session.add(interest)
    
    db.session.commit()
    
    # Create matches between users
    users = User.query.filter(User.email.like('user%@datify.com')).all()
    
    # Match user1 with user2 and user3
    if len(users) >= 3:
        # Check if match already exists
        match1 = Match.query.filter(
            ((Match.user1_id == users[0].id) & (Match.user2_id == users[1].id)) |
            ((Match.user1_id == users[1].id) & (Match.user2_id == users[0].id))
        ).first()
        
        if not match1:
            match1 = Match(
                user1_id=min(users[0].id, users[1].id),
                user2_id=max(users[0].id, users[1].id),
                created_at=datetime.utcnow() - timedelta(days=5),
                last_activity=datetime.utcnow() - timedelta(hours=2)
            )
            db.session.add(match1)
        
        match2 = Match.query.filter(
            ((Match.user1_id == users[0].id) & (Match.user2_id == users[2].id)) |
            ((Match.user1_id == users[2].id) & (Match.user2_id == users[0].id))
        ).first()
        
        if not match2:
            match2 = Match(
                user1_id=min(users[0].id, users[2].id),
                user2_id=max(users[0].id, users[2].id),
                created_at=datetime.utcnow() - timedelta(days=2),
                last_activity=datetime.utcnow() - timedelta(hours=1)
            )
            db.session.add(match2)
    
    db.session.commit()
    
    # Add messages to matches
    matches = Match.query.all()
    
    for match in matches:
        # Check if messages already exist
        if Message.query.filter_by(match_id=match.id).count() == 0:
            # Add a couple of messages
            message1 = Message(
                match_id=match.id,
                sender_id=match.user1_id,
                recipient_id=match.user2_id,
                content='Hey there! How are you doing?',
                created_at=match.created_at + timedelta(minutes=10),
                is_read=True,
                read_at=match.created_at + timedelta(minutes=15)
            )
            db.session.add(message1)
            
            message2 = Message(
                match_id=match.id,
                sender_id=match.user2_id,
                recipient_id=match.user1_id,
                content='I\'m good, thanks! How about you?',
                created_at=match.created_at + timedelta(minutes=20),
                is_read=True,
                read_at=match.created_at + timedelta(minutes=25)
            )
            db.session.add(message2)
            
            message3 = Message(
                match_id=match.id,
                sender_id=match.user1_id,
                recipient_id=match.user2_id,
                content='Doing well! Would you like to chat more?',
                created_at=match.created_at + timedelta(minutes=30),
                is_read=False
            )
            db.session.add(message3)
    
    db.session.commit()
    
    # Add some reels/media for users
    for user in users[:3]:  # Add media for first 3 test users
        # Check if user already has media
        if Media.query.filter_by(user_id=user.id).count() == 0:
            # Add a profile picture
            media1 = Media(
                user_id=user.id,
                media_type='image',
                file_path=f'/static/uploads/default/profile_{user.id}.jpg',
                is_profile_picture=True,
                created_at=datetime.utcnow() - timedelta(days=10)
            )
            db.session.add(media1)
            
            # Add a sample reel
            media2 = Media(
                user_id=user.id,
                media_type='reel',
                file_path=f'/static/uploads/default/reel_{user.id}.mp4',
                thumbnail_path=f'/static/uploads/default/reel_{user.id}_thumb.jpg',
                caption='Check out my first reel!',
                duration=15,
                music='Popular Song - Artist',
                filter_used='None',
                hashtags='#datify,#firstpost',
                created_at=datetime.utcnow() - timedelta(days=5),
                view_count=random.randint(50, 200)
            )
            db.session.add(media2)
    
    db.session.commit()
    
    # Add likes and comments to reels
    reels = Media.query.filter_by(media_type='reel').all()
    
    for reel in reels:
        # Add likes from other users
        for user in users:
            if user.id != reel.user_id and not Like.query.filter_by(user_id=user.id, media_id=reel.id).first():
                like = Like(
                    user_id=user.id,
                    media_id=reel.id,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 4))
                )
                db.session.add(like)
        
        # Add a comment
        if Comment.query.filter_by(media_id=reel.id).count() == 0:
            comment = Comment(
                user_id=users[0].id if users[0].id != reel.user_id else users[1].id,
                media_id=reel.id,
                content='Great reel! 👍',
                created_at=datetime.utcnow() - timedelta(days=2)
            )
            db.session.add(comment)
    
    db.session.commit()
    
    # Add a subscription for the premium user
    user1 = User.query.filter_by(email='user1@datify.com').first()
    if user1 and not Subscription.query.filter_by(user_id=user1.id).first():
        subscription = Subscription(
            user_id=user1.id,
            plan_type='premium',
            amount=19.99,
            currency='USD',
            status='active',
            start_date=datetime.utcnow() - timedelta(days=5),
            end_date=datetime.utcnow() + timedelta(days=25),
            auto_renew=True
        )
        db.session.add(subscription)
    
    db.session.commit()
    
    print("Database initialization complete!")

# Import this at the top for the random.randint function
import random

if __name__ == '__main__':
    # This would be called from a script
    init_db()
