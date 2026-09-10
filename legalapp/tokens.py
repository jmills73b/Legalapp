"""The token dictionary.

Every piece of personal detail in a letter is a typed placeholder. Tokens are the
output, not a defect to be cleaned up -- and they are also the seam a case
management system maps onto later, without anything else in the design changing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

#: Matches a placeholder in letter text: [CLIENT_FULL_NAME], [CHILD_1_NAME].
TOKEN_RE = re.compile(r"\[([A-Z][A-Z0-9_]*)\]")


class TokenType(str, Enum):
    PERSON = "person"
    DATE = "date"
    ADDRESS = "address"
    REFERENCE = "reference"
    MONEY = "money"
    TEXT = "text"


@dataclass(frozen=True)
class TokenDef:
    id: str
    type: TokenType
    description: str
    required: bool = True
    #: Computed by the app at merge time rather than typed by the fee earner.
    derived: str | None = None
    #: Repeating tokens carry an index: CHILD_1_NAME, CHILD_2_NAME, ...
    indexed: bool = False


_DEFS: list[TokenDef] = [
    TokenDef("CLIENT_FULL_NAME", TokenType.PERSON, "Our client's full name"),
    TokenDef("CLIENT_SALUTATION", TokenType.PERSON, "How our client is addressed, e.g. 'Ms Patel'"),
    TokenDef("OTHER_PARTY_NAME", TokenType.PERSON, "The other party's full name"),
    TokenDef("OTHER_FIRM_NAME", TokenType.TEXT, "The other side's firm", required=False),
    TokenDef("CHILD_N_NAME", TokenType.PERSON, "A child's name", indexed=True, required=False),
    TokenDef("CHILD_N_DOB", TokenType.DATE, "A child's date of birth", indexed=True, required=False),
    TokenDef("MATTER_REF", TokenType.REFERENCE, "Our own file reference"),
    TokenDef("THEIR_REF", TokenType.REFERENCE, "The recipient's reference", required=False),
    TokenDef("CASE_NO", TokenType.REFERENCE, "Court case number", required=False),
    TokenDef("COURT_NAME", TokenType.TEXT, "The court seised of the matter", required=False),
    TokenDef("HEARING_DATE", TokenType.DATE, "Date of the next hearing", required=False),
    TokenDef("LETTER_DATE", TokenType.DATE, "Date of this letter", derived="today"),
    TokenDef(
        "RESPONSE_DEADLINE",
        TokenType.DATE,
        "Date by which a reply is requested",
        derived="letter_date + deadline_days",
        required=False,
    ),
    TokenDef("FEE_EARNER_NAME", TokenType.PERSON, "Fee earner signing the letter"),
    TokenDef("FEE_EARNER_ROLE", TokenType.TEXT, "Their role, e.g. 'Senior Associate'"),
    TokenDef("SUPERVISOR_NAME", TokenType.PERSON, "The supervising solicitor", required=False),
    TokenDef("FIRM_NAME", TokenType.TEXT, "Our firm"),
    TokenDef(
        "FIRM_ADDRESS_BLOCK",
        TokenType.ADDRESS,
        "Our address block -- suppressed where confidentiality applies",
        required=False,
    ),
    TokenDef("RECIPIENT_SALUTATION", TokenType.TEXT, "Salutation, e.g. 'Dear Sirs'"),
    TokenDef("DISCLOSURE_DUE_DATE", TokenType.DATE, "Date disclosure fell due", required=False),
]

DICTIONARY: dict[str, TokenDef] = {d.id: d for d in _DEFS}

#: Indexed tokens are declared once as CHILD_N_NAME and used as CHILD_1_NAME.
_INDEX_RE = re.compile(r"_(\d+)_")


def canonical(token_id: str) -> str:
    """CHILD_2_NAME -> CHILD_N_NAME. Leaves unindexed tokens alone."""
    return _INDEX_RE.sub("_N_", token_id, count=1)


def lookup(token_id: str) -> TokenDef | None:
    return DICTIONARY.get(token_id) or DICTIONARY.get(canonical(token_id))


def used_in(text: str) -> list[str]:
    """Token ids appearing in text, in order of first appearance."""
    seen: dict[str, None] = {}
    for m in TOKEN_RE.finditer(text):
        seen.setdefault(m.group(1), None)
    return list(seen)


def strip_tokens(text: str, fill: str = " ") -> str:
    """Blank out placeholders so a scanner sees only the letter's own prose."""
    return TOKEN_RE.sub(lambda m: fill * (len(m.group(0))), text)


def unknown_tokens(text: str) -> list[str]:
    return [t for t in used_in(text) if lookup(t) is None]
