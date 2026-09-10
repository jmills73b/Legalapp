# Legalapp

AI agent system for drafting family law correspondence (England & Wales) from a short description of the request.

```
$ legalapp letter form-e-chaser --deadline 14d
```

```
$ legalapp draft form_e_chaser --deadline 14
$ legalapp merge drafts/form_e_chaser.txt --values values.json
$ legalapp check some_existing_letter.txt
```

See [docs/DESIGN.md](docs/DESIGN.md) for the architecture — agent roster, pipeline,
interface contract, and build order.

## What works today

| | |
| --- | --- |
| Token dictionary + **invented-PII check** | done — the safety property everything else rests on |
| Deprecated terminology lexicon | done — auto-fixed, never silent |
| Tone lexicon (deterministic half) | done |
| Structure checks — WP marking, address suppression, enclosures | done |
| Register checks — salutation/sign-off, deadline floor, plain language, advice to a litigant in person | done |
| Paragraph library + composer + local merge | done, full 10-letter catalogue |
| Client vs outbound review split | done |
| Intake and review agents | written against the Claude API, not yet exercised live |

### Letter types

| Type | To | Notes |
| --- | --- | --- |
| `client_care_letter` | client | costs, supervision and complaints paragraphs enforced |
| `first_letter_unrepresented` | litigant in person | plain-language and no-advice checks; 21-day deadline floor |
| `first_letter_solicitors` | other side's solicitors | |
| `ncdr_proposal` | other side's solicitors | |
| `voluntary_disclosure_request` | other side's solicitors | |
| `form_e_chaser` | other side's solicitors | |
| `child_arrangements_proposal` | other side's solicitors | Without Prejudice enforced; child-focus checks |
| `client_hearing_report` | client | contains advice; costs-information paragraph required |
| `order_enclosure_to_client` | client | plain language; enclosure enforced |
| `ncdr_position_fm5` | other side's solicitors | |

`legalapp check` runs over any letter you already have — no drafting required.

## Install

```
pip install -e ".[agents,dev]"
pytest
```

Letters are generated generically with typed placeholders where PII belongs — no client data
enters the system. Every letter is a draft for a solicitor to check and sign.
