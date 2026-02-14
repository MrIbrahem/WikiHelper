"""
config.py - Flask Application Configuration Module

This module defines the configuration class for the WikiHelper Flask application.
Configuration values are loaded from environment variables with sensible defaults.

Configuration Sources (in order of priority):
    1. Environment variables
    2. .env file (via python-dotenv)
    3. Default values defined in this module

Security Notes:
    - FLASK_SECRET_KEY should be set to a secure random value in production
    - DEBUG mode should never be enabled in production
    - WIKI_WORK_ROOT should be set to a dedicated directory with appropriate permissions

Usage:
    from config import Config
    app.config.from_object(Config)
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

# Load environment variables from .env file before accessing them.
# This allows developers to create a .env file with local configuration.
load_dotenv()


class Config:
    """
    Flask application configuration class.

    This class defines all configuration options for the WikiHelper application.
    Values are read from environment variables at class definition time.

    Attributes:
        SECRET_KEY: Flask secret key for session security and CSRF protection.
                    Must be set to a secure random value in production.
        WIKI_WORK_ROOT: Root directory for storing workspace data.
                        Each user's workspaces are stored in subdirectories.
        MAX_CONTENT_LENGTH: Maximum size for uploaded/request content in bytes.
                            Prevents denial-of-service via large uploads.
        MAX_TITLE_LENGTH: Maximum length for workspace titles in characters.
        DEBUG: Enable Flask debug mode. Should be False in production.
        WTF_CSRF_ENABLED: Enable CSRF protection for WTF forms.

    Environment Variables:
        FLASK_SECRET_KEY: Sets SECRET_KEY. Required for production.
        WIKI_WORK_ROOT: Sets WIKI_WORK_ROOT. Defaults to $HOME/data.
        FLASK_DEBUG: Sets DEBUG. Use "1" for True, "0" for False.
        MAX_CONTENT_LENGTH: Sets MAX_CONTENT_LENGTH in bytes.

    Example:
        >>> from config import Config
        >>> Config.SECRET_KEY
        'change-me-in-production'  # Default (insecure)
        >>> Config.DEBUG
        False

    Warning:
        Using the default SECRET_KEY in production is a security vulnerability.
        Always set FLASK_SECRET_KEY in production environments.
    """

    # Secret key for session security and CSRF protection.
    # This is used to sign session cookies and CSRF tokens.
    # In production, this MUST be set to a secure random value.
    _secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not _secret_key:
        warnings.warn(
            "FLASK_SECRET_KEY not set. Using default key which is insecure for production!",
            UserWarning,
            stacklevel=2
        )
        _secret_key = "change-me-in-production"
    SECRET_KEY: Final[str] = _secret_key

    # Root directory for workspace storage.
    # Falls back to $HOME/data if WIKI_WORK_ROOT is not set.
    # The path is resolved to an absolute path at startup.
    _home = os.environ.get("HOME", ".")
    _alternative_path = f"{_home}/data"
    _work_root_raw = os.environ.get("WIKI_WORK_ROOT") or _alternative_path
    WIKI_WORK_ROOT: Final[Path] = Path(_work_root_raw).resolve()

    # Maximum content length for uploads and requests.
    # Default is 500MB to accommodate large Wikipedia articles.
    # This prevents memory exhaustion from oversized uploads.
    _max_content = os.environ.get("MAX_CONTENT_LENGTH", "524288000")
    MAX_CONTENT_LENGTH: Final[int] = int(_max_content)

    # Maximum length for workspace titles.
    # This prevents database/storage issues with extremely long titles.
    MAX_TITLE_LENGTH: Final[int] = 120

    # Debug mode setting.
    # Enable with FLASK_DEBUG=1 in environment.
    # WARNING: Never enable in production - exposes sensitive information.
    _debug = os.environ.get("FLASK_DEBUG", "0")
    DEBUG: Final[bool] = _debug == "1"

    # CSRF protection for Flask-WTF forms.
    # This should always be enabled unless you have a specific reason to disable it.
    WTF_CSRF_ENABLED: Final[bool] = True


# Log configuration at startup for debugging purposes.
# This helps diagnose configuration issues without exposing sensitive values.
if DEBUG := (os.environ.get("FLASK_DEBUG", "0") == "1"):
    warnings.warn(
        f"Flask DEBUG mode enabled. WIKI_WORK_ROOT={WIKI_WORK_ROOT}",
        UserWarning,
        stacklevel=2
    )
