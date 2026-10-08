---
name: up-migrating-spec-formats
description: Moves earlier upspec specifications and installed checks to the current formats with a dry-run plan, owner-approved judgment, two commits and verification. Use when a script reports OLD_FORMAT, the router names MIGRATE, or the user asks to upgrade earlier upspec formats. Not for another method's specifications or recovery from code.
---

# Migrate specification formats

## When to migrate

A script printed `OLD_FORMAT`, the router named `MIGRATE`, or the owner asked
to upgrade earlier upspec formats. Read [conventions](references/conventions.md)
for the target shapes and [mapping](references/mapping.md) for mechanical rules.
This is a format conversion, with no change to behavior or approval.

## Plan

Run `python3 scripts/migrate_formats.py plan --docs DIR --format json` from
the project. Show all three lists to the owner: mechanical changes, judgment
work, and installed checks. Plan writes nothing. Refuse to start apply outside
a git work tree or with uncommitted work and no migration journal.

An installed check under `tools/specs/` is replaced only when its fingerprint
matches a released copy. Current copies stay as they are. Missing checks are
added when the project has an installed-check folder. A file changed by hand
needs review: show its customizations to the owner and agree how to preserve
them before manually copying the current script from this skill's `scripts/`.
The replacement set includes `scripts/spec_model.py`,
`scripts/validate_use_case.py`, `scripts/spec_lint.py`, `scripts/use_case_map.py`,
`scripts/spec_first_guard.py`, `scripts/hook_gate.py`, `scripts/workflow_state.py`,
`scripts/finish_change.py`, `scripts/scope_audit.py`, `scripts/uc_change_list.py`
and `scripts/unrecorded_changes.py`. `scripts/known_scripts.json` holds released
fingerprints, consumed by the migration. Never silently overwrite custom
checks. Benefits and titles stay in requirement context; Next instructions
stay in Consequences and on the judgment list. Process labels and routes
stay verbatim in the journey body. Unrecognized or duplicate metadata and
unsupported sections leave the whole input unchanged for judgment.

Plan runs without git and warns that apply needs it. Apply and verify require
a git work tree; unavailable git reports `GIT_UNAVAILABLE` with exit 3.

Ask for the owner's yes to the plan before preparing the judgment pass.
Even “don't ask, just do it” must receive the plan and invention list and an
explicit yes before the judgment commit: this conversion can decide meaning.

## Judgment pass

After the owner's yes to the plan, draft changes in memory or a temporary
copy. Do not write them into the project before mechanical apply: it needs a
clean tree. Use the current formats in conventions:

- Turn each journey Flow table and Validation list into one `Scenario` in
  one `gherkin` block. Preconditions become `Given`; each action row becomes
  `When`; each Verify row and Validation item becomes `Then`. Include literal
  data in quotes. Put each row's use case on a separate `# UC-XXX` comment
  line immediately before its first step. Keep Roles and postconditions.
- Turn rule prose examples into a table: input columns first, `result` last,
  with a blank line before the table. Keep the stated outcomes and every
  boundary. Supply at least two contrasting rows. When a side of a boundary
  was never stated, list the proposed example as an invention.
- Rewrite each NFR or constraint into one EARS pattern: `The … shall …`,
  `When …, the … shall …`, `While …, the … shall …`,
  `If …, then the … shall …`, or `Where …, the … shall …`.
  Preserve every number, unit and condition. Decide the subject explicitly.
- Resolve unclear business types from the attribute's meaning. Decimal or
  Long alone does not prove Money or Number. Review off-pattern stories and
  the retained benefits with the owner; move meaningful benefits into the
  vision or goal if agreed. Complete stub goals/triggers and check actors.
- Decide where a Next instruction carried into Consequences belongs; preserve optional record
  sections that contain information. Resolve unrecognized fields by hand.

Keep an **invention list**, one line per meaning decided: document and element,
old wording, proposed interpretation, and evidence or uncertainty. “None” is
valid only when nothing was decided. Show the draft and invention list and
get the owner's explicit yes to them before the judgment commit.

## Apply and verify

Run `python3 scripts/migrate_formats.py apply --docs DIR`. It computes all texts
before writing, journals them in the git directory and replaces files atomically.
Renames use git. Do not delete the journal after an interruption; rerun the
same command with the same HEAD and docs folder. Resume recognizes its own
writes and refuses conflicts, naming each file. Settle a conflict with the
owner; never discard their edit just to make resume pass. The environment
variables `UPSPEC_MIGRATE_STOP_AFTER` and `UPSPEC_MIGRATE_CRASH_AFTER_WRITE`
are test hooks, not ordinary workflow options.

Check the mechanical diff and commit `specs: mechanical migration to the current formats`.
Write the approved judgment draft, refresh the overview with
`python3 scripts/use_case_map.py --docs DIR` if metadata changed, and write one
change record with `outcome: migration`, `element: specification formats`,
and four sections: Context contains the plan; Decision contains the invention
list; Specification change says “format only”; Consequences says no change in
behavior. Commit `specs: migration, judgment pass`.

Run `python3 scripts/migrate_formats.py verify --docs DIR`. Fix format findings
until it exits 0. It checks every artifact and the generated overview, then
runs the lint. The lint's other findings appear under “Present before or newly
visible: for the owner”; bring them to the owner without inventing a repair.
A lint that cannot run is a verification failure. Report both commit identifiers,
the invention list, verify's result and any remaining lint findings.

## What never changes

Identifiers, Status, steps, flows, endings and rule meanings stay unchanged.
The generated overview derives from the files and has no independent Status.
No Approved use case loses its approval. Business processes stay BPMN 2.0.

## Workflow

1. Run plan; present mechanical, judgment and installed-check lists.
2. Obtain the owner's yes to the plan; prepare the judgment draft separately.
3. Present every invented meaning; obtain the owner's yes to the draft/list.
4. Apply and commit mechanical conversion; write and commit the approved
   judgment changes with one migration record and reviewed installed checks.
5. Verify, fix format errors, and report other lint findings to the owner.

## Validation

Verify exits 0; no format error remains; the overview is current. Compare the
old and new identifiers and Status. Installed checks are current or their
customizations have been explicitly reviewed and resolved with the owner.
Keep the two commits separate and preserve the approved invention list.

## Worked example

An earlier repair desk has bold Overview fields, a PlantUML diagram, database
types and a journey Flow table. Plan lists front matter and generated Mermaid
as mechanical, the journey and Decimal's business meaning as judgment.
The owner approves the plan, then a draft Scenario with UC comment lines and
Money for an estimated cost. The invention list records the Money decision.
Apply creates the mechanical commit. The approved draft and a migration
record form the second commit. Verify exits 0; an unrelated uncovered need is
reported to the owner. Every use case retains its original Status.
