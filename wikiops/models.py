# wikiops/models.py
# Optional dataclasses for workspace metadata

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class WorkspaceMeta:
    """Metadata for a workspace."""
    title_original: str
    slug: str
    created_at: str
    updated_at: str
    refs_count: int

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceMeta":
        return cls(
            title_original=data.get("title_original", ""),
            slug=data.get("slug", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            refs_count=data.get("refs_count", 0)
        )

    def to_dict(self) -> dict:
        return {
            "title_original": self.title_original,
            "slug": self.slug,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "refs_count": self.refs_count
        }


@dataclass
class Workspace:
    """Represents a workspace."""
    slug: str
    path: Path
    meta: Optional[WorkspaceMeta] = None

    @property
    def original_path(self) -> Path:
        return self.path / "original.wiki"

    @property
    def refs_path(self) -> Path:
        return self.path / "refs.json"

    @property
    def editable_path(self) -> Path:
        return self.path / "editable.wiki"

    @property
    def restored_path(self) -> Path:
        return self.path / "restored.wiki"

    @property
    def meta_path(self) -> Path:
        return self.path / "meta.json"
