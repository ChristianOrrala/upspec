# Agent hooks

The agent prepares the hooks; the person approves and enables them. Generated
files and each tool's delivery limits are in `agent-hook-examples.md`.

## Contents

- The three hooks and results
- Generate, review, approve
- Integration branch
- Stop-time validation and the loop guard
- Updating installed copies
- Proving each hook
- Recording what was wired
- Other tools and limits

## The three hooks and results

| Moment | Gate command | What runs |
|---|---|---|
| Session starts or resumes | `hook_gate.py session-start` | The specification state and next step |
| After a file write or edit | `hook_gate.py after-edit` | Validation of the edited use case specifications |
| Before the agent ends its turn | `hook_gate.py before-stop` | Validation of changed specifications; during implementation, the finish check for open change records |

One gate owns the policy. Each firing uses one view of the change and runs
the checks in one process; a failed record does not prevent checking others.
The tool configuration selects the moment and an explicit output profile,
never reimplements a check or guesses the tool from environment variables.

| Internal result | Meaning | Delivery |
|---|---|---|
| 0 | Pass | Session text becomes context where supported |
| 1 | Warn | Never blocks; shown only where a warning channel exists |
| 2 | Act | Feedback after an edit, or keep working at the stop, where supported |
| 3 | The gate could not run | Never blocks; shown where the tool permits a warning |

These are the gate's internal results, not universal shell exit meanings.
`--emit raw` (the default) returns them directly; a named profile renders
what its tool accepts. The profiles live in `scripts/hook_profiles.py`,
including capabilities and message caps. An unavailable warning channel
cannot be created by changing an exit code. See the examples for the limits.

Each firing logs its moment, internal result and base in `up-hooks.log` in
the git folder (`git rev-parse --git-path up-hooks.log`). Stop entries also
name the change records considered.
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

## Stop-time validation and the loop guard

The stop validates changed use case specifications regardless of Status.
Errors warn during specification work and block during implementation;
validator warnings stay warnings. Work files are:

- the specification folder (`--docs`, otherwise the recorded folder);
- `tools/specs/`;
- the guideline file holding the rules block;
- root `ACTIVE.md`, `ABILITIES.md`, `AHEAD.md` and `ATLAS.md`.

Any other changed file makes the change implementation. Only then do open
change records also run through the finish check. Ignored specifications
count as changed at every stop; ignored records never open the finish check.
Setup warns about both. A deleted file can be attributed by the use case id
in its path or its text at the base, or by naming its exact repository-relative
path in the change record. Root A-files count as tracking in scope checks.

The loop guard counts distinct validation and finish problems, ignoring
validator line numbers. It gives up when the third consecutive blocked stop
has no fewer problems than the first, or on the sixth consecutive block even
when the count falls. It delivers the instruction to stop and report once;
the same problem set then only warns. A different set starts counting again.
A pass or warning resets the count. A gate that could not run neither counts
nor resets; a record whose check could not run warns, and a warning resets.
A supplied session id starts fresh for a new session; without one the count
can span sessions. If guard state cannot be stored, the gate warns instead
of trapping the agent.

The profile delivers give-up instructions through the available channel.
A tool without a stop-time warning channel may need one final continuation
to ask the agent to report and stop. Do not bypass the guard or invent
specification content to satisfy a check: report unresolved problems.

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
Moments are `session-start`, `after-edit` and `before-stop`. Repeat
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
   then restore it. The log shows `after-edit exit=2`. Confirm feedback
   reaches the agent or the person as the profile's capabilities state.
3. **Stop check:** first change only work files with an invalid specification;
   stopping warns. Then, with implementation changed and an unfinished open
   record, stop: the log shows `before-stop exit=2` and the agent continues
   where the profile supports it. Restore the proof edits and confirm a
   clean stop shows `before-stop exit=0`.

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
**Hooks:** session state, specification check, stop check: <tool>, <configuration file>, seen firing <YYYY-MM-DD>
```

Name only moments seen firing, with any delivery limitation. Another agent
can read the line and prepare wiring for its own tool.

## Other tools and limits

A tool without a profile stays unwired until it has one. Additional profiles
are planned ideas, listed in the examples. Never substitute session-end for
before-stop; session-end cannot keep the agent working. Leave unsupported
moments out and explain why.

Hooks provide feedback within the tool's sessions. Keep the commit hook
and team pipeline for everyone. Hooks never approve a specification, and
a passing finish check still needs a person to read the report.
