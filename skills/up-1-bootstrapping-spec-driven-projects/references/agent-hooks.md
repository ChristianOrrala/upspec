# Agent hooks

Three hooks that let the agent's own tool run the checks of the method at the
moments they matter. The agent wires them; the person turns them on. Labeled
examples for four tools are in agent-hook-examples.md, in this folder.

## Contents

- The three hooks
- The gate's result
- Setting them up
- Wiring rules
- Proving each hook
- Recording what was wired
- What hooks do not replace

## The three hooks

| Hook | Fires when | Runs | Strength |
|---|---|---|---|
| Session state | A session starts or resumes | `hook_gate.py session-start`: where each use case stands and the next step | Adds context; never blocks |
| Specification check | Right after the agent writes or edits a file | `hook_gate.py after-edit`: the validator on each use case specification among the edited files | Feeds errors back to fix now; the edit stays |
| Finish check | The agent is about to end its turn and hand back | `hook_gate.py before-stop`: the finish check for each change record still open | Keeps the agent working until the change is finished, or until the same problems come back a third time |

All three call one script. The checks live in the scripts it calls, never in
the tool's configuration: the configuration says only when the gate runs and
what its result means.

The finish check runs only while a change record is open: added or changed
and not committed, or changed on the current branch, and once the change
touches files outside the specification folder (`--docs`) and `tools/specs/`.
It stays quiet during triage, specification writing and review.

## The gate's result

| Exit | Meaning | What the tool must do with it |
|---|---|---|
| 0 | Pass | Nothing; text on stdout is context to add where the event allows it |
| 1 | Warn | Show the text; do not block. Some tools show it to the person only |
| 2 | Act | Block, or keep the agent working, with the text as the reason. The only result sure to reach the agent |
| 3 | The gate could not run | Never block; show the text to the person |

The gate reads the JSON the tool writes to its standard input and also takes
file paths as arguments. It finds the repository from its working directory.

## Setting them up

1. Copy the gate and the scripts it calls into the project:
   `scripts/scaffold_docs.py --hooks`, a dry run first, then `--apply`. They
   land in `tools/specs/`.
2. Wire the hooks into the tool the person uses, following the rules below.
3. Show the configuration and ask the person to turn it on. If they turn it on later, give them the proof steps below, so that they or the next session can run them.
4. Prove each hook.
5. Record what was wired.
6. Commit the copied scripts, the configuration and the record on their own,
   before any change. Hook files committed inside a change appear in its
   finish check as files no use case explains.

## Wiring rules

- **Project configuration.** Use the tool's project-level hook file, committed
  with the repository. Fall back to the person's own configuration only when
  the tool has no project level, and say so.
- **Real events only.** Map each hook to the event the tool really has: the
  start of a session; the moment after a file write or edit (filtered to the
  write and edit tools when the tool filters by tool); the end of the agent's
  turn. When the tool lacks one, leave that hook out and say which and why.
  Never stand another event in for it.
- **Narrow where the tool can.** When the tool filters a hook by file path or
  by an expression on the call, narrow the specification check to the use case
  folder. The gate filters anyway, so a tool that cannot narrow loses nothing.
- **The tool's own documentation decides** the event names, the filter syntax,
  and how a hook adds context, feeds back and keeps the agent working. The
  examples are a starting point, checked against one version each.
- **Map the result, nothing else.** When the tool reads exit codes and the
  standard error stream, send the gate's output to standard error for the
  specification check and the finish check. When the tool wants JSON, write a
  short adapter next to its configuration that runs the gate and turns its
  exit code into that JSON. Never copy a check into the adapter.
- **Keep the strength.** Do not turn a warning into a block or a block into a
  warning.
- **Run from the root.** Change to the repository root first
  (`git rev-parse --show-toplevel`), then call `tools/specs/hook_gate.py`.
- **A missing gate must not block.** When the interpreter cannot open a script
  it exits 2, which several tools read as "block". Run the gate only when its
  file is there: `if [ -f tools/specs/hook_gate.py ]; then python3 tools/specs/hook_gate.py <hook>; fi`.
  An adapter answers as for result 3 when the gate is missing.
- **Name the base when needed.** The gate tries `--base`, `UP_BASE`, the
  remote's default branch, then `origin/main`, `main`, `origin/master`, `master`.
  When the base branch is not found automatically, add `--base <branch>` to
  the before-stop command or set `UP_BASE`. The log says "no base known" if
  none can be found.
- **The person turns them on.** Tools protect their hook configuration from
  the agent: a protected folder, a trust prompt, a fingerprint the person
  approves. Prepare the configuration, show it, and let the person approve the
  write or the trust. Never bypass or widen permissions for it, in the wiring
  or in the proof.

## Proving each hook

A hook that was configured but never seen to fire is not done: documentation
and the running tool disagree often enough that only firing settles it.

Each firing appends a line to `up-hooks.log` in the repository's git folder
(`git rev-parse --git-path up-hooks.log`): the time, the hook, the exit code
and the files it looked at. With the hooks on, in a new session of the tool:

1. **Session state:** start the session and ask for the next step. The log
   shows `session-start exit=0`, and the answer matches the state report.
2. **Specification check:** change the Status of a use case to a value that
   does not exist, then put it back. The log shows `after-edit exit=2`, and
   the agent quotes the finding.
3. **Finish check:** with a change record open and unfinished and a changed file
   outside the specification folder and `tools/specs/`, end the turn.
   The log shows `before-stop exit=2`, and the agent keeps working or reports
   the problems. With no change open, it shows `before-stop exit=0`.

Undo every edit made for the proof.

## Recording what was wired

Add one line under the profile line of the rules block in the guideline file:

```text
**Hooks:** session state, specification check, finish check: <tool>, <configuration file>, seen firing <YYYY-MM-DD>
```

Name only the hooks that were seen firing. An agent of another tool reads the
line and knows it can wire its own.

## What hooks do not replace

- **The commit hook and the pipeline.** Agent hooks run only in sessions of
  the tool that has them; the commit hook of the profiles reference and the
  team's pipeline hold for every tool and every person.
- **The person's approval of a specification.** No hook approves anything.
- **Reading the report.** The finish check before a stop makes the agent
  finish; it does not make the change right.
