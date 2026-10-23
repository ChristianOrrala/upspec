# Profiles

How much discipline to apply, what each level turns on, and when to move up.

## Contents

- The deciding question
- Throwaway
- Solo
- Team
- Moving up
- Adopting it in an existing team
- What not to install

## The deciding question

> Will this system be maintained, extended, or handed over to someone else?

Discipline pays where a system lives long, changes often and is touched by
many people. A script that renames files once does not need a use case. A
booking system that will run for years does, from its first behavior on.

Apply the question to the system, not to the mood of the week. "We are in a
hurry" is not an answer to it.

## Throwaway

Nothing is set up. One line records the status and what ends it:

```text
This code is disposable. It becomes a maintained system, and gets specifications, when someone else depends on it, it is used as the base of the product, or it is still running after [end date].
```

When one of those events happens, do not "clean it up". Treat the code as an
existing system: recover the specifications of what will be kept, then go on
specification-first.

## Solo

One person, one agent at a time. The order is kept by habit and by a warning.

| Turned on | How |
|---|---|
| Vision | One page, written by the developer |
| Use case specifications | One file per use case, Status kept current |
| Catalog, entity model, diagram | As soon as the system stores data or passes a handful of use cases |
| Rules block | In the guideline file |
| Validator | After every specification edit |
| Review | A fresh context reads the specification before the developer signs it off |
| Guard | Warning, from a commit hook or run by hand |
| Agent hooks | Offered: session state, after-edit findings, open work at turn start, claim evidence at the stop (agent hooks reference) |

**Leaving artifacts out.** A solo project may leave out the requirements
catalog and the use case diagram while it has only a handful of use cases, and
the entity model if the system stores nothing. The vision and the use case
specifications are never left out. What is left out is recorded under the
profile line of the rules block, so that no skill keeps asking for it:

```text
**Profile:** solo
**Skipped:** requirements catalog, use case diagram
```

The scaffold writes that line with `--skip requirements --skip diagram`.
Remove a word from the line when the artifact is added later.

The weakest point of solo work is review: the author approves their own
specification. A fresh-context review (a new session that receives only the
specification and its neighbors, not the conversation that produced it)
replaces the second person as far as anything can.

**Commit hook, on request.** In `.git/hooks/commit-msg` (not versioned; each
clone installs its own):

```sh
#!/bin/sh
python3 path/to/spec_first_guard.py --staged --message-file "$1" --mode warn
```

Replace `path/to` with where the script lives in the project. In `warn` mode
the hook never stops a commit; it prints what it found.

## Team

Several people, or several agents in parallel. Informal discipline breaks
down here: two changes to the same use case, a fix that skipped the
specification, an approval nobody gave. The order is enforced.

| Turned on | How |
|---|---|
| The full chain | Vision, catalog, entity model, diagram, specifications, journey test cases |
| Ownership of `docs/` | The host's code owner rule; a named requirements owner |
| Review | An independent reviewer and a named person's sign-off before `Approved` |
| Pull request template | One use case per pull request; specification first |
| Pipeline | Claims and lint on every push and pull request; Draft findings warn. The guard blocks on pull requests and pushes to the integration or default branch; it warns on other pushes |
| Dashboard | Generated each iteration |
| Refinement | A short recurring session on upcoming use cases |
| Agent hooks | Offered; the pipeline stays the check that holds for everyone |

## Optional local push check (solo and team)

Offer `scaffold_docs.py --pre-push`, then add `--apply` after the plan is
accepted. It installs the claims script and its dependencies and a POSIX
`pre-push` hook in the folder returned by `git rev-parse --git-path hooks`,
which honors `core.hooksPath`. Setup writes only inside the work tree or git
folder, including the common Git folder shared by linked worktrees. If git tracks the hooks folder, the plan says the hook will be
committed for every clone. An outside folder or an existing hook is never
edited: the plan gives this line for its owner to add:

```sh
python3 tools/specs/status_claims.py --pre-push "$@" || exit 1
```

For each pushed ref whose tip is HEAD, the hook checks Status claims since
its remote tip (the resolved integration base for a new branch). Deletions
are skipped; other tips get a notice. It blocks only on problems. Missing
Python, missing scripts, an unknown revision or a crash lets the push through
with a notice. Uncommitted specification edits are included, with a notice
that the answer may differ from CI. `git push --no-verify` skips the hook.
CI stays the backstop and the authority.

The GitHub workflow is rendered with the integration branch in the rules
block. With no shared branch line, only the default branch blocks on push.
Pull requests compare against their target; pushes compare against the event's
previous commit when available. First pushes select from the integration
fork, or an empty baseline without an earlier fork. For evidence, pull requests
and integration or default branch pushes use the range base; other pushes
resolve the base as the stop does. Push commit messages
form the guard's declaration text; pull requests use their body. When a push
has no available previous tip, the guard judges only the last commit and
reads only that commit's message. A root commit is compared with an empty
tree rather than an absent parent.

`scaffold_docs.py --update` adds the claims dependencies wherever the workflow
exists, and offers the hook without installing it. Add `--pre-push --apply` to
install it. The bundle `tools/specs/upspec-installed.json` records both files.
An untouched workflow refreshes; a customized or unrecorded workflow needs
`--replace ci:specifications` or `--keep ci:specifications` before any write.
A recorded pristine package hook refreshes; a customized or unrecorded hook
stays with its owner and gets the line above. Agent wiring is still optional.

## Moving up

| From | To | When |
|---|---|---|
| Throwaway | Solo | An ending event from the status line occurs |
| Solo | Team | A second person commits, or two agents work in parallel on the same repository |
| Team | Bounded contexts | The specification set can no longer be reviewed as a whole, or teams collide under `docs/` |

Move up when the pain appears, not before. Each instrument answers a specific
failure; installed early, it is ceremony.

Record the profile in the rules block (`**Profile:**`). It is the one place
other skills read it from.

## Adopting it in an existing team

Do not announce a process. Take three steps, each with a check that says the
step is done.

| Step | Do | Done when |
|---|---|---|
| 1 | Pick one behavior that is contested or unclear today. Specify it as one use case: one main success scenario, a handful of alternative flows, explicit postconditions | Someone who did not write it has reviewed it and both agree on what it says |
| 2 | Implement that use case with its id in code and tests | Every flow and rule has a named test, and the suite passes |
| 3 | Make the next change to that behavior specification-first | The specification changed before the code did, in the same change set |

The first use case is small on purpose. The aim is the habit, not a perfect
document.

Expect a first stage where specifications are written after the code. It is a
stage, not the destination: maturity shows in whether intent and
implementation agree, not in how many documents exist.

## What not to install

- A task board, a ticket workflow or a second tracking system. Status in the
  specification is the tracking.
- A tool nobody has felt the need for. Start with Markdown, an agent and the
  rules block.
- Stack rules in the rules block. They have their own section.
