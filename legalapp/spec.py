"""The LetterSpec is the seam between every component.

It carries no personal detail -- only the shape of the letter. That is what
makes it diffable, re-runnable and safe to send to a model: "the same letter but
to a litigant in person" is a one-field change that re-routes tone, review path
and salutation together.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum


class RecipientClass(str, Enum):
    CLIENT = "client"
    OTHER_SIDE_SOLICITORS = "other_side_solicitors"
    LITIGANT_IN_PERSON = "litigant_in_person"
    COURT = "court"

    @property
    def is_outbound(self) -> bool:
        """Anyone other than our own client -- the risk review path."""
        return self is not RecipientClass.CLIENT

    @property
    def unrepresented(self) -> bool:
        return self is RecipientClass.LITIGANT_IN_PERSON


@dataclass
class LetterSpec:
    letter_type: str
    recipient_class: RecipientClass
    jurisdiction: str = "EW"
    privileged: bool = False           # marked Without Prejudice
    intent: str = ""                   # the fee earner's line of instruction
    deadline_days: int | None = None
    suppress_address: bool = False     # client's address withheld -- safeguarding
    include: list[str] = field(default_factory=list)   # optional paragraphs chosen
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["recipient_class"] = self.recipient_class.value
        return d

    def to_json(self, **kw) -> str:
        return json.dumps(self.to_dict(), indent=2, **kw)

    @classmethod
    def from_dict(cls, d: dict) -> "LetterSpec":
        d = dict(d)
        d["recipient_class"] = RecipientClass(d["recipient_class"])
        return cls(**d)
