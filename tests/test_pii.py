"""The invented-PII check is the safety property everything else rests on."""
import pytest

from legalapp import library
from legalapp.checks import pii
from legalapp.findings import Severity

VOCAB = library.vocabulary()


def scan(text):
    return pii.scan(text, "p1", extra_vocab=VOCAB)


CLEAN = [
    "We act for [CLIENT_FULL_NAME] and write further to our earlier correspondence.",
    "Your client's Form E fell due on [DISCLOSURE_DUE_DATE].",
    "Under the Family Procedure Rules 2010 we invite a reply by [RESPONSE_DEADLINE].",
    "The First Directions Appointment is listed for [HEARING_DATE].",
    "Dear Sirs\n\nRe: [CLIENT_FULL_NAME] and [OTHER_PARTY_NAME] -- financial remedy",
    "Yours faithfully\n\n[FEE_EARNER_NAME]\n[FEE_EARNER_ROLE]",
    "Our client relies on the Matrimonial Causes Act 1973 and Practice Direction 28A.",
    "We refer to section 25 and to FPR 28.3(6).",
    "A Child Arrangements Order was made by the Family Court.",
    "Please complete Form C100 and the FM5 in good time.",
]


@pytest.mark.parametrize("text", CLEAN)
def test_generic_letters_produce_no_findings(text):
    assert scan(text) == [], f"false positive on: {text!r}"


LEAKS = [
    ("We act for Sarah Thompson in this matter.", "Sarah Thompson"),
    ("Mr Okafor has not filed his Form E.", "Mr Okafor"),
    ("The disclosure fell due on 14 March 2025.", "14 March 2025"),
    ("Please reply by 28/03/2025.", "28/03/2025"),
    ("Our office is at SW1A 2AA.", "SW1A 2AA"),
    ("Case ZC24D01234 refers.", "ZC24D01234"),
    ("The sum of £14,500 remains outstanding.", "£14,500"),
    ("Contact j.mills@firm.co.uk for details.", "j.mills@firm.co.uk"),
    ("Telephone 020 7946 0912 to discuss.", "020 7946 0912"),
]


@pytest.mark.parametrize("text,expected", LEAKS)
def test_literal_pii_is_caught(text, expected):
    found = scan(text)
    assert found, f"missed PII in: {text!r}"
    assert any(expected in f.excerpt for f in found), [f.excerpt for f in found]
    assert all(f.severity is Severity.BLOCKING for f in found)


def test_pii_inside_a_placeholder_is_not_a_finding():
    # Placeholders are the intended output, never a defect.
    assert scan("Re: [CLIENT_FULL_NAME] and [CHILD_1_NAME]") == []


def test_finding_names_a_replacement_token():
    (f,) = scan("We act for Sarah Thompson.")
    assert "[CLIENT_FULL_NAME]" in f.suggestion


def test_whole_library_is_clean():
    for pid, para in library.paragraphs().items():
        assert scan(para["text"]) == [], f"library paragraph {pid} contains literal PII"


CASE_STYLE = [
    "Re: Thompson v Thompson -- financial remedy",
    "We refer to Kaur v Kaur.",
]


@pytest.mark.parametrize("text", CASE_STYLE)
def test_party_names_in_a_case_style_are_caught(text):
    found = scan(text)
    assert found, f"missed case-style party names in {text!r}"
    assert all(f.severity is Severity.BLOCKING for f in found)


def test_case_style_does_not_fire_on_reported_authority_in_vocabulary():
    # A genuine placeholder Re line stays clean.
    assert scan("Re: [CLIENT_FULL_NAME] and [OTHER_PARTY_NAME] -- financial remedy") == []
