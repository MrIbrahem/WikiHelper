from __future__ import annotations

import re
import unicodedata


def fix_space_before_section(content: str) -> str:
    """
    Fix section headers that have space before the equal signs.
    """
    # ( ==Header==) to (==Header==)
    content = re.sub(r"^( +)(=+[^=]+=+)", r"\g<2>", content, flags=re.MULTILINE)

    return content


def fix_sections_space(content: str) -> str:
    """
    Fix section headers that lack spaces around the text.
    """
    # (==text==) to (== text ==)
    # (==text 2==) to (== text 2 ==)
    # (==text 2 ==) to (== text 2 ==)
    # (====text    2 ====) to (==== text    2 ====)
    # (===  text ! ===) to (=== text ! ===)
    content = re.sub(r"^(=+)([^\s=].*?[^\s=])(\1)$", r"\1 \2 \3", content, flags=re.MULTILINE)
    return content


def fix_some_issues(content: str) -> str:
    """
    Fix some common issues in the content before writing to file.
    """
    content = fix_space_before_section(content)
    content = fix_sections_space(content)

    return content


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
    slug = re.sub(r"[^a-z0-9_]+", "-", lower)

    # Remove consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    return slug
