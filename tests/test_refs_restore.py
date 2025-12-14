# tests/test_refs_restore.py
# Tests for ref restoration logic

from restore_refs_wtp import restore_refs_in_text


def test_restore_single_ref():
    """Test restoration of a single reference."""
    text = "Hello [ref1] world"
    refs = {"ref1": "<ref>Test</ref>"}

    restored = restore_refs_in_text(text, refs)

    assert "<ref>Test</ref>" in restored
    assert "[ref1]" not in restored


def test_restore_missing_ref_key():
    """Test that missing reference keys are preserved."""
    text = "Hello [ref99] world"
    refs = {"ref1": "<ref>Test</ref>"}

    restored = restore_refs_in_text(text, refs)

    assert "[ref99]" in restored
