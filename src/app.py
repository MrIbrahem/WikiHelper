"""
app.py - Flask Application for Wiki Ref Workspace Manager

This is the main entry point for the WikiHelper web application. It defines
all routes and handles HTTP requests for workspace management.

Application Architecture:
    - Uses Flask's built-in development server (suitable for internal use)
    - Cookie-based user identification for workspace isolation
    - CSRF protection on all forms
    - Path traversal protection on all file operations

User Isolation:
    Workspaces are isolated per-user based on a cookie-stored username.
    Each user's workspaces are stored in a subdirectory under WIKI_WORK_ROOT.
    Note: This is NOT authentication - cookies can be manipulated.

Routes:
    /                   Dashboard listing workspaces
    /new                Create new workspace from WikiText
    /import-wikipedia   Import article from Wikipedia API
    /set_user           Set username cookie
    /logout             Clear username cookie
    /w/<slug>/edit      Edit workspace content
    /w/<slug>/save      Save and restore references
    /w/<slug>/browse    Browse workspace files
    /w/<slug>/file/<name>   View specific file
    /w/<slug>/download/<name>   Download file

Usage:
    cd src && python app.py
    # Access at http://localhost:5000

Security Considerations:
    - No rate limiting (consider adding for public deployments)
    - No authentication (cookie-based user isolation only)
    - DEBUG mode should never be enabled in production
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_wtf.csrf import CSRFProtect
from urllib.parse import quote
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.wrappers import Response as WerkzeugResponse

# Import wikiops modules for workspace operations.
from wikiops.storage import (
    get_workspace_file,
    list_workspaces,
    create_workspace,
    read_json,
    read_text,
    safe_workspace_path,
    update_workspace,
)
from wikiops.wikipedia import fetch_wikipedia_article, validate_article_title

# Import configuration.
from config import Config


# Type alias for Flask route return values.
# Routes can return strings (templates), Response objects, or redirects.
RouteResponse = Union[str, Response, WerkzeugResponse]


# ============================================================================
# Application Setup
# ============================================================================

# Initialize Flask application with configuration from Config class.
app = Flask(__name__)
app.config.from_object(Config)

# Initialize CSRF protection for all forms.
# This adds hidden csrf_token fields to forms and validates them on POST.
csrf = CSRFProtect(app)

# Ensure the workspace root directory exists.
# This is the parent directory for all user workspace directories.
root: Path = app.config["WIKI_WORK_ROOT"]
root.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Helper Functions
# ============================================================================

def is_safe_redirect_url(url: str) -> bool:
    """
    Validate that a URL is safe for redirects (relative or same-host).

    This prevents open-redirect vulnerabilities by ensuring the redirect
    target is either a relative path or belongs to the same host.

    Args:
        url: The URL to validate.

    Returns:
        True if the URL is safe to redirect to, False otherwise.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    # Safe if both scheme and netloc are empty (relative URL)
    if not parsed.scheme and not parsed.netloc:
        return True
    # Could add same-host check here if needed for absolute URLs
    return False


def validate_username(username: str) -> bool:
    """
    Validate a username from cookies for use as a directory name.

    This prevents path traversal attacks by rejecting usernames that
    contain path separators, parent directory references, or other
    unsafe characters.

    Args:
        username: The username to validate.

    Returns:
        True if the username is safe, False otherwise.
    """
    if not username:
        return False
    # Reject path traversal attempts
    if ".." in username or "/" in username or "\\" in username:
        return False
    # Reject Windows reserved names
    reserved = {
        "con", "prn", "aux", "nul",
        "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
        "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
    }
    if username.lower() in reserved:
        return False
    return True


def get_user_root() -> Optional[Path]:
    """
    Get the root directory for the current user based on cookies.

    This function implements simple user isolation by creating a
    subdirectory for each username. Note that this is NOT authentication -
    cookies can be manipulated by users.

    Returns:
        Path to the user's workspace directory if username cookie exists
        and is valid.
        None if no username cookie is set or validation fails.

    Side Effects:
        Creates the user directory if it doesn't exist and validation passes.
    """
    username = request.cookies.get("username")
    if not username:
        return None

    # Validate username to prevent path traversal attacks.
    if not validate_username(username):
        return None

    # Create user-specific directory under root.
    user_root = root / username

    # Resolve and verify the path is within root.
    try:
        resolved_user_root = user_root.resolve()
        resolved_root = root.resolve()
        if not resolved_user_root.is_relative_to(resolved_root):
            return None
    except (OSError, ValueError):
        return None

    resolved_user_root.mkdir(parents=True, exist_ok=True)
    return resolved_user_root


# ============================================================================
# Request Hooks
# ============================================================================

@app.before_request
def check_user() -> Optional[RouteResponse]:
    """
    Redirect to set_user if username cookie is missing.

    This hook runs before every request except set_user and static files.
    It ensures all users have a username set before accessing workspaces.

    Returns:
        None if username cookie exists (request proceeds normally).
        Redirect response to set_user if no username cookie.

    Exempt Routes:
        - set_user: The route that sets the cookie
        - static: Static file serving (CSS, JS, images)
    """
    # Skip check for user setup and static files.
    if request.endpoint in ["set_user", "static"]:
        return None

    if not request.cookies.get("username"):
        # Redirect to user setup, preserving the original destination.
        # return redirect(url_for("set_user", next=request.url))

        # Pass the relative path to avoid failing is_safe_redirect_url's
        # scheme/netloc check, which blocks absolute URLs.
        next_path = request.path
        if request.query_string:
            next_path = f"{request.path}?{request.query_string.decode('utf-8')}"
        return redirect(url_for("set_user", next=next_path))
    return None


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(RequestEntityTooLarge)
def handle_large_request(_e: RequestEntityTooLarge) -> Tuple[Response, int]:
    """
    Handle requests that exceed MAX_CONTENT_LENGTH.

    This handler returns a JSON error response for oversized uploads,
    which is useful for AJAX-based file uploads.

    Args:
        e: The RequestEntityTooLarge exception.

    Returns:
        JSON response with error details and 413 status code.
    """
    return jsonify({
        "error": "Request too large",
        "message": "Uploaded data exceeds the allowed size limit"
    }), 413


# ============================================================================
# User Management Routes
# ============================================================================

@app.route("/set_user", methods=["GET", "POST"])
def set_user() -> RouteResponse:
    """
    Set the username cookie for user identification.

    GET: Display the username form.
    POST: Process the form and set the cookie.

    The username is slugified for use as a directory name, so special
    characters and non-ASCII text are removed.

    Returns:
        GET: Rendered set_user.html template.
        POST: Redirect to next URL or index with username cookie set.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()

        if not username:
            flash("Username is required.", "error")
            return render_template("set_user.html")

        # Slugify username for safe use as directory name.
        from wikiops.utils import slugify_title
        safe_username = slugify_title(username)

        if not safe_username:
            flash("Invalid username.", "error")
            return render_template("set_user.html")

        # Determine redirect target (next URL or index).
        # Validate next_url to prevent open-redirect attacks.
        next_url = request.args.get("next")
        if not next_url or not is_safe_redirect_url(next_url):
            next_url = url_for("index")

        # Create response with cookie set.
        resp = make_response(redirect(next_url))
        # Cookie expires in 30 days.
        resp.set_cookie("username", safe_username, max_age=30 * 24 * 60 * 60)

        return resp

    return render_template("set_user.html")


@app.route("/logout")
def logout() -> RouteResponse:
    """
    Clear the username cookie and redirect to user setup.

    Returns:
        Redirect to set_user with cookie deleted.
    """
    resp = make_response(redirect(url_for("set_user")))
    resp.delete_cookie("username")
    flash("Logged out successfully.", "info")
    return resp


# ============================================================================
# Dashboard Route
# ============================================================================

@app.route("/")
def index() -> str:
    """
    Dashboard - list all workspaces for the current user.

    Workspaces are grouped by status:
    - Active: status != "done" (currently being edited)
    - Done: status == "done" (editing complete)

    Returns:
        Rendered index.html template with workspace lists.
    """
    user_root = get_user_root()
    if not user_root:
        # Should not happen due to before_request hook, but handle gracefully.
        return render_template("index.html", active_workspaces=[], done_workspaces=[])

    # Get all workspaces and split by status.
    all_workspaces = list_workspaces(user_root)
    active_workspaces = [ws for ws in all_workspaces if ws.get("status") != "done"]
    done_workspaces = [ws for ws in all_workspaces if ws.get("status") == "done"]

    return render_template(
        "index.html",
        active_workspaces=active_workspaces,
        done_workspaces=done_workspaces
    )


# ============================================================================
# Workspace Creation Routes
# ============================================================================

@app.route("/new", methods=["GET", "POST"])
def new_workspace() -> RouteResponse:
    """
    Create a new workspace from pasted or uploaded WikiText.

    GET: Display the new workspace form.
    POST: Create the workspace from submitted content.

    The form accepts either direct text input or file upload.
    File upload takes precedence if both are provided.

    Returns:
        GET: Rendered new.html template.
        POST: Redirect to edit page on success, or form with errors.
    """
    user_root = get_user_root()
    if not user_root:
        return redirect(url_for("set_user"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        wikitext = request.form.get("wikitext", "")

        # Check for file upload (takes precedence over text field).
        file = request.files.get("wikitext_file")
        if file and file.filename:
            try:
                wikitext = file.read().decode("utf-8")
            except UnicodeDecodeError:
                flash("Uploaded file must be UTF-8 encoded text.", "error")
                return render_template("new.html", title=title, wikitext=wikitext)

        # Validate title.
        if not title:
            flash("Title is required.", "error")
            return render_template("new.html", title=title, wikitext=wikitext)

        max_title = app.config.get("MAX_TITLE_LENGTH", 120)
        if len(title) > max_title:
            flash(f"Title must be {max_title} characters or less.", "error")
            return render_template("new.html", title=title, wikitext=wikitext)

        # Validate wikitext content.
        if not wikitext:
            if file and file.filename:
                flash("Uploaded file is empty or does not contain valid text.", "error")
            else:
                flash("WikiText content is required.", "error")
            return render_template("new.html", title=title, wikitext=wikitext)

        try:
            slug, _, is_new = create_workspace(user_root, title, wikitext)

            if is_new:
                flash(f"Workspace '{slug}' created successfully.", "success")
            else:
                flash(f"Workspace '{slug}' already exists. Redirecting to edit.", "info")

            return redirect(url_for("edit_workspace", slug=slug))

        except ValueError as e:
            flash(str(e), "error")
            return render_template("new.html", title=title, wikitext=wikitext)

    return render_template("new.html")


@app.route("/import-wikipedia", methods=["GET", "POST"])
def import_wikipedia() -> RouteResponse:
    """
    Import an article from English Wikipedia to create a new workspace.

    GET: Display the Wikipedia import form.
    POST: Fetch article and create workspace.

    The article title is validated client-side and server-side before
    making the API request to Wikipedia.

    Returns:
        GET: Rendered import_wikipedia.html template.
        POST: Redirect to edit page on success, or form with errors.
    """
    user_root = get_user_root()
    if not user_root:
        return redirect(url_for("set_user"))

    if request.method == "POST":
        article_title = request.form.get("article_title", "").strip()

        # Validate article title format.
        is_valid, error_msg = validate_article_title(article_title)
        if not is_valid:
            flash(error_msg, "error")
            return render_template("import_wikipedia.html", article_title=article_title)

        # Fetch article content from Wikipedia API.
        wikitext, error = fetch_wikipedia_article(article_title)

        if error:
            flash(error, "error")
            return render_template("import_wikipedia.html", article_title=article_title)

        if not wikitext:
            flash("Retrieved empty content from Wikipedia.", "error")
            return render_template("import_wikipedia.html", article_title=article_title)

        # Create workspace with fetched content.
        try:
            slug, _, is_new = create_workspace(
                user_root, article_title, wikitext
            )

            if is_new:
                flash(f"Successfully imported '{article_title}' from Wikipedia.", "success")
            else:
                flash(f"Workspace '{slug}' already exists. Redirecting to edit.", "info")

            return redirect(url_for("edit_workspace", slug=slug))

        except ValueError as e:
            flash(str(e), "error")
            return render_template("import_wikipedia.html", article_title=article_title)

    return render_template("import_wikipedia.html")


# ============================================================================
# Workspace Editing Routes
# ============================================================================

@app.route("/w/<slug>/edit", methods=["GET"])
def edit_workspace(slug: str) -> str:
    """
    Edit workspace's editable.wiki content.

    This route displays the editing interface with the current editable
    content and a preview of the restored content.

    Args:
        slug: The workspace identifier (safe directory name).

    Returns:
        Rendered edit.html template with workspace content.

    Raises:
        404: If workspace doesn't exist or slug is invalid.
    """
    user_root = get_user_root()
    if not user_root:
        # This shouldn't happen due to before_request, but handle it.
        abort(404)

    # Validate and resolve workspace path.
    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    editable_path = workspace_path / "editable.wiki"
    if not editable_path.exists():
        abort(404)

    # Load content for editing.
    editable_content = read_text(editable_path)

    # Load metadata for display.
    meta_path = workspace_path / "meta.json"
    meta = read_json(meta_path) if meta_path.exists() else {}

    # Load restored content for preview.
    restored_path = workspace_path / "restored.wiki"
    restored_content = read_text(restored_path) if restored_path.exists() else ""

    return render_template(
        "edit.html",
        slug=slug,
        editable_content=editable_content,
        restored_content=restored_content,
        meta=meta
    )


@app.route("/w/<slug>/save", methods=["POST"])
def save_workspace(slug: str) -> RouteResponse:
    """
    Save workspace's editable.wiki and regenerate restored.wiki.

    This route handles form submission from the edit page. It saves
    the user's edits and triggers reference restoration.

    Args:
        slug: The workspace identifier.

    Returns:
        Redirect to view the restored file on success.
        Redirect back to edit page on error.

    Raises:
        404: If workspace doesn't exist.
    """
    user_root = get_user_root()
    if not user_root:
        abort(404)

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    # Get form data.
    editable_content = request.form.get("editable_content", "")
    status = request.form.get("status")

    try:
        update_workspace(workspace_path, editable_content, status=status)
        flash("Workspace updated and references restored.", "success")
        return redirect(url_for("view_file", slug=slug, name="restored.wiki"))
    except Exception as e:
        flash(f"Error updating workspace: {e}", "error")
        return redirect(url_for("edit_workspace", slug=slug))


# ============================================================================
# Workspace Browsing Routes
# ============================================================================

@app.route("/w/<slug>/browse")
def browse_workspace(slug: str) -> str:
    """
    Browse workspace files.

    Displays a list of all files in the workspace with their sizes
    and modification times.

    Args:
        slug: The workspace identifier.

    Returns:
        Rendered browse.html template with file list.

    Raises:
        404: If workspace doesn't exist.
    """
    user_root = get_user_root()
    if not user_root:
        abort(404)

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    # Build file list with metadata.
    files: List[Dict[str, Any]] = []
    for filename in ["original.wiki", "refs.json", "editable.wiki", "restored.wiki", "meta.json"]:
        file_path = workspace_path / filename
        if file_path.exists():
            stat = file_path.stat()
            files.append({
                "name": filename,
                "size": stat.st_size,
                "modified": stat.st_mtime
            })

    # Load metadata for display.
    meta_content = get_workspace_file(workspace_path, "meta.json")

    return render_template(
        "browse.html",
        slug=slug,
        files=files,
        meta=meta_content
    )


@app.route("/w/<slug>/file/<name>")
def view_file(slug: str, name: str) -> str:
    """
    View a specific file in the workspace.

    Displays the file content in a readable format. JSON files are
    pretty-printed for readability.

    Args:
        slug: The workspace identifier.
        name: The filename to view.

    Returns:
        Rendered view_file.html template with file content.

    Raises:
        404: If workspace or file doesn't exist.
    """
    user_root = get_user_root()
    if not user_root:
        abort(404)

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    # Get file content (whitelist enforced in get_workspace_file).
    content = get_workspace_file(workspace_path, name)
    if content is None:
        abort(404)

    return render_template(
        "view_file.html",
        slug=slug,
        filename=name,
        content=content
    )


@app.route("/w/<slug>/download/<name>")
def download_file(slug: str, name: str) -> Response:
    """
    Download a specific file from the workspace.

    Returns the file as an attachment with appropriate content type.

    Args:
        slug: The workspace identifier.
        name: The filename to download.

    Returns:
        Response with file content as attachment.

    Raises:
        404: If workspace or file doesn't exist.
    """
    user_root = get_user_root()
    if not user_root:
        abort(404)

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    content = get_workspace_file(workspace_path, name)
    if content is None:
        abort(404)

    # Determine content type based on file extension.
    if name.endswith(".json"):
        content_type = "application/json"
    else:
        content_type = "text/plain"

    # Safely encode filename for Content-Disposition header.
    # Uses RFC 5987 encoding for non-ASCII filenames.
    safe_filename = quote(name, safe="")

    return Response(
        content,
        mimetype=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
    )


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    # Enable debug mode if FLASK_DEBUG=1 or "debug" in command line args.
    debug = app.config["DEBUG"] or "debug" in sys.argv

    # Run the development server.
    # host="0.0.0.0" makes it accessible from other machines on the network.
    # This is suitable for internal tools but NOT for production.
    app.run(debug=debug, host="0.0.0.0", port=5000)
