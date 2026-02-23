"""
wikiops/refs.py - Reference Extraction and Restoration Module

This module provides the core functionality for extracting <ref> tags from WikiText
and restoring them after user editing. It uses the wikitextparser library for
robust HTML tag parsing within WikiText documents.

Design Decisions:
    - Placeholder format: [refN] where N is a sequential integer (1-indexed)
    - Original ref content is stored as exact substring slices to preserve formatting
    - Replacements during extraction are applied in reverse order to maintain index validity
    - Missing placeholders during restoration are preserved as-is (not stripped)

Thread Safety:
    This module is stateless and thread-safe. All functions are pure.

Example:
    >>> from wikiops.refs import extract_refs_from_text, restore_refs_in_text
    >>> text = 'Hello<ref>World</ref>'
    >>> editable, refs = extract_refs_from_text(text)
    >>> editable
    'Hello[ref1]'
    >>> restore_refs_in_text(editable, refs)
    'Hello<ref>World</ref>'
"""

from __future__ import annotations

import re
from typing import Dict, Final, List, Tuple

import wikitextparser as wtp


# Compiled regex pattern for matching [refN] placeholders during restoration.
# Uses word boundary-like matching via digit requirement to avoid partial matches.
PLACEHOLDER_PATTERN: Final[re.Pattern[str]] = re.compile(r"\[(ref\d+)\]")

# Type alias for the reference map structure
RefsMap = Dict[str, str]


def extract_refs_from_text(text: str) -> Tuple[str, RefsMap]:
    """
    Extract all <ref> tags from WikiText and replace them with numbered placeholders.

    This function parses WikiText to identify all reference tags, including:
    - Standard refs: <ref>citation text</ref>
    - Named refs: <ref name="source">citation text</ref>
    - Self-closing refs: <ref name="source" />

    The function preserves the exact original content of each ref tag, including
    all whitespace, attributes, and formatting.

    Args:
        text: The raw WikiText content containing <ref> tags. Must be a valid
              string; empty strings are handled gracefully.

    Returns:
        A tuple containing:
            - modified_text: The input text with all <ref> tags replaced by
              placeholders like [ref1], [ref2], etc.
            - refs_map: A dictionary mapping placeholder keys to their original
              ref tag content. Keys are strings like "ref1", "ref2", etc.

    Raises:
        No exceptions are raised; malformed or unclosed refs are simply ignored
        by the underlying wikitextparser library.

    Note:
        - Refs are numbered by their position in the source text (stable ordering)
        - Empty ref tags (<ref></ref>) are still extracted and replaced
        - The original text is preserved exactly via substring slicing

    Example:
        >>> text = 'A<ref>First</ref>B<ref name="x"/>C'
        >>> modified, refs = extract_refs_from_text(text)
        >>> modified
        'A[ref1]B[ref2]C'
        >>> refs
        {'ref1': '<ref>First</ref>', 'ref2': '<ref name="x"/>'}
    """
    # Parse the WikiText into an AST-like structure using wikitextparser.
    # This handles complex WikiText features like templates, links, and HTML tags.
    parsed = wtp.parse(text)

    # Get all HTML tags and filter to only <ref> tags (case-insensitive).
    # wikitextparser identifies tags by their name attribute.
    tags = [t for t in parsed.get_tags() if (t.name or "").lower() == "ref"]

    # Sort tags by their start position to ensure stable, sequential numbering.
    # This guarantees that ref1 is always the first ref in the document.
    tags.sort(key=lambda t: t.span[0])

    refs_map: RefsMap = {}
    # List of (start, end, placeholder) tuples for batch replacement.
    # Stored as list to apply in reverse order later.
    replacements: List[Tuple[int, int, str]] = []

    for i, tag in enumerate(tags, start=1):
        key = f"ref{i}"
        start, end = tag.span

        # Store the exact original substring from the source text.
        # Using text[start:end] preserves all formatting, whitespace, and attributes
        # exactly as they appeared in the original document.
        refs_map[key] = text[start:end]

        # Queue this replacement for later application.
        replacements.append((start, end, f"[{key}]"))

    # Apply replacements from end to start (reverse order).
    # This is critical: if we replaced from start, each replacement would
    # shift all subsequent indices, requiring index recalculation.
    # By going backwards, earlier indices remain valid.
    modified = text
    for start, end, placeholder in reversed(replacements):
        modified = modified[:start] + placeholder + modified[end:]

    return modified, refs_map


def restore_refs_in_text(text: str, refs_map: RefsMap) -> str:
    """
    Restore placeholder references back to their original <ref> tag content.

    This function scans the input text for [refN] placeholders and replaces
    each one with the corresponding original ref tag content from the refs_map.
    Placeholders not found in the map are preserved as-is.

    Args:
        text: The edited text containing [refN] placeholders. This is typically
              the output of extract_refs_from_text after user modifications.
        refs_map: A dictionary mapping placeholder keys (e.g., "ref1") to their
                  original ref tag content. Usually comes from a prior call to
                  extract_refs_from_text.

    Returns:
        The text with all recognized placeholders replaced by their original
        ref tag content. Unrecognized placeholders (not in refs_map) are left
        unchanged.

    Example:
        >>> text = 'Hello[ref1] and [ref2]!'
        >>> refs = {'ref1': '<ref>World</ref>', 'ref2': '<ref name="x">X</ref>'}
        >>> restore_refs_in_text(text, refs)
        'Hello<ref>World</ref> and <ref name="x">X</ref>!'

        >>> # Missing keys are preserved
        >>> restore_refs_in_text('[ref99]', {'ref1': '<ref>X</ref>'})
        '[ref99]'
    """
    def _repl(match: re.Match[str]) -> str:
        """Replacement function called for each regex match."""
        key = match.group(1)  # Extract the refN key from the match
        # Return the original ref if found, otherwise keep the placeholder.
        # This graceful handling allows users to manually add new refs.
        return refs_map.get(key, match.group(0))

    return PLACEHOLDER_PATTERN.sub(_repl, text)
