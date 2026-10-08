# Team instruments

Four instruments that make the order hold when several people and agents work
in one repository. Each is described without a host, then with the form it
takes on GitHub and what to adapt elsewhere.

## Contents

- Ownership of the specifications
- The pull request
- The pipeline job
- The advisory review
- Refinement
- Changing the rules

## Ownership of the specifications

A change under `docs/` needs the review of the person or group that owns the
requirements. Without this, a specification can be edited to match whatever
the code already does.

Ask who the requirements owner is. Never invent a name, a handle or a team:
a wrong owner either blocks every pull request or protects nothing.

On GitHub, a code owners file (`CODEOWNERS` in `.github/`, the root or `docs/`):

```text
/docs/ ${REQUIREMENTS_OWNER}
```

`${REQUIREMENTS_OWNER}` stands for a user or team handle the owner gives you.
The file takes effect when the branch protection rule of the main branch has
"Require review from Code Owners" enabled; that setting is the repository administrator's to
make. Other hosts have an equivalent rule under the same or a similar file
name; use the host's documentation for the file's location and syntax.

## The pull request

One use case per pull request, containing the specification change and all
code and tests that follow from it. The reviewer can then judge one thing:
does this code do what this specification says?

The template (`pull-request.md` in this skill's templates) fixes the review
order:

1. **The specification change.** Is this the behavior we want? If not, stop:
   nothing below matters yet.
2. **The invention list.** What did the implementation decide that the
   specification left open? Behavior items go to the owner.
3. **The code against the specification.** Does it do that, and only that?
4. **The tests.** Is every flow and every rule exercised, on both sides of
   each boundary?

Reviewing the code first inverts the method: the reviewer then judges the
specification by whether it matches the code.

Location: `.github/pull_request_template.md` on GitHub;
`.gitlab/merge_request_templates/Default.md` on GitLab. The scaffold writes
it for those two hosts. Elsewhere, put it where the host looks for a default
description.

## The pipeline job

Two commands, both exact and repeatable, both blocking:

```bash
python3 tools/specs/spec_lint.py
python3 tools/specs/spec_first_guard.py --base <target branch> --message-file <pull request description> --mode block
```

- The **lint** fails on a specification that is not in the diagram, an
  identifier used twice, or a reference that points to nothing. Add
  `--strict` when the team wants warnings to fail too.
- The **guard** fails when behavior code changes with no specification change
  and no declaration, or arrives with a use case not yet approved.
- The job needs the full history of the branch (a shallow clone hides the
  base), and Python 3.9 or later. Nothing else.

The scripts live in the project under `tools/specs/`, copied there by the
scaffold, so the pipeline does not depend on any plugin being installed. When
this skill is updated, run the scaffold again in a branch to see whether the
copies differ; it never overwrites, so replace them deliberately.

On GitHub Actions the job is the workflow in this skill's templates
(`ci-github.yml`), written to `.github/workflows/specifications.yml`. It runs
on pull requests with read-only permissions and passes the pull request
description to the guard through a file, never by pasting it into a command.

Introducing the lint to an existing project: the first run may report old
findings. Let the owner decide between fixing them and recording a baseline
(the lint's `--update-baseline`), so that only new findings fail.

Run the project's own tests in the project's own job. Tests named after use
cases, flows and rules make a failure there name the behavior that drifted,
not only the build that broke.

## The advisory review

An agent may read a pull request's specification change and comment: unclear
steps, missing failure handling, contradictions with other use cases. This is
useful and it is judgment, so:

- it comments, it never blocks;
- it runs in a fresh context that did not write the change;
- it never approves, and never edits a `status` field.

Only the exact checks block. A pipeline that fails on an opinion teaches the
team to argue with the pipeline.

## Refinement

A short recurring session (weekly or every two weeks) where the people who
know the business and the people who build read the upcoming use cases
together. No estimation, no ceremony:

1. Read the next one or two `Draft` use cases aloud, flow by flow.
2. Collect what is unclear or contested as questions on the specification.
3. Decide what can be decided; name an owner for what cannot.

Work is pulled when a use case is `Approved`, not when a time box starts.

## Changing the rules

The rules block and these instruments are versioned with the code. A change
to them is a pull request like any other, reviewed by the team. A rule that
is ignored in practice is either enforced again or removed; a rule nobody
follows teaches that rules are optional.
