"""Flask route handlers."""

from .health import health_bp
from .api import api_bp


def register_routes(app):
    """
    Register all Flask routes to the given Flask app.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(health_bp)
    app.register_blueprint(api_bp)


__all__ = [
    "register_routes",
    "health_bp",
    "api_bp",
]
