"""Flask application factory"""
import os
from flask import Flask, session, request, redirect, url_for, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
from app.config import Config
from app.routes import auth_bp, admin_bp, devices_bp, api_bp
from app.utils.sidebar_context import get_sidebar_context
from app.utils.logging_config import setup_logging

# Initialize extensions
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
csrf = CSRFProtect()


def create_app(config_class=Config):
    """Create and configure Flask application"""
    # Get the root directory (ComLabInventorySystem)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(root_dir, 'templates')
    static_dir = os.path.join(root_dir, 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # Initialize config
    config_class.init_app(app)
    
    # Initialize extensions
    limiter.init_app(app)
    csrf.init_app(app)
    
    # Setup logging
    setup_logging(app)
    
    # Make limiter available to other modules
    app.limiter = limiter
    
    # Session management - set permanent session lifetime
    # Get the value from config (should be seconds as integer)
    session_lifetime_seconds = app.config.get('PERMANENT_SESSION_LIFETIME', 28800)
    # Convert to timedelta if it's not already
    if isinstance(session_lifetime_seconds, timedelta):
        app.permanent_session_lifetime = session_lifetime_seconds
    else:
        app.permanent_session_lifetime = timedelta(seconds=int(session_lifetime_seconds))
    
    # Make sessions permanent by default
    @app.before_request
    def make_session_permanent():
        session.permanent = True
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(api_bp)
    
    # Context processor for sidebar variables
    @app.context_processor
    def inject_sidebar_context():
        """Inject sidebar context into all templates"""
        return get_sidebar_context()
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    return app

