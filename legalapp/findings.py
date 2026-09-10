"""Findings are the common currency between every check and every agent.

A finding is always addressed to a paragraph, never to the letter as a whole:
the patch loop rewrites only the paragraphs a finding names, which is what makes
the revision loop converge (see docs/DESIGN.md §3).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum


class Severity(str, Enum):
    #: Blocks export. Rare, and always right, or fee earners learn to route around it.
    BLOCKING = "blocking"
    #: Already corrected. Listed so the change is visible, never silent.
    AUTO_FIXED = "auto_fixed"
    #: The fee earner's judgement. Never blocks.
    ADVISORY = "advisory"


ORDER = {Severity.BLOCKING: 0, Severity.AUTO_FIXED: 1, Severity.ADVISORY: 2}


@dataclass
class Finding:
    check: str
    severity: Severity
    paragraph_id: str
    message: str
    excerpt: str = ""
    suggestion: str = ""
    #: Set by checks that can repair the text themselves.
    replacement: str | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        d.pop("replacement", None)
        return d


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (ORDER[f.severity], f.paragraph_id, f.check))


def blocking(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity is Severity.BLOCKING]
