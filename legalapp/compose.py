"""Assembly: letter type + library -> a paragraph sequence.

Deterministic. The only model-written content is the optional bespoke paragraph,
which arrives already drafted and is spliced in by id like any other.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import library
from .spec import LetterSpec
from .tokens import used_in


@dataclass
class Paragraph:
    id: str
    text: str
    role: str
    #: "library:<id>@<version>" or "generated:<spec-hash>" -- provenance, always.
    source: str


@dataclass
class Letter:
    spec: LetterSpec
    paragraphs: list[Paragraph] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(p.text.strip() for p in self.paragraphs)

    @property
    def tokens(self) -> list[str]:
        return used_in(self.text)

    def paragraph(self, pid: str) -> Paragraph | None:
        return next((p for p in self.paragraphs if p.id == pid), None)

    def replace(self, pid: str, text: str) -> None:
        """Patch one paragraph. Every other byte of the letter is untouched --
        which is what makes the revision loop converge."""
        for p in self.paragraphs:
            if p.id == pid:
                p.text = text
                p.source = f"{p.source}+patched"
                return
        raise KeyError(pid)


def compose(spec: LetterSpec, bespoke: dict[str, str] | None = None) -> Letter:
    types, paras = library.letter_types(), library.paragraphs()
    if spec.letter_type not in types:
        raise KeyError(f"unknown letter type {spec.letter_type!r}; try `legalapp letters`")
    lt = types[spec.letter_type]
    letter = Letter(spec=spec)

    if spec.privileged and lt["wp_marking"] != "forbidden":
        p = paras["hdr_wp"]
        letter.paragraphs.append(Paragraph("hdr_wp", p["text"], p["role"], f"library:hdr_wp@{p['version']}"))

    for pid in lt["paragraphs"]:
        p = paras[pid]
        text = p["text"]
        if pid == "hdr_refs" and spec.suppress_address:
            text = text.replace("[FIRM_ADDRESS_BLOCK]\n", "")
        letter.paragraphs.append(Paragraph(pid, text, p["role"], f"library:{pid}@{p['version']}"))

    for pid, text in (bespoke or {}).items():
        letter.paragraphs.append(Paragraph(pid, text, "body", "generated"))

    return letter
