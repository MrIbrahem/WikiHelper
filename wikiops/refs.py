# wikiops/refs.py
# Extract and restore <ref> tags using wikitextparser (wtp)

from __future__ import annotations

import re
from typing import Dict, Tuple

import wikitextparser as wtp


PLACEHOLDER_PATTERN = re.compile(r"\[(ref\d+)\]")


def extract_refs_from_text(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Extract all <ref> tags from WikiText and replace with placeholders.

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
    replacements = []

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


def restore_refs_in_text(text: str, refs_map: Dict[str, str]) -> str:
    """
    Restore placeholders like [ref1] back to their original <ref ...>...</ref> tags.

    Args:
        text: Text containing [refN] placeholders
        refs_map: Dictionary mapping refN keys to original ref content

    Returns:
        Text with placeholders replaced by original ref tags
    """
    def _repl(match: re.Match) -> str:
        key = match.group(1)
        return refs_map.get(key, match.group(0))  # keep placeholder if missing

    return PLACEHOLDER_PATTERN.sub(_repl, text)
