"""Intake: a fee earner's sentence -> a LetterSpec.

Its job is not to interrogate. It resolves the letter type and the fields that
change the letter's structure and review path -- and nothing else. It never asks
for, and is never given, a name, a date or a reference.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .. import library
from ..spec import LetterSpec, RecipientClass
from .client import AgentUnavailable, parse

SYSTEM = """\
You resolve a family law fee earner's request into a letter specification, for a \
solicitors' practice in England and Wales.

You choose the shape of the letter only. You never write letter content, and you \
never record a name, date, address, sum of money or case reference -- those are \
supplied later as typed placeholders by the fee earner, and must not appear in \
your output.

recipient_class is the most consequential field, because it decides the review \
path: 'litigant_in_person' means the recipient has no solicitor and the letter \
carries the highest tone risk; 'client' means the letter contains advice.

If the request does not clearly match one letter type, set confidence to 'low' \
and list the nearest candidates in alternatives."""


class IntakeResult(BaseModel):
    letter_type: str = Field(description="id of the chosen letter type")
    recipient_class: str = Field(description="client | other_side_solicitors | litigant_in_person | court")
    privileged: bool = Field(description="true if the letter should be marked Without Prejudice")
    deadline_days: int | None = Field(default=None, description="days for a reply, null if none asked")
    intent: str = Field(description="one line: what this letter is to achieve")
    confidence: str = Field(description="high | medium | low")
    alternatives: list[str] = Field(default_factory=list, description="other plausible letter type ids")


def resolve(request: str) -> tuple[LetterSpec, IntakeResult]:
    types = library.letter_types()
    catalogue = "\n".join(
        f"- {t['id']}: {t['name']} (to {t['recipient_class']}, "
        f"WP {t['wp_marking']}, default deadline {t.get('default_deadline_days', 'none')} days)"
        for t in types.values()
    )
    result = parse(
        system=SYSTEM,
        prompt=f"Available letter types:\n{catalogue}\n\nThe fee earner asks:\n{request!r}",
        output_format=IntakeResult,
        effort="low",  # structured extraction, not judgement
    )
    if result.letter_type not in types:
        raise AgentUnavailable(
            f"intake chose {result.letter_type!r}, which is not in the catalogue"
        )
    lt = types[result.letter_type]
    spec = LetterSpec(
        letter_type=result.letter_type,
        recipient_class=RecipientClass(result.recipient_class),
        privileged=result.privileged and lt["wp_marking"] != "forbidden",
        intent=result.intent,
        deadline_days=result.deadline_days or lt.get("default_deadline_days"),
    )
    return spec, result
