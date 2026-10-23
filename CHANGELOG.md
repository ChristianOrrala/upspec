# Changelog

All notable changes to upspec. Versions follow semantic versioning.

## 1.2.0

Claims, not progress. The stop hook no longer blocks work in progress. It blocks only when the session raised a use case to Implemented or Tested without the evidence a script can check. The agent hears what is still open as information, and the push becomes the hard gate.

- **The stop blocks only on a claim.**
  - At session start the hooks take a snapshot of each use case's Status.
  - The stop blocks when this session raised a use case to Implemented or above without its evidence: the finish check on the whole use case (or on the open change record that covers it), and for Tested a test naming every flow and rule.
  - Only the session's own raises count, in the working tree or in local commits. A pull, a merge of remote work, or a teammate's commit never makes a claim.
  - Specification errors and open change records no longer block at the stop, and the stop no longer warns at every turn during specification work.
  - Unpushed commits on the integration branch no longer turn a design session into implementation.
- **The open-work list.**
  - At session start, the state report ends with a short list: the open change records, the changed use cases with their errors, the use cases raised in the change, and those at Reviewed or above that would fail at the push.
  - Its heading says these are work in progress: fix one only when it belongs to the current task.
  - A fourth hook moment, `turn-start`, repeats the list when it has changed, and never blocks or delays a prompt. It is wired for Claude Code, Codex and Kiro CLI; Antigravity CLI has no such event and gets the list at session start only.
- **The push is the hard gate.**
  - The team pipeline now runs on every push as well as on pull requests. It checks the same claims (`status_claims.py`) and runs spec lint with `--gate`: findings in a Draft use case warn, and those at Reviewed or above fail.
  - The spec-first guard blocks on pull requests and on pushes to the integration or default branch, and warns on other branches.
  - `scaffold_docs.py --pre-push` installs an optional pre-push hook with the same check. It is written only to a hooks folder inside the repository, never into an existing `pre-push`, and a check that cannot run lets the push through.
  - The team profile now installs `status_claims.py` and the finish-check helpers with the check scripts.
- **The finish check's scope.**
  - A changed file that is not part of the change is a warning, not a problem.
  - At the stop, a file this session changed whose path names a use case the change does not cover is still a problem.
- **One answer for what a file is.**
  - Every script asks one classifier. A file named after a use case outside the use case folder is never a use case, so review reports named `UC-…-review-N.md` are no longer validated as use cases.
  - A file in a subfolder of the use case folder is no longer a use case to the after-edit check.
  - A README in the use case folder no longer counts as a specification change for the spec-first guard.
  - The state reader no longer accepts a `change_records` folder; the convention is `change-records`.
- **After an edit.** The check reports only findings about the edited file. A finding that depends on another file (a requirements link, the entity model) goes to the open list.
- **Session state.** The hooks keep one small state file per session in the git folder, written atomically, with no lock.
- **Updates.** `--update` adds the `turn-start` entry to each tool's wiring, brings the pipeline workflow under the name `ci:specifications` (a hand-changed or unrecorded workflow needs `--replace` or `--keep`), and offers the pre-push hook.
- **Seen firing** on Claude Code 2.1.309, Codex 0.159.2, Kiro CLI 2.33.1 (V3 engine) and Antigravity CLI 1.4.4 (trial 05).

**How to migrate:**
1. Update the plugin.
2. In each project with installed copies, run `scaffold_docs.py --update` and read the plan. Name every copy changed by hand in `--replace` or `--keep`, including a hand-patched `change_view.py`, then add `--apply`.
3. Accept the new `turn-start` entry in your tool's wiring. Codex asks you to approve the new hook in `/hooks`.
4. For the team profile, decide `ci:specifications`: `--replace` takes the new workflow, `--keep` keeps yours.
5. Optionally run `scaffold_docs.py --pre-push --apply`.
6. Commit `tools/specs/`, the wiring and the workflow on their own.

## 1.1.0

Portable agent hooks. The hooks now run as one process that builds one view of the change. They find the branch a change is integrated into, and each tool gets output in the form it reads: Claude Code, Codex, Antigravity CLI and Kiro CLI.

- **Faster stop hook.** One view per firing: the file list and the marker search go through git, untracked files included, and each source file is read at most once. On a generated repository the size of a large project (about 9,000 files and 67 MB, five open change records), the stop hook took about 51 s with the 1.0.4 copies and about 4 s with these, with the same result.
- **The integration branch.**
  - The base is `--base`, then `UP_BASE`, then `git config up.base`, then a new rules-block line `**Integration branch:** <name>`, then detection.
  - Detection looks at each remote's default branch and `main`, `master`, `dev` and `develop`, on any remote, not only `origin`, then the local branches. It picks the one with the fewest commits that HEAD has and it lacks.
  - Setup proposes the line from detection, and a personal override stays local.
  - Detection can now find a base where 1.0.4 found none, for example a repository whose only integration branch is `dev`. A feature branch on an unpushed local branch takes that local branch.
- **Each tool gets its own output.** `hook_gate.py <moment> --emit claude|codex|antigravity|kiro`. A configuration without `--emit` keeps 1.0.4's exit codes and output.
- **Setup writes the wiring.**
  - Run `scaffold_docs.py --hooks --tool <tool>`, review the plan, then `--apply`.
  - It merges only its own entries, keeps everything else in the file, and shows a diff before it writes.
  - It refuses to add an entry for a moment that another entry or a 1.0.x adapter already covers, until you name that moment in `--replace wiring:<moment>` or `--keep wiring:<moment>`.
  - Each tool's wiring was seen firing on Claude Code 2.1.307, Codex 0.159.2, Kiro CLI 2.33.1 (V3 engine) and Antigravity CLI 1.4.4.
- **Specifications are checked at the stop.**
  - Changed use case files are validated each time the agent ends its turn.
  - During specification work, errors warn. Once implementation files change, they block.
- **What counts as implementation.** Edits to the guideline file and to the root A-files no longer start the finish check, and the scope audit groups the A-files as tracking.
- **Deleted files.** A deleted file belongs to the change when its path names the use case, when it carried the use case id at the base, or when the change record names its exact path.
- **A new loop guard.**
  - The stop hook gives up, with "stop and report these to the person", after three blocked stops with no fall in the number of problems, or at six blocked stops in a row.
  - The give-up comes once.
  - A problem keeps its identity when only its line number moves.
  - Codex no longer turns the second block into a message; the cap ends a stuck agent in every tool.
- **Updating installed copies.**
  - `scaffold_docs.py --update` sorts each copy in `tools/specs/` as current, untouched, kept, changed by hand, or missing. It replaces the untouched ones and shows a diff for each copy changed by hand.
  - It writes nothing until each of those is named in `--replace` or `--keep`.
  - A bundle file, `tools/specs/upspec-installed.json`, records what setup wrote.
  - The migration skill uses the same sorting, and replaces no script while a copy changed by hand is undecided.
- **An update notice.** The state reader, run from the plugin, says in one line when the copies in `tools/specs/` are older than the plugin.
- **A mixed set is caught.** Every installed script carries `UPSPEC_VERSION`. The gate answers "could not run", naming `--update`, when its siblings come from another release.
- **Submodules.** The hooks and the default checks no longer read submodule contents. A `--code` or `--tests` folder inside a submodule or another repository is still searched as in 1.0.4.
- **Tool notes.**
  - Kiro CLI runs the hook file only on its V3 engine: `kiro-cli settings chat.agentEngine v3`, or `kiro-cli chat --v3`.
  - Antigravity's after-edit check is not wired, because on 1.4.4 nothing from it reaches the agent; the stop carries the specification check.
  - Codex runs project hooks only after you trust the folder and approve each hook.

**How to migrate:**
1. Update the plugin.
2. In each project with installed copies, run `scaffold_docs.py --update` and read the plan. Name every copy changed by hand in `--replace` or `--keep`, then add `--apply`.
3. Run `scaffold_docs.py --hooks --tool <tool>` to bring your hook entries under setup. Name each moment that a 1.0.x adapter or a hand-made entry covers in `--replace wiring:<moment>` or `--keep wiring:<moment>`.
4. Accept the integration-branch line the plan proposes, or keep the branch local with `git config up.base <branch>`.
5. Commit `tools/specs/` and the wiring on their own.

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
