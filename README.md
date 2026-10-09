# upspec

Agent skills for specification-first development with use cases, for any
stack.

You write down what the system should do. A person reviews and approves it.
Only then does the agent write or change code, and scripts check the code and
the tests against what was approved. The skills cover the whole path: vision,
requirements, entity model, use cases, review, implementation, tests, change
and coverage. They also bring an existing codebase under specifications.

**Version 1.0.3.** Fifteen skills. Their scripts are tested against fixture
projects, and each skill is evaluated against sessions without it.

## Install

Claude Code:

```text
/plugin marketplace add ChristianOrrala/plugins
/plugin install upspec@christian-orrala
```

Codex:

```text
codex plugin marketplace add ChristianOrrala/plugins
codex plugin add upspec@christian-orrala
```

Other agents: copy the folders under `skills/` into the folder where your
agent finds skills, for example `.agents/skills/` in the project. Each skill
folder carries its own references, templates and scripts.

**Requirements:** Python 3.9 or later (the scripts use the standard library
only) and git.

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

Type `up-` to list them all. The number is the skill's place in the chain.

| Skill | What it does |
|---|---|
| `up-0-navigating-spec-driven-work` | Says where the project stands and what comes next |
| `up-1-bootstrapping-spec-driven-projects` | Sets the repo up: rigor profile, docs tree, agent rules, team checks |
| `up-2-cataloging-requirements` | Builds the requirements catalog and records conflicts |
| `up-3-modeling-domain-entities` | Models the entities as a shared vocabulary, with their lifecycles |
| `up-4-mapping-use-cases` | Finds the use cases, at the right level, in delivery order |
| `up-5-writing-use-case-specs` | Writes one use case an agent can implement without inventing |
| `up-6-reviewing-specifications` | Lints and reviews specifications; reports only |
| `up-7-implementing-use-cases` | Implements one approved use case, or brings the code back in line |
| `up-8-deriving-use-case-tests` | Derives tests from the specification and proves they guard its rules |
| `up-9-auditing-spec-coverage` | Shows coverage from requirement to test; reports only |

Five side entries, without a number:

| Skill | What it does |
|---|---|
| `up-writing-journey-test-cases` | Writes end-to-end journeys across several use cases |
| `up-triaging-change-requests` | Turns a bug, a change or a hotfix into a change that starts at the specification |
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
