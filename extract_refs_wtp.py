# extract_refs_wtp.py
# Extract <ref> tags using wikitextparser (wtp), save to file_name.refs.json,
# and replace them with placeholders [ref1], [ref2], ...

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import wikitextparser as wtp


def extract_refs_from_text(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Returns:
      - modified_text: text with <ref ...>...</ref> and <ref .../> replaced by [refN]
      - refs_map: {"ref1": "<ref ...>...</ref>", ...} stored as exact original slices
    """
    parsed = wtp.parse(text)

    # Get all tags and filter only <ref ...>
    tags = [t for t in parsed.get_tags() if (t.name or "").lower() == "ref"]

    # Sort by position to keep stable numbering
    tags.sort(key=lambda t: t.span[0])

    refs_map: Dict[str, str] = {}
    replacements: List[Tuple[int, int, str]] = []

    for i, tag in enumerate(tags, start=1):
        key = f"ref{i}"
        start, end = tag.span

        # Store the exact original substring (preserves formatting exactly)
        refs_map[key] = text[start:end]

        # Plan replacement with placeholder
        replacements.append((start, end, f"[{key}]"))

    # Apply replacements from end to start so indices remain valid
    modified = text
    for start, end, placeholder in reversed(replacements):
        modified = modified[:start] + placeholder + modified[end:]

    return modified, refs_map
