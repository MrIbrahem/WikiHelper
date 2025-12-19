# wikiops/wikipedia.py
# Functions to fetch article content from English Wikipedia API

from __future__ import annotations

from typing import Optional, Tuple
import requests


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
    
    # Wikipedia API endpoint
    api_url = "https://en.wikipedia.org/w/api.php"
    
    # Parameters for the API request
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2"
    }
    
    try:
        # Make the API request
        response = requests.get(api_url, params=params, timeout=timeout)
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
        return None, f"Request timed out after {timeout} seconds"
    except requests.exceptions.ConnectionError:
        return None, "Failed to connect to Wikipedia API"
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP error: {e}"
    except requests.exceptions.RequestException as e:
        return None, f"Request error: {e}"
    except ValueError as e:
        return None, f"Failed to parse JSON response: {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"


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
