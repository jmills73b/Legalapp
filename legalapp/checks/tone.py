"""The deterministic half of tone and conduct.

Inflammatory correspondence is formulaic, so a lexicon catches most of it for
free. The judgement half -- is there a proposal, is the deadline reasoned, is
the language child-focused -- needs a model and lives in agents/review.py.
"""
from __future__ import annotations

import re

from ..findings import Finding, Severity
from ..library import tone as _lexicon

CHECK = "tone_lexicon"

_PERSON_NEAR = r"(?:your client|the (?:father|mother|applicant|respondent)|he|she|they)"


def scan(text: str, paragraph_id: str = "letter", to_other_side: bool = True,
         children_matter: bool = False) -> list[Finding]:
    lex = _lexicon()
    findings: list[Finding] = []

    for entry in lex["banned_phrases"]:
        for m in re.finditer(entry["pattern"], text, flags=re.I):
            findings.append(
                Finding(
                    check=CHECK,
                    severity=Severity.ADVISORY,
                    paragraph_id=paragraph_id,
                    message=entry["why"],
                    excerpt=m.group(0),
                    suggestion=entry["suggestion"],
                )
            )

    adjectives = "|".join(lex["conduct_adjectives"])
    for m in re.finditer(rf"{_PERSON_NEAR}\W+(?:\w+\W+){{0,3}}?\b({adjectives})\b", text, flags=re.I):
        findings.append(
            Finding(
                check=CHECK,
                severity=Severity.ADVISORY,
                paragraph_id=paragraph_id,
                message=f"{m.group(1)!r} characterises a person rather than describing an act.",
                excerpt=m.group(0),
                suggestion="Describe what happened and leave the characterisation out.",
            )
        )

    for entry in lex.get("child_focus", []):
        if not children_matter:
            break
        for m in re.finditer(entry["pattern"], text, flags=re.I):
            findings.append(
                Finding(
                    check=CHECK,
                    severity=Severity.ADVISORY,
                    paragraph_id=paragraph_id,
                    message=entry["why"],
                    excerpt=m.group(0),
                    suggestion=entry["suggestion"],
                )
            )

    if to_other_side:
        for m in re.finditer(r"[^.!?\n]*\?", text):
            question = m.group(0).strip()
            if question.lower().startswith(("would you", "could you", "please could", "may we", "can you")):
                continue  # a genuine request, not a rhetorical jab
            findings.append(
                Finding(
                    check=CHECK,
                    severity=Severity.ADVISORY,
                    paragraph_id=paragraph_id,
                    message="Question put to the other side reads as rhetorical.",
                    excerpt=question[:100],
                    suggestion="Put it as a request, or state the position instead.",
                )
            )
    return findings
