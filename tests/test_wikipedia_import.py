# tests/test_wikipedia_import.py
# Tests for Wikipedia article import functionality

from unittest.mock import patch, Mock
from src.wikiops.wikipedia import fetch_wikipedia_article, validate_article_title


class TestValidateArticleTitle:
    """Tests for article title validation."""

    def test_valid_title(self):
        """Test that valid titles pass validation."""
        is_valid, error = validate_article_title("Albert Einstein")
        assert is_valid is True
        assert error is None

    def test_valid_title_with_parentheses(self):
        """Test that titles with parentheses pass validation."""
        is_valid, error = validate_article_title("Python (programming language)")
        assert is_valid is True
        assert error is None

    def test_empty_title(self):
        """Test that empty titles fail validation."""
        is_valid, error = validate_article_title("")
        assert is_valid is False
        assert "required" in error.lower()

    def test_whitespace_only_title(self):
        """Test that whitespace-only titles fail validation."""
        is_valid, error = validate_article_title("   ")
        assert is_valid is False
        assert "required" in error.lower()

    def test_title_too_long(self):
        """Test that overly long titles fail validation."""
        long_title = "A" * 256
        is_valid, error = validate_article_title(long_title, max_length=255)
        assert is_valid is False
        assert "255" in error

    def test_title_with_invalid_chars(self):
        """Test that titles with invalid characters fail validation."""
        invalid_chars = ["#", "<", ">", "[", "]", "|", "{", "}"]
        for char in invalid_chars:
            title = f"Article{char}Title"
            is_valid, error = validate_article_title(title)
            assert is_valid is False
            assert "invalid character" in error.lower()


class TestFetchWikipediaArticle:
    """Tests for fetching Wikipedia articles."""

    @patch('wikiops.wikipedia.requests.get')
    def test_fetch_successful(self, mock_get):
        """Test successful article fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "parse": {
                "wikitext": "Article content here"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        wikitext, error = fetch_wikipedia_article("Test Article")

        assert wikitext == "Article content here"
        assert error is None
        mock_get.assert_called_once()

        # Verify User-Agent header is included
        call_args = mock_get.call_args
        assert 'headers' in call_args.kwargs
        assert 'User-Agent' in call_args.kwargs['headers']
        assert 'WikiHelper' in call_args.kwargs['headers']['User-Agent']

    @patch('wikiops.wikipedia.requests.get')
    def test_fetch_missing_article(self, mock_get):
        """Test fetching a non-existent article."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": {
                "code": "missingtitle",
                "info": "The page you specified doesn't exist."
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        wikitext, error = fetch_wikipedia_article("NonExistentArticle123456")

        assert wikitext is None
        assert error is not None
        assert "not found" in error.lower()

    @patch('wikiops.wikipedia.requests.get')
    def test_fetch_timeout(self, mock_get):
        """Test handling of request timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        wikitext, error = fetch_wikipedia_article("Test Article")

        assert wikitext is None
        assert error is not None
        assert "timed out" in error.lower()

    @patch('wikiops.wikipedia.requests.get')
    def test_fetch_connection_error(self, mock_get):
        """Test handling of connection errors."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()

        wikitext, error = fetch_wikipedia_article("Test Article")

        assert wikitext is None
        assert error is not None
        assert "connect" in error.lower()

    def test_fetch_empty_title(self):
        """Test that empty title returns error without making request."""
        wikitext, error = fetch_wikipedia_article("")

        assert wikitext is None
        assert error is not None
        assert "required" in error.lower()

    def test_fetch_whitespace_title(self):
        """Test that whitespace-only title returns error."""
        wikitext, error = fetch_wikipedia_article("   ")

        assert wikitext is None
        assert error is not None
        assert "required" in error.lower()

    @patch('wikiops.wikipedia.requests.get')
    def test_fetch_api_error(self, mock_get):
        """Test handling of generic API errors."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": {
                "code": "internal_api_error",
                "info": "Internal API error"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        wikitext, error = fetch_wikipedia_article("Test Article")

        assert wikitext is None
        assert error is not None
        assert "error" in error.lower()

    @patch('wikiops.wikipedia.requests.get')
    def test_fetch_invalid_json(self, mock_get):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        wikitext, error = fetch_wikipedia_article("Test Article")

        assert wikitext is None
        assert error is not None
        assert "invalid response" in error.lower() or "api" in error.lower()

    @patch('wikiops.wikipedia.requests.get')
    def test_fetch_missing_wikitext_field(self, mock_get):
        """Test handling when wikitext field is missing from response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "parse": {
                "title": "Test Article"
                # Missing "wikitext" field
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        wikitext, error = fetch_wikipedia_article("Test Article")

        assert wikitext is None
        assert error is not None
        assert "extract" in error.lower()
