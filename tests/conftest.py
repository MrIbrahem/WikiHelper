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
