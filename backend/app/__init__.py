import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_restful import Api
from flask_security import Security, SQLAlchemyUserDatastore
import redis

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
bcrypt = Bcrypt()
socketio = SocketIO()
cors = CORS()
api = Api()
security = Security()

# Redis connection
redis_client = None

def create_app(config_name='default'):
    from config import config
    
    # Initialize app
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)
    api.init_app(app)
    
    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Create uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Set up Redis
    global redis_client
    redis_client = redis.from_url(app.config['REDIS_URL'])
    
    # Set up SocketIO
    socketio.init_app(app, message_queue=app.config['SOCKETIO_MESSAGE_QUEUE'], 
                      cors_allowed_origins="*")
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.api import api_bp
    from app.routes.user import user_bp
    from app.routes.match import match_bp
    from app.routes.chat import chat_bp
    from app.routes.reels import reels_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(match_bp, url_prefix='/match')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(reels_bp, url_prefix='/reels')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Set up Flask-Security
    from app.models.user import User, Role
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security.init_app(app, user_datastore)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register socket event handlers
    from app.routes.events import register_socket_events
    register_socket_events(socketio)
    
    return app

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404
    
    @app.errorhandler(500)
    def server_error(error):
        return {"error": "Server error"}, 500
