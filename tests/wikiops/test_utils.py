from wikiops.utils import slugify_title, fix_space_before_section, fix_sections_space


class TestSlugifyTitle:
    def test_basic_slugify(self):
        """Test basic slugification."""
        title = "Hello World"
        expected = "hello-world"
        result = slugify_title(title)
        assert result == expected

    def test_remove_special_characters(self):
        """Test removing special characters."""
        title = "Hello! World@#"
        expected = "hello-world"
        result = slugify_title(title)
        assert result == expected

    def test_handle_unicode_characters(self):
        """Test handling Unicode characters by normalizing to ASCII."""
        title = "Café Müller"
        expected = "cafe-muller"
        result = slugify_title(title)
        assert result == expected

    def test_remove_consecutive_hyphens(self):
        """Test removing consecutive hyphens."""
        title = "Hello--World"
        expected = "hello-world"
        result = slugify_title(title)
        assert result == expected

    def test_strip_leading_trailing_hyphens(self):
        """Test stripping leading and trailing hyphens."""
        title = "-Hello World-"
        expected = "hello-world"
        result = slugify_title(title)
        assert result == expected

    def test_mixed_case_and_numbers(self):
        """Test mixed case and numbers."""
        title = "Test123 Case"
        expected = "test123-case"
        result = slugify_title(title)
        assert result == expected

    def test_only_special_characters(self):
        """Test title with only special characters."""
        title = "!@#$%^&*()"
        expected = ""
        result = slugify_title(title)
        assert result == expected

    def test_empty_string(self):
        """Test with empty string."""
        title = ""
        expected = ""
        result = slugify_title(title)
        assert result == expected

    def test_arabic_characters(self):
        """Test with Arabic characters (should be ignored in ASCII)."""
        title = "عنوان عربي"
        expected = ""
        result = slugify_title(title)
        assert result == expected

    def test_underscores_allowed(self):
        """Test that underscores are allowed."""
        title = "hello_world"
        expected = "hello_world"
        result = slugify_title(title)
        assert result == expected
