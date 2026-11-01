---
name: up-0-navigating-spec-driven-work
description: >-
  Reads the state of a spec-driven repository (vision, requirements catalog, entity model, use case
  diagram, use case specifications with their Status, journey test cases, code and tests) and names
  the single next step and the skill that performs it, following the artifact chain from vision to
  tests. Also classifies work that is not a change: new behavior before any use case is approved,
  recovery of an existing system, throwaway, and picks the rigor profile (throwaway, solo, team). Use
  when the user asks where the project stands, what comes next, which step follows the entity model or
  an approved use case, whether to go ahead with a step now, whether a piece of work needs use cases
  or specifications at all, how to start spec-driven development or use-case-driven work on an idea or
  an existing codebase, to clean the specs, or names spec-driven development without naming an
  artifact. For a fix, change or feature, use up-1-triaging-change-requests. Routes only; writes no
  artifact.
---

# Navigating spec-driven work

Say where a specification-driven project stands and what the single next step
is. You route. You write no artifact, change no Status and start no work:
you name the step, the skill that performs it, and the evidence for it.

The method is a chain: vision, requirements, entity model, use case diagram,
use case specifications, then per use case: review, approval, implementation,
tests, acceptance. In the skill names, 0 and 1 are the two entries (0 for the
state, 1 for a change); 2 to 9 are the artifact chain in the method's order;
unnumbered skills are used when needed. Each artifact narrows what the next one may decide. The
order is the method; a step taken early is a guess that later steps inherit.

Shared paths, identifiers and Status values: [references/conventions.md](references/conventions.md).

`scripts/use_case_map.py --check` checks overview freshness; the mapping skill
regenerates it. You write no files.

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
its Status, format findings and overview freshness, and the first decision
row that matches. If Python is unavailable, read the same things by hand: the
guideline file, the four artifact files, and the front matter `status` of each file in
`docs/use_cases/`.

When the project tracks its work in the A-files (`ACTIVE.md` with a hot
zone), the script reads them too: the current work, what blocks it and what
waits on the owner, AHEAD's Next up, and the use cases each ability names in
its `Specs` line. An ability's status comes from its row in any index table of
`ABILITIES.md`, or from an old entry's Status line when the row has none. It
then answers for the current work first, lists a use case in progress that the
current work does not name as a mismatch, and warns when an ability's status
disagrees with its use cases. Without `ABILITIES.md` it says nothing about
abilities.

The report you pass on has the same parts each time for the same files. The
Next step block carries a `when:` line (not for MIGRATE): no other task is in hand, and a fix,
change or feature on an existing use case goes to
`up-1-triaging-change-requests` first. After the block, when format findings
that do not block exist, one line reads `To clean (not blocking): N format
findings in M files. Say "clean the specs" to fix them.`; with every use case
Done it reads `Nothing in flight; N item(s) to clean.` The tracking part ends
with `Next up:` (the AH IDs of `AHEAD.md`) and `Debt:` (the bullets of
`ACTIVE.md`'s Debt section, at most five, then "and N more"). Give these lines
to the person as the report prints them.

## Classify the request

Before the table, decide what kind of request this is. The rows are tried from
the top; the first row that takes a task wins.

| The request is | First move |
|---|---|
| A question about state or the next step | The decision table |
| "Clean the specs" | The section "Clean the specs", below |
| Any task on a repository with no rules block, no vision and no specifications, unless the person asked for setup, recovery or migration | Say one line: `No upspec setup here; this task runs outside the method. Say "set up" to start.` The task goes ahead as ordinary work; ask nothing. With no task in hand, row 1 of the decision table stays: set the project up |
| Throwaway work: a one-off script, an experiment, a prototype to discard | Ask the deciding question below. If it is throwaway: no specification skill. Say so and stop |
| New behavior on a set-up project that has no approved use case yet | The decision table: it is part of building the chain |
| A fix, a change or a feature on a project with approved use cases | `up-1-triaging-change-requests`, which classifies it and moves the specification first |
| An existing system without specifications | `up-bootstrapping-spec-driven-projects` if no rules block exists, then `up-recovering-specs-from-code` |
| Specifications in another format (another folder, another method's files) | `up-bootstrapping-spec-driven-projects` if no rules block exists, then `up-migrating-spec-formats`, not recovery |
| "Too big to review", teams colliding under `docs/` | `up-splitting-bounded-contexts` |
| A named artifact ("write UC-004", "review the specs") | The skill for that artifact. Check the table first: if an earlier step is missing, say so |

The deciding question for rigor:

> Will this be maintained, extended, or handed over to someone else?

No means throwaway: structured use cases would cost more than they return.
Say what would change the answer: the script is kept, someone else comes to
depend on it, or it becomes the base of something lasting.

## Clean the specs

When the person says "clean the specs", the findings on the "to clean" line are
the list. Read them from the JSON report:

```bash
python3 scripts/workflow_state.py --format json
```

List the entries of `format_findings` whose `blocking` is false: the file, the
line and code, and the skill named in the entry's `skill` field, which repairs
it. Group them by skill, one line per file, and name the skill that takes each
group. You edit nothing. An entry that blocks is not on this list: it is already
the next step (`FIX_FORMAT`). With no such entry, say there is nothing to clean.

## Decision table

Earlier formats route to `MIGRATE` first. A format finding routes to
`FIX_FORMAT` before every other row only when it blocks, that is when
`use_case_map.refusals()` names its file (an `id` or `goal` written over
several lines, so the overview cannot be written); the row names the files,
codes and the artifact-writing skill. Every other finding goes on the "to
clean" line and is never the next step. Otherwise the first matching row wins,
in the order the script tries them. Evidence and edge cases for each row:
[references/decision-table.md](references/decision-table.md).

| # | Observed | Next step | Skill or actor |
|---|---|---|---|
| 0a | Earlier specification formats detected (`OLD_FORMAT`) | `MIGRATE` | `up-migrating-spec-formats` |
| 0b | A blocking format finding: `use_case_map.refusals()` names the file | `FIX_FORMAT`: repair it | The skill that writes the artifact (e.g. `up-5` for use cases) |
| 1 | No rules block, no vision, no specifications | Set the project up | `up-bootstrapping-spec-driven-projects` |
| 2 | Code exists; no requirements catalog, entity model or use case file | Recover what the system does | `up-recovering-specs-from-code` |
| 3 | Use cases recovered from code are still `Draft` | The baseline review | `up-6-reviewing-specifications`, then the owner |
| 4 | Vision missing or still placeholder text | The owner writes the vision | A person; readiness check by `up-bootstrapping-spec-driven-projects` |
| 5 | Requirements catalog missing | Catalog the requirements | `up-2-cataloging-requirements` |
| 6 | Entity model missing | Model the entities, before any use case | `up-3-modeling-domain-entities` |
| 7 | A use case has no ID, an ID is used twice, or a Status is not a Status (`FIX`) | Repair the specification files first | `up-6-reviewing-specifications` (the specification lint) |
| 8 | Use case diagram missing or stale | Map the use cases | `up-4-mapping-use-cases` |
| 9 | With the A-files: a use case the current work names has a next step (only when `ACTIVE.md` has no current work, AHEAD's first Next up item) | That use case's own step, from rows 10 to 14 or row 18, tried in the order of those rows | Its row's skill or actor |
| 10 | A use case is `Implemented` | Test the built slice, then audit it | `up-8-deriving-use-case-tests`, `up-9-auditing-spec-coverage` |
| 11 | A use case is `Approved` | Implement it | `up-7-implementing-use-cases` |
| 12 | A use case is `Reviewed` | A person approves it | A person |
| 13 | A use case file is a stub: its body is `Not written yet.` (Status should be `Draft`) | `WRITE`: specify it | `up-5-writing-use-case-specs` |
| 14 | A written use case is `Draft` | Validate and review it | `up-6-reviewing-specifications` |
| 15 | No use case file exists yet | `SPECIFY`: write the first use case | `up-5-writing-use-case-specs` |
| 16 | A requirement has no use case | Add the use case, or defer the requirement | `up-4-mapping-use-cases` |
| 17 | Two or more use cases `Tested` or `Done`, no journey test case | Test the seams | `up-writing-journey-test-cases` |
| 18 | A use case is `Tested` | The business accepts it | A person |
| 19 | Everything is `Done` | Nothing in flight; new requests are changes | `up-1-triaging-change-requests` |

Rows 2 and 3 come before the vision on purpose: an existing system is
recovered first, and its baseline review settles what it does before anyone
writes what it is for. The vision and the catalog follow.

Row 7 sits directly above row 8 because the overview is built from the use
case files: a missing ID, a reused ID or a Status that is not a Status spoils it.

Rows 9 to 14 are ordered so that work in flight finishes before new work
starts: the current work's use cases come first, then the use case furthest
along; a stub is written (row 13) before a written draft is reviewed (row 14).

**Inside one use case the order is strict**: specify, review, approve,
implement, test. A slice that is `Implemented` gets its tests before any
further flow of the same use case is built. **Across use cases work runs in
parallel**: while UC-003 waits for a person's approval, UC-005 can be
reviewed. The script lists each use case's own next step for that reason.

If the user names a use case, answer for that use case: its row, and anything
of the same use case that must finish first.

Steps done by a person (rows 3, 4, 12, 18) are real steps. Name who must act and
what they need in front of them. Do not skip past them, and do not perform
them: an agent never sets `Approved` or `Done`.

## Rigor profile

The profile is recorded in the rules block of the guideline file
(`**Profile:** solo` or `team`). It changes the gates, not the order.

| | Solo | Team |
|---|---|---|
| Rows 5 and 8 (catalog, diagram) | May be skipped; recorded as `**Skipped:**` in the rules block | Required |
| Row 6 (entity model) | Skipped only for a system that stores nothing. May start thin: only what the use cases written so far and the next one need, growing with each use case; it still exists before the first use case | Required, covering the catalog |
| Row 12 (approval) | The developer's own sign-off | A named person other than the author |
| Row 14 (review) | A cold read | An independent reviewer |
| The spec-first guard | Warns | Warns; fails only in a pipeline the team made strict with `--strict` |

If no profile is recorded, ask once which applies, and suggest recording it
through `up-bootstrapping-spec-driven-projects`. Until then apply the full chain.

A thin model changes nothing in the decision table: row 6 asks only that the
model exists. A noun a use case needs and the model lacks is added through
`up-3-modeling-domain-entities`, in either profile, and the vocabulary check
is the same in both: every business noun a specification uses is defined in
the model.

## Workflow

1. Run `scripts/workflow_state.py` on `docs/` (read the folder by hand if
   Python is unavailable).
   When the state report carries an update notice, pass it on to the person in one line; it never blocks the next step.
2. If the script reports `MIGRATE`, name `up-migrating-spec-formats` and
   stop routing normal work. Otherwise classify the request: question, clean
   the specs, then a task on a repository with no rules block, no vision and no
   specifications (unless the person asked for setup, recovery or migration:
   say the outside-the-method line and let the task go ahead), then throwaway,
   new behavior on a set-up project with no approved use case yet, a fix,
   change or feature (`up-1-triaging-change-requests`), existing system,
   specifications in another format, too large.
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
   owner resolves in `ACTIVE.md` or `ABILITIES.md`; you change neither. When a recovery left an alignment backlog, give its count line, its `ready` hints and its warnings; the count never changes the next step.
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
