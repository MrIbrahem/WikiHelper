"""
main - Main Blueprint

This blueprint handles the main application routes including:
- User authentication (set_user, logout)
- Dashboard (index)
- Static pages
"""

from flask import Blueprint

bp = Blueprint("main", __name__)

from main_app.main import routes  # Import routes after bp is created
