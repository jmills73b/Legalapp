"""The invented-PII check.

Letters are generated generically. That inverts the usual validator: a leftover
placeholder is the *intended* output, and the dangerous failure is a model that
helpfully writes a plausible name instead of emitting [CLIENT_FULL_NAME] -- a
letter that looks finished and is wrong in a way a busy fee earner may not catch.

So: no name-shaped, date-shaped, address-shaped, money-shaped or reference-shaped
text may appear anywhere outside a declared placeholder.
"""
from __future__ import annotations

import re

from ..findings import Finding, Severity
from ..tokens import TOKEN_RE

CHECK = "invented_pii"

# --- vocabulary that legitimately looks like a name -------------------------
# Capitalised legal English. Anything here is expected in a generic letter.
LEGAL_VOCAB = {
    # correspondence furniture
    "Dear", "Sirs", "Madam", "Sir", "Yours", "Faithfully", "Sincerely", "Re",
    "Our", "Your", "Ref", "Reference", "Enc", "Encs", "Enclosures", "By", "Post",
    "Email", "Recorded", "Delivery", "Strictly", "Private", "Confidential",
    "Without", "Prejudice", "Save", "As", "To", "Costs", "Open", "Letter",
    # courts, bodies, procedure
    "Family", "Court", "Central", "Principal", "Registry", "District", "Judge",
    "Circuit", "Magistrates", "High", "Division", "The", "Law", "Society",
    "Resolution", "Code", "Practice", "Legal", "Aid", "Agency", "Cafcass",
    "First", "Directions", "Appointment", "Financial", "Dispute", "Resolution",
    "Final", "Hearing", "Conditional", "Order", "Child", "Arrangements",
    "Remedy", "Non", "Court", "Mediation", "Information", "Assessment",
    "Meeting", "Mediator", "Statement", "Issues", "Questionnaire", "Schedule",
    "Deficiencies", "Directions", "Application", "Applicant", "Respondent",
    "Petitioner", "Notice", "Acknowledgement", "Service", "Consent", "Undertaking",
    # instruments and forms
    "Act", "Rules", "Regulations", "Practice", "Direction", "Part", "Rule",
    "Section", "Schedule", "Form", "Forms", "Annex", "Appendix",
    "Children", "Matrimonial", "Causes", "Procedure", "Divorce", "Dissolution",
    "Separation", "Senior", "Trusts", "Land", "Appointment", "Trustees",
    # months are protected separately but appear in prose
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    # common sentence-initial words in this register
    "We", "I", "You", "If", "In", "It", "This", "That", "There", "Please",
    "Unless", "Should", "Where", "When", "While", "Whilst", "Although", "As",
    "Our", "Their", "His", "Her", "They", "Thank", "Further", "Following",
    "Accordingly", "However", "Therefore", "Given", "Once", "Both", "Either",
    "Neither", "Any", "All", "No", "None", "Such", "Subject", "Pursuant",
    "Alternatively", "Finally", "Firstly", "Secondly", "Lastly", "Meanwhile",
}

# Phrases protected wholesale before scanning: real citations and form names.
PROTECTED = [
    re.compile(r"\b(?:[A-Z][a-z]+ )+Act \d{4}\b"),
    re.compile(r"\bFamily Procedure Rules \d{4}\b"),
    re.compile(r"\bPractice Direction \d+[A-Z]?\b"),
    re.compile(r"\bFPR \d+\.\d+(?:\(\d+\))*\b"),
    re.compile(r"\bPD\d+[A-Z]?\b"),
    re.compile(r"\bs\.?\s?\d+[A-Z]?\b"),
    re.compile(r"\bsection \d+[A-Z]?\b", re.I),
    re.compile(r"\bForm [A-Z]\d?\b"),
    re.compile(r"\bC\d{3}[A-Z]?\b"),          # C100, C1A
    re.compile(r"\bFM\d\b"),                  # FM5
    re.compile(r"\bD\d{2,3}\b"),
]

# --- detectors --------------------------------------------------------------
# Party-name shape in a Re line: "Thompson v Thompson". The lowercase "v"
# breaks a capitalised run, so this needs its own detector.
CASE_STYLE = re.compile(r"\b([A-Z][a-z'\-]{1,}\s+v\.?\s+[A-Z][a-z'\-]{1,})\b")
TITLE_NAME = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Lord|Lady)\.?\s+([A-Z][a-z'\-]+)")
NAME_RUN = re.compile(r"\b([A-Z][a-z'\-]{1,}(?:\s+[A-Z][a-z'\-]{1,})+)\b")
DATE_LONG = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|"
    r"August|September|October|November|December)(?:\s+\d{4})?\b", re.I)
DATE_NUM = re.compile(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b")
POSTCODE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b")
CASE_REF = re.compile(r"\b[A-Z]{2}\d{2}[A-Z]\d{4,6}\b")
MONEY = re.compile(r"£\s?\d[\d,]*(?:\.\d{2})?")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PHONE = re.compile(r"\b(?:0\d{3}\s?\d{3}\s?\d{4}|0\d{2}\s?\d{4}\s?\d{4}|\+44\s?\d[\d\s]{8,})\b")
NI_NUMBER = re.compile(r"\b[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]\b")

_DETECTORS = [
    (TITLE_NAME, "a person's name"),
    (CASE_STYLE, "a person's name"),
    (NAME_RUN, "a person's name"),
    (DATE_LONG, "a date"),
    (DATE_NUM, "a date"),
    (POSTCODE, "a postcode"),
    (CASE_REF, "a case reference"),
    (MONEY, "a sum of money"),
    (EMAIL, "an email address"),
    (PHONE, "a telephone number"),
    (NI_NUMBER, "a National Insurance number"),
]

_SUGGESTED_TOKEN = {
    "a person's name": "[CLIENT_FULL_NAME] / [OTHER_PARTY_NAME] / [CHILD_1_NAME]",
    "a date": "[HEARING_DATE] / [RESPONSE_DEADLINE] / [LETTER_DATE]",
    "a postcode": "[FIRM_ADDRESS_BLOCK]",
    "a case reference": "[CASE_NO] / [MATTER_REF]",
    "a sum of money": "a declared money token",
    "an email address": "firm contact details are part of the letterhead, not the body",
    "a telephone number": "firm contact details are part of the letterhead, not the body",
    "a National Insurance number": "a declared reference token",
}


def _blank(text: str, match: re.Match) -> str:
    """Replace a span with spaces, preserving offsets so later spans still line up."""
    start, end = match.span()
    return text[:start] + (" " * (end - start)) + text[end:]


def _mask(text: str) -> str:
    """Blank placeholders and protected legal phrases before scanning."""
    for pattern in (TOKEN_RE, *PROTECTED):
        while True:
            m = pattern.search(text)
            if not m:
                break
            text = _blank(text, m)
    return text


def _is_vocab_run(phrase: str) -> bool:
    return all(word in LEGAL_VOCAB for word in phrase.split())


def scan(text: str, paragraph_id: str = "letter", extra_vocab: set[str] | None = None) -> list[Finding]:
    """Return a blocking finding for every literal PII-shaped span in text."""
    vocab = LEGAL_VOCAB | (extra_vocab or set())
    masked = _mask(text)
    findings: list[Finding] = []
    # Keyed on the excerpt, not its offset: overlapping detectors find the same
    # name at different starts ("Dear Mr Okafor" vs "Mr Okafor") and a fee
    # earner should see it once.
    seen: set[str] = set()

    for pattern, kind in _DETECTORS:
        for m in pattern.finditer(masked):
            excerpt = m.group(0).strip()
            if kind == "a person's name":
                phrase = m.group(1) if m.groups() else excerpt
                if all(w in vocab for w in phrase.split()):
                    continue
                # A title makes it a name regardless of vocabulary.
                if pattern is NAME_RUN and any(w in vocab for w in phrase.split()):
                    # Mixed run such as "Financial Remedy Smith" -- report only
                    # the words the vocabulary does not account for.
                    unknown = [w for w in phrase.split() if w not in vocab]
                    if len(unknown) < 2:
                        continue
                    excerpt = " ".join(unknown)
            key = excerpt.lower()
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(
                    check=CHECK,
                    severity=Severity.BLOCKING,
                    paragraph_id=paragraph_id,
                    message=f"Literal personal detail in the letter body -- looks like {kind}.",
                    excerpt=excerpt,
                    suggestion=f"Replace with a declared placeholder: {_SUGGESTED_TOKEN[kind]}",
                )
            )
    return findings
