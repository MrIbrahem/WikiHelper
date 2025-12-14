# tests/test_edge_cases.py
# Tests for edge cases

from src.wikiops.refs import extract_refs_from_text


def test_text_without_refs():
    """Test text without any references."""
    text = "Plain text without references."

    modified, refs = extract_refs_from_text(text)

    assert modified == text
    assert refs == {}


def test_duplicate_ref_content():
    """Test text with duplicate reference content."""
    text = "A<ref>Same</ref>B<ref>Same</ref>C"

    modified, refs = extract_refs_from_text(text)

    assert modified.count("[ref") == 2
    assert len(refs) == 2
    assert refs["ref1"] == refs["ref2"]


def test_adjacent_refs():
    """Test adjacent references."""
    text = "<ref>One</ref><ref>Two</ref>"

    modified, refs = extract_refs_from_text(text)

    assert modified == "[ref1][ref2]"


def test_malformed_ref_does_not_crash():
    """Test that malformed ref tags don't cause crashes."""
    text = "Text <ref>Unclosed ref"

    modified, refs = extract_refs_from_text(text)

    assert modified == text
    assert refs == {}
