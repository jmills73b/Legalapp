"""Correspondence register: the conventions that make a letter read as a
solicitor's letter, and the extra duties owed to someone without one.

Three of these only ever fire on letters to an unrepresented person, which is
why the recipient class set at intake matters more than any other field.
"""
from __future__ import annotations

import re

from .. import library
from ..findings import Finding, Severity

CHECK = "register"

# A gloss follows the term it explains -- "a Form E, which is the form both of
# you use". Searching the whole sentence would accept "This is a financial
# remedy matter", where "this is" explains nothing.
_GLOSS = re.compile(r"\(|which is\b|which means\b|meaning\b|in other words\b|that is\b|i\.e\.", re.I)


def _lexicon():
    return library._load("lexicons/plain_language.yaml")


def salutation_signoff(letter) -> list[Finding]:
    """"Dear Sirs" takes "Yours faithfully"; a named salutation takes
    "Yours sincerely". Absolute in English practice, so it can safely block."""
    lt = library.letter_types()[letter.spec.letter_type]
    style = lt.get("salutation_style", "formal")
    ids = {p.id for p in letter.paragraphs}
    expected = "signoff_sincerely" if style == "named" else "signoff_faithfully"
    wrong = "signoff_faithfully" if style == "named" else "signoff_sincerely"
    if wrong in ids and expected not in ids:
        want = "Yours sincerely" if style == "named" else "Yours faithfully"
        return [Finding(
            CHECK, Severity.BLOCKING, wrong,
            f"A {style} salutation does not take this sign-off.",
            suggestion=f"Use {want!r}.",
        )]
    return []


def deadline_floor(letter) -> list[Finding]:
    """An unrepresented person needs time to take advice before replying."""
    lt = library.letter_types()[letter.spec.letter_type]
    floor = lt.get("min_deadline_days")
    days = letter.spec.deadline_days
    if floor and days and days < floor:
        return [Finding(
            CHECK, Severity.ADVISORY, "letter",
            f"A {days}-day deadline to someone without a solicitor is short; "
            f"this letter type suggests at least {floor} days.",
            suggestion="Lengthen it, or say in the letter why it has to be this short.",
        )]
    return []


def plain_language(text: str, paragraph_id: str) -> list[Finding]:
    """Terms of art used to a lay reader without a gloss.

    Applies to our own client as much as to a litigant in person -- correct
    vocabulary is not the same thing as comprehensible vocabulary.
    """
    out: list[Finding] = []
    for term in _lexicon()["terms"]:
        for m in re.finditer(rf"\b{re.escape(term)}\b", text, flags=re.I):
            if _GLOSS.search(_after_term(text, m.end())):
                continue
            out.append(Finding(
                CHECK, Severity.ADVISORY, paragraph_id,
                f"{term!r} is a term of art and the reader is not a lawyer.",
                excerpt=term,
                suggestion="Explain it in the same sentence, or use plain words.",
            ))
    return out


def advice_to_unrepresented(text: str, paragraph_id: str) -> list[Finding]:
    """We act for the other party and cannot advise this recipient -- except to
    tell them to get their own advice, which is required."""
    lex = _lexicon()
    exempt = re.compile("|".join(lex["advice_exemptions"]), re.I)
    out: list[Finding] = []
    for pattern in lex["advice_markers"]:
        for m in re.finditer(pattern, text, flags=re.I):
            sentence = _sentence_around(text, m.start())
            if exempt.search(sentence):
                continue
            out.append(Finding(
                CHECK, Severity.ADVISORY, paragraph_id,
                "Reads as advising a recipient we do not act for.",
                excerpt=sentence.strip()[:120],
                suggestion="State our client's position instead, and point them to their own solicitor.",
            ))
    return out


def _after_term(text: str, index: int) -> str:
    """The rest of the sentence following a term -- where its gloss would sit."""
    end = min((i for i in (text.find(".", index), text.find("\n", index)) if i != -1), default=len(text))
    return text[index:end + 1]


def _sentence_around(text: str, index: int) -> str:
    start = max(text.rfind(".", 0, index), text.rfind("\n", 0, index)) + 1
    end = min((i for i in (text.find(".", index), text.find("\n", index)) if i != -1), default=len(text))
    return text[start:end + 1]


def scan(letter) -> list[Finding]:
    lt = library.letter_types()[letter.spec.letter_type]
    out = salutation_signoff(letter) + deadline_floor(letter)

    # Two different triggers. A lay reader needs plain language whether or not
    # they are the other side -- our own client is a lay reader too. But the
    # advice check only applies to someone we do not act for: advising our own
    # client is the entire point of a client letter.
    lay_reader = lt.get("plain_language") or letter.spec.recipient_class.unrepresented
    unrepresented = letter.spec.recipient_class.unrepresented

    for p in letter.paragraphs:
        if lay_reader:
            out += plain_language(p.text, p.id)
        if unrepresented:
            out += advice_to_unrepresented(p.text, p.id)
    return out
