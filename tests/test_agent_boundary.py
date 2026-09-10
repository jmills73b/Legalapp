"""The PII boundary is enforced structurally, not by convention."""
import pytest

from legalapp.agents.client import PIILeakBlocked, assert_no_pii
from legalapp.agents import review
from legalapp.compose import compose
from legalapp.render import merge
from legalapp.spec import LetterSpec, RecipientClass


def test_clean_generic_text_passes_the_boundary():
    assert_no_pii("We act for [CLIENT_FULL_NAME] and write further.", "draft")


def test_literal_pii_is_refused_before_any_api_call():
    with pytest.raises(PIILeakBlocked) as e:
        assert_no_pii("We act for Sarah Thompson.", "draft")
    assert "Sarah Thompson" in str(e.value)


def test_a_merged_letter_cannot_be_sent_for_review():
    spec = LetterSpec("form_e_chaser", RecipientClass.OTHER_SIDE_SOLICITORS, deadline_days=14)
    letter = compose(spec)
    merged, _ = merge(letter.text, {"CLIENT_FULL_NAME": "Ayesha Kaur"}, spec)
    letter.replace("intro_acting", merged.splitlines()[0] if merged else "Ayesha Kaur")
    letter.replace("intro_acting", "We act for Ayesha Kaur.")
    with pytest.raises(PIILeakBlocked):
        review.tone_and_conduct(letter)


def test_risk_review_does_not_run_on_letters_to_our_own_client():
    letter = compose(LetterSpec("form_e_chaser", RecipientClass.CLIENT))
    assert review.risk_review(letter) == []


def test_recipient_class_drives_the_review_path():
    assert RecipientClass.CLIENT.is_outbound is False
    assert RecipientClass.OTHER_SIDE_SOLICITORS.is_outbound is True
    assert RecipientClass.LITIGANT_IN_PERSON.unrepresented is True
