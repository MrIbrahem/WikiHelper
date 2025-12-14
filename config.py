# config.py
# Flask application configuration

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Flask configuration class."""

    # Secret key for session security
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-me-in-production")

    # Root directory for workspaces
    WIKI_WORK_ROOT = Path(os.environ.get("WIKI_WORK_ROOT", "./data")).resolve()

    # Maximum content length (5MB)
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))

    # Maximum title length
    MAX_TITLE_LENGTH = 120

    # Debug mode
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    # WTF CSRF protection
    WTF_CSRF_ENABLED = True
