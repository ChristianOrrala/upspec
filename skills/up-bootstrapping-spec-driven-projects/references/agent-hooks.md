# Agent hooks

The plugin carries the hooks; setup writes none. The person turns them on in
their tool. What each tool delivers is in `agent-hook-examples.md`.

## Contents

- Where the hooks come from, and when they act
- The four hooks and results
- Turning them on, tool by tool
- A project wired by an earlier release
- Integration branch
- Status claims, decisions and notes
- Unattended sessions
- Updating installed copies
- Seeing each hook fire
- Other tools and limits

## Where the hooks come from, and when they act

The plugin ships a hooks file for Claude Code and Codex, a hook file for Kiro
and a module for OpenCode. Each runs `scripts/hook_gate.py` from the plugin's
own skill folder; nothing is copied into the project, so a plugin update
changes the hooks in every project at once. The gate reads the project from the
hook's event.

The hooks act only where the project's guideline file (`AGENTS.md` or
`CLAUDE.md`) carries the rules block "Working from specifications". In any
other repository, and outside git, a hook prints nothing, exits 0 and writes
no file. A teammate without the plugin gets no agent hooks; the commit hook and
the pipeline still apply to everyone.

The A-files plugin sends its own session-start note and its own findings at the
stop. This gate sends neither, so a project with both plugins gets each once.

## The four hooks and results

| Moment | Gate command | What runs |
|---|---|---|
| Session starts or resumes | `hook_gate.py session-start` | A session snapshot, the specification state, next step and open-work list |
| After a file write or edit | `hook_gate.py after-edit` | Validation of the edited use case specifications, as information |
| Before the agent reads a prompt | `hook_gate.py turn-start` | The open-work list, only when it changed; always exits 0 |
| Before the agent ends its turn | `hook_gate.py before-stop` | Owner decisions asked once; routine notes handed to the agent once |

The tools inform; they never stop the work. No hook blocks, refuses or keeps
the agent working, except to deliver decisions and notes once at the end of a turn.
One gate owns the policy. Each firing uses one view of the change and runs
the checks in one process; a failed record does not prevent checking others.
The open-work list reads git paths and specification artifacts only, never source files or the finish check.
The hook file selects the moment and an output profile (`--emit auto` is
`codex` when the environment has `PLUGIN_ROOT`, else `claude`), never
reimplements a check.

| Internal result | Meaning | Delivery |
|---|---|---|
| 0 | Pass | Session and turn-start text becomes context where supported |
| 1 | Warn | Information, never blocking; after an edit the findings reach the agent as context where the tool allows, elsewhere they are shown where a warning channel exists |
| 2 | Ask | Only at the stop: owner questions and/or agent notes, delivered by continuing the agent's turn once; at any other moment rendered as a warning |
| 3 | The gate could not run | Never blocks; shown where the tool permits a warning |

These are the gate's internal results, not universal shell exit meanings.
`--emit raw` (the default) returns them directly; a named profile renders
what its tool accepts. The profiles live in `scripts/hook_profiles.py`,
including capabilities and message caps. An unavailable warning channel
cannot be created by changing an exit code. See the examples for the limits.

Each firing logs its moment, internal result and base in `up-hooks.log` in
the git folder (`git rev-parse --git-path up-hooks.log`). Stop entries name the baseline (`snapshot` or `HEAD`) and the open-list size.
Turn-start failures log a reason, print nothing and always exit 0.
A shortened message points to the full text in `up-hooks-report.txt` there;
that report is replaced the next time output is shortened. If it cannot be
saved, the shortened message says so.

## Turning them on, tool by tool

The person switches the hooks on, in the tool. The agent never switches its
own hooks on and never bypasses or widens permissions.

| Tool | Turn them on | What to know |
|---|---|---|
| Claude Code | Install the plugin; its hooks load with it. | Hooks fire in every repository you open; the gate stays silent where the rules block is absent. |
| Codex | Install the plugin from the marketplace, then approve each hook once in `/hooks`. | An unapproved hook is skipped without a word. Codex copies the plugin at install: after a plugin update, reinstall it and approve again. |
| Kiro CLI | Copy the skill folders of the plugin to `~/.kiro/skills/` and `hooks/kiro/upspec.json` to `~/.kiro/hooks/`; trust the workspace. | The hook file calls the gate in `~/.kiro/skills/up-bootstrapping-spec-driven-projects/`; without it, it does nothing. After-edit text reaches only the person, not the agent. Hooks run only on Kiro's V3 engine (`kiro-cli settings chat.agentEngine v3`). |
| OpenCode | List the `hooks/opencode` folder of a full copy of the plugin (a clone of its repository) in the `plugins` array of `opencode.json`, in the project or globally. | The module finds the gate beside it, in the copy's `skills/`, and ignores events of other projects. `opencode plugin add` fetches the folder alone, without the gate, and the hooks stay silent. |
| Antigravity CLI | Not supported: it has no plugin hooks. | The commit hook and the pipeline still apply. |

## A project wired by an earlier release

Releases before 2.0.0 copied the gate and its scripts into `tools/specs/` and
wrote the tool's hook file in the project. With the plugin's hooks also on,
every hook would fire twice, so while `tools/specs/hook_gate.py` exists the
plugin's gate stays silent except for one session-start line: run
`scripts/scaffold_docs.py --update` to retire the old wiring.

1. Run `scripts/scaffold_docs.py --update --root DIR` without `--apply`. The
   plan lists every step: each entry removed from `.claude/settings.json`,
   `.codex/hooks.json`, `.agents/hooks.json` or `.kiro/hooks/upspec.json`
   (only entries that run `tools/specs/hook_gate.py`; every other entry, key,
   order, indentation and character stays; a file that held nothing else is
   removed, an emptied `hooks` key too), each hook-only copy in `tools/specs/`
   that goes, and the `**Hooks:**` line of the rules block. The bundle stops
   recording the wiring. The plan ends with one line saying that the plugin
   now carries the hooks.
2. After `tools/specs/` is updated, it holds the check set when the project uses
   it (team profile, the pipeline job or the pre-push hook) and otherwise only
   `spec_data.py` and its reader `spec_model.py`.
3. An entry the owner adapted is still upspec's: it calls the gate this update
   removes. The plan names it with its recorded reason and removes it;
   `--keep wiring:<moment>` keeps it. An entry changed by hand, and a changed
   copy, wait for `--replace NAME` or `--keep NAME` (`wiring:<moment>` for an
   entry; moments are `session-start`, `after-edit`, `before-stop` and
   `turn-start`). Unreadable JSON or an undecided item prevents every write.
4. `.claude/settings.local.json` is personal: the plan names an upspec entry in
   it and never edits it.
5. Show the plan, apply it after the person's yes, and commit the result on its
   own.

## Integration branch

The gate resolves the base in this order:

1. `--base REF`;
2. `UP_BASE`;
3. `git config up.base`;
4. `**Integration branch:** <name>` in the guideline's rules block;
5. detection.

Confirm the integration branch with the person. It is where the feature
will be integrated, which may differ from a deployment branch. Setup proposes
the shared line from detection only. A set environment or git-config
override stays local: setup names it and proposes no shared line. Add the
line by hand if the team should share that choice. `--no-integration-line`
declines the proposal while accepting other setup or update work. When
detection finds no branch, setup prints a note; add the line by hand.

Detection considers each remote's default branch and `main`, `master`,
`dev`, `develop`, then those local branches. For each candidate it counts
the commits HEAD has that the candidate lacks, and chooses the smallest
count, with candidate order breaking ties.
A named branch is tried locally and on every remote; a remote-qualified ref
or commit is used as given. The current branch's local ref is excluded
unless it is the only candidate. The comparison starts at the merge base.
An invalid explicit base reports its source with result 3; with no detected
base, only uncommitted changes count. Committed pins and tracking warnings
compare against HEAD when it exists, while the header still names the base
as `none`. The log names the selected ref and its source. Use an override when detection does not describe the change.

## Status claims, decisions and notes

Session start records each use case's Status by id and HEAD in its own
git-folder file, `up-session-<key>.json`. The key is the first sixteen hex
characters of the session id's SHA-256, or `none` without an id. Each file
holds one session's baseline and cache, written by an atomic replacement
without a lock. A resume keeps its baseline; after each write pruning targets
the eight newest files by modification time. Files younger than one minute
are retained even above the target. A pruning candidate is renamed aside,
then its device, inode and modification time are compared with the selection.
A match removes the renamed file. A refreshed file is restored with a hard
link, which preserves a newer file already at the session name; the renamed
copy is then removed. Temporary files older than one day are cleaned up. Each worktree keeps its own snapshots. If turn
start finds no slot, it records a real snapshot before the agent acts. A null HEAD always means that the
repository had no commit yet, including when no use cases existed then.
An interrupted temporary write never prevents another session from saving.
A write failure is logged and never changes the session hook's result.

At the end of a turn the stop looks for drift: a Status raised without its
evidence, an open change record, behavior code changed without a
specification. It checks a Status raised to
Implemented or above against that snapshot, or against HEAD without one. It considers working-tree changes
(including untracked files) and local commits made after the snapshot that
are on no remote. Pulled work is excluded. A checkout outside the snapshot's
history falls back to HEAD. A rename alone is not a claim because use cases
are keyed by id.

Implemented needs a ready finish check. Tested and Done also need every
flow and rule named by a test. Open records select the units when they cover
the use case; otherwise the whole use case is checked, including a raise
already committed during the session. A missing piece of evidence is a
drift, with the move and the problems: add the evidence, or restore the
previous Status and tell the person what remains. A path naming an uncovered
use case counts only when it belongs to this session's changes; earlier spill
warns. An open change record is a change record changed in this change and
still present. Code changed without a specification is read as the
spec-first guard reads it: behavior code outside the specification folder,
tests and `tools/specs/` excluded, with no specification change, no
`No behavior change:` line and no `Fixes: UC-XXX` note in the change's commit
messages. The note counts once it is in a commit message. A light-path
fix is noted once before its commit. The agent commits it with the `Fixes:`
note in the same session; no scheduling question is needed. A fix written
and committed in one turn is noted only while the change still holds that
commit (a fix branch); on the integration branch, where the base moves with
the commit, it is not noted. Code that reaches the session through a pull or
a merge is on the base and is not noted. Specification
errors are never a drift at the stop. The early migration notice still warns
at session start and at the stop.

Each drift is a decision or a note. A decision is a
Status only a person sets (`Approved`, `Done`) that the change sets or relies
on, or work the owner reserved for approval. Unsupported `Implemented` or
`Tested` claims, open change records and code without a specification are
notes. The gate uses the claim's Status and explicit
reserved-approval metadata; it never infers approval from prose or a label.

Each new decision asks the person once: align now, at the end of the session,
or later. Now means align it in this session; end of the session means leave
it and remind the person once at session end; later runs the item's
`hook_gate.py later TEXT` command, which the message gives with the plugin's
path. That command appends to `up-deferred.txt` in the git folder, shown as
open work at session start. It never writes `AHEAD.md`: with the A-files,
that file is entered on the owner's decision, and he may make an item of a
deferred line when he sees it. A drift recorded before is not recorded again.

Notes go to the agent as one list: the records out of step and what aligns
each. It explicitly says none needs the owner, and asks the agent to align
them now or list them in its handoff within the current task's authorization.
It offers no now / end of session / later choices. For an explicit request
for uncovered behavior, record the missing use case as open work directly
with `hook_gate.py later TEXT`; no owner question is needed.

Both kinds use result 2 on the existing before-stop channel, continuing the
agent's turn once to receive the message. A mixed stop combines the decision
question and notes in that one message. The result's historical name is
`ASK`; notes do not ask the owner anything. The hook never forces alignment.
The snapshot's `asked` list remembers both kinds by key, so neither is sent
twice in a session; a new session can receive them again. If the git folder
cannot be written, a temporary file remembers them (removed after a day
untouched); if neither can be written, the stop only warns. With no new
drift, it prints nothing and passes.

The open-work list holds open records, changed use cases' finding counts and
first error, raises against the change's base, and broken use cases at
Reviewed or above marked "a problem at push". Its instruction treats these
as work in progress: fix an item only when it belongs to the current task; a
use case is marked Implemented or Tested once its items are clean, and the
push check reports the rest. Fifteen items are shown, then a count of omitted items.
Session context stays within sixty lines, keeping the next-step tail.

At turn start, a digest suppresses unchanged lists. When a shown list
empties, "Nothing is open now." is delivered once. Validation is reused by
content digest, including its specification dependencies. Completed cache
updates are saved even when the shown list is unchanged; a capped run saves
its completed entries without advancing the shown digest. Computation runs
in a daemon thread with a three-second cap to limit per-prompt cost. A
failure or timeout produces no output and always exits 0. The hook's eight-second
timeout includes stdin, computation and startup overhead.
Unsupported tools
receive the list at session start only. After-edit feedback contains only
findings the edited file can resolve: cross-file requirements, mechanism
vocabulary and another artifact's recognition errors stay in the open list.
An edited use case in an earlier format still warns with the migration notice.

A drift is known by its kind and subject (the use case and its new Status,
the record's path, the change that code without a specification belongs to,
known by the name of its base and the current branch), never by its problem text, so
changed line numbers, a count that grows, more code in the same change, more
commits or pushes on the same branch, or a shorter problem list do not send
again, and a new record of the same kind is sent once. A
base with no name is known by its commit. Without a session id both kinds are
remembered under one shared slot. Report what remains rather than inventing
specification content.

## Unattended sessions

A session with nobody present cannot answer a question. With
`CLAUDE_CODE_SESSION_ATTENDED=0`, or `UP_UNATTENDED=1` set for any tool, the
stop does not ask. It records each owner decision as later, the way the `later`
command does (a line of the deferred list, never an `AHEAD.md` item), once per
session through the same memory, and sends only the notes for the agent with one
line naming what it recorded. With no notes it sends nothing. Other tools are not
guessed: set `UP_UNATTENDED=1` where a tool runs without a person.

## Updating installed copies

Run `scripts/scaffold_docs.py --update --root DIR` from the new plugin to
review the plan; add `--apply` only after approval. The plugin's state reader and
router show an advisory update notice with both versions and this command.

`tools/specs/upspec-installed.json` records package baselines and kept
fingerprints. The plan classifies scripts as current, untouched, kept, changed
by hand or missing. Current and kept copies stay; untouched copies refresh;
missing copies are added only where the check set is in use. For every
changed-by-hand script, read the diff and choose `--replace NAME` to take the
package copy, or `--keep NAME` after porting the customization onto this
release. A kept customization needs a fresh decision at the next release; the
old baseline is shown for context. Undecided items prevent every write,
including otherwise safe script updates. Resolve the whole plan, approve,
apply, then commit on its own. Retiring an earlier release's hooks uses the
same plan, as described above.

Missing or mixed siblings of the gate in the plugin make it return result 3
naming `scaffold_docs.py --update`; they never block a stop. If `hook_profiles.py`
itself cannot load, the gate logs that failure and exits 0 with no output.

## Seeing each hook fire

Turned on is not seen. Start a new session in an adopted project with the
hooks on, and check the tool's behavior and the git-folder log:

1. **Session state:** ask for the next step. The log shows
   `session-start exit=0` and the answer matches the state report.
2. **Specification check:** temporarily give a use case an invalid Status,
   then restore it. The log shows `after-edit exit=1`. Confirm the findings
   reach the agent as context, or the person, as the tool's row in the
   examples states, and that the agent goes on with its task.
3. **Open work:** submit a prompt after changing an open item; confirm the
   list reaches the agent. An unchanged list prints nothing; an emptied one
   is announced once. Check `turn-start exit=0`.
4. **Decisions and notes:** raise an Approved use case to Implemented without
   its evidence. The log shows `before-stop exit=2`, and the agent receives
   a note to align or include in its handoff, with no owner question. End
   another turn: `before-stop exit=0`, with no repeated note. Restore the
   Status. Raise it to Done without its evidence: the agent asks the person
   once, with the three scheduling choices. Restore the Status again.

The log records internal results, which can differ from the command's exit
code. Undo all proof edits. A hook that never logs a line was usually not
approved or not enabled (Codex in particular), or the project does not carry
the rules block.

## Other tools and limits

A tool without hooks, or without a profile, has none. Additional profiles are
planned ideas, listed in the examples. Never substitute session-end for
before-stop; session-end cannot ask the person anything. The commit hook and the
pipeline report and pass unless the team added `--strict`.

Hooks provide feedback within the tool's sessions. Keep the commit hook and
the team pipeline for everyone. Hooks never approve a specification, and a
passing finish check still needs a person to read the report.
