"""
main/routes.py - Main Blueprint Routes

Routes for user management and dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from flask import (
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.wrappers import Response as WerkzeugResponse

from main_app.main import bp
from config import Config
from wikiops.storage import list_workspaces
from wikiops.utils import slugify_title

# Type alias for route return values
RouteResponse = str | Response | WerkzeugResponse


def _is_safe_redirect_url(url: str) -> bool:
    """
    Determine whether a redirect URL is a relative path and therefore safe to use.
    
    Parameters:
        url (str): The URL to validate.
    
    Returns:
        bool: `True` if the URL is relative (has no scheme and no network location), `False` otherwise.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    # Safe if both scheme and netloc are empty (relative URL)
    if not parsed.scheme and not parsed.netloc:
        return True
    return False


def _validate_username(username: str) -> bool:
    """
    Check whether a username is safe to use as a filesystem directory name.
    
    Rejects empty names, names containing '..', '/' or '\\', and reserved Windows device names
    (such as 'con', 'prn', 'aux', 'nul', 'com1'–'com9', 'lpt1'–'lpt9').
    
    Returns:
        True if the username is valid for use as a directory name, False otherwise.
    """
    if not username:
        return False
    if ".." in username or "/" in username or "\\" in username:
        return False
    reserved = {
        "con", "prn", "aux", "nul",
        "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
        "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
    }
    if username.lower() in reserved:
        return False
    return True


def _get_user_root() -> Optional[Path]:
    """
    Return the filesystem root directory for the current session's user or `None` if unavailable.
    
    Retrieves the username from the session, validates it, constructs the user directory under the configured `WIKI_WORK_ROOT`, ensures the resolved user path is contained within that root, creates the directory if missing, and returns the resolved Path.
    
    Returns:
        Path | None: The resolved Path to the user's root directory if a valid username exists and path checks succeed; `None` if the username is missing/invalid or path resolution/security checks fail.
    """
    from flask import current_app

    username = session.get("username")
    if not username:
        return None

    if not _validate_username(username):
        return None

    root: Path = current_app.config["WIKI_WORK_ROOT"]
    user_root = root / username

    try:
        resolved_user_root = user_root.resolve()
        resolved_root = root.resolve()
        if not resolved_user_root.is_relative_to(resolved_root):
            return None
    except (OSError, ValueError):
        return None

    resolved_user_root.mkdir(parents=True, exist_ok=True)
    return resolved_user_root


@bp.route("/set_user", methods=["GET", "POST"])
def set_user() -> RouteResponse:
    """
    Present a username entry form (GET) and, on POST, validate and store a slugified username in the session before redirecting to a safe next URL.
    
    GET: renders the username form. POST: trims and slugifies the submitted username, flashes an error and re-renders the form on invalid input, validates the target redirect for safety, marks the session permanent, stores the sanitized username under session["username"], and redirects to the determined next URL.
    
    Returns:
        A Flask response that either renders the username form template or redirects to the selected safe next page.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()

        if not username:
            flash("Username is required.", "error")
            return render_template("set_user.html")

        safe_username = slugify_title(username)

        if not safe_username:
            flash("Invalid username.", "error")
            return render_template("set_user.html")

        # Validate redirect target
        next_url = request.args.get("next")
        if not next_url or not _is_safe_redirect_url(next_url):
            next_url = url_for("main.index")

        # Set session as permanent
        session.permanent = True
        session["username"] = safe_username

        return redirect(next_url)

    return render_template("set_user.html")


@bp.route("/logout")
def logout() -> RouteResponse:
    """
    Clear the current username from the session and redirect the user to the username setup page.
    
    Removes the "username" key from the session and flashes an informational logout message.
    
    Returns:
        A Flask redirect response to the main.set_user route.
    """
    session.pop("username", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("main.set_user"))


@bp.route("/health")
def health() -> dict:
    """
    Health check endpoint returning service status and metadata.
    
    Returns:
        dict: JSON-serializable object with keys:
            - "status": service health string (e.g., "healthy").
            - "service": service name.
            - "version": service version.
    """
    from flask import jsonify
    return jsonify({
        "status": "healthy",
        "service": "wikihelper",
        "version": "1.0.0"
    })


@bp.route("/")
def index() -> str:
    """
    Render the dashboard showing active and completed workspaces for the current user.
    
    If there is no valid user context, renders the dashboard with empty workspace lists.
    Returns:
        str: Rendered HTML for the index dashboard. The template context includes
        `active_workspaces` (workspaces whose status is not "done") and
        `done_workspaces` (workspaces whose status is "done").
    """
    user_root = _get_user_root()
    if not user_root:
        return render_template("index.html", active_workspaces=[], done_workspaces=[])

    all_workspaces = list_workspaces(user_root)
    active_workspaces = [ws for ws in all_workspaces if ws.get("status") != "done"]
    done_workspaces = [ws for ws in all_workspaces if ws.get("status") == "done"]

    return render_template(
        "index.html",
        active_workspaces=active_workspaces,
        done_workspaces=done_workspaces
    )