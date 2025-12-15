
import re
import unicodedata


def fix_some_issues(content: str) -> str:
    """
    Fix some common issues in the content before writing to file.
    """
    # Normalize line endings to LF
    # any line start with space then = should be fixed to remove leading spaces
    content = re.sub(r"^( +)=", lambda m: "=" + m.group(1), content, flags=re.MULTILINE)

    # ==text== to == text ==
    content = re.sub(r"^(=+)([^\s=])(\1)$", r"\g<1> \g<2> \g<1>", content, flags=re.MULTILINE)

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
    slug = re.sub(r"[^a-z0-9]+", "-", lower)

    # Remove consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    return slug
