# tests/test_refs_extract.py
# Tests for ref extraction logic

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from extract_refs_wtp import extract_refs_from_text


def test_extract_single_ref(simple_wikitext):
    """Test extraction of a single reference."""
    modified, refs = extract_refs_from_text(simple_wikitext)

    assert "[ref1]" in modified
    assert "ref1" in refs
    assert refs["ref1"] == "<ref>Reference one</ref>"


def test_extract_multiline_ref(multiline_ref_wikitext):
    """Test extraction of a multiline reference."""
    modified, refs = extract_refs_from_text(multiline_ref_wikitext)

    assert "[ref1]" in modified
    assert "\nLine one\n" in refs["ref1"]


def test_extract_self_closing_ref(self_closing_ref_wikitext):
    """Test extraction of a self-closing reference."""
    modified, refs = extract_refs_from_text(self_closing_ref_wikitext)

    assert "[ref1]" in modified
    assert refs["ref1"].startswith("<ref")
    assert refs["ref1"].endswith("/>")
