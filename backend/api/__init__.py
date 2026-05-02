"""
API Routes Package
"""
from .auth_routes import auth_bp
from .forecast_routes import forecast_bp
from .user_routes import user_bp
from .data_routes import data_bp

__all__ = ['auth_bp', 'forecast_bp', 'user_bp', 'data_bp']
