import os
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app, socketio, db
from app.models import User, Role, Match, Message, UserPreference, Media, Report

# Create app with the specified configuration
app = create_app(os.getenv('FLASK_ENV', 'development'))

# Shell context processor
@app.shell_context_processor
def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Match=Match, 
                Message=Message, UserPreference=UserPreference, Media=Media, Report=Report)

# Run the application
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=app.config['DEBUG'])
