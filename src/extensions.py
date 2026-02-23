"""
extensions.py - Flask Extensions Module

This module initializes Flask extensions without binding them to a specific
application instance. This allows the extensions to be imported anywhere in
the application without creating circular import issues.

The extensions are bound to the Flask app in the application factory function
(create_app) using the init_app pattern.

This pattern is required for the application factory pattern to work correctly
and to enable testing with different configurations.

Example:
    from extensions import csrf, limiter

    def create_app(config_class=Config):
        app = Flask(__name__)
        app.config.from_object(config_class)

        # Initialize extensions with the app
        csrf.init_app(app)
        limiter.init_app(app)

        return app
"""

from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

# Initialize extensions without app (deferred initialization)
# These will be bound to the app in create_app()
csrf = CSRFProtect()

# Rate limiter with default limits
# Limits can be customized per-route using @limiter.limit()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Use Redis in production: "redis://localhost:6379"
    strategy="fixed-window",  # or "moving-window" for more accurate limiting
)
