# app.py
# Flask application for Wiki Ref Workspace Manager

from urllib.parse import quote
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, abort, Response, jsonify
from flask_wtf.csrf import CSRFProtect

from werkzeug.exceptions import RequestEntityTooLarge
from wikiops.storage import (
    list_workspaces,
    create_workspace,
    update_workspace,
    safe_workspace_path,
    read_text,
    read_json,
    get_workspace_file
)
from config import Config


# def create_app(config_class=Config):
"""Application factory."""
app = Flask(__name__)
app.config.from_object(Config)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Ensure workspace root exists
root = app.config["WIKI_WORK_ROOT"]
root.mkdir(parents=True, exist_ok=True)


@app.errorhandler(RequestEntityTooLarge)
def handle_large_request(e):
    return jsonify({
        "error": "Request too large",
        "message": "Uploaded data exceeds the allowed size limit"
    }), 413


@app.route("/")
def index():
    """Dashboard - list all workspaces."""
    all_workspaces = list_workspaces(root)
    active_workspaces = [ws for ws in all_workspaces if ws.get("status") != "done"]
    done_workspaces = [ws for ws in all_workspaces if ws.get("status") == "done"]
    return render_template(
        "index.html",
        active_workspaces=active_workspaces,
        done_workspaces=done_workspaces
    )


@app.route("/new", methods=["GET", "POST"])
def new_workspace():
    """Create a new workspace."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        wikitext = request.form.get("wikitext", "")

        # Check if a file was uploaded
        file = request.files.get('wikitext_file')
        if file and file.filename:
            try:
                wikitext = file.read().decode('utf-8')
            except UnicodeDecodeError:
                flash("Uploaded file must be UTF-8 encoded text.", "error")
                return render_template("new.html", title=title, wikitext=wikitext)

        # Validate title
        if not title:
            flash("Title is required.", "error")
            return render_template("new.html", title=title, wikitext=wikitext)

        if len(title) > app.config.get("MAX_TITLE_LENGTH", 120):
            flash(f"Title must be {app.config.get('MAX_TITLE_LENGTH', 120)} characters or less.", "error")
            return render_template("new.html", title=title, wikitext=wikitext)

        # Validate wikitext
        if not wikitext:
            if file and file.filename:
                flash("Uploaded file is empty or does not contain valid text.", "error")
            else:
                flash("WikiText content is required.", "error")
            return render_template("new.html", title=title, wikitext=wikitext)

        try:
            slug, workspace_path, is_new = create_workspace(root, title, wikitext)

            if is_new:
                flash(f"Workspace '{slug}' created successfully.", "success")
            else:
                flash(f"Workspace '{slug}' already exists. Redirecting to edit.", "info")

            return redirect(url_for("edit_workspace", slug=slug))

        except ValueError as e:
            flash(str(e), "error")
            return render_template("new.html", title=title, wikitext=wikitext)

    return render_template("new.html")


@app.route("/w/<slug>/edit", methods=["GET", "POST"])
def edit_workspace(slug: str):
    """Edit workspace's editable.wiki."""
    workspace_path = safe_workspace_path(root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    editable_path = workspace_path / "editable.wiki"

    if not editable_path.exists():
        abort(404)

    restored_content = ""
    if request.method == "POST":
        editable_content = request.form.get("editable_content", "")
        status = request.form.get("status")

        try:
            restored_content = update_workspace(workspace_path, editable_content, status=status)
            flash("Workspace updated and references restored.", "success")
        except Exception as e:
            flash(f"Error updating workspace: {e}", "error")
            editable_content = read_text(editable_path)
    else:
        editable_content = read_text(editable_path)

    # Load meta for display
    meta_path = workspace_path / "meta.json"
    meta = read_json(meta_path) if meta_path.exists() else {}

    return render_template(
        "edit.html",
        slug=slug,
        editable_content=editable_content,
        restored_content=restored_content,
        meta=meta
    )


@app.route("/w/<slug>/browse")
def browse_workspace(slug: str):
    """Browse workspace files."""
    workspace_path = safe_workspace_path(root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    # List available files
    files = []
    for filename in ["original.wiki", "refs.json", "editable.wiki", "restored.wiki", "meta.json"]:
        file_path = workspace_path / filename
        if file_path.exists():
            files.append({
                "name": filename,
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime
            })

    # Load meta for display
    meta_content = get_workspace_file(workspace_path, "meta.json")

    return render_template(
        "browse.html",
        slug=slug,
        files=files,
        meta=meta_content
    )


@app.route("/w/<slug>/file/<name>")
def view_file(slug: str, name: str):
    """View a specific file in the workspace."""
    workspace_path = safe_workspace_path(root, slug)
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


@app.route("/w/<slug>/download/<name>")
def download_file(slug: str, name: str):
    """Download a specific file from the workspace."""
    workspace_path = safe_workspace_path(root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    content = get_workspace_file(workspace_path, name)
    if content is None:
        abort(404)

    # Determine content type
    if name.endswith(".json"):
        content_type = "application/json"
    else:
        content_type = "text/plain"

    # Safely encode the filename for Content-Disposition header
    safe_filename = quote(name, safe="")
    return Response(
        content,
        mimetype=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
    )


if __name__ == "__main__":
    debug = app.config["DEBUG"] or "debug" in sys.argv
    app.run(debug=debug, host="0.0.0.0", port=5000)
