"""Command line. One verb per step of the fee earner's journey."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from . import checks, library
from .compose import compose
from .findings import Severity, blocking, sort_findings
from .render import fill_sheet, merge, values_template
from .spec import LetterSpec, RecipientClass
from .tokens import DICTIONARY

_MARK = {Severity.BLOCKING: "!", Severity.AUTO_FIXED: "~", Severity.ADVISORY: "-"}
_LABEL = {Severity.BLOCKING: "BLOCKING", Severity.AUTO_FIXED: "auto-fixed", Severity.ADVISORY: "advisory"}


def _print_findings(findings, stream=sys.stdout) -> None:
    if not findings:
        print("  no findings", file=stream)
        return
    current = None
    for f in sort_findings(findings):
        if f.severity != current:
            current = f.severity
            print(f"\n  {_LABEL[f.severity]}", file=stream)
        excerpt = f" {f.excerpt!r}" if f.excerpt else ""
        print(f"  {_MARK[f.severity]} [{f.paragraph_id}]{excerpt}", file=stream)
        print(f"      {f.message}", file=stream)
        if f.suggestion:
            print(f"      -> {f.suggestion}", file=stream)


def cmd_letters(args) -> int:
    for lt in library.letter_types().values():
        wp = lt["wp_marking"]
        print(f"  {lt['id']:<32} {lt['name']}")
        print(f"  {'':<32} to: {lt['recipient_class']} | WP: {wp} | "
              f"default deadline: {lt.get('default_deadline_days', '-')}d")
    return 0


def cmd_tokens(args) -> int:
    for d in DICTIONARY.values():
        flag = "required" if d.required else "optional"
        extra = f" [derived: {d.derived}]" if d.derived else ""
        print(f"  [{d.id}]".ljust(28), f"{d.type.value:<10} {flag:<9} {d.description}{extra}")
    return 0


def cmd_draft(args) -> int:
    types = library.letter_types()
    if args.letter_type not in types:
        print(f"unknown letter type {args.letter_type!r}. Available:", file=sys.stderr)
        for t in types:
            print(f"  {t}", file=sys.stderr)
        return 2
    lt = types[args.letter_type]
    spec = LetterSpec(
        letter_type=args.letter_type,
        recipient_class=RecipientClass(args.to or lt["recipient_class"]),
        # A letter type that requires the marking gets it without being asked.
        privileged=args.wp or lt["wp_marking"] == "required",
        intent=args.note or "",
        deadline_days=args.deadline if args.deadline is not None else lt.get("default_deadline_days"),
        suppress_address=args.suppress_address,
    )
    letter = compose(spec)
    findings = checks.run_all(letter)

    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = args.letter_type
    (outdir / f"{stem}.txt").write_text(letter.text + "\n", encoding="utf-8")
    (outdir / f"{stem}.fill.md").write_text(fill_sheet(letter), encoding="utf-8")
    (outdir / f"{stem}.values.json").write_text(
        json.dumps(values_template(letter), indent=2) + "\n", encoding="utf-8")
    (outdir / f"{stem}.spec.json").write_text(spec.to_json() + "\n", encoding="utf-8")

    print(f"drafted  {lt['name']}")
    print(f"  to     {spec.recipient_class.value}")
    print(f"  files  {outdir/stem}.txt, .fill.md, .values.json, .spec.json")
    print(f"\n  tokens to complete: {len(letter.tokens)}")
    for tok in letter.tokens:
        from .tokens import lookup
        d = lookup(tok)
        note = "derived" if (d and d.derived) else ("optional" if d and not d.required else "")
        print(f"    [{tok}]".ljust(30), (d.type.value if d else "?").ljust(10), note)
    if lt.get("bespoke_slot"):
        print(f"\n  bespoke slot: {lt['bespoke_slot']}")
    print("\n  deterministic checks:")
    _print_findings(findings)
    return 1 if blocking(findings) else 0


def cmd_check(args) -> int:
    path = pathlib.Path(args.file)
    text = path.read_text(encoding="utf-8")
    vocab = library.vocabulary()
    findings = (
        checks.pii.scan(text, path.name, extra_vocab=vocab)
        + checks.terminology.scan(text, path.name)
        + checks.tone.scan(text, path.name, to_other_side=not args.to_client)
    )
    print(f"checked {path}")
    _print_findings(findings)
    n = len(blocking(findings))
    print(f"\n  {len(findings)} finding(s), {n} blocking")
    return 1 if n else 0


def cmd_merge(args) -> int:
    text = pathlib.Path(args.file).read_text(encoding="utf-8")
    values = json.loads(pathlib.Path(args.values).read_text(encoding="utf-8"))
    spec = None
    specfile = pathlib.Path(args.file).with_suffix("").with_suffix(".spec.json")
    if specfile.exists():
        spec = LetterSpec.from_dict(json.loads(specfile.read_text(encoding="utf-8")))
    merged, unresolved = merge(text, values, spec)
    out = pathlib.Path(args.out) if args.out else pathlib.Path(args.file).with_suffix(".merged.txt")
    out.write_text(merged, encoding="utf-8")
    print(f"merged -> {out}")
    if unresolved:
        print("  unresolved required tokens:")
        for t in unresolved:
            print(f"    [{t}]")
        return 1
    print("  all required tokens resolved")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="legalapp", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("letters", help="list available letter types").set_defaults(fn=cmd_letters)
    sub.add_parser("tokens", help="show the token dictionary").set_defaults(fn=cmd_tokens)

    d = sub.add_parser("draft", help="draft a letter, generically")
    d.add_argument("letter_type")
    d.add_argument("--deadline", type=int, help="days for a reply")
    d.add_argument("--note", help="what you want the letter to do")
    d.add_argument("--to", choices=[r.value for r in RecipientClass], help="override recipient class")
    d.add_argument("--wp", action="store_true", help="mark Without Prejudice")
    d.add_argument("--suppress-address", action="store_true",
                   help="address confidentiality applies to this matter")
    d.add_argument("--out", default="drafts")
    d.set_defaults(fn=cmd_draft)

    c = sub.add_parser("check", help="run the deterministic checks over any letter")
    c.add_argument("file")
    c.add_argument("--to-client", action="store_true", help="letter is to our own client")
    c.set_defaults(fn=cmd_check)

    m = sub.add_parser("merge", help="fill the tokens locally -- no model involved")
    m.add_argument("file")
    m.add_argument("--values", required=True)
    m.add_argument("--out")
    m.set_defaults(fn=cmd_merge)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
