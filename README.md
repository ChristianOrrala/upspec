# upspec

Agent skills for specification-first development with use cases, for any
stack.

You write down what the system should do. A person reviews and approves it.
Only then does the agent write or change code, and scripts check the code and
the tests against what was approved. The skills cover the whole path: vision,
requirements, entity model, use cases, review, implementation, tests, change
and coverage. They also bring an existing codebase under specifications.

**Version 2.1.3.** Fifteen skills. Their scripts are tested against fixture
projects, and each skill is evaluated against sessions without it.

## Install

Claude Code:

```text
/plugin marketplace add ChristianOrrala/agents
/plugin install upspec@christianorrala
```

Codex:

```text
codex plugin marketplace add ChristianOrrala/agents
codex plugin add upspec@christianorrala
```

Then approve each hook once in Codex's `/hooks`.

Kiro CLI and OpenCode run the plugin from a full copy, kept in one place:

```sh
git clone --branch v2.1.3 https://github.com/ChristianOrrala/upspec.git ~/.local/share/agent-plugins/upspec
```

- **Kiro CLI:** link each folder under the copy's `skills/` into
  `~/.kiro/skills/`, copy `hooks/kiro/upspec.json` to `~/.kiro/hooks/`, trust
  the workspace, and set the V3 engine once:
  `kiro-cli settings chat.agentEngine v3`. Kiro runs hooks on no other engine.
- **OpenCode:** add the copy's `hooks/opencode` folder, as an absolute path,
  to the `plugins` array of `opencode.json`. Not `opencode plugin add`: it
  fetches only that folder, and the module then finds no gate and stays
  silent.

Other agents: copy the folders under `skills/` into the folder where your
agent finds skills, for example `.agents/skills/` in the project. Each skill
folder carries its own references, templates and scripts.

**Agent hooks.** The plugin carries four hooks that run the checks in the
agent's own tool: the state at session start, open work per prompt, the
validator after an edit and the finish check at the end of a turn. They act only
in a project whose guideline file carries the rules block, and stay silent
elsewhere. Each tool turns them on as above. A project wired by an earlier
release is cleaned up by `scaffold_docs.py --update` (see Upgrading from 1.x).

**Requirements:** Python 3.9 or later (the scripts use the standard library
only) and git.

## Upgrading from 1.x

Releases before 2.0.0 came from the marketplace `christian-orrala`
(ChristianOrrala/plugins) and wired the agent hooks into each project. On each
computer, once:

```sh
# Claude Code: leave the old marketplace, install from the new one
claude plugin uninstall upspec@christian-orrala
claude plugin marketplace remove christian-orrala
claude plugin marketplace add ChristianOrrala/agents
claude plugin install upspec@christianorrala

# Codex: the same, then approve each hook once in /hooks
codex plugin remove upspec@christian-orrala
codex plugin marketplace remove christian-orrala
codex plugin marketplace add ChristianOrrala/agents
codex plugin add upspec@christianorrala
```

A step for a tool or marketplace you never installed fails harmlessly. Kiro
CLI and OpenCode: follow Install above, and replace a skill folder an earlier
release copied into `~/.kiro/skills/`.

Then in each project set up by an earlier release, on its own branch:

```sh
python3 "<setup-skill>/scripts/scaffold_docs.py" --root . --update          # the plan; writes nothing
python3 "<setup-skill>/scripts/scaffold_docs.py" --root . --update --apply  # after you agree
```

`<setup-skill>` is the installed plugin's
`skills/up-bootstrapping-spec-driven-projects` folder (Claude Code:
`~/.claude/plugins/cache/christianorrala/upspec/<version>/`). The update
brings `tools/specs/` to this release, removes the hook-only scripts and
upspec's entries in the tool settings, and keeps everything else. Remove what
still names the old wiring by hand: a task to prove the hooks, a
`**Hooks:**` line, a restart line or map row that names `workflow_state.py`
or the hooks in `.claude/settings.json`. Commit the result on its own with
the line `No behavior change: none, tooling only.` in the message, so the
commit guard reads it as tooling. A second dry run reports `0 to write`.

## Quick start

Ask your agent in plain words. The right skill loads on its own.

| You have | Ask |
|---|---|
| A new project | *Set this repo up for spec-driven development.* |
| An existing codebase | *Reverse-engineer this system into specifications from its code.* |
| Work under way | *Where are we with the specs, and what comes next?* |

The last one runs the router. It reads the repository's state and names the
one next step and the skill that does it, so you never need to remember the
order.

In Claude Code you can also call a skill by name, for example
`/upspec:up-5-writing-use-case-specs`.

## What you get

- **Invention lists.** The agent lists every decision its inputs did not
  settle, instead of quietly choosing.
- **Status needs evidence.** A use case becomes Implemented or Tested only
  when a check or a report shows it.
- **Checks that hold.** Lint, the finish check, the guard check and coverage
  are scripts, so they work even when a model skips an instruction.
- **Reviewers that don't edit.** Review and audit report findings and leave
  the files alone.
- **A rigor dial.** Throwaway, solo or team: the ceremony fits the project.
- **People decide.** The vision is written by a person, and only a person
  approves a specification.

## The skills

Type `up-` to list them all. 0 and 1 are the two entries (0 for the state, 1 for a change); 2 to 9 are the artifact chain in the method's order; unnumbered skills are used when needed.

| Skill | What it does |
|---|---|
| `up-0-navigating-spec-driven-work` | Says where the project stands and what comes next |
| `up-1-triaging-change-requests` | Turns a bug, a change or a hotfix into a change that starts at the specification |
| `up-2-cataloging-requirements` | Builds the requirements catalog and records conflicts |
| `up-3-modeling-domain-entities` | Models the entities as a shared vocabulary, with their lifecycles |
| `up-4-mapping-use-cases` | Finds the use cases, at the right level, in delivery order |
| `up-5-writing-use-case-specs` | Writes one use case an agent can implement without inventing |
| `up-6-reviewing-specifications` | Lints and reviews specifications; reports only |
| `up-7-implementing-use-cases` | Implements one approved use case, or brings the code back in line |
| `up-8-deriving-use-case-tests` | Derives tests from the specification and proves they guard its rules |
| `up-9-auditing-spec-coverage` | Shows coverage from requirement to test; reports only |

Five more, without a number:

| Skill | What it does |
|---|---|
| `up-writing-journey-test-cases` | Writes end-to-end journeys across several use cases |
| `up-bootstrapping-spec-driven-projects` | Sets the repo up: rigor profile, docs tree, agent rules, team checks |
| `up-recovering-specs-from-code` | Recovers the specifications of an existing system |
| `up-splitting-bounded-contexts` | Splits a specification set that has grown too large for one review |
| `up-migrating-spec-formats` | Moves earlier specification formats to the current ones after your approval |

## How they fit together

```text
bootstrapping ─► vision (a person) ─► requirements ─► entities ─► use case map
                                                                        │
      ┌─────────────────────────────────────────────────────────────────┘
      ▼
  writing ─► reviewing ─► approval (a person) ─► implementing ─► tests ─► audit
                                                                   │
                                               journey test cases ◄┘

Triage turns every later request into a change that starts at the specification.
Recovery brings an existing system to the same starting point.
Splitting cuts a set that has outgrown review.
Migration moves a project from the earlier formats.
The router tells you where you are in this picture.
```

## One skill set at a time

Seven of these skills answer the same requests as other spec-driven skill
sets: requirements, the entity model, use case diagrams and specifications,
their review, test cases and recovery. With two such sets installed, both
respond. Keep one set installed for those requests.

## Documentation

[MANUAL.md](MANUAL.md) is the full guide: concepts, the project's files,
workflows for each kind of work, every check, rigor profiles, working with
different agents, safety and troubleshooting.

Nothing leaves your machine: no script calls a network service, and no skill
pushes, publishes or deploys.

## Credits

These skills are inspired by Simon Martinelli's work on the Unified Process.
They are an independent work, not affiliated with or endorsed by him.

## License

MIT. Copyright (c) 2026 Christian Orrala. See [LICENSE](LICENSE).
