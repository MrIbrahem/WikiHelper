"""
app.py - Application Entry Point

This module serves as the entry point for running the WikiHelper Flask application.
It creates an app instance using the factory pattern and provides it to the WSGI server.

Usage:
    # Development (with auto-reload)
    cd src && python app.py
    # or
    cd src && flask --app run app --debug

    # Production (with Gunicorn)
    cd src && gunicorn -w 4 -b 0.0.0.0:8000 "app:app"

Environment Variables:
    FLASK_DEBUG: Set to "1" for debug mode (development only)
    FLASK_SECRET_KEY: Required for production
    WIKI_WORK_ROOT: Root directory for workspace storage
"""

from main_app import create_app
from config import Config

# Create the application instance
# The factory pattern allows us to create app instances with different configs
app = create_app(Config)

if __name__ == "__main__":
    import sys

    # Enable debug mode if FLASK_DEBUG=1 or "debug" in command line args
    debug = app.config.get("DEBUG", False) or "debug" in sys.argv

    # Run the development server
    # WARNING: This is NOT suitable for production!
    # For production, use: gunicorn -w 4 -b 0.0.0.0:8000 "app:app"
    app.run(debug=debug, host="0.0.0.0", port=5000)
