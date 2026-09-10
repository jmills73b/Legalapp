"""Structural assertions against the letter type's own policy."""
from __future__ import annotations

from .. import library
from ..findings import Finding, Severity
from ..tokens import unknown_tokens, used_in

CHECK = "structure"


def scan(letter) -> list[Finding]:
    lt = library.letter_types()[letter.spec.letter_type]
    present = {p.id for p in letter.paragraphs}
    text = letter.text
    tokens = set(used_in(text))
    out: list[Finding] = []

    def add(sev, pid, msg, suggestion=""):
        out.append(Finding(CHECK, sev, pid, msg, suggestion=suggestion))

    for pid in lt.get("required_paragraphs", []):
        if pid not in present:
            add(Severity.BLOCKING, pid, f"Letter type requires paragraph {pid!r}, which is absent.")

    marking = lt.get("wp_marking", "optional")
    has_wp = "hdr_wp" in present
    if marking == "forbidden" and has_wp:
        add(Severity.BLOCKING, "hdr_wp",
            "This letter type must not be marked Without Prejudice -- it is an open letter.",
            "Remove the marking, or use a letter type that is privileged.")
    if marking == "required" and not has_wp:
        add(Severity.BLOCKING, "hdr_wp",
            "This letter type must be marked Without Prejudice.",
            "Set privileged = true on the spec.")

    for tok in unknown_tokens(text):
        add(Severity.BLOCKING, "letter", f"[{tok}] is not in the token dictionary.",
            "Add it to legalapp/tokens.py or use an existing token.")

    if lt.get("requires_deadline") and letter.spec.deadline_days:
        if "RESPONSE_DEADLINE" not in tokens:
            add(Severity.BLOCKING, "letter",
                "A deadline was requested but the letter contains no [RESPONSE_DEADLINE].",
                "Include a paragraph that states the date by which a reply is asked for.")

    declared = lt.get("enclosures", [])
    enclosure_paras = [p for p in letter.paragraphs if p.role == "enclosure"]
    if declared and not enclosure_paras:
        add(Severity.BLOCKING, "letter",
            f"Letter type declares {len(declared)} enclosure(s) but none is listed in the letter.")
    if enclosure_paras and not declared:
        add(Severity.ADVISORY, enclosure_paras[0].id,
            "The letter lists an enclosure the letter type does not declare.",
            "Check the enclosure is actually attached.")

    if letter.spec.suppress_address and "FIRM_ADDRESS_BLOCK" in tokens:
        add(Severity.BLOCKING, "hdr_refs",
            "Address confidentiality applies to this matter but the letter still carries an address block.",
            "Address suppression is a safeguarding control, not a formatting preference.")

    return out
