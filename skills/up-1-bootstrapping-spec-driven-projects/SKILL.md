---
name: up-1-bootstrapping-spec-driven-projects
description: >-
  Sets a repository up for specification-first development with use cases: chooses a rigor profile
  (throwaway, solo, team), creates the docs tree and a vision skeleton, adds the spec-first rules to
  the guideline file (CLAUDE.md or AGENTS.md), for teams adds spec ownership, a pull request template
  with the specification-first review order, and a CI job that runs the specification lint and a
  spec-first guard, and offers agent hooks that run the checks in the agent's own tool. Use when the
  user wants to adopt, introduce or set up spec-driven development or use-case-driven work in a new or
  existing repository, asks which artifacts and gates a solo developer or a team needs, asks whether
  spec discipline is worth it for a prototype or a short-lived project, wants agent guideline rules
  for working from use cases, or wants hooks that make an agent run the specification checks without
  being asked. Not for writing a general CLAUDE.md and not for task boards.
---

# Bootstrapping spec-driven projects

Set a repository up so that specifications come first and stay first. The
method's promise ("code follows the specification, without exception") is
only as strong as what enforces it. This skill chooses how much to enforce
and installs exactly that.

It sets up. It writes no vision content, no requirement and no use case.

Shared paths, identifiers and Status values: [references/conventions.md](references/conventions.md).

## Choose the profile

Ask one question first:

> Will this system be maintained, extended, or handed over to someone else?

| Answer | Profile |
|---|---|
| No. It is a prototype, an experiment or a one-off script | **Throwaway** |
| Yes, and one person works on it | **Solo** |
| Yes, and several people work on it, or several agents run in parallel | **Team** |

Parallel work is the dividing line between solo and team: one person can keep
the order by habit, several people with agents cannot.

| Instrument | Throwaway | Solo | Team |
|---|---|---|---|
| Vision | — | One page | One page |
| Requirements catalog, entity model, diagram | — | Yes, unless the owner leaves one out; that is recorded as `**Skipped:**` | Yes |
| Use case specifications | — | Yes | Yes |
| Rules block in the guideline file | One line: disposable | Yes | Yes |
| Validator and lint | — | Run on each specification | Blocking in the pipeline |
| Review before `Approved` | — | Fresh-context review, own sign-off | Independent reviewer and a named person's sign-off |
| Spec-first guard | — | Warning in a commit hook | Blocking in the pipeline |
| Ownership of `docs/` | — | — | Yes |
| Pull request template with review order | — | — | Yes |
| Spec dashboard | — | On demand | Each iteration |

For **throwaway**, set up nothing. Add one line to the README or guideline
file saying the code is disposable, and name the event that ends that status:
someone else starts depending on it, it is shown as the base of the real
system, or it outlives its planned end. Then stop.

What each profile turns on, when to move up, and the three-step adoption path
for an existing team: [references/profiles.md](references/profiles.md).

## Scaffold

```bash
python3 scripts/scaffold_docs.py --root . --profile solo
python3 scripts/scaffold_docs.py --root . --profile team --host github
```

The script is in this skill's folder; use the base directory shown when the skill
was loaded, and do not search the disk for it. Without `--apply` it
prints the plan and writes nothing. Show the plan, get a yes, then run it
again with `--apply`.

For a solo project that leaves an artifact out, add `--skip requirements`,
`--skip overview` or `--skip entity-model`; the choice is recorded in the rules
block, where the other skills read it.

It never replaces a file. The one change it makes to an existing file is
appending the rules block to the guideline file, once. It picks the file
agents will actually read: `AGENTS.md` when it stands alone or `CLAUDE.md`
imports it, otherwise the existing `CLAUDE.md`. Name another with
`--guideline`, and pass on any note it prints about a second guideline file.

For the team profile it also copies `scripts/spec_lint.py`, `scripts/validate_use_case.py`,
the guard, `scripts/status_claims.py` and its finish-check helpers into `tools/specs/`,
so the pipeline runs without anything installed.

The identical copies of `scripts/finish_change.py`, `scripts/change_view.py`, `scripts/scope_audit.py`,
`scripts/uc_change_list.py` and `scripts/unrecorded_changes.py` serve for CI and the agent hooks.
The hooks also install `scripts/workflow_state.py`, their entry point `scripts/hook_gate.py`
and its module `scripts/hook_profiles.py`.

Setup and migration share the module `scripts/installed_copies.py` and released
fingerprints in `scripts/known_scripts.json`; both stay in the plugin.

When the project's files move to this layout, `scripts/relink.py` plans the
moves with every reference to them, applies them and verifies that nothing is
left broken; the existing structure reference says when.

## Existing structure and the A-files

Before the first dry run, look at what the project already has, and ask
about it once.

- **Specifications elsewhere.** The scaffold names folders of specifications
  outside the specification folder: this method's use cases in another
  folder, or another method's (`specs/`, `.kiro/specs/`, `openspec/`). Ask
  whether to align them fully (moved into `docs/` with `scripts/relink.py`;
  another method's converted by `up-recovering-specs-from-code` with the
  owner's review) or keep them (this method's: recorded with
  `--specs-folder`; another method's: kept as reference documents).
- **The A-files.** When `ACTIVE.md` has a hot zone, the project tracks its
  work in the A-files, and the dry run shows the joining edits. After
  `--apply`, run `python3 tools/check_tracking.py`; it must print nothing.
  Without them, ask once: "Track the project's work with the A-files too
  (five files every agent reads first: rules, current work, abilities, what
  is ahead, the map)?" On a yes, hand over to the `a-files` skill when it is
  available and run this setup again afterwards; without it, say how to get
  it and finish without them.

Choices, commands and the joining edits:
[references/existing-structure.md](references/existing-structure.md).

## Vision readiness

The vision is the one artifact a person writes. The scaffold puts the skeleton
[templates/vision.md](templates/vision.md) in place. Do not draft its content, even
when asked to "just fill it in": a vision an agent invented gives every later
step permission to invent. Offer to interview the owner and write down their
answers instead.

If the project already has a product document (`PRODUCT.md`, `VISION.md`, a
PRD), the scaffold finds it and the skeleton's Mission and Target Users point
to it instead of asking for the same text twice. Say so in the plan. The
vision then holds only what that document does not say: goals, scope,
neighboring systems, constraints, success measures. A glossary the scaffold
names is the vocabulary the entity model takes.

When it is written, run the scaffold again (dry run): it lists sections that
are missing or still hold placeholder text. Then read it and check three
things the script cannot:

| Check | Why |
|---|---|
| It names the **actors** by role | They become the primary actors of every use case |
| It names the **core nouns** with a meaning | They become the entities and the only words used for them |
| It states the **boundaries**: in scope, out of scope, neighboring systems | Without them, scope is decided one prompt at a time |

A slogan passes none of them. Report what is missing as questions for the
owner.

## Guideline rules

[templates/guideline-rules.md](templates/guideline-rules.md) is ten process rules under one heading, with
the profile recorded on its first line. It is short on purpose: the guideline
file is read on every task, and everything in it competes for attention.

- Append it. Leave existing content as it is, including stack rules.
- Do not merge it into existing sections or reword it per project.
- Stack rules (language, framework, commands) stay in their own section.
- If the file already has rules that contradict the block (for example
  "fix bugs directly"), point to the contradiction and ask which holds.

## Team instruments

Details and host-specific forms: [references/team-instruments.md](references/team-instruments.md).

- **Ownership:** changes under `docs/` need the requirements owner's review.
  Ask who that is. Never invent a name, a handle or a team.
- **Pull request template** ([templates/pull-request.md](templates/pull-request.md)): one use case
  per pull request; specification first in the review order; the invention
  list has its own section.
- **Pipeline job** ([templates/ci-github.yml](templates/ci-github.yml) for GitHub Actions; two
  commands for any other host): the lint and the guard block. An advisory
  review by an agent may comment and never blocks.

## The guard

```bash
python3 scripts/spec_first_guard.py --base INTEGRATION_BRANCH --mode warn
```

Replace `INTEGRATION_BRANCH` with the project's integration branch. The guard flags
a change set that changes behavior code with no specification change
and no declaration line `No behavior change: UC-012`, and code that arrives
with a use case still `Draft` or `Reviewed`. Refactoring and dependency
updates pass through the declaration, so the guard stays honest without false
alarms. `warn` reports and exits 0; `block` exits 1.

For a solo developer, offer the commit hook from the profiles reference. Do
not install a hook without asking: hooks change how every commit behaves.

## Agent hooks

With the solo and team profiles, offer four hooks: session state and the
open-work list at session start, validation after specification edits, the
open-work list at turn start, and a stop that blocks only on a use case raised
to Implemented or Tested without its evidence. All four call
`scripts/hook_gate.py`; `scripts/scaffold_docs.py --hooks` copies it into
`tools/specs/` with the scripts it calls.
Offer `--pre-push` in either profile, using [templates/pre-push.sh](templates/pre-push.sh); [references/profiles.md](references/profiles.md) explains placement and CI's authority.

Generate with `--hooks --tool <tool>`, review, then approve `--apply`, following
[references/agent-hooks.md](references/agent-hooks.md); labeled examples for
four tools are in [references/agent-hook-examples.md](references/agent-hook-examples.md).
For installed copies, use `scaffold_docs.py --update` as the reference explains.
You prepare the configuration and show it; the person turns it on. Never
bypass or widen permissions for it. A hook is done once it was seen firing,
and a `**Hooks:**` line under the profile in the rules block records it.
When the person has not turned them on yet, end with the three proof steps of the reference, so that they, or the next session, can see each hook fire.

## Workflow

1. Decide the profile with the deciding question and the number of people and
   agents working in parallel. For throwaway, write the one line and stop.
2. Run `scripts/scaffold_docs.py` without `--apply` and show the plan. Ask
   the questions of "Existing structure and the A-files" when the plan names
   specifications elsewhere or the project has no A-files.
3. After a yes, run it with `--apply`. With the A-files, run
   `python3 tools/check_tracking.py` until it prints nothing.
4. Ask the owner to write the vision. Run the readiness check and report what
   is missing.
5. Confirm the rules block is in the guideline file and nothing above it
   changed.
6. Team profile: ask for the requirements owner and the Git host; add the
   ownership rule; confirm the pull request template and the pipeline job.
7. Run `scripts/spec_first_guard.py` against the last commit and show what it
   reports.
8. If the owner wants agent hooks: run the scaffold with `--hooks` (dry run,
   then `--apply`), wire them as the agent hooks reference says, ask the owner
   to turn them on, prove each one, add the `**Hooks:**` line, and commit the
   hook files on their own.
9. Name the first use case to specify: one behavior that is contested or
   unclear today, small enough for one main success scenario and a handful of
   alternatives. Hand over to `up-0-navigating-spec-driven-work`.

## Report

Close with a report the owner can check, in this order:

1. **The profile and the reason for it** in one sentence: the answer to the
   deciding question, and for a team that several people or agents work in
   parallel.
2. **What is on and what is off** under that profile.
3. **What was written:** the scaffold's list of created, appended and skipped
   paths, as it printed them, and the hooks wired, with the log line that
   shows each one firing.
4. **What blocks and what only advises** (team): the lint and the guard block
   a merge; a review by an agent comments and never blocks.
5. **What is left to the owner:** the vision, the requirements owner, host
   settings only an administrator can make. If specifications were recovered
   from code and are still Draft, their baseline review comes before the
   vision: name it as the next step.

Installed checks include `scripts/use_case_map.py`: mapping runs it after
creating stubs or changing their id, name, actors or goal. Status changes
need no regeneration.

## Validation

- With the A-files: `python3 tools/check_tracking.py` prints nothing, and a
  second dry run reports the joining edits as already done.
- A second dry run of the scaffold reports nothing left to write.
- The guideline file starts with its previous content, unchanged, and
  contains the rules block once.
- The guard runs and exits as the profile expects (0 in `warn`).
- Team: the pipeline file parses, and no owner name or handle was invented.
- No vision content was written by you.
- Hooks, when wired: each was seen firing in `up-hooks.log`, and the
  `**Hooks:**` line names only those.

## Worked example

A repository with a `CLAUDE.md` of stack rules; one developer.

```text
$ python3 scripts/scaffold_docs.py --root . --profile solo
Plan: nothing written; add --apply to write (profile solo, host none)
  create docs/vision.md
  create docs/use_cases/.gitkeep  (keeps the empty folder under version control)
  create docs/test_cases/.gitkeep  (keeps the empty folder under version control)
  append CLAUDE.md  (rules block added at the end; existing content untouched)
4 to write, 0 left as they are
```

After a yes and `--apply`, the answer to the developer:

- Profile **solo**: specifications, the rules block, validator and lint on
  each specification, a fresh-context review before your own sign-off, the
  guard as a warning. Off: ownership rule, pull request template, blocking
  pipeline.
- `docs/vision.md` is a skeleton. It is yours to write; nine sections, one
  page. Tell me when it is ready and I check it for actors, core nouns and
  boundaries.
- Then pick one behavior that is argued about today and specify that first.
