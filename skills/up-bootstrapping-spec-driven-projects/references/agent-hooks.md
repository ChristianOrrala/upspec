# Agent hooks

The agent prepares the hooks; the person approves and enables them. Generated
files and each tool's delivery limits are in `agent-hook-examples.md`.

## Contents

- The four hooks and results
- Generate, review, approve
- Integration branch
- Status claims and the one question
- Updating installed copies
- Proving each hook
- Recording what was wired
- Other tools and limits

## The four hooks and results

| Moment | Gate command | What runs |
|---|---|---|
| Session starts or resumes | `hook_gate.py session-start` | A session snapshot, the specification state, next step and open-work list |
| After a file write or edit | `hook_gate.py after-edit` | Validation of the edited use case specifications, as information |
| Before the agent reads a prompt | `hook_gate.py turn-start` | The open-work list, only when it changed; always exits 0 |
| Before the agent ends its turn | `hook_gate.py before-stop` | One question for the person per drift, each asked once per session |

The tools inform; they never stop the work. No hook blocks, refuses or keeps
the agent working, except to ask the one question at the end of a turn.
One gate owns the policy. Each firing uses one view of the change and runs
the checks in one process; a failed record does not prevent checking others.
The open-work list reads git paths and specification artifacts only, never source files or the finish check.
The tool configuration selects the moment and an explicit output profile,
never reimplements a check or guesses the tool from environment variables.

| Internal result | Meaning | Delivery |
|---|---|---|
| 0 | Pass | Session and turn-start text becomes context where supported |
| 1 | Warn | Information, never blocking; after an edit the findings reach the agent as context where the tool allows, elsewhere they are shown where a warning channel exists |
| 2 | Ask | Only at the stop: the questions for the person, delivered by continuing the agent's turn once; at any other moment rendered as a warning |
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

## Generate, review, approve

1. **Generate:** run `scripts/scaffold_docs.py --hooks --tool <tool>` from
   the installed skill, targeting the project with `--root DIR`. Tools with
   profiles are listed in the examples. Without `--tool`, `--hooks` copies
   scripts only. The dry run writes nothing: it proposes the scripts in
   `tools/specs/` and the project's hook file, with a full unified diff of
   each wiring file that would change.
2. **Review:** read that plan against the repository's existing hooks, the
   installed tool version, the layout and conflicts. Check that a real event
   exists for each moment and that the profile can deliver its result. Adapt
   anything that does not fit, and tell the person why. When keeping an
   existing adapted moment, pass its reason with
   `--keep wiring:<moment> --reason TEXT`.
3. **Approve:** show the final plan and obtain the person's approval before
   running it with `--apply`. The tool's own trust prompt still switches the
   hooks on. The agent never switches its own hooks on or widens permissions
   to write or trust the settings. Preparing files does not replace trust.
4. Prove each hook below, then record only what was seen firing. If the
   person enables hooks later, leave these proof steps for the next session.
5. Commit the copied scripts, configuration and record on their own before
   a behavior change; otherwise setup files appear in that change's scope.

Generated commands change to the git root and check that the gate exists
before invoking it. A missing gate must not block. Profiles handle output
inside the gate, so setup needs no separate adapter. The example blocks are
what setup generates for an empty project.

Setup merges only its own entries, preserving other settings and hooks.
It preserves indentation, key order, Unicode and the final newline; inline
layout may be normalized, so inspect the full file diff. A file that cannot
be read as plain JSON (including JSON with comments) is refused.

Existing unrecorded or customized entries, including legacy adapters, cover
their moment: setup will not add a duplicate. A command naming a repository
script that calls the gate also covers its moment. A partial generated set also
needs a decision. Plain `--update` points out unrecorded wiring and the command
to bring it under setup. After replacement, the plan names files left behind
that the person may delete; setup never deletes them. Local settings are scanned where the tool loads them,
but setup never writes that read-only configuration: keep its moment or
remove its entry by hand before requesting replacement.

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

## Status claims and the one question

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
specification, a broken A-files shape. It checks a Status raised to
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
fix is no exception before that: its uncommitted code is asked once at the
end of the turn, like any other, and the question says which answer fits.
The fix is committed with its note in the same session, so the person
answers "at the end of the session", or aligns it now; "later" would add an
item for work the commit closes. The question is asked before the commit,
so a fix written and committed in one turn, before any stop, is asked only
while the change still holds that commit (a fix branch); on the integration
branch, where the base moves with the commit, it is not asked. Code that
reaches the session through a pull or a merge is on the base, not in the
change, and is not asked. A broken A-files
shape is what the project's own `tools/check_tracking.py` reports, run as a
command with `--strict` (without it for an earlier check that does not know
the option): exit 1 and its `path:line: ERROR CODE: message` lines are the
drift. A check that cannot run is logged and skipped. Specification
errors are never a drift at the stop. The early migration notice still warns
at session start and at the stop.

Each drift not asked yet in this session becomes one question for the person,
all in one message, the result 2: align it now, at the end of the session, or
later. The message says what each answer means: now, align it in this
session; end of the session, leave it and remind the person once when the
session ends; later, run the item's `hook_gate.py later TEXT` command. That
command adds an item to `AHEAD.md` (kind `idea`, state `open`, with its
entry under Items) when the project uses the A-files and its AHEAD keeps the
index and the Items section; otherwise it appends a line to `up-deferred.txt`
in the git folder, which the open-work list shows at session start until the
line is removed. A drift recorded before is not recorded again. The session snapshot remembers which drifts were asked, so
the same drift is never raised again in that session, whatever the answer;
a new session asks again. If the git folder cannot be written, a file in the
system's temporary folder remembers them (the stop removes such files left
untouched for a day); if neither can be written, the stop
does not ask and passes the text on as a warning. With no new drift, the stop
prints nothing and passes.

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
failure or timeout produces no output and always exits 0. The generated eight-second
timeout includes stdin, computation and startup overhead.
Unsupported tools
receive the list at session start only. After-edit feedback contains only
findings the edited file can resolve: cross-file requirements, mechanism
vocabulary and another artifact's recognition errors stay in the open list.
An edited use case in an earlier format still warns with the migration notice.

A drift is known by its kind and subject (the use case and its new Status,
the record's path, the change that code without a specification belongs to,
known by the name of its base and the current branch, each A-files finding by
its path, its code and what its message names), never by its problem text, so
changed line numbers, a count that grows, more code in the same change, more
commits or pushes on the same branch, or a shorter problem list do not ask
again, and a new record or finding of the same kind is asked about once. A
base with no name is known by its commit. Without a session id the questions are
remembered under one shared slot. Report what remains rather than inventing
specification content.

## Updating installed copies

Run `scripts/scaffold_docs.py --update --root DIR` from the new plugin to
review the plan; add `--apply` only after approval. Running `--hooks` over an
existing setup also uses the update plan, avoiding mixed script releases.
The plugin's state reader and router show an advisory update notice with
both versions and this command. The installed session hook cannot know
about a newer plugin release and does not issue that notice.

`tools/specs/upspec-installed.json` records package baselines and kept
fingerprints, plus generated entries and adapted moments with reasons per
tool. The plan classifies scripts as current, untouched, kept, changed by
hand or missing. Current and kept copies stay; untouched copies refresh;
missing copies are added only to an installed set. An update alone never
installs hooks into a project that had none.

For every changed-by-hand script, read the diff and choose `--replace NAME`
to take the package copy, or `--keep NAME` after porting the customization
onto this release. A kept customization needs a fresh decision at the next
release; the old baseline is shown for context. It must carry this release's
version. Missing or mixed siblings make the gate return result 3 naming
`scaffold_docs.py --update`; they never block a stop. One exception: if
`hook_profiles.py` itself cannot load, the gate logs that failure and exits 0
with no output.

An ordinary update also plans wiring for every tool recorded in the bundle.
`--hooks` without `--tool` still requests scripts only. With several recorded
tools, select `--hooks --tool <tool>` when deciding a wiring moment. Use
`--replace wiring:<moment>` to generate its replacement, or
`--keep wiring:<moment>` to retain it and add nothing for that moment.
Moments are `session-start`, `after-edit`, `before-stop` and `turn-start`. Repeat
`--reason TEXT` in the order of the `--keep wiring:<moment>` arguments;
reasons are recorded in the bundle (default: "kept by the person").
A moment the profile no longer generates, but whose entry is still installed,
is undecided too: `--replace` removes the entry and puts nothing in its
place, and `--keep` retains it.

Fingerprints cover the command object and its group's matcher, or the
whole hook object where the file format requires it. Editing those wrapper
fields also makes an entry changed. Matching baselines refresh; exact
complete generated sets are current. A kept adaptation stays until another
decision is made. Undecided scripts or moments, or unreadable JSON, prevent
**every write**, including otherwise safe script updates. Resolve the whole
plan, approve, apply, then commit scripts and wiring on their own.

## Proving each hook

Configured is not proven. Start a new session with the approved hooks
trusted, and check both the tool's behavior and the git-folder log:

1. **Session state:** ask for the next step. The log shows
   `session-start exit=0` and the answer matches the state report.
2. **Specification check:** temporarily give a use case an invalid Status,
   then restore it. The log shows `after-edit exit=1`. Confirm the findings
   reach the agent as context, or the person, as the profile's capabilities
   state, and that the agent goes on with its task.
3. **Open work:** submit a prompt after changing an open item; confirm the
   list reaches the agent. An unchanged list prints nothing; an emptied one
   is announced once. Check `turn-start exit=0` and verify timeout or failure
   also lets the prompt through.
4. **The question:** raise an Approved use case to Implemented without its
   evidence. The log shows `before-stop exit=2`, and the agent asks the
   person: align now, at the end of the session, or later. End another turn:
   the log shows `before-stop exit=0` and nothing is asked again. Restore the
   Status; a broken Draft spec is never asked about.

The log records internal results, which can differ from the command's exit
code. Verify the tool version, warning delivery and trust behavior too.
Undo all proof edits. Mark an example proven only after observing its hooks
on that version; documentation alone does not establish delivery. Some tools
run project hooks only after the person approves them, or only in a
particular mode, so a hook that never logs a line usually means it was not
approved or not enabled.

## Recording what was wired

Under the profile line in the guideline's rules block, add:

```text
**Hooks:** session state, specification check, open work, claim check: <tool>, <configuration file>, seen firing <YYYY-MM-DD>
```

Name only moments seen firing, with any delivery limitation. Another agent
can read the line and prepare wiring for its own tool.

## Other tools and limits

A tool without a profile stays unwired until it has one. Additional profiles
are planned ideas, listed in the examples. Never substitute session-end for
before-stop; session-end cannot ask the person anything. Leave unsupported
moments out and explain why. The commit hook and the pipeline report and pass
unless the team added `--strict`.

Hooks provide feedback within the tool's sessions. Keep the commit hook
and team pipeline for everyone. Hooks never approve a specification, and
a passing finish check still needs a person to read the report.
