"""
wikiops/utils.py - Utility Functions Module

This module provides common utility functions used throughout the WikiHelper
application, including:
- Title slugification for safe filesystem operations
- WikiText section header formatting corrections

Security Note:
    The slugify_title function is security-critical as slugs are used as
    directory names. It strips all non-ASCII characters to prevent issues
    with filesystem encoding across different operating systems.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final


# Regex pattern to match non-alphanumeric characters (except underscore).
# Used for replacing unsafe characters with hyphens in slugs.
NON_ALPHANUMERIC_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9_]+")

# Regex pattern to match consecutive hyphens for consolidation.
CONSECUTIVE_HYPHEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"-+")


def fix_space_before_section(content: str) -> str:
    """
    Remove leading spaces before MediaWiki section headers.

    MediaWiki expects section headers to start at the beginning of a line.
    Leading spaces can cause the header to not be recognized as a section
    header and instead be rendered as preformatted text.

    This function handles cases like:
        "  ==Header==" -> "==Header=="

    Args:
        content: The WikiText content to fix.

    Returns:
        The content with leading spaces removed from section headers.

    Example:
        >>> fix_space_before_section("  ==Section==\\n   ==Subsection==")
        '==Section==\\n==Subsection=='
    """
    # Match lines that start with whitespace followed by one or more = characters
    # and content ending with matching = characters.
    # The replacement removes the leading whitespace while preserving the header.
    content = re.sub(
        r"^( +)(=+[^=]+=+)",
        r"\g<2>",  # Keep only the header, discard leading whitespace
        content,
        flags=re.MULTILINE
    )

    return content


def fix_sections_space(content: str) -> str:
    """
    Add required spaces around MediaWiki section header text.

    MediaWiki section headers require spaces between the equals signs and
    the header text for proper rendering:
        - "==text==" should become "== text =="
        - "===text===" should become "=== text ==="

    This function only modifies headers that lack spaces on BOTH sides.
    Headers that already have spaces on either side are left unchanged
    to avoid breaking intentionally different formatting.

    Args:
        content: The WikiText content to fix.

    Returns:
        The content with proper spacing in section headers.

    Example:
        >>> fix_sections_space("==Header==\\n=== Subsection===")
        '== Header ==\\n=== Subsection==='

    Note:
        This function is conservative - it only fixes headers where both
        the opening and closing equals signs directly touch the text.
        Headers with existing space on either side are preserved as-is.
    """
    # Match headers where:
    # - Opening equals are directly followed by non-whitespace, non-equals text
    # - Text ends with non-whitespace, non-equals followed by closing equals
    # The pattern captures: (opening =)(text)(closing =)
    content = re.sub(
        r"^(=+)([^\s=].*?[^\s=])(\1)$",
        r"\1 \2 \3",  # Add space around the text
        content,
        flags=re.MULTILINE
    )
    return content


def fix_some_issues(content: str) -> str:
    """
    Apply all WikiText formatting fixes to content.

    This is a convenience function that applies all registered fixes
    in the appropriate order. Currently includes:
    1. Removing leading spaces before section headers
    2. Adding spaces around section header text

    Args:
        content: The WikiText content to fix.

    Returns:
        The content with all formatting issues corrected.

    Note:
        The order of fixes matters: we first remove leading spaces,
        then add spaces around header text. This ensures consistent
        formatting regardless of the input state.
    """
    content = fix_space_before_section(content)
    content = fix_sections_space(content)

    return content


def slugify_title(title: str) -> str:
    """
    Convert a title to a safe filesystem slug.

    This function transforms an arbitrary title string into a safe,
    lowercase, ASCII-only string suitable for use as a directory or
    file name. The transformation is designed to be:
    - Safe: No path traversal characters (/, \\, ..)
    - Portable: Works across Windows, macOS, and Linux
    - Readable: Preserves word boundaries with hyphens

    Transformation Steps:
        1. Unicode NFKD normalization (decomposes accented characters)
        2. ASCII encoding (strips non-ASCII characters)
        3. Lowercase conversion
        4. Non-alphanumeric replacement with hyphens
        5. Consecutive hyphen consolidation
        6. Leading/trailing hyphen removal

    Args:
        title: The input title string. Can contain any Unicode characters.

    Returns:
        A safe slug string containing only lowercase alphanumeric
        characters, underscores, and hyphens. Returns an empty string
        if the title contains no ASCII characters.

    Security Note:
        This function is used to generate directory names from user input.
        The ASCII-only restriction prevents filesystem encoding issues
        and path traversal attacks.

    Example:
        >>> slugify_title("Hello World")
        'hello-world'
        >>> slugify_title("Café Müller")
        'cafe-muller'
        >>> slugify_title("عنوان عربي")  # Arabic text
        ''
        >>> slugify_title("Test---Multiple___Hyphens")
        'test-multiple___hyphens'

    Warning:
        Non-ASCII characters (Arabic, Chinese, etc.) are completely removed,
        which can result in empty strings for titles containing only
        non-ASCII characters. Callers should handle this case.
    """
    # Step 1: Normalize Unicode to NFKD form.
    # This decomposes characters like 'é' into 'e' + combining acute accent.
    # The combining marks will be stripped in the next step.
    normalized = unicodedata.normalize("NFKD", title)

    # Step 2: Encode to ASCII, ignoring non-ASCII characters.
    # This strips all combining marks and non-Latin characters.
    # For example: 'café' -> 'cafe', '日本語' -> ''
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")

    # Step 3: Convert to lowercase for consistency.
    lower = ascii_str.lower()

    # Step 4: Replace any non-alphanumeric characters (except underscore) with hyphen.
    # This converts spaces, punctuation, and special characters to word separators.
    slug = NON_ALPHANUMERIC_PATTERN.sub("-", lower)

    # Step 5: Consolidate consecutive hyphens into single hyphens.
    # This prevents ugly slugs like "hello---world".
    slug = CONSECUTIVE_HYPHEN_PATTERN.sub("-", slug)

    # Step 6: Strip leading and trailing hyphens.
    # These provide no value and look unclean in URLs/paths.
    slug = slug.strip("-")

    return slug
