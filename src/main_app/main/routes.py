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
    Validate that a URL is safe for redirects (relative or same-host).

    This prevents open-redirect vulnerabilities by ensuring the redirect
    target is either a relative path or belongs to the same host.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    # Safe if both scheme and netloc are empty (relative URL)
    if not parsed.scheme and not parsed.netloc:
        return True
    return False


def _validate_username(username: str) -> bool:
    """
    Validate a username from session for use as a directory name.
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
    Get the root directory for the current user based on session.
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
    Set the username in session for user identification.

    GET: Display the username form.
    POST: Process the form and set the session.
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
    Clear the username from session and redirect to user setup.
    """
    session.pop("username", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("main.set_user"))


@bp.route("/health")
def health() -> dict:
    """
    Health check endpoint for monitoring.

    Returns:
        JSON with status and version information.
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
    Dashboard - list all workspaces for the current user.
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
