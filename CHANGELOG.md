# Changelog

All notable changes to upspec. Versions follow semantic versioning.

## 1.0.4

- The migration plan no longer lists empty "unclear business type" items
  for tables in the entity model that hold no attributes, such as a
  glossary or a words-to-avoid table. Those tables were never changed;
  only the plan's list was wrong.

**How to migrate:** Update the plugin. Nothing in a project changes.

## 1.0.3

- Recovery starts when you ask it to carry the items a baseline review
  left for later forward, and on inherited codebases. With the A-files it
  shows the drafts of the new items and writes nothing until you say yes,
  even when you asked it to take defaults.

**How to migrate:** Update the plugin. Nothing in a project changes.

## 1.0.2

- Recovery offers four depths after the map: full only where change is
  coming, a baseline for every use case, a baseline for every use case with
  full ones where change is coming, or full for all. Each says what it costs
  to review; the recommendation still follows the size of the map.

**How to migrate:** Update the plugin. Nothing in a project changes.

## 1.0.1

- The migration skill recognizes the installed checks copied from 1.0.0,
  so a later format change can refresh them.

**How to migrate:** Update the plugin. Nothing in a project changes.

## 1.0.0

- Use case metadata moves to YAML front matter; Draft stubs are files with
  the body `Not written yet.`.
- The use case overview is `docs/use_cases.md`: an actor-goal table and
  Mermaid use case diagram (Mermaid 12.0.0 or later) generated from the use
  case files. It replaces the
  PlantUML diagram; scope and delivery order remain editable.
- Functional requirements use Role and Need columns; non-functional
  requirements and constraints use EARS statements.
- Entity attributes use business types from a closed list, with Meaning
  and Rules columns instead of storage details.
- Journeys use front matter and one Gherkin Scenario per file, with literal
  test data and comments naming the use cases.
- Each business rule has an Examples table with input columns and a final
  `result` column, covering both sides of its boundaries.
- Change records use front matter and four required sections: Context,
  Decision, Specification change and Consequences.
- Checks recognize earlier formats and stop with `OLD_FORMAT` and exit 5;
  the router names migration as the next step.
- Retired codes: `NO_START_END`, `NO_SYSTEM`, `LABEL_FORM`,
  `ACTOR_UNCONNECTED`, `USE_CASE_UNCONNECTED`, `SPEC_NOT_IN_DIAGRAM`,
  `NAME_MISMATCH`, `SPEC_PENDING`, `FK_NO_RELATIONSHIP`, `STORY_FORM`.
- The fifteenth skill, `up-migrating-spec-formats`, shows the mechanical
  plan and judgment work, preserves identifiers and Status, and waits for
  your approval before writing.

**How to migrate:** Update the plugin, then ask the agent: *Move the specs to the current formats.* It shows a plan, asks before writing, and makes two commits.

## 0.2.1

- The README is rewritten: what the skills do and why, install steps for
  Claude Code, Codex and other agents, a quick start, and the skills grouped
  into the chain and the side entries.

## 0.2.0

- Recovery: the change log is the alignment backlog. A new kind, Claimed but
  not built, holds what an old document promises and the code lacks; the
  decisions later, in change, aligned and dropped follow an entry, and only
  the coverage audit's report closes it. With the A-files, recovery drafts
  one AHEAD item per use case and writes them on the owner's yes.
- The ledger check refuses a dropped entry without its reason, an entry in
  change whose record is missing, and an aligned entry whose audit reports
  are missing or do not cover its use cases, and prints the backlog.
- The router prints the alignment count, hints when an entry is ready for
  its audit, and warns when an ability is done while its use cases still
  have open entries; it never blocks new work.
- Triage names the change log entry a change starts from and marks it in
  change; the audit lists the entries its report can close.

## 0.1.0

The first public release.

- Fourteen skills for specification-first development with use cases: a
  router that names the next step; project setup with rigor profiles and
  agent hooks; the requirements catalog; the entity model; the use case map;
  use case specifications; their review; implementation against an approved
  specification; tests derived from the specification; coverage audit;
  journeys across use cases; change triage; recovery of specifications from
  existing code; and splitting a specification set for several teams.
- Bundled scripts (Python 3.9 or later, standard library only) that validate
  specifications, read the project's state, check the finish of a change and
  audit coverage.
- Works alone or with the A-files in the same project.
