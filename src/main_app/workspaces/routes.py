"""
workspaces/routes.py - Workspaces Blueprint Routes

Routes for workspace management.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import (
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.wrappers import Response as WerkzeugResponse

from main_app.workspaces import bp
from extensions import limiter
from wikiops.storage import (
    create_workspace,
    get_workspace_file,
    list_workspaces,
    read_json,
    read_text,
    safe_workspace_path,
    update_workspace,
)
from wikiops.wikipedia import fetch_wikipedia_article, validate_article_title

# Type alias for route return values
RouteResponse = str | Response | WerkzeugResponse


def _validate_username(username: str) -> bool:
    """
    Check whether a username is safe to use as a filesystem directory name.
    
    Parameters:
        username (str): Candidate username. Must be non-empty, must not contain "..", "/" or "\", and must not match reserved names (case-insensitive) such as "con", "prn", "aux", "nul", "com1"… "com9", or "lpt1"… "lpt9".
    
    Returns:
        bool: True if the username satisfies the rules above, False otherwise.
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
    Resolve and return the per-user workspace root directory for the current session user.
    
    This validates the session-stored username, ensures it is a safe directory name, verifies the resolved user path is contained within the configured WIKI_WORK_ROOT, and creates the directory if it does not exist.
    
    Returns:
        Path: The resolved user root directory.
        None: If there is no username in session, the username is invalid, path resolution fails, or the resolved user path is not contained within the configured root.
    """
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


@bp.route("/new", methods=["GET", "POST"])
def new_workspace() -> RouteResponse:
    """Create a new workspace from pasted or uploaded WikiText."""
    user_root = _get_user_root()
    if not user_root:
        return redirect(url_for("main.set_user"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        wikitext = request.form.get("wikitext", "")

        # Check for file upload
        file = request.files.get("wikitext_file")
        if file and file.filename:
            try:
                wikitext = file.read().decode("utf-8")
            except UnicodeDecodeError:
                flash("Uploaded file must be UTF-8 encoded text.", "error")
                return render_template("new.html", title=title, wikitext=wikitext)

        # Validate title
        if not title:
            flash("Title is required.", "error")
            return render_template("new.html", title=title, wikitext=wikitext)

        max_title = current_app.config.get("MAX_TITLE_LENGTH", 120)
        if len(title) > max_title:
            flash(f"Title must be {max_title} characters or less.", "error")
            return render_template("new.html", title=title, wikitext=wikitext)

        # Validate wikitext content
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

            return redirect(url_for("workspaces.edit_workspace", slug=slug))

        except ValueError as e:
            flash(str(e), "error")
            return render_template("new.html", title=title, wikitext=wikitext)

    return render_template("new.html")


@bp.route("/import-wikipedia", methods=["GET", "POST"])
@limiter.limit("10 per minute")  # Prevent Wikipedia API abuse
def import_wikipedia() -> RouteResponse:
    """Import an article from English Wikipedia to create a new workspace."""
    user_root = _get_user_root()
    if not user_root:
        return redirect(url_for("main.set_user"))

    if request.method == "POST":
        article_title = request.form.get("article_title", "").strip()

        # Validate article title format
        is_valid, error_msg = validate_article_title(article_title)
        if not is_valid:
            flash(error_msg, "error")
            return render_template("import_wikipedia.html", article_title=article_title)

        # Fetch article content
        wikitext, error = fetch_wikipedia_article(article_title)

        if error:
            flash(error, "error")
            return render_template("import_wikipedia.html", article_title=article_title)

        if not wikitext:
            flash("Retrieved empty content from Wikipedia.", "error")
            return render_template("import_wikipedia.html", article_title=article_title)

        # Create workspace
        try:
            slug, _, is_new = create_workspace(user_root, article_title, wikitext)

            if is_new:
                flash(f"Successfully imported '{article_title}' from Wikipedia.", "success")
            else:
                flash(f"Workspace '{slug}' already exists. Redirecting to edit.", "info")

            return redirect(url_for("workspaces.edit_workspace", slug=slug))

        except ValueError as e:
            flash(str(e), "error")
            return render_template("import_wikipedia.html", article_title=article_title)

    return render_template("import_wikipedia.html")


@bp.route("/<slug>/edit", methods=["GET"])
def edit_workspace(slug: str) -> str:
    """
    Render the edit page for a workspace by loading its editable content, restored content, and metadata.
    
    Loads editable.wiki, meta.json (if present), and restored.wiki (if present) for the workspace identified by `slug`, then renders the "edit.html" template with those values.
    
    Parameters:
        slug (str): Workspace identifier (slug).
    
    Returns:
        str: Rendered HTML for the workspace edit page.
    """
    user_root = _get_user_root()
    if not user_root:
        abort(404)

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    editable_path = workspace_path / "editable.wiki"
    if not editable_path.exists():
        abort(404)

    editable_content = read_text(editable_path)

    meta_path = workspace_path / "meta.json"
    meta = read_json(meta_path) if meta_path.exists() else {}

    restored_path = workspace_path / "restored.wiki"
    restored_content = read_text(restored_path) if restored_path.exists() else ""

    return render_template(
        "edit.html",
        slug=slug,
        editable_content=editable_content,
        restored_content=restored_content,
        meta=meta
    )


@bp.route("/<slug>/save", methods=["POST"])
def save_workspace(slug: str) -> RouteResponse:
    """
    Save the editable content for a workspace and regenerate its restored file.
    
    Saves the provided editable.wiki content for the workspace identified by `slug`, updates restoration data, flashes a success message and redirects to the restored.wiki view on success; on failure flashes an error message and redirects back to the edit view.
    
    Parameters:
        slug (str): Workspace slug used to locate the workspace directory.
    
    Returns:
        A redirect response to the workspace's restored.wiki view on success, or a redirect response to the workspace edit view on failure.
    """
    user_root = _get_user_root()
    if not user_root:
        abort(404)

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    editable_content = request.form.get("editable_content", "")
    status = request.form.get("status")

    try:
        update_workspace(workspace_path, editable_content, status=status)
        flash("Workspace updated and references restored.", "success")
        return redirect(url_for("workspaces.view_file", slug=slug, name="restored.wiki"))
    except Exception as e:
        flash(f"Error updating workspace: {e}", "error")
        return redirect(url_for("workspaces.edit_workspace", slug=slug))


@bp.route("/<slug>/browse")
def browse_workspace(slug: str) -> str:
    """
    Render the workspace file browser for the given workspace slug.
    
    Lists present workspace files (original.wiki, refs.json, editable.wiki, restored.wiki, meta.json) with their sizes and last-modified times and includes the workspace's meta content in the rendered page.
    
    Parameters:
        slug (str): Workspace slug identifier.
    
    Returns:
        str: Rendered HTML for the browse view.
    
    Raises:
        404: If the user root cannot be resolved or the workspace does not exist.
    """
    user_root = _get_user_root()
    if not user_root:
        abort(404)

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

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

    meta_content = get_workspace_file(workspace_path, "meta.json")

    return render_template(
        "browse.html",
        slug=slug,
        files=files,
        meta=meta_content
    )


@bp.route("/<slug>/file/<name>")
def view_file(slug: str, name: str) -> str:
    """
    Render an HTML page showing the contents of a named file from the workspace.
    
    Aborts with a 404 response when the user root is unavailable, the workspace does not exist, or the named file is not found.
    
    Returns:
        Rendered HTML for the file view page.
    """
    user_root = _get_user_root()
    if not user_root:
        abort(404)

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    content = get_workspace_file(workspace_path, name)
    if content is None:
        abort(404)

    return render_template(
        "view_file.html",
        slug=slug,
        filename=name,
        content=content
    )


@bp.route("/<slug>/download/<name>")
def download_file(slug: str, name: str) -> Response:
    """
    Send a workspace file to the client as a downloadable attachment.
    
    Parameters:
        slug (str): Workspace slug identifying the workspace directory.
        name (str): Name of the file inside the workspace to download.
    
    Returns:
        Response: A Flask Response containing the file content with a Content-Disposition
        attachment header. The response uses "application/json" for filenames ending in
        ".json" and "text/plain" for other files.
    
    Notes:
        Returns a 404 response if the user is not resolved, the workspace does not exist,
        or the named file is not found.
    """
    from urllib.parse import quote

    user_root = _get_user_root()
    if not user_root:
        abort(404)

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    content = get_workspace_file(workspace_path, name)
    if content is None:
        abort(404)

    if name.endswith(".json"):
        content_type = "application/json"
    else:
        content_type = "text/plain"

    safe_filename = quote(name, safe="")

    return Response(
        content,
        mimetype=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
    )