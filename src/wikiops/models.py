"""
wikiops/models.py - Data Models Module

This module defines dataclasses for representing workspace metadata and
workspace entities within the WikiHelper application.

Design Decisions:
    - Dataclasses are used for automatic __init__, __repr__, and __eq__ generation
    - Optional fields use Optional type hints with None defaults
    - Property methods provide convenient access to common file paths

Usage:
    These models are primarily used for type-safe data transfer and
    documentation purposes. The actual storage is handled by storage.py
    which reads/writes JSON files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class WorkspaceMeta:
    """
    Metadata for a workspace.

    This dataclass represents the contents of a workspace's meta.json file.
    It tracks the workspace's identity, creation time, and reference count.

    Attributes:
        title_original: The user-provided title before slugification.
                        May contain Unicode characters and special characters.
        slug: The filesystem-safe directory name derived from the title.
              Contains only lowercase ASCII alphanumeric, hyphens, and underscores.
        created_at: ISO 8601 timestamp of workspace creation (e.g., "2024-01-15T10:30:00Z").
        updated_at: ISO 8601 timestamp of last modification.
        refs_count: The number of <ref> tags found in the original WikiText.
        status: The current workspace status. Common values:
                - "processing": Workspace is being actively edited
                - "done": Workspace editing is complete

    Example:
        >>> meta = WorkspaceMeta(
        ...     title_original="My Article",
        ...     slug="my-article",
        ...     created_at="2024-01-15T10:30:00Z",
        ...     updated_at="2024-01-15T10:30:00Z",
        ...     refs_count=5,
        ...     status="processing"
        ... )
        >>> meta.refs_count
        5
    """

    title_original: str
    slug: str
    created_at: str
    updated_at: str
    refs_count: int
    status: str = "processing"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkspaceMeta:
        """
        Create a WorkspaceMeta instance from a dictionary.

        This factory method is used to deserialize metadata loaded from
        a meta.json file. Missing keys use sensible defaults.

        Args:
            data: A dictionary containing workspace metadata keys.
                  Typically loaded from JSON via json.load().

        Returns:
            A new WorkspaceMeta instance populated from the dictionary.

        Example:
            >>> data = {"title_original": "Test", "slug": "test"}
            >>> meta = WorkspaceMeta.from_dict(data)
            >>> meta.title_original
            'Test'
            >>> meta.refs_count  # Default value
            0
        """
        return cls(
            title_original=data.get("title_original", ""),
            slug=data.get("slug", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            refs_count=data.get("refs_count", 0),
            status=data.get("status", "processing")
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the WorkspaceMeta instance to a dictionary.

        This method serializes the metadata for writing to meta.json.
        All fields are included in the output.

        Returns:
            A dictionary suitable for JSON serialization.

        Example:
            >>> meta = WorkspaceMeta("Test", "test", "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z", 3)
            >>> meta.to_dict()
            {'title_original': 'Test', 'slug': 'test', 'created_at': '2024-01-01T00:00:00Z', 'updated_at': '2024-01-01T00:00:00Z', 'refs_count': 3, 'status': 'processing'}
        """
        return {
            "title_original": self.title_original,
            "slug": self.slug,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "refs_count": self.refs_count,
            "status": self.status
        }


@dataclass
class Workspace:
    """
    Represents a complete workspace with its files and metadata.

    This dataclass provides a unified interface for accessing workspace
    components. It combines the workspace path with optional metadata
    and provides property methods for common file paths.

    Attributes:
        slug: The workspace directory name (filesystem-safe identifier).
        path: The absolute path to the workspace directory.
        meta: Optional WorkspaceMeta instance. May be None if metadata
              hasn't been loaded yet or is corrupted.

    Properties:
        original_path: Path to the immutable original WikiText file.
        refs_path: Path to the immutable reference map JSON file.
        editable_path: Path to the user-editable WikiText file.
        restored_path: Path to the auto-generated restored WikiText file.
        meta_path: Path to the workspace metadata JSON file.

    Example:
        >>> from pathlib import Path
        >>> ws = Workspace(slug="my-article", path=Path("/data/my-article"))
        >>> ws.editable_path
        PosixPath('/data/my-article/editable.wiki')
    """

    slug: str
    path: Path
    meta: Optional[WorkspaceMeta] = None

    @property
    def original_path(self) -> Path:
        """
        Get the path to the original.wiki file.

        This file contains the immutable original WikiText as submitted
        by the user. It should never be modified after creation.

        Returns:
            Path object pointing to original.wiki in the workspace directory.
        """
        return self.path / "original.wiki"

    @property
    def refs_path(self) -> Path:
        """
        Get the path to the refs.json file.

        This file contains the immutable reference map extracted from
        the original WikiText. It maps placeholder keys to original
        <ref> tag content.

        Returns:
            Path object pointing to refs.json in the workspace directory.
        """
        return self.path / "refs.json"

    @property
    def editable_path(self) -> Path:
        """
        Get the path to the editable.wiki file.

        This file contains the user-editable WikiText with references
        replaced by [refN] placeholders. Users modify this file and
        save to regenerate restored.wiki.

        Returns:
            Path object pointing to editable.wiki in the workspace directory.
        """
        return self.path / "editable.wiki"

    @property
    def restored_path(self) -> Path:
        """
        Get the path to the restored.wiki file.

        This file contains the auto-generated WikiText with references
        restored from the user's edits. It is regenerated each time
        the user saves their changes.

        Returns:
            Path object pointing to restored.wiki in the workspace directory.
        """
        return self.path / "restored.wiki"

    @property
    def meta_path(self) -> Path:
        """
        Get the path to the meta.json file.

        This file contains workspace metadata including title, timestamps,
        reference count, and status.

        Returns:
            Path object pointing to meta.json in the workspace directory.
        """
        return self.path / "meta.json"
