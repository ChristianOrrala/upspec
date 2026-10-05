# Decision table in detail

For every row: what is observed, the evidence to cite, what the step needs,
and what done looks like. The script's step code is given with each row.

## Contents

- Building the chain (rows 1 to 7)
- Keeping it consistent (row 8)
- Per use case (rows 9 to 13)
- Closing gaps (rows 14 to 17)
- Why this order
- Edge cases
- Answer format

## Building the chain (rows 1 to 7)

| Row | Code | Evidence | The step needs | Done when |
|---|---|---|---|---|
| 1 | `SETUP` | No rules block in `AGENTS.md` or `CLAUDE.md`; no `docs/vision.md`; no specification | The deciding question; the number of people | Profile recorded; docs tree and rules block exist |
| 2 | `RECOVER` | Source files exist; no catalog, entity model, diagram or specification | The code base; someone who knows the system | Diagram, entity model and ledger exist; specifications at the depth the owner chose; baseline review prepared |
| 3 | `BASELINE_REVIEW` | A use case with rows in `docs/recovery/ledger.md` still has Status `Draft` | Its specification, ledger rows and suspects to decide; the owner | Each recovered draft is reviewed and answered: `Reviewed`, open items in the change log |
| 4 | `VISION` | `docs/vision.md` missing, or it still holds placeholder text | The owner's knowledge of problem and users | It names the actors, the core nouns and the boundaries |
| 5 | `REQUIREMENTS` | `docs/requirements.md` missing, not recorded as skipped | The vision; stakeholder input | Catalog with FR, NFR and C rows passes its check |
| 6 | `ENTITY_MODEL` | `docs/entity_model.md` missing, not recorded as skipped | The catalog (or the vision's core terms) | Model passes its check |
| 7 | `DIAGRAM` | `docs/use_cases.puml` missing, not recorded as skipped | Catalog and entity model | Every functional requirement is realized by a use case |

Row 2 needs judgment the script cannot make: whether the code found is
behavior worth recovering or only a fresh project skeleton. Look at it. A
generated scaffold with no business logic is not an existing system: continue
with row 4.

Rows 2 and 3 come before the vision for an existing system. Recovery needs the
code, not the vision; the baseline review then settles what the system does,
and the vision written afterwards can point to it. A vision written first
would be guessed from the same code.

Requirements come before the entity model, and the entity model before use
cases: a use case written without the model invents its own nouns, and the
next one invents different ones.

## Keeping it consistent (row 8)

| Row | Code | Evidence | The step needs | Done when |
|---|---|---|---|---|
| 8 | `FIX` | A specification that is not in the diagram; a name that differs; a Status that is not a Status; an identifier used twice | The lint output | The lint reports no error |

Broken traceability comes before any further work on use cases: every later
step reads these links.

## Per use case (rows 9 to 13)

| Row | Code | Status found | The step needs | Done when (evidence for the next Status) |
|---|---|---|---|---|
| 9 | `TEST` | `Implemented` | Specification; the code of the slice | Every flow and rule of the slice has a named, passing test; the coverage audit is complete: `Tested` |
| 10 | `IMPLEMENT` | `Approved` | Specification, entity model, linked requirements | Code merged with rule markers; invention list answered: `Implemented` |
| 11 | `APPROVE` | `Reviewed` | The specification and its review report in front of a person | A named person signs off: `Approved` |
| 12 | `REVIEW` | `Draft` | The specification; a reviewer that did not write it | Validator clean; review verdict ready: `Reviewed` |
| 13 | `SPECIFY` | In the diagram, no file | Diagram, entity model, linked requirements | A file with Status `Draft` that passes the validator |

A Status is a claim about evidence. If the evidence for the Status found is
visibly missing (a use case marked `Tested` whose tests do not exist), say so
and route to `up-9-auditing-spec-coverage` instead of the next row.

A specification that changes after `Approved` goes back to `Reviewed` and
earns the later Status values again. That applies to `Done` too.

## Closing gaps (rows 14 to 17)

| Row | Code | Evidence | The step needs | Done when |
|---|---|---|---|---|
| 14 | `MAP` | A functional requirement no use case links, not `Deferred` or `Rejected` | Catalog and diagram | A use case realizes it, or the owner sets a scope Status |
| 15 | `JOURNEY` | Two or more use cases `Tested` or `Done`; no file in `docs/test_cases/` | The use cases that hand state to each other | A journey test case chains them |
| 16 | `BUSINESS_REVIEW` | A use case is `Tested` | The running behavior in front of the business | A person accepts it: `Done` |
| 17 | `IDLE` | Every use case `Done` | — | — |

Row 15 applies where use cases hand state to each other (one records what the
next one needs). Independent use cases need no journey; say so and go on.

## Why this order

- **Chain rows first.** An artifact missing upstream makes everything
  downstream a guess.
- **Then consistency.** Links that do not resolve make every status report
  wrong.
- **Then the use case furthest along.** Finishing work in flight delivers
  verified behavior; starting new work only adds to what is unverified. A
  slice left `Implemented` without tests is the usual place where a project
  stops being specification-driven.
- **Gaps last.** They matter, and none of them blocks a slice in flight.

## Edge cases

| Situation | Answer |
|---|---|
| The user wants a later step while an earlier row matches | Name the earlier row and why it comes first. If they decide to proceed anyway, that is their decision: say what the later step will have to guess |
| Several use cases match the same row | The one the user named; otherwise the lowest identifier. Mention the others |
| Use cases exist but the entity model does not (solo, nothing recorded as skipped) | Row 6. If the system stores nothing, suggest recording the skip |
| The docs use older file spellings (`use-cases/`, `entity-model.md`) | They are read as they are; mention the convention once |
| A use case is `Obsolete` | It has no next step and is not counted |
| The repository has several bounded contexts | Run the script once per context's docs folder; answer per context |
| The state contradicts what the user says ("I already reviewed it") | Report what the file says. A review that is not recorded in the Status did not happen for the next person |

## Answer format

```text
Where it stands: <one or two sentences with the evidence: files present, Status values>
Next step: <one step>
Who: <skill name, or the person who must act>
Needs: <the inputs>
Done when: <the evidence that moves it on>
Also in flight: <other use cases and their next steps, if any>
```
