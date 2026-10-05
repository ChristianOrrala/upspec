# Conventions

Shared by every skill of this package. Follow them exactly: scripts and other
skills parse these names.

## Contents

- Files
- Identifiers
- Status of a use case
- Markers
- Where information lives
- Script output
- Working with the A-files

## Files

| Path | Content | Written by |
|---|---|---|
| `docs/vision.md` | Purpose, users, goals, scope in and out | A human |
| `docs/requirements.md` | Tables of `FR`, `NFR` and `C` rows | up-2-cataloging-requirements |
| `docs/entity_model.md` | Mermaid `erDiagram` and one section per entity | up-3-modeling-domain-entities |
| `docs/use_cases.puml` | PlantUML overview of actors and use cases | up-4-mapping-use-cases |
| `docs/use_cases/UC-XXX-<kebab-name>.md` | One use case per file | up-5-writing-use-case-specs |
| `docs/processes/<name>.bpmn` | Optional business process models | A human |
| `docs/test_cases/TC-XXX-<kebab-name>.md` | One journey per file | up-writing-journey-test-cases |
| `docs/recovery/` | Ledger, suspect list, change log and baseline review plan of a system recovered from code | up-recovering-specs-from-code |
| `docs/change-records/UC-XXX-<kebab-name>.md` | One change record per change: classification, differences from today, impact; the pull request links it | up-triaging-change-requests |
| `docs/reviews/<scope>-review-<n>.md`, `<scope>-audit-<n>.md` | One report per review or audit run; scope is `UC-004`, `TC-001` or `all` | up-6-reviewing-specifications, up-9-auditing-spec-coverage |
| `CLAUDE.md` or `AGENTS.md` | Guideline file; its rules block records `**Profile:**` (solo or team) and what a solo project `**Skipped:**` | up-1-bootstrapping-spec-driven-projects |

In paths and commands of the skills, `docs/` stands for the specification folder: the one the rules block records as `**Specs folder:**`, else `docs`.

The file name of a use case is its name from the diagram, lowercased, spaces to
hyphens, nothing paraphrased: *Log In* is `UC-002-log-in.md`.

When `docs/` also feeds a documentation site, the specifications still live
there: whether the site lists or excludes them is the owner's choice, not a
reason to move them. A project that keeps them elsewhere records the folder as
`**Specs folder:** DIR` in the rules block (setup's `--specs-folder`); every
script reads it, and `--docs DIR` overrides it for one run.

## Identifiers

| Identifier | Unique within | Cited elsewhere as |
|---|---|---|
| `FR-001`, `NFR-001`, `C-001` | The catalog | The same |
| `UC-001`, `TC-001` | The project | The same |
| `BR-001` | Its use case; numbering restarts in every file | `UC-001 BR-001` |
| `A1` | Its use case | `UC-001 A1` |

Three digits. Never reused, never renumbered. A requirement that leaves scope
gets Status `Deferred` or `Rejected`; a superseded use case gets `Obsolete`. A
rule or flow that leaves a use case keeps its heading with one line saying
where it went or why: `### BR-004: Retired, moved to UC-022 BR-025`.

A flow's trigger names the step it branches from: `(step 4)`, or `(A2 step 3)`
for a step of another flow.
References are written once, downstream pointing upstream. A citation into
another bounded context carries its name: `billing/UC-003 BR-002`.

## Status of a use case

| Move | Evidence it needs | Who |
|---|---|---|
| Draft → Reviewed | Validator clean; author's checklist done | Author |
| Reviewed → Approved | Independent review says ready; a named human signs off in the change | Owner, human |
| Approved → Implemented | Code for the slice merged; rule markers in place | Implementer |
| Implemented → Tested | Coverage matrix complete for the slice; suite green | On the audit's suggestion |
| Tested → Done | Business review of the working slice accepted | Owner, human |
| any → Reviewed or Approved | The specification changed | Whoever changed it |
| any → Obsolete | Superseded; the file stays | Owner |

An agent proposes a move with its evidence. It never sets Approved or Done.
A step, flow or rule that describes behavior recorded as suspect names it in
the text: `(S-012)`.
The Status line is the only place a use case's Status is written; change logs,
review plans and reports refer to it and never copy it.

Journey test case: `Draft`, `Reviewed`, `Approved`, `Automated`, `Obsolete`.

Requirement: `Open`, `In Progress`, `Implemented`, `Verified` follow the use
cases that link it and are never typed by hand: Verified when all are Tested or
Done, Implemented when all are at least Implemented, In Progress when some
are, Open otherwise. `Deferred` and `Rejected` are set by hand.

## Markers

Code, directly above what enforces a rule, as a comment, one line:

```text
UC-005 BR-003: A guest must be at least eighteen years old on the day of arrival.
```

Tests: the suite carries the use case id in its name (`UC-005` or `UC005`).
Each test names its flow (`Main`, `A1`, ...) and the rules it covers (`BR-003`)
in its name, annotation or tag. Journey tests carry the `TC` id and label each
step with its row number.

Commits and pull requests name the use case in the subject. A change without a
behavior change carries the line `No behavior change: UC-012` (or `none` and why).

## Where information lives

| Information | Home |
|---|---|
| What a stakeholder can observe | The use case specification |
| The shape of a business noun | The entity model |
| A quality threshold and how it is verified | An `NFR` row |
| A mandatory boundary and its source | A `C` row |
| A technical rule for every task | The guideline file |
| A one-off technical choice | A decision record under `docs/decisions/` |
| Layout, interface contracts | A linked mockup or supplementary specification |
| What the agent decided on its own | The invention list in the pull request |
| What is being worked on, what the product can do, what is ahead | The A-files (`ACTIVE.md`, `ABILITIES.md`, `AHEAD.md`), when the project uses them |

One home each. Reference it elsewhere; never restate it.

**People.** Specifications and records name roles (the administrator, a
member), never people. Examples use invented values, never a real name,
identifier, address or account found in the code or its data.

**Language.** Specifications, records and messages are written in the
project's own language. The structure stays as the template has it, because
the scripts parse it: section headings, field labels (`**Status:**`,
`**Trigger:**`), Status values and flow endings (`Use case ends.`,
`Use case continues at step N.`). Everything else follows the project.

## Script output

`path:line: SEVERITY CODE [element]: message` with `ERROR`, `WARN` or `INFO`.
Exit 0 clean, 1 on an error (with `--strict` also on a warning), 2 on a usage
error. Scripts read project files as data and need Python 3.9 or later.

## Working with the A-files

Some projects track their work in the A-files: five files at the root
(`AGENTS.md`, `ACTIVE.md`, `ABILITIES.md`, `AHEAD.md`, `ATLAS.md`) that every
agent reads first. They are present when `ACTIVE.md` holds the line
`<!-- hot zone ends -->`. The two methods keep their own files and are joined
by these rules; whichever is set up second makes the joining edits (P1, P5).

<!-- pairing contract: start -->
| # | Where | Rule |
|---|---|---|
| P1 | `AGENTS.md` | The specification rules section sits below the hot zone and is named in its `Below:` line. The keep-in-step list says that a use case changing Status is followed by the ability whose `Specs` line names it, and that a newly mapped use case joins an ability's `Specs` line. |
| P2 | `ABILITIES.md` | An ability entry may carry `- **Specs:**` with use case identifiers (`UC-003, UC-007`) or relative links to specification files. An ability is `done` only when every use case it names is `Done`, and it is not `planned` while one of them is `Implemented`, `Tested` or `Done`. |
| P3 | `ACTIVE.md`, `AHEAD.md` | The next step comes from the current work first: the use cases and abilities `ACTIVE.md` names; when there is no current work, the first item of AHEAD's Next up, through its ability's `Specs` line. A use case that is `Implemented` or `Tested` and not named by the current work is a mismatch to resolve. |
| P4 | `AHEAD.md` | A deferred requirement keeps its row in the requirements catalog; an AHEAD item cites its identifier (`FR-012`). A change request accepted for later becomes an AHEAD item that links its change record. A recovery change log entry decided `later` becomes an AHEAD item that cites it; the entries of one use case share one item. Nothing is copied. |
| P5 | `ATLAS.md` | One row maps the specifications: their folder and files, and the checks that cover them. |
| P6 | The finish check | A change that moves a use case's Status while `ABILITIES.md` and `ACTIVE.md` stay unchanged gets a warning. |
| P7 | The session start | The state shown when a session starts includes the current work from `ACTIVE.md`. |
| P8 | `docs/decisions/` | Decision records follow the A-files naming: four digits, then the subject. |
<!-- pairing contract: end -->

An agent never edits the A-files on its own initiative while it works on a
use case: it names what they should say, and the main session or the person
updates them in the same commit as the work.
