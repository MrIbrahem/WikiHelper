"""
conftest.py - Shared pytest fixtures for WikiHelper tests

This module defines fixtures for testing the Flask application using
the application factory pattern.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app import create_app
from config import TestingConfig


@pytest.fixture
def app():
    """
    Create application for testing.

    Uses TestingConfig with:
    - TESTING = True
    - WTF_CSRF_ENABLED = False (for easier form testing)
    - Temporary directory for WIKI_WORK_ROOT
    """
    # Create a temporary directory for workspace storage
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_config = type(
            "TestConfig",
            (TestingConfig,),
            {"WIKI_WORK_ROOT": Path(tmp_dir)}
        )
        app = create_app(test_config)

        with app.app_context():
            yield app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def auth_client(client):
    """
    Create an authenticated test client with username in session.

    This simulates a logged-in user.
    """
    with client.session_transaction() as sess:
        sess["username"] = "testuser"
    return client


# Data fixtures for wikiops testing
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
        'Text <ref name="nyt-1910-03-31" /> end.'
    )


@pytest.fixture
def mixed_refs_wikitext():
    return (
        "A<ref>First</ref>"
        "B<ref name=\"x\" />"
        "C<ref>Third</ref>"
    )


@pytest.fixture
def complex_wikitext_with_wikilinks():
    """Real-world WikiText with Arabic text, wikilinks and multiple bridges."""
    return (
        "The Queensboro Bridge carries New York State Route 25 (NY 25), which "
        "terminates at the bridge's western end in Manhattan. The bridge has two "
        "levels: an upper level with a pair of two-lane roadways, and a lower level "
        "with four vehicular lanes flanked by a  walkway and a bike lane. The western "
        "leg of the Queensboro Bridge is paralleled on its northern side by the "
        "Roosevelt Island Tramway. The bridge is one of four vehicular bridges "
        "directly connecting Manhattan Island and [[لونغ آيلند]], along with the "
        "[[جسر ويليامزبرغ|Williamsburg]]، [[جسر مانهاتن|Manhattan]], and "
        "[[جسر بروكلين|Brooklyn]] bridges to the south. It lies along the courses "
        "of the [[ماراثون مدينة نيويورك]] and the Five Boro Bike Tour."
    )


@pytest.fixture
def complex_wikitext_with_refs():
    """Real-world WikiText with wikilinks, Arabic text, and references."""
    return (
        "The Queensboro Bridge<ref>Bridge reference</ref> carries New York State "
        "Route 25 (NY 25), which terminates at the bridge's western end in Manhattan. "
        "The bridge has two levels<ref name=\"levels\">Level details here</ref>: an "
        "upper level with a pair of two-lane roadways, and a lower level with four "
        "vehicular lanes flanked by a  walkway and a bike lane. The western leg of "
        "the Queensboro Bridge is paralleled on its northern side by the Roosevelt "
        "Island Tramway<ref name=\"tramway\" />. The bridge is one of four vehicular "
        "bridges directly connecting Manhattan Island and [[لونغ آيلند]], along with "
        "the [[جسر ويليامزبرغ|Williamsburg]]، [[جسر مانهاتن|Manhattan]], and "
        "[[جسر بروكلين|Brooklyn]] bridges to the south<ref>Southern bridges info</ref>. "
        "It lies along the courses of the [[ماراثون مدينة نيويورك]] and the Five Boro "
        "Bike Tour<ref name=\"tour\">Tour reference</ref>."
    )
