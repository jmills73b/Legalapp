import datetime

import pytest

from legalapp import checks, library
from legalapp.compose import compose
from legalapp.findings import Severity, blocking
from legalapp.render import merge, values_template
from legalapp.spec import LetterSpec, RecipientClass


def spec(**kw):
    kw.setdefault("letter_type", "form_e_chaser")
    kw.setdefault("recipient_class", RecipientClass.OTHER_SIDE_SOLICITORS)
    return LetterSpec(**kw)


def test_every_letter_type_composes_and_passes_every_check():
    for lt_id, lt in library.letter_types().items():
        s = spec(letter_type=lt_id, deadline_days=lt.get("default_deadline_days"))
        letter = compose(s)
        assert checks.run_all(letter) == [], f"{lt_id} produced findings"


def test_unknown_letter_type_is_rejected():
    with pytest.raises(KeyError):
        compose(spec(letter_type="nonexistent"))


def test_patching_a_paragraph_leaves_the_rest_byte_identical():
    letter = compose(spec())
    before = {p.id: p.text for p in letter.paragraphs}
    letter.replace("offer_call", "Please telephone the writer if that is difficult.")
    for p in letter.paragraphs:
        if p.id != "offer_call":
            assert p.text == before[p.id]
    assert "patched" in letter.paragraph("offer_call").source


def test_provenance_is_recorded_for_every_paragraph():
    for p in compose(spec()).paragraphs:
        assert p.source.startswith("library:") or p.source == "generated"


def test_bespoke_paragraph_is_marked_generated():
    letter = compose(spec(), bespoke={"chase_specifics": "Two bank statements remain outstanding."})
    assert letter.paragraph("chase_specifics").source == "generated"


# --- structure ---------------------------------------------------------------

def test_wp_marking_forbidden_on_an_open_letter():
    # form_e_chaser is an open letter; marking it WP is a blocking error.
    letter = compose(spec())
    p = library.paragraphs()["hdr_wp"]
    from legalapp.compose import Paragraph
    letter.paragraphs.insert(0, Paragraph("hdr_wp", p["text"], p["role"], "library:hdr_wp@1"))
    found = blocking(checks.structure.scan(letter))
    assert any("Without Prejudice" in f.message for f in found)


def test_wp_request_is_ignored_where_the_letter_type_forbids_it():
    letter = compose(spec(privileged=True))
    assert letter.paragraph("hdr_wp") is None
    assert checks.run_all(letter) == []


def test_address_suppression_removes_the_address_block():
    letter = compose(spec(suppress_address=True))
    assert "FIRM_ADDRESS_BLOCK" not in letter.tokens
    assert checks.run_all(letter) == []


def test_address_suppression_breach_is_blocking():
    letter = compose(spec())          # composed without suppression...
    letter.spec.suppress_address = True   # ...but the matter is flagged
    found = blocking(checks.structure.scan(letter))
    assert any("safeguarding" in f.suggestion for f in found)


def test_missing_required_paragraph_is_blocking():
    letter = compose(spec())
    letter.paragraphs = [p for p in letter.paragraphs if p.id != "signoff_faithfully"]
    assert blocking(checks.structure.scan(letter))


def test_undeclared_token_is_blocking():
    letter = compose(spec())
    letter.replace("offer_call", "Please contact [NOT_A_REAL_TOKEN].")
    found = blocking(checks.structure.scan(letter))
    assert any("token dictionary" in f.message for f in found)


# --- merge -------------------------------------------------------------------

VALUES = {
    "FIRM_NAME": "Harbrook & Vane LLP",
    "FIRM_ADDRESS_BLOCK": "12 Bedford Row, London WC1R 4BU",
    "MATTER_REF": "HV/FAM/2261",
    "THEIR_REF": "KDR/4417",
    "RECIPIENT_SALUTATION": "Sirs",
    "CLIENT_FULL_NAME": "Ayesha Kaur",
    "OTHER_PARTY_NAME": "Daniel Kaur",
    "DISCLOSURE_DUE_DATE": "3 August 2026",
    "FEE_EARNER_NAME": "J. Mills",
    "FEE_EARNER_ROLE": "Senior Associate",
}


def test_merge_resolves_every_required_token():
    letter = compose(spec(deadline_days=14))
    merged, unresolved = merge(letter.text, VALUES, letter.spec, datetime.date(2026, 9, 10))
    assert unresolved == []
    assert "Ayesha Kaur" in merged and "[CLIENT_FULL_NAME]" not in merged


def test_derived_dates_are_computed_not_typed():
    letter = compose(spec(deadline_days=14))
    merged, _ = merge(letter.text, VALUES, letter.spec, datetime.date(2026, 9, 10))
    assert "10 September 2026" in merged          # LETTER_DATE
    assert "24 September 2026" in merged          # RESPONSE_DEADLINE = +14 days
    assert "LETTER_DATE" not in VALUES            # never asked of the fee earner


def test_missing_required_value_is_reported_not_guessed():
    letter = compose(spec(deadline_days=14))
    partial = {k: v for k, v in VALUES.items() if k != "CLIENT_FULL_NAME"}
    merged, unresolved = merge(letter.text, partial, letter.spec, datetime.date(2026, 9, 10))
    assert unresolved == ["CLIENT_FULL_NAME"]
    assert "[CLIENT_FULL_NAME]" in merged         # left visible, never invented


def test_values_template_omits_derived_tokens():
    letter = compose(spec(deadline_days=14))
    template = values_template(letter)
    assert "LETTER_DATE" not in template and "RESPONSE_DEADLINE" not in template
    assert "CLIENT_FULL_NAME" in template


def test_merged_letter_would_now_fail_the_pii_scan():
    # Confirms the boundary is real: once merged, this text must never go to a model.
    letter = compose(spec(deadline_days=14))
    merged, _ = merge(letter.text, VALUES, letter.spec, datetime.date(2026, 9, 10))
    assert checks.pii.scan(merged, "merged", extra_vocab=library.vocabulary())


def test_dates_use_uk_correspondence_style():
    letter = compose(spec(deadline_days=21))
    merged, _ = merge(letter.text, VALUES, letter.spec, datetime.date(2026, 9, 10))
    assert "1 October 2026" in merged and "01 October 2026" not in merged
