---
name: up-0-navigating-spec-driven-work
description: >-
  Reads the state of a spec-driven repository (vision, requirements catalog, entity model, use case
  diagram, use case specifications with their Status, journey test cases, code and tests) and names
  the single next step and the skill that performs it, following the artifact chain from vision to
  tests. Also classifies incoming work as new behavior, change, bug, recovery of an existing system or
  throwaway, and picks the rigor profile (throwaway, solo, team). Use when the user asks where the
  project stands, what comes next, which step follows the entity model or an approved use case,
  whether to go ahead with a step now, whether a piece of work needs use cases or specifications at
  all, how to start spec-driven development or use-case-driven work on an idea or an existing
  codebase, or names spec-driven development without naming an artifact. Routes only; writes no
  artifact.
---

# Navigating spec-driven work

Say where a specification-driven project stands and what the single next step
is. You route. You write no artifact, change no Status and start no work:
you name the step, the skill that performs it, and the evidence for it.

The method is a chain: vision, requirements, entity model, use case diagram,
use case specifications, then per use case: review, approval, implementation,
tests, acceptance. The number in a skill's name is its place in that chain
(`up-1-...` to `up-9-...`); skills without a number are side entries that can
be needed at any point. Each artifact narrows what the next one may decide. The
order is the method; a step taken early is a guess that later steps inherit.

Shared paths, identifiers and Status values: [references/conventions.md](references/conventions.md).

## Read the state

Scripts read the specification folder the rules block records (`**Specs folder:**`), else `docs`; `--docs DIR` overrides it.

State comes from the repository on every call. Not from this conversation,
not from what the user says was done, not from an earlier answer: files change
between two questions.

```bash
python3 scripts/workflow_state.py
```

The script is in this skill's folder; use the base directory shown when the skill
was loaded, and do not search the disk for it. It reports the profile
recorded in the guideline file, which artifacts exist, every use case with
its Status, disagreements between diagram and files, and the first decision
row that matches. If Python is unavailable, read the same things by hand: the
guideline file, the four artifact files, and the Status line of each file in
`docs/use_cases/`.

When the project tracks its work in the A-files (`ACTIVE.md` with a hot
zone), the script reads them too: the current work, what blocks it and what
waits on the owner, AHEAD's Next up, and the use cases each ability names in
its `Specs` line. It then answers for the current work first, lists a use case
in progress that the current work does not name as a mismatch, and warns when
an ability's status disagrees with its use cases.

## Classify the request

Before the table, decide what kind of request this is.

| The request is | First move |
|---|---|
| A question about state or the next step | The decision table |
| Throwaway work: a one-off script, an experiment, a prototype to discard | Ask the deciding question below. If it is throwaway: no specification skill. Say so and stop |
| New behavior on a project that has no approved use case yet | The decision table: it is part of building the chain |
| New behavior, a change of mind, or a bug on a project with approved use cases | `up-triaging-change-requests`, which classifies it and moves the specification first |
| An existing system without specifications | `up-1-bootstrapping-spec-driven-projects` if no rules block exists, then `up-recovering-specs-from-code` |
| "Too big to review", teams colliding under `docs/` | `up-splitting-bounded-contexts` |
| A named artifact ("write UC-004", "review the specs") | The skill for that artifact. Check the table first: if an earlier step is missing, say so |

The deciding question for rigor:

> Will this be maintained, extended, or handed over to someone else?

No means throwaway: structured use cases would cost more than they return.
Say what would change the answer: the script is kept, someone else comes to
depend on it, or it becomes the base of something lasting.

## Decision table

First matching row wins. Evidence and edge cases for each row:
[references/decision-table.md](references/decision-table.md).

| # | Observed | Next step | Skill or actor |
|---|---|---|---|
| 1 | No rules block, no vision, no specifications | Set the project up | `up-1-bootstrapping-spec-driven-projects` |
| 2 | Code exists, no specification of any kind | Recover what the system does | `up-recovering-specs-from-code` |
| 3 | Use cases recovered from code are still `Draft` | The baseline review | `up-6-reviewing-specifications`, then the owner |
| 4 | Vision missing or still placeholder text | The owner writes the vision | A person; readiness check by `up-1-bootstrapping-spec-driven-projects` |
| 5 | Requirements catalog missing | Catalog the requirements | `up-2-cataloging-requirements` |
| 6 | Entity model missing | Model the entities, before any use case | `up-3-modeling-domain-entities` |
| 7 | Use case diagram missing | Map the use cases | `up-4-mapping-use-cases` |
| 8 | Diagram and specification files disagree | Repair traceability | `up-6-reviewing-specifications` |
| 9 | A use case is `Implemented` | Test the built slice, then audit it | `up-8-deriving-use-case-tests`, `up-9-auditing-spec-coverage` |
| 10 | A use case is `Approved` | Implement it | `up-7-implementing-use-cases` |
| 11 | A use case is `Reviewed` | A person approves it | A person |
| 12 | A use case is `Draft` | Validate and review it | `up-6-reviewing-specifications` |
| 13 | A use case is in the diagram without a specification | Specify it | `up-5-writing-use-case-specs` |
| 14 | A requirement has no use case | Add the use case, or defer the requirement | `up-4-mapping-use-cases` |
| 15 | Two or more use cases `Tested`, no journey test case | Test the seams | `up-writing-journey-test-cases` |
| 16 | A use case is `Tested` | The business accepts it | A person |
| 17 | Everything is `Done` | Nothing in flight; new requests are changes | `up-triaging-change-requests` |

Rows 2 and 3 come before the vision on purpose: an existing system is
recovered first, and its baseline review settles what it does before anyone
writes what it is for. The vision and the catalog follow.

Rows 9 to 13 are ordered so that work in flight finishes before new work
starts: the use case furthest along comes first.

**Inside one use case the order is strict**: specify, review, approve,
implement, test. A slice that is `Implemented` gets its tests before any
further flow of the same use case is built. **Across use cases work runs in
parallel**: while UC-003 waits for a person's approval, UC-005 can be
reviewed. The script lists each use case's own next step for that reason.

If the user names a use case, answer for that use case: its row, and anything
of the same use case that must finish first.

Steps done by a person (rows 3, 4, 11, 16) are real steps. Name who must act and
what they need in front of them. Do not skip past them, and do not perform
them: an agent never sets `Approved` or `Done`.

## Rigor profile

The profile is recorded in the rules block of the guideline file
(`**Profile:** solo` or `team`). It changes the gates, not the order.

| | Solo | Team |
|---|---|---|
| Rows 5 and 7 (catalog, diagram) | May be skipped; recorded as `**Skipped:**` in the rules block | Required |
| Row 6 (entity model) | Skipped only for a system that stores nothing | Required |
| Row 12 (review) | A fresh-context review | An independent reviewer |
| Row 11 (approval) | The developer's own sign-off | A named person other than the author |
| The spec-first guard | Warns | Blocks |

If no profile is recorded, ask once which applies, and suggest recording it
through `up-1-bootstrapping-spec-driven-projects`. Until then apply the full chain.

## Workflow

1. Run `scripts/workflow_state.py` on `docs/` (read the folder by hand if
   Python is unavailable).
2. Classify the request: question, throwaway, new behavior, change, bug,
   existing system, too large.
3. Read the rigor profile from the guideline file; ask once if none is
   recorded.
4. Walk the decision table top to bottom; the first matching row wins.
5. Answer with: the evidence found (files, Status values), one next step, the
   skill or person, its inputs, and what done looks like. When the step moves a
   Status, say what evidence moves it: `Tested` only when every built flow and
   rule has a named, passing test and the coverage audit shows it. Never
   propose a Status the evidence does not carry.
   With the A-files, say first what blocks the work or waits on the owner,
   name the current work, and give each mismatch and warning as something the
   owner resolves in `ACTIVE.md` or `ABILITIES.md`; you change neither.
6. If a slice is in flight on the same use case, say to finish it first.

## Validation

Before answering, check your answer:

- It names exactly one next step.
- It cites a file or a Status value you read in this call as evidence.
- It names the skill by its exact name, or says a person must act.
- Nothing was created or edited.
- With the A-files: the answer names the current work from `ACTIVE.md`, and
  none of the A-files was edited.

## Worked example

"UC-004 is approved. What now? I'd like to start on its alternative flows."

```text
Profile: solo (CLAUDE.md)
Use cases
  UC-001  Book Repair          Done          —
  UC-003  Record Diagnosis     Implemented   next: TEST
  UC-004  Approve Estimate     Approved      next: IMPLEMENT
Next step: TEST UC-003
```

Answer:

- **UC-004:** its file says `Approved`, so the next step for it is
  `up-7-implementing-use-cases UC-004`, starting with a first slice: the main
  success scenario and the rules it touches. Its alternative flows are later
  slices, each implemented and tested in turn. Done for this step: code merged
  with rule markers, Status `Implemented`.
- **Before or beside it:** UC-003 is `Implemented` with no tests yet. That
  slice is in flight; `up-8-deriving-use-case-tests UC-003` finishes it. It is a
  different use case, so it does not block UC-004, but it should not be left
  behind.
