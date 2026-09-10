# Legalapp

AI agent system for drafting family law correspondence (England & Wales) from a short description of the request.

```
$ legalapp letter form-e-chaser --deadline 14d
```

**Status:** design phase. See [docs/DESIGN.md](docs/DESIGN.md) for the architecture — agent roster,
pipeline, interface contract, and build order.

Letters are generated generically with typed placeholders where PII belongs — no client data
enters the system. Every letter is a draft for a solicitor to check and sign.
