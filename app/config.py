import os
import secrets

class Config:
    """Application configuration"""
    # Generate secure SECRET_KEY from environment or create a random one
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(32)
    DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.db")
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    
    # Environment detection
    ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'
    
    # Session security configuration
    PERMANENT_SESSION_LIFETIME = 28800  # 8 hours in seconds
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Only set Secure=True in production (HTTPS)
    SESSION_COOKIE_SECURE = ENV == 'production'
    
    # Rate limiting configuration
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = "memory://"
    
    @staticmethod
    def init_app(app):
        """Initialize app with config"""
        app.config['SECRET_KEY'] = Config.SECRET_KEY
        app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
        app.config['DB_FILE'] = Config.DB_FILE
        app.config['PERMANENT_SESSION_LIFETIME'] = Config.PERMANENT_SESSION_LIFETIME
        app.config['SESSION_COOKIE_HTTPONLY'] = Config.SESSION_COOKIE_HTTPONLY
        app.config['SESSION_COOKIE_SAMESITE'] = Config.SESSION_COOKIE_SAMESITE
        app.config['SESSION_COOKIE_SECURE'] = Config.SESSION_COOKIE_SECURE

