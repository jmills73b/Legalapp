"""Output: the letter, its fill sheet, and the local merge.

The merge is the point at which real names exist -- and it is deterministic
code, not a model call. The PII boundary is the model, not the application:
this module may hold a client's name, a prompt may not.
"""
from __future__ import annotations

import datetime as _dt
import re

from .tokens import DICTIONARY, TOKEN_RE, TokenType, canonical, lookup


def fill_sheet(letter) -> str:
    """The tokens a fee earner must complete, typed, in order of appearance."""
    lt_tokens = letter.tokens
    lines = [
        f"# Fill sheet -- {letter.spec.letter_type}",
        "",
        f"Recipient: {letter.spec.recipient_class.value}",
        f"Tokens to complete: {len(lt_tokens)}",
        "",
        "| Token | Type | Required | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for tok in lt_tokens:
        d = lookup(tok)
        if d is None:
            lines.append(f"| `[{tok}]` | ? | ? | **not in the dictionary** |")
            continue
        note = d.description
        if d.derived:
            note += f" (derived: {d.derived})"
        lines.append(
            f"| `[{tok}]` | {d.type.value} | {'yes' if d.required else 'optional'} | {note} |"
        )
    return "\n".join(lines) + "\n"


def _uk_date(d: _dt.date) -> str:
    """UK correspondence style: "1 October 2026", not "01 October 2026"."""
    return f"{d.day} {d:%B %Y}"


def derived_values(spec, letter_date: _dt.date | None = None) -> dict[str, str]:
    """Values the app computes rather than asking the fee earner to type."""
    today = letter_date or _dt.date.today()
    out = {"LETTER_DATE": _uk_date(today)}
    if spec.deadline_days:
        due = today + _dt.timedelta(days=spec.deadline_days)
        out["RESPONSE_DEADLINE"] = _uk_date(due)
    return out


_TYPE_HINT = {
    TokenType.DATE: "a date, e.g. 14 March 2026",
    TokenType.PERSON: "a name",
    TokenType.REFERENCE: "a reference",
    TokenType.MONEY: "an amount",
    TokenType.ADDRESS: "an address block",
    TokenType.TEXT: "text",
}


def merge(text: str, values: dict[str, str], spec=None, letter_date=None) -> tuple[str, list[str]]:
    """Substitute token values locally. Returns (merged text, unresolved tokens).

    No model is involved and none ever should be: this is a string substitution
    over values the fee earner typed.
    """
    resolved = dict(derived_values(spec, letter_date)) if spec is not None else {}
    resolved.update({k: v for k, v in values.items() if v not in (None, "")})

    unresolved: list[str] = []

    def sub(m: re.Match) -> str:
        tok = m.group(1)
        if tok in resolved:
            return str(resolved[tok])
        d = lookup(tok)
        if d is not None and not d.required:
            return m.group(0)  # optional and unsupplied -- leave visible
        unresolved.append(tok)
        return m.group(0)

    merged = TOKEN_RE.sub(sub, text)
    # Tidy lines that became empty because an optional block was dropped.
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    return merged, sorted(set(unresolved))


def values_template(letter) -> dict[str, str]:
    """A blank values file for the fill sheet, derived tokens omitted."""
    return {
        tok: ""
        for tok in letter.tokens
        if not (lookup(tok) and lookup(tok).derived)
    }
