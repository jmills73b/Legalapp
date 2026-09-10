# Legalapp

AI agent system for composing legal documents from a plain-language description of the request.

```
$ legalapp draft "mutual NDA, Delaware, 2yr, Acme Inc + Jane Doe"
```

**Status:** design phase. See [docs/DESIGN.md](docs/DESIGN.md) for the architecture — agent roster,
pipeline, interface contract, and build order.

Output is a draft for attorney review, not legal advice and not an executable instrument.
