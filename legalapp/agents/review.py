"""Tone & conduct, and risk review -- the judgement half.

The lexicon in checks/tone.py catches formulaic inflammatory language for free.
What is left needs a model: whether a position reads as an accusation, whether
the letter proposes anything, whether a deadline is reasoned.

One rule holds throughout: model findings are never blocking. Only deterministic
checks block an export, because only they are reliable enough to be trusted with
a veto a fee earner cannot argue with.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..findings import Finding, Severity
from ..spec import RecipientClass
from .client import assert_no_pii, parse

TONE_SYSTEM = """\
You review a draft letter from a family law solicitor in England and Wales for \
tone and professional conduct.

Most family solicitors here practise under the Resolution Code of Practice, which \
requires constructive, non-confrontational correspondence. In financial remedy the \
general rule is no order as to costs (FPR 28.3(6)), subject to the court taking a \
broad view of litigation conduct including how a party has corresponded and \
negotiated (PD28A para 4.4). An inflammatory letter can cost the client money.

Check, for each paragraph:
- Is every position stated as a position rather than as an accusation?
- Does the letter propose something? A letter that only demands has nowhere to go.
- Is any deadline framed neutrally, with a reason, and long enough to be reasonable?
- Is the language child-focused -- arrangements for the children, not rights over them?

The letter contains placeholders like [CLIENT_FULL_NAME]. That is correct and is \
never a finding. Report only what you would actually raise with the fee earner; \
an empty list is a good outcome. Address every finding to a paragraph id."""

LIP_ADDENDUM = """\

This letter goes to someone with no solicitor. Apply the higher standard for a \
first letter to an unrepresented person: it must be non-threatening, explain \
plainly what is happening, avoid a deadline too short to act on, and encourage \
them to take their own legal advice."""

RISK_SYSTEM = """\
You review a draft letter leaving a family law firm in England and Wales, for \
risk. This is a different lens from tone. Check:

- Does the letter make an admission the client may not have authorised?
- Does it disclose something not yet disclosable -- a financial fact, an address, \
  the existence of advice taken?
- Is it correctly marked, or correctly not marked, Without Prejudice?
- Does it inadvertently give legal advice to an unrepresented recipient?
- Does it commit the client to a position beyond the stated intent of the letter?

The letter contains placeholders like [CLIENT_FULL_NAME]. That is correct and is \
never a finding. Report only what you would actually raise. Address every finding \
to a paragraph id."""


class ReviewFinding(BaseModel):
    paragraph_id: str = Field(description="the paragraph this concerns")
    kind: str = Field(description="short slug, e.g. no_proposal, unreasoned_deadline, admission")
    message: str = Field(description="one sentence stating the problem")
    suggestion: str = Field(description="what to do about it")
    excerpt: str = Field(default="", description="the words at issue, if any")


class ReviewResult(BaseModel):
    findings: list[ReviewFinding] = Field(default_factory=list)


def _render_for_review(letter) -> str:
    return "\n\n".join(f"[{p.id}]\n{p.text.strip()}" for p in letter.paragraphs)


def _run(letter, system: str, check_name: str) -> list[Finding]:
    body = _render_for_review(letter)
    # Structural enforcement, not a comment: nothing reaches a model until the
    # deterministic scanner agrees the text carries no literal personal detail.
    assert_no_pii(body, "draft letter")
    prompt = (
        f"Letter type: {letter.spec.letter_type}\n"
        f"Recipient: {letter.spec.recipient_class.value}\n"
        f"Stated intent: {letter.spec.intent or '(none given)'}\n"
        f"Deadline requested: {letter.spec.deadline_days or 'none'} days\n\n"
        f"Draft:\n\n{body}"
    )
    result = parse(system=system, prompt=prompt, output_format=ReviewResult)
    return [
        Finding(
            check=check_name,
            severity=Severity.ADVISORY,  # never blocking: only deterministic checks veto
            paragraph_id=f.paragraph_id,
            message=f.message,
            excerpt=f.excerpt,
            suggestion=f.suggestion,
        )
        for f in result.findings
    ]


def tone_and_conduct(letter) -> list[Finding]:
    """Runs on every letter, including letters to our own client."""
    system = TONE_SYSTEM
    if letter.spec.recipient_class.unrepresented:
        system += LIP_ADDENDUM
    return _run(letter, system, "tone_conduct")


def risk_review(letter) -> list[Finding]:
    """Runs only on correspondence leaving the firm."""
    if not letter.spec.recipient_class.is_outbound:
        return []
    return _run(letter, RISK_SYSTEM, "risk_review")


def review(letter) -> list[Finding]:
    return tone_and_conduct(letter) + risk_review(letter)
