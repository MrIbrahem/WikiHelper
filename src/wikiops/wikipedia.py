# wikiops/wikipedia.py
# Functions to fetch article content from English Wikipedia API

from __future__ import annotations

from typing import Optional, Tuple
import requests

# Wikipedia API endpoint URL (configurable for testing)
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"

# User-Agent header for Wikipedia API requests
# Following Wikimedia's User-Agent policy: https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = "WikiHelper/1.0 (https://github.com/MrIbrahem/WikiHelper; WikiText reference manager)"


def fetch_wikipedia_article(title: str, timeout: int = 10) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch the wikitext content of an article from English Wikipedia.
    
    Args:
        title: The title of the Wikipedia article to fetch
        timeout: Request timeout in seconds (default: 10)
    
    Returns:
        Tuple of (wikitext, error_message):
        - On success: (wikitext_content, None)
        - On failure: (None, error_message)
    """
    if not title or not title.strip():
        return None, "Article title is required"
    
    title = title.strip()
    
    # Parameters for the API request
    # formatversion=2 provides cleaner response format with consistent data types
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2"
    }
    
    # Headers including User-Agent for Wikipedia API compliance
    headers = {
        "User-Agent": USER_AGENT
    }
    
    try:
        # Make the API request with proper User-Agent header
        response = requests.get(WIKIPEDIA_API_URL, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if the page exists
        if "error" in data:
            error_code = data["error"].get("code", "unknown")
            if error_code == "missingtitle":
                return None, f"Article '{title}' not found on English Wikipedia"
            return None, f"Wikipedia API error: {data['error'].get('info', 'Unknown error')}"
        
        # Extract wikitext from the response
        if "parse" in data and "wikitext" in data["parse"]:
            wikitext = data["parse"]["wikitext"]
            return wikitext, None
        
        return None, "Could not extract wikitext from Wikipedia response"
        
    except requests.exceptions.Timeout:
        return None, "Request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return None, "Failed to connect to Wikipedia API. Please check your internet connection."
    except requests.exceptions.HTTPError as e:
        # Provide user-friendly error without exposing internal details
        status_code = e.response.status_code if e.response else "unknown"
        if status_code == 429:
            return None, "Too many requests. Please wait a moment and try again."
        return None, f"Wikipedia API returned an error (HTTP {status_code}). Please try again later."
    except requests.exceptions.RequestException:
        return None, "Failed to retrieve article from Wikipedia. Please try again."
    except ValueError:
        return None, "Received invalid response from Wikipedia API. Please try again."
    except Exception:
        return None, "An unexpected error occurred. Please try again."


def validate_article_title(title: str, max_length: int = 255) -> Tuple[bool, Optional[str]]:
    """
    Validate a Wikipedia article title.
    
    Args:
        title: The article title to validate
        max_length: Maximum allowed length (default: 255)
    
    Returns:
        Tuple of (is_valid, error_message):
        - On success: (True, None)
        - On failure: (False, error_message)
    """
    if not title or not title.strip():
        return False, "Article title is required"
    
    title = title.strip()
    
    if len(title) > max_length:
        return False, f"Article title must be {max_length} characters or less"
    
    # Wikipedia doesn't allow certain characters in titles
    invalid_chars = ["#", "<", ">", "[", "]", "|", "{", "}"]
    for char in invalid_chars:
        if char in title:
            return False, f"Article title contains invalid character: {char}"
    
    return True, None
