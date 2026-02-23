"""
workspaces - Workspaces Blueprint

This blueprint handles all workspace-related routes including:
- Creating new workspaces
- Importing from Wikipedia
- Editing workspaces
- Browsing and downloading files
"""

from flask import Blueprint

bp = Blueprint("workspaces", __name__)

from main_app.workspaces import routes  # Import routes after bp is created
