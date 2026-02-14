"""
wikiops/wikipedia.py - Wikipedia API Integration Module

This module provides functions for fetching article content from the
English Wikipedia API. It handles:
- Article title validation
- API request construction with proper headers
- Error handling for various failure scenarios

API Documentation:
    https://en.wikipedia.org/w/api.php

User-Agent Policy:
    Wikimedia requires a descriptive User-Agent header for API requests.
    See: https://meta.wikimedia.org/wiki/User-Agent_policy

Rate Limiting:
    This module does not implement rate limiting. Callers should implement
    appropriate throttling to avoid hitting Wikipedia's rate limits.
"""

from __future__ import annotations

from typing import Final, List, Optional, Tuple

import requests


# Wikipedia API endpoint URL for English Wikipedia.
# Can be modified for testing or to use other language editions.
WIKIPEDIA_API_URL: Final[str] = "https://en.wikipedia.org/w/api.php"

# User-Agent header for Wikipedia API requests.
# Following Wikimedia's User-Agent policy with tool name, version, URL, and purpose.
USER_AGENT: Final[str] = (
    "WikiHelper/1.0 "
    "(https://github.com/MrIbrahem/WikiHelper; "
    "WikiText reference manager)"
)

# Default timeout for API requests in seconds.
DEFAULT_TIMEOUT: Final[int] = 10

# Characters not allowed in Wikipedia article titles.
# See: https://en.wikipedia.org/wiki/Wikipedia:Article_titles#Characters_not_allowed_in_titles
INVALID_TITLE_CHARS: Final[List[str]] = ["#", "<", ">", "[", "]", "|", "{", "}"]


def fetch_wikipedia_article(
    title: str,
    timeout: int = DEFAULT_TIMEOUT
) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch the wikitext content of an article from English Wikipedia.

    This function uses the Wikimedia Parse API to retrieve the raw wikitext
    source of a given article. It handles various error conditions gracefully
    and returns user-friendly error messages.

    Args:
        title: The title of the Wikipedia article to fetch. Case-sensitive
               matching Wikipedia's case sensitivity rules (first letter
               is case-insensitive, rest is case-sensitive).
        timeout: Request timeout in seconds. Defaults to 10 seconds.
                 Increase for slow connections or large articles.

    Returns:
        A tuple of (wikitext, error_message):
        - On success: (wikitext_content, None)
        - On failure: (None, error_message)

        The error_message is always a user-friendly string suitable for
        display in the UI.

    Error Handling:
        The function catches all exceptions and returns appropriate error
        messages for:
        - Empty/missing titles
        - Non-existent articles
        - Network timeouts
        - Connection failures
        - HTTP errors (including rate limiting)
        - Invalid JSON responses

    Example:
        >>> wikitext, error = fetch_wikipedia_article("Albert Einstein")
        >>> if error:
        ...     print(f"Error: {error}")
        ... else:
        ...     print(f"Got {len(wikitext)} characters")

    Note:
        The function strips whitespace from the title before processing.
        Empty or whitespace-only titles return an error without making
        a network request.
    """
    # Validate input early to avoid unnecessary network requests.
    if not title or not title.strip():
        return None, "Article title is required"

    title = title.strip()

    # Build API request parameters.
    # formatversion=2 provides cleaner response format with consistent data types.
    # See: https://www.mediawiki.org/wiki/API:JSON_version_2
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2"
    }

    # Headers including User-Agent for Wikipedia API compliance.
    headers = {
        "User-Agent": USER_AGENT
    }

    try:
        # Make the API request with proper headers and timeout.
        response = requests.get(
            WIKIPEDIA_API_URL,
            params=params,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()  # Raise HTTPError for 4xx/5xx responses

        data = response.json()

        # Check for API-level errors (e.g., missing page).
        if "error" in data:
            error_code = data["error"].get("code", "unknown")
            if error_code == "missingtitle":
                return None, f"Article '{title}' not found on English Wikipedia"
            return None, f"Wikipedia API error: {data['error'].get('info', 'Unknown error')}"

        # Extract wikitext from successful response.
        if "parse" in data and "wikitext" in data["parse"]:
            wikitext = data["parse"]["wikitext"]
            return wikitext, None

        # Response structure was unexpected.
        return None, "Could not extract wikitext from Wikipedia response"

    except requests.exceptions.Timeout:
        # Request took longer than the timeout.
        return None, "Request timed out. Please try again."

    except requests.exceptions.ConnectionError:
        # Network-level connection failure (DNS, refused, etc.).
        return None, "Failed to connect to Wikipedia API. Please check your internet connection."

    except requests.exceptions.HTTPError as e:
        # HTTP status error (4xx, 5xx).
        status_code = e.response.status_code if e.response else "unknown"
        if status_code == 429:
            # Rate limited - client should wait before retrying.
            return None, "Too many requests. Please wait a moment and try again."
        return None, f"Wikipedia API returned an error (HTTP {status_code}). Please try again later."

    except requests.exceptions.RequestException:
        # Catch-all for other requests library exceptions.
        return None, "Failed to retrieve article from Wikipedia. Please try again."

    except ValueError:
        # JSON parsing failed - invalid response body.
        return None, "Received invalid response from Wikipedia API. Please try again."

    except Exception:
        # Catch-all for unexpected errors. We intentionally don't expose
        # internal error details to users for security reasons.
        return None, "An unexpected error occurred. Please try again."


def validate_article_title(
    title: str,
    max_length: int = 255
) -> Tuple[bool, Optional[str]]:
    """
    Validate a Wikipedia article title before attempting to fetch it.

    This function performs client-side validation to catch obviously invalid
    titles before making API requests. It implements a subset of Wikipedia's
    title restrictions.

    Validation Rules:
        1. Title must not be empty or whitespace-only
        2. Title must not exceed max_length characters
        3. Title must not contain forbidden characters: # < > [ ] | { }

    Note: This validation is intentionally permissive. Wikipedia has
    additional restrictions (e.g., certain prefixes, length limits by
    namespace) that are only enforced server-side.

    Args:
        title: The article title to validate.
        max_length: Maximum allowed title length. Defaults to 255 characters,
                    which matches Wikipedia's typical limit for article titles.

    Returns:
        A tuple of (is_valid, error_message):
        - On valid: (True, None)
        - On invalid: (False, error_message)

    Example:
        >>> validate_article_title("Albert Einstein")
        (True, None)
        >>> validate_article_title("")
        (False, 'Article title is required')
        >>> validate_article_title("Test[Article]")
        (False, 'Article title contains invalid character: [')

    Note:
        This function does NOT check if the article exists - it only
        validates that the title format is acceptable. Use fetch_wikipedia_article
        to check for article existence.
    """
    # Check for empty or whitespace-only titles.
    if not title or not title.strip():
        return False, "Article title is required"

    title = title.strip()

    # Check title length.
    if len(title) > max_length:
        return False, f"Article title must be {max_length} characters or less"

    # Check for forbidden characters.
    # These characters have special meaning in wikitext or URLs and are
    # not allowed in article titles.
    for char in INVALID_TITLE_CHARS:
        if char in title:
            return False, f"Article title contains invalid character: {char}"

    return True, None
