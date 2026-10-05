# Synchronization

Applying only the behavioral difference between two versions of a use case.
The alternative, regenerating, rewrites structure that was fine, loses
refinements, and produces a diff nobody can review.

## Contents

- The change list
- Working through it
- Both directions
- Drift is a decision
- Slices
- Branches and undoing
- Reporting

## The change list

```bash
python3 scripts/uc_change_list.py UC-012
python3 scripts/uc_change_list.py UC-012 --base v1.4.0
```

Without `--base` the script finds the last commit in which the file's Status
was `Implemented` or later and compares that version with the working tree.
With `--base` it compares against that revision.

| Exit code | Meaning | Do |
|---|---|---|
| 0 | A list of changes, possibly empty | Work through it |
| 3 | No earlier implemented version exists | Treat the use case as new: generate |
| 2 | Usage error, not a git repository, file not found | Fix the call |

An empty list means the specification's behavior did not change (only Status
or wording outside the elements). Then no code changes for this use case.

Without git, compare by hand: the version the code was built from against the
current file, element by element.

## Working through it

One change at a time, in this order: rules, preconditions, main scenario
steps, flows, postconditions.

| Change | Do |
|---|---|
| `added` rule, step or flow | Implement it, with marker |
| `changed` rule | Change the enforcing code and the marker text |
| `changed` step | Change what the step accepts, shows or records; nothing around it |
| `changed` flow | Change detection, steps or exit as the diff shows |
| `removed` anything | Remove the behavior it described, and its marker. A removal is invisible unless you look for it: the remaining specification is still satisfied by code that does too much |
| `changed` Requirements line | Read the newly linked rows; a new `NFR` or `C` is a new limit |
| `changed` actor | Change who may reach the behavior |

Leave everything else alone. No renaming, reformatting, reordering or
"while I am here" improvements: each makes the diff harder to check against
the change list.

## Both directions

Compare specification to code, then code to specification.

- Specification to code: every element of the change list has its change.
- Code to specification: read what the code and its comments attribute to
  this use case. Anything the specification no longer mentions is behavior to
  remove, if the change list shows it was removed.

## Drift is a decision

If existing code does something the specification never said, and the change
list does not explain it, you have found drift. It has two possible repairs:
the behavior is wanted and the specification must say so, or it is not and the
code must lose it. Choosing is the owner's call.

Report it with file and line, name both repairs, recommend neither, and
continue with the change list. Do not remove the behavior. Do not edit the
specification to match the code.

## Slices

A use case is built in slices: the main success scenario first, then
alternative flows by business priority. Some flows may never be built, on
purpose.

- State which elements the current slice covers. The plan lists only those.
- The first slice includes the guards and whatever keeps the failure
  postconditions true.
- A use case with some flows built and others waiting is in a normal state.
  Its Status moves to `Implemented` for the slice; say which flows are not
  built yet.
- One slice goes through plan, code, scope audit and tests in order. Slices of
  different use cases may be in different stages at the same time.

## Branches and undoing

- One branch per use case change. The specification change, the code and the
  tests travel together in one pull request, and the reviewer reads the
  specification first.
- A generation that went wrong is undone by discarding the branch. That
  deletes work: say what would be lost and get an explicit yes before running
  any command that discards commits or uncommitted changes.
- Never rewrite published history to hide a wrong attempt.

## Reporting

```text
UC-012 synchronized (slice: BR-001, BR-002, A1, A2)

Changed
  src/tasks/assignment.<ext>     BR-001 changed, BR-002 added, A2 added
  src/tasks/assign_view.<ext>    A1 message content

Invention list
  UC-012 A2  how the team-lead assignment is visible, to whom    behavior   asked; answer: shown in the task history
  UC-012 A2  where the record is stored                           mechanism  existing audit mechanism
  UC-012 A1  wording of the refusal beyond the stated content     free

Drift found
  src/tasks/assign_view.<ext>:88  sends a notice to the previous assignee; no step, flow or rule describes it

Verified: build, existing tests. Not verified: NFR-002 response time (no load test in the project).
Proposed Status: Implemented. Next: up-8-deriving-use-case-tests UC-012.
```
