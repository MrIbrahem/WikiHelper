import pytest

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

    # @pytest.mark.skip(reason="Demonstration of recent edits")
    def test_underscores_allowed(self):
        """Test that underscores are allowed."""
        title = "hello_world"
        expected = "hello_world"
        result = slugify_title(title)
        assert result == expected


class TestFixSpaceBeforeSection:
    def test_remove_leading_spaces(self):
        """Test removing leading spaces before equal signs."""
        content = "  =Header="
        expected = "=Header="
        result = fix_space_before_section(content)
        assert result == expected

    def test_no_change_if_no_spaces(self):
        """Test no change if no leading spaces."""
        content = "=Header="
        expected = "=Header="
        result = fix_space_before_section(content)
        assert result == expected

    def test_multiple_spaces(self):
        """Test removing multiple leading spaces."""
        content = "   ==Section=="
        expected = "==Section=="
        result = fix_space_before_section(content)
        assert result == expected

    def test_multiple_lines(self):
        """Test fixing multiple lines."""
        content = "  =Header=\n   ==Subsection\n=Normal"
        expected = "=Header=\n==Subsection\n=Normal"
        result = fix_space_before_section(content)
        assert result == expected

    def test_no_change_middle_of_line(self):
        """Test no change if spaces are not at the start."""
        content = "Text  =Header="
        expected = "Text  =Header="
        result = fix_space_before_section(content)
        assert result == expected


class TestFixSectionsSpace:
    def test_add_spaces_around_text(self):
        """Test adding spaces around section text."""
        content = "==text=="
        expected = "== text =="
        result = fix_sections_space(content)
        assert result == expected

    def test_no_change_if_spaces_present(self):
        """Test no change if spaces are already present."""
        content = "== text =="
        expected = "== text =="
        result = fix_sections_space(content)
        assert result == expected

    def test_multiple_equals(self):
        """Test with multiple equal signs."""
        content = "===subsection==="
        expected = "=== subsection ==="
        result = fix_sections_space(content)
        assert result == expected

    def test_no_change_if_space_after_equals(self):
        """Test no change if there's already space after equals."""
        content = "== text=="
        expected = "== text=="
        result = fix_sections_space(content)
        assert result == expected

    def test_no_change_if_space_before_closing_equals(self):
        """Test no change if there's space before closing equals."""
        content = "==text =="
        expected = "==text =="
        result = fix_sections_space(content)
        assert result == expected

    def test_multiple_lines(self):
        """Test fixing multiple lines."""
        content = "==section1==\n===section2===\n== section3 =="
        expected = "== section1 ==\n=== section2 ===\n== section3 =="
        result = fix_sections_space(content)
        assert result == expected

    def test_no_change_if_not_exact_match(self):
        """Test no change if not exact match (e.g., extra equals)."""
        content = "==text==="
        expected = "==text==="
        result = fix_sections_space(content)
        assert result == expected
