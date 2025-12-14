# tests/conftest.py
# Shared pytest fixtures for WikiHelper tests

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
