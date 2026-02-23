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
    Create and configure a Flask application with extensions, blueprints, error handlers, and request hooks registered.
    
    Parameters:
        config_class (type, optional): Configuration class to apply to the app. If omitted, uses DevelopmentConfig when the environment variable FLASK_DEBUG is "1", otherwise uses Config.
    
    Returns:
        Flask: The configured Flask application instance.
    """
    # Determine config class if not provided
    if config_class is None:
        if os.environ.get("FLASK_DEBUG") == "1":
            config_class = DevelopmentConfig
        else:
            config_class = Config

    # Use absolute paths for template and static folders
    # __file__ is in main_app/, so parent is src/
    src_dir = Path(__file__).parent.parent
    app = Flask(
        __name__,
        template_folder=str(src_dir / "templates"),
        static_folder=str(src_dir / "static")
    )
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
    """
    Return a 413 JSON response for requests that exceed the configured maximum content length.
    
    Parameters:
        e (RequestEntityTooLarge): The exception raised for an oversized request.
    
    Returns:
        tuple[Response, int]: A JSON response containing `error` and `message` fields, and the HTTP status code 413.
    """
    from flask import jsonify
    return jsonify({
        "error": "Request too large",
        "message": "Uploaded data exceeds the allowed size limit"
    }), 413


def _check_user() -> Optional[Response]:
    """
    Ensure a username is present in the session before processing a request.
    
    If the session does not contain "username", redirects to the "main.set_user" endpoint and preserves the original path and query string as the `next` parameter. This hook is not applied to the "main.set_user" and "static" endpoints.
    
    Returns:
        Response or None: A redirect `Response` to the user-setup page when no username is present, `None` to continue normal request handling.
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
    """
    Attach common security-related HTTP headers to the given response.
    
    Adds the following headers to mitigate common web vulnerabilities:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: SAMEORIGIN
    - X-XSS-Protection: 1; mode=block
    
    If the application's SESSION_COOKIE_SECURE config is enabled, also adds
    Strict-Transport-Security set to "max-age=31536000; includeSubDomains".
    
    Parameters:
    	response (Response): The Flask response object to modify.
    
    Returns:
    	response (Response): The same response object with security headers applied.
    """
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Only add HSTS in production with HTTPS
    from flask import current_app
    if current_app.config.get("SESSION_COOKIE_SECURE"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


def _configure_logging(app: Flask) -> None:
    """
    Set up rotating file logging for production.
    
    Creates a "logs" directory if it does not exist, attaches a RotatingFileHandler writing to "logs/wikihelper.log" (max 10240 bytes per file, 10 backup files), sets the handler and application logger level to INFO, and logs a startup message.
    
    Parameters:
        app (Flask): The Flask application instance to configure.
    """
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