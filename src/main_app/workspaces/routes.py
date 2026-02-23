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
    """Validate a username for use as a directory name."""
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
    """Get the root directory for the current user."""
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
    """Edit workspace's editable.wiki content."""
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
    """Save workspace's editable.wiki and regenerate restored.wiki."""
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
    """Browse workspace files."""
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
    """View a specific file in the workspace."""
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
    """Download a specific file from the workspace."""
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
