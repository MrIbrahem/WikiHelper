# wikiops/storage.py
# Filesystem operations, safe paths, slugify, atomic writes

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import unicodedata


def slugify_title(title: str) -> str:
    """
    Convert a title to a safe slug for use as a folder name.

    - Normalize Unicode to NFKD form
    - Convert to lowercase
    - Replace spaces and special characters with hyphens
    - Allow only alphanumeric, hyphen, and underscore
    - Remove consecutive hyphens
    - Strip leading/trailing hyphens
    """
    # Normalize Unicode characters
    normalized = unicodedata.normalize("NFKD", title)

    # Encode to ASCII, ignoring non-ASCII characters
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase
    lower = ascii_str.lower()

    # Replace any non-alphanumeric characters with hyphen
    slug = re.sub(r"[^a-z0-9]+", "-", lower)

    # Remove consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    return slug


def safe_workspace_path(root: Path, slug: str) -> Optional[Path]:
    """
    Validate and return a safe workspace path within root directory.

    Returns None if the path would escape the root directory or contains
    unsafe characters.
    """
    # Check for path traversal attempts
    if ".." in slug or "/" in slug or "\\" in slug:
        return None

    # Check for reserved names (Windows compatibility)
    reserved_names = {
        "con", "prn", "aux", "nul",
        "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
        "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
    }
    if slug.lower() in reserved_names:
        return None

    # Check slug is not empty
    if not slug:
        return None

    # Construct path
    workspace_path = root / slug

    # Resolve to absolute path and verify it's within root
    try:
        resolved = workspace_path.resolve()
        root_resolved = root.resolve()

        # Check the path is within root
        if not str(resolved).startswith(str(root_resolved) + os.sep) and resolved != root_resolved:
            # Allow if it's the root itself or a direct child
            if resolved.parent != root_resolved:
                return None

        return resolved
    except (OSError, ValueError):
        return None


def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """
    Write content to a file atomically using a temporary file.
    """
    # Create temp file in the same directory to ensure atomic rename
    dir_path = path.parent
    dir_path.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
        # Atomic rename
        os.replace(temp_path, path)
    except Exception:
        # Clean up temp file if something goes wrong
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def read_text(path: Path, encoding: str = "utf-8") -> str:
    """
    Read text content from a file.
    """
    return path.read_text(encoding=encoding)


def read_json(path: Path) -> dict:
    """
    Read JSON content from a file.
    """
    content = read_text(path)
    return json.loads(content)


def write_json(path: Path, data: dict) -> None:
    """
    Write JSON content to a file atomically.
    """
    content = json.dumps(data, ensure_ascii=False, indent=2)
    atomic_write(path, content)


def list_workspaces(root: Path) -> list:
    """
    List all workspaces in root directory, sorted by last modification time.

    Returns a list of dicts with workspace info.
    """
    workspaces = []

    if not root.exists():
        return workspaces

    for item in root.iterdir():
        if item.is_dir():
            meta_path = item / "meta.json"
            if meta_path.exists():
                try:
                    meta = read_json(meta_path)
                    workspaces.append({
                        "slug": item.name,
                        "title": meta.get("title_original", item.name),
                        "created_at": meta.get("created_at", ""),
                        "updated_at": meta.get("updated_at", ""),
                        "refs_count": meta.get("refs_count", 0),
                        "path": item
                    })
                except (json.JSONDecodeError, OSError):
                    # Skip invalid workspaces
                    pass

    # Sort by updated_at descending (most recent first)
    workspaces.sort(key=lambda w: w.get("updated_at", ""), reverse=True)

    return workspaces


def create_workspace(root: Path, title: str, wikitext: str) -> tuple:
    """
    Create a new workspace or return existing one.

    Returns:
        (slug, workspace_path, is_new) tuple
    """
    from .refs import extract_refs_from_text

    slug = slugify_title(title)
    if not slug:
        raise ValueError("Invalid title: cannot generate a safe slug")

    workspace_path = safe_workspace_path(root, slug)
    if workspace_path is None:
        raise ValueError("Invalid workspace path")

    # Check if workspace already exists
    original_path = workspace_path / "original.wiki"
    is_new = not original_path.exists()

    if is_new:
        # Create workspace directory
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Extract references
        editable_text, refs_map = extract_refs_from_text(wikitext)

        # Write original.wiki (immutable)
        atomic_write(original_path, wikitext)

        # Write refs.json (immutable)
        refs_path = workspace_path / "refs.json"
        write_json(refs_path, refs_map)

        # Write editable.wiki
        editable_path = workspace_path / "editable.wiki"
        atomic_write(editable_path, editable_text)

        # Write restored.wiki (initially same as original)
        restored_path = workspace_path / "restored.wiki"
        atomic_write(restored_path, wikitext)

        # Write meta.json
        now = datetime.utcnow().isoformat() + "Z"
        meta = {
            "title_original": title,
            "slug": slug,
            "created_at": now,
            "updated_at": now,
            "refs_count": len(refs_map)
        }
        meta_path = workspace_path / "meta.json"
        write_json(meta_path, meta)

    return slug, workspace_path, is_new


def update_workspace(workspace_path: Path, editable_content: str) -> str:
    """
    Update workspace's editable.wiki and generate restored.wiki.

    Returns the restored content.
    """
    from .refs import restore_refs_in_text

    # Read refs.json
    refs_path = workspace_path / "refs.json"
    refs_map = read_json(refs_path)

    # Update editable.wiki
    editable_path = workspace_path / "editable.wiki"
    atomic_write(editable_path, editable_content)

    # Restore references
    restored_content = restore_refs_in_text(editable_content, refs_map)

    # Write restored.wiki
    restored_path = workspace_path / "restored.wiki"
    atomic_write(restored_path, restored_content)

    # Update meta.json
    meta_path = workspace_path / "meta.json"
    if meta_path.exists():
        meta = read_json(meta_path)
        meta["updated_at"] = datetime.utcnow().isoformat() + "Z"
        write_json(meta_path, meta)

    return restored_content


def get_workspace_file(workspace_path: Path, filename: str) -> Optional[str]:
    """
    Get content of a specific file in the workspace.

    Only allows access to whitelisted files.
    """
    allowed_files = {
        "original.wiki",
        "refs.json",
        "editable.wiki",
        "restored.wiki",
        "meta.json"
    }

    if filename not in allowed_files:
        return None

    file_path = workspace_path / filename
    if not file_path.exists():
        return None

    return read_text(file_path)
