from . import pii, register, structure, terminology, tone  # noqa: F401


def run_all(letter, *, to_other_side: bool | None = None) -> list:
    """Every deterministic check, over an assembled letter.

    Runs on every iteration of the revision loop, because it costs nothing.
    """
    from .. import library
    from ..findings import sort_findings

    if to_other_side is None:
        to_other_side = letter.spec.recipient_class.is_outbound
    vocab = library.vocabulary()
    children = library.letter_types()[letter.spec.letter_type].get("children_matter", False)
    findings = list(structure.scan(letter)) + list(register.scan(letter))
    for para in letter.paragraphs:
        findings += pii.scan(para.text, para.id, extra_vocab=vocab)
        findings += terminology.scan(para.text, para.id)
        findings += tone.scan(para.text, para.id, to_other_side=to_other_side,
                              children_matter=children)
    return sort_findings(findings)
