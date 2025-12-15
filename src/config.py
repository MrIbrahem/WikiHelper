# config.py
# Flask application configuration

import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Flask configuration class."""

    # Secret key for session security
    _secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not _secret_key:
        warnings.warn(
            "FLASK_SECRET_KEY not set. Using default key which is insecure for production!",
            UserWarning,
            stacklevel=2
        )
        _secret_key = "change-me-in-production"
    SECRET_KEY = _secret_key

    # Root directory for workspaces
    ALTERNATIVE_PATH = os.environ.get("HOME", ".") + "/data"

    WIKI_WORK_ROOT = Path(os.environ.get("WIKI_WORK_ROOT") or ALTERNATIVE_PATH).resolve()

    # Maximum content length (5MB)
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 500 * 1024 * 1024))

    # Maximum title length
    MAX_TITLE_LENGTH = 120

    # Debug mode
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    # WTF CSRF protection
    WTF_CSRF_ENABLED = True
