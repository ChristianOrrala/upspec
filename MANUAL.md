# upspec: User Manual

Version 1.8.2

This manual explains how to install the `upspec` skills, how the work
they support is organized, and how to carry a piece of work from an idea, a
change request or an existing codebase to code and tests that are checked
against their specification. It is written for the person who directs the
agent: a solo developer, a product owner, a lead or a reviewer.

## Contents

1. [What this package is](#1-what-this-package-is)
2. [Installing](#2-installing)
3. [First steps](#3-first-steps)
4. [Core concepts](#4-core-concepts)
5. [The project's files](#5-the-projects-files)
6. [The skills](#6-the-skills)
7. [Workflows](#7-workflows)
8. [The change record](#8-the-change-record)
9. [The checks](#9-the-checks)
10. [Rigor profiles: throwaway, solo, team](#10-rigor-profiles-throwaway-solo-team)
11. [Working with different agents and models](#11-working-with-different-agents-and-models)
12. [Safety](#12-safety)
13. [Troubleshooting](#13-troubleshooting)
14. [Known limits](#14-known-limits)
15. [Glossary](#15-glossary)
16. [Credits and license](#16-credits-and-license)

---

## 1. What this package is

`upspec` is a set of fifteen agent skills for specification-first
development with use cases. The specification is the source of truth: behavior
is written down, reviewed and approved before code is generated or changed,
and code and tests are then checked against it.

The skills are stack-neutral. They describe what to produce and how to check
it, never which framework, test tool or migration command to use, so they work
for any language a project uses.

What the package adds to the method it implements:

| Addition | What it means for you |
|---|---|
| Invention lists | The agent lists every decision its inputs did not settle, instead of quietly choosing |
| Status needs evidence | A use case moves to Implemented or Tested only when a check or a report shows it |
| Checks run by scripts | Lint, finish check, guard check and coverage are scripts, so they hold even when a model skips an instruction |
| Read-only reviewers | Review and audit report findings; they never edit what they judge |
| One home per fact | Every kind of information has one place; everything else refers to it |
| A rigor dial | Throwaway, solo or team: the ceremony fits the project |

What it does not do: it does not decide what your product should be (the
vision is always written by a person), it does not approve anything (approval
is always a person's), and it does not deploy, publish or change anything
outside the project's folder.

## 2. Installing

### Requirements

- Python 3.9 or later. The bundled scripts use the standard library only.
- git. Several checks read the project's history.
- An agent that loads skills: Claude Code, or another agent that reads skill
  folders (see [section 11](#11-working-with-different-agents-and-models)).

Installing the project layout and checks reads the plugin's folder: run
`python3 "<skill-folder>/scripts/scaffold_docs.py" --root . --profile solo`
in place from the setup skill's base directory, first for its plan, then
with `--apply` after agreement. Keep the script path quoted when substituting
the installed folder, including a folder with spaces. The script writes
the agreed files into the project; the agent does not run a copy command.
A tool's permission mode may ask for access to that folder. If a step is
refused or fails, report the command, what is installed and what is missing,
and commit nothing half-written. Resolve that access or failure before
resuming. No script sends anything over the network.

### Claude Code

Add the marketplace once, then install the plugin:

```text
/plugin marketplace add ChristianOrrala/plugins
/plugin install upspec@christian-orrala
```

Skills load on demand: Claude reads a skill when your request matches its
description. You can also call one by name, for example
`/upspec:up-5-writing-use-case-specs`.

### Other agents

Copy the skill folders from the plugin's `skills/` folder into the folder
where your agent discovers skills. For the Antigravity CLI (`agy`) that is
`.agents/skills/` in the project. Each skill folder is self-contained: its
references, templates and scripts travel with it. Tools that read the
Agent Plugins format can install the plugin folder instead: it carries a
`plugin.json` for them. Codex installs it from the same marketplace:
`codex plugin marketplace add ChristianOrrala/plugins`, then
`codex plugin add upspec@christian-orrala`.

### The A-files (optional)

The same marketplace lists a second plugin, the A-files
(`/plugin install a-files@christian-orrala`). It keeps five files at
the repository's root that every coding agent reads first (`AGENTS.md`,
`ACTIVE.md`, `ABILITIES.md`, `AHEAD.md`, `ATLAS.md`) and checks their shape
before every commit. Each plugin works alone; when a project has both, they
work together (section 5, "With the A-files").

### One set at a time

Seven of these skills answer requests that other spec-driven skill sets also
answer: requirements, the entity model, use case diagrams and specifications,
their review, test cases and recovery. With two such sets installed, both
respond to the same request. Use one set for those requests.

## 3. First steps

**A new project.** Ask:

> Set this repo up for spec-driven development.

The setup skill asks one question (will this be maintained or handed over?),
proposes a rigor profile, shows the plan as a dry run, and writes the docs tree
and the rules block of your guideline file only after you say yes. Then write
the vision yourself (`docs/vision.md`), or let the agent interview you and
record your answers.

**An existing codebase.** Ask:

> Reverse-engineer this system into specifications from its code. I'm the
> owner, so ask me whatever only I can decide.

**Specifications or tracking files already there.** When the project keeps
specifications in another folder or another format, or tracks its
work in files such as a board or a feature list, setup lists them and asks
once: full alignment (everything moves into the root and `docs/`, and
`scripts/relink.py` checks every reference to what moves, agent instructions
included) or keep (a specification folder is recorded with `--specs-folder`,
nested or not; files in another format stay as references). Full alignment
of specifications in another format goes through the migration
(`up-migrating-spec-formats`): its plan converts mechanically only the parts
that match an earlier upspec format, and the agent converts the rest by
judgment, with an invention list and your yes before anything is committed. Recovery is for a system that has code and no
specifications. When the project
tracks its work in the A-files, setup joins them; when you ask for the
A-files and they are not there yet, setup hands over to the A-files skill
first and writes nothing.

**Not sure where you are.** Ask:

> Where are we with the specs, and what comes next?

The router (`up-0-navigating-spec-driven-work`) reads the repository's state
and names the single next step and the skill that performs it. It also gives
the debt from `ACTIVE.md`, the Next up list from `AHEAD.md` and, when format
findings exist that do not block, one "to clean" line. The report and the
hooks' questions name each use case, rule, requirement, ability and AHEAD item
with its title, as in `UC-001 (Book Repair)`, and rule 11 of the rules block
asks the agent to do the same in its messages. Files, commit lines, code
markers and test names keep the bare identifier.

**What authorizes work.** A request authorizes what it asks to happen now, under its stated conditions; preparing for approval authorizes preparation only. A reserved approval requires an owner reply granting the named slice; record its date and words. An agent-written record, tests, a review verdict, a status label or an answer to another question cannot grant it. If a reply is unclear or approves one slice and defers another, work on the approved slice, do as much as it allows, state your reading and say what still waits. A missing specification, format or lint warning, or an open technical name adds no condition.

**An explicit request outside the specifications.** When you explicitly ask in
the session for behavior no use case covers, the agent says so, records the
missing use case to write as open work (with the A-files, an item in `AHEAD.md`; otherwise, where
upspec's hooks are installed, the deferred list through the hook's `later`
command; with neither, name the missing use case in the report and in the
commit message), and does the work. A behavior decision goes back to you when it changes an outcome named by the request or specification. Agents set Implemented
and Tested when evidence exists; only a person sets Approved and Done. A reserved approval still holds until you grant it.

**A fix, a change or a feature.** Just ask for it:

> Members can borrow a sixth book. Bug or feature?

On a project with approved use cases this is the daily entry. Triage
(`up-1-triaging-change-requests`) reads the use case first, classifies the
request, finds what it touches and states a size line (see 7.3). The router is
for the questions that need the state of the whole project.

**A repository without setup.** With no rules block, no vision and no
specifications, a task runs outside the method. Whichever of the router and
triage was started says one line and asks nothing, and the task goes ahead as
ordinary work:

> No upspec setup here; this task runs outside the method. Say "set up" to start.

**Cleaning up.** Say "clean the specs" and the router lists the format findings
that do not block, file by file, with the skill that repairs each. It edits
nothing itself.

## 4. Core concepts

### The chain of artifacts

```text
vision (a person) ─► requirements ─► entity model ─► use case map
                                                          │
       ┌──────────────────────────────────────────────────┘
       ▼
  specification ─► review ─► approval (a person) ─► code ─► tests ─► audit
                                                              │
                                          journey test cases ◄┘
```

Every later request (a bug, a change, a new feature) enters through triage,
which turns it into a change that starts at the specification. Recovery brings
an existing system to the same starting point.

### Use cases

A use case is one goal of one actor, reached in one sitting: *Book a repair*,
*Reset a password*, *Export completed work orders*. Its specification holds:

| Part | What it says |
|---|---|
| Goal and trigger | The outcome the actor walks away with, and the event that starts it |
| Preconditions | What is already true and never checked again |
| Main success scenario | Three to nine steps in which everything succeeds |
| Alternative flows (`A1`, `A2`, ...) | Each way a step can go differently, with an explicit ending |
| Postconditions | What is true on success, and what is guaranteed on every failure |
| Business rules (`BR-001`, ...) | Named decisions with boundary examples |

Use case section headings match regardless of letter case, repeated spaces or a
trailing colon: `## Main success scenario` and `## Main  Success Scenario:`
name the same section. Two headings with the same canonical name are reported
as `DUPLICATE_SECTION`; diagnostics keep the headings as written.

A specification says what a stakeholder can observe and a test can verify. It
says nothing about how the system does it.

### Identifiers

| Identifier | Unique within | Cited elsewhere as |
|---|---|---|
| `FR-001`, `NFR-001`, `C-001` | The requirements catalog | The same |
| `UC-001`, `TC-001` | The project | The same |
| `BR-001` | Its use case | `UC-001 BR-001` |
| `A1` | Its use case | `UC-001 A1` |

Identifiers are never reused and never renumbered. A rule that leaves a use
case keeps its heading with a line saying where it went.

### Status of a use case

| Move | Evidence it needs | Who |
|---|---|---|
| Draft → Reviewed | Validator clean; author's checklist done | Author |
| Reviewed → Approved | Independent review says ready; a named person signs off | **Owner, a person** |
| Approved → Implemented | Code merged, rule markers in place, finish check ready | Implementer |
| Implemented → Tested | Coverage matrix complete; suite green | On the audit's suggestion |
| Tested → Done | Business review of the working slice accepted | **Owner, a person** |
| any → Reviewed or Approved | The specification changed | Whoever changed it |
| any → Obsolete | Superseded; the file stays | Owner |

An agent proposes a move together with its evidence. It never sets Approved or
Done. The stop and push checks report evidence missing for a raise to
Implemented or Tested (Done uses Tested's check). Changed use cases at
Reviewed or above that do not validate are reported as problems at push;
Draft findings warn. An invalid Status is an error of the lint even in a Draft.

### Markers

Code that enforces a rule carries a one-line comment directly above it:

```text
UC-005 BR-003: A guest must be at least eighteen years old on the day of arrival.
```

Tests carry the use case identifier in their suite name and name the flow and
rules they cover. Markers are how the checks find the code and the tests of a
specification.

### Inventions

When the agent must decide something the specification does not settle, it
lists the decision instead of hiding it: in the specification's hand-off, in
the change record's assumptions, and in the implementation report. A free
detail is declared as free.

A name or signature the specification leaves open (function, module, file or
parameter) is a technical choice (rule 8): pick one, list it in the invention
list and go on. Where the specification names an interface, its names bind.
Ask about a behavior decision that changes an outcome that the request or specification names; otherwise record the closest reading as an assumption and name it in the handoff. Record a reading for each unanswered behavior item. An answer goes into the specification; if you say to continue without answering, the agent implements the recorded reading.

## 5. The project's files

```text
docs/
├── vision.md
├── requirements.md
├── entity_model.md
├── use_cases.md
├── use_cases/UC-XXX-name.md
├── processes/name.bpmn
├── test_cases/TC-XXX-name.md
├── change-records/UC-XXX-name.md
├── reviews/
└── recovery/
```

| Path | Content | Written by |
|---|---|---|
| `docs/vision.md` | Purpose, users, goals, scope in and out | A person |
| `docs/requirements.md` | Functional (`FR`), non-functional (`NFR`) and constraint (`C`) rows | `up-2` |
| `docs/entity_model.md` | Entities, relationships, attributes, lifecycles; the project's vocabulary | `up-3` |
| `docs/use_cases.md` | Scope, delivery order and the generated actor-goal table and Mermaid overview | `up-4` |
| `docs/use_cases/UC-XXX-<name>.md` | One use case specification per file | `up-5` |
| `docs/processes/<name>.bpmn` | Optional business process models | A person |
| `docs/test_cases/TC-XXX-<name>.md` | One end-to-end journey per file | `up-writing-journey-test-cases` |
| `docs/change-records/UC-XXX-<name>.md` | One record per change | `up-1-triaging-change-requests` |
| `docs/reviews/` | One review report per scope (`<scope>-review.md`, overwritten by each review), numbered audit reports (`<scope>-audit-<n>.md`), the guard-check log | `up-6`, `up-9`, guard checks |
| `docs/recovery/` | Ledger, suspects, baseline review plan, change log of a recovered system | `up-recovering-specs-from-code` |
| `CLAUDE.md` or `AGENTS.md` | Guideline file with the rules block and the profile | `up-bootstrapping-spec-driven-projects` |

**Language.** Specifications and records are written in the project's own
language. Front matter keys, section headings, table columns, Gherkin
keywords, flow labels (`**Trigger:**`), Status values and flow endings (`Use case ends.`) stay as the template has
them, because the scripts read them.

**People.** Specifications and records name roles (the administrator, a
member), never people, and use invented example values.

**Another folder.** A project that keeps its specifications outside `docs/`
records the folder in the rules block as `**Specs folder:** DIR` (setup writes
it with `--specs-folder DIR`; a nested folder such as `documentation/specs`
works). Every script reads it, and `--docs DIR` overrides it for one run.

### 5.1 With the A-files

When the project also tracks its work in the A-files, the two join by files,
and neither moves the other's:

- `AGENTS.md` names the specification rules in its hot zone and, when the
  project keeps `ABILITIES.md`, keeps two rows in step with the use cases
  (P1).
- An ability in `ABILITIES.md` may name its use cases in a `Specs` line. The
  router warns when an ability is done while one of its use cases is not,
  planned while one is built, or in progress while all of them are `Done`,
  and notes use cases no ability names (P2). It
  reads an ability's status from its row in any index table of
  `ABILITIES.md`, so done rows may sit below the hot zone, and from an old
  entry's Status line when the row has none.
- A project with the small A-files setup (`AGENTS.md` and `ACTIVE.md`, no
  `ABILITIES.md`) hears nothing about abilities: no unnamed use cases, the
  close-out and the finish check's warning name `ACTIVE.md` alone, setup adds
  no keep-in-step rows about abilities, and the use case map proposes none.
- The router answers for the current work in `ACTIVE.md` first and says what
  blocks it; with no current work it takes AHEAD's first Next up item when
  that item's ability names use cases, and otherwise decides as usual
  (P3).
- An AHEAD item may cite a requirement deferred in the catalog by its
  identifier (`FR-012`), or link the change record of a change accepted for
  later; the requirement and the record stay where they are, nothing is
  copied (P4).
- `ATLAS.md` has a row for the specifications (P5).
- The finish check warns when a use case's Status changes while `ACTIVE.md`
  and `ABILITIES.md` stay as they were (P6).
- The state report also shows AHEAD's Next up list (`Next up:`) and the bullets
  of `ACTIVE.md`'s `## Debt` section (`Debt:`, one line each, at most five and
  then "and N more"). The session-start hook passes the same view on (P7).
- The Next step block has a `when:` line after `reason:` (and before `what:`):
  `no other task is in hand; a fix, change or feature on an existing use case
  goes to up-1 first`. It says the step applies when nothing else is being
  worked on, and that a fix, change or feature on an existing use case starts
  with `up-1-triaging-change-requests`. The migration step has no such line.
- When you answer "later" to the end-of-turn question, the drift becomes one
  AHEAD item: an index row with the next free identifier, kind `idea`, state
  `open`, and an entry with What, Why and Write-up. The same drift is
  recorded once (P9).
- The end-of-turn question runs the A-files check as its command line
  states (`--strict`, again without it when the check exits 2; exit 0 when
  the A-files are clean; exit 1 and one `path:line: ERROR CODE: message` line
  per problem), and knows a finding by
  its path, code and subject, never by a count in its message (P10).

A tracking file kept at adoption (the board, say) becomes the A-file's home:
the A-file names it with `**Home:**`, and the router then guesses nothing from
it. Without the A-files the skills behave as before.

**Mixing versions.** These skills read the files of earlier and later A-files
releases alike: the status from the row or from an old entry. Two limits
belong to the earlier releases and stay:

- upspec 1.2.0 reads an ability's status only from its entry, so with A-files
  that keep it in the row alone it warns about no ability's status; on a small
  setup it notes every use case as named by no ability. Upgrade the skills to
  read the row and go quiet.
- The A-files check of 1.2.4 needs at least one ability row in the hot zone of
  `ABILITIES.md`: with every row below it, that check reports `NO_INDEX`. Keep
  one open row in the hot zone, or upgrade the A-files with these skills.

### 5.2 The formats

Front matter starts at the first line between `---` delimiters. The supported
subset is top-level `key: value`, inline lists, quoted strings and comments.
No nesting, anchors or multiline values; `FRONT_MATTER` reports violations.
A value written over several lines is refused once, with what to do instead:
write it on one line. For a goal the message adds that a goal needing more
than one line is usually two goals. An `id` refused this way leaves its file
unidentified until it is fixed: the lint reports nothing else about it. An
`id` or a `goal` refused this way stops `use_case_map.py` from writing: it
writes nothing rather than drop the use case from the overview or empty its
goal, and exits 1. `use_case_map.py --check` reports each refusal as
`FRONT_MATTER` with its line, judges the rest of the overview as it will read
once the value is on one line, and exits 1 only with `--strict`. Until the
value is on one line, the state report's text lists the `FRONT_MATTER`
finding and names `FIX_FORMAT` as the next step, and `--format json` gives
the overview `current: false`. Such a finding blocks, because the overview
cannot be written until it is repaired; with the overview skipped nothing
blocks. Every other format finding is not a next step: the report lists it on
one line, `To clean (not blocking): N format findings in M files. Say "clean
the specs" to fix them.`, and `--format json` marks each finding with
`blocking` and with `skill`, the skill that repairs it. When every use case is
Done and such findings remain, the idle step's reason reads `Nothing in
flight; N item(s) to clean.` A use case with no ID, an ID used twice or a Status
that is not a Status stays a step (`FIX`), because it hides a use case.

| Artifact | Required keys | Optional keys |
|---|---|---|
| Use case | `id`, `name`, `primary_actor`, `goal`, `trigger`, `status`, `requirements` | `secondary_actors` |
| Overview | `system` | — |
| Journey | `id`, `goal`, `priority`, `status`, `use_cases` | `process` |
| Change record | `outcome`, `element`; `decided_by` for outcomes 2, 4, 5, 6 | `decided_by` for other outcomes |

A mapped use case starts as a stub: required front matter, `status: Draft`,
and `Not written yet.` as the body. Past Draft a stub reports `STUB`.
People write Scope and Delivery order in `docs/use_cases.md`. After adding a
use case or changing its id, name, actors or goal, run `scripts/use_case_map.py`.
Never edit between the generated markers. Status changes need no regeneration.
The actor-goal table and Mermaid use case diagram are generated (Mermaid
12.0.0 or later draws it); `STALE_OVERVIEW` means regenerate them. Business processes remain BPMN 2.0.

Requirements tables:

- Functional: `ID | Role | Need | Priority | Status`. Need is a short verb
  phrase of what the role must be able to do.
- Non-functional: `ID | Title | Statement | Category | Verification | Priority | Status`.
- Constraints: `ID | Title | Statement | Category | Source | Priority | Status`.

Each Statement follows an EARS pattern: `The <system> shall …`,
`When <trigger>, the <system> shall …`, `While <state>, …`,
`If <condition>, then the <system> shall …`, or `Where <feature is present>, …`.
NFRs keep a numeric threshold, unit and condition. `NEED_FORM` reports a
missing Role or Need, or a statement outside those patterns.

Entity attributes use `Attribute | Meaning | Type | Rules`. Types are Text,
Number, Money, Date, Date and time, Yes/No, Identifier, Choice of …, and
Reference to ENTITY. No storage lengths, keys or sequences. The Mermaid
`erDiagram` owns relationships; `REFERENCE_NO_RELATIONSHIP` reports a
reference without one, and `ENTITY_TYPE` an unknown type.

Each business rule has a `### BR-001: Name` heading, a sentence and an Examples
table, with a blank line before the Examples table. Input columns precede
`result`, the last column. Keep at least two rows for every active rule.
Fill every cell and include a row on each side of every stated boundary.
Otherwise the check reports `EXAMPLES_FORM`.

A journey has exactly one fenced `gherkin` block and one named Scenario.
Steps use Given, When, Then, And or But, with literal test data in quotes.
Each use case listed in `use_cases` is named by a comment on its own line,
`# UC-001` or `# UC-001 Name`, immediately above its first step. Every such
comment names a listed use case. Closing Then steps verify the end state;
`GHERKIN_FORM` reports violations. Roles, Preconditions and Postconditions
remain in the body. `process`, when present, is the relative BPMN path.

Change records have outcomes 1 through 7 or `migration`, and four required
sections: Context (report and sign-off test), Decision (owner's decisions
table with each decision's element), Specification change, Consequences
(differences from today and impact). Sources of new behavior, Assumptions,
Reproduction and Urgent path appear only when applicable. `RECORD_FORM`
reports an unknown outcome or missing required section.

## 6. The skills

Every skill name starts with `up-`. 0 and 1 are the two entries (0 for the
state, 1 for a change); 2 to 9 are the artifact chain in the method's order;
unnumbered skills are used when needed.

| Skill | Use it to | It produces |
|---|---|---|
| `up-0-navigating-spec-driven-work` | Find out where the project stands and what comes next, with the debt, what is ahead and what to clean | A recommendation; writes nothing |
| `up-1-triaging-change-requests` | The daily entry: turn a fix, change, feature or hotfix into a specification-first change | A classification, a size line and a change record |
| `up-2-cataloging-requirements` | Turn a vision, notes or an interview into requirements | `docs/requirements.md` and a conflict ledger |
| `up-3-modeling-domain-entities` | Build or change the entity model and its vocabulary | `docs/entity_model.md` |
| `up-4-mapping-use-cases` | Decide which use cases exist, at the right level, in what order | `docs/use_cases.md` and a delivery order |
| `up-5-writing-use-case-specs` | Write or revise one use case | `docs/use_cases/UC-XXX-<name>.md` |
| `up-6-reviewing-specifications` | Review a use case or the whole set, without editing it | A review report with a verdict; a traceability matrix on request |
| `up-7-implementing-use-cases` | Implement or synchronize one approved use case | Code with markers, a plan, an invention list, the finish check's report |
| `up-8-deriving-use-case-tests` | Derive and maintain the tests of one use case | Tests per coverage unit, each rule test proven by a guard check |
| `up-9-auditing-spec-coverage` | Check that code and tests realize the specification | A coverage matrix or the spec dashboard; a suggested Status |
| `up-bootstrapping-spec-driven-projects` | Set a repository up: profile, docs tree, rules block, team instruments | The docs tree, a vision skeleton, the rules block; for teams, ownership, a pull request template and a pipeline job |
| `up-recovering-specs-from-code` | Bring an existing system under specifications | Use cases, entities, specifications, an evidence ledger, suspects, a baseline review plan |
| `up-splitting-bounded-contexts` | Split a specification set that has outgrown review | Proposed contexts, assignments and contracts; the move, on approval |
| `up-writing-journey-test-cases` | Write an end-to-end journey across use cases | `docs/test_cases/TC-XXX-<name>.md` |
| `up-migrating-spec-formats` | Move earlier specification formats, or another format, to the current ones | A mechanical plan and judgment items; on approval, converted specifications in one or two commits |

You rarely need to name a skill. Describe the work ("write the use case for
resetting a forgotten password", "is UC-004 fully tested?") and the matching
skill is used. When in doubt, ask the router.

## 7. Workflows

Each workflow lists who does what. "You" is the owner; "the agent" is the
coding agent with the skills.

| Workflow | Route |
|---|---|
| Small change | short path: one use case's existing steps, rules or flows; no entity, no new use case, and no interface another use case reads changes. |

### 7.1 Starting a new project

1. **Set up.** Ask the agent to set the repository up. Choose a profile
   ([section 10](#10-rigor-profiles-throwaway-solo-team)), read the dry run,
   and say yes. The overview's `system` starts with the repository folder's
   name, quoted when needed; edit it later to the system's actual name.
2. **Write the vision.** `docs/vision.md` is yours. It must name the actors by
   role, the core nouns with their meaning, and the boundaries (in scope, out
   of scope, neighboring systems). The agent can interview you and write down
   your answers, but it never invents a vision.
3. **Requirements.** "Turn the vision and these notes into requirements."
   Review the conflict ledger it returns and decide each open item.
4. **Entity model.** "Model the entities." The model becomes the vocabulary
   every specification must use. In the solo profile it may start thin, with
   only what the first use case needs, and grow with each use case; it still
   comes before the first use case.
5. **Use case map.** "Which use cases do we need?" Agree on the list and the
   delivery order of the first slices.
6. **First specification.** "Write UC-001." Answer its questions (at most five
   per use case). Everything else it assumes is listed in its hand-off.
7. **Review.** "Review UC-001." The reviewer works from the files alone,
   reports a verdict and saves it as `docs/reviews/UC-001-review.md`,
   overwriting the last one. A later review compares with that report (or
   with the newest numbered report of an earlier release). A warning it finds on
   text that has not changed since was missed before: it is listed in its
   own block and keeps the use case from ready for approval until it is
   fixed or you decline it; you can decline them all in one answer, and a
   declined finding is not raised again. Findings of severity `info` never
   count.
8. **Approve.** Read the specification and the review, then set
   `status: Approved` in the front matter yourself.
9. **Implement and test.** "Implement UC-001 with its tests." See 7.4.
10. **Audit.** "Is UC-001 fully tested?" The audit suggests whether Tested is
    justified. The report lists the recovery change log entries in change on the use case; a report without gaps is what closes them.

### 7.2 Bringing an existing codebase under specifications

1. **Ask for recovery.** The agent maps actors, entry points, entities and use
   cases from the code, keeping an evidence ledger: every claim points at the
   line that decides it.
2. **Choose the depth.** Four choices: full specifications only for the use
   cases about to change; a short baseline for every use case; a baseline for
   every use case and full ones where change is coming; or full for all. The
   agent says what each costs to review and recommends one from the system's
   size; full for all is yours to choose at any size.
3. **Suspects, not corrections.** Behavior that looks wrong is recorded as
   suspect (`S-012`) and named in the text. Nothing is fixed during recovery.
4. **Verification pass.** A second reader checks a random sample of claims
   against the code, looking for counterexamples to every rule and failure
   guarantee. Rounds repeat until a sample comes back clean.
5. **Baseline review.** With you in two roles (what the system does, and what
   it was meant to do), the review settles suspects and moves the
   specifications to Reviewed. Approved stays yours to write.
6. **First change.** From here every change goes through triage (7.3). Today's
   behavior is pinned by tests before the first change.

**The alignment backlog.** What the owner decides to fix later stays in the
change log as `later` (or `later: <the decision>`), beside claims old
documents make that the code never built (kind `Claimed but not built`). A
change that takes one up writes `in change: <record>`; the coverage audit's
report closes it as `aligned: <report>` only when each cited report lists
the entry on its `Change log` line; a dropped one keeps its reason.
With the A-files, recovery drafts one AHEAD item per use case and writes
them on your yes. The router prints `Alignment: N open (...)`, a `ready`
hint when an entry's use cases are Tested or Done and only the audit's
report is missing, and a warning when an ability is done while its use
cases still have open entries. The backlog never blocks new work.
The router keeps an aligned entry open, with a warning, while its reports fail the shared closure check.

### 7.3 Changing behavior the system already has

This is the most common workflow once a project is under specifications.

For a qualifying small change, triage routes to up-7's short path: edit the
specification line, pin it with a test, make the change, run validator and tests,
and add one line to the change log in the commit message. It skips the element-to-code table, full
invention list unless an invention appears, specification delta and test
derivation. The approval rule still applies; only a person accepts. The bug
light path remains distinct; changes outside both paths follow the full path.
Triage checks cross-references with `impact.py` or by reading other use cases; if another use case reads the changed interface, it takes the full path. The owner's request grants the slice under its conditions, including an `Approved` line: record the request’s date and words beside the changed line. A `Draft` or `Reviewed` Status stays as it was; a later active Status (`Approved`, `Implemented`, `Tested`, `Done`) goes down to `Reviewed` for the specification edit. Implement without waiting for fresh approval, and name the resulting Status in the handoff. A person sets `Approved` and `Done`; acceptance outstanding is not blocked. A small change gets no change record.


1. **Tell the agent what you want.** "When a code expires unclaimed, tell the
   group too." Triage reads the specification before any code.
2. **Classification.** The agent applies the sign-off test: would you have
   signed the specification as it stands, knowing what you want now? The
   outcome is one of seven (see [section 8](#8-the-change-record)). For a
   specification that is wrong, ambiguous or simply outgrown, it asks you to
   confirm. With no behavior change (outcome 7) it gives the line
   `No behavior change: UC-NNN` and stops.
   Otherwise it lists what the change touches and states its size in one line:
   `Size: <local|wide|structural> (N use cases[, entity model]). Say another
   size to change it.` The table is fixed, tried in order, and the first match
   wins: structural for a new use case or a change to the vision's scope; wide
   for two or more use cases or a change to the entity model; local for
   anything else. Independent changes that share no use case, rule or entity
   are sized each on its own, with the order agreed and the rest recorded as
   later work. The size is information only: it changes no rigor, and you can
   name another size. At the end, each skill of the chain tells you the step
   that normally follows, and says that a gap earlier in the chain comes first
   and that the router's state report decides when in doubt.
3. **The change record.** For a change to the specification (outcomes 2,
   4, 5 and 6), the agent writes
   `docs/change-records/UC-XXX-<name>.md`: what differs from today, your
   decisions and where each one lives in the specification, the source of
   every new flow and rule, and the assumptions you still have to confirm.
4. **The specification change.** The agent updates the specification and
   resets its Status to Reviewed. A correction found on the way is a
   difference too: it goes into the record before the file changes.
5. **Review.** An independent review checks the specification, runs the lint,
   and lists any flow or rule changed outside the record.
6. **Approve.** You set Approved.
7. **Implement.** The implementer runs the finish check before any code. Rows
   whose today's behavior was only read from the code are pinned with a test
   first, committed alone. Then it changes the code, places markers, updates
   or writes the tests, breaks each rule on purpose to prove its test catches
   it, and runs the finish check until it says ready. It proposes Implemented.
8. **Audit.** "Is UC-XXX fully tested?" The audit reports gaps and the Status
   the evidence supports.

### 7.4 Implementing an approved use case

For a qualifying small change, the implementer uses the short path in 7.3,
skipping the element-to-code table, full invention list unless an invention
appears, specification delta and test derivation. The approval rule stays,
and only a person accepts. The bug light path remains available for code wrong
against a clear specification.

The implementer reads only the use case, its linked requirements, the entity
model and the guideline file. Then:

1. It shows an element-to-code plan and the decisions the specification leaves
   open. Open actor actions or system answers stop the run and become
   questions for you; unspecified names and signatures are technical choices
   the agent picks and lists, as described under Inventions.
2. It works on a branch for the use case, never on the main branch.
3. Schema changes follow a guarded procedure with a rehearsal and your
   confirmation; nothing destructive runs unconfirmed. A schema change that
   adds or changes a business concept, a key, a uniqueness constraint or a
   version column included, starts in the entity model. Only an index or
   partitioning, which no flow can observe, is a technical change: triage
   classifies it as no behavior change, and it carries the line
   `No behavior change: UC-012` (or `none` and the reason) instead of a
   specification change. A foreign-key constraint added later, for a
   relationship the entity model already states, is the code catching up
   with the model (triage outcome 1, with no element): it takes the
   destructive path, with your yes and a count of the rows that violate it,
   the model stays unchanged, and the commit names the relationship and
   carries `Fixes: UC-012`, naming the use case whose relationship it
   enforces. The spec-first guard reads that note.
4. It audits the scope: every changed file must belong to the use case.
5. It runs the project's tests and reports failures as they are.
6. It runs the finish check and pastes its report, filling in the three fields
   the check cannot verify (tests run, guard check, inventions).

### 7.5 Fixing a bug

Report it as you see it: "Users say booking a full day still works." Triage
decides whether the code, the specification or a test is wrong.

Code that is wrong against a clear specification takes the light path, a test
and a line:

1. A failing test named after the use case and the element the code breaks (a
   rule, a flow, a step, a precondition or a postcondition), for example
   `test_uc001_br001_ninth_order_is_refused`.
2. The fix, with the rule's marker where it enforces a rule.
3. If you want proof that the test guards the element, its guard check
   ([section 9](#9-the-checks)). Its verdict is information; nothing waits
   for it.
4. The note `Fixes: UC-001 BR-001` in the commit message. The spec-first
   guard and the agent hooks read it and do not report the change as code
   without a specification. If the session stops before the
   commit, the hook sends the agent one note about the fix, as for any code
   without a specification; it is not a question to you. The agent commits
   the fix with its `Fixes:` line, which closes the note. A fix committed
   with its note before any stop draws no note.
   A `Fixes:` line that names no use case, such as `Fixes: #123`, is not the
   note.

No change record, finish check, test derivation or audit, and the Status
stays where it is. A test that is wrong is fixed the same way, without a
note: test files are never behavior code. A change with no behavior change
carries its `No behavior change: UC-012` line and nothing else.

For a specification that is wrong, the change goes
through 7.3. An urgent production fix takes the urgent path, which keeps the
same order at its smallest and takes minutes: the smallest specification edit,
a failing test, the fix, one change set, one reviewer. A code-only fix with
the specification promised for later is not offered.

### 7.6 Tests and journeys

- **Tests of one use case.** "Write the tests for UC-004." The test skill lists
  the coverage units (main scenario, each flow, each rule with its boundaries,
  postconditions, failure guarantees), writes one traceable test per unit,
  asserts outcomes rather than internals, and proves each rule test with a
  guard check.
- **Journeys.** "Write the journey from booking to collection." A journey test
  case chains several use cases with literal test data and checks at the seams
  between them. It can be derived from a business process model.

### 7.7 Checking progress

- "Is UC-004 fully implemented and tested?" gives a coverage matrix of every
  step, flow, rule, postcondition and linked quality requirement against code
  and test evidence, with gaps, drift and the justified Status.
- "Show the spec dashboard" gives two tables: requirements and use cases
  complete, in progress or not started.

### 7.8 Splitting a large specification set

When the set is too large to review, or several teams collide in `docs/`, ask
how to split it. The agent measures the set, clusters use cases by shared
entities and actors, and proposes contexts named after business capabilities.
Every requirement, entity and use case goes to exactly one context; shared data
becomes an explicit contract. Files move only after you approve, with their
identifiers and history kept.

### 7.9 Moving a project to the current formats

When a check reports `OLD_FORMAT` (exit 5), normal work stops. The router's
single next step is `MIGRATE` → `up-migrating-spec-formats`.

The migration first inventories old files and shows a mechanical dry run.
A separate judgment pass lists choices and inventions for you to decide.
After your approval it commits the mechanical conversion, then the judgment
changes (one commit when nothing is mechanical), replaces installed checks in `tools/specs/`, regenerates the overview
and verifies the formats. Identifiers and Status stay unchanged; Approved use
cases keep their approval. The change record uses `outcome: migration`.

Specifications in another format take the same skill: ask for them to be
moved to the current formats. The plan converts mechanically only the parts
that match an earlier upspec format; the agent converts the rest in the
judgment pass, lists every meaning it decided, and commits nothing before your
yes. Then it asks whether the old files stay as references or move.

Run the migration skill's `scripts/migrate_formats.py plan|apply|verify --docs DIR`.
Plan is read-only and runs without git, with a warning that apply needs it.
Apply needs a clean git work tree; verify also requires git. Missing git or a
folder outside a git work tree reports `GIT_UNAVAILABLE` with exit 3. Apply
records every planned text and fingerprint before writing, in
`upspec-migration.json` in the git
directory (also in linked worktrees). After interruption, rerun apply with the
same HEAD and docs folder. Resume recognizes completed writes and refuses
files changed by a person or unrelated uncommitted work. Keep the journal
until apply completes. An artifact the method owns that cannot be read (a
link that cannot be resolved, a folder that cannot be listed or searched, or
a file that is denied or not UTF-8) stops plan and apply, a resumed apply
included, with exit 1 and its `UNREADABLE` line on standard error before
anything is planned or written, as verify reports it: each of them, and
verify, first reads whole every text the migration or verify reads (the
vision, the catalog, the entity model, the overview, every use case, journey,
process model, recovery record and change record; a process model's bytes
only, since XML names its own encoding). The earlier formats themselves never
stop them.

An uncertain conversion leaves the entire file and its filename unchanged and
lists the reason under judgment. Dependent overviews and stubs wait for that
document. A diagram with unmapped lines stays intact; its judgment items name
each line, while the overview can still be generated from supported content.
Writes are limited to the rules block's recorded Specs folder (otherwise
`docs/`) and `tools/specs/`. An unauthorized `--docs` is refused with exit 2
before reading specification contents or creating a journal. Resume checks
every target and rename source against the same boundary and refuses conflicts.
Apply rechecks their fingerprints immediately before each mutation, keeping
the journal and any owner edit when a conflict stops it. Journey Process lines
and change-record Next instructions carry over verbatim; requirement titles
and benefits remain as context for owner judgment.

Installed checks use setup's classification. While any copy is changed and
undecided, migration replaces and adds no scripts; specifications still convert.
The plan names each changed file and `scaffold_docs.py --update` with
`--replace` or `--keep`. Once decided, untouched copies are refreshed and the
whole missing set is added, including hooks, when `tools/specs/` exists.
Current and kept copies stay; each script written gets a bundle baseline.
Verification checks all formats and the generated overview. Other lint findings are listed
for you without changing the verification result. A file verification cannot
read, and a lint that cannot run, are findings like the others. Exit codes are 0
for done, nothing to do, or a verification that ran whatever it found (with
`--strict`, 1 on a finding), 1 when plan or apply cannot read a file, 2 for
usage, and 3 for git or resume conflicts. The environment
variables `UPSPEC_MIGRATE_STOP_AFTER` and `UPSPEC_MIGRATE_CRASH_AFTER_WRITE`
exercise interruptions in tests; leave them unset during ordinary migration.

## 8. The change record

A change record is the agreement behind one change to a specification.
Triage writes one for outcomes 2, 4, 5 and 6; the specification writer, the
reviewer, the implementer and the finish check all read it. Outcomes 1, 3 and
7 change no specification and get no change record (outcome 1 takes the light
path of [7.5](#75-fixing-a-bug)). A record of an earlier release with another
outcome stays valid.

Front matter holds `outcome` (1–7 or `migration`), `element`, and
`decided_by` (required for outcomes 2, 4, 5 and 6). The record is found by path;
it has no identifier.

| Required section | What it holds |
|---|---|
| Context | The report or recovery change log entry, and the sign-off test |
| Decision | The chosen outcome and your decisions table, with the specification element carrying each decision |
| Specification change | What changes in which element, and the Status reset |
| Consequences | Differences from today (`Element \| Today \| After the change \| Requested by \| Seen in`) and upward, sideways and downward impact |

Sources of new behavior, Assumptions, Reproduction and Urgent path appear only
when applicable. A new flow or rule needs its source; an assumption names its
element. Defects get a reproduction and hotfixes an urgent-path account.
Pinning and other next steps belong with Consequences.

**Seen in** says how today's behavior is known: `code` (read from the code, so
it must be pinned by a test before it changes), `test <name>` (pinned by that
test), or `observed` (seen on the running system with its real services).

**The seven outcomes of triage:**

| # | Outcome | It is when | What changes | Status |
|---|---|---|---|---|
| 1 | Code wrong | The specification is clear and right | Code, behind a failing test; the commit carries `Fixes: UC-012 BR-005`, no change record. A foreign-key constraint for a relationship the entity model states: the destructive path of the schema procedure, the model unchanged, and the commit carries `Fixes: UC-012`, the use case whose relationship it enforces | Unchanged |
| 2 | Specification wrong | It says something nobody meant | The specification | Back to Reviewed |
| 3 | Test wrong | Code and specification agree; a test does not | The test | Unchanged |
| 4 | Specification ambiguous | Two readings; the code picked one | The specification, after you choose | Back to Reviewed |
| 5 | Enhancement | The specification was right for what was wanted then | The specification | Back to Reviewed |
| 6 | New use case | A goal no use case covers | Requirement, map, new specification | New file, Draft |
| 7 | No behavior change | Refactoring, dependency update, infrastructure | Nothing; the change carries `No behavior change: UC-012` | Unchanged |

## 9. The checks

The skills run these scripts themselves. You can run them too, from the
project's root, with the script's path inside the installed skill folder. For
the team profile, setup copies the lint, the validator and the guard into
`tools/specs/` of the project, so the pipeline needs nothing installed.

Output follows one format: `path:line: SEVERITY CODE [element]: message`,
with `ERROR`, `WARN` or `INFO`. The tools inform; they never stop the work.
Every check exits 0 when it ran, whatever it found: the findings are its
output. With `--strict` it exits 1 when it found problems (for the lint and
the validators, an error or a warning), so a strict pipeline is a choice you
make on purpose, in a command you run. A file the check cannot read is the
finding `UNREADABLE`, under the same rule, and so is a link that cannot be
resolved in place of a specification file or folder: no command reads it as
missing, and setup writes nothing through it. Exit 2 means a usage error, 3 that
the script could not run (git unavailable, a conflict), 5 `OLD_FORMAT`.
`unrecorded_changes.py` exits 4 when no change record names the use case: there
is nothing to compare it with, which is not the same as being unable to run.
Being unable to run wins: without git, or with nothing committed, it exits 3
whether or not a record names the use case. A
script that acts or lists instead of checking exits 1 when it cannot do its
work: the overview writer refuses markers out of order, or an `id` or a
`goal` it cannot read (`FRONT_MATTER`); the reference check's `apply` refuses
or is interrupted; a lister or the dashboard cannot read a file. "The check
reports no error" in a skill means its output names no `ERROR`.

### Format codes

| Code | Meaning |
|---|---|
| `OLD_FORMAT` | Earlier formats detected; stop with exit 5 and use `up-migrating-spec-formats` |
| `FRONT_MATTER` | Missing or malformed front matter, unsupported YAML or a missing required key |
| `STALE_OVERVIEW` | The generated overview differs from the use case files; regenerate it |
| `STUB` | A stub whose `status` is past Draft |
| `EXAMPLES_FORM` | A rule needs a filled Examples table: a blank line before the Examples table, input columns then final `result`, and rows on both sides of each boundary |
| `GHERKIN_FORM` | A journey needs one gherkin block, one named Scenario, allowed steps and comments matching its `use_cases` list |
| `ENTITY_TYPE` | An attribute type is outside the closed business list |
| `REFERENCE_NO_RELATIONSHIP` | A Reference to ENTITY lacks a relationship in the diagram |
| `NEED_FORM` | A functional row lacks Role or Need, or a Statement follows no EARS pattern |
| `RECORD_FORM` | A change record lacks a required section or has an unknown outcome |
| `UNREADABLE` | A file cannot be read |

Retired codes: `NO_START_END`, `NO_SYSTEM`, `LABEL_FORM`, `ACTOR_UNCONNECTED`,
`USE_CASE_UNCONNECTED`, `SPEC_NOT_IN_DIAGRAM`, `NAME_MISMATCH`, `SPEC_PENDING`,
`FK_NO_RELATIONSHIP`, `STORY_FORM`. The overview is generated from existing
files; references use business types, and functional rows use Role and Need.

### Specification checks

| Script (skill) | What it checks | Example |
|---|---|---|
| `validate_use_case.py` (`up-5`, `up-6`) | One specification's structure and closed loop: every flow ends, every ending is covered | `validate_use_case.py --strict docs/use_cases/UC-001-book-repair.md` |
| `spec_lint.py` (`up-6`, `up-bootstrapping-spec-driven-projects`) | The whole set across files: dangling or duplicate identifiers, unrealized requirements, front matter errors and stale overview content, copied rules, mechanism and weak words; the traceability matrix | `spec_lint.py --strict`, `spec_lint.py --trace` |
| `unrecorded_changes.py` (`up-6`, `up-7`) | Flows and rules the specification changed since the change began that the change record does not name | `unrecorded_changes.py UC-012` |
| `check_requirements.py` (`up-2`) | The catalog row by row | `check_requirements.py --strict` |
| `check_entity_model.py` (`up-3`) | Diagram and sections agree; the vocabulary is used | `check_entity_model.py` |
| `use_case_map.py` (`up-4`) | Generate the actor-goal table and Mermaid diagram inside the overview markers; preserve the surrounding text | `use_case_map.py --docs DIR` (`--check` checks freshness) |
| `check_use_case_map.py` (`up-4`) | Use case front matter, stubs, overview freshness and catalog coverage | `check_use_case_map.py` |
| `check_test_case.py` (`up-writing-journey-test-cases`) | Journey test case documents | `check_test_case.py docs/test_cases/TC-001-*.md` |
| `bpmn_paths.py` (`up-writing-journey-test-cases`) | The start-to-end paths of a BPMN process | `bpmn_paths.py docs/processes/repair.bpmn` |

The lint reports at `INFO`, as `REQ_IMPLEMENTED_UNLINKED`, a requirement of any
kind whose Status is `Implemented` and that no use case links (a use case that
is Obsolete does not count): the claim has nothing behind it to read. A
functional requirement that `FR_UNREALIZED` already reports gets no second
finding. Like every `INFO`, it changes no exit code, with `--strict` or
without it, and the baseline does not take it. The reviewer's lint codes
reference lists every code.

### Change and implementation checks

| Script (skill) | What it checks | Example |
|---|---|---|
| `impact.py` (triage) | Everything that refers to an identifier or a business noun | `impact.py UC-004 "work order"` |
| `uc_change_list.py` (`up-7`) | What changed in one specification since it was last implemented | `uc_change_list.py UC-012` |
| `scope_audit.py` (`up-7`) | Every changed file belongs to the use case | `scope_audit.py UC-012 --base <start>` |
| `finish_change.py` (`up-7`) | The implementer's gate (below) | `finish_change.py UC-012 --base <start>` |
| `coverage_units.py` (`up-8`) | The coverage units of a use case and the tests that carry each label | `coverage_units.py UC-006 --tests tests` |
| `guard_check.py` (`up-7`, `up-8`) | Breaks one element on purpose, runs its test, restores the file and logs what happened: caught, crashed, not caught or unclear | see below |
| `spec_first_guard.py` (`up-bootstrapping-spec-driven-projects`) | A change set that changes behavior code with no specification behind it, no `No behavior change:` line and no `Fixes:` note | `spec_first_guard.py --base <integration-branch>` |
| `relink.py` (`up-bootstrapping-spec-driven-projects`, recovery) | Moves files and every reference to them: `plan` lists links, imports, settings paths and agent instructions that name them, `apply` moves and rewrites, `verify` finds what is left; `--keep FILE` leaves a record of the moves as written | `relink.py plan --move specs docs` |

The scope audit groups root A-files as `tracking`; guideline files still need
attribution. A deleted file belongs to the change when its text at the base
carries the use case id, or the change record names its exact repository-relative
path in backticks or as a Markdown link target. The audit finds the newest record
for the use case by default; `--record PATH` selects one explicitly. Its default
`--base HEAD` compares against the HEAD commit, or lists uncommitted files when
there is no commit yet; pass another base to include commits. Paths with spaces
can appear in backticks, angle-bracket link targets or percent-encoded link
targets. Bytecode cache folders (`__pycache__`) never belong to a change.

**The finish check** (`finish_change.py`) is the gate before an
implementation is reported. It checks:

- **Scope**: files outside the change warn as "changed, not part of this
  change". A file changed in this session whose path names an uncovered use
  case is a problem at the stop: undo it or name that use case in the change
  record. Earlier unpushed work and every scope finding at push only warn.
  Root A-files count as tracking. Deleted files belong when they carried an
  id at the base or the record names their exact path.
- **Markers**: every rule in the change has its marker in the code; a marker on
  a function nothing calls is warned about. When the marker is only in files
  read as tests by a `spec` or `specs` folder, the problem names them (JSON:
  `markers.in_test_folders`). Marker checks run only for changes
  with rules; callers count even in files without an id, including untracked files.
- **Tests named**: every flow and rule in the change is named by a test.
- **Guard check**: every rule in the change has a logged break that a test
  caught: the newest row of the rule counts, and only when it is `caught`. A
  row is stale when the rule's text, its Examples table or the enforcing file
  changed since it was logged, or when it is in the format before 1.3.0
  (no fingerprints); the report then says
  `the guard check of UC-012 BR-001 (...) is stale: run scripts/guard_check.py again`. A guard-check log it
  cannot read is the finding `UNREADABLE`.
- **Decisions**: every owner decision names an element that exists.
- **Sources**: every flow and rule in the change rests on a source.
- **Record**: nothing changed in the specification outside the change record.
- **Pinning**: every row read only from the code is pinned by a test that
  existed before the code changed, and the pin of a row the change alters
  changed with it.

Run it with `--base` set to the branch or commit the change started from
(`HEAD` while nothing is committed). It ends with "ready to report" or with a
numbered list of problems. With the A-files, it also prints
`Tracking: warning: …` when a use case's Status changed and neither
`ACTIVE.md` nor `ABILITIES.md` did (`ACTIVE.md` alone in a project without
`ABILITIES.md`); the warning never changes the result.

`--claim` checks the whole use case unless a changed, present change record
names it in its metadata, differences or filename. Every such record must
pass. A committed Status raise therefore still needs evidence even if the
specification has no further changes.

`status_claims.py --since REF [--base REF]` checks raises to Implemented or
above and validates changed use cases. `--since` selects claims and changed
use cases; `--base` selects the evidence view and defaults to the hook base
resolution. Without `--since`, the resolved base selects both. Tested and
Done also need a test naming every active flow and rule in the whole use
case. Renames alone, downward moves and Obsolete are not claims. Validation
errors fail at Reviewed or above; Draft findings warn. Scope findings warn
in this range check. `--docs`, `--code`, `--tests` and `--format text|json`
work as in the finish check. Exit codes are 0 when it ran, whatever it found
(with `--strict`, 1 on problems), 2 usage or unknown revision, and 5 old
formats.

`--code` and `--tests` limit their sections to those folders, including folders
in another repository or a submodule. Test names and test folders are recognized
relative to the folder searched: with `--tests selected/tests`, `test_capacity.py`
counts as a test and `capacity.py` does not. `spec` and `specs` count as test
folders except under `src`, `app` or `lib`, where a feature about
specifications keeps its code. The spec-first guard names the changed files
read as tests only by a `spec` or `specs` folder, so a wrong reading shows. Text files marked `-diff` or `binary`
in git attributes still count; files containing NUL bytes or invalid UTF-8 do not.

**The guard check** (`guard_check.py`) turns "this test guards that rule" from
a claim into a recorded fact:

```bash
python3 guard_check.py "UC-012 BR-001" \
  --file src/booking.py \
  --find "if count >= DAILY_CAPACITY:" \
  --replace "if count > DAILY_CAPACITY:" \
  --test "pytest -q tests/test_booking.py"
```

It runs the test once (it must pass), applies the break (the text must occur
exactly once), runs the test again, always restores the file and verifies it
byte for byte, and appends a row to `docs/reviews/guard-checks.md`. It
checks any element of a use case, in the finish check's names: `UC-012 BR-001`,
`UC-012 A2`, `UC-012 Step 3`, `UC-012 Pre-1`, `UC-012 Post-S-1`,
`UC-012 Post-F-2`.

It reads the test's output, both streams together, and gives one of four
verdicts about the break:

| Verdict | Meaning |
|---|---|
| `caught` | A test whose name holds both the use case and the element failed on an assertion |
| `crashed` | The element's test stopped on an error rather than a failed assertion: a syntax error, a failed import, any exception the test did not expect (a bare `Error`, `StopIteration`, the project's own), a build that did not compile, or the runner marking the test as an error |
| `not caught` | The test still passed: it does not guard the element |
| `unclear` | The test failed, but the output does not say that the element's test failed on an assertion |

Beside them, `invalid` says the check proved nothing: the test failed before
the break, or ran past the time limit (`--timeout`, 600 seconds by default).

Only lines new since the run before the break count, and the element's own
report decides first: from the line that reports its test to the next test's
report. An error there, or the runner's error mark on the test, gives
`crashed`; otherwise `caught`, whatever another test printed. An error printed
apart from every test's report (before the first one, or in a section of the
whole run, as with pytest's `--tb=line`) gives `unclear` instead, because the
output does not say whether the element's test crashed. Only when no line
reports the element's test does an error anywhere give `crashed`. The
explanation of a failed assertion is not an error: a pytest diff line, a
field labeled `Error:` and padded to a column (Go's testify), or a line such
as `Expected: 8`; an exception whose name does not end in `Error` or
`Exception` counts only on the line right after a traceback's frame. For
`crashed` and `unclear` the check prints the new lines of the output (the
first 40, and how many there were). Its JSON report holds `element` (and
`unit`, the same value under its earlier name), `file`, `verdict`,
`evidence`, `failed_test`, `log` and `restored`, and for `crashed` and
`unclear` the lines as `output` and their count as `output_lines`.

Element numbers restart in every use case, so a failed test counts only when
the line reporting it holds both the use case and the element, in a common
spelling (`test_uc012_br001_...`, `UC012Test.test_br001_...`,
`testUc012Br001`) or as a displayed name (`UC-012 BR-001 refuses a full
day`). A failing test of another use case's BR-001 does not count. For a
runner that prints no test names, `--expect TEXT` gives the text that shows
the element's test failed; it counts when that text appears more often after
the break than before it, and its part of the output is read as the element's
report is.

The signs the check reads follow the documented output of common runners,
named in the script as examples (unittest, pytest, Go, .NET, Jest, Vitest,
TAP, Mocha, RSpec, PHPUnit, JUnit with Maven or Gradle), and one shape any
runner may print: a failure word in parentheses or brackets at the start of
a line (`(fail) name`, `[FAIL] name`, as Bun prints the first). The package's tests
run only unittest, pytest and stand-in runners; Go's output with testify was
captured from a real run by hand, and the others were not run.
Known limits: the check sees only what the runner prints, so a mode that
prints a failed test's name without its error reads a crash as `caught`.
With pytest 9.1, `--tb=no` and `--tb=line` name the error only in the
summary line, cut to the terminal's width; the check runs the test with a
terminal 500 columns wide. A syntax error there, or any exception
(`StopIteration`, the project's own), gives `crashed`, under a parametrized
test's id too, spaces and brackets included (`test_br001_limit[a full day]`,
`test_br001_limit[[8]]`); a test name too long even for that leaves no room,
and a crash reads as `caught` (`unclear` under `--tb=line`). A parameter id
that itself holds `] - ` ends the id early: a syntax error reads as `caught`
under `--tb=no` and `unclear` under `--tb=line`, and an exception whose name
ends neither in `Error` nor in `Exception` reads as `caught` under both; an
id holding `] - File "` reads every failure as `crashed`, an assertion too.
`--tb=no -rN` gives `unclear`. The default `--tb=auto` shows every error.
The check runs the tests with `COLUMNS=500`, so a project test that depends
on the terminal's width can fail before the break and give `invalid`. An
assertion message holding the words "syntax error" reads as `crashed` in
every runner and mode, since the check reads those words as a crash on any
line.
A query that throws its own error when an element is missing (for example,
Testing Library's `getByText` under Vitest or Jest) makes a caught break read
as `crashed`; write that test with a query that does not throw and an
`expect` assertion (in the example, `expect(queryByText(…)).toBeInTheDocument()`).
Mocha prints a test's group and title on separate lines, so it
needs `--expect`.

Each row keeps the element, the file, the find and replace texts whole, a
fingerprint of the element's text (with its Examples table for a rule), a
fingerprint of the file, the test command, the failed test and the verdict. A
cell keeps every character: `\\` is a backslash, `\|` a pipe, `\n` a line
break, `\r` a carriage return, `\t` a tab, `\s` a space at either end, and
`\uXXXX` any other control character, line separator or blank at either end.
A log of an earlier release keeps its table, and new rows go into a new table
below it.

The use case is found in any folder spelling the scripts accept (`use_cases`,
`use-cases`, `usecases`); the change list, the unrecorded-changes check, the
finish check and the guard check all read the same file. A specification,
enforcing file or guard-check log the guard check cannot read is the finding
`UNREADABLE`, and the check does not run; a log that becomes unreadable
during the run is the same finding, with the verdict in the message and no
row written. The script exits 0 whatever the verdict or finding;
`--strict` exits 1 unless it is `caught`. It exits 1 when it cannot write the
log, with the verdict in the message and the file restored, and 2 on a usage
error or a failed restore. The verdict is information for you: nothing checks
it for cheating, and a test weakened while the element and its file stay the
same is not detected.

### Audit and recovery checks

| Script (skill) | What it does | Example |
|---|---|---|
| `coverage_matrix.py` (`up-9`) | Starts a use case's coverage matrix from identifiers in code and tests | `coverage_matrix.py UC-001` |
| `spec_dashboard.py` (`up-9`) | The spec dashboard, optionally with a JUnit test report | `spec_dashboard.py --junit report.xml` |
| `check_recovery_ledger.py` (recovery) | The recovery records against the specifications and the code | `check_recovery_ledger.py --strict` |
| `sample_claims.py` (recovery) | A random sample of recovered claims for a second reader | `sample_claims.py --count 10` |
| `spec_core_metrics.py` (splitting) | Size of the specification set and where it could be cut | `spec_core_metrics.py` |
| `workflow_state.py` (`up-0`) | The repository's state and the first step that applies, the alignment count of a recovery and its hints | `workflow_state.py` |
| `spec_data.py` (`up-0`) | Prints the whole model of the project as JSON for a program; judges nothing and decides no step (see The model as data, below) | `spec_data.py` |
| `scaffold_docs.py` (`up-bootstrapping-spec-driven-projects`) | The setup or installed-copy update plan; writes only with `--apply`, with explicit decisions for customized scripts | `python3 "<skill-folder>/scripts/scaffold_docs.py" --profile solo` |

The overview is generated from the use case files' front matter. Rerun
`use_case_map.py --docs DIR` after changing an identifier, name, actor or goal.
Status stays in the use case file and dashboard. The lint reports
`STALE_OVERVIEW` when the generated block differs. A Draft stub whose body is
`Not written yet.` routes to `WRITE`; a stub past Draft reports `STUB`. When
a format finding blocks (`use_case_map.py` refuses the file's `id` or `goal`),
the router reports `FIX_FORMAT` naming the files and codes, and the skill that
writes the artifact, before any Status-based step. Every other format finding
goes on one "to clean (not blocking)" line and is never the next step.

Use case checks stop with exit 5 and `OLD_FORMAT` on earlier specification
formats. The router instead reports `MIGRATE` with `up-migrating-spec-formats`.
Check the source before honoring a carried-over blocker and say so. A blocker names what it stops and a dated owner message, specification identifier or path, or failing check by name; the A-files check advises `BLOCKER_WITHOUT_SOURCE` when no source is named (exit 0 normally, 1 with `--strict`). Implemented and tested work has acceptance outstanding, not blocked; unrelated work continues. Fix a validator or lint finding, or report it as a tool defect; ask the owner only if it raises a behavior question.

The checks and the router look at every file for the earlier formats, also
past one that cannot be read, and the listing of each folder is part of that
pass: the earlier formats win over an unreadable file or a folder that cannot
be listed, which the checks name beside them as `UNREADABLE`. The vision, the
overview and the recovery ledger and change log are read whole in the same
pass, so one that is denied or not UTF-8 is named as `UNREADABLE` too, never
left to end a command in a decoding error. The router
names each one under its `MIGRATE` step, as an `unreadable:` line with the
file and the error (in its JSON, `migration.unreadable`: `file` and `error`
for each, an empty list when there is none), and exits 0. When the router
cannot read a specification file and there is no earlier format, it names
the file and exits 2 instead of naming a step, so it never asks for a file to
be written that is there as a broken link.

A link that cannot be resolved (its target is missing, or it leads back to
itself) is never an absent file: in place of the specification folder, an
artifact, a `change-records` folder anywhere under the specification folder,
or a recovery record (`ledger.md`, `change-log.md`, `suspects.md`,
`baseline-review.md`), every command reports it as `UNREADABLE`, and the
error says it is a link and where it points. So does a specification folder
behind such a link, or behind a folder that cannot be searched, at any depth
(`docs/nested/specs` when `docs` is a broken link): every part of the path is
looked at before a missing part is read as absence, with or without a mark of
the project's root, the error names the link or the folder that stops the
reader, and the router never suggests setup for it. A folder the method owns
that cannot be listed, or that can be listed and not searched (read without
execute permission, so nothing in it can be reached), is `UNREADABLE` too:
the specification folder, one of its canonical folders (`use_cases`,
`test_cases`, `processes`, `recovery`, `reviews`, in any of their spellings)
or a `change-records` folder at any depth. A file a command
is given that is such a link (a journey, a catalog, a change record with
`--record`, a ledger with `--ledger`) is reported the same way, before any
test of its existence, any git call or any resolution of the path; a code or
test folder, or the file the guard check edits, is a usage error (exit 2)
that names it as a link. Setup writes nothing through such a link.

Any other folder under the specification folder that the search for change
records cannot look into, such as a tool's cache, `node_modules` or a build
that cannot be listed or reached, fails no command, with `--strict` too; so
does a link there whose target the search is denied. The method writes no
change record there, and the search goes on around it; a `change-records`
folder directly inside a folder that can be searched but not listed is still
found by its name and read, and one the search can see and not reach is
`UNREADABLE`. Since a change record under such a folder, if any, is not read,
the folder is named all the same: every command writes `note: PATH was not
searched for change records: ERROR` on standard error, the router and the
model in either format, and the router's and the model's JSON also list it
under `not_searched` (`folder` and `error` for each, an empty list when there
is none). A check that needs a change record it cannot see reports it
missing, as it would without the folder.

Every command writes its output whatever the encoding of the terminal or the
pipe. A character the output cannot write, as on a legacy Windows code page
or under a C (POSIX) locale, appears as its escape (`\u2192` for an arrow)
instead of ending the command in an encoding error; under a C locale a file
name that is not text in the locale's encoding is still written as its bytes.
JSON then comes as plain ASCII (see The model as data). What git prints is
read as UTF-8 whatever the locale.

Session start and the stop show a migration notice with result 1 (warn).
After-edit feedback stays local; turn start always exits 0, silently on failure.
Setup creates `use_cases.md`; `--skip overview` skips it, and `--skip diagram`
is accepted as an alias with a note. Installed checks and hooks include the
overview generator beside the model.

### The model as data

`spec_data.py`, in `up-0-navigating-spec-driven-work`, prints everything the
scripts read from a project as one JSON document, for a program such as a
dashboard: every connection the specifications hold, not only the broken
ones. It reads the files as data and writes nothing, not even a bytecode
cache beside an installed copy. It decides no step and judges nothing: the
checks say what is wrong, the state report says what comes next.

```bash
python3 "<skill-folder>/scripts/spec_data.py"
```

Setup installs a copy into the project's `tools/specs/` with either set of
installed scripts (the team profile's checks or the agent hooks), and
`scaffold_docs.py --update` adds it where it is missing and keeps it current,
as it does the others; the migration does the same. A program can then run
the project's own copy, `python3 tools/specs/spec_data.py`, from the
project's root. No check or hook runs it, and the hook gate runs whether it is
there or not.

`--docs` defaults to the folder the rules block records, else `docs`;
`--format json` is accepted and is the only format. Exit 0 when the model was
printed; 1 when a file or a folder could not be read (the rest is printed and
it is listed under `unreadable`; every A-file and guideline file that exists
is read for this, so one that cannot be decoded is listed rather than read as
empty); 2 on a usage error; 3 when it could not run because the `spec_model.py`
beside it is of another release, as when an older copy was kept in
`tools/specs/` (the message names both releases: run `scaffold_docs.py
--update`); 5 with `OLD_FORMAT` on standard error and nothing printed when the
project still uses the earlier formats. The earlier formats win over a file
that cannot be read: every other file is still checked for them, the exit is
5, and standard error names the unreadable file as `UNREADABLE` beside the
`OLD_FORMAT` lines.

How to read it:

- The JSON is valid whatever the encoding of standard output. A Unicode
  output (UTF-8, as on most systems) gets every character as written; any
  other, such as a legacy Windows code page, gets plain ASCII with JSON's
  `\u` escapes, which a program that decodes the output as UTF-8 reads the
  same. Every command's `--format json` below follows the same rule, except
  `scope_audit.py`, which prints plain ASCII on every output, as it always
  has.
- Paths are relative to the project's root, with forward slashes; only
  `root` and the `target` of an `outside_link` are absolute, and a ledger's
  evidence path says in its `place` when it is not in the project. An
  absolute evidence path that leads into the project on the file system,
  through a link or another spelling of a folder on the way (`/var` for
  `/private/var` on macOS), is in the project. Lines count from 1.
- A file or folder read through a link whose real target is outside the
  project's root is read like any other, and says so, so that a program can
  tell the project's own files from those it borrows through a link: its
  `outside_link` is `{"link": ..., "target": ...}`, the link that leaves
  the project (relative to the root) and the real path of the file or folder
  itself (absolute, with forward slashes). A linked file and a file inside a
  linked folder carry the same shape; only `link` tells them apart. Every
  file or folder the model reads carries the key, `null` when nothing leads
  it out of the project, a link that stays inside included. Whether a target
  is inside the project is decided by the identity of the folders on the file
  system, so a link written with another capitalisation of the project's
  folder, on a file system blind to case, stays inside. A Windows junction
  counts as a link, also on Python 3.9 to 3.11, which tell it from what the
  system reports for it. It changes no exit code, and such a file is not
  listed under `unreadable`.
- Every element carries `file`, `line` and `fingerprint`: the first 16 hex
  digits of a SHA-256. A file's fingerprint is of its bytes. A rule's, a
  flow's, a step's, a precondition's and a postcondition's is of the text the
  guard check fingerprints for that element, so it can be compared with the
  guard-check log. A table row's is of the row as written, and any other
  element's of its text, both with their white space made single spaces.
- A kind of file the project lacks keeps its key: `present` is `false`, its
  `file` or `folder` is `null` and its lists are empty. A file that exists
  and holds nothing, or a folder that exists and is empty, has
  `present: true` and empty lists. A folder that cannot be listed, or that
  can be listed and not searched, is present, with empty lists, and named
  under `unreadable`. So is a link that cannot be
  resolved (its target is missing, or it leads back to itself) in place of a
  file or a folder, the specification folder included: it is not an absent
  one, and `unreadable` gives the reason, naming it as a link. A
  specification folder behind such a link, or behind a folder that cannot be
  searched, at any depth, is present too (`docs_present: true`) and named
  under `unreadable`, its error naming what stops the reader. A
  `change-records` link that cannot be resolved is one of the `folders`, and a
  `change-records` folder at any depth that cannot be listed or reached is
  named under `unreadable`. Each file or folder is listed under `unreadable`
  once.
- Any other folder under the specification folder that the search for change
  records cannot look into (a tool's cache, `node_modules`, a build), or a
  link there whose target it is denied, is not `unreadable` and changes no
  exit code: it is named under `not_searched`, and in a note on standard
  error, since a change record under it, if any, is not read. A
  `change-records` folder directly inside one that can be searched but not
  listed is still read.
- Each folder is read once. A folder link inside the specification folder,
  an alias of a `change-records` folder or a loop back to `docs/`, repeats no
  change record; a folder reached only through a link is read under the
  link's path. On a file system blind to case, a folder spelled
  `Change-Records` is found under the spelling `change-records`, as before.
- `schema` changes only when a key changes its meaning or goes away. A new key
  keeps the number.

| Key | Holds |
|---|---|
| `schema` | The shape of the output: `1` |
| `upspec_version` | The release of the scripts that printed it |
| `root`, `docs`, `docs_present`, `docs_outside_link` | The project's root (absolute), the specification folder, whether it exists (`true` also when it cannot be reached, and it is then under `unreadable`), and its `outside_link` |
| `files` | For `vision`, `requirements`, `entity_model`, `overview`, `use_cases`, `journeys`, `processes`, `recovery` and `reviews`: `present`, `path` and `outside_link` |
| `rules_block` | `present`, `file` (`AGENTS.md` or `CLAUDE.md`), `outside_link`, `profile`, `skipped` (which of requirements, entity model, overview and diagram the Skipped line names), `skipped_text` (that line, lower case), `specs_folder`, `integration_branch` |
| `use_cases` | `present`, `folder`, `outside_link`, `items`: one per use case file |
| `requirements` | `present`, `file`, `outside_link`, `fingerprint`, `items`: one per catalog row |
| `entities` | `present`, `file`, `outside_link`, `fingerprint`, `diagram` (`present`, and `entities` with `name` and `line`), `items`, `relations` (`from`, `to`, `label`), `duplicates` (`name`, `line` of a second section for one entity) |
| `journeys` | `present`, `folder`, `outside_link`, `items`: one per journey test case |
| `change_records` | `present`, `folders` (each `change-records` folder), `folder_outside_links` (each of those folders with its `outside_link`), `items` |
| `recovery` | `present`, `folder`, `outside_link`, `ledger` (`present`, `file`, `outside_link`, `fingerprint`, `rows`), `change_log` (`present`, `file`, `outside_link`, `fingerprint`, `entries`) |
| `reviews` | `present`, `folder`, `outside_link`, `items`: one per review report (`<scope>-review.md`, or `<scope>-review-<n>.md` of an earlier release) |
| `tracking` | `present` (`ACTIVE.md` with its hot-zone marker), `files` (`AGENTS.md`, `CLAUDE.md` and the four A-files, each with `present`, `readable`, `outside_link` and `fingerprint`), and what the A-files say (below) |
| `unreadable` | Each file that could not be read: `file`, `error` |
| `not_searched` | Each folder under the specification folder that the search for change records could not look into and that the method does not own: `folder`, `error`; an empty list when there is none |

A use case item:

| Key | Holds |
|---|---|
| `id`, `name`, `status`, `stub` | Its identifier (`null` when it cannot be read), name, Status and whether it is a stub |
| `file`, `outside_link`, `fingerprint`, `line_count` | Its file, its `outside_link`, the fingerprint of the file and its number of lines |
| `title` | The `# ` heading: `text`, `line`; `null` without one |
| `front_matter` | `values` (each key with its `value` and `line`), `problems` (`line`, `message`), `refused` (each key refused as a value on several lines, with the line) |
| `goal`, `trigger` | `text` with its place; `null` when the key is absent |
| `actors` | `name` and `role` (`primary` or `secondary`) |
| `requirements` | `id` of each requirement it links |
| `sections`, `duplicate_sections` | Each known section with its `title` as written and its `line`; a repeated one with `name`, `title`, `line` |
| `preconditions`, `steps` | `name` (`Pre-1`, `Step 3`), `number`, `text` |
| `flows` | `label`, `name`, `trigger` (`text`, `steps`: the main steps it names, `flow_steps`: `flow` and `step` for a flow that branches from another, `any_time`), `steps` (named `A1 step 2`), `ending` (`kind` `continues` or `ends`, `step`, `line`; `null` without one), `retired`, `moved_to` (what a retired flow says it moved to, else `null`) |
| `flows_placeholder` | The italic line that says no step can fail: `text`, `line`; else `null` |
| `postconditions` | The endings: `success` and `failure`, each item with `name` (`Post-S-1`, `Post-F-1`), `number`, `text` |
| `rules` | `id`, `name`, `text` (its body without the table), `examples` (`line`, `header`, `rows` with `line` and `cells`; `null` without a table), `retired`, `moved_to` |
| `citations` | A rule a step or a flow cites: `use_case` (`null` for this one), `rule`, `target` (`UC-001 BR-002`), `where` (`step 4` or the flow's label) |
| `references` | A citation into another bounded context: `context`, `id`, `rule`, `where` (a step, a flow or `Requirements`) |

The other items:

| Item | Keys |
|---|---|
| A requirement | `id`, `kind` (`FR`, `NFR`, `C`), `title` (its Title, or its need without the reason, as the reports name it), `text`, `role`, `need`, `statement`, `status`, `priority`, `columns` (every cell by its column) |
| An entity | `name`, `description`, `avoid`, `attributes` (`name`, `meaning`, `type`, `rules`, `reference`: the entity a `Reference to` type names, `columns`), `lifecycle` (`text`, `line`), `constraints` (`text`, `line`) |
| A journey | `id`, `file`, `outside_link`, `fingerprint`, `title`, `front_matter`, `goal`, `priority`, `status`, `process`, `use_cases`, `roles`, `preconditions` and `postconditions` (`text`, `line`), `scenarios` (`name`, `line`, `steps`, `problems`), `problems`. A step has `keyword`, `text`, `use_cases` (the ids its comment names) and `flows` (`use_case`, `flow`): a flow the comment names right after an id it annotates, as in `# UC-001 A15`. The flow is kept as data; no check reads it |
| A change record | `file`, `outside_link`, `fingerprint`, `front_matter`, `outcome`, `element`, `use_cases`, `decided_by`, `sections` (each heading with its line), `differences` (the rows of the table with Element and Today columns: `line`, `element`, `use_cases`, `units`, `columns`) |
| A ledger row | `element`, `use_case`, `part` (the flow or rule, or an entity's aspect such as `required`), `entity`, `state` (lower case, as written), `note`, `evidence` (each location: `text` as written; `path`, relative to the project's root with forward slashes, a backslash read as a separator; `place`: `project`, `outside` when the path leaves the project, or `other_drive` when it names a drive or a share the project is not on, `path` then keeping its own form with forward slashes; `line`; `last_line` for a range; a location without a line has `line` `null`) |
| A change log entry | `number`, `kind`, `use_cases`, `evidence`, `decision`, `decided_by` (`null` without the column), `state` (`later`, `in_change`, `aligned`, `dropped`, `undecided`, `settled`), `detail` (the reason of a dropped entry), `paths` (the record or the audit reports), `ahead` |
| A review report | `scope` (`UC-004`, `TC-001`, `all`), `scope_kind` (`use_case`, `journey`, `all`, `other`), `number` (n of `-review-<n>.md`, else `null`), `title`, `title_line`, `verdicts` (each `Ready for <Status>: yes` or `no`: `status`, `ready`, `line`, read in the Verdict section when there is one), `verdict_line`, `declined` (each bullet of the Declined section but "None": `line`, `text`, `element`), `declined_line` (`null` when the report has no Declined section); and its `file`, `outside_link` and `fingerprint` |

What the A-files say, under `tracking`: `current_work`, `blocked_by`,
`waiting_on_owner` and `next_step` (the fields of `ACTIVE.md`, `""` when
empty); `next_new_work` (the text under its `## Next new work`, `""` when
empty or a placeholder); `debt`; `abilities` (each with `name`, `status`,
`specs`, `links`, and `known_limits` and `evidence`: the text of the entry's
Known limits and Evidence lines with any indented lines below them, `null`
without the line); `abilities_present`; `next_up`; `items` (each AHEAD item's
abilities); `item_titles`; `ahead_items` (each AHEAD item with `title`, `kind`,
`state`, `abilities`, `belongs_to`: the entry's Belongs to line, `section`:
the heading its row sits under, such as Index or History, and `line`); and
`active_home`, `abilities_home`, `ahead_home` (the file an A-file names as
its home, else `null`). Without the A-files every one of these is empty.

**The state reader's JSON** (`workflow_state.py --format json`) keeps every
key it had and adds:

- `coded_mismatches` beside `mismatches`, and in `tracking` both
  `coded_mismatches` and `coded_warnings`, and in `alignment`
  `coded_warnings`: the same items in the same order, each as `code` and
  `message`, the sentence unchanged. The codes are `UC_NO_ID`,
  `UC_ID_REUSED` and `UC_STATUS_INVALID` (a use case that needs repair);
  `IN_PROGRESS_NOT_CURRENT` (built and not named by the current work);
  `SPECS_UNKNOWN_USE_CASE`, `DONE_ABILITY_NOT_DONE`,
  `PLANNED_ABILITY_BUILT`, `IN_PROGRESS_ABILITY_DONE` and
  `DONE_ABILITY_OPEN_ENTRY` (an ability and its use cases disagree);
  `LATER_WITHOUT_AHEAD` and `AHEAD_ITEM_UNKNOWN` (a change log entry and
  AHEAD disagree); and, for an aligned entry that stays
  open, the closure check's code: `AUDIT_REPORT_MISSING`,
  `AUDIT_REPORT_INVALID`, `AUDIT_REPORT_STALE` or `ALIGNED_INCOMPLETE`.
- `alignment.dropped_entries`: each dropped change log entry, listed as the
  open ones are in `entries` (`number`, `state`, `use_cases`, `record`,
  `ahead`), with its `reason`.
- `migration.unreadable` (and the same in `next`) when the step is
  `MIGRATE`: each file or folder that could not be read beside the earlier
  formats, as `file` and `error`; an empty list when there is none.
- `tracking.abilities`: each ability with its `name`, `status` and the
  `use_cases` its Specs line names, which deliver it.
- `tracking.abilities_compared`: how many abilities had their status
  compared with their use cases: those `planned`, `in progress` or `done`
  whose Specs line names a use case that exists. `0` means nothing was
  compared, which is not the same as everything agreeing.

These keys leave the text report as it was. One warning is new in both: an
ability `in progress` whose use cases are all `Done` is warned with the other
ability-status mismatches (`IN_PROGRESS_ABILITY_DONE`): mark it `done`, or
name in its Specs line the use case still to build.

### Other commands as data

Several commands also answer as data and for the whole project in one call.
Each of these modes reads only and writes nothing; what each command printed
before is unchanged. Run from a project's `tools/specs/`, the model command,
the state reader, the lint and the unrecorded-changes command leave no
bytecode cache (`__pycache__`) beside the copies either.

**The dashboard** (`spec_dashboard.py --format json`, in `up-9`) gives the
evidence of its two tables. `progress` holds `functional_requirements`,
`use_cases` and `full_test_coverage`, each with `total`, `complete`,
`in_progress`, `not_started` (numbers, `null` where the table prints `—`) and
`coverage` (the cell as printed: `25%`, `—`, `not searched`), and
`regression` with `tests`, `passed`, `failed` (`null` without a report) and
`result` (`Stable`, `Regressed` or `unknown`). `use_cases` holds one row per
use case that is not Obsolete: `id`, `name`, `linked_fr` (a list), `status`,
and the cells `code`, `unit`, `e2e`, `regression` and `integrity`, each the
word the table prints (`yes`, `partial`, `planned`, `no`, `not searched`,
`unknown`; `Strong`, `Partial`, `Weak`); `units` (the labels a test named,
`found`, and the ones none did, `missing`; `null` when no tests folder was
given); and `journeys` (the journey test cases that include it). `rules` gives
the lines of "How the cells are computed", and `searched` the folders and the
report the command was given.

**Tests in several folders.** `spec_dashboard.py`, `coverage_matrix.py` and
`coverage_units.py` take `--tests` once for each folder that holds tests,
such as `--tests py/tests --tests web/tests`. A file two of the folders hold
counts once, under the first folder's spelling: also when one folder is given
twice, under two spellings on a file system blind to case or through a link.

**Every use case at once.** `coverage_matrix.py --all` and
`coverage_units.py --all` give, in one call, what a call naming each use case
gives, for every use case that is not Obsolete, in identifier order. The text
or Markdown is each use case's in turn; the JSON holds them under
`use_cases`, each item exactly the object a call naming it prints. Naming a
use case together with `--all`, or neither, is a usage error (exit 2).

**Impact, typed** (`impact.py --format json`, in triage). Each term keeps
`term`, `upward`, `sideways` and `downward` with their sentences, and adds
`term_kind` (`requirement`, `rule`, `use_case`, `journey`, `noun`) and, beside
each group, the same items typed, one for one and in the same order:
`upward_items`, `sideways_items`, `downward_items`. A typed item holds:

| Key | Holds |
|---|---|
| `text` | The sentence the group prints, unchanged |
| `kind` | `catalog_row` (the term's own catalog row), `rule` (the rule's definition in its use case), `entity`, `attribute`, `missing` (nothing was found), `links` (a use case links a requirement), `cites` (a specification cites a rule), `includes` (a journey includes a use case), `marks` (a code or test file carries the identifier), `mentions` (a specification line names the noun) |
| `from` | The end that refers: a use case, with the flow or rule when the line sits in one (`UC-004 A1`, `UC-004 BR-001`); a journey; a requirement (a catalog row that names a noun); a code location (`path:line`); or the term itself |
| `to` | The end referred to: `FR-001`, `UC-002`, `UC-002 BR-001`, `WORK_ORDER`, `WORK_ORDER.status`; `null` for `missing` |
| `basis` | What the connection rests on: `catalog`, `specification`, `entity_model`, `requirements_line`, `citation` (a rule cited by identifier in a step or a flow), `journey` (a journey's `use_cases` list), `marker` (an identifier in a code or test file, a claim to confirm by reading), `text` (a line's text matches) |
| `file`, `line` | Where it was found, or `null` |

**Unrecorded changes for every use case** (`unrecorded_changes.py --all`, in
`up-6` and `up-7`). One call answers for every use case with an identifier, in
identifier order. Each entry has `use_case`, `state` and `reason` (why it was
not compared, else `null`), and what a call naming the use case reports
(`record`, `since`, `changed`, `recorded`, `unrecorded`; `null` or empty when
it was not compared). The state is `compared`, `no_record` (no change record
names it, the usual case for a use case nobody is changing), `cannot_tell` (a
new use case, nothing committed) or `unreadable`. A use case file that cannot
be read is an `unreadable` entry under the identifier its file name carries,
its reason naming the file, and every other use case is still answered; each
file that cannot be read is also the finding `UNREADABLE` on standard error.
The text gives one line per
use case and a `Result:` line; the JSON holds the entries under `use_cases`.
It exits 0 when it ran, 1 with `--strict` when a change is not in its record
or a file cannot be read, 2 on a usage error (`--record` names one use case's
record and does not go with `--all`), and 3 outside a git repository. A
specification folder that is a link that cannot be resolved is the finding
`UNREADABLE` before git is asked, with nothing on standard output.

### Agent hooks (optional)

Setup offers four moments through one gate, `tools/specs/hook_gate.py`:

| Moment | What runs |
|---|---|
| Session starts or resumes | A Status snapshot, specification state, next step and open-work list |
| After a write or edit | The validator on the edited use case specifications, as information |
| Before the agent reads a prompt | The open-work list only when it changed; always exits 0 |
| Before the agent stops | Owner decisions asked once; routine notes handed to the agent once |

No hook blocks, refuses or keeps the agent working, except to deliver one
message of decisions and notes at the end of a turn.

The session-start context opens with one light note to the agent, and to no
one else: before its first edit, say where things stand in four short lines
(Finished, Remaining, Blocked by, Next step), or in one short line when the
request already says exactly what to do. It never blocks, never asks you and
does not change the result; it is sent at session start only and counts inside
the sixty lines.

**Generate, review, approve.** Ask the setup skill for hooks. It runs
`python3 "<skill-folder>/scripts/scaffold_docs.py" --hooks --tool claude|codex|antigravity|kiro` from the plugin
with `--root DIR`, proposing scripts and wiring without writing. Without
`--tool`, `--hooks` copies scripts only. The agent reads the plan against
existing hooks, the tool version, the repository layout and conflicts,
adapts what does not fit, and explains why. You approve `--apply`; the tool's
own trust prompt still enables the hooks. The agent never enables its own
hooks or widens permissions for them.

| Labeled tool example | Generated project file | After-edit feedback | Stop keeps working | Warning channel |
|---|---|---|---|---|
| Claude Code | `.claude/settings.json` | Agent | Yes | Person |
| Codex CLI | `.codex/hooks.json` | Agent | Yes | Person |
| Antigravity CLI | `.agents/hooks.json` | Nobody: not wired, since on 1.4.4 nothing reached the agent (per the tool's 1.4.3 changelog the failure is only logged); open work arrives at session start | Yes | None documented |
| Kiro CLI V3 | `.kiro/hooks/upspec.json` | Person only, by Kiro's documentation; unproven in the TUI | Yes, once per prompt; prove the IDE runtime, since its docs differ | By Kiro's documentation, person at session start and after edits (unproven in the TUI); nobody at Stop |

All four generated examples were seen firing on 2026-10-21: Claude Code
2.1.307, Codex 0.159.2, Kiro CLI 2.33.1 and Antigravity CLI 1.4.4. The
reference records proof only after a firing on the named version. Kiro CLI
runs the hooks only on its V3 engine: set `kiro-cli settings
chat.agentEngine v3`, or start with `kiro-cli chat --v3`; setup changes no
Kiro setting. Antigravity's after-edit is not wired. Codex runs hooks in a login
shell (`$SHELL -lc`); startup output can corrupt the JSON, so check it in proof.
Kiro's after-edit warnings never reach the agent; its documentation says they
reach the person, which the proof did not see in `--no-interactive` mode and
which is unproven in the TUI. Its stop cannot deliver an
ordinary warning, so the decisions and notes use one block at the stop. Its generated
command maps invocation failures to exit 3 and never returns exit 1, which
would accidentally continue the agent. Those firings saw 1.1.0's blocking
stop and after-edit; decisions, notes and the after-edit context of this release
are **not yet proven** in any tool.

Profiles translate the internal results (0 pass, 1 warn, 2 ask, 3 could not
run) into each tool's contract. The stop delivers owner questions and/or
agent notes: Claude Code, Codex and Kiro receive one `decision: block`; Antigravity receives one
`decision: continue`, which continues the agent's turn once so it can ask
you about decisions or act on notes. After an edit, Claude Code and Codex receive the findings as additional
context with a `systemMessage` for you. Result 3 never blocks. Select
`--emit raw|claude|codex|antigravity|kiro`; the default is `raw`. Gemini CLI,
Copilot CLI and Cursor have hook systems but no upspec profiles yet. A tool
without a profile stays unwired until it has one. Profiles for Gemini CLI,
Copilot CLI and Cursor are planned ideas; the commit hook and pipeline still
apply to their work.

**Integration branch.** The base order is `--base`, `UP_BASE`,
`git config up.base`, the rules-block line `**Integration branch:** <name>`,
then detection. Set it to where the feature will be integrated, even when a
different branch receives deployments. Named branches are considered locally
and on every remote. Detection compares remote defaults and `main`, `master`,
`dev`, `develop`, then local candidates. It counts the commits HEAD has that
each candidate lacks and chooses the smallest count. The current local
branch is excluded unless it is the only candidate; ties follow candidate
order. The comparison uses the merge base.
An invalid named base reports its source with result 3; without a detected
base, only uncommitted changes count. Committed pins and tracking warnings
still compare against HEAD when it exists; the header keeps naming the base
as `none`. The log names the ref and its source.

Setup proposes the integration line from detection for you to confirm. It
never turns `UP_BASE` or `git config up.base` into a shared setting: when one
is set, it names the local override and proposes no line. Add a shared line
by hand if appropriate. `--no-integration-line` declines a proposal while
accepting the rest of the plan. When detection finds no branch, setup prints
a note; add the integration line by hand. Setup also warns when git ignores
the spec folder or change records: ignored specifications are validated at
the open-work list; ignored records never open its record list.

**Stop policy.** Session start records each use case's Status by id and HEAD
in a separate git-folder `up-session-<key>.json` file for each session. The key
is the first sixteen hex characters of the session id's SHA-256, or `none`
without an id. Writes replace the file atomically without a lock; interrupted
temporary writes never block later writes. After each write, pruning targets
the eight newest session files. Files younger than one minute are kept even
above that target. Pruning renames a candidate aside before comparing its
device, inode and modification time with the selection. A matching file is
removed; a refreshed file is restored with a hard link that never overwrites
a newer file at the session name. The renamed copy is then removed. Abandoned
temporary files older than one day are cleaned up. A first turn without a
snapshot creates one before the agent acts; a null HEAD always means no
commit existed yet. Resumes keep the same snapshot, and worktrees have
separate files. A write failure is logged without failing session start.
Without a snapshot, the stop compares against HEAD; checking out another history falls back to HEAD too.

Only a Status raised to Implemented or above in the working tree or in local
commits made since the snapshot and absent from remotes is a claim. Pulled
raises and renames alone never count. Implemented needs a ready finish check;
Tested and Done also need every flow and rule named by a test. A covering
change record selects the units; otherwise the whole use case is checked.
Missing evidence is a drift, with the move, the problems and both ways to
align: add the evidence, or restore the previous Status and tell the person
what remains. A file naming an uncovered use case counts only when the session
changed it, uncommitted or in a commit that is the claimed use case's work (a
path or the message names it; a range such as `UC-001..UC-003` names each);
in such a commit, a file whose use case the message names, or a specification the commit creates, is that other use case's
work. When files of other use cases are the only finding, the drift says so
instead of "without its evidence", and its advice is to look at those files;
the Status can stay. Earlier unpushed spill warns. The other drifts are an open change
record, behavior code changed without a specification (read as the spec-first
guard reads it, with the change's commit messages for the `No behavior
change:` line and the `Fixes:` note; a light-path fix is noted once before
its commit, with advice to commit its `Fixes:` note in the same session;
code that reaches the session through a pull or merge is not noted) and a broken A-files shape, as the project's own
`tools/check_tracking.py --strict` reports it on its command line. Broken specifications are never a drift
at the stop.

**Decisions and notes.** Questions are reserved for choices only
you can make: a person-set Status (`Approved`, `Done`) that the change sets
or relies on, or work you reserved for approval. An unsupported `Implemented`
or `Tested` claim, an open change record, code without a specification and
an A-files finding are notes.

Each new decision asks once: align now, at the end of the session, or later.
Now means align in this session; end of the session means remind you once at
session end; later runs the item's `hook_gate.py later TEXT` command. With the
A-files, it adds an `AHEAD.md` item (kind `idea`, state `open`, entry under
Items); otherwise it appends to `up-deferred.txt` in the git folder, shown
as open work at session start until removed. It never duplicates an item.

Notes reach the agent as one list of what is out of step and what aligns
each item. The message says none needs you and tells the agent to align them
now or include them in its handoff, within the current task's authorization.
There are no scheduling choices. An explicit request for uncovered behavior
records its missing use case as open work directly through `hook_gate.py
later TEXT`, without a question.

Decisions and notes use the same before-stop delivery channel (internal
result 2, historically `ASK`). A mixed stop carries both in one message.
The snapshot's `asked` memory covers both kinds: each key is sent once per
session; a new session can receive it again. A temporary file remembers keys
when the git folder is read-only; files untouched for a day are removed.
If nothing can be written, the stop only informs. With no new drift it passes
quietly. Its log names the baseline, open-list size, drifts found and new.
The hook never forces alignment.

**Open work.** Session context includes open records, changed specifications'
finding counts and first error, raises against the change's base and broken
use cases at Reviewed or above marked "a problem at push". These are work in
progress: fix an item only when it belongs to the current task. A use case
is marked Implemented or Tested once its items are clean; the push check
reports the rest. The list reads docs and git paths only, never source files or
the finish check, and caches validation by content. Completed cache updates
are saved even when the shown list stays unchanged or computation hits its cap. It shows fifteen items
plus an omitted count; session context stays within sixty lines.

Turn start delivers a changed list, suppresses an unchanged one and announces
"Nothing is open now." once when it empties. Its three-second computation cap
keeps prompt work bounded; generated timeouts are eight seconds, covering
stdin, computation and startup overhead. Every failure exits 0, prints nothing and logs its reason. Claude Code and Codex
use `UserPromptSubmit` additional context; Kiro uses plain stdout below
3,000 characters. These turn-start entries are **not yet proven** in live
tools. Antigravity has no start-of-turn event: `PreInvocation` fires before
every model call, so only session start delivers its open list.

After-edit feedback leaves out cross-file requirements and mechanism
findings, and recognition errors belonging to other files. An edited use case
in an earlier format warns with the migration notice. Other in-file errors
reach the agent as information, result 1; the agent goes on with its task.

A drift is known by its kind and subject (the use case and its new Status,
the record's path, the change that code without a specification belongs to,
known by the name of its base and the current branch (a base with no name by
its commit), each A-files finding by its path, its code and what its message
names: an identifier, a quoted or bold name, a path), never by its problem
text, so changed line numbers, a count that grows, more code in the same
change, more commits or pushes on the same branch, or a shorter problem list
do not ask again, and a new record or
finding of the same kind is asked about once. Without a session id the questions are
remembered under one shared slot. There is no loop guard: nothing keeps the
agent working, and nothing is asked twice in a session.

**Generated wiring and conflicts.** Setup preserves unrelated hooks and
settings, indentation, key order, Unicode and the final newline; inline
layout may be normalized. Every wiring file that changes has a full unified
diff before `--apply`; unchanged files have no file diff. Claude Code's Edit
and Write entries both narrow to the use case folder. Setup scans other
Kiro hook files for legacy entries, and Claude's local settings for duplicates.
It never writes `.claude/settings.local.json`: keep that moment or remove
its local entry by hand before asking for a generated replacement.

An unrecorded, customized or legacy adapter entry already covers its moment,
even if only one of two expected edit entries exists. Setup refuses duplicate
wiring. Choose `--replace wiring:<moment>` for generated replacements, or
`--keep wiring:<moment>` to retain the existing entries and add nothing.
Moments are `session-start`, `after-edit`, `before-stop` and `turn-start`. Pass the reason
for each adaptation using repeated `--reason TEXT`, in the order of the kept
wiring moments; the bundle records it (default: "kept by the person").
A moment no longer generated for the tool (Antigravity's after-edit) whose
entry is still installed must be decided the same way: `--replace` removes it
and generates nothing, naming its old adapter as left behind; `--keep`
retains it.

**Updates.** Run `python3 "<skill-folder>/scripts/scaffold_docs.py" --update` from the new plugin to see the
plan, review it, then approve `--apply`. The plugin's state reader adds one
advisory line naming older installed versions and the update command, also
available as JSON `notice` (otherwise `null`). The router passes it on without
blocking. The installed state reader cannot know about newer plugin releases.
No installed copies means no notice.

Each script is current, untouched, kept, changed by hand or missing. Current
and kept copies stay; untouched copies refresh; missing copies are added only
for an installed set. An update alone never installs the hook set. `--hooks`
installs it and uses the same update plan when copies already exist. Read each
changed script's diff and choose `--replace NAME` to take this release's copy,
or `--keep NAME` after porting the customization onto this release, including
its version. A kept file needs a new decision at the next release; the old
baseline is shown for context. A kept customization can also be replaced.

**The rules block.** `--update` treats the rules block (the section from
`## Working from specifications` to the next `## ` line or the end of the
guideline file) like an installed script. A block exactly as a release wrote
it is untouched: the plan lists `guideline:rules-block` as replaced, and
`--apply` swaps in this release's template whole, keeping the block's own
`**Profile:**`, `**Hooks:**`, `**Skipped:**`, `**Specs folder:**`,
`**Integration branch:**` and `**Host:**` lines (the Hooks line goes directly
under the profile line) and its specification folder. "Exactly" is judged
with those lines and the folder in the paths put back to the template's, so a
profile, a proven-hooks line or a folder never makes a block look edited. A block you edited
shows its diff as changed and waits for `--replace guideline:rules-block` or
`--keep guideline:rules-block`; nothing is rewritten until you choose, and
a keep is recorded in `tools/specs/upspec-installed.json` (the folder is
created for it) and is offered again only when the block or the template
changes. The rest of the guideline file is never touched, and a project
with no guideline file or no rules block gets none from `--update`.
`--replace guideline:rules-block` and `--keep guideline:rules-block` belong to
`--update`; without it they are a usage error (exit 2). When `--update` adds
the integration branch line (and a specs folder line, if the block has none),
the dry run prints the lines it adds beside the rules-block diff. The guideline
file keeps its own line endings (LF or CRLF) through both steps.

`tools/specs/upspec-installed.json` records package baselines, kept script
fingerprints, and generated or adapted wiring per tool. An ordinary update
also plans every recorded tool's wiring; `--hooks` without `--tool` requests
scripts only. With several recorded tools, select `--hooks --tool` when
deciding a moment. Matching entry baselines refresh; exact generated sets
are current. Fingerprints include the whole Kiro hook, or the inner command
object plus the group's matcher for other tools. Changes to those wrapper
fields need another decision. Kept wiring adaptations stay recorded.

Updates are **all or nothing**: an undecided script or wiring moment, or
unreadable JSON (including comments), prevents every write. An undecided
`--apply` exits 1; invalid decisions exit 2. Missing or mixed script versions
make the gate return result 3 naming `scaffold_docs.py --update`. One exception:
if `hook_profiles.py` itself cannot load, the gate logs that failure and exits
0 with no output. Commit installed scripts and wiring on their own before a
behavior change.

**Proof and records.** After you enable hooks, the agent proves each moment
in a new session, checking behavior and the git-folder `up-hooks.log`.
Temporarily invalid specifications test after-edit delivery. A Status raise
without evidence tests the question and its three answers; a second stop
asks nothing. Restore the Status. Submit prompts with a
changed, unchanged and then emptied open list to prove turn-start delivery.
Restore every proof edit. Add
only hooks seen firing to a `**Hooks:**` line below the profile in the rules
block, with the tool, configuration, date and delivery limitations.
The log records internal results rather than the tool command's exit code.
A shortened message names `up-hooks-report.txt` in the git folder for its
full text; that file is replaced on the next shortened message.

Hooks provide feedback in the tool's sessions. The commit hook and the team's
pipeline report to everyone, and pass unless the team added `--strict`. Hooks never approve specifications, and a
passing finish check still needs a person to read the report.

**The push gate.** The GitHub workflow checks Status claims, runs
`spec_lint.py --gate` and the spec-first guard on every push and pull
request. Every step reports and passes: Draft findings warn, Reviewed or
later specifications that do not validate are reported as problems, and the
guard warns on every branch. A team that wants a strict pipeline adds
`--strict` to a step, which then fails on its findings (the lint's Draft
findings never fail). Push messages supply the guard's declarations and `Fixes:` notes. The range is the pull request target or the push's
previous commit when available; a first push selects from the integration
fork, even when that fork equals HEAD. An empty baseline is used only for
a first push to the integration or default branch, or when no integration
ref exists. `--first-push` and `--since` are mutually exclusive; combining
them is a usage error (exit 2). CI uses the range base for evidence on pull
requests and integration or default branch pushes. Other pushes resolve the evidence base as the stop does. Without an available
previous push tip, the guard checks the last commit and only its message;
a root commit is checked from an empty tree.

**Optional pre-push hook.** In either profile, plan with
`python3 "<skill-folder>/scripts/scaffold_docs.py" --pre-push`; add `--apply` to install. It uses git's hooks
folder, honoring `core.hooksPath`, only inside the work tree or git folder,
including the common Git folder shared by linked worktrees.
The plan names a tracked folder as shared by every clone. An existing hook
or outside folder gets the line to add by hand; setup never edits it. The
hook checks pushed HEAD refs and skips deletions; other tips get a notice.
It reports problems and lets the push go ahead; add `--strict` to its claims
line to stop a push on problems. Unavailable checks pass with a notice. Uncommitted docs
edits are included and can differ from CI; `git push --no-verify` skips the
hook. CI stays authoritative.

The bundle records the rendered workflow and the package hook. `--update`
adds the claims scripts wherever the workflow exists, and offers a new hook
without writing it unless `--pre-push` is supplied. Recorded untouched files
refresh. A hand-changed or unrecorded workflow needs
`--replace ci:specifications` or `--keep ci:specifications`; an existing
custom hook stays with its owner and gets the line to add. See setup's
`references/profiles.md` for the command and placement details.

## 10. Rigor profiles: throwaway, solo, team

Setup asks one question: will this system be maintained, extended or handed
over to someone else?

| Instrument | Throwaway | Solo | Team |
|---|---|---|---|
| Vision | — | One page | One page |
| Requirements, entity model, use case map | — | Yes, unless you leave one out (recorded as skipped) | Yes |
| Use case specifications | — | Yes | Yes |
| Rules block in the guideline file | One line: the code is disposable | Yes | Yes |
| Validator and lint | — | Run on each specification | Every push and pull request, reporting; Draft findings warn; `--strict` to fail |
| Review before Approved | — | Cold read, your own sign-off | Independent reviewer and a named person's sign-off |
| Spec-first guard | — | Warning in a commit hook | Warning on every push and pull request; `--strict` to fail |
| Agent hooks | — | Offered: session state, after-edit findings, open work at turn start, owner decisions asked once and agent notes sent once at the stop | Offered; the pipeline reports to everyone |
| Push claims check | — | Optional pre-push hook | Every push and pull request in CI; optional pre-push hook |
| Ownership of `docs/`, pull request template | — | — | Yes |
| Spec dashboard | — | On demand | Each iteration |

Throwaway sets up nothing beyond one line saying the code is disposable, and
names the event that ends that status (someone starts depending on it, or it
outlives its planned end). Parallel work is the line between solo and team:
one person keeps the order by habit; several people or agents in parallel
cannot.

The solo review is a cold read: a new session that receives only the
specification and its neighbors, never the conversation that wrote it. Its
limit: the same model catches sloppiness, not a misreading it shares.

## 11. Working with different agents and models

The skills are plain skill folders and the checks are plain Python scripts,
so nothing in them is tied to one vendor.

| Agent | Status |
|---|---|
| Claude Code (Sonnet) | Evaluated with `claude plugin eval` and on two real projects |
| Antigravity CLI `agy` (Gemini 3.8 Flash High) | Trialed on a real project through five rounds |
| Others that read `AGENTS.md` and skill folders | Expected to work the same way; not tried |

What the trials showed, in short:

- **The model matters more than the skills.** The same skills gave more
  accurate specifications on Sonnet than on Gemini. The skills made both more
  honest and better organized; they do not raise a model's accuracy.
- **Scripts hold where wording does not.** On Gemini, instructions in text were
  sometimes skipped; the script checks (finish check, guard check, record
  check, lint) held in every round.
- **Some steps stay advisory on weaker models.** Pinning today's behavior first
  for a row the change alters, and asking you to confirm a classification,
  were skipped by Gemini more than once. The approval gate, which is yours,
  always puts the record in front of you.

Keep the guideline file the agent reads (`CLAUDE.md`, `AGENTS.md`, or both
with one importing the other) carrying the rules block that setup writes; it
names the skills, so a fresh session finds the right one even for a task that
looks simple.

Agent hooks are wired per tool from one tool-neutral template; the setup skill
carries examples for Claude Code, Codex, the Antigravity CLI and Kiro, each
checked against one version and seen firing on it. For the Antigravity
desktop app it is unclear whether workspace hooks run.

## 12. Safety

- **Approval and acceptance are a person's.** No skill sets Approved or Done.
- **Destructive steps are gated.** Schema changes, data migrations and moving
  files run only after a dry run or plan and your explicit confirmation.
- **Breaks are restored.** The guard check restores every file it breaks and
  verifies it byte for byte; if a restore ever failed, the original is kept
  next to it as `<file>.guard-backup`.
- **Nothing leaves the machine.** The scripts read files and git history. They
  never push, publish or call a network service.
- **No secrets in files.** Specifications and records name roles and use
  invented values. Recovery never copies a credential, a connection string or
  personal data; a credential committed to the repository is recorded as a
  suspect that names the file and the kind of secret, never its value, and you
  are told it needs rotating.
- **Text in the project is data.** Instructions found in code comments,
  documents or data are treated as content to describe, never as instructions
  to follow.

## 13. Troubleshooting

| Symptom | What to do |
|---|---|
| A script says `OLD_FORMAT` | Stop normal work and run `up-migrating-spec-formats`; see 7.9. Old formats are recognized, not accepted by the checks |
| A skill does not start for your request | Name it (`up-7-implementing-use-cases UC-004`), or ask the router where you are |
| Two skills answer the same request | Another skill set for the same steps is installed; keep one set |
| The agent searches the disk for a script | The script is in the skill's own folder; every skill says so. Point it there |
| The finish check lists hundreds of files | Set `**Integration branch:** <name>` in the rules block to the feature's integration branch, or override it with `--base`, `UP_BASE` or `git config up.base`; check the base and source in the hook log |
| A deleted file is flagged | Name its exact repository-relative path in the change record, in backticks or as a Markdown link target, so the check can attribute the deletion |
| A hook never writes to `up-hooks.log` | The tool did not run it: check that the person approved the hook (and trusted the folder), and that the tool runs hooks in this mode or engine |
| The agent was not told what is open | Check the `turn-start` entry, the tool's start-of-turn support and `up-hooks.log`; Antigravity receives the list at session start only |
| The stop sent a decision or note once and then said nothing | That is the design: each decision is asked once and each note is sent once per session. A decision's "later" answer is in `AHEAD.md` or in `up-deferred.txt` in the git folder; the open-work list shows the deferred lines at session start |
| The pipeline passed with findings | Every check reports and exits 0 by default; add `--strict` to a step for a strict pipeline |
| "unknown revision" from the finish check | Pass the branch or commit the change started from with `--base`, or `HEAD` while nothing is committed |
| "rests on no source" | Add the flow or rule to the record's sources table: the request, a decision, today, or a listed assumption |
| "... the change record does not name it" | A flow or rule changed outside the record: add a row for it (with why), or undo the change |
| "a pin the change did not touch" | The cited test does not pin what changed. Pin the row with a test that asserts its Today cell, commit it, then change the code and the test |
| Guard check verdict `invalid` | The test fails before the break, or ran past the timeout: fix the test first |
| Guard check verdict `not caught` | The test does not guard the rule: strengthen it until the break makes it fail |
| Guard check verdict `crashed` | The element's test stopped on an error rather than an assertion (a syntax error, a failed import, an unexpected exception): read the output the check prints, then make a smaller break that keeps the code running, or make the test assert the element's outcome before anything else can fail |
| Guard check verdict `unclear` | Read the output the check prints: another element's test may have caught the break, the name may lack the use case or the element, or an error was printed apart from every test's report. Name a test after the element, or pass `--expect TEXT` |
| `UNREADABLE` from the guard check | It could not read the specification, the enforcing file or its log and did not run: fix the file's permissions or encoding, then run it again |
| "the guard check of UC-012 BR-001 (...) is stale: run scripts/guard_check.py again" | The rule, its Examples table or the enforcing file changed since the row was logged, or the row is from before 1.3.0: run the guard check again |
| The spec-first guard warns about a bug fix | Add the note `Fixes: UC-012 BR-005` to the commit message, naming the use case and the element the fix restores |
| "the text to replace occurs N times" | Give a longer piece of text, so that it occurs exactly once |
| Specifications live outside `docs/` | Record the folder as `**Specs folder:** DIR` in the rules block (setup's `--specs-folder`); every script reads it, and `--docs DIR` overrides it for one run |
| The validator warns about emoji or long quotations | A specification says what a message tells the actor; it quotes exact screen words only where a rule depends on them |

## 14. Known limits

- **Early release.** Tested on three small real projects, all
  in Python, with a stand-in owner, plus fixture projects.
- **Other stacks.** The skills carry no framework code, but only Python
  projects have run them end to end; the TypeScript fixture is read as text.
- **Size.** The largest real project tried had about twenty use cases. How
  the skills behave on hundreds is not known.
- **Renderers and hosts.** The overview's use case diagram needs Mermaid
  12.0.0 or later (keyword `usecase-beta`); GitHub draws it, and an older
  renderer shows a syntax error in its place while the table stays readable. The pipeline template was checked as YAML, not run on a hosted runner.
- **Pinning on weaker models.** On Gemini, pinning today's behavior first for a
  row the change alters can be skipped in ways the finish check cannot see.
  The new test and its guard check still protect the changed behavior.
- **Models vary from run to run.** No set of instructions is followed every
  time. Rely on the script checks and on your approval, not on any single
  instruction.
- Agent hooks depend on each tool's hook system, which changes between
  versions. The examples name the version they were checked against; the
  proof step, not the example, decides whether a hook works.
- **Installing in other tools.** Agent Plugins support differs by tool. Codex
  installed from the marketplace file and Antigravity from the plugin folder;
  Kiro installed the folder as a power, but only its V3 engine offered the
  skills. Copying the skill folders worked in every tool tried. Kiro's custom
  agents see a skill only when it is listed in their `resources`.
- **References from outside.** `relink.py` checks references inside the
  repository only: links from other repositories or websites, and paths built
  at run time, are not checked.

## 15. Glossary

| Term | Meaning |
|---|---|
| Alternative flow | A numbered way a step can go differently (`A1`), with its trigger step and an explicit ending |
| Baseline review | The review of recovered specifications, in two roles: what the system does and what it was meant to do |
| Bounded context | A part of a large system that owns its own requirements, entities and use cases |
| Business rule | A named decision of a use case (`BR-001`), with boundary examples |
| Change record | The agreement behind one change: front matter, Context, Decision, Specification change and Consequences |
| Coverage unit | Something a test must cover: the main scenario, a flow, a rule boundary, a postcondition, a failure guarantee |
| Evidence ledger | Recovery's record of where each recovered claim comes from, with its verification state |
| Finish check | The implementer's gate before reporting a change |
| Guard check | A deliberate break of an element to prove its test fails |
| Guideline file | `CLAUDE.md` or `AGENTS.md`: the rules every agent session reads |
| Invention list | The decisions an agent made that its inputs did not settle |
| Journey test case | An end-to-end story across several use cases (`TC-001`) |
| Marker | The comment `UC-XXX BR-YYY: <rule>` above the code that enforces a rule |
| Pin | A test that asserts today's behavior before a change alters it |
| Rigor profile | Throwaway, solo or team: how much of the process a project uses |
| Sign-off test | Would the stakeholder have signed the specification as it stands, knowing what they want now? |
| Suspect | Recovered behavior that looks unintended, recorded instead of corrected (`S-012`) |
| Use case | One goal of one actor, reached in one sitting (`UC-001`) |

## 16. Credits and license

These skills are inspired by Simon Martinelli's work on the Unified Process.
They are an independent work, not affiliated with or endorsed by him.

Licensed under the MIT License; see `LICENSE`. Copyright (c) 2026 Christian Orrala.
