# Decision table in detail

For every row: what is observed, the evidence to cite, what the step needs,
and what done looks like. The script's step code is given with each row, and
the rows are in the order the script tries them.

## Contents

- Before the chain (rows 0a and 0b)
- Building the chain (rows 1 to 8)
- Per use case (rows 9 to 15)
- Closing gaps (rows 16 to 19)
- Why this order
- Edge cases
- Answer format

## Before the chain

| Row | Code | Evidence | The step needs | Done when |
|---|---|---|---|---|
| 0a | `MIGRATE` | The shared reader found an earlier artifact format (`OLD_FORMAT`) | The migration skill, `up-migrating-spec-formats`; it takes precedence over every row | Migration verified, installed checks replaced, identifiers and Status preserved, and no format finding remains |
| 0b | `FIX_FORMAT` | A format finding that blocks: `use_case_map.refusals()` names its file | The format findings | Repaired using the skill that writes the artifact |

`FIX_FORMAT` takes precedence over the rows below only when a finding blocks:
`use_case_map.refusals()` names its file, which today means an `id` or `goal`
written over several lines, so the overview cannot be written. Name every
blocking file and code, and route to the skill that writes the first affected
artifact. Every other finding goes on one line, "To clean (not blocking): N
format findings in M files", and is never the next step. With every use case
Done, the reason reads "Nothing in flight; N item(s) to clean."

## Building the chain (rows 1 to 8)

| Row | Code | Evidence | The step needs | Done when |
|---|---|---|---|---|
| 1 | `SETUP` | No rules block in `AGENTS.md` or `CLAUDE.md`; no `docs/vision.md`; no specification | The deciding question; the number of people | Profile recorded; docs tree and rules block exist |
| 2 | `RECOVER` | Source files exist; no requirements catalog, entity model or use case file | The code base; someone who knows the system | Diagram, entity model and ledger exist; specifications at the depth the owner chose; baseline review prepared |
| 3 | `BASELINE_REVIEW` | A use case with rows in `docs/recovery/ledger.md` still has Status `Draft` | Its specification, ledger rows and suspects to decide; the owner | Each recovered draft is reviewed and answered: `Reviewed`, open items in the change log |
| 4 | `VISION` | `docs/vision.md` missing, or it still holds placeholder text | The owner's knowledge of problem and users | It names the actors, the core nouns and the boundaries |
| 5 | `REQUIREMENTS` | `docs/requirements.md` missing, not recorded as skipped | The vision; stakeholder input | Catalog with FR, NFR and C rows passes its check |
| 6 | `ENTITY_MODEL` | `docs/entity_model.md` missing, not recorded as skipped | The catalog (or the vision's core terms) | Model passes its check |
| 7 | `FIX` | A use case with no ID, an ID used twice, or a Status that is not a Status | The specification lint's report | The lint reports no such problem; every use case is readable |
| 8 | `DIAGRAM` | `docs/use_cases.md` missing or stale, not recorded as skipped | Catalog and entity model | Every functional requirement is realized by a use case |

Row 2 needs judgment the script cannot make: whether the code found is
behavior worth recovering or only a fresh project skeleton. Look at it. A
generated scaffold with no business logic is not an existing system: continue
with row 4. The script reads only the specification folder, so it still names
row 2 when specifications in another format sit outside it; those go to the
migration, not to recovery.

Rows 2 and 3 come before the vision for an existing system. Recovery needs the
code, not the vision; the baseline review then settles what the system does,
and the vision written afterwards can point to it. A vision written first
would be guessed from the same code.

Requirements come before the entity model, and the entity model before use
cases: a use case written without the model invents its own nouns, and the
next one invents different ones.

Row 7 sits directly above row 8: the overview is built from the use case
files, so identifier and Status mismatches are repaired before it, and before
any further work on use cases. Every later step reads these links.

## Per use case (rows 9 to 15)

| Row | Code | Status found | The step needs | Done when (evidence for the next Status) |
|---|---|---|---|---|
| 9 | The use case's own code from rows 10 to 14, or `BUSINESS_REVIEW` (row 18) | With the A-files: a use case the current work in `ACTIVE.md` names, directly or through an ability's `Specs` line; only when `ACTIVE.md` has no current work, the use cases of AHEAD's first Next up item | What the row of its Status needs; the script tries its codes in the order `TEST`, `IMPLEMENT`, `APPROVE`, `WRITE`, `REVIEW`, `BUSINESS_REVIEW` | As for that row |
| 10 | `TEST` | `Implemented` | Specification; the code of the slice | Every flow and rule of the slice has a named, passing test; the coverage audit is complete: `Tested` |
| 11 | `IMPLEMENT` | `Approved` | Specification, entity model, linked requirements | Code merged with rule markers; invention list answered: `Implemented` |
| 12 | `APPROVE` | `Reviewed` | The specification and its review report in front of a person | A named person signs off: `Approved` |
| 13 | `WRITE` | A use case file whose body is `Not written yet.` and has no Main Success Scenario (its Status should be `Draft`; any other Status is the lint's `STUB` finding) | Overview, entity model, linked requirements | A file with Status `Draft` that passes the validator |
| 14 | `REVIEW` | Written `Draft`, not a stub | The specification; a reviewer that did not write it | Validator clean; review verdict ready: `Reviewed` |
| 15 | `SPECIFY` | No use case file exists yet | The overview and the owner's choice of the first behavior: one that is contested or unclear today | One use case file exists, written with `up-5-writing-use-case-specs` |

Row 9 applies only when the project keeps the A-files and the current work
names use cases (only when `ACTIVE.md` has no current work, AHEAD's first
Next up item). It is
the same set of steps as rows 10 to 14 and row 18, restricted to the named use
cases, so the work in hand is answered before any other use case. When none of
the named use cases has a next step, the script goes on to row 10.

Rows 13 and 14 run in this order across the whole project: a stub is written
before a written draft is reviewed.

A Status is a claim about evidence. If the evidence for the Status found is
visibly missing (a use case marked `Tested` whose tests do not exist), say so
and route to `up-9-auditing-spec-coverage` instead of the next row.

A specification that changes after `Approved` goes back to `Reviewed` and
earns the later Status values again. That applies to `Done` too.

## Closing gaps (rows 16 to 19)

| Row | Code | Evidence | The step needs | Done when |
|---|---|---|---|---|
| 16 | `MAP` | A functional requirement no use case links, not `Deferred` or `Rejected` | Catalog and diagram | A use case realizes it, or the owner sets a scope Status |
| 17 | `JOURNEY` | Two or more use cases `Tested` or `Done`; no file in `docs/test_cases/` | The use cases that hand state to each other | A journey test case chains them |
| 18 | `BUSINESS_REVIEW` | A use case is `Tested` | The running behavior in front of the business | A person accepts it: `Done` |
| 19 | `IDLE` | Every use case `Done` | — | — |

Row 17 applies where use cases hand state to each other (one records what the
next one needs). Independent use cases need no journey; say so and go on.

## Why this order

- **Chain rows first.** An artifact missing upstream makes everything
  downstream a guess.
- **Then consistency.** Links that do not resolve make every status report
  wrong, so `FIX` comes directly above `DIAGRAM`. A blocking format finding
  comes before all of it, because the overview cannot be written.
- **Then the use case furthest along, the current work's first.** Finishing work in flight delivers
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
| Earlier artifact formats or retired artifact spellings are detected | `MIGRATE` first; the migration renames them |
| Format findings exist and none blocks | They are on the "to clean" line, never the next step; the person says "clean the specs" to have them listed with the skill for each |
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
