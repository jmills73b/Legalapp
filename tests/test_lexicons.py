from legalapp.checks import terminology, tone
from legalapp.findings import Severity

DEPRECATED = [
    ("Our client seeks custody of the children.", "child arrangements"),
    ("We enclose the decree absolute.", "final order"),
    ("The decree nisi was pronounced.", "conditional order"),
    ("This is an ancillary relief matter.", "financial remedy"),
    ("The petitioner has filed.", "applicant"),
    ("A residence order was made.", "child arrangements order"),
]


def test_deprecated_terms_are_flagged_and_fixed():
    for text, replacement in DEPRECATED:
        findings = terminology.scan(text)
        assert findings, f"missed deprecated term in {text!r}"
        assert all(f.severity is Severity.AUTO_FIXED for f in findings)
        fixed, _ = terminology.apply_fixes(text)
        assert replacement in fixed


def test_auto_fix_is_never_silent():
    _, findings = terminology.apply_fixes("We enclose the decree absolute.")
    assert findings and "out of date" in findings[0].message


def test_access_to_the_file_is_not_a_deprecated_term():
    # "access" is only wrong in the children sense.
    assert terminology.scan("Please confirm you have access to the file.") == []


BANNED = [
    "We note with some surprise that nothing has been provided.",
    "Your client has singularly failed to reply.",
    "It is regrettable that no response was forthcoming.",
    "As you are well aware, the deadline has passed.",
    "We will not hesitate to apply to the court.",
]


def test_inflammatory_phrases_are_flagged():
    for text in BANNED:
        findings = tone.scan(text)
        assert findings, f"missed inflammatory phrase in {text!r}"
        assert all(f.severity is Severity.ADVISORY for f in findings)


def test_conduct_adjective_applied_to_a_person():
    findings = tone.scan("Your client's obstruction is deliberate.")
    assert any("characterises a person" in f.message for f in findings)


def test_constructive_letter_passes():
    text = ("We would be grateful for your response by [RESPONSE_DEADLINE]. We suggest that "
            "date so that the parties can keep to the directions timetable. If there is a "
            "difficulty, please telephone the writer.")
    assert tone.scan(text) == []


def test_genuine_request_is_not_treated_as_rhetorical():
    assert tone.scan("Could you confirm the position by return?") == []


def test_rhetorical_question_to_the_other_side_is_flagged():
    assert tone.scan("Does your client seriously expect us to wait?")
