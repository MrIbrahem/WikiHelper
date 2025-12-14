# tests/test_refs_roundtrip.py
# Tests for round-trip integrity

from extract_refs_wtp import extract_refs_from_text
from restore_refs_wtp import restore_refs_in_text


def test_roundtrip_preserves_original(mixed_refs_wikitext):
    """Test that extract + restore produces byte-for-byte identical text."""
    modified, refs = extract_refs_from_text(mixed_refs_wikitext)
    restored = restore_refs_in_text(modified, refs)

    assert restored == mixed_refs_wikitext


def test_ref_order_preserved(mixed_refs_wikitext):
    """Test that reference order is preserved during extraction."""
    modified, refs = extract_refs_from_text(mixed_refs_wikitext)

    assert list(refs.keys()) == ["ref1", "ref2", "ref3"]


def test_roundtrip_complex_wikitext_with_refs(complex_wikitext_with_refs):
    """Test round-trip with complex WikiText containing wikilinks, Arabic text, and refs."""
    modified, refs = extract_refs_from_text(complex_wikitext_with_refs)
    restored = restore_refs_in_text(modified, refs)

    assert restored == complex_wikitext_with_refs


def test_complex_wikitext_ref_count(complex_wikitext_with_refs):
    """Test that all refs are extracted from complex WikiText."""
    modified, refs = extract_refs_from_text(complex_wikitext_with_refs)

    # Should have 5 refs: 3 regular, 2 with names (1 self-closing)
    assert len(refs) == 5
    assert list(refs.keys()) == ["ref1", "ref2", "ref3", "ref4", "ref5"]


def test_wikilinks_preserved_without_refs(complex_wikitext_with_wikilinks):
    """Test that wikilinks (including Arabic) are preserved when no refs exist."""
    modified, refs = extract_refs_from_text(complex_wikitext_with_wikilinks)

    # No refs in this text, should be unchanged
    assert modified == complex_wikitext_with_wikilinks
    assert refs == {}
    # Verify Arabic wikilinks are preserved
    assert "[[لونغ آيلند]]" in modified
    assert "[[ماراثون مدينة نيويورك]]" in modified
