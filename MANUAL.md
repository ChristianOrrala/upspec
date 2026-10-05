# upspec: User Manual

Version 0.1.0

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

`upspec` is a set of fourteen agent skills for specification-first
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

Nothing is installed into your project by the skills themselves, and no
script sends anything over the network.

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
specifications in another folder or another method's format, or tracks its
work in files such as a board or a feature list, setup lists them and asks
once: full alignment (everything moves into the root and `docs/`, and
`scripts/relink.py` checks every reference to what moves, agent instructions
included) or keep (a specification folder is recorded with `--specs-folder`,
nested or not; another method's files stay as references). When the project
tracks its work in the A-files, setup joins them; when you ask for the
A-files and they are not there yet, setup hands over to the A-files skill
first and writes nothing.

**Not sure where you are.** Ask:

> Where are we with the specs, and what comes next?

The router (`up-0-navigating-spec-driven-work`) reads the repository's state
and names the single next step and the skill that performs it.

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
Done.

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
the change record's assumptions, and in the implementation report. Behavior
you could observe is a question for you; a free detail is declared as free.

## 5. The project's files

| Path | Content | Written by |
|---|---|---|
| `docs/vision.md` | Purpose, users, goals, scope in and out | A person |
| `docs/requirements.md` | Functional (`FR`), non-functional (`NFR`) and constraint (`C`) rows | `up-2` |
| `docs/entity_model.md` | Entities, relationships, attributes, lifecycles; the project's vocabulary | `up-3` |
| `docs/use_cases.puml` | Overview of actors and use cases | `up-4` |
| `docs/use_cases/UC-XXX-<name>.md` | One use case specification per file | `up-5` |
| `docs/processes/<name>.bpmn` | Optional business process models | A person |
| `docs/test_cases/TC-XXX-<name>.md` | One end-to-end journey per file | `up-writing-journey-test-cases` |
| `docs/change-records/UC-XXX-<name>.md` | One record per change | `up-triaging-change-requests` |
| `docs/reviews/` | Review and audit reports; the guard-check log | `up-6`, `up-9`, guard checks |
| `docs/recovery/` | Ledger, suspects, baseline review plan, change log of a recovered system | `up-recovering-specs-from-code` |
| `CLAUDE.md` or `AGENTS.md` | Guideline file with the rules block and the profile | `up-1` |

**Language.** Specifications and records are written in the project's own
language. Section headings, field labels (`**Status:**`, `**Trigger:**`),
Status values and flow endings (`Use case ends.`) stay as the template has
them, because the scripts read them.

**People.** Specifications and records name roles (the administrator, a
member), never people, and use invented example values.

**Another folder.** A project that keeps its specifications outside `docs/`
records the folder in the rules block as `**Specs folder:** DIR` (setup writes
it with `--specs-folder DIR`; a nested folder such as `documentation/specs`
works). Every script reads it, and `--docs DIR` overrides it for one run.

### With the A-files

When the project also tracks its work in the A-files, the two join by files,
and neither moves the other's:

- `AGENTS.md` names the specification rules in its hot zone and keeps two
  rows in step with the use cases (P1).
- An ability in `ABILITIES.md` may name its use cases in a `Specs` line. The
  router warns when an ability is done while one of its use cases is not, or
  planned while one is built, and notes use cases no ability names (P2).
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
- The session-start hook passes the same view on (P7).

A tracking file kept at adoption (the board, say) becomes the A-file's home:
the A-file names it with `**Home:**`, and the router then guesses nothing from
it. Without the A-files the skills behave as before.

## 6. The skills

Every skill name starts with `up-`. The number is the skill's place in the
chain; the four without a number are side entries.

| Skill | Use it to | It produces |
|---|---|---|
| `up-0-navigating-spec-driven-work` | Find out where the project stands and what comes next; classify incoming work | A recommendation; writes nothing |
| `up-1-bootstrapping-spec-driven-projects` | Set a repository up: profile, docs tree, rules block, team instruments | The docs tree, a vision skeleton, the rules block; for teams, ownership, a pull request template and a pipeline job |
| `up-2-cataloging-requirements` | Turn a vision, notes or an interview into requirements | `docs/requirements.md` and a conflict ledger |
| `up-3-modeling-domain-entities` | Build or change the entity model and its vocabulary | `docs/entity_model.md` |
| `up-4-mapping-use-cases` | Decide which use cases exist, at the right level, in what order | `docs/use_cases.puml` and a delivery order |
| `up-5-writing-use-case-specs` | Write or revise one use case | `docs/use_cases/UC-XXX-<name>.md` |
| `up-6-reviewing-specifications` | Review a use case or the whole set, without editing it | A review report with a verdict; a traceability matrix on request |
| `up-7-implementing-use-cases` | Implement or synchronize one approved use case | Code with markers, a plan, an invention list, the finish check's report |
| `up-8-deriving-use-case-tests` | Derive and maintain the tests of one use case | Tests per coverage unit, each rule test proven by a guard check |
| `up-9-auditing-spec-coverage` | Check that code and tests realize the specification | A coverage matrix or the spec dashboard; a suggested Status |
| `up-triaging-change-requests` | Turn a bug, change or hotfix into a specification-first change | A classification and a change record |
| `up-recovering-specs-from-code` | Bring an existing system under specifications | Use cases, entities, specifications, an evidence ledger, suspects, a baseline review plan |
| `up-splitting-bounded-contexts` | Split a specification set that has outgrown review | Proposed contexts, assignments and contracts; the move, on approval |
| `up-writing-journey-test-cases` | Write an end-to-end journey across use cases | `docs/test_cases/TC-XXX-<name>.md` |

You rarely need to name a skill. Describe the work ("write the use case for
resetting a forgotten password", "is UC-004 fully tested?") and the matching
skill is used. When in doubt, ask the router.

## 7. Workflows

Each workflow lists who does what. "You" is the owner; "the agent" is the
coding agent with the skills.

### 7.1 Starting a new project

1. **Set up.** Ask the agent to set the repository up. Choose a profile
   ([section 10](#10-rigor-profiles-throwaway-solo-team)), read the dry run,
   and say yes.
2. **Write the vision.** `docs/vision.md` is yours. It must name the actors by
   role, the core nouns with their meaning, and the boundaries (in scope, out
   of scope, neighboring systems). The agent can interview you and write down
   your answers, but it never invents a vision.
3. **Requirements.** "Turn the vision and these notes into requirements."
   Review the conflict ledger it returns and decide each open item.
4. **Entity model.** "Model the entities." The model becomes the vocabulary
   every specification must use.
5. **Use case map.** "Which use cases do we need?" Agree on the list and the
   delivery order of the first slices.
6. **First specification.** "Write UC-001." Answer its questions (at most five
   per use case). Everything else it assumes is listed in its hand-off.
7. **Review.** "Review UC-001." The reviewer works from the files alone and
   reports a verdict.
8. **Approve.** Read the specification and the review, then set
   `**Status:** Approved` yourself.
9. **Implement and test.** "Implement UC-001 with its tests." See 7.4.
10. **Audit.** "Is UC-001 fully tested?" The audit suggests whether Tested is
    justified.

### 7.2 Bringing an existing codebase under specifications

1. **Ask for recovery.** The agent maps actors, entry points, entities and use
   cases from the code, keeping an evidence ledger: every claim points at the
   line that decides it.
2. **Choose the depth.** A short baseline specification for every use case, or
   full specifications for the use cases about to change. The agent
   recommends one from the system's size.
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

### 7.3 Changing behavior the system already has

This is the most common workflow once a project is under specifications.

1. **Tell the agent what you want.** "When a code expires unclaimed, tell the
   group too." Triage reads the specification before any code.
2. **Classification.** The agent applies the sign-off test: would you have
   signed the specification as it stands, knowing what you want now? The
   outcome is one of seven (see [section 8](#8-the-change-record)). For a
   specification that is wrong, ambiguous or simply outgrown, it asks you to
   confirm.
3. **The change record.** The agent writes
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

The implementer reads only the use case, its linked requirements, the entity
model and the guideline file. Then:

1. It shows an element-to-code plan and the decisions the specification leaves
   open. Behavior decisions stop the run and become questions for you.
2. It works on a branch for the use case, never on the main branch.
3. Schema changes follow a guarded procedure with a rehearsal and your
   confirmation; nothing destructive runs unconfirmed.
4. It audits the scope: every changed file must belong to the use case.
5. It runs the project's tests and reports failures as they are.
6. It runs the finish check and pastes its report, filling in the three fields
   the check cannot verify (tests run, guard check, inventions).

### 7.5 Fixing a bug

Report it as you see it: "Users say booking a full day still works." Triage
decides whether the code, the specification or a test is wrong. For code that
is wrong, the agent writes a failing test named after the flow or rule first,
then fixes the code. For a specification that is wrong, the change goes
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

## 8. The change record

A change record is the agreement behind one change. Triage writes it; the
specification writer, the reviewer, the implementer and the finish check all
read it.

| Section | What it holds |
|---|---|
| Report and Element | Who reported what, and the use case element it concerns |
| Classification | The outcome, the sign-off test and who decided |
| Owner's decisions | Each decision you made, and the specification element it lives in |
| Sources of new behavior | Each new flow or rule and what it rests on: the request, a decision, today's behavior or an assumption |
| Assumptions | What the agent assumed for you to confirm, and where |
| Specification change | What changes in which element, and the Status reset |
| Differences from today | `Element \| Today \| After the change \| Requested by \| Seen in` |
| Impact | What else is affected, upward, sideways and downward |
| Reproduction, Urgent path | For defects and hotfixes |
| Next | The steps that follow |

**Seen in** says how today's behavior is known: `code` (read from the code, so
it must be pinned by a test before it changes), `test <name>` (pinned by that
test), or `observed` (seen on the running system with its real services).

**The seven outcomes of triage:**

| # | Outcome | It is when | What changes | Status |
|---|---|---|---|---|
| 1 | Code wrong | The specification is clear and right | Code, behind a failing test | Unchanged |
| 2 | Specification wrong | It says something nobody meant | The specification | Back to Reviewed |
| 3 | Test wrong | Code and specification agree; a test does not | The test | Unchanged |
| 4 | Specification ambiguous | Two readings; the code picked one | The specification, after you choose | Back to Reviewed |
| 5 | Enhancement | The specification was right for what was wanted then | The specification | Back to Reviewed |
| 6 | New use case | A goal no use case covers | Requirement, map, new specification | New file, Draft |
| 7 | No behavior change | Refactoring, dependency update, infrastructure | Nothing | Unchanged |

## 9. The checks

The skills run these scripts themselves. You can run them too, from the
project's root, with the script's path inside the installed skill folder. For
the team profile, setup copies the lint, the validator and the guard into
`tools/specs/` of the project, so the pipeline needs nothing installed.

Output follows one format: `path:line: SEVERITY CODE [element]: message`,
with `ERROR`, `WARN` or `INFO`. Exit code 0 means clean, 1 a problem (with
`--strict`, warnings too), 2 a usage error.

### Specification checks

| Script (skill) | What it checks | Example |
|---|---|---|
| `validate_use_case.py` (`up-5`, `up-6`) | One specification's structure and closed loop: every flow ends, every ending is covered | `validate_use_case.py --strict docs/use_cases/UC-001-book-repair.md` |
| `spec_lint.py` (`up-6`, `up-1`) | The whole set across files: dangling or duplicate identifiers, unrealized requirements, diagram and file mismatches, copied rules, mechanism and weak words; the traceability matrix | `spec_lint.py --strict`, `spec_lint.py --trace` |
| `unrecorded_changes.py` (`up-6`, `up-7`) | Flows and rules the specification changed since the change began that the change record does not name | `unrecorded_changes.py UC-012` |
| `check_requirements.py` (`up-2`) | The catalog row by row | `check_requirements.py --strict` |
| `check_entity_model.py` (`up-3`) | Diagram and sections agree; the vocabulary is used | `check_entity_model.py` |
| `check_use_case_map.py` (`up-4`) | The diagram against its conventions, the specifications and the catalog | `check_use_case_map.py` |
| `check_test_case.py` (`up-writing-journey-test-cases`) | Journey test case documents | `check_test_case.py docs/test_cases/TC-001-*.md` |
| `bpmn_paths.py` (`up-writing-journey-test-cases`) | The start-to-end paths of a BPMN process | `bpmn_paths.py docs/processes/repair.bpmn` |

### Change and implementation checks

| Script (skill) | What it checks | Example |
|---|---|---|
| `impact.py` (triage) | Everything that refers to an identifier or a business noun | `impact.py UC-004 "work order"` |
| `uc_change_list.py` (`up-7`) | What changed in one specification since it was last implemented | `uc_change_list.py UC-012` |
| `scope_audit.py` (`up-7`) | Every changed file belongs to the use case | `scope_audit.py UC-012 --base main` |
| `finish_change.py` (`up-7`) | The implementer's gate (below) | `finish_change.py UC-012 --base <start>` |
| `coverage_units.py` (`up-8`) | The coverage units of a use case and the tests that carry each label | `coverage_units.py UC-006 --tests tests` |
| `guard_check.py` (`up-7`, `up-8`) | Breaks one rule on purpose, runs its test, restores the file and logs whether the test caught it | see below |
| `spec_first_guard.py` (`up-1`) | A change set that changes behavior code with no specification behind it | `spec_first_guard.py --base main` |
| `relink.py` (`up-1`, recovery) | Moves files and every reference to them: `plan` lists links, imports, settings paths and agent instructions that name them, `apply` moves and rewrites, `verify` finds what is left; `--keep FILE` leaves a record of the moves as written | `relink.py plan --move specs docs` |

**The finish check** (`finish_change.py`) is the gate before an
implementation is reported. It checks:

- **Scope**: every changed file belongs to the use case or to another use case
  the same record names.
- **Markers**: every rule in the change has its marker in the code; a marker on
  a function nothing calls is warned about.
- **Tests named**: every flow and rule in the change is named by a test.
- **Guard check**: every rule in the change has a logged break that a test
  caught.
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
`ACTIVE.md` nor `ABILITIES.md` did; the warning never changes the result.

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
byte for byte, and appends a row to `docs/reviews/guard-checks.md`. The
verdict is `caught`, `not caught` (the test does not guard the rule) or
`invalid` (the test failed before the break, or timed out).

### Audit and recovery checks

| Script (skill) | What it does | Example |
|---|---|---|
| `coverage_matrix.py` (`up-9`) | Starts a use case's coverage matrix from identifiers in code and tests | `coverage_matrix.py UC-001` |
| `spec_dashboard.py` (`up-9`) | The spec dashboard, optionally with a JUnit test report | `spec_dashboard.py --junit report.xml` |
| `check_recovery_ledger.py` (recovery) | The recovery records against the specifications and the code | `check_recovery_ledger.py --strict` |
| `sample_claims.py` (recovery) | A random sample of recovered claims for a second reader | `sample_claims.py --count 10` |
| `spec_core_metrics.py` (splitting) | Size of the specification set and where it could be cut | `spec_core_metrics.py` |
| `workflow_state.py` (`up-0`) | The repository's state and the first step that applies | `workflow_state.py` |
| `scaffold_docs.py` (`up-1`) | The setup plan; writes only with `--apply`, never overwrites | `scaffold_docs.py --profile solo` |

### Agent hooks (optional)

Setup can make the agent's own tool run three checks without being asked:

| Hook | When | What it does |
|---|---|---|
| Session state | A session starts | Gives the agent where each use case stands and the next step |
| Specification check | Right after the agent edits a use case specification | Runs the validator and hands errors back to fix now |
| Finish check | The agent is about to stop while a change record is open | Runs the finish check and keeps the agent working until it passes, or until the same problems come back a third time |

The finish check starts once the change touches files outside the specification
folder (`--docs`) and `tools/specs/`, with a change record open. It stays quiet
during triage, specification writing and review.

All three call one script, `tools/specs/hook_gate.py`, which setup copies into
the project with `scaffold_docs.py --hooks`. Ask the setup skill for agent
hooks: it wires them into the tool you use (examples exist for Claude Code,
Codex, the Antigravity CLI and Kiro), shows you the configuration, and waits
for you to turn it on. Tools protect their hook settings from the agent on
purpose; approving is your step. The agent then proves that each hook fires
(each firing is logged in the git folder's `up-hooks.log`) and records them in
a `**Hooks:**` line of the rules block.

Hooks are earlier feedback, not a gate: they run only in sessions of the tool
that has them. The commit hook and the team's pipeline still hold for
everyone.

## 10. Rigor profiles: throwaway, solo, team

Setup asks one question: will this system be maintained, extended or handed
over to someone else?

| Instrument | Throwaway | Solo | Team |
|---|---|---|---|
| Vision | — | One page | One page |
| Requirements, entity model, use case map | — | Yes, unless you leave one out (recorded as skipped) | Yes |
| Use case specifications | — | Yes | Yes |
| Rules block in the guideline file | One line: the code is disposable | Yes | Yes |
| Validator and lint | — | Run on each specification | Blocking in the pipeline |
| Review before Approved | — | Fresh-context review, your own sign-off | Independent reviewer and a named person's sign-off |
| Spec-first guard | — | Warning in a commit hook | Blocking in the pipeline |
| Agent hooks | — | Offered | Offered |
| Ownership of `docs/`, pull request template | — | — | Yes |
| Spec dashboard | — | On demand | Each iteration |

Throwaway sets up nothing beyond one line saying the code is disposable, and
names the event that ends that status (someone starts depending on it, or it
outlives its planned end). Parallel work is the line between solo and team:
one person keeps the order by habit; several people or agents in parallel
cannot.

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
checked against one version. The Kiro example comes from its documentation
and has not been seen firing; for the Antigravity desktop app it is unclear
whether workspace hooks run.

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
| A skill does not start for your request | Name it (`up-7-implementing-use-cases UC-004`), or ask the router where you are |
| Two skills answer the same request | Another skill set for the same steps is installed; keep one set |
| The agent searches the disk for a script | The script is in the skill's own folder; every skill says so. Point it there |
| "unknown revision" from the finish check | Pass the branch or commit the change started from with `--base`, or `HEAD` while nothing is committed |
| "rests on no source" | Add the flow or rule to the record's sources table: the request, a decision, today, or a listed assumption |
| "... the change record does not name it" | A flow or rule changed outside the record: add a row for it (with why), or undo the change |
| "a pin the change did not touch" | The cited test does not pin what changed. Pin the row with a test that asserts its Today cell, commit it, then change the code and the test |
| Guard check verdict `invalid` | The test fails before the break, or ran past the timeout: fix the test first |
| Guard check verdict `not caught` | The test does not guard the rule: strengthen it until the break makes it fail |
| "the text to replace occurs N times" | Give a longer piece of text, so that it occurs exactly once |
| Specifications live outside `docs/` | Record the folder as `**Specs folder:** DIR` in the rules block (setup's `--specs-folder`); every script reads it, and `--docs DIR` overrides it for one run |
| The validator warns about emoji or long quotations | A specification says what a message tells the actor; it quotes exact screen words only where a rule depends on them |

## 14. Known limits

- **First release.** Version 0.1.0. Tested on three small real projects, all
  in Python, with a stand-in owner, plus fixture projects.
- **Other stacks.** The skills carry no framework code, but only Python
  projects have run them end to end; the TypeScript fixture is read as text.
- **Size.** The largest real project tried had about twenty use cases. How
  the skills behave on hundreds is not known.
- **Renderers and hosts.** PlantUML and Mermaid output was checked by parsers,
  not rendered. The pipeline template was checked as YAML, not run on a
  hosted runner.
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
| Change record | The agreement behind one change: classification, decisions, sources, assumptions, differences from today |
| Coverage unit | Something a test must cover: the main scenario, a flow, a rule boundary, a postcondition, a failure guarantee |
| Evidence ledger | Recovery's record of where each recovered claim comes from, with its verification state |
| Finish check | The implementer's gate before reporting a change |
| Guard check | A deliberate break of a rule to prove its test fails |
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
