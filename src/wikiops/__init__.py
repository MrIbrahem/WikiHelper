"""
wikiops - Wiki Operations Package

This package provides core functionality for WikiHelper's WikiText processing:

Modules:
    refs: Reference extraction and restoration using wikitextparser
    storage: Workspace filesystem operations with security validation
    models: Data models for workspace metadata
    utils: Utility functions (slugification, text fixes)
    wikipedia: Wikipedia API integration for article import

Typical Usage:
    >>> from wikiops.refs import extract_refs_from_text, restore_refs_in_text
    >>> from wikiops.storage import create_workspace, update_workspace
    >>>
    >>> # Extract references from WikiText
    >>> text = 'Article<ref>Citation</ref>'
    >>> editable, refs = extract_refs_from_text(text)
    >>>
    >>> # Restore references after editing
    >>> restored = restore_refs_in_text(editable, refs)

Security:
    All user-provided paths are validated through safe_workspace_path()
    to prevent directory traversal attacks.
"""

from __future__ import annotations

# Re-export commonly used functions for convenience.
from .refs import extract_refs_from_text, restore_refs_in_text, PLACEHOLDER_PATTERN
from .storage import (
    create_workspace,
    update_workspace,
    list_workspaces,
    safe_workspace_path,
    get_workspace_file,
    read_text,
    read_json,
    atomic_write,
)
from .utils import slugify_title, fix_some_issues
from .models import Workspace, WorkspaceMeta

__all__ = [
    # refs module
    "extract_refs_from_text",
    "restore_refs_in_text",
    "PLACEHOLDER_PATTERN",
    # storage module
    "create_workspace",
    "update_workspace",
    "list_workspaces",
    "safe_workspace_path",
    "get_workspace_file",
    "read_text",
    "read_json",
    "atomic_write",
    # utils module
    "slugify_title",
    "fix_some_issues",
    # models module
    "Workspace",
    "WorkspaceMeta",
]

__version__ = "1.0.0"
