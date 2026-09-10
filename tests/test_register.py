"""Register checks: the conventions and the extra duties owed to a litigant in person."""
import pytest

from legalapp import checks, library
from legalapp.checks import register
from legalapp.compose import Paragraph, compose
from legalapp.findings import Severity, blocking
from legalapp.spec import LetterSpec, RecipientClass


def lip(**kw):
    kw.setdefault("deadline_days", 28)
    return LetterSpec("first_letter_unrepresented", RecipientClass.LITIGANT_IN_PERSON, **kw)


# --- salutation and sign-off -------------------------------------------------

def test_named_salutation_with_faithfully_is_blocking():
    letter = compose(lip())
    p = library.paragraphs()["signoff_faithfully"]
    letter.paragraphs = [x for x in letter.paragraphs if x.id != "signoff_sincerely"]
    letter.paragraphs.append(Paragraph("signoff_faithfully", p["text"], p["role"], "library:signoff_faithfully@1"))
    found = register.salutation_signoff(letter)
    assert found and found[0].severity is Severity.BLOCKING
    assert "Yours sincerely" in found[0].suggestion


def test_formal_salutation_with_sincerely_is_blocking():
    letter = compose(LetterSpec("form_e_chaser", RecipientClass.OTHER_SIDE_SOLICITORS, deadline_days=14))
    p = library.paragraphs()["signoff_sincerely"]
    letter.paragraphs = [x for x in letter.paragraphs if x.id != "signoff_faithfully"]
    letter.paragraphs.append(Paragraph("signoff_sincerely", p["text"], p["role"], "library:signoff_sincerely@1"))
    found = register.salutation_signoff(letter)
    assert found and "Yours faithfully" in found[0].suggestion


def test_correct_pairings_produce_nothing():
    assert register.salutation_signoff(compose(lip())) == []
    assert register.salutation_signoff(
        compose(LetterSpec("form_e_chaser", RecipientClass.OTHER_SIDE_SOLICITORS))) == []


# --- deadline floor ----------------------------------------------------------

def test_short_deadline_to_an_unrepresented_person_is_flagged():
    found = register.deadline_floor(compose(lip(deadline_days=7)))
    assert found and found[0].severity is Severity.ADVISORY
    assert "21 days" in found[0].message


def test_deadline_floor_is_advisory_not_blocking():
    # An urgent case may justify a short deadline; this is the fee earner's call.
    assert not blocking(register.deadline_floor(compose(lip(deadline_days=3))))


def test_generous_deadline_passes():
    assert register.deadline_floor(compose(lip(deadline_days=28))) == []


def test_deadline_floor_does_not_apply_to_represented_recipients():
    letter = compose(LetterSpec("form_e_chaser", RecipientClass.OTHER_SIDE_SOLICITORS, deadline_days=7))
    assert register.deadline_floor(letter) == []


# --- plain language ----------------------------------------------------------

JARGON = ["Please complete the Form E.", "The FDA is next.", "We await disclosure.",
          "Your undertaking is required.", "This is a financial remedy matter."]


@pytest.mark.parametrize("text", JARGON)
def test_terms_of_art_to_a_litigant_in_person_are_flagged(text):
    assert register.plain_language(text, "p1"), f"missed jargon in {text!r}"


def test_a_glossed_term_is_accepted():
    text = ("You will be asked to complete a Form E, which is the form both of you use to "
            "set out your finances.")
    assert register.plain_language(text, "p1") == []


def test_plain_language_does_not_run_on_solicitor_correspondence():
    letter = compose(LetterSpec("form_e_chaser", RecipientClass.OTHER_SIDE_SOLICITORS, deadline_days=14))
    assert [f for f in register.scan(letter) if "term of art" in f.message] == []


# --- advice to someone we do not act for -------------------------------------

ADVICE = ["You should agree to the proposal.", "You must reply within 14 days.",
          "You are entitled to a share of the property.", "You will need to file a statement."]


@pytest.mark.parametrize("text", ADVICE)
def test_advising_an_unrepresented_recipient_is_flagged(text):
    assert register.advice_to_unrepresented(text, "p1"), f"missed advice in {text!r}"


EXEMPT = [
    "You should speak to your own solicitor before replying.",
    "You must take advice on this before agreeing anything.",
    "You should contact Citizens Advice if cost is a concern.",
    "We would encourage you to obtain independent legal advice.",
]


@pytest.mark.parametrize("text", EXEMPT)
def test_telling_them_to_get_their_own_advice_is_never_a_finding(text):
    assert register.advice_to_unrepresented(text, "p1") == [], text


# --- the library holds up ----------------------------------------------------

def test_every_letter_type_composes_clean():
    for lt_id, lt in library.letter_types().items():
        s = LetterSpec(lt_id, RecipientClass(lt["recipient_class"]),
                       deadline_days=lt.get("default_deadline_days"))
        assert checks.run_all(compose(s)) == [], f"{lt_id} produced findings"


def test_client_letters_skip_the_outbound_only_checks():
    letter = compose(LetterSpec("client_hearing_report", RecipientClass.CLIENT, deadline_days=14))
    assert not [f for f in checks.run_all(letter) if "no solicitor" in f.message]
