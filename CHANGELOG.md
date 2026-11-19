# Changelog

All notable changes to upspec. Versions follow semantic versioning.

## 2.1.1 (2026-11-19)

Fixes found by the review of 2.1.0.

- **No lost "later".** In a session nobody attends, a decision whose line could not be written is not marked as asked: the agent hears of it, and the next turn's end tries again.
- **Setup joins an `AGENTS.md` in more shapes.** One keep-in-step row already there no longer keeps out the other; a sample list inside a fence never receives the rows; a list written with asterisks gets its rows with asterisks. The index of `AGENTS.md` is read as the A-files' check reads it (no closing pipe needed; a File table is the index).
- **The deferred list keeps its records apart** when its last line has no newline.
- **Texts.** Setup's existing-structure reference no longer speaks of a length finding the check retired; the pairing contract names `ITEM_WITHOUT_DECISION`.

## 2.1.0 (2026-11-19)

Released with a-files 2.2.0, whose pairing text this plugin shares. "Later" no longer writes `AHEAD.md`, and setup reads `AGENTS.md` with or without an end of hot zone.

- **"Later" goes to upspec's own list.** A drift answered "later", attended or unattended, is recorded as a line in `up-deferred.txt` in the git folder and shown with the open work at session start. It never becomes an item in `AHEAD.md`, which the owner decides, and the record no longer says a person chose when nobody was asked. The question says where "later" records.
- **A missing use case noted while implementing** goes to the same list where the hooks are installed; without them it is named in the report and in the commit message.
- **Still items, on the person's word:** a change request accepted for later and a recovery entry written on a yes become AHEAD items and carry the `**Entered:**` line.
- **Setup joins an `AGENTS.md` in both forms.** With an end of hot zone, as before. Without one, the two keep-in-step rows are added and nothing is named in a hot zone; the rules section stands at the end of the file. The scripts find the A-files' index table anywhere in the file.
- **Pairing rows P1, P4 and P9** are reworded on both sides.

**What an upgrade asks of you:** update the plugin, then in each project run `scaffold_docs.py --update` from the new plugin and apply its plan: the rules block in your `AGENTS.md` or `CLAUDE.md` is the project's own copy, and until it is replaced it still tells agents to file a missing use case in `AHEAD.md`. A project wired by 1.x follows the update of 2.0.0 first. Items that earlier releases wrote into `AHEAD.md` on a "later" stay where they are; a-files 2.2.0's *Sort a full AHEAD* removes the ones you never chose.

## 2.0.1 (2026-11-17)

A text release: the install and upgrade steps are complete enough to follow without help. No script behaves differently; only the version lines change.

- **Upgrading from 1.x.** The README has the commands per tool to leave the marketplace `christian-orrala` for `christianorrala`, and the update of each project wired by an earlier release: the plan, `--apply`, what to remove by hand, and the line `No behavior change: none, tooling only.` that the commit guard reads.
- **Kiro CLI runs hooks only on its V3 engine.** With `--no-interactive` and no setting it picks V2, which runs none. The README, the manual and setup's hook references name the step: `kiro-cli settings chat.agentEngine v3`.
- **OpenCode needs a full copy of the plugin.** `opencode plugin add` fetches only `hooks/opencode`, and the module then finds no gate and stays silent. The README shows a clone of the repository and the absolute path to list in `opencode.json`.

**What an upgrade asks of you:** update the plugin; in Kiro, set the V3 engine if you have not.

## 2.0.0 (2026-11-17)

The plugin carries its agent hooks. Setup no longer wires hooks into a project, and a project wired by an earlier release is retired by `--update`. This changes how a project gets its hooks, hence the major version.

- **The hooks come with the plugin.** `hooks/hooks.json` serves Claude Code and Codex; `hooks/kiro/upspec.json` is a hook file for Kiro CLI; `hooks/opencode/` is a module for OpenCode. Each runs `hook_gate.py` from the plugin's setup skill and reads the project from the hook's event. The moments are the same four: session start, turn start, after an edit, before the stop.
- **Only where upspec is adopted.** The hooks act in a project whose `AGENTS.md` or `CLAUDE.md` carries the rules block. In any other repository, and outside git, they print nothing, exit 0 and write no file.
- **Turning them on.** Claude Code: with the plugin. Codex: install from the marketplace, then approve each hook once in `/hooks` (an unapproved hook is skipped without a word; after a plugin update, reinstall and approve again). Kiro CLI: copy the skill folders to `~/.kiro/skills/` and `hooks/kiro/upspec.json` to `~/.kiro/hooks/`; after-edit text reaches only the person. OpenCode: list `hooks/opencode` in the `plugins` array of `opencode.json`; the module ignores events of other projects. Seen firing on Claude Code 2.1.326, Codex 0.167.0, Kiro CLI 3.3.0 and OpenCode 2.3.0.
- **Setup writes no hooks.** `--hooks`, `--tool` and `--reason` are gone and exit 2 with a message that names the plugin's hooks. Setup copies no hook script and writes no `**Hooks:**` line.
- **`--update` retires an earlier release's wiring,** in the same all-or-nothing plan: only upspec's entries leave `.claude/settings.json`, `.codex/hooks.json`, `.agents/hooks.json` and `.kiro/hooks/upspec.json` (every other entry stays; a file that held nothing else is removed); an entry you adapted is named with its recorded reason and removed unless you `--keep` it; the hook-only copies (`hook_gate.py`, `hook_profiles.py`, `workflow_state.py`) leave `tools/specs/`, which keeps the check set where the team profile, the pipeline or the pre-push hook uses it, and otherwise `spec_data.py` with its reader; the `**Hooks:**` line goes. `.claude/settings.local.json` is named, never edited. Until then the plugin's gate stays silent in that project, apart from one line at session start that names the update.
- **An unattended session asks nothing.** With `CLAUDE_CODE_SESSION_ATTENDED=0`, or `UP_UNATTENDED=1` in any tool, the stop records an owner decision as later (an AHEAD item or a deferred line), sends the notes for the agent, and names what it recorded.
- **The A-files' note and findings come from the A-files plugin.** upspec's session start no longer opens with the note to say where things stand, and its stop no longer reports the A-files check. With both plugins installed, each arrives once.
- **`--emit auto`** renders for Codex when the environment has `PLUGIN_ROOT`, else for Claude Code. The `antigravity` profile is removed: the Antigravity CLI has no plugin hooks.
- **The root `plugin.json` declares no `$schema`.** Codex loads no plugin hooks from a plugin whose root manifest declares it. The other fields are unchanged.
- The commit hook, the pre-push hook and the pipeline are unchanged.
- **Install lines name the catalog `ChristianOrrala/agents`,** marketplace `christianorrala` (`/plugin install upspec@christianorrala`). The marketplace `christian-orrala` in `ChristianOrrala/plugins` still lists the plugin; to move, remove it and add the new one, then install again.

**What an upgrade asks of you:** update the plugin, then turn its hooks on in your tool as above. In each project wired by an earlier release, run `scaffold_docs.py --update`, review its plan and apply it; commit the result on its own. A teammate without the plugin no longer gets agent hooks from the repository; the commit hook and the pipeline still apply to everyone.

## 1.8.2 (2026-11-16)

A repair release. Three checks misread an ordinary project: one whose feature is about specifications, one session that builds several use cases, and a test runner whose failure line they did not know. On a project none of this touches, every command prints what 1.8.1 printed, apart from the new key below.

- **A folder named `spec` or `specs` is not always tests** (0057). Under `src`, `app` or `lib` it holds code: the spec-first guard, the finish check and the end-of-turn check now read it as code, also when `--code` points at the code root itself. RSpec's `spec/` at the root of a project or a package stays tests, helpers included. The guard prints the changed files it read as tests only because of such a folder, and when a rule's marker is only in such files the finish check names them (JSON: `markers.in_test_folders`).
- **A claim's scope is its own commits** (0058). At the end of a turn, a file of another use case counts against a Status raise only when it is uncommitted or in a commit that is the raised use case's work (a path or the message names it). In such a commit, a file whose use case the message names, a range such as `UC-001..UC-003` included, or a specification the commit creates, is that other use case's work. A session that writes several use cases and builds them one after another no longer trips it.
- **The end-of-turn note says what it found.** When files of other use cases are the only finding, it says so instead of "without its evidence", and never advises lowering a Status whose evidence is complete.
- **The guard check reads a failure word in brackets.** A line that starts with `(fail) name` or `[FAIL] name` reports that test's failure, so such a runner's caught break is logged as caught without `--expect`.
- **The A-files reader keeps a blocker that begins with "nothing".** Blocked by, Waiting on owner and Next step are empty only when they say nothing else; "nothing blocks it, but the ledger is late" now reads as written.

**What an upgrade asks of you:** update the plugin. In each project with installed copies, run `scaffold_docs.py --update`, review its plan and apply the agreed updates; it brings every copy in `tools/specs/` to 1.8.2. A project with code in a `src/.../specs/` folder may now see the guard ask for a specification behind it, as it should have before.

## 1.8.1 (2026-11-14)

A repair release. Reviews by another vendor's model found cases where 1.8.0 printed nothing, wrong data or a wrong answer in unusual projects: a legacy Windows code page, links, folders that cannot be read. Nothing changes on an ordinary project: there every command prints what 1.8.0 printed, apart from the new keys below (0056).

- **Output never ends in an encoding error.** Under a legacy Windows code page or a C locale, a character the console cannot write is written as its escape (`→`) instead of stopping the run; the model command prints its JSON there too.
- **A link that leaves the project is followed and marked** (0056). In the model's JSON, a file or folder read through a link whose real target is outside the project carries `outside_link` (`link` and `target`); the specification folder carries `docs_outside_link`, and each change-records folder is listed under `change_records.folder_outside_links`. A ledger's evidence path gives `place`: `project`, `outside` or `other_drive`, and names a project file reached through an alias of the root (a link, `/var` for `/private/var`) as `project`.
- **A link that cannot be resolved is unreadable, never absent.** In place of a specification file or folder, a change-records folder, a recovery ledger or a given file, it is reported as `UNREADABLE` with the link named. The same holds for a broken link or a folder that cannot be entered anywhere above a nested specification folder: the router exits 2 and never suggests setup.
- **What the method owns and cannot read stops the run; anything else is reported and passes.** The specification folder, its canonical folders and every `change-records` folder, when they cannot be listed or entered (mode 0400 included), are unreadable and stop the run. Any other folder under the specification folder that cannot be searched (a cache, `node_modules`, a build folder) is listed under the new JSON key `not_searched` of the model and the router, with a note on standard error; the exit code stays as in 1.8.0, `--strict` included.
- **The migration refuses to work past an unreadable owned file.** `migrate_formats.py plan` and `apply` read every text the method owns first; one that cannot be read (a broken link, not UTF-8, denied) stops them with verify's `UNREADABLE` line and exit 1, before anything is renamed or journaled. Verify names the same files.
- **Fixed in the model and the checks:** a folder link that repeated change records (33 times through a loop); one test file listed twice under two spellings of a folder on a case-insensitive file system; evidence paths that kept backslashes and drive letters; one unreadable file that hid an earlier format elsewhere; `unrecorded_changes.py --all --format json` printing nothing when one use case was unreadable; `spec_lint.py` and `use_case_map.py` ending in a traceback on an overview that is not UTF-8.

**What an upgrade asks of you:** update the plugin. In each project with installed copies, run `scaffold_docs.py --update`, review its plan and apply the agreed updates; it brings every copy in `tools/specs/` to 1.8.1. A project with a broken link or an unreadable folder where the method keeps its files, which 1.8.0 passed as absent, now reports it: repair the link or the permission.

## 1.8.0 (2026-11-13)

- A new command, `spec_data.py` in `up-0-navigating-spec-driven-work`, prints the whole model of a project as JSON for a program such as a dashboard: the rules block; every use case with its front matter, goal, trigger, actors, preconditions, steps, flows, rules, postconditions, citations and references into other bounded contexts; the requirements, entities and relations, journeys, change records, the recovery ledger and change log, the review reports and the A-files. Every element carries its file, line and fingerprint, and the output carries a schema number and the upspec version. A kind of file the project lacks keeps its key, empty, with `present: false`; a folder that exists and is empty is `present: true` with no items. A file or a folder it cannot read, an A-file or guideline file included, is listed under `unreadable` and the rest is printed, with exit 1. Beside a `spec_model.py` of another release, as an older copy kept in `tools/specs/`, it exits 3 with a message naming both releases and `scaffold_docs.py --update`. It writes nothing, decides no step and judges nothing (0055, AB-048).
- The state reader's JSON (`workflow_state.py --format json`) gives a stable code beside every mismatch and warning (`coded_mismatches`, `coded_warnings`), lists the dropped change log entries with their reasons as it lists the open ones (`alignment.dropped_entries`), and gives the use cases that deliver each ability (`tracking.abilities`). Every existing key is unchanged, and so is the text report but for the one new warning below.
- The shared parser also reads, as data: a review report's verdict lines, declines and scope; the recovery ledger row by row, with each row's state and code locations; a flow a journey's comment names after a use case id (`# UC-001 A15`); what a retired flow or rule says it moved to; and from the A-files, Next step, Next new work, an ability's Known limits and Evidence lines, and an AHEAD item's kind, state and Belongs to line. No check changes.
- The dashboard gives its evidence as data: `spec_dashboard.py --format json` prints the progress rows and one row per use case, each cell with the word the table prints, for the whole project in one call. `spec_dashboard.py`, `coverage_matrix.py` and `coverage_units.py` take `--tests` once for each folder that holds tests, and `coverage_matrix.py --all` and `coverage_units.py --all` cover every use case that is not Obsolete in one call. The tables and every existing output are unchanged (0055, AB-048).
- The impact command's JSON (`impact.py --format json`) types its answers: beside each group's sentences, `upward_items`, `sideways_items` and `downward_items` give the same items one for one, each with its kind, its two ends as addresses (with the flow or rule where there is one, such as `UC-004 A1` or `UC-002 BR-001`), its basis and where it was found, and each term its `term_kind`. The sentences and the text output are unchanged (0055, AB-048).
- `unrecorded_changes.py --all` answers for every use case in one call, each with its state (`compared`, `no_record`, `cannot_tell`, `unreadable`). **One exit code changes meaning:** for one use case, "no change record names this use case" now exits 4, apart from "cannot tell" (no git, nothing committed, a new use case), which stays 3 and wins when both apply. A pipeline or script that read exit 3 as "no record" reads 4 now (0055, AB-048).
- The lint reports at INFO a requirement whose Status is `Implemented` and that no use case links (`REQ_IMPLEMENTED_UNLINKED`), unless `FR_UNREALIZED` already reports it. An INFO changes no exit code, so a project that passes today still passes, `--strict` included (0055, AB-048).
- The state reader warns about an ability `in progress` whose use cases are all `Done`, where it warns about the other ability-status mismatches, with the code `IN_PROGRESS_ABILITY_DONE`: mark it `done`, or name the use case still to build. Its JSON gives `tracking.abilities_compared`, how many abilities it compared, so that nothing to compare can be told from everything in agreement. The pairing rule P2 says it, in the contract both products carry (0055, AB-048).
- Setup installs the model command into the project's `tools/specs/` with either set of installed scripts, and `scaffold_docs.py --update` and the migration add it where it is missing, so that a program can run the project's own copy (`python3 tools/specs/spec_data.py`). No check or hook runs it, and the hook gate does not require it (0055, AB-048).
- Run from a project's `tools/specs/`, the model command, the state reader, the lint and `unrecorded_changes.py` leave no bytecode cache (`__pycache__`) beside the copies.

**What an upgrade asks of you:** update the plugin. In each project with installed copies, run `scaffold_docs.py --update`, review its plan and apply the agreed updates; it brings every copy in `tools/specs/` to 1.8.0 and adds `spec_data.py`. If a script of yours reads exit 3 of `unrecorded_changes.py` as "no change record", read 4 instead.

## 1.7.2

- The session-start hook opens its context with one light note to the agent: before the first edit, say where things stand in four short lines (Finished, Remaining, Blocked by, Next step), or in one short line when the request already says exactly what to do. It goes to the agent only, never blocks or asks the owner, appears at session start only and counts inside the sixty-line budget (0053, AB-047).

**What an upgrade asks of you:** update the plugin. In each project with installed copies, run `scaffold_docs.py --update`, review its plan and apply the agreed updates.

## 1.7.1

- The short path for a small change keeps a `Draft` or `Reviewed` Status as the person set it and lowers only a later active Status (`Approved`, `Implemented`, `Tested`, `Done`) to `Reviewed` for the specification edit; up-1, up-7 and the manual now agree with the request-grants-the-slice rule.
- The bug light path describes the hook's one-time note to the agent and the commit with its `Fixes:` line that closes it; it no longer tells the agent to answer an end-of-turn question for the owner.
- The invention list says what stays unimplemented while a required behavior answer has not arrived: that behavior, unless the owner authorizes the recorded reading, while independent authorized work goes on.

## 1.7.0

- Use case section headings now match regardless of case, repeated spaces or a trailing colon; duplicate sections are reported. Flow and rule identifiers match regardless of case.
- Before stopping, the hook asks only about decisions the owner must make. Routine drift reaches the agent as notes to align or include in its handoff (0051).
- Install commands quote the plugin path, including paths with spaces.
- A request authorizes the work it asks for now under its stated conditions. Reserved approval requires an owner reply granting the named work; an agent's record cannot supply it (0048).
- The agent fixes validator and lint findings or reports a tool defect; acceptance still due is not a blocker (0049).
- A small change within one use case can follow a short path: update the specification, pin it with a test, implement it, run the validator and tests, and add a change-log line (0050).

**What an upgrade asks of you:** update the plugin. In each project with installed copies, run `scaffold_docs.py --update`, review its plan and apply the agreed updates.

## 1.6.0

A name or signature the specification leaves open is a technical choice: the agent picks one, lists it in the invention list and goes on; specified interface names bind, and the agent still asks about open behavior a user of the system observes.

When the owner explicitly requests behavior no use case covers, the agent names the gap, records the missing use case as open work, and does the requested work. Agents set Implemented and Tested when evidence exists; a person sets Approved and Done. Existing Draft and Reviewed use cases still go through their approval gate.

The stop hook advises answering "later" with the missing use case when the owner explicitly requested uncovered behavior in the session, recording the gap as open work.

## 1.5.0

Codes come with their titles. The state report and the hooks' open list and questions print `UC-001 (Book Repair)` instead of `UC-001`. A new rule 11 in the rules block asks the agent to do the same in its messages. `--update` brings the rule to a repository whose rules block is untouched. Files, commit lines, code markers and test names keep the bare identifier.

## 1.4.0

The skill numbers follow daily use. Triage, which you run before every fix, change or feature, becomes `up-1`, and setup, which you run once per project, loses its number. The state report no longer opens every session with cleanup, and it shows what is waiting.

| Old name | New name |
|---|---|
| `up-triaging-change-requests` | `up-1-triaging-change-requests` |
| `up-1-bootstrapping-spec-driven-projects` | `up-bootstrapping-spec-driven-projects` |

The old names stop working. A command, a prompt or a note of your own that names a skill by its old name needs the new one. The numbers now mean: 0 and 1 are the two entries (0 for the state, 1 for a change), 2 to 9 are the artifact chain in the method's order, and unnumbered skills are used when needed.

- **Cleanup leads only when it blocks.**
  - A format finding is the next step only when the use case overview cannot be written, today an `id` or `goal` written over several lines. A use case with no readable ID stays a step.
  - Every other finding goes on one "To clean (not blocking): ..." line. When nothing else is in flight, the report reads "Nothing in flight; N item(s) to clean."
- **The state report shows what waits.** With the A-files it prints the debt from `ACTIVE.md` and the Next up list from `AHEAD.md`, and its JSON carries them. After the reason it prints a `when:` line: no other task in hand, or a fix, change or feature on an existing use case, which goes to `up-1` first.
- **Triage is the daily entry.** It has two early exits: in a repository with no rules block, vision or specifications it says so in one line and stops, and for a change that alters no behavior (outcome 7) it gives the line `No behavior change: UC-NNN` and stops. Otherwise it adds one line with the change's size (local, wide, structural, or several changes), counted from what the change touches. The size is information only.
- **A repository that is not set up** runs the task outside the method: the router says so in one line and asks nothing. New behavior is scoped to a set-up project. The router also names "clean the specs" for the items on the to-clean line.
- **What normally follows.** Each skill of the chain ends with a short section saying what usually comes next. The state report wins when they disagree.
- **`--update` and the rules block.**
  - `scaffold_docs.py --update` replaces the rules block of your guideline file whole when it is exactly as a release wrote it (its profile, hooks, folder and other field lines aside, which stay yours). The plan lists it as `guideline:rules-block`.
  - A block you edited shows its diff and waits for `--replace guideline:rules-block` or `--keep guideline:rules-block`. Nothing is rewritten until you choose, and a keep is recorded in `tools/specs/upspec-installed.json` and offered again only when the block or the template changes.
  - The rest of the guideline file is never touched, and a project with no rules block gets none.
  - `known_scripts.json` recognizes the rules blocks released up to 1.3.0.
  - The dry run prints the integration branch line it will add, a guideline file with CRLF line endings keeps them, `--replace`/`--keep guideline:rules-block` without `--update` is a usage error, and a damaged `known_scripts.json` gives a plain error.
- **Hook scripts.** `hook_gate.py`, `hook_profiles.py` and `spec_first_guard.py` are shared scripts like the others. Their behavior is unchanged.
- **Evaluations.** None ran for this release: no new evaluation cases, no trigger reruns and no trials. The 1.3.0 scores below stay what they were, for 1.3.0.

**What an upgrade asks of you:**
1. Update the plugin, and use the new skill names (the table above).
2. In each project with installed copies, run `scaffold_docs.py --update` and read the plan. Untouched copies and an untouched rules block are replaced. Name every copy changed by hand in `--replace` or `--keep`, and an edited rules block as `guideline:rules-block`, then add `--apply`.
3. The rules block you keep keeps its old wording, including the old skill names it may mention; replace it when you want the new text.
4. Commit `tools/specs/` and the guideline file on their own.

## 1.3.0

The tools inform; they never stop the work. Every check reports what it found and lets the work go on, unless you ask for a strict run. The hooks ask one question per drift instead of blocking. A bug against a clear specification takes a light path, the guard check says what really happened, and a review keeps the warnings it missed before apart.

- **Nothing stops the work.**
  - Every check exits 0 when it ran, whatever it found: the findings are its output. With `--strict` it exits 1 on problems; the lint's `--strict` keeps its meaning. A file a check cannot read is the finding `UNREADABLE`, under the same rule.
  - Writers and listers still exit 1 when they cannot do their work, for example the overview writer refusing markers out of order.
  - The spec-first guard warns in every profile and on every branch. `--mode block` now behaves as `warn`.
  - The pipeline workflow and the pre-push hook report and let the work go on. A team that wants a strict pipeline adds `--strict` to a step's command.
  - The stop hook no longer holds the work. At the end of a turn it asks once per drift (a Status claim without its evidence, an open change record, code without a specification, a broken A-files shape): align now, at the end of the session, or later. "Later" becomes an AHEAD item when the project keeps the A-files, otherwise a line in the open-work list shown at session start. The same drift is not raised again in that session, and code without a specification is asked about once per change. A light-path fix is asked once, before its commit, like any code without a specification. It is committed with its note in the same session, so the fitting answer is "at the end of the session" (or "now"), never "later", which would add an item for work the commit closes. A fix written and committed in one turn, before any stop, is asked only while the change still holds that commit, as on a fix branch; on the integration branch it is not asked. Code that reaches the session through a pull or a merge is not asked. On Claude Code the question reaches the agent as the stop hook's block, returned once per new drift; the agent answers it, and the next stop goes through.
  - The loop guard is gone, since nothing blocks.
- **The guard check says what happened.**
  - It keeps the test output and gives one of four verdicts: `caught` (a failed test whose name holds both the use case and the element, in any common spelling, displayed names included), `crashed` (the output shows an error, not a failed assertion), `not caught` (the test still passed) or `unclear` (the output does not say). `invalid` stays for a test that fails before the break or times out.
  - It accepts every element of a use case: a rule, a flow, a step, a precondition or a postcondition. `--expect TEXT` serves runners that print no test names.
  - It runs the test with a terminal 500 columns wide, so a runner that fits its summary to the terminal keeps the error after a long test name, and it reads any exception a summary line names (pytest's `FAILED …::name - StopIteration` under `--tb=no` or `--tb=line`) as `crashed`.
  - Its log keeps the break's find and replace texts and fingerprints of the element and of the enforcing file. The finish check counts only the newest `caught` row per element and reports a row as stale when either fingerprint changed.
- **The light path.**
  - Triage writes a change record only for outcomes 2, 4, 5 and 6.
  - A bug against a clear specification (outcome 1) needs a failing test named after the use case and the element, the fix, the guard check of that element if you want its confirmation, and the note `Fixes: UC-012 BR-005` in the commit. The spec-first guard and the hooks read the note and do not report the change. A `Fixes:` line that names no use case, such as `Fixes: #123`, is not the note.
- **The foreign-key exception.** A foreign-key constraint added later, for a relationship the entity model states, is outcome 1 with no element, and it does not take the light path. It takes the destructive path of the schema procedure, with the owner's yes and a count of the rows that violate it; the model stays unchanged, and the commit carries `Fixes: UC-012`, naming the use case whose relationship it enforces.
- **Schema changes.** A schema change that adds or changes a business concept starts in the entity model, a key, a uniqueness constraint or a version column included. Only a change no flow can observe, an index or partitioning, is technical: triage classifies it as no behavior change, and it carries `No behavior change: UC-012` (or `none` and the reason).
- **Reviews.**
  - A warning that is new on text unchanged since the last review was missed before. The report lists such warnings in their own block, which the owner can decline in one pass, and the use case is not ready for Approved while one is open. Info findings never count. Every report lists what was declined, and a declined finding is not raised again.
  - One report per scope: `docs/reviews/<scope>-review.md`, overwritten at each review; git keeps the history. Audits stay numbered.
  - In solo, the review is a cold read, and its limit is stated: the same model catches sloppiness, not a misreading it shares.
- **A thin entity model in solo.** The model may hold only what the use cases written so far need, and grows with each one. It still exists before the first use case, and the vocabulary check is unchanged. The team profile keeps the full model.
- **Front matter.**
  - A value written over several lines is refused once, with what to do instead: write it on one line. For a goal, the message adds that a goal needing more than one line is usually two goals.
  - While a use case's `id` or `goal` is refused, `use_case_map.py` writes nothing (exit 1) rather than drop the use case or empty its goal. `--check` reports the refusal as `FRONT_MATTER` with its line. The state report lists the finding and names `FIX_FORMAT` as the next step, and its JSON gives the overview `current: false`.
- **Requirements.** The catalog skill gains two worked constraints, a budget and a mandated technology. The check is unchanged: a constraint may have any subject before "shall".
- **With the A-files.**
  - upspec reads an ability's status from its index row, with an old entry's Status line as fallback.
  - With a small A-files setup (`AGENTS.md` and `ACTIVE.md` only), upspec says nothing about abilities: setup adds the keep-in-step rows for abilities, and the map proposes abilities, only when the project keeps `ABILITIES.md`.
  - The hooks run the project's A-files check as a command and read its output. Two new pairing rows say what "later" writes into `AHEAD.md` and how the hook reads the check.
- **Tests.** An `IT` suffix marks a test file only on CamelCase names of the JVM languages.
- **The migration takes other formats.** Setup and the router's guidance send specifications in another format to the migration; the router's script reads only the specification folder, so it still names recovery when such files sit outside it. The migration's plan converts mechanically only the parts that match an earlier upspec format, and the agent converts the rest in the judgment pass, with the invention list and your yes before any commit. Recovery keeps the systems that have code and no specifications.
- **Known limits.** The end-of-turn question and the after-edit findings were seen live in Claude Code only; in the other tools they are rendered per tool and tested. The after-edit check runs on Edit and Write, so a use case written through a shell command is not checked until the next check. The validator still reports a use case whose headings use the manual's sentence case as missing sections. The guard check reads a caught break as `crashed` when the test's query throws its own error for a missing element (for example, Testing Library's `getByText` under Vitest or Jest); write that test with a query that does not throw and an `expect` assertion (in the example, `expect(queryByText(…)).toBeInTheDocument()`). The guard check runs the tests with a terminal 500 columns wide, so a project test that depends on the terminal's width can fail before the break and give `invalid`. An assertion message holding the words "syntax error" reads as `crashed` in every runner and mode. Under pytest, a parameter id that itself holds `] - ` hides a crash: a syntax error reads as `caught` under `--tb=no` and `unclear` under `--tb=line`, and an exception whose name ends neither in `Error` nor in `Exception` reads as `caught` under both; `-q` and the default `--tb=auto` read `crashed`. An id holding `] - File "` reads every failure as `crashed`, a failed assertion too.
- **Evaluations.** The cases this release changed ran on 1.3.0 **once each**, so every score is a single run and noisy. Behavior cases, with the plugin and without: up-6 e1 to e4 (e4 new: the missed-before warnings), 1.00, 1.00, 1.00 and 0.86 against 0.86, 0.80, 0.75 and 0.57; up-1 e2, 0.75 against 0.25; up-8 e2, 1.00 against 0.40; triage e1 (the light path), 1.00 against 0.50. With the plugin only: up-7's three trigger cases fired and its two near-miss cases held. The two misses were one grader each: up-1 e2 did not say that an agent's review only comments, and up-6 e4 did not set the missed-before warning apart in its reply, though its saved report did. Not rerun: every other case, among them the near-misses of up-3, up-5 and triage that expect up-7, and up-1 e5, whose workspace changed but not its prompt or graders. These cases check that a skill fires and follows its conventions; they do not measure whether it helps.

**What an upgrade asks of you:**
1. Update the plugin.
2. In each project with installed copies, run `scaffold_docs.py --update` and read the plan. The copies 1.2.0 installed are recognized and replaced; name every copy changed by hand in `--replace` or `--keep`, then add `--apply`. For the team profile, `--replace ci:specifications` takes the reporting workflow; a kept 1.2.0 workflow still runs, and its `--mode block` now warns.
3. Nothing blocks any more. If your team relied on a failing pipeline or push, add `--strict` to the steps that should fail. For the push: in the pre-push hook setup installed, add `--strict` to its `status_claims.py` line. A line you added to your own pre-push hook by hand needs only `--strict` when it came from 1.2.0 (it ends `|| exit 1`); the 1.3.0 line ends `|| true`, so add `--strict` and replace `|| true` with `|| exit 1`.
4. Guard results logged before 1.3.0 hold no fingerprints, so the finish check reports them as stale. Run `guard_check.py` again for each element it names.
5. Review reports with the old numbered names are still read: the next review compares with the newest numbered report and saves its own under the name of its scope. Nothing needs renaming.
6. With the A-files, an old ability entry's Status line is still read as a fallback; the status lives in the index row.
7. With an A-files small setup, upspec 1.2.0 notes every use case as named by no ability: upgrade to 1.3.0, which says nothing about abilities without `ABILITIES.md`.
8. The rules block setup wrote into your guideline file keeps its wording. New setups add a sentence on the `Fixes:` note; add it by hand if you want it in an existing block.
9. Commit `tools/specs/`, the wiring and the workflow on their own.

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
