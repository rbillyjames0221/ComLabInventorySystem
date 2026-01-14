"""Routes package"""
from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.devices import devices_bp
from app.routes.api import api_bp

__all__ = ['auth_bp', 'admin_bp', 'devices_bp', 'api_bp']

