"""
app - Flask Application Package

This package contains the WikiHelper Flask application using the factory pattern.
The create_app() function is the entry point for creating application instances.

Usage:
    # Development
    from main_app import create_app
    app = create_app()

    # Production
    from main_app import create_app
    from config import ProductionConfig
    app = create_app(ProductionConfig)

    # Testing
    from main_app import create_app
    from config import TestingConfig
    app = create_app(TestingConfig)
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from werkzeug.exceptions import RequestEntityTooLarge
from pathlib import Path
from typing import Optional

from flask import Flask, Response

from config import Config, DevelopmentConfig, TestingConfig, ProductionConfig
from extensions import csrf, limiter


def create_app(config_class: Optional[type] = None) -> Flask:
    """
    Application factory function.

    Creates and configures a Flask application instance with all extensions,
    blueprints, and request handlers registered.

    Args:
        config_class: Configuration class to use. Defaults to Config for
            production-like settings, or DevelopmentConfig if FLASK_DEBUG=1.

    Returns:
        Configured Flask application instance.

    Example:
        >>> app = create_app()
        >>> app.config['DEBUG']
        False
        >>> app = create_app(TestingConfig)
        >>> app.config['TESTING']
        True
    """
    # Determine config class if not provided
    if config_class is None:
        if os.environ.get("FLASK_DEBUG") == "1":
            config_class = DevelopmentConfig
        else:
            config_class = Config

    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)

    # Initialize extensions
    csrf.init_app(app)
    limiter.init_app(app)

    # Ensure the workspace root directory exists
    root: Path = app.config["WIKI_WORK_ROOT"]
    root.mkdir(parents=True, exist_ok=True)

    # Register blueprints
    from main_app.main import bp as main_bp
    from main_app.workspaces import bp as workspaces_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(workspaces_bp, url_prefix="/w")

    # Register error handlers
    from werkzeug.exceptions import RequestEntityTooLarge
    app.register_error_handler(RequestEntityTooLarge, _handle_large_request)

    # Register request handlers
    app.before_request(_check_user)
    app.after_request(_add_security_headers)

    # Configure logging for production
    if not app.debug and not app.testing:
        _configure_logging(app)

    return app


def _handle_large_request(e: RequestEntityTooLarge) -> tuple[Response, int]:
    """Handle requests that exceed MAX_CONTENT_LENGTH."""
    from flask import jsonify
    return jsonify({
        "error": "Request too large",
        "message": "Uploaded data exceeds the allowed size limit"
    }), 413


def _check_user() -> Optional[Response]:
    """
    Redirect to set_user if username session is missing.

    This hook runs before every request except set_user and static files.
    """
    from flask import request, session, redirect, url_for

    # Skip check for user setup and static files
    if request.endpoint in ["main.set_user", "static"]:
        return None

    if not session.get("username"):
        # Preserve the original destination
        next_path = request.path
        if request.query_string:
            next_path = f"{request.path}?{request.query_string.decode('utf-8')}"
        return redirect(url_for("main.set_user", next=next_path))
    return None


def _add_security_headers(response: Response) -> Response:
    """Add security headers to all responses."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Only add HSTS in production with HTTPS
    from flask import current_app
    if current_app.config.get("SESSION_COOKIE_SECURE"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


def _configure_logging(app: Flask) -> None:
    """Configure rotating file logging for production."""
    if not os.path.exists("logs"):
        os.mkdir("logs")

    file_handler = RotatingFileHandler(
        "logs/wikihelper.log",
        maxBytes=10240,  # 10KB per file
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    ))
    file_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("WikiHelper startup")
