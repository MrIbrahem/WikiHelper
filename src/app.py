# app.py
# Flask application for Wiki Ref Workspace Manager

from urllib.parse import quote
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, abort, Response, jsonify, make_response
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
from wikiops.wikipedia import fetch_wikipedia_article, validate_article_title
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


def get_user_root():
    """Get the root directory for the current user based on cookies."""
    username = request.cookies.get("username")
    if not username:
        return None
    user_root = root / username
    user_root.mkdir(parents=True, exist_ok=True)
    return user_root


@app.before_request
def check_user():
    """Redirect to set_user if username cookie is missing, except for set_user and static files."""
    if request.endpoint in ["set_user", "static"]:
        return

    if not request.cookies.get("username"):
        return redirect(url_for("set_user", next=request.url))


@app.route("/set_user", methods=["GET", "POST"])
def set_user():
    """Set the username cookie."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            flash("Username is required.", "error")
            return render_template("set_user.html")

        # Basic validation for username to be used as folder name
        from wikiops.utils import slugify_title
        safe_username = slugify_title(username)
        if not safe_username:
            flash("Invalid username.", "error")
            return render_template("set_user.html")

        next_url = request.args.get("next") or url_for("index")
        resp = make_response(redirect(next_url))
        resp.set_cookie("username", safe_username, max_age=30*24*60*60) # 30 days
        return resp

    return render_template("set_user.html")


@app.route("/logout")
def logout():
    """Clear the username cookie."""
    resp = make_response(redirect(url_for("set_user")))
    resp.delete_cookie("username")
    flash("Logged out successfully.", "info")
    return resp


@app.errorhandler(RequestEntityTooLarge)
def handle_large_request(e):
    return jsonify({
        "error": "Request too large",
        "message": "Uploaded data exceeds the allowed size limit"
    }), 413


@app.route("/")
def index():
    """Dashboard - list all workspaces."""
    user_root = get_user_root()
    if not user_root:
        return redirect(url_for("set_user"))

    all_workspaces = list_workspaces(user_root)
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
    user_root = get_user_root()
    if not user_root:
        return redirect(url_for("set_user"))

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
            slug, workspace_path, is_new = create_workspace(user_root, title, wikitext)

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
def import_wikipedia():
    """Import an article from English Wikipedia to create a new workspace."""
    user_root = get_user_root()
    if not user_root:
        return redirect(url_for("set_user"))

    if request.method == "POST":
        article_title = request.form.get("article_title", "").strip()

        # Validate article title
        is_valid, error_msg = validate_article_title(article_title)
        if not is_valid:
            flash(error_msg, "error")
            return render_template("import_wikipedia.html", article_title=article_title)

        # Fetch article content from Wikipedia
        flash(f"Fetching article '{article_title}' from Wikipedia...", "info")
        wikitext, error = fetch_wikipedia_article(article_title)

        if error:
            flash(error, "error")
            return render_template("import_wikipedia.html", article_title=article_title)

        if not wikitext:
            flash("Retrieved empty content from Wikipedia.", "error")
            return render_template("import_wikipedia.html", article_title=article_title)

        # Create workspace with the fetched content
        try:
            slug, workspace_path, is_new = create_workspace(user_root, article_title, wikitext)

            if is_new:
                flash(f"Successfully imported '{article_title}' from Wikipedia.", "success")
            else:
                flash(f"Workspace '{slug}' already exists. Redirecting to edit.", "info")

            return redirect(url_for("edit_workspace", slug=slug))

        except ValueError as e:
            flash(str(e), "error")
            return render_template("import_wikipedia.html", article_title=article_title)

    return render_template("import_wikipedia.html")


@app.route("/w/<slug>/edit", methods=["GET", "POST"])
def edit_workspace(slug: str):
    """Edit workspace's editable.wiki."""
    user_root = get_user_root()
    if not user_root:
        return redirect(url_for("set_user"))

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    editable_path = workspace_path / "editable.wiki"

    if not editable_path.exists():
        abort(404)

    editable_content = read_text(editable_path)

    # Load meta for display
    meta_path = workspace_path / "meta.json"
    meta = read_json(meta_path) if meta_path.exists() else {}

    # Read restored content for preview
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
def save_workspace(slug: str):
    """Save workspace's editable.wiki and restore references."""
    user_root = get_user_root()
    if not user_root:
        return redirect(url_for("set_user"))

    workspace_path = safe_workspace_path(user_root, slug)
    if workspace_path is None or not workspace_path.exists():
        abort(404)

    editable_content = request.form.get("editable_content", "")
    status = request.form.get("status")

    try:
        update_workspace(workspace_path, editable_content, status=status)
        flash("Workspace updated and references restored.", "success")
        return redirect(url_for("view_file", slug=slug, name="restored.wiki"))
    except Exception as e:
        flash(f"Error updating workspace: {e}", "error")
        return redirect(url_for("edit_workspace", slug=slug))


@app.route("/w/<slug>/browse")
def browse_workspace(slug: str):
    """Browse workspace files."""
    user_root = get_user_root()
    if not user_root:
        return redirect(url_for("set_user"))

    workspace_path = safe_workspace_path(user_root, slug)
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
    user_root = get_user_root()
    if not user_root:
        return redirect(url_for("set_user"))

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


@app.route("/w/<slug>/download/<name>")
def download_file(slug: str, name: str):
    """Download a specific file from the workspace."""
    user_root = get_user_root()
    if not user_root:
        return redirect(url_for("set_user"))

    workspace_path = safe_workspace_path(user_root, slug)
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
