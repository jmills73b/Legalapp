# Family Law Correspondence — Agent System Design

**Jurisdiction:** England & Wales
**Scope:** solicitors' correspondence in family matters — primarily letters
**PII posture (v1):** generic output with typed placeholders; no client data enters the system

---

## 1. Thesis

A family law letter is not a document to be generated. It is a **known form, assembled from
a paragraph library**, with two or three paragraphs of genuinely bespoke content in the middle.
A firm sends perhaps thirty recurring letter types, over and over.

So the request supplies *intent*, the library supplies *form*, and — in v1 — nothing at all
supplies the facts. The letter comes out with typed placeholders where PII belongs, and a
fee earner fills them in.

That last decision is not a limitation. It is the single best property of the design.

## 2. The PII posture, and why it inverts a validator

Because letters are generated generically, **no client-confidential data ever enters a model
context.** Three consequences follow, and they shape everything downstream:

1. **You can build and test this against real letter types without a single real matter.**
   No data processing agreement, no retention decision, no anonymisation pipeline before
   you can start.
2. **Placeholders are the intended output, not a defect.** In a contract system, a leftover
   `[PARTY]` is a bug. Here it is the product.
3. **The critical failure mode flips.** The dangerous output is not a missing placeholder —
   it is **invented PII**. A model that helpfully writes "Sarah Thompson" instead of emitting
   `[CLIENT_FULL_NAME]` has produced a letter that looks complete and is wrong in a way a
   busy fee earner may not catch.

So the flagship deterministic check becomes: **no name-shaped, date-shaped, address-shaped or
reference-shaped token may appear outside a declared placeholder.** Everything else is caught
by the same scan.

### The token dictionary

Each placeholder is typed, not just named:

| Token | Type | Notes |
|---|---|---|
| `[CLIENT_FULL_NAME]` | person | required in every letter |
| `[OTHER_PARTY_NAME]` | person | |
| `[CHILD_1_NAME]`, `[CHILD_1_DOB]` | person, date | repeats per child |
| `[MATTER_REF]` | reference | firm's own reference |
| `[CASE_NO]` | reference | court case number, where issued |
| `[HEARING_DATE]` | date | |
| `[RESPONSE_DEADLINE]` | date | derived, not typed — see §6 |
| `[FEE_EARNER_NAME]`, `[FEE_EARNER_ROLE]` | person, text | |
| `[FIRM_ADDRESS_BLOCK]` | address | suppressed where confidentiality applies |

Every generated letter ships with a **fill sheet**: the tokens it used, their types, and a
one-line description of each. That sheet is also the integration seam — when a case management
system is added later, it maps to these tokens and nothing else in the design changes.

## 3. Pipeline

```
request ──▶ Intake ──▶ LetterSpec ──▶ Compose ──▶ Assemble ──▶ Validate ──▶ Tone & Conduct ──▶ Risk Review ──▶ Format
             (model)                   (model)     (code)       (code)        (model)            (model)        (code)
                                          │                        ▲              │                  │
                                          └──── paragraph library  └──────────────┴── patch loop ────┘
```

Four model stages, four code stages. Risk Review runs only on letters leaving the firm.

## 4. Agent roster

Four agents. One fewer than the contract design, because letters need no research agent —
family correspondence rarely cites authority, and where it does, it cites the same handful
of provisions the library already contains.

### 4.1 Intake
**In:** letter type plus a line of intent. **Out:** a `LetterSpec`.

Resolves which letter type is being asked for, who the recipient is (client / other side's
solicitors / litigant in person / court), the posture, and which tokens the letter will need.
Recipient class is the most important field it sets — it determines the entire review path (§4.4).

### 4.2 Composer
**In:** LetterSpec + paragraph library. **Out:** paragraph sequence.

Pulls standard paragraphs by ID and drafts only the bespoke middle. Runs per paragraph, so
it cannot drift across the letter.

> **Hard rule:** may not emit a name, date, address, sum of money or case reference as
> literal text. Every such value is a declared token. This is enforced by §6, not by asking
> the model nicely.

### 4.3 Tone & Conduct — *the flagship*
**In:** assembled draft. **Out:** structured findings.

See §5. Runs on every letter, including letters to the client.

### 4.4 Risk Review
**In:** draft leaving the firm. **Out:** structured findings.

A different lens from tone, and a different cadence — this one runs only on outbound
correspondence to anyone other than the client:

- Does the letter make an **admission** the client has not authorised?
- Does it **disclose** something not yet disclosable — a financial fact, an address, the
  existence of advice taken?
- Is it correctly marked, or correctly *not* marked, **Without Prejudice**?
- Does it inadvertently give advice to an **unrepresented** recipient?
- Does it commit the client to a position the LetterSpec did not authorise?

Letters to the client take the other path entirely: they contain advice, so they are always
attorney-reviewed and carry costs-information duties under the SRA Transparency Rules.

## 5. Tone & Conduct

In contract drafting, tone is style. In family law it is a professional obligation with a
price attached. Most family solicitors here practise under the **Resolution Code of Practice**,
which requires constructive, non-confrontational correspondence — and in financial remedy
proceedings the general rule is no order as to costs (FPR 28.3(6)), *subject to* the court
taking a broad view of litigation conduct, which includes how a party has corresponded and
negotiated (PD28A para 4.4). An inflammatory letter can cost the client money directly.

### The deterministic half

Inflammatory correspondence is formulaic, so a banned-phrase lexicon catches most of it for free:

- "We note with some surprise…", "It is regrettable that…", "As you are well aware…"
- "your client has singularly failed…", "we are frankly astonished…"
- Rhetorical questions addressed to the other side
- Adjectives characterising the other party's conduct: *outrageous, unreasonable, blatant,
  deliberate* (as applied to a person rather than a described act)

### The model half

- Is every position stated **as a position**, rather than as an accusation?
- Does the letter **propose something**? A letter that only demands has nowhere to go.
- Is any deadline framed neutrally, **with a reason**, and is it long enough to be reasonable?
- Is the language **child-focused** — arrangements for the children, not rights over them?
- For a **first letter to an unrepresented person**: is it non-threatening, does it explain
  plainly what is happening, and does it encourage them to take their own legal advice?
  Resolution's guidance on first letters is specific, and this check should be too.

## 6. Deterministic checks

Per the core thesis: if a check can be written as an assertion, it must not be an agent.

| Check | Implementation |
|---|---|
| **Invented PII** — literal name/date/address/reference outside a token | pattern scan + token allowlist |
| Token declared but never used, or used but never declared | set difference |
| Token type mismatch (a date token in a name slot) | dictionary lookup |
| **Deprecated terminology** — see below | lexicon |
| **Without Prejudice** marking consistent with letter type | letter-type policy |
| **Address suppression** where confidentiality applies | letter-type flag → block letterhead token |
| Enclosures listed vs. enclosures attached | list comparison |
| Deadline stated but no diary entry created | integration assertion |
| Letter type's required paragraphs all present | template check |

### Deprecated terminology

This one is worth building on day one. English family law renamed a great deal, and a letter
using the old vocabulary reads as dated to any other solicitor who receives it:

| Do not use | Correct term | Since |
|---|---|---|
| custody, access | child arrangements; "lives with" / "spends time with" | 2014 |
| residence order, contact order | child arrangements order | 2014 |
| ancillary relief | financial remedy | 2011 |
| petition, petitioner | application, applicant | 2022 |
| decree nisi | conditional order | 2022 |
| decree absolute | final order | 2022 |
| unreasonable behaviour (as a ground) | irretrievable breakdown (statement of) | 2022 |

Pure lexicon. Free, instant, and it catches a class of error that a model would only sometimes spot.

## 7. Interface

```
$ legalapp letter form-e-chaser --deadline 14d \
    --note "flag we will seek directions if no response"

✓ Financial disclosure chaser — to other side's solicitors
  → form-e-chaser.docx  ·  fill-sheet.md

  Tokens to complete (6)
  · [CLIENT_FULL_NAME]      person
  · [OTHER_PARTY_NAME]      person
  · [MATTER_REF]            reference
  · [CASE_NO]               reference   optional — omit if not yet issued
  · [RESPONSE_DEADLINE]     date        derived: 14 days from date of letter
  · [FEE_EARNER_NAME]       person

  Tone & conduct: clear
  Risk review:    1 note
  · Para 4 sets a deadline without stating a reason for it —
    consider "so that we can meet the directions timetable".

$ legalapp letters                    # list available letter types
$ legalapp revise form-e-chaser.docx "soften para 4, offer a call"
```

One `LetterSpec` JSON is the seam between every component — letter type, recipient class,
posture, intent, tokens required, deadline. It is diffable and re-runnable, so "the same
letter but to a litigant in person" is a one-field change.

## 8. Letter catalogue — build these first

Ordered by volume, not by interest:

1. Client care / engagement letter *(SRA client care + costs information)*
2. First letter to an unrepresented other party *(highest tone risk in the whole catalogue)*
3. First letter to the other side's solicitors
4. Proposal to engage in non-court dispute resolution / MIAM
5. Voluntary financial disclosure request
6. Financial disclosure chaser *(Form E)*
7. Child arrangements proposal — Without Prejudice
8. Letter to client reporting on a hearing, with next steps
9. Letter enclosing a court order, explaining its effect
10. NCDR position correspondence *(FM5)*

Ten letter types working properly beats thirty half-built. Numbers 2 and 8 carry the most
risk and should get the most review attention.

## 9. Guardrails

- **Every letter is a draft for a solicitor to check and sign.** Nothing is sent by the system.
- **No PII in model context (v1).** Structural, and the strongest privacy position available.
  Preserve it deliberately when a case management system is added later — send the *shape* of
  the matter, not its contents, wherever that is possible.
- **Provenance per paragraph.** Library ID and version, or generated with the spec hash and
  model version.
- **The tone lexicon is firm property.** It encodes the firm's house standard for correspondence
  and should be reviewed by a partner, not inferred from a model.
- **Advice to clients is never auto-approved.** Path in §4.4 is not optional.

## 10. Build order

1. **Token dictionary + the invented-PII check.** Before any drafting. It is the safety property
   the whole design rests on, and it is testable on letters you already have.
2. **Deprecated terminology lexicon.** An afternoon's work; immediately useful on existing
   precedents even before an agent exists.
3. **Paragraph library + Composer + Formatter, for letter types 5 and 6.** Low risk, high volume,
   short letters. End to end on two types beats a start on ten.
4. **Tone & Conduct**, lexicon half first, then the model half.
5. **Risk Review**, and the split between client-path and outbound-path.
6. **Letter types 1, 2, 3, 7–10**, in that order.

The paragraph library is the asset, not the prompts. When a fee earner edits a generated letter,
diff it and offer the delta back as a library revision — that loop is what makes this improve
week over week, and it is worth building before it feels necessary.
