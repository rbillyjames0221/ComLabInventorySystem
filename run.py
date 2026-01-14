"""Application entry point"""
import os
from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    # Environment-based configuration
    env = os.environ.get('FLASK_ENV', 'development')
    debug_mode = env == 'development'
    
    # Run on all network interfaces (0.0.0.0) to allow mobile access
    # Set host='127.0.0.1' if you only want localhost access
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)

