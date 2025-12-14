# tests/test_refs_roundtrip.py
# Tests for round-trip integrity

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

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
