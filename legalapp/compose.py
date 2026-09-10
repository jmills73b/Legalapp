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


def optional_paragraphs(letter_type: str) -> list[dict]:
    """The menu of paragraphs a fee earner may add to this letter type."""
    return library.letter_types()[letter_type].get("optional", [])


def _apply_optional(letter: Letter, lt: dict, include: list[str], paras: dict) -> None:
    """Insert or swap chosen optional paragraphs.

    An entry with `replaces` swaps a core paragraph out -- that is how a second
    chase replaces a first one rather than sitting awkwardly beside it. An entry
    with `after` is inserted following the paragraph it names.
    """
    menu = {entry["id"]: entry for entry in lt.get("optional", [])}
    unknown = [i for i in include if i not in menu]
    if unknown:
        raise KeyError(
            f"{unknown} not available for {lt['id']}; try `legalapp options {lt['id']}`"
        )
    # Two paragraphs that replace the same core paragraph are alternatives, not
    # additions -- a second chase and a final chase cannot both be the letter.
    claimed: dict[str, str] = {}
    for pid in include:
        target = menu[pid].get("replaces")
        if target and target in claimed:
            raise ValueError(
                f"{pid!r} and {claimed[target]!r} are alternatives -- both replace "
                f"{target!r}. Choose one."
            )
        if target:
            claimed[target] = pid
    for pid in include:
        entry = menu[pid]
        p = paras[pid]
        block = Paragraph(pid, p["text"], p["role"], f"library:{pid}@{p['version']}")
        replaces = entry.get("replaces")
        if replaces and letter.paragraph(replaces) is not None:
            idx = next(i for i, x in enumerate(letter.paragraphs) if x.id == replaces)
            letter.paragraphs[idx] = block
            continue
        anchor = entry.get("after")
        if anchor and letter.paragraph(anchor) is not None:
            idx = next(i for i, x in enumerate(letter.paragraphs) if x.id == anchor)
            letter.paragraphs.insert(idx + 1, block)
        else:
            closing = next((i for i, x in enumerate(letter.paragraphs)
                            if x.role in ("closing", "enclosure")), len(letter.paragraphs))
            letter.paragraphs.insert(closing, block)


def compose(spec: LetterSpec, bespoke: dict[str, str] | None = None,
            include: list[str] | None = None) -> Letter:
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

    if include:
        _apply_optional(letter, lt, include, paras)

    for pid, text in (bespoke or {}).items():
        letter.paragraphs.append(Paragraph(pid, text, "body", "generated"))

    return letter
