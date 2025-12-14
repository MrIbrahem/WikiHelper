# Additional Plan: Pytest Testing Strategy for Wiki Ref Extraction & Restoration

## 1. Purpose of the Test Plan

The goal of this test plan is to **guarantee correctness, stability, and data integrity** for the most critical logic in the application:

- Extraction of `<ref>` tags using `wikitextparser`
- Replacement with placeholders `[refN]`
- Restoration of references without loss, corruption, or reordering
- Safety against edge cases (multiline refs, self-closing refs, duplicates, malformed input)

This plan focuses on **pure logic tests** (unit tests) first, with optional integration tests later.

---

## 2. Testing Scope

### In Scope (High Priority)
- Reference extraction logic
- Reference restoration logic
- Placeholder integrity
- Round-trip correctness (extract → edit → restore)
- Handling of edge cases

### Out of Scope (Lower Priority / Later)
- Flask route tests
- HTML rendering
- Authentication / CSRF
- Performance / load testing

---

## 3. Test Directory Structure

tests/ │ ├── test_refs_extract.py ├── test_refs_restore.py ├── test_refs_roundtrip.py ├── test_edge_cases.py └── conftest.py

---

## 4. Shared Test Fixtures (`conftest.py`)

Define reusable fixtures for sample WikiText inputs.

```python
import pytest

@pytest.fixture
def simple_wikitext():
    return (
        "Text before."
        "<ref>Reference one</ref>"
        "Text after."
    )

@pytest.fixture
def multiline_ref_wikitext():
    return (
        "Intro.\n"
        "<ref>\n"
        "Line one\n"
        "Line two\n"
        "</ref>\n"
        "End."
    )

@pytest.fixture
def self_closing_ref_wikitext():
    return (
        "Text <ref name=\"nyt-1910-03-31\" /> end."
    )

@pytest.fixture
def mixed_refs_wikitext():
    return (
        "A<ref>First</ref>"
        "B<ref name=\"x\" />"
        "C<ref>Third</ref>"
    )

```
---

##5. Extraction Tests (test_refs_extract.py)

###5.1 Basic Extraction
```python
def test_extract_single_ref(simple_wikitext):
    modified, refs = extract_refs_from_text(simple_wikitext)

    assert "[ref1]" in modified
    assert "ref1" in refs
    assert refs["ref1"] == "<ref>Reference one</ref>"
```
###5.2 Multiline Reference Preservation
```python
def test_extract_multiline_ref(multiline_ref_wikitext):
    modified, refs = extract_refs_from_text(multiline_ref_wikitext)

    assert "[ref1]" in modified
    assert "\nLine one\n" in refs["ref1"]
```
###5.3 Self-Closing <ref />
```python
def test_extract_self_closing_ref(self_closing_ref_wikitext):
    modified, refs = extract_refs_from_text(self_closing_ref_wikitext)

    assert "[ref1]" in modified
    assert refs["ref1"].startswith("<ref")
    assert refs["ref1"].endswith("/>")

```
---

##6. Restoration Tests (test_refs_restore.py)

###6.1 Basic Restoration
```python
def test_restore_single_ref():
    text = "Hello [ref1] world"
    refs = {"ref1": "<ref>Test</ref>"}

    restored = restore_refs_in_text(text, refs)

    assert "<ref>Test</ref>" in restored
    assert "[ref1]" not in restored
```
###6.2 Missing Reference Key (Fail-Safe)
```python
def test_restore_missing_ref_key():
    text = "Hello [ref99] world"
    refs = {"ref1": "<ref>Test</ref>"}

    restored = restore_refs_in_text(text, refs)

    assert "[ref99]" in restored
```

---

##7. Round-Trip Integrity Tests (test_refs_roundtrip.py)

###7.1 Exact Round-Trip Equality

This is the most critical test.
```python
def test_roundtrip_preserves_original(mixed_refs_wikitext):
    modified, refs = extract_refs_from_text(mixed_refs_wikitext)
    restored = restore_refs_in_text(modified, refs)

    assert restored == mixed_refs_wikitext
```
###7.2 Order Preservation
```python
def test_ref_order_preserved(mixed_refs_wikitext):
    modified, refs = extract_refs_from_text(mixed_refs_wikitext)

    assert list(refs.keys()) == ["ref1", "ref2", "ref3"]

```
---

##8. Edge Case Tests (test_edge_cases.py)

###8.1 No References at All
```python
def test_text_without_refs():
    text = "Plain text without references."

    modified, refs = extract_refs_from_text(text)

    assert modified == text
    assert refs == {}
```
###8.2 Repeated Identical References
```python
def test_duplicate_ref_content():
    text = "A<ref>Same</ref>B<ref>Same</ref>C"

    modified, refs = extract_refs_from_text(text)

    assert modified.count("[ref") == 2
    assert len(refs) == 2
    assert refs["ref1"] == refs["ref2"]
```
###8.3 Adjacent References
```python
def test_adjacent_refs():
    text = "<ref>One</ref><ref>Two</ref>"

    modified, refs = extract_refs_from_text(text)

    assert modified == "[ref1][ref2]"

```
---

##9. Negative & Robustness Tests

Malformed ref tags should not crash extraction

Broken wiki syntax should leave text unchanged

Extraction must never raise unhandled exceptions

```python
def test_malformed_ref_does_not_crash():
    text = "Text <ref>Unclosed ref"

    modified, refs = extract_refs_from_text(text)

    assert modified == text
    assert refs == {}

```
---

##10. Test Execution Strategy

Run all tests
```
pytest
```
Run only ref-related tests
```
pytest tests/test_refs_*
```
Enable verbose output
```
pytest -vv
```

---

##11. Quality Gates (Must Pass)

The implementation is considered acceptable only if:

All tests pass

Round-trip tests pass with strict equality

No test relies on monkeypatch or mocks

No reference text is altered or normalized

Placeholder numbering is deterministic and stable



---

##12. Extension (Optional, Future)

Property-based testing with hypothesis

Fuzz testing with random WikiText

Integration tests for Flask routes

Snapshot tests for large wiki articles



---

##13. Guiding Principle

> If extraction + restoration does not produce byte-for-byte identical WikiText, the implementation is incorrect, regardless of visual similarity.



This rule is non-negotiable.
