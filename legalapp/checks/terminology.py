"""Deprecated terminology. Auto-fixed, never silent."""
from __future__ import annotations

import re

from ..findings import Finding, Severity
from ..library import terminology as _lexicon

CHECK = "deprecated_terminology"


def scan(text: str, paragraph_id: str = "letter") -> list[Finding]:
    findings: list[Finding] = []
    for entry in _lexicon():
        for m in re.finditer(entry["pattern"], text, flags=re.I):
            since = f" (renamed {entry['since']})" if entry.get("since") else ""
            findings.append(
                Finding(
                    check=CHECK,
                    severity=Severity.AUTO_FIXED,
                    paragraph_id=paragraph_id,
                    message=f"{m.group(0)!r} is out of date{since}. {entry['authority']}",
                    excerpt=m.group(0),
                    suggestion=f"Use {entry['replacement']!r}.",
                    replacement=entry["replacement"],
                )
            )
    return findings


def apply_fixes(text: str) -> tuple[str, list[Finding]]:
    """Return the corrected text and the findings describing what changed."""
    findings = scan(text)
    fixed = text
    for entry in _lexicon():
        fixed = re.sub(entry["pattern"], entry["replacement"], fixed, flags=re.I)
    return fixed, findings
